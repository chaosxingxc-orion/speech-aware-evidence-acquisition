"""Dump every recall the identity proof compares, from ONE tree (old or new).

Usage: PYTHONPATH=<tree>/src python recall_dump.py --tree <tree> --out <jsonl> [--workers N]

Every record is one (roster, row, store, k): the recall mapping exactly as
multidim_recall / multidim_segment_recall returned it -- insertion order kept,
every score as float.hex (bitwise). Records are written in a fixed order so the
two trees' files compare line by line.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall_io as rio  # noqa: E402

EXEMPLAR_KS = (8, 20, 60)
IB_KS = {"key-encoding": (8, 16, 60), "centroid-keys": (8, 60)}

STATE = {}


def canon(recalled):
    return [[fid, [[dim, float(score).hex()] for dim, score in dims.items()]] for fid, dims in recalled.items()]


def load(rosters):
    from speech_aware_evidence_acquisition.rails.phase_supply import SealedSegmentQuery  # noqa: F401

    STATE["ex_snap"] = rio.load_snapshot(rio.EXEMPLAR_SNAPSHOT)
    STATE["ex_facets"] = rio.load_vectors(rio.EXEMPLAR_FACETS, ["content"])
    STATE["ib_snap"] = rio.load_snapshot(rio.IB_SNAPSHOT)
    STATE["ib_facets"] = {name: rio.load_vectors(rel, ["intent-boundary"]) for name, rel in rio.IB_FACETS.items()}
    STATE["content"] = {}
    STATE["segments"] = {}
    for roster in rosters:
        content_rel, segment_rel = rio.ROSTERS[roster]
        STATE["content"][roster] = rio.load_vectors(content_rel, ["content"])
        STATE["segments"][roster] = rio.load_segments(segment_rel, ["intent-boundary"])


def one(task):
    from speech_aware_evidence_acquisition.rails import kb_policy as kb

    roster, sid = task
    out = []
    timings = []
    query = STATE["content"][roster].get(sid)
    if query is not None:
        facets = STATE["ex_facets"]
        for k in EXEMPLAR_KS:
            t = time.perf_counter()
            recalled = kb.multidim_recall(STATE["ex_snap"], dict(query), lambda fid: facets.get(fid, {}), k)
            timings.append(("train-exemplars", k, time.perf_counter() - t))
            out.append(json.dumps([roster, sid, "train-exemplars", k, canon(recalled)]))
    segs = STATE["segments"][roster].get(sid)
    if segs is not None:
        for name, ks in IB_KS.items():
            facets = STATE["ib_facets"][name]
            for k in ks:
                t = time.perf_counter()
                recalled = kb.multidim_segment_recall(STATE["ib_snap"], segs.segments, lambda fid, f=facets: f.get(fid, {}), k)
                timings.append((f"intent-boundaries/{name}", k, time.perf_counter() - t))
                out.append(json.dumps([roster, sid, f"intent-boundaries/{name}", k, canon(recalled)]))
    return out, timings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--rosters", default="fold-a,dev2000-added,fold-b")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    rio.pkg(args.tree)
    rosters = args.rosters.split(",")
    t0 = time.perf_counter()
    load(rosters)
    print("loaded", round(time.perf_counter() - t0, 1), "s", flush=True)
    tasks = []
    for roster in rosters:
        ids = sorted(set(STATE["content"][roster]) | set(STATE["segments"][roster]))
        if args.limit:
            ids = ids[: args.limit]
        tasks.extend((roster, sid) for sid in ids)
        print(roster, "content rows", len(STATE["content"][roster]), "segment rows", len(STATE["segments"][roster]), "union", len(ids), flush=True)
    timing_sum = {}
    t0 = time.perf_counter()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        if args.workers == 1:
            results = map(one, tasks)
        else:
            import multiprocessing as mp

            pool = mp.get_context("fork").Pool(args.workers)
            results = pool.imap(one, tasks, chunksize=4)
        for index, (lines, timings) in enumerate(results, start=1):
            for line in lines:
                fh.write(line + "\n")
            for store, k, seconds in timings:
                agg = timing_sum.setdefault(f"{store}|k={k}", [0, 0.0, 0.0])
                agg[0] += 1
                agg[1] += seconds
                agg[2] = max(agg[2], seconds)
            if index % 200 == 0:
                print("rows", index, "/", len(tasks), round(time.perf_counter() - t0, 1), "s", flush=True)
    summary = {key: {"calls": n, "mean_s": total / n, "max_s": mx} for key, (n, total, mx) in sorted(timing_sum.items())}
    summary["_wall_s"] = time.perf_counter() - t0
    summary["_workers"] = args.workers
    summary["_rows"] = len(tasks)
    with open(args.out + ".timing.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
