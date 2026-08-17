"""Are residual numeric 'errors' partly Earnings21 wer_tags annotation artifacts?"""
import json, sys
from collections import Counter
from pathlib import Path
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.references import reference_tokens, reference_entity_mentions

S = Path(sys.argv[1])
rows = [json.loads(l) for l in (S / "wrong_mentions_r1verify.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
root, lock = data_root(), load_lock(umbrella_lock_path())

# find the '199' / '201' / 'December 31 of 202' cases and show the raw context
targets = [r for r in rows if r["ref_text"] in ("199", "201", "December 31 of 202")]
print("target mentions:", len(targets))
cache = {}
for r in targets[:6]:
    sid = r["sample_id"]
    if sid not in cache:
        cache[sid] = (reference_tokens(lock, root, "earnings21-original", sid),
                      reference_entity_mentions(lock, root, "earnings21-original", sid))
    toks, ments = cache[sid]
    m = next(m for m in ments if m.entity_id == r["entity_id"])
    lo, hi = min(m.token_indices), max(m.token_indices)
    print(f"\n{sid} entity {m.entity_id} {m.entity_type} indices={m.token_indices}")
    print("  gold tokens in context:", toks[max(0,lo-6):hi+7])
    print("  mention tokens        :", list(m.tokens))

# how many numeric-class wrong mentions have a gold text with NO digit and NO number word?
NUMERIC = {"CARDINAL","DATE","YEAR","PERCENT","MONEY","ORDINAL","TIME","QUANTITY","ALPHANUMERIC","RANGE"}
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tndl_lib import NUMWORDS, WORD_ORDINALS
nodigit = Counter(); noncontig = Counter(); total = Counter()
for r in rows:
    if r["entity_type"] not in NUMERIC:
        continue
    total[r["entity_type"]] += 1
    words = r["ref_text"].casefold().replace("-", " ").split()
    if not any(any(c.isdigit() for c in w) for w in words) and \
       not any(w in NUMWORDS or w in WORD_ORDINALS for w in words):
        nodigit[r["entity_type"]] += 1
print("\n=== numeric-class wrong mentions whose gold text carries NO number at all ===")
tn = sum(nodigit.values()); tt = sum(total.values())
for t, c in nodigit.most_common():
    print(f"  {t:14} {c:4d} / {total[t]:4d}")
print(f"  TOTAL {tn}/{tt} = {100.0*tn/tt:.1f}% of numeric wrong mass")
ex = [r["ref_text"] for r in rows if r["entity_type"] in NUMERIC and
      not any(c.isdigit() for c in r["ref_text"]) and
      not any(w in NUMWORDS or w in WORD_ORDINALS for w in r["ref_text"].casefold().replace("-"," ").split())]
print("  examples:", Counter(ex).most_common(20))
