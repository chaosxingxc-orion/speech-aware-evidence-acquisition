"""N1 re-run stage 2: reference-token -> absolute audio time.

A flagged re-listen window is an interval of call audio. A gold entity mention is
a set of reference-token positions. To ask "did any flagged window reach this
mention?" the two must live in the same coordinate system.

The scored reference (`earnings21-original`, the file `data.references` reads and
the file T-NDL's token indices index) declares `ts`/`endTs` columns but leaves
them EMPTY -- 0 of 6,602 rows populated on 4330115, and the same on all ten
calls. ConEC ships a separately-corrected copy of the same transcripts WITH
word-level timestamps, but it is not index-aligned: 6,612 rows against 6,602 for
the same call. Copying its timestamps by position would silently shift the map by
however many tokens ConEC inserted earlier in the file.

So the two token sequences are ALIGNED (same frozen-mirror Levenshtein used
throughout T-NDL) and timestamps are transferred across matched pairs; scored
tokens with no matched ConEC partner, and ConEC tokens whose own ts cell is empty,
are filled by interpolating between the nearest timed neighbours. Every call
reports its own transfer rate so the mapping's quality is visible rather than
assumed.

OFFLINE, MODEL-FREE. Writes a cache only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

TNDL = Path(os.environ["TNDL"])
sys.path.insert(0, str(TNDL))
from tndl_lib import align_trace  # noqa: E402

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root, load_lock, umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.references import (  # noqa: E402
    reference_file_relpath, reference_tokens,
)
from speech_aware_evidence_acquisition.scoring.normalize import normalize_text_v1  # noqa: E402

CARRIER = "earnings21-original"


def conec_rows(path):
    """(token, ts, endTs) per row of a ConEC timestamps .nlp."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header = lines[0].split("|")
    ti, si, ei = header.index("token"), header.index("ts"), header.index("endTs")
    out = []
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) <= max(ti, si, ei):
            continue

        def num(cell):
            cell = cell.strip()
            try:
                return float(cell)
            except ValueError:
                return None

        out.append((cells[ti], num(cells[si]), num(cells[ei])))
    return out


def interpolate(times, total_seconds):
    """Fill None gaps by walking outward from the nearest timed neighbours."""
    n = len(times)
    filled = list(times)
    known = [i for i, t in enumerate(filled) if t is not None]
    if not known:
        step = total_seconds / max(1, n)
        return [(i * step, (i + 1) * step) for i in range(n)]
    first, last = known[0], known[-1]
    for i in range(first):
        filled[i] = (0.0, filled[first][0])
    for i in range(last + 1, n):
        filled[i] = (filled[last][1], total_seconds)
    prev = first
    for idx in known[1:]:
        gap = idx - prev
        if gap > 1:
            lo, hi = filled[prev][1], filled[idx][0]
            step = (hi - lo) / gap
            for k in range(1, gap):
                filled[prev + k] = (lo + (k - 1) * step, lo + k * step)
        prev = idx
    return filled


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", nargs="+", required=True)
    parser.add_argument("--durations", required=True, type=Path,
                        help="JSON {call: decoded_duration_seconds} from a replay-derivation set")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    root = data_root()
    lock = load_lock(umbrella_lock_path())
    durations = json.loads(args.durations.read_text(encoding="utf-8"))
    conec_dir = Path(os.environ["SPEECHRL_DATA_DIR"]) / "datasets/conec/earnings21/transcripts/timestamps"

    cache = {}
    print(f"{'call':10}{'scored':>8}{'conec':>8}{'matched':>9}{'timed':>8}{'rate':>8}{'span_s':>10}")
    for call in args.calls:
        scored = reference_tokens(lock, root, CARRIER, call)
        rows = conec_rows(conec_dir / f"{call}.nlp")
        a = [normalize_text_v1(t) for t in scored]
        b = [normalize_text_v1(t) for t, _s, _e in rows]
        ref_to_hyp, _ops, _ha, mask = align_trace(a, b)

        times = [None] * len(scored)
        matched = 0
        for i, j in enumerate(ref_to_hyp):
            if j is None:
                continue
            matched += 1
            _tok, s, e = rows[j]
            if s is not None and e is not None:
                times[i] = (s, e)
            elif s is not None:
                times[i] = (s, s)
        timed = sum(1 for t in times if t is not None)
        total = float(durations[call])
        cache[call] = interpolate(times, total)
        print(f"{call:10}{len(scored):8d}{len(rows):8d}{matched:9d}{timed:8d}"
              f"{100.0*timed/len(scored):7.1f}%{total:10.1f}")

    args.out.write_text(json.dumps(cache), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
