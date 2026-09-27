"""Usage: PYTHONPATH=<tree>/src WT=<tree> python flip_census.py <out.json>

Near-tie census on the real rosters (new tree): where a BLAS-only ranking
would have delivered a different ordered top-k than the exact loop, and how
many extra rows the pre-selection re-scored to rule that out."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import recall_io as rio  # noqa: E402


def main():
    rio.pkg(os.environ["WT"])
    from speech_aware_evidence_acquisition.rails import kb_policy as kb

    ex_snap = rio.load_snapshot(rio.EXEMPLAR_SNAPSHOT)
    ex_facets = rio.load_vectors(rio.EXEMPLAR_FACETS, ["content"])
    ib_snap = rio.load_snapshot(rio.IB_SNAPSHOT)
    stores = {
        "train-exemplars": (ex_snap, ex_facets, "content", (8, 20, 60)),
    }
    for name, rel in rio.IB_FACETS.items():
        stores[f"intent-boundaries/{name}"] = (ib_snap, rio.load_vectors(rel, ["intent-boundary"]), "intent-boundary", (8, 16, 60))
    report = {}
    for roster, (content_rel, segment_rel) in rio.ROSTERS.items():
        content = rio.load_vectors(content_rel, ["content"])
        segments = rio.load_segments(segment_rel, ["intent-boundary"])
        for store, (snap, facets, dim, ks) in stores.items():
            ids = sorted(f.facet_id for f in snap.facets if f.dimension == dim and facets.get(f.facet_id, {}).get(dim) is not None)
            vectors = tuple(facets[fid][dim] for fid in ids)
            entry = kb._KEY_MATRICES.get_or_build(vectors)
            assert entry.matrix is not None, store
            if dim == "content":
                queries = [(sid, q["content"]) for sid, q in sorted(content.items())]
            else:
                queries = [(f"{sid}#{i}", seg["intent-boundary"]) for sid, rec in sorted(segments.items()) for i, seg in enumerate(rec.segments)]
            for k in ks:
                stats = {"queries": 0, "blas_order_differs": 0, "blas_membership_differs": 0, "extra_rows_rescored_total": 0,
                         "extra_rows_rescored_max": 0, "min_gap_kth_to_next_exact": None, "blas_vs_exact_max_abs_diff": 0.0}
                for _sid, q in queries:
                    qn = kb._l2_norm(q)
                    approx = (entry.matrix @ np.array(q)) / (entry.norms * qn)
                    exact = kb._preselected_exact_scores(q, qn, ids, vectors, k)
                    rescored = len(exact)
                    exact.sort(key=lambda item: (-item[0], item[1]))
                    delivered = [fid for _s, fid in exact[:k]]
                    order = np.lexsort((np.array(ids), -approx))
                    naive = [ids[i] for i in order if approx[i] > 0][:k]
                    stats["queries"] += 1
                    stats["blas_order_differs"] += naive != delivered
                    stats["blas_membership_differs"] += set(naive) != set(delivered)
                    extra = max(0, rescored - k)
                    stats["extra_rows_rescored_total"] += extra
                    stats["extra_rows_rescored_max"] = max(stats["extra_rows_rescored_max"], extra)
                    if len(exact) > k:
                        gap = exact[k - 1][0] - exact[k][0]
                        cur = stats["min_gap_kth_to_next_exact"]
                        stats["min_gap_kth_to_next_exact"] = gap if cur is None else min(cur, gap)
                    index = {fid: i for i, fid in enumerate(ids)}
                    for s, fid in exact:
                        stats["blas_vs_exact_max_abs_diff"] = max(stats["blas_vs_exact_max_abs_diff"], abs(float(approx[index[fid]]) - s))
                report[f"{roster}|{store}|k={k}"] = stats
                print(roster, store, k, json.dumps(stats), flush=True)
    with open(sys.argv[1] if len(sys.argv) > 1 else "flip-census.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)


if __name__ == "__main__":
    t = time.perf_counter()
    main()
    print("seconds", round(time.perf_counter() - t, 1))
