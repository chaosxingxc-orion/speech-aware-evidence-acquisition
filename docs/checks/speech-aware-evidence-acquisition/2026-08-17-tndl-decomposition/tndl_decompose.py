"""T-NDL stages 2+3: FORMAT / PRE-PUBLISHED / NOVEL decomposition.

Consumes the stage-1 wrong-mention inventory and emits the three-way ledger.
OFFLINE, MODEL-FREE (owner ruling D5 archival replay).

FORMAT     -- hypothesis and reference differ only by writing convention.
PRE-PUBLISHED -- a surviving true error whose correct value is present in the
              call's own ConEC accompanying materials (legally suppliable).
NOVEL      -- the residual: no legal knowledge base can reach it.

Chance control: ConEC coverage of a SHORT numeric string is close to meaningless
("3" occurs in every financial deck), so every coverage figure is reported beside
a matched-shape decoy rate -- the same search keys with their characters
randomised. Coverage that does not clear its decoy rate is not evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tndl_lib import MARKERS, canonical_variants  # noqa: E402
from pdf_cmap import pdf_text  # noqa: E402

NUMERIC = {"CARDINAL", "DATE", "YEAR", "PERCENT", "MONEY", "ORDINAL", "TIME",
           "QUANTITY", "ALPHANUMERIC", "RANGE"}
CONVENTION = {"CONTRACTION", "ABBREVIATION"}
NAME = {"ORG", "PERSON", "GPE", "LOC", "NORP", "EVENT", "PRODUCT", "FAC",
        "WORK_OF_ART", "WEBSITE", "TWITTER"}


# --------------------------------------------------------------------------
# ConEC accompanying materials
# --------------------------------------------------------------------------

def despace(text):
    """Lowercase, keep alphanumerics and decimal points, drop everything else.

    PDF text extraction fragments words across kerning operators ("Thir d
    Quart er"), so all whitespace is removed before substring search rather than
    tokenising.
    """
    text = text.casefold()
    kept = [c for c in text if c.isalnum() or c == "."]
    return "".join(kept)


def load_conec(root, call_id):
    base = Path(root) / "datasets" / "conec" / "earnings21" / "contexts"
    layers = {}
    txt = base / f"{call_id}.txt"
    layers["biasing_txt"] = txt.read_text(encoding="utf-8", errors="replace") if txt.exists() else ""
    names = base / "participant_names" / f"{call_id}.names.txt"
    layers["names"] = names.read_text(encoding="utf-8", errors="replace") if names.exists() else ""
    pdfs = sorted((base / "pdfs").glob(f"{call_id}_*.pdf"))
    texts, meta = [], []
    for path in pdfs:
        text, info = pdf_text(path)
        texts.append(text)
        meta.append(dict(info, name=path.name, chars=len(text)))
    layers["pdf"] = "\n".join(texts)
    return layers, meta


# --------------------------------------------------------------------------
# Search keys
# --------------------------------------------------------------------------

def search_keys(ref_text):
    """Despaced strings that would evidence this gold value in a document."""
    keys = set()
    raw = despace(ref_text)
    if raw:
        keys.add(raw)
    for variant in canonical_variants(ref_text):
        tokens = [t for t in variant if t not in MARKERS and not t.startswith("#")]
        joined = despace("".join(tokens))
        if joined:
            keys.add(joined)
    return {k for k in keys if k}


def decoy_keys(keys, rng):
    """Matched-shape null: same lengths and digit/letter pattern, random content."""
    out = set()
    for key in keys:
        out.add("".join(
            rng.choice("0123456789") if c.isdigit()
            else (rng.choice("abcdefghijklmnopqrstuvwxyz") if c.isalpha() else c)
            for c in key))
    return out


def hits(keys, haystack):
    return any(k in haystack for k in keys)


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
    pdf_names = {}
    for call in calls:
        layers, names = load_conec(root, call)
        conec[call] = {k: despace(v) for k, v in layers.items()}
        conec[call]["any"] = "".join(conec[call].values())
        pdf_names[call] = names
        print(f"  ConEC {call}: biasing={len(conec[call]['biasing_txt']):7d} "
              f"names={len(conec[call]['names']):5d} pdf={len(conec[call]['pdf']):8d} "
              f"chars  pdfs={[(m['name'], m['chars']) for m in names]}")

    rng = random.Random(20260817)
    per_class = defaultdict(Counter)
    per_call = defaultdict(Counter)
    examples = {"format_caught": [], "format_missed": [], "prepublished": [], "novel": []}

    for row in rows:
        entity_type = row["entity_type"]
        call = row["sample_id"]
        group = ("NUMERIC" if entity_type in NUMERIC
                 else "CONVENTION" if entity_type in CONVENTION else "NAME")
        counters = (per_class[entity_type], per_call[call], per_class["__" + group],
                    per_class["__ALL"])
        for counter in counters:
            counter["wrong"] += 1

        if row["fmt_window"]:
            for counter in counters:
                counter["format"] += 1
            if group == "NUMERIC" and len(examples["format_caught"]) < 40:
                examples["format_caught"].append(row)
            continue

        keys = search_keys(row["ref_text"])
        decoys = decoy_keys(keys, rng)
        layer_hit = {name: hits(keys, text) for name, text in conec[call].items()}
        decoy_hit = {name: hits(decoys, text) for name, text in conec[call].items()}
        covered = layer_hit["any"]

        for counter in counters:
            counter["surviving"] += 1
            counter["prepublished"] += int(covered)
            counter["prepublished_decoy"] += int(decoy_hit["any"])
            counter["pdf_hit"] += int(layer_hit["pdf"])
            counter["biasing_hit"] += int(layer_hit["biasing_txt"])
            counter["names_hit"] += int(layer_hit["names"])
            if not covered:
                counter["novel"] += 1
        longest = max((len(k) for k in keys), default=0)
        bucket = "len1_2" if longest <= 2 else "len3_4" if longest <= 4 else "len5plus"
        for counter in counters:
            counter[f"surviving_{bucket}"] += 1
            if covered:
                counter[f"prepublished_{bucket}"] += 1
            if decoy_hit["any"]:
                counter[f"decoy_{bucket}"] += 1

        record = dict(row, keys=sorted(keys), layer_hit=layer_hit,
                      decoy_hit=decoy_hit["any"], key_len=longest)
        if group == "NUMERIC":
            if covered and len(examples["prepublished"]) < 30:
                examples["prepublished"].append(record)
            if not covered and len(examples["novel"]) < 30:
                examples["novel"].append(record)
            if len(examples["format_missed"]) < 40:
                examples["format_missed"].append(record)

    report = {
        "arm": args.arm,
        "schema": "saea-tndl-decomposition-v1",
        "groups": {"NUMERIC": sorted(NUMERIC), "CONVENTION": sorted(CONVENTION),
                   "NAME": sorted(NAME)},
        "per_class": {k: dict(v) for k, v in sorted(per_class.items())},
        "per_call": {k: dict(v) for k, v in sorted(per_call.items())},
        "conec_pdfs": pdf_names,
        "examples": examples,
    }
    args.out.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")

    total = per_class["__ALL"]
    print(f"\n=== {args.arm}: three-way decomposition over ALL wrong mentions ===")
    print(f"  wrong        {total['wrong']:5d}")
    print(f"  FORMAT       {total['format']:5d}  {100*total['format']/total['wrong']:6.2f}%")
    print(f"  PRE-PUBLISHED{total['prepublished']:5d}  "
          f"{100*total['prepublished']/total['wrong']:6.2f}%  "
          f"(decoy {100*total['prepublished_decoy']/total['wrong']:5.2f}%)")
    print(f"  NOVEL        {total['novel']:5d}  {100*total['novel']/total['wrong']:6.2f}%")
    for group in ("NUMERIC", "CONVENTION", "NAME"):
        g = per_class["__" + group]
        print(f"\n  [{group}] wrong={g['wrong']}  FORMAT={g['format']} "
              f"({100*g['format']/g['wrong']:.2f}%)  PRE-PUB={g['prepublished']} "
              f"({100*g['prepublished']/g['wrong']:.2f}%, decoy "
              f"{100*g['prepublished_decoy']/g['wrong']:.2f}%)  NOVEL={g['novel']} "
              f"({100*g['novel']/g['wrong']:.2f}%)")
        for bucket in ("len1_2", "len3_4", "len5plus"):
            s = g[f"surviving_{bucket}"]
            if s:
                print(f"      key {bucket:9} surviving={s:4d} prepub="
                      f"{g['prepublished_' + bucket]:4d} "
                      f"({100*g['prepublished_' + bucket]/s:5.1f}%)  decoy="
                      f"{g['decoy_' + bucket]:4d} ({100*g['decoy_' + bucket]/s:5.1f}%)")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
