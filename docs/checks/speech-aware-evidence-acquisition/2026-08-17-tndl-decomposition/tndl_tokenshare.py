"""Mention-level vs TOKEN-level error share.

Earnings21's ``wer_tags`` gives one reference token several entity IDs at once: a
spoken year is routinely tagged YEAR *and* CARDINAL *and* DATE, so one wrong token
contributes three wrong MENTIONS, while a company name usually carries a single
ORG id. Any share computed over mentions therefore over-weights numbers by
construction. This recomputes the same split over DISTINCT reference tokens.
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

NUMERIC = {"CARDINAL", "DATE", "YEAR", "PERCENT", "MONEY", "ORDINAL", "TIME",
           "QUANTITY", "ALPHANUMERIC", "RANGE"}
CONVENTION = {"CONTRACTION", "ABBREVIATION"}

rows = [json.loads(l) for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l.strip()]
label = sys.argv[2]

token_types = defaultdict(set)
token_fmt = defaultdict(list)
for r in rows:
    for i in r.get("token_indices", []):
        token_types[(r["sample_id"], i)].add(r["entity_type"])
        token_fmt[(r["sample_id"], i)].append(r["fmt_window"])

mention_groups = Counter()
for r in rows:
    g = ("NUMERIC" if r["entity_type"] in NUMERIC
         else "CONVENTION" if r["entity_type"] in CONVENTION else "NAME")
    mention_groups[g] += 1

token_groups = Counter()
labels_per_token = Counter()
for key, types in token_types.items():
    labels_per_token[len(types)] += 1
    if types & (set(types) - NUMERIC - CONVENTION):
        token_groups["NAME"] += 1
    elif types - NUMERIC:
        token_groups["CONVENTION"] += 1
    else:
        token_groups["NUMERIC"] += 1

tm = sum(mention_groups.values())
tt = sum(token_groups.values())
print(f"=== {label}: mention-level vs token-level wrong-entity mass ===")
print(f"  wrong MENTIONS: {tm}     distinct wrong TOKENS: {tt}"
      f"   (inflation x{tm/tt:.2f})")
print(f"  {'group':12}{'mentions':>10}{'m-share':>10}{'tokens':>10}{'t-share':>10}")
for g in ("NUMERIC", "CONVENTION", "NAME"):
    print(f"  {g:12}{mention_groups[g]:10d}{100*mention_groups[g]/tm:9.2f}%"
          f"{token_groups[g]:10d}{100*token_groups[g]/tt:9.2f}%")
print(f"  {'NUM+CONV':12}{mention_groups['NUMERIC']+mention_groups['CONVENTION']:10d}"
      f"{100*(mention_groups['NUMERIC']+mention_groups['CONVENTION'])/tm:9.2f}%"
      f"{token_groups['NUMERIC']+token_groups['CONVENTION']:10d}"
      f"{100*(token_groups['NUMERIC']+token_groups['CONVENTION'])/tt:9.2f}%")
print("\n  entity labels per wrong token:",
      {k: v for k, v in sorted(labels_per_token.items())})

fmt_tokens = sum(1 for k, v in token_fmt.items() if any(v))
print(f"\n  distinct wrong tokens whose mentions include a FORMAT match: "
      f"{fmt_tokens}/{tt} = {100*fmt_tokens/tt:.2f}%")
