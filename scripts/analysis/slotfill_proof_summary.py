#!/usr/bin/env python3
"""Assemble the SLOTFILL falsifier receipt from the model-free runs (owner decision 159).

Reads the gap-decomposition receipt (``slotfill_gap_decomposition.py``, the reproduced ROLL-2
accounting) and the proof-bench receipts (``slotfill_fake_server_harness.py``, one per run of
one comparison pair), and writes into ``--out-dir``:

* ``gap-decomposition-v1.json`` -- the reproduction receipt, copied;
* ``bench/<label>.json`` -- each bench receipt with its per-contact digest KEYS re-keyed to
  ``sha256(row|contact)[:16]`` (a committed receipt carries no sample identifier) and its
  scratch paths dropped; the digest VALUES are untouched;
* ``proof-summary-v1.json`` -- the numbers the registration quotes: the reproduction, the
  byte-identity verdict over every run against the first key-off run, and the throughput table;
* ``MANIFEST.sha256`` -- ``<sha256> *<relpath>`` over every file but itself, the repository's
  convention, which ``scripts/checks/harness_admission_check.py`` re-verifies for a run-class
  switch's falsifier.

Zero contacts: it reads local JSON only. No utterance text, gold, model output or sample id.

    python3 scripts/analysis/slotfill_proof_summary.py --gap /tmp/saea-slotfill/gap-v1.json \\
        --bench off=/tmp/.../h-off-s.json --bench all=/tmp/.../h-all-s.json ... \\
        --out-dir docs/checks/speech-aware-evidence-acquisition/2026-09-27-dispatch-slot-fill-byte-identity-v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rekey(receipt: dict) -> dict:
    out = json.loads(json.dumps(receipt))
    for name, value in list(out.get("digests", {}).items()):
        if isinstance(value, dict):
            out["digests"][name] = {sha(k.encode())[:16]: v for k, v in sorted(value.items())}
    out.pop("run_dir", None)
    if isinstance(out.get("phase_supply"), dict):
        out["phase_supply"].pop("relpath", None)
    return out


def _minted(patterns) -> dict:
    """Each minted supply artifact's OWN recorded output digest (the digest a
    flip compares with the sealed PLAN preparation's), by the bench run that
    minted it; the bench receipts' ``output_sha256`` is a digest of the parsed
    output, kept for the within-group comparison."""

    import glob

    found = {}
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if not path.endswith(".json"):
                continue
            # phase-supply-<label>-<stamp>.json -> <label>
            label = Path(path).stem.removeprefix("phase-supply-").rsplit("-", 1)[0]
            found[label] = json.loads(Path(path).read_text(encoding="utf-8")).get("output_sha256")
    return {"count": len(found), "output_sha256_values": sorted(set(found.values())), "by_run": found}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gap", required=True)
    ap.add_argument("--bench", action="append", required=True, help="label=path; the FIRST is the key-off reference")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--statement", required=True, help="the honest throughput statement, one paragraph")
    ap.add_argument("--flown-bound", required=True, help="the flown-cell bound, one sentence")
    ap.add_argument("--minted-supply", action="append", default=[],
                    help="glob of the first-phase supply artifacts the bench minted (their own output_sha256 is read)")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    (out_dir / "bench").mkdir(parents=True, exist_ok=True)

    gap = json.loads(Path(args.gap).read_text(encoding="utf-8"))
    (out_dir / "gap-decomposition-v1.json").write_text(json.dumps(gap, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    rep = gap["reproduced_note_accounting"]
    fit = gap["fit_gate_on_the_server_clock"]

    benches = []
    groups: dict[str, list] = {}
    for item in args.bench:
        spec, _, path = item.partition("=")
        group, _, label = spec.rpartition("/")
        group = group or "main"
        receipt = rekey(json.loads(Path(path).read_text(encoding="utf-8")))
        receipt["comparison_group"] = group
        groups.setdefault(group, []).append((label, receipt))
        (out_dir / "bench" / f"{label}.json").write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        benches.append((label, receipt))

    # One scratch run id per comparison group (the run id enters every row's
    # QueryState id), so every run is compared with the FIRST run of its group.
    ref_label, ref = benches[0]
    comparisons = {}
    for members in groups.values():
        g_label, g_ref = members[0]
        for label, receipt in members[1:]:
            comparisons[f"{g_label} vs {label}"] = {
                name: (value == receipt["digests"][name]) for name, value in g_ref["digests"].items()
            }
    seals = {
        label: r["seal"]["status"] for label, r in benches
        if isinstance(r.get("seal"), dict) and r["seal"].get("status") not in (None, "NOT-REQUESTED")
    }
    all_identical = all(all(v.values()) for v in comparisons.values())
    supply = {label: r["phase_supply"]["output_sha256"] for label, r in benches}
    rows = {r["rows"] for _l, r in benches}
    contacts = {r["contacts"] for _l, r in benches}

    def tp(r):
        sa = r["slot_accounting"]
        return {
            "dispatch": r["dispatch_block"], "contact_window_s": sa["contact_window_s"],
            "empty_slot_share_pct": round(100 * sa["empty_slot_share"], 2), "all_slots_empty_s": sa["all_slots_empty_s"],
            "mean_busy_slots": sa["mean_busy_slots"], "contacts_per_hour_of_window": sa["contacts_per_hour_of_window"],
            "solver_role_input_mean_s": r["role_input_seconds"].get("solver", {}).get("mean"),
            "gc_pause_s_sum": r["gc"]["pause_s_sum"], "process_cpu_s": r["process_cpu_s"],
        }

    table = {label: tp(r) for label, r in groups[next(iter(groups))]}
    # the key-off runs are "off", "off2", ...; the all-switch runs "all", "all2", ...
    offs = [t for label, t in table.items() if re.fullmatch(r"off\d*", label)]
    ons = [t for label, t in table.items() if re.fullmatch(r"all\d*", label)]
    off_cph = sum(t["contacts_per_hour_of_window"] for t in offs) / len(offs)
    on_cph = sum(t["contacts_per_hour_of_window"] for t in ons) / len(ons) if ons else None
    on_empty = sum(t["empty_slot_share_pct"] for t in ons) / len(ons) if ons else None
    off_empty = sum(t["empty_slot_share_pct"] for t in offs) / len(offs)
    by_role = rep["turnaround_by_role"]
    summary = {
        "schema": "saea-slotfill-proof-summary-v1",
        "contacts_made": 0,
        "reproduction": {
            "run_id": gap["run_id"],
            "server_lifetime_index": rep["server_lifetime_index"],
            "joined_contacts": rep["joined_contacts"],
            "wall_s": rep["wall_s"],
            "empty_slot_s": rep["slot_capacity"]["empty_slot_s"],
            "client_turnaround_slot_s": rep["slot_capacity"]["client_turnaround_slot_s"],
            "all_idle_s": rep["states_s"]["all_idle"],
            "slot_seconds_total": rep["slot_capacity"]["slot_seconds_total"],
            "solver1_turnaround_mean_s": by_role["solver#1"]["turnaround_mean_s"],
            "turnaround_slot_s_by_role": {k: v["turnaround_slot_s"] for k, v in by_role.items()},
            "matches_note": bool(rep.get("matches_note")) and all(rep["matches_note"].values()),
            "matches_note_detail": rep.get("matches_note"),
            "fit_gate": {
                "fit_lock_busy_share_of_window": fit["fit_lock_busy_share_of_window"],
                "fit_duration_s": fit["fit_duration_s"],
                "fit_intervals_overlapping_their_predecessor": fit["fit_intervals_overlapping_their_predecessor"],
                "clock_note": "fit times are drvfs file times; the two causal bounds on the clock offset conflict at the 0.1 % tails (about +/-0.6 s of file-time jitter), so only medians of the split are read",
            },
            "solver_role_input_s_offline": table[ref_label]["solver_role_input_mean_s"],
        },
        "mechanism": {
            "finding": (
                "Rows in flight already exceed the slots (queue depth 4 x slots = 16 admitted rows over 4 slots), but every "
                "admitted row is pinned to one llama.cpp slot from its first contact to its delivery, because 88.9 % of the "
                "flown prompt tokens are served from that slot's KV prefix; releasing a slot between contacts would re-prefill "
                "a row's whole supply block (about 7,500 tokens, 3.3 s) to save a 0.5 s gap. The slots therefore empty while "
                "their OWN row prepares the next contact. The largest part of that preparation is the first Solver visit's "
                "role input: settle -> the train-exemplars recall (rails.kb_policy.multidim_recall, a pure-Python cosine over "
                "every exemplar key vector) -> material, run synchronously in the OpenJiuwen role-query component on the ONE "
                "asyncio event loop every row shares, so while one row recalls, no other row can route or dispatch; full "
                "garbage collections over the loaded key vectors freeze every thread at once."
            ),
            "dependency_verified": (
                "1b is POSSIBLE for the recall and IMPOSSIBLE for the rest: the exemplar recall's inputs are the frozen "
                "snapshot, the row's own sealed speech query record and the key vectors (rails.phase_supply supply_for_phase "
                "-> KbFacetProvider.candidates -> multidim_recall), none of which is the Perception answer; the rank, fusion "
                "and the candidate-bound slot-contract selection (candidate_supply.solver, candidate_state_phase perception) "
                "DO read the sealed Perception state and stay exactly where they are."
            ),
            "switches": {
                "recall_prefetch": "the row's Perception-independent recall submitted to one background worker at admission; the Solver visit consumes it through the provider's existing prepared-recall path; a revisit recomputes live",
                "role_input_offload": "the role-input builder awaited on ONE dedicated worker thread (role inputs stay mutually exclusive across rows, the calling task's context variables carried over)",
                "gc_freeze": "gc.collect(); gc.freeze() before the first episode, gc.unfreeze() after the last",
            },
            "default": "absent key = every committed configuration = the dispatch exactly as before; the parser refuses unknown keys, a wrong schema, non-boolean switches and a block that arms nothing",
        },
        "byte_identity": {
            "experiment": ref["experiment"],
            "rows": sorted(rows)[0] if len(rows) == 1 else sorted(rows),
            "contacts": sorted(contacts)[0] if len(contacts) == 1 else sorted(contacts),
            "reference": ref_label,
            "runs": [label for label, _r in benches],
            "comparisons": comparisons,
            "all_identical": all_identical,
            "supply_output_sha256_by_run": supply,
            "minted_first_phase_supplies": _minted(args.minted_supply),
            "supply_outputs_identical_within_each_group": all(
                len({supply[label] for label, _r in members}) == 1 for members in groups.values()
            ),
            "groups": {group: [label for label, _r in members] for group, members in groups.items()},
            "seal": seals,
            "seal_all_verified": bool(seals) and all(v == "VERIFIED" for v in seals.values()),
            "normalisation": (
                "exactly two facts are assigned by ARRIVAL and already differ between two runs of today's dispatcher: the "
                "request-id counter (flight-<n>) and the slot number (id_slot on the wire, slot_id / slot_ids in the sealed "
                "waves); each flight-<n> and each request sha256 is renamed to its own (row, contact) identity, the slot keys "
                "are masked, the runtime-trace digest (computed over the slot ids) is masked while its preimage records are "
                "compared, and latency_seconds is dropped. Every other byte is compared."
            ),
        },
        "throughput": {
            "service_model": "each request holds its slot for a deterministic draw from the sealed ROLL-2 per-role server busy times (launch to release) of the same role",
            "table": table,
            "offline_contacts_per_hour_off": round(off_cph, 1),
            "offline_contacts_per_hour_on": round(on_cph, 1) if ons else None,
            "offline_gain_pct": round(100 * (on_cph / off_cph - 1), 1) if ons else None,
            "offline_empty_share_off_pct": round(off_empty, 2),
            "offline_empty_share_on_pct": round(on_empty, 2) if ons else None,
            "off_vs_off_spread_pct": round(100 * (max(t["contacts_per_hour_of_window"] for t in offs) / min(t["contacts_per_hour_of_window"] for t in offs) - 1), 1) if len(offs) > 1 else None,
            "statement": args.statement,
            "flown_bound_statement": args.flown_bound,
        },
    }
    (out_dir / "proof-summary-v1.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    files = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256")
    manifest = "".join(f"{sha(p.read_bytes())} *{p.relative_to(out_dir).as_posix()}\n" for p in files)
    (out_dir / "MANIFEST.sha256").write_text(manifest, encoding="utf-8")
    print(json.dumps({"all_identical": all_identical, "gain_pct": summary["throughput"]["offline_gain_pct"],
                      "files": len(files)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
