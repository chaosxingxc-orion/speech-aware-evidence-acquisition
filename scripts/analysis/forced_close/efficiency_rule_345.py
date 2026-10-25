"""efficiency_rule_345.py -- owner ruling 345 A (2026-10-24), intent test in the form of ruling 346 A (2026-10-25), applied beside a sealed NX-T Solver column read (model-free).

Ruling 345 A (registry docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, section 2026-10-24 17:50Z, quoted): "A Solver arm that cuts
the Solver forced-close share by >= 15 pp (absolute, against the in-flight twin / delivering lock of the same flight) with no resolved loss (SLU-F1
delta CI95 lower bound >= -1.49 pp AND intent delta CI95 lower bound >= -0.65 pp against the twin) enters the composed lock v3.x as an EFFICIENCY
component even when its pre-registered score word is NEUTRAL." Ruling 346 A (2026-10-25, section 2026-10-25 23:30Z) fixes the intent test: on a
1,080-row column the intent CI95 half-width is about 1 pp, so the literal lower-bound floor fails every null-intent arm; the intent test is the
preregistered NO-RESOLVED-LOSS form (intent delta CI95 UPPER bound >= -0.65 pp, i.e. no resolved intent loss) and the SLU test stays the lower-bound
form (SLU delta CI95 lower bound >= -1.49 pp). The preregistered readers are untouched (registered before the ruling); this script
reads the sealed trace and the official per-arm columns the reader already consumed and prints, per candidate arm against the delivering lock arm
(the reader's paired contrast; the twin supplies the offset):

  * the forced-close share of the arm and of the lock on the SAME rows, the paired per-row difference (pp) with an utterance-cluster bootstrap CI95
    (the reader's seed and draw count), and whether the cut reaches the 15 pp bar (point estimate);
  * Solver seconds per contact of the arm, of the lock, and the ratio;
  * the no-resolved-loss conditions in the RULED form (345 A + 346 A: SLU delta CI95 lower bound >= -1.49 pp; intent delta CI95 upper bound >= -0.65 pp), taken
    from the deltas the preregistered read wrote (``arm_words.words[arm].slu_ci95`` / ``intent_ci95``), never recomputed; the reader's own
    NO-RESOLVED-LOSS conditions (CI95 upper bounds for both) are carried beside them for reference;
  * the 345 verdict: ENTERS-LOCK-EFFICIENCY-345 when the cut reaches the bar AND both ruled-form conditions hold, otherwise NO-345.

Usage (after ``nxt_r<N>_read.sh`` has written ``read.json``):

    python -B scripts/analysis/forced_close/efficiency_rule_345.py --family nxt_r3 --data-root $SPEECHRL_DATA_DIR

Booleans and counts only; no utterance text, gold label, model output or reasoning text is opened. Write-once beside the read (``efficiency-345.json`` and
``efficiency-345.md`` in the read's analysis root).
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[2]
for _path in (str(_REPO / "src"), str(_REPO / "scripts" / "analysis"), str(_REPO / "scripts" / "flights" / "nx"), str(_REPO / "scripts" / "flights" / "direct"),
              str(_REPO / "scripts" / "flights" / "tfrl")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

FAMILIES = {
    "nxt_r3": {"family": "nxt_r3_family", "reader": "slurp_nxt_r3_solver_template_column_read"},
    "nxt_r4": {"family": "nxt_r4_family", "reader": "slurp_nxt_r4_solver_decoding_column_read"},
}
FORCED_CUT_BAR_PP = 15.0
SLU_LOSS_FLOOR_PP = -1.49   # decision 190 SLU floor, as the ruling states it (CI95 lower bound of the SLU delta)
INTENT_LOSS_FLOOR_PP = -0.65  # decision 190 intent floor; applied to the CI95 UPPER bound of the intent delta (ruling 346 A: no resolved intent loss)
RULING = ("owner ruling 345 A (2026-10-24; registry docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, section 2026-10-24 17:50Z) with the "
          "intent test in the form of ruling 346 A (2026-10-25; section 2026-10-25 23:30Z: intent delta CI95 upper bound >= -0.65 pp)")


def forced_share(rows: Sequence[Mapping]) -> float:
    seen = [r for r in rows if r["forced_close"] is not None]
    return 100.0 * sum(1 for r in seen if r["forced_close"]) / len(seen) if seen else float("nan")


def paired(arm_rows: Mapping[str, Mapping], lock_rows: Mapping[str, Mapping], cluster_of, seed: int, draws: int) -> dict:
    """Per-row forced-close difference (arm minus lock) on the rows both arms decoded with a wire record; utterance-cluster bootstrap CI95 in pp."""

    common = sorted(s for s in arm_rows if s in lock_rows and arm_rows[s]["forced_close"] is not None and lock_rows[s]["forced_close"] is not None)
    if not common:
        return {"rows": 0}
    by_cluster: dict[str, list[str]] = defaultdict(list)
    for sid in common:
        by_cluster[str(cluster_of(sid))].append(sid)
    clusters = sorted(by_cluster)

    def share(sids: Sequence[str], rows: Mapping[str, Mapping]) -> float:
        return 100.0 * sum(1 for s in sids if rows[s]["forced_close"]) / len(sids)

    point = share(common, arm_rows) - share(common, lock_rows)
    rng = random.Random(seed)
    deltas = []
    for _ in range(draws):
        picked = [rng.choice(clusters) for _ in clusters]
        sids = [s for c in picked for s in by_cluster[c]]
        deltas.append(share(sids, arm_rows) - share(sids, lock_rows))
    deltas.sort()
    lo, hi = deltas[int(0.025 * draws)], deltas[min(draws - 1, int(0.975 * draws))]
    both = sum(1 for s in common if arm_rows[s]["forced_close"] and lock_rows[s]["forced_close"])
    arm_only = sum(1 for s in common if arm_rows[s]["forced_close"] and not lock_rows[s]["forced_close"])
    lock_only = sum(1 for s in common if lock_rows[s]["forced_close"] and not arm_rows[s]["forced_close"])
    return {"rows": len(common), "clusters": len(clusters), "arm_forced_share": share(common, arm_rows), "lock_forced_share": share(common, lock_rows),
            "delta_pp": point, "ci95_pp": [lo, hi], "forced_both": both, "forced_arm_only": arm_only, "forced_lock_only": lock_only}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=sorted(FAMILIES), required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--force", action="store_true", help="overwrite an existing efficiency-345 output (development only)")
    args = parser.parse_args(argv)
    spec = FAMILIES[args.family]
    fam = importlib.import_module(spec["family"])
    reader = importlib.import_module(spec["reader"])
    base = reader.base
    npc = reader.npc
    root = args.analysis_root or (args.data_root / fam.ANALYSIS_ROOT)
    read_path = root / "read.json"
    if not read_path.exists():
        print(f"REFUSED: {read_path} is absent; run the preregistered read first", file=sys.stderr)
        return 2
    out = root / "efficiency-345.json"
    if out.exists() and not args.force:
        print(f"REFUSED: {out} exists (write-once)", file=sys.stderr)
        return 6
    read = json.loads(read_path.read_text(encoding="utf-8"))
    words = (read.get("arm_words") or {}).get("words") or {}
    cells = fam.CELLS
    paths = base.run_paths(args.data_root, cells["arm"]["run"], cells["arm"]["attempt"])
    outputs_rows = reader.load_outputs_rows(paths["outputs"])
    contacts = npc.trace_contacts(paths["trace"], fam.THINKING_KNOBS["budget_message"])
    crows = reader.contact_rows(outputs_rows, contacts)
    _ids, cluster_of, _scenario_of = base.roster_maps(args.repo_root / fam.ROSTER["arm"])
    by_arm: dict[str, dict[str, Mapping]] = defaultdict(dict)
    for r in crows:
        by_arm[r["arm"]][r["sample_id"]] = r
    delivering = reader.DELIVERING
    lock_rows = by_arm[delivering]
    seed, draws = getattr(reader, "SEED", 20261018), getattr(reader, "DRAWS", 10000)
    lock_seconds = statistics.fmean(r["latency_seconds"] for r in lock_rows.values() if r.get("latency_seconds") is not None)
    result = {"schema": "saea-efficiency-rule-345-v2", "ruling": RULING, "intent_test": "ci95-upper-bound (346 A)", "slu_test": "ci95-lower-bound (345 A)", "family": args.family, "read": str(read_path), "read_sealed_hashes": read.get("sealed_hashes"),
              "forced_cut_bar_pp": FORCED_CUT_BAR_PP, "slu_loss_floor_pp": SLU_LOSS_FLOOR_PP, "intent_loss_floor_pp": INTENT_LOSS_FLOOR_PP,
              "delivering": delivering, "seed": seed, "draws": draws,
              "lock": {"forced_share": forced_share(list(lock_rows.values())), "seconds_per_contact": lock_seconds, "rows": len(lock_rows)}, "arms": {}}
    for arm in reader.CANDIDATES:
        rows = by_arm.get(arm, {})
        word = words.get(arm) or {}
        if not rows or not word.get("slu_ci95") or not word.get("intent_ci95"):
            result["arms"][arm] = {"verdict": "ABSENT"}
            continue
        pair = paired(rows, lock_rows, cluster_of, seed, draws)
        seconds = statistics.fmean(r["latency_seconds"] for r in rows.values() if r.get("latency_seconds") is not None)
        cond = word.get("conditions") or {}
        cut_ok = pair.get("rows", 0) > 0 and (-pair["delta_pp"]) >= FORCED_CUT_BAR_PP
        slu_ok = word["slu_ci95"][0] >= SLU_LOSS_FLOOR_PP
        intent_ok = word["intent_ci95"][1] >= INTENT_LOSS_FLOOR_PP  # 346 A: upper bound (no resolved intent loss)
        verdict = "ENTERS-LOCK-EFFICIENCY-345" if (cut_ok and slu_ok and intent_ok) else "NO-345"
        result["arms"][arm] = {"quality_word": word.get("word"), "forced_share": forced_share(list(rows.values())), "paired_vs_lock": pair,
                               "seconds_per_contact": seconds, "seconds_ratio_vs_lock": seconds / lock_seconds if lock_seconds else float("nan"),
                               "forced_cut_reaches_bar": cut_ok,
                               "slu_no_resolved_loss_345": slu_ok, "intent_no_resolved_loss_345": intent_ok,
                               "reader_conditions": {"slu_no_resolved_loss": cond.get("slu_no_resolved_loss"), "intent_no_resolved_loss": cond.get("intent_no_resolved_loss")},
                               "slu_delta_pp": word.get("slu_delta_pp"), "slu_ci95": word.get("slu_ci95"),
                               "intent_delta_pp": word.get("intent_delta_pp"), "intent_ci95": word.get("intent_ci95"),
                               "verdict": verdict}
    lines = [f"# Efficiency rule 345 A beside the {args.family} read", "", f"{RULING}. Bar: forced-close share cut >= {FORCED_CUT_BAR_PP:.0f} pp against `{delivering}` "
             f"(paired per row, utterance-cluster bootstrap CI95, seed {seed}, {draws} draws) AND no resolved loss in the ruled form (SLU delta CI95 lower bound "
             f">= {SLU_LOSS_FLOOR_PP} pp; intent delta CI95 upper bound >= {INTENT_LOSS_FLOOR_PP} pp, ruling 346 A; deltas copied from the preregistered read, never recomputed). "
             "Development numbers; claims no benefit.", "",
             f"Lock arm `{delivering}`: forced share {result['lock']['forced_share']:.1f} %, {lock_seconds:.1f} s per Solver contact, {result['lock']['rows']} rows.", "",
             "| arm | quality word | forced share | delta vs lock (pp) CI95 | cut >= 15 pp | s / contact (ratio) | SLU delta CI95 | intent delta CI95 | no resolved loss, ruled form (SLU lo >= -1.49 / intent hi >= -0.65) | 345 verdict |",
             "| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |"]
    for arm, a in result["arms"].items():
        if a.get("verdict") == "ABSENT":
            lines.append(f"| {arm} | ABSENT | | | | | | | | ABSENT |")
            continue
        p = a["paired_vs_lock"]
        lines.append(f"| {arm} | {a['quality_word']} | {a['forced_share']:.1f} % | {p['delta_pp']:+.2f} [{p['ci95_pp'][0]:+.2f}, {p['ci95_pp'][1]:+.2f}] (n={p['rows']}) | "
                     f"{'yes' if a['forced_cut_reaches_bar'] else 'no'} | {a['seconds_per_contact']:.1f} ({a['seconds_ratio_vs_lock']:.2f}) | "
                     f"{a['slu_delta_pp']:+.2f} [{a['slu_ci95'][0]:+.2f}, {a['slu_ci95'][1]:+.2f}] | {a['intent_delta_pp']:+.2f} [{a['intent_ci95'][0]:+.2f}, {a['intent_ci95'][1]:+.2f}] | "
                     f"{a['slu_no_resolved_loss_345']} / {a['intent_no_resolved_loss_345']} | **{a['verdict']}** |")
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps({"written": str(out), "verdicts": {a: v.get("verdict") for a, v in result["arms"].items()}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
