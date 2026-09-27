"""Compare the old-tree and new-tree recall dumps record by record."""
import collections
import hashlib
import json
import sys

old_path, new_path, out_path = sys.argv[1:4]
counts = collections.Counter()
rows = collections.defaultdict(set)
mismatches = []
h_old, h_new = hashlib.sha256(), hashlib.sha256()
with open(old_path, encoding="utf-8") as fo, open(new_path, encoding="utf-8") as fn:
    for number, (lo, ln) in enumerate(zip(fo, fn), start=1):
        h_old.update(lo.encode())
        h_new.update(ln.encode())
        ro, rn = json.loads(lo), json.loads(ln)
        key = (ro[0], ro[2], ro[3])
        counts[key] += 1
        rows[ro[0]].add(ro[1])
        if lo != ln:
            mismatches.append({"line": number, "roster": ro[0], "row": ro[1], "store": ro[2], "k": ro[3],
                               "old_ids": [e[0] for e in ro[4]], "new_ids": [e[0] for e in rn[4]]})
    extra_old, extra_new = fo.readline(), fn.readline()
summary = {
    "old_dump_sha256": h_old.hexdigest(),
    "new_dump_sha256": h_new.hexdigest(),
    "records_compared": sum(counts.values()),
    "length_mismatch": bool(extra_old or extra_new),
    "rows_per_roster": {r: len(s) for r, s in sorted(rows.items())},
    "records_per_roster_store_k": {f"{r}|{s}|k={k}": n for (r, s, k), n in sorted(counts.items())},
    "mismatching_records": len(mismatches),
    "mismatches_first_20": mismatches[:20],
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "records_per_roster_store_k"}, indent=1))
