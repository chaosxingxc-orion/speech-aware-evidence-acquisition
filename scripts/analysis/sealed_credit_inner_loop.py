#!/usr/bin/env python3
"""CLI for the sealed-credit inner loop, run 1 (design spec task 7).

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/sealed_credit_inner_loop.py \\
        --pools configs/analysis/sealed-credit-pools-v1.json \\
        --policy-space configs/analysis/sealed-credit-policy-space-v1.json \\
        --read-design same-flight-supply-variant --out "$SPEECHRL_DATA_DIR/analysis/<id>" \\
        [--dry-run] [--check] [--data-root ...] [--lock ...] [--rows N] [--workers 4]

Model-free: registers no cell, authorises no flight, contacts no model/server/GPU.
``--dry-run`` validates the pool manifest and policy space (roster overlap, knob
shape, ``SUPPLY_VARIANT_KNOB_TAILS`` admission) and prints a summary WITHOUT
opening a single sealed run or loading gold. Without ``--dry-run`` it extracts
every TUNING pool's row/item state, builds the credit table, estimates every
non-excluded knob value, ranks candidates under ``--read-design``'s guard/floor
(``scripts/checks/stage3_effect_floor_check.py``), and writes:

* ``row-states.jsonl`` -- one line per (pool, sample id): node-state booleans/
  ranks/classes only, never filler text;
* ``credit.json`` -- the hash-pinned credit table (``analysis.sealed_credit.
  credit.build_credit_table``);
* ``candidates.json`` -- every candidate, ranked, with its predicted effects,
  the read design's guard/floor, and ``clears_floor``;
* ``nomination.json`` -- the one nominated candidate, or none and why;
* ``report.md`` -- counts-only markdown summary;
* ``content-sha256.json`` -- the sha256 of every file above.

Refuses a non-empty ``--out`` without ``--check`` (which re-derives and diffs
byte-for-byte, like every other sealed analysis driver in this repository).
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.analysis.sealed_credit import (  # noqa: E402
    accept,
    credit,
    estimate,
    policy_space as ps,
    pools as pl,
    row_states as rs,
)
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
READ_DESIGNS = {
    "same-flight-supply-variant": ("same-flight-supply-variant", 1080),
    "cross-flight": ("cross-flight-with-in-chain-replicate", 1000),
    # run 2: the composed-policy question at the Fold A arm size (COMP-1 / COMP-1b read at
    # n = 1,080 against their in-chain A/A; rule-3 bar 2.5 pp at 1,080).
    "cross-flight-with-in-chain-replicate": ("cross-flight-with-in-chain-replicate", 1080),
    # run 3: the Perception-branch same-flight design (owner decision 190 puts the same two
    # per-metric anchors on it as on the supply-variant design).
    "same-flight-perception-variant": ("same-flight-perception-variant", 1080),
}
RECIPE = "sealed-credit-inner-loop-run-1-v1"


class CliError(RuntimeError):
    pass


def strip_time(text: str) -> str:
    import re

    return re.sub(r'"generated_at[^"]*": "[^"]*"', "", text)


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_gold_for_pools(pools_list: list[dict], lock, data_root: Path, workers: int) -> dict:
    """Gold OFFLINE, on the scoring side only, through the governed loader --
    every one of run 1's tuning pools is on the TRAIN split."""

    records = load_slurp_split(lock, data_root, "train", workers=workers)
    return {r.sample_id: r for r in records}


def build_pairs_from_policy_space(policy: dict) -> list[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for knob in policy["knobs"]:
        for value in knob.get("values", []):
            source = value["conversion_source"]
            if source["type"] == "pool_pair_delta":
                right, left = source["pools"]
                pairs.add((right, left))
    return sorted(pairs)


def row_state_lines(pools_extracted: list[dict]) -> list[str]:
    lines = []
    for pool in sorted(pools_extracted, key=lambda p: p["label"]):
        for sid in sorted(pool["rows"]):
            row = pool["rows"][sid]
            record = {
                "pool": pool["label"], "sample_id": sid,
                "block_pos": row["block_pos"], "perc_rank": row["perc_rank"],
                "perc_rank_bucket": row["perc_rank_bucket"],
                "s1_ok": row["s1_ok"], "s_last_ok": row["s_last_ok"], "d_ok": row["d_ok"],
                "revised": row["revised"], "reviewer_visited": row["reviewer_visited"],
                "normaliser_changed": row["normaliser_changed"],
            }
            lines.append(json.dumps(record, sort_keys=True))
    return lines


def render_report(
    credit_table: dict, ranked: list[dict], nomination: dict, design: str, rows: int,
    run_label: str = "run 1", compositions: list[dict] | None = None, top_n: int = 5,
) -> str:
    recipe = RECIPE if run_label == "run 1" else f"sealed-credit-inner-loop-{run_label.replace(' ', '-')}-v1"
    lines = [
        f"# Sealed-credit inner loop, {run_label} -- model-free read", "",
        f"Read design: `{design}` at n = {rows}. Recipe `{recipe}`. Counts and rates only.", "",
        "## Pools", "",
        "| pool | kind | rows | d_ok | s1_ok |", "| --- | --- | --- | --- | --- |",
    ]
    for label, entry in sorted(credit_table["pools"].items()):
        h = entry["headline"]
        lines.append(f"| {label} | {h['kind']} | {h['rows']} | {h['d_ok']} | {h['s1_ok']} |")
    with_status = any("status" in c for c in ranked)
    lines += ["", f"## Top {top_n} candidates (ranked by predicted intent gain)", ""]
    if with_status:
        lines += ["| rank | knob | value | predicted intent pp | predicted SLU pp | guard | floor | clears floor | status |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    else:
        lines += ["| rank | knob | value | predicted intent pp | predicted SLU pp | guard | floor | clears floor |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in ranked[:top_n]:
        row = (
            f"| {c['rank']} | {c['knob_id']} | {c['value']} | {c['predicted_intent_pp']:.4f} | "
            f"{c['predicted_slu_pp'] if c['predicted_slu_pp'] is not None else 'n/a'} | "
            f"{c['guard_pp']:.4f} | {c['floor_pp']:.4f} | {c['clears_floor']} |"
        )
        lines.append(row + (f" {c.get('status', 'open')} |" if with_status else ""))
    lines += ["", "## Nomination", ""]
    if nomination["nominated"]:
        top = nomination["candidate"]
        lines.append(
            f"Nominated: `{top['knob_id']}` = `{top['value']}` (predicted intent "
            f"{top['predicted_intent_pp']:+.4f} pp, floor {top['floor_pp']:.4f} pp, claim ceiling `nominated`)."
        )
    else:
        lines.append(f"No candidate nominated: {nomination['reason']}.")
    for c in nomination.get("cleared_but_not_open", []):
        lines.append(
            f"Clears the floor but not open ({c['status']}, never nominated): `{c['knob_id']}` = "
            f"`{c['value']}` (predicted intent {c['predicted_intent_pp']:+.4f} pp)."
        )
    if compositions:
        lines += ["", "## Composed policies (additive; overlapping rows not de-duplicated)", "",
                  "| id | components | predicted intent pp | predicted SLU pp | guard | floor | guard discarded | clears floor |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for c in compositions:
            parts = " + ".join(f"{p['knob_id']}={p['value']}" for p in c["components"])
            slu = f"{c['predicted_slu_pp']:+.4f}" if c["predicted_slu_pp"] is not None else "n/a"
            lines.append(
                f"| {c['id']} | {parts} | {c['predicted_intent_pp']:+.4f} | {slu} | {c['guard_pp']:.4f} | "
                f"{c['floor_pp']:.4f} | {c['guard_discarded']} | {c['clears_floor']} |"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pools", required=True)
    parser.add_argument("--policy-space", required=True)
    parser.add_argument("--read-design", required=True, choices=sorted(READ_DESIGNS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--rows", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--run-label", default="run 1", help="report title label, e.g. 'run 2'")
    parser.add_argument("--compositions", default=None,
                        help="optional JSON {schema, compositions: [{id, components: [{knob_id, value}]}]}")
    parser.add_argument("--top", type=int, default=5, help="candidates shown in report.md")
    args = parser.parse_args(argv)

    manifest = pl.load_manifest(Path(args.pools))
    findings = pl.roster_findings(manifest, REPO_ROOT)
    blocking = [f for f in findings if f["severity"] == "blocking"]
    for finding in findings:
        print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    if blocking:
        print("refused: blocking roster finding(s) above", file=sys.stderr)
        return 1

    policy = ps.load_policy_space(Path(args.policy_space))
    ps.validate_supply_variant_routes(policy)
    tuning_labels = {p["label"] for p in pl.pools_by_use(manifest, "tuning")}
    ps.validate_tuning_sources(policy, tuning_labels)

    design, default_rows = READ_DESIGNS[args.read_design]
    rows = args.rows if args.rows is not None else default_rows

    if args.dry_run:
        print(f"dry-run OK: {len(manifest['pools'])} pool(s), {len(policy['knobs'])} knob(s), "
              f"{len(tuning_labels)} tuning pool(s), read design {design!r} at rows={rows}")
        return 0

    out_dir = Path(args.out)
    if out_dir.exists() and any(out_dir.iterdir()) and not args.check:
        print(f"refused: {out_dir} is non-empty; pass --check to verify reproducibility instead", file=sys.stderr)
        return 1

    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    tuning_pools = pl.pools_by_use(manifest, "tuning")
    gold = load_gold_for_pools(tuning_pools, lock, data_root, args.workers)

    extracted = []
    for pool in tuning_pools:
        phases_dir = None
        if pool.get("phases_attempt"):
            # a seal-only completion: outputs + scores in ``attempt``, phases in the predecessor
            phases_dir = pl.attempt_dir(data_root, pool["run_id"], pool["phases_attempt"])
            attempt = data_root / "runs" / pool["run_id"] / pool["attempt"]
            if not (attempt / f"{pool['run_id']}.scores.json").is_file():
                print(f"refused: {pool['label']}: seal-only attempt carries no scores", file=sys.stderr)
                return 1
        else:
            attempt = pl.attempt_dir(data_root, pool["run_id"], pool.get("attempt"))
        extracted.append(rs.extract_pool(pool, data_root, gold, attempt, phases_dir))

    pairs = build_pairs_from_policy_space(policy)
    credit_table = credit.build_credit_table(extracted, pairs=pairs)
    pools_by_label = {p["label"]: p for p in extracted}
    estimates = estimate.estimate_all(policy, pools_by_label, REPO_ROOT, data_root)
    ranked = accept.rank_candidates(estimates, design, rows, REPO_ROOT)
    nomination = accept.nominate(ranked)
    compositions = None
    if args.compositions:
        comp_doc = json.loads(Path(args.compositions).read_text(encoding="utf-8"))
        if comp_doc.get("schema") != "saea-sealed-credit-compositions-v1":
            print("refused: --compositions schema must be 'saea-sealed-credit-compositions-v1'", file=sys.stderr)
            return 1
        compositions = accept.score_compositions(estimates, comp_doc["compositions"], design, rows, REPO_ROOT)

    texts = {
        "row-states.jsonl": "\n".join(row_state_lines(extracted)) + "\n",
        "credit.json": json.dumps(credit_table, indent=2, sort_keys=True) + "\n",
        "candidates.json": json.dumps(
            {"schema": "saea-sealed-credit-candidates-v1", "read_design": design, "rows": rows,
             "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "candidates": ranked},
            indent=2, sort_keys=True,
        ) + "\n",
        "nomination.json": json.dumps(
            {"schema": "saea-sealed-credit-nomination-v1", "read_design": design, "rows": rows, **nomination},
            indent=2, sort_keys=True,
        ) + "\n",
        "report.md": render_report(credit_table, ranked, nomination, design, rows,
                                   run_label=args.run_label, compositions=compositions, top_n=args.top),
    }
    if compositions is not None:
        texts["compositions.json"] = json.dumps(
            {"schema": "saea-sealed-credit-composition-scores-v1", "read_design": design, "rows": rows,
             "compositions": compositions},
            indent=2, sort_keys=True,
        ) + "\n"

    if args.check:
        if not out_dir.is_dir():
            print(f"refused: --check given but {out_dir} does not exist", file=sys.stderr)
            return 1
        bad = []
        for name, text in texts.items():
            existing_path = out_dir / name
            if not existing_path.is_file():
                bad.append(name)
                continue
            if strip_time(existing_path.read_text(encoding="utf-8")) != strip_time(text):
                bad.append(name)
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest_hashes = {name: _digest_text(strip_time(text)) for name, text in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(
        json.dumps(manifest_hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    print(f"wrote {out_dir}")
    print(json.dumps(manifest_hashes, indent=2))
    top5 = ranked[:5]
    print("\ntop 5 candidates by predicted intent gain:")
    for c in top5:
        print(f"  rank {c['rank']}: {c['knob_id']}={c['value']!r} intent={c['predicted_intent_pp']:+.4f}pp "
              f"slu={c['predicted_slu_pp']} clears_floor={c['clears_floor']}")
    print("\nnomination:", "NONE (" + nomination.get("reason", "") + ")" if not nomination["nominated"]
          else f"{nomination['candidate']['knob_id']}={nomination['candidate']['value']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
