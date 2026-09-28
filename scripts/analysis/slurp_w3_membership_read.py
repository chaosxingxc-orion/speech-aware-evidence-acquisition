#!/usr/bin/env python3
"""Cell W3a: recompute the row-attribution membership its recipe fixed before contact.

The W3 analysis recipe (``docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/analysis-recipe-v1.json``,
``membership_sets``) fixes the attribution groups by the offline read's Fold A counts
(``offline-estimates-v1.json``, ``fold_a_estimates.contrast_cards``) and requires the per-row membership
to be recomputed at read time by the same functions from the same pinned inputs, reproducing those counts
exactly. This script imports ``scripts/analysis/slurp_w3_contrast_cap_offline.py`` by path (unmodified)
and uses its own loaders: the pinned TRAIN gold (intent label only, offline), the sealed AGREE arm's chosen
intents and delivered boundary sets, the authored confusable exclusions and the released contrast source.

Groups (the AGREE arm's intent-wrong rows):
  ``newly_named`` -- a DELIVERED card names the chosen-vs-gold pair after the contrast lines, not before;
  ``named_before`` -- a delivered card already named the pair before;
  ``wrong_unnamed_after`` -- the rest of the wrong rows;
and ``agree_right`` -- the AGREE arm's intent-right rows.

It REFUSES unless ``wrong``, ``named before`` and ``named after`` reproduce the registered counts. It
writes ``<out>`` (a JSON object: group -> sorted sample ids, plus the reproduced counts). MODEL-FREE: zero
model, tokenizer, encoder, scorer, server and network contacts. Sample ids and counts only; no gold label,
intent name, utterance text or model output is printed or persisted.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"REFUSED: {a.out} exists")
    spec = importlib.util.spec_from_file_location("w3off", REPO / "scripts/analysis/slurp_w3_contrast_cap_offline.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    root = a.data_root
    registered = json.loads((PKG / "offline-estimates-v1.json").read_text(encoding="utf-8"))["fold_a_estimates"]["contrast_cards"]
    roster = json.loads((REPO / m.ROSTERS["fold_a"]).read_text(encoding="utf-8"))
    ids = sorted(str(i["sample_id"]) for i in roster["items"])
    gold = m.load_gold(root)
    agree = m.load_agree(root)
    contrast = json.loads((root / m.CONTRAST_SOURCE).read_text(encoding="utf-8"))
    carried = {intent: set(card["rivals_carried"]) for intent, card in contrast["cards"].items()}
    authored = m.authored_exclusions(root)
    after_names = {i: authored.get(i, set()) | carried.get(i, set()) for i in set(authored) | set(carried)}

    def gold_of(s: str) -> str:
        return gold[m.utterance(s)]

    def named(names, s):
        g, c = gold_of(s), agree["chosen"][s]
        delivered = set(agree["consumption"][s]["boundary"])
        return (c in names.get(g, set()) and g in delivered) or (g in names.get(c, set()) and c in delivered)

    wrong = [s for s in ids if agree["chosen"][s] != gold_of(s)]
    right = [s for s in ids if agree["chosen"][s] == gold_of(s)]
    before = [s for s in wrong if named(authored, s)]
    after = [s for s in wrong if named(after_names, s)]
    reproduced = {"wrong_rows": len(wrong), "pair_named_on_a_delivered_card_before": len(before),
                  "pair_named_on_a_delivered_card_after": len(after)}
    for k, v in reproduced.items():
        if registered[k] != v:
            raise SystemExit(f"REFUSED: {k} reproduces {v}, registered {registered[k]}")
    before_set, after_set = set(before), set(after)
    groups = {
        "newly_named": sorted(after_set - before_set),
        "named_before": sorted(before_set),
        "wrong_unnamed_after": sorted(set(wrong) - after_set - before_set),
        "agree_right": sorted(right),
    }
    doc = {"schema": "saea-slurp-w3-membership-v1", "reproduced_counts": reproduced,
           "group_sizes": {k: len(v) for k, v in groups.items()}, "groups": groups}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"written": str(a.out), "reproduced_counts": reproduced, "group_sizes": doc["group_sizes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
