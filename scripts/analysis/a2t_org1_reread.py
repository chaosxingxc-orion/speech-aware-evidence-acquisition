#!/usr/bin/env python3
"""a2t_org1_reread.py -- re-read the Audio2Tool cell A2T-ORG-1 (the domain-grouped tool
registry, 2026-09-05, HARMFUL) against Audio2Tool's own null h_A2T (cell A2T-AA,
owner decision 167), for owner decision 166's records pass.

Inputs (sealed, read only):

* ORG-1: ``SAEA-A2T-ORG1-DOMAIN-GROUPED-V1`` / ``attempt-20260905T171519Z-org1groupedraw``
  (4,000 rows), manifest digest pinned by the verdict;
* its comparator exactly as the verdict paired it: each row's own sealed 2026-09-04
  official-protocol output, merged from the three official-population runs the receipt's
  ``baseline_sources`` names (manifest digests checked against the receipt);
* the roster ``A2T-PAIRED-400-V1`` (the tier-stratified 400 drawn from ORG-1's own
  union-4000), on which h_A2T was measured;
* CONTEXT ONLY: the sealed native-role direct rows (the A/A pair's comparator,
  ``SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1``) of the same 400 ids: levels and official
  tool-verdict agreement only.

Interval: the A2T-AA driver's own ``bootstrap`` (scripts/analysis/a2t_aa_paired_read.py):
tier-stratified paired bootstrap, the row as the resampling unit within tier, CI95, the
A2T-AA recipe's seed and draws, natural-mixture and equal-tier weightings. Delta = ORG-1
minus baseline (the verdict's sign convention).

MODEL-FREE: zero model, tokenizer, encoder, scorer, server, GPU and network contacts; the
sealed per-sample scores are read and nothing is re-scored. Only ids, tier and domain names,
counts, scores and hashes are used; no query text, transcript, gold tool, expected call,
predicted call or model output is printed or persisted.

Usage (WSL, the study venv)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$TREE/src \\
    python -B scripts/analysis/a2t_org1_reread.py --repo-root $TREE --data-root $DATA \\
      --lock $UMBRELLA/docs/datasets.lock.json \\
      --analysis-root $DATA/analysis/SAEA-A2T-ORG1-REREAD-H-A2T-V1
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

_REPO = Path(__file__).resolve().parents[2]

RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-org1-domain-grouped-4000-v1/"
    "result-summary.json"
)
AA_RECIPE = "docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1/analysis-recipe-v1.json"
AA_DRIVER = "scripts/analysis/a2t_aa_paired_read.py"
ORG1_MANIFEST_SHA = "55a6c23a03a2c882d5a7f8c25dddf7f21801e8d0192adfe53549ec6c7cf52087"
#: owner decision 167 (docs/results/2026-09-27-a2t-aa-paired-400-read.md section 4): the three
#: half-widths, and the A/A macro parameter-F1 offset (+2.23) as the parameter-F1 margin.
H_A2T = {
    "official_tool_accuracy": 1.625,
    "official_exact_match": 1.375,
    "repo_tool_accuracy": 1.875,
    "official_param_f1_macro": 2.23,
}
READ_METRICS = tuple(H_A2T)
#: verdict section 6 item 2: the comparator's tiers 2/5/8 flew at -np 3, the rest at -np 2.
NP3_TIERS = {"tier2_parametric", "tier5_needle", "tier8_intent_blending"}


class StopError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def aa_driver(repo: Path):
    spec = importlib.util.spec_from_file_location("a2t_aa_paired_read", repo / AA_DRIVER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class Scores:
    """Sealed per-sample scores of one or more runs, keyed by sample id."""

    def __init__(self, label: str, drv) -> None:
        self.label, self.drv = label, drv
        self.tables: dict[str, dict[str, dict]] = {}
        self.sources: list[dict] = []

    def add_run(self, data: Path, run_id: str, attempt_id: str, manifest_sha: str) -> None:
        drv = self.drv
        run_dir = data / "runs" / run_id / attempt_id
        manifest_path = run_dir / f"{run_id}.run-manifest.json"
        scores_path = run_dir / f"{run_id}.scores.json"
        m_sha, s_sha = sha(manifest_path), sha(scores_path)
        if m_sha != manifest_sha:
            raise StopError(f"{self.label}: {run_id} manifest digest differs from the pin")
        manifest = load(manifest_path)
        if manifest.get("status") != "COMPLETED":
            raise StopError(f"{self.label}: {run_id} manifest not COMPLETED")
        if (manifest.get("scores") or {}).get("sha256") != s_sha:
            raise StopError(f"{self.label}: {run_id} manifest does not pin the sealed scores bytes")
        scores = load(scores_path)
        for scorer in (drv.OFFICIAL, drv.REPO, drv.REPO_V2):
            dest = self.tables.setdefault(scorer, {})
            for sid, row in drv.per_sample(scores, scorer).items():
                if sid in dest:
                    raise StopError(f"{self.label}: sample {sid} scored twice")
                dest[sid] = row
        self.sources.append({
            "run_id": run_id,
            "attempt_id": attempt_id,
            "run_manifest_sha256": m_sha,
            "scores_sha256": s_sha,
            "study_commit": manifest.get("study_commit"),
            "rows": len(drv.per_sample(scores, drv.OFFICIAL)),
        })

    def metric(self, sid: str, name: str) -> float:
        scorer, field = self.drv.ROW_METRICS[name]
        v = self.tables[scorer][sid].get(field)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        return float(v or 0.0)

    def micro_counts(self, sid: str) -> tuple[int, int, int]:
        r = self.tables[self.drv.OFFICIAL][sid]
        return (
            int(r.get("param_correct_keys") or 0),
            int(r.get("param_predicted_keys") or 0),
            int(r.get("param_gold_keys") or 0),
        )


def paired(drv, left: Scores, right: Scores, ids: Sequence[str], tiers: np.ndarray, seed: int, draws: int) -> dict:
    deltas = {k: np.array([right.metric(s, k) - left.metric(s, k) for s in ids]) for k in drv.ROW_METRICS}
    ca, pa, ga = (np.array(x, dtype=float) for x in zip(*(left.micro_counts(s) for s in ids)))
    cb, pb, gb = (np.array(x, dtype=float) for x in zip(*(right.micro_counts(s) for s in ids)))
    out = drv.bootstrap(deltas, tiers, seed=seed, draws=draws, micro=(ca, pa, ga, cb, pb, gb))
    for k in drv.ROW_METRICS:
        v = deltas[k]
        out[k]["saves"], out[k]["harms"], out[k]["ties"] = int((v > 0).sum()), int((v < 0).sum()), int((v == 0).sum())
    return out


def level(drv, arm: Scores, ids: Sequence[str]) -> dict:
    out = {k: 100.0 * float(np.mean([arm.metric(s, k) for s in ids])) for k in drv.ROW_METRICS}
    c = [arm.micro_counts(s) for s in ids]
    out["official_param_f1_micro"] = 100.0 * drv._f1(sum(x[0] for x in c), sum(x[1] for x in c), sum(x[2] for x in c))
    return out


def classification_inputs(pair: dict) -> dict:
    out = {}
    for k in READ_METRICS:
        nat, eq, h = pair[k]["natural_mixture"], pair[k]["equal_tier"], H_A2T[k]
        point, (lo, hi) = nat["mean_delta_pp"], nat["ci95_pp"]
        out[k] = {
            "margin_pp": h,
            "natural_point_pp": point,
            "natural_ci95_pp": [lo, hi],
            "equal_tier_point_pp": eq["mean_delta_pp"],
            "equal_tier_ci95_pp": eq["ci95_pp"],
            "sign": "negative" if point < 0 else ("positive" if point > 0 else "zero"),
            "abs_point_beyond_margin": abs(point) > h,
            "ci95_upper_below_zero": hi < 0,
            "ci95_upper_below_minus_margin": hi < -h,
        }
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--repo-root", default=str(_REPO))
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--lock", required=True)
    ap.add_argument("--analysis-root", required=True)
    args = ap.parse_args(argv)
    repo, data = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    drv = aa_driver(repo)
    recipe = load(repo / AA_RECIPE)
    seed, draws = int(recipe["interval"]["seed"]), int(recipe["interval"]["draws"])
    receipt = load(repo / RECEIPT)

    org1 = Scores("org1", drv)
    org1.add_run(data, receipt["run_id"], receipt["attempt_id"], ORG1_MANIFEST_SHA)
    base = Scores("baseline", drv)
    for src in receipt["baseline_sources"]:
        base.add_run(data, src["run_id"], src["attempt_id"], src["manifest_sha256"])
    comp = recipe["arms"]["sealed_direct_comparator"]
    native = Scores("native_role_direct", drv)
    native.add_run(data, comp["run_id"], comp["attempt_id"], comp["run_manifest"]["sha256"])

    roster = load(repo / recipe["roster"]["relpath"])
    ids400 = [str(i["sample_id"]) for i in roster["items"]]
    tier_of = {str(i["sample_id"]): str(i["tier"]) for i in roster["items"]}
    ids4000 = sorted(org1.tables[drv.OFFICIAL])
    if len(ids4000) != 4000 or set(ids4000) != set(base.tables[drv.OFFICIAL]):
        raise StopError("ORG-1 and its baseline do not cover the same 4,000 ids")
    if not set(ids400) <= set(ids4000):
        raise StopError("the paired 400 is not a subset of ORG-1's 4,000")
    tier4000 = {s: str(org1.tables[drv.OFFICIAL][s]["tier"]) for s in ids4000}
    if any(tier4000[s] != tier_of[s] for s in ids400):
        raise StopError("roster tiers disagree with the sealed scores' tiers")

    if str(repo / "src") not in sys.path:
        sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: PLC0415
        domains_by_sample_id,
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    domain_of = domains_by_sample_id(load_lock(Path(args.lock)), data, ids400)

    t400 = np.array([tier_of[s] for s in ids400])
    t4000 = np.array([tier4000[s] for s in ids4000])
    pair400 = paired(drv, base, org1, ids400, t400, seed, draws)
    pair4000 = paired(drv, base, org1, ids4000, t4000, seed, draws)

    def groups(ids: Sequence[str], key) -> dict[str, list[str]]:
        g: dict[str, list[str]] = {}
        for s in ids:
            g.setdefault(key(s), []).append(s)
        return dict(sorted(g.items()))

    def table(gs: dict[str, list[str]]) -> dict:
        out = {}
        for g, sids in gs.items():
            lb, lo = level(drv, base, sids), level(drv, org1, sids)
            d = [org1.metric(s, "official_tool_accuracy") - base.metric(s, "official_tool_accuracy") for s in sids]
            out[g] = {
                "rows": len(sids),
                "baseline": lb,
                "org1": lo,
                "delta_pp": {k: lo[k] - lb[k] for k in lb},
                "official_tool_saves": sum(1 for x in d if x > 0),
                "official_tool_harms": sum(1 for x in d if x < 0),
            }
        return out

    geo = {
        "comparator_flew_np2": [s for s in ids400 if tier_of[s] not in NP3_TIERS],
        "comparator_flew_np3": [s for s in ids400 if tier_of[s] in NP3_TIERS],
    }
    geo4000 = {
        "comparator_flew_np2": [s for s in ids4000 if tier4000[s] not in NP3_TIERS],
        "comparator_flew_np3": [s for s in ids4000 if tier4000[s] in NP3_TIERS],
    }
    geo4000_paired = {}
    for g, sids in geo4000.items():
        block = paired(drv, base, org1, sids, np.array([tier4000[s] for s in sids]), seed, draws)
        geo4000_paired[g] = {
            "rows": len(sids),
            "paired_org1_minus_baseline": {k: block[k] for k in READ_METRICS},
            "classification_inputs": classification_inputs(block),
        }
    agree = sum(
        base.metric(s, "official_tool_accuracy") == native.metric(s, "official_tool_accuracy") for s in ids400
    )
    result = {
        "schema": "saea-a2t-org1-reread-against-h-a2t-v1",
        "cell": "A2T-ORG-1",
        "original_verdict": {
            "status": "HARMFUL",
            "receipt": RECEIPT,
            "receipt_sha256": sha(repo / RECEIPT),
            "rule": "CI90 upper bound below 0 at n = 4,000 (zero-referenced; no carrier null existed)",
        },
        "h_A2T": {
            "margins_pp": H_A2T,
            "source": "docs/results/2026-09-27-a2t-aa-paired-400-read.md section 4",
            "accepted_by": "owner decision 167",
            "valid_at": "n = 400 on A2T-PAIRED-400-V1, native-role direct form, np3 x 32,768, max_tokens 2048",
        },
        "interval": {
            "driver": AA_DRIVER,
            "driver_sha256": sha(repo / AA_DRIVER),
            "function": "bootstrap",
            "seed": seed,
            "draws": draws,
            "level": "CI95",
            "stratification": "tier",
            "seed_and_draws_source": AA_RECIPE,
            "sign": "ORG-1 minus baseline",
        },
        "sealed_sources": {
            "org1": org1.sources,
            "baseline": base.sources,
            "context_native_role_direct": native.sources,
        },
        "roster": {
            "roster_id": roster["roster_id"],
            "relpath": recipe["roster"]["relpath"],
            "split_identity_hash": roster["split_identity_hash"],
            "rows": len(ids400),
            "subset_of_org1_4000": True,
        },
        "paired_400": {
            "levels": {
                "baseline": level(drv, base, ids400),
                "org1": level(drv, org1, ids400),
                "context_native_role_direct": level(drv, native, ids400),
            },
            "paired_org1_minus_baseline": pair400,
            "classification_inputs": classification_inputs(pair400),
            "per_tier": table(groups(ids400, lambda s: tier_of[s])),
            "per_domain": table(groups(ids400, lambda s: domain_of[s])),
            "per_comparator_geometry": table(geo),
        },
        "full_4000_same_driver": {
            "levels": {"baseline": level(drv, base, ids4000), "org1": level(drv, org1, ids4000)},
            "paired_org1_minus_baseline": pair4000,
            "classification_inputs": classification_inputs(pair4000),
            "per_tier": table(groups(ids4000, lambda s: tier4000[s])),
            "per_comparator_geometry_paired": geo4000_paired,
        },
        "comparator_context": {
            "what": (
                "CONTEXT ONLY: the verdict's comparator (the 2026-09-04 official-protocol cells) against the "
                "A/A pair's comparator (the 2026-09-15 native-role direct) on the same 400 ids"
            ),
            "official_tool_verdict_agreement_rows": int(agree),
            "rows": len(ids400),
        },
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "gpu": 0, "network": 0},
        "privacy": "ids, tier and domain names, counts, scores and hashes only; no text, gold, call or output",
    }
    root = Path(args.analysis_root)
    root.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (root / "reread.json").write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"written": str(root / "reread.json"), "sha256": hashlib.sha256(text.encode()).hexdigest()}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StopError as error:
        print(f"a2t_org1_reread: STOP: {error}", file=sys.stderr)
        raise SystemExit(2) from None
