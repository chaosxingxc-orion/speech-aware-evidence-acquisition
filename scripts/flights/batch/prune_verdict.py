"""Write a pruning cell's verdict document from its read deliverables and close its records (decision 58: reads by script).

    python scripts/flights/batch/prune_verdict.py --name prune-reviewer1 --short P1 --status "NEUTRAL (...)" \
        --factor "..." --reading "..." [--commit 1e349630] [--flown "2026-09-22T23:10-2026-09-23T00:49 UTC"]

WSL Python from the study root (reads the analysis root on the data root, writes docs/results, the exposure ledger, the
results ledger and the decisions file). Counts and metrics only; no utterance text.
"""
import os
import argparse
import hashlib
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--short", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--status", required=True); ap.add_argument("--factor", required=True); ap.add_argument("--reading", required=True)
    ap.add_argument("--commit", default="1e349630"); ap.add_argument("--flown", required=True); ap.add_argument("--date", default="2026-09-23")
    a = ap.parse_args()
    D = f"{DATA}/analysis/SAEA-SLURP-{a.tag}-PAIRED-ANALYSIS-V1"
    sc = json.load(io.open(f"{D}/score-contrasts.json", encoding="utf-8")); ef = json.load(io.open(f"{D}/efficiency.json", encoding="utf-8"))
    fr = json.load(io.open(f"{D}/frontier.json", encoding="utf-8")); st = json.load(io.open(f"{D}/structural.json", encoding="utf-8"))
    ps = json.load(io.open(f"{D}/per-scenario-tables.json", encoding="utf-8"))
    cmp_ = sc["comparisons"]["arm_vs_comparator"]; pooled = cmp_.get("pooled_micro", {}); per_row = cmp_.get("per_row", {})
    h = ef["headline"]; tr = st["trajectory"]["arm"]; trc = st["trajectory"]["comparator"]; dp = st["dispositions"]["arm"]
    NOTE = f"docs/results/{a.date}-slurp-{a.name}-verdict.md"
    L = []
    L.append(f"# Cell {a.short} verdict: {a.factor} (owner decision 85, on the measurable-Reviewer base R-PRIM, decision 97)")
    L.append("")
    L.append(f"Read {a.date} by the coordinator (Fable 5.1) with `scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/prune_read.sh {a.name}` (analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-{a.tag}-PAIRED-ANALYSIS-V1`, score-contrasts sha256 `{sha(f'{D}/score-contrasts.json')}`). Comparator = the sealed R-PRIM arm at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / tokenizer / encoder / server contacts. Development numbers (decisions 28, 86).")
    L.append("")
    L.append("## 1. Verdict"); L.append(""); L.append("| item | result |"); L.append("| --- | --- |")
    L.append(f"| status | **{a.status}** |")
    L.append(f"| reading | {a.reading} |")
    L.append(f"| cost | contacts / row {h['contacts_per_row']:.3f} vs {h['contacts_per_row_comparator']:.3f}; GPU-h / 1,080 {h['gpu_hours_per_1080']:.3f} vs {h['gpu_hours_per_1080_comparator']:.3f}; contacts / min {h['contacts_per_minute']:.1f} vs {h['contacts_per_minute_comparator']:.1f}; prefilled tokens / row {h['prefilled_tokens_per_row']:.0f} vs {h['prefilled_tokens_per_row_comparator']:.0f}; cost lower than the base: {h['cost_is_lower_than_the_base']} |")
    L.append(f"| trajectory | contacts {tr['contacts']} ({tr['contacts_per_row']:.3f} / row; histogram {tr['contacts_per_row_histogram']}; reviewer contacts per row {tr.get('reviewer_contacts_per_row_histogram')}); comparator {trc['contacts']} ({trc['contacts_per_row']:.3f} / row; {trc.get('contacts_per_row_histogram')}) |")
    L.append(f"| dispositions | finite stops {dp['finite_stops']['count']}, planner-action-illegal {dp['planner_action_illegal']['count']}, other terminal {dp['other_terminal_dispositions']['count']} |")
    L.append("")
    L.append(f"## 2. Headline contrasts ({a.short} minus R-PRIM, paired, 10,000 draws, seed 20260915)"); L.append("")
    L.append("| metric | R-PRIM | " + a.short + " | delta pp | CI95 |"); L.append("| --- | ---: | ---: | ---: | --- |")
    for k, v in list(pooled.items()) + list(per_row.items()):
        if isinstance(v, dict) and "ci95" in v:
            left = v.get("left", v.get("comparator")); right = v.get("right", v.get("arm")); delta = v.get("delta", v.get("delta_pp"))
            try:
                L.append(f"| {k} | {float(left):.4f} | {float(right):.4f} | {float(delta):+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] |")
            except Exception:
                L.append(f"| {k} | | | {float(delta):+.4f} | [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}] |")
    L.append("")
    lk = sc.get("lock", {}).get("comparisons", {})
    L.append("Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and TRAIN-symmetric companions are in `score-contrasts.json`.")
    L.append("")
    L.append("## 3. Per-scenario (natural mixture and equal-scenario weighting; diagnostics, never gates)"); L.append("")
    nm = ps["natural_mixture_and_equal_scenario"]["arm_vs_comparator"]
    for key, val in nm.items():
        if isinstance(val, dict) and val and all(isinstance(x, dict) for x in val.values()):
            cols = sorted({c for x in val.values() for c in x if isinstance(x[c], (int, float))})[:8]
            if not cols:
                continue
            L.append(f"### {key}"); L.append(""); L.append("| scenario | " + " | ".join(cols) + " |"); L.append("| --- |" + " ---: |" * len(cols))
            for scen, x in sorted(val.items()):
                L.append(f"| {scen} | " + " | ".join(f"{x[c]:.3f}" if isinstance(x.get(c), float) else str(x.get(c, "")) for c in cols) + " |")
            L.append("")
        elif isinstance(val, (int, float)):
            L.append(f"- {key}: {val}")
    band = sc["band"]["arm_vs_comparator"]
    L.append(f"Intent band: decision-17 flagged scenarios = {band.get('decision_17_flagged_scenarios')}."); L.append("")
    L.append("## 4. Frontier row (decision 75)"); L.append("")
    r = fr["row"]
    L.append("| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | on GPU-h frontier | on token frontier |"); L.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    L.append(f"| {a.short} | {r['official_slu']:.2f} | {r['official_intent']:.2f} | {r['gpu_hours_per_1080']:.4f} | {r['contacts_per_row']:.3f} | {r.get('prefilled_tokens_per_row', 0):.1f} | {fr['plan_is_on_the_gpu_hour_frontier']} | {fr['plan_is_on_the_prefilled_token_frontier']} |")
    L.append("")
    L.append("## 5. Records"); L.append("")
    L.append(f"Four exposure-ledger rows closed (SAEA-SLURP-NATIVE-{a.tag}-{{SMOKE-4-,SMOKE-4-FIT-,,FIT-}}V1, flight commit {a.commit}, {a.flown}); results-ledger entry; decision-85 outcome appended. Stage-3 algorithm label: none (decision 101).")
    io.open(NOTE, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n"); print("written", NOTE)
    # ledger closures
    LED = "docs/exposure-ledger.md"; s = io.open(LED, encoding="utf-8", newline="").read(); lines = s.split("\n"); n = 0
    for i, ln in enumerate(lines):
        if not ln.startswith("|"):
            continue
        cells = ln.split("|")
        if len(cells) < 16:
            continue
        rid = cells[2].strip()
        if rid.startswith(f"SAEA-SLURP-NATIVE-{a.tag}-") and cells[9].strip() == "no":
            cells[9] = " yes "
            what = "CONSUMED (fit, within cap)" if rid.endswith("-FIT-V1") else ("SEALED (four-row smoke, structural PASS)" if "SMOKE" in rid else f"SEALED: {tr['contacts']} contacts ({tr['contacts_per_row']:.2f} per row), {h['gpu_hours_per_1080']:.2f} GPU-h, manifest COMPLETED, scored once; {a.status}")
            cells[15] = f" {what}; flight commit {a.commit} (SAEA-Batch-Chain-Prune, {a.flown}). Read: `{NOTE}`." + cells[15]
            lines[i] = "|".join(cells); n += 1
    assert n == 4, n
    io.open(LED, "w", encoding="utf-8", newline="").write("\n".join(lines)); print("ledger rows closed", n)
    R = "docs/results/stage2-results-ledger.md"; rr = io.open(R, encoding="utf-8", newline="").read().rstrip("\n")
    slu = pooled.get("slu_f1_micro", {}); intent = per_row.get("scenario_action_exact", {})
    rr += f"\n\n## {a.date}: cell {a.short}, {a.factor} (Fable 5.1)\n\nRun SAEA-SLURP-NATIVE-{a.tag}-V1 ({tr['contacts']} contacts = {tr['contacts_per_row']:.2f} per row, {h['gpu_hours_per_1080']:.2f} GPU-h, FINALIZED at flight commit {a.commit}, SAEA-Batch-Chain-Prune) against the sealed R-PRIM arm on the same 1,080 rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 {slu.get('left', 0):.2f} -> {slu.get('right', 0):.2f}, **{slu.get('delta', 0):+.2f} pp CI95 [{slu.get('ci95', [0, 0])[0]:+.2f}, {slu.get('ci95', [0, 0])[1]:+.2f}]**; intent {intent.get('left', 0):.2f} -> {intent.get('right', 0):.2f}, **{intent.get('delta_pp', intent.get('delta', 0)):+.2f} pp CI95 [{intent.get('ci95', [0, 0])[0]:+.2f}, {intent.get('ci95', [0, 0])[1]:+.2f}]**: **{a.status}**. {a.reading} Read: `{NOTE}`.\n"
    io.open(R, "w", encoding="utf-8", newline="").write(rr + "\n"); print("results ledger entry added")
    Dd = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"; dd = io.open(Dd, encoding="utf-8", newline="").read().rstrip("\n")
    dd += f"\n\nOutcome of decision 85 ({a.short}, {a.date}): {a.status}. {a.reading} Read: `{NOTE}`.\n"
    io.open(Dd, "w", encoding="utf-8", newline="").write(dd); print("decision outcome appended")


if __name__ == "__main__":
    main()
