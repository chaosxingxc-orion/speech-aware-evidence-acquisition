#!/usr/bin/env python3
"""NX R5 read helper (zero GPU, zero model contact): every cross-flight contrast of the composed read, under the DELIVERED columns and under
ONE normaliser (v4g applied offline to the v3 pools), with per-scenario tables in both weightings and the registered decision rule's
arithmetic.

Columns (all on the DEV-2000-ADDED roster, one sample id set, asserted):
  composed       the composed arm's DELIVERED answers (v4g at runtime)
  replicate      the module OFF-arm replicate's delivered answers (v3)
  a2_arm         the sealed A2 arm's delivered answers (v3)
  a2_aa          the sealed A2 in-chain A/A's delivered answers (v3)
  v4g(<pool>)    the registered ``saea-deliver-normalise-v4g`` applied to a v3 pool's delivered column through the SAME replay the apply
                 script uses (``analysis.deliver_normaliser_replay.replay_row``); labels are never touched (asserted per column)

Contrasts: the registered claim (a2_arm -> composed) read beyond the flight OFFSET (a2_aa -> replicate), the same-chain base
(replicate -> composed), the sealed base (a2_aa -> composed), and the same under v4g (v4g(left) -> composed). Statistics are the search
driver's own (``slurp_nx_postproc_v4_search.Bootstrap``): paired, whole-utterance clusters, 10,000 draws, seed 20260915, and the scored vectors
are the apply script's (``slurp_nx_postproc_v4_apply.score_vectors``), so a number here equals the apply script's on the same pair.

The decision-rule arithmetic (``rule_arithmetic``) only DESCRIBES which registered word each contrast satisfies; the verdict word is the
coordinator's (owner decision 139). Gold enters only through the governed devel loader, in memory. Nothing is printed or written but ids,
counts, rates, pp and hashes.

    python -B scripts/analysis/nx_r5_v4g_contrast.py --data-root "$SPEECHRL_DATA_DIR" --lock <datasets.lock.json> \\
        --out-dir "$SPEECHRL_DATA_DIR/analysis/<READ run>/v4g-contrast" [--recipe docs/readiness/<package>/analysis-recipe-v1.json]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

PACKAGE = "docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1"
SCHEMA = "saea-nx-r5-v4g-contrast-v1"
NORMALISER = "saea-deliver-normalise-v4g"
BAR_PP = 2.5
HARM_MARGIN_PP = 2.5


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rule_arithmetic(claim: Mapping[str, Any], offset: Mapping[str, Any], *, bar: float = BAR_PP, margin: float = HARM_MARGIN_PP) -> dict:
    """Which registered word the claim contrast (a2_arm -> composed) satisfies, given the offset contrast (a2_aa -> replicate).

    ``claim`` and ``offset`` are ``Bootstrap.contrast`` outputs. NOMINATED: SLU CI95 lower bound above |offset SLU| and the point at or
    above the bar, and intent not HARM. HARM: the CI95 upper bound of SLU or intent below -|offset| of that metric. NEUTRAL: neither, and
    both lower bounds at or above -margin. UNRESOLVED: neither NOMINATED nor HARM but a lower bound under -margin. Descriptive only."""

    o_slu, o_int = abs(float(offset["delta_slu_pp"])), abs(float(offset["delta_intent_pp"]))
    slu_lb, slu_ub = (float(x) for x in claim["ci95_slu_pp"])
    int_lb, int_ub = (float(x) for x in claim["ci95_intent_pp"])
    harm_slu, harm_int = slu_ub < -o_slu, int_ub < -o_int
    harm = harm_slu or harm_int
    nominated = slu_lb > o_slu and float(claim["delta_slu_pp"]) >= bar and not harm_int
    if nominated:
        word = "NOMINATED"
    elif harm:
        word = "HARM"
    elif slu_lb >= -margin and int_lb >= -margin:
        word = "NEUTRAL"
    else:
        word = "UNRESOLVED"
    return {"satisfies": word, "offset_abs_slu_pp": round(o_slu, 4), "offset_abs_intent_pp": round(o_int, 4), "bar_pp": bar,
            "harm_margin_pp": margin, "slu": {"delta": claim["delta_slu_pp"], "ci95": [slu_lb, slu_ub]},
            "intent": {"delta": claim["delta_intent_pp"], "ci95": [int_lb, int_ub]},
            "note": "descriptive: the verdict word is the coordinator's (owner decision 139)"}


def scenario_tables(ids: Sequence[str], gold: Mapping[str, Mapping], left, right, pooled) -> dict:
    """Per-scenario SLU-F1 and intent deltas, natural-mixture and equal-stratum weightings (the search driver's own SLU table, plus intent)."""

    from collections import defaultdict

    groups = defaultdict(list)
    for k, sid in enumerate(ids):
        groups[gold[sid]["scenario"]].append(k)
    table = {}
    for name in sorted(groups):
        rows = groups[name]
        lp, rp = pooled(left[rows]), pooled(right[rows])
        table[name] = {"rows": len(rows), "delta_slu_pp": round(rp["slu_f1_pp"] - lp["slu_f1_pp"], 4),
                       "delta_intent_pp": round(rp["intent_pp"] - lp["intent_pp"], 4)}
    n = len(table)
    all_l, all_r = pooled(left), pooled(right)
    return {"per_scenario": table,
            "natural_mixture": {"delta_slu_pp": round(all_r["slu_f1_pp"] - all_l["slu_f1_pp"], 4),
                                "delta_intent_pp": round(all_r["intent_pp"] - all_l["intent_pp"], 4)},
            "equal_stratum": {"delta_slu_pp": round(sum(v["delta_slu_pp"] for v in table.values()) / n, 4),
                              "delta_intent_pp": round(sum(v["delta_intent_pp"] for v in table.values()) / n, 4)}}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--recipe", default=f"{PACKAGE}/analysis-recipe-v1.json")
    parser.add_argument("--dry-run", action="store_true", help="resolve the recipe and the sealed paths, print identities, open no gold")
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    recipe = json.loads((REPO_ROOT / args.recipe).read_text(encoding="utf-8"))
    arms = recipe["arms"]
    pools = {
        "composed": arms["arm"], "replicate": arms["in_chain_replicate"], "a2_arm": arms["comparator"],
        "a2_aa": arms["a2_aa"],
    }
    paths = {}
    for name, spec in pools.items():
        directory = data_root / "runs" / spec["run_id"] / spec["attempt_id"]
        outputs = directory / f"{spec['run_id']}.outputs.jsonl"
        if not (directory / f"{spec['run_id']}.run-manifest.json").is_file() or not outputs.is_file():
            print(f"REFUSED: {name} ({spec['run_id']}) is not sealed under {directory}", file=sys.stderr)
            return 3
        paths[name] = outputs
    if args.dry_run:
        print(json.dumps({"dry_run": True, "pools": {n: str(p.relative_to(data_root)) for n, p in paths.items()}}, indent=2))
        return 0
    out_dir = Path(args.out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"REFUSED: {out_dir} already holds files; a sealed read is never overwritten", file=sys.stderr)
        return 6

    import numpy as np  # noqa: F401  (the search driver's Bootstrap needs it)

    from speech_aware_evidence_acquisition.analysis.deliver_normaliser_replay import replay_row
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401

    drv = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")
    apply_mod = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_apply.py", "slurp_nx_postproc_v4_apply")

    texts = {name: {str(r["sample_id"]): r.get("text") or "" for r in drv.iter_jsonl(path)} for name, path in paths.items()}
    ids = sorted(texts["composed"])
    for name, rows in texts.items():
        if sorted(rows) != ids:
            raise SystemExit(f"REFUSED: {name} does not cover the composed arm's sample ids exactly")
    gold = drv.load_gold(load_lock(Path(args.lock)), data_root, "devel")
    missing = [s for s in ids if s not in gold]
    if missing:
        raise SystemExit(f"REFUSED: {len(missing)} roster ids absent from the devel gold")
    normaliser = DELIVERY_NORMALISERS.resolve(NORMALISER)
    columns: dict[str, Any] = {}
    column_hashes: dict[str, str] = {}
    for name in ("composed", "replicate", "a2_arm", "a2_aa"):
        columns[name], _ = apply_mod.score_vectors(ids, texts[name], gold)
        column_hashes[name] = sha256_file(paths[name])
    for name in ("replicate", "a2_arm", "a2_aa"):
        edited = {sid: replay_row({"sample_id": sid, "text": texts[name][sid]}, normaliser=normaliser)["text"] for sid in ids}
        matrix, _ = apply_mod.score_vectors(ids, edited, gold)
        if any(matrix[k][9] != columns[name][k][9] for k in range(len(ids))):
            raise SystemExit(f"REFUSED: {NORMALISER} moved an intent label on the {name} pool")
        columns[f"v4g({name})"] = matrix
    boot = drv.Bootstrap(ids, {sid: gold[sid]["utterance_id"] for sid in ids})
    pooled = drv.pooled

    def contrast(left: str, right: str) -> dict:
        block = boot.contrast(columns[left], columns[right])
        block["left"], block["right"] = left, right
        block["scenarios"] = scenario_tables(ids, gold, columns[left], columns[right], pooled)
        return block

    delivered = {
        "claim: a2_arm -> composed": contrast("a2_arm", "composed"),
        "offset: a2_aa -> replicate": contrast("a2_aa", "replicate"),
        "same chain: replicate -> composed": contrast("replicate", "composed"),
        "sealed base: a2_aa -> composed": contrast("a2_aa", "composed"),
        "A2 reproduction: a2_aa -> a2_arm": contrast("a2_aa", "a2_arm"),
    }
    under_v4g = {
        "claim: v4g(a2_arm) -> composed": contrast("v4g(a2_arm)", "composed"),
        "offset: v4g(a2_aa) -> v4g(replicate)": contrast("v4g(a2_aa)", "v4g(replicate)"),
        "same chain: v4g(replicate) -> composed": contrast("v4g(replicate)", "composed"),
        "sealed base: v4g(a2_aa) -> composed": contrast("v4g(a2_aa)", "composed"),
        "offline gain: a2_arm -> v4g(a2_arm)": contrast("a2_arm", "v4g(a2_arm)"),
        "offline gain: replicate -> v4g(replicate)": contrast("replicate", "v4g(replicate)"),
    }
    rule = {
        "delivered": rule_arithmetic(delivered["claim: a2_arm -> composed"], delivered["offset: a2_aa -> replicate"]),
        "under_v4g": rule_arithmetic(under_v4g["claim: v4g(a2_arm) -> composed"], under_v4g["offset: v4g(a2_aa) -> v4g(replicate)"]),
    }
    report = {
        "schema": SCHEMA, "recipe": args.recipe, "recipe_sha256": sha256_file(REPO_ROOT / args.recipe), "rows": len(ids),
        "clusters": boot.clusters, "bootstrap": {"draws": drv.BOOT_DRAWS, "seed": drv.BOOT_SEED, "cluster": "utterance_id"},
        "normaliser": NORMALISER, "column_outputs_sha256": column_hashes,
        "delivered": delivered, "under_v4g": under_v4g, "decision_rule_arithmetic": rule, "status": "DESCRIPTIVE",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "network": 0, "gpu": 0, "paid_api": 0},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"written": str(out_dir / "report.json"), "rows": len(ids), "delivered_rule": rule["delivered"]["satisfies"],
                      "under_v4g_rule": rule["under_v4g"]["satisfies"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
