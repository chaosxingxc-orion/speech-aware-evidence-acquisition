"""N1 re-run stage 1: the surviving TRUE-WRONG inventory.

OFFLINE, MODEL-FREE (owner ruling D5 archival replay).

The N1 routing measurement was computed over all 2,873 wrong entity mentions.
T-NDL (2026-08-17-tndl-decomposition) showed 1,921 of those are FORMAT: the
frozen core already emitted the right value, in words, where the reference stores
digits. Routing cannot "fix" what was never wrong, so every N1 denominator that
includes FORMAT mass is inflated. This rebuilds the denominator as the mentions
that survive the FORMAT filter.

Persists the DERIVATION -- structural fields only (ids, entity class, reference
token indices, coverage verdicts). No gold mention text and no hypothesis text
are written, exactly as in the T-NDL bundle.

The FORMAT verdict and the ConEC coverage verdict are not recomputed here from a
private copy of the logic: this script imports the COMMITTED T-NDL bundle, so the
two analyses cannot drift.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

TNDL = Path(os.environ["TNDL"])
sys.path.insert(0, str(TNDL))

from tndl_decompose import (  # noqa: E402
    CONVENTION, NAME, NUMERIC, decoy_keys, despace, hits, load_conec, search_keys,
)


def group_of(entity_type):
    if entity_type in NUMERIC:
        return "NUMERIC"
    if entity_type in CONVENTION:
        return "CONVENTION"
    if entity_type in NAME:
        return "NAME"
    raise KeyError(entity_type)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wrong", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--arm", required=True)
    args = parser.parse_args()

    root = os.environ["SPEECHRL_DATA_DIR"]
    rows = [json.loads(line) for line in
            args.wrong.read_text(encoding="utf-8").splitlines() if line.strip()]
    calls = sorted({r["sample_id"] for r in rows})

    conec = {}
    for call in calls:
        layers, _meta = load_conec(root, call)
        conec[call] = {k: despace(v) for k, v in layers.items()}
        conec[call]["any"] = "".join(conec[call].values())

    rng = random.Random(20260817)
    out_rows = []
    tally = Counter()
    for row in rows:
        tally["wrong"] += 1
        group = group_of(row["entity_type"])
        tally[f"wrong_{group}"] += 1
        if row["fmt_window"]:
            tally["format"] += 1
            tally[f"format_{group}"] += 1
            continue

        keys = search_keys(row["ref_text"])
        decoys = decoy_keys(keys, rng)
        layer_hit = {name: hits(keys, text) for name, text in conec[row["sample_id"]].items()}
        covered = layer_hit["any"]
        key_len = max((len(k) for k in keys), default=0)
        bucket = "len1_2" if key_len <= 2 else "len3_4" if key_len <= 4 else "len5plus"

        tally["truewrong"] += 1
        tally[f"truewrong_{group}"] += 1
        if bucket == "len5plus":
            tally[f"truewrong_{group}_len5plus"] += 1
        if covered:
            tally["prepublished"] += 1
            tally[f"prepublished_{group}"] += 1
        else:
            tally["novel"] += 1
            tally[f"novel_{group}"] += 1

        out_rows.append({
            "sample_id": row["sample_id"],
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "group": group,
            "token_indices": row["token_indices"],
            "key_len": key_len,
            "key_len_bucket": bucket,
            "prepublished": covered,
            "pdf_hit": layer_hit["pdf"],
            "biasing_hit": layer_hit["biasing_txt"],
            "names_hit": layer_hit["names"],
            "decoy_hit": hits(decoys, conec[row["sample_id"]]["any"]),
        })

    args.out.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in out_rows) + "\n",
        encoding="utf-8")

    print(f"=== {args.arm}: true-wrong inventory ===")
    print(f"  wrong mentions      {tally['wrong']:5d}")
    print(f"  FORMAT (removed)    {tally['format']:5d}")
    print(f"  TRUE-WRONG          {tally['truewrong']:5d}   <- the new N1 denominator")
    print(f"  {'group':12}{'wrong':>8}{'format':>8}{'truewrong':>11}{'len5plus':>10}"
          f"{'prepub':>8}{'novel':>8}")
    for group in ("NUMERIC", "CONVENTION", "NAME"):
        print(f"  {group:12}{tally['wrong_' + group]:8d}{tally['format_' + group]:8d}"
              f"{tally['truewrong_' + group]:11d}"
              f"{tally['truewrong_' + group + '_len5plus']:10d}"
              f"{tally['prepublished_' + group]:8d}{tally['novel_' + group]:8d}")
    print(f"\n  wrote {args.out} ({len(out_rows)} rows)")
    assert tally["format"] + tally["truewrong"] == tally["wrong"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
