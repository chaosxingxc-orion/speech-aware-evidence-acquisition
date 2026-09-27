"""Usage: PYTHONPATH=<tree>/src python recall_timing.py <tree>/src <out.json> [rows]

Per-row wall time of the Solver's exemplar recall (train-exemplars, k=20, the
PLAN cell's store) on the first N Fold A rows, one process, warm after the first
row -- the call the Solver's role input makes once per row."""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall_io as rio  # noqa: E402

tree, out = sys.argv[1], sys.argv[2]
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 100
rio.pkg(tree)
from speech_aware_evidence_acquisition.rails import kb_policy as kb  # noqa: E402

snap = rio.load_snapshot(rio.EXEMPLAR_SNAPSHOT)
facets = rio.load_vectors(rio.EXEMPLAR_FACETS, ["content"])
queries = rio.load_vectors(rio.ROSTERS["fold-a"][0], ["content"])
ids = sorted(queries)[: rows + 1]
times = []
for sid in ids:
    t = time.perf_counter()
    kb.multidim_recall(snap, dict(queries[sid]), lambda fid: facets.get(fid, {}), 20)
    times.append(time.perf_counter() - t)
first, warm = times[0], sorted(times[1:])
result = {
    "tree": tree, "rows_warm": len(warm), "first_row_s": round(first, 3),
    "warm_median_ms": round(1000 * statistics.median(warm), 2),
    "warm_mean_ms": round(1000 * statistics.mean(warm), 2),
    "warm_p90_ms": round(1000 * warm[int(0.9 * len(warm))], 2),
    "warm_max_ms": round(1000 * warm[-1], 2),
    "loadavg_1m": os.getloadavg()[0],
}
print(json.dumps(result))
with open(out, "w", encoding="utf-8") as fh:
    json.dump(result, fh, indent=1)
