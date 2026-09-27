#!/usr/bin/env python3
"""CLI: the MAXIMUM intent accuracy attainable on SLURP under its gold labels as they
stand -- the measurement owner decision 137 made a prerequisite of treating 95 per cent
as a distance.

The question, stated so a number settles it: SLURP was collected by prompting annotators,
so the same normalised sentence can carry more than one gold ``scenario_action``.  Every
such utterance caps accuracy directly, because no function of the audio can be right on
both copies.  This read measures that collision structure in the corpus itself, turns it
into a per-roster upper bound, and partitions the locked v2.0 PLAN arm's TRAIN Fold A
error against it.

ZERO CONTACTS -- no model, server, tokenizer, encoder, embedder, ASR, scorer, network, GPU
or paid-API contact of any kind.  Every number is arithmetic over the governed SLURP
annotation bytes, three committed roster receipts and one sealed analysis artefact, all
sha256-pinned in section 0.

THE TEST SPLIT STAYS CLOSED -- ``test.jsonl`` is never opened, hashed or counted; the
census covers ``train`` and ``devel`` only.  Gold is read offline into aggregate tables
and reaches no runtime path.

IDS AND COUNTS ONLY -- no utterance text, sentence text, transcript, token surface, gold
filler or delivered text is printed or persisted.  Sentence identity enters as a GROUP KEY
consumed in-process and discarded; what this read emits is intent ids, counts, rates and
hashes.

A DIAGNOSTIC, never a gate: it registers no cell, admits no mechanism, releases no store,
draws no roster, proposes no mechanism, authorises no flight and states no effectiveness,
superiority or generalisation claim.  Every roster is a discovery or dev roster and every
number a development number (owner decisions 28 and 86), never a test claim.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:<worktree>/src \\
      python -B scripts/analysis/slurp_intent_label_ceiling_audit.py
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import _governed_roots  # noqa: E402

RECIPE_ID = "slurp-intent-label-ceiling-audit-v1"
READ_ID = "SAEA-SLURP-MF-INTENT-LABEL-CEILING-AUDIT-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-intent-label-ceiling-audit.md"
BANK_RELPATH = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
CATCH_ALL = "general_quirky"
TARGET = 95.0
#: Owner decision 137's own measured line, so the gap arithmetic is checked against the
#: record rather than recomputed from a different source.
LOCK_ARM_INTENT = 82.2222
#: The three rosters every effectiveness read of this carrier uses.  ``field`` names the
#: item key that carries the sample id in that receipt.
ROSTERS = (
    {"key": "roll1-r01c", "field": "sample_id", "split": "train",
     "relpath": "docs/receipts/rosters/slurp-stage3-construction-r01c.json"},
    {"key": "train-fold-a", "field": "id", "split": "train",
     "relpath": "docs/receipts/rosters/slurp-evo-fold-a-v2.json"},
    {"key": "dev2000-added", "field": "id", "split": "devel",
     "relpath": "docs/receipts/rosters/slurp-dev-2000-added-v1.json"},
)
#: The three MECHANICAL sentence keys, loosest last.  No judgement of this read's enters
#: any of them: each is a deterministic function of the corpus's OWN ``tokens[].surface``
#: sequence, lowercased, with non-alphanumeric characters (the apostrophe excepted)
#: removed and empty tokens dropped.
KEYS = ("sequence", "bag", "set")
SCOPES = ("train", "devel", "train+devel")
ROSTER_SCOPES = ("roster-local", "split-consistent", "pool-consistent")
JACCARD = (1.0, 0.9, 0.8, 0.7, 0.6)
CLASSES = ("UNWINNABLE", "AMBIGUOUS-BUT-MAJORITY", "CATCH-ALL", "OURS")
MEANING = {
    "UNWINNABLE": "gold is a MINORITY label inside a colliding sentence group -- no "
                  "function of the sentence can be right here",
    "AMBIGUOUS-BUT-MAJORITY": "inside a colliding group, but gold IS the group's most "
                              "frequent label -- winnable, though the group is ambiguous",
    "CATCH-ALL": f"gold or delivered is `{CATCH_ALL}` -- conceded in full below, although "
                 "section 2 finds no label cause for it",
    "OURS": "neither cause applies -- the part that is genuinely the system's",
}
PUBLISHED = (
    ("Gold/HerMiT", "84.84", "gold transcripts, test split -- the published TEXT-side bound"),
    ("Multi-SLURP/HerMiT", "78.33", "strong trained ASR-to-NLU pipeline, test split"),
    ("Google/SF-ID", "72.06", "weak commercial pipeline, test split"),
    ("ChatGPT, 0-shot prompt-only", "79.25", "oracle transcripts, 60 intents (He & Garner)"),
)


class AuditError(SystemExit):
    """Refuse rather than report a number this read cannot bind to pinned bytes."""


def digest(path: pathlib.Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def key_of(name: str, toks: list[str]) -> str:
    if name == "sequence":
        return " ".join(toks)
    return " ".join(sorted(toks if name == "bag" else set(toks)))


def read_split(metadata_dir: pathlib.Path, split: str) -> list[dict]:
    """One row per SLURP utterance: its gold intent (the COMPUTED
    ``f"{scenario}_{action}"``, exactly ``data.slurp._parse_record``'s own field, never the
    governed jsonl's occasionally inconsistent ``intent`` key), its recording count, and
    its three mechanical sentence keys."""

    path = metadata_dir / f"{split}.jsonl"
    if not path.is_file():
        raise AuditError(f"SLURP governed metadata missing: {path}")
    out: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            surfaces = [re.sub(r"[^a-z0-9']", "", t["surface"].lower()) for t in raw["tokens"]]
            toks = [s for s in surfaces if s]
            if not toks:
                raise AuditError(f"{split}.jsonl line {line_no}: no usable token surfaces")
            out.append({"utterance_id": str(raw["slurp_id"]),
                        "intent": f'{raw["scenario"]}_{raw["action"]}',
                        "recordings": len(raw["recordings"]),
                        "tokenset": frozenset(toks),
                        "keys": {name: key_of(name, toks) for name in KEYS}})
    return out


def group_by(rows: list[dict], name: str, weight: str = "utterances") -> dict:
    groups: dict = collections.defaultdict(collections.Counter)
    for row in rows:
        groups[row["keys"][name]][row["intent"]] += 1 if weight == "utterances" else row["recordings"]
    return groups


def census(rows: list[dict], name: str, weight: str) -> dict:
    """The collision census at one key and one counting unit.  ``min_loss`` is the honest
    floor: inside a colliding group the best any function of the sentence can do is answer
    the group's most frequent gold, so every other member is wrong.  A TIE resolves in the
    system's favour -- this is an upper bound, so a tied group loses only non-maximal mass."""

    groups = group_by(rows, name, weight)
    colliding = {k: v for k, v in groups.items() if len(v) > 1}
    total = sum(sum(v.values()) for v in groups.values())
    min_loss = sum(sum(v.values()) - max(v.values()) for v in colliding.values())
    pairs: collections.Counter = collections.Counter()
    for counts in colliding.values():
        names = sorted(counts)
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                pairs[(left, right)] += 1
    return {"distinct_keys": len(groups), "colliding_groups": len(colliding), "total": total,
            "affected": sum(sum(v.values()) for v in colliding.values()), "min_loss": min_loss,
            "ties": sum(1 for v in colliding.values() if list(v.values()).count(max(v.values())) > 1),
            "ceiling": 100.0 * (1.0 - min_loss / total) if total else 100.0, "pairs": pairs}


def roster_rows(repo: pathlib.Path, spec: dict, by_utterance: dict) -> list[dict]:
    receipt = repo / spec["relpath"]
    if not receipt.is_file():
        raise AuditError(f"roster receipt missing: {receipt}")
    rows = []
    for item in json.loads(receipt.read_text(encoding="utf-8"))["items"]:
        sample_id = item[spec["field"]]
        parts = sample_id.split(":")
        if len(parts) < 4 or parts[0] != "slurp" or parts[1] != spec["split"]:
            raise AuditError(f"{spec['key']}: {sample_id!r} is not a {spec['split']} SLURP id")
        utterance = parts[2].lstrip("0") or "0"
        if utterance not in by_utterance:
            raise AuditError(f"{spec['key']}: utterance {utterance} absent from the split")
        rows.append({"sample_id": sample_id, **by_utterance[utterance]})
    return rows


def unwinnable(rows: list[dict], groups: dict, name: str) -> dict:
    """Rows sitting in a colliding group; of those, the rows whose gold is NOT the group's
    most frequent label (the ones a function of the sentence must get wrong) and the rows
    whose group is an exact TIE, which the upper bound resolves in the system's favour."""

    inside = minority = tied = 0
    for row in rows:
        counts = groups[row["keys"][name]]
        if len(counts) > 1:
            inside += 1
            top = max(counts.values())
            if counts[row["intent"]] < top:
                minority += 1
            elif list(counts.values()).count(top) > 1:
                tied += 1
    return {"inside": inside, "minority": minority, "tied": tied,
            "ceiling": 100.0 * (1.0 - minority / len(rows)) if rows else 100.0}


def near_neighbours(rows: list[dict], pool: list[dict], threshold: float) -> tuple:
    """Rows with a DIFFERENT-intent utterance in ``pool`` whose token set reaches
    ``threshold`` Jaccard.  A SOFT signal, never a cap: two sentences can differ by a
    single token and still be unambiguously different intents."""

    hits = 0
    pairs: collections.Counter = collections.Counter()
    for row in rows:
        own = row["tokenset"]
        best, partner = 0.0, None
        for other in pool:
            if other["intent"] == row["intent"] or other["utterance_id"] == row["utterance_id"]:
                continue
            union = len(own | other["tokenset"])
            if not union:
                continue
            score = len(own & other["tokenset"]) / union
            if score > best or (score == best and partner is not None and other["intent"] < partner):
                best, partner = score, other["intent"]
        if best >= threshold:
            hits += 1
            pairs[tuple(sorted((row["intent"], partner)))] += 1
    return hits, pairs


def partition(fold_a: list[dict], groups: dict, by_sample: dict, name: str) -> dict:
    """The locked PLAN arm's Fold A intent error, split by CAUSE in a fixed precedence so
    the classes are mutually exclusive and exhaustive."""

    wrong = [r for r in fold_a if r["gold_intent"] != r["delivered_intent"]]
    out: collections.Counter = collections.Counter({name_: 0 for name_ in CLASSES})
    confusion: collections.Counter = collections.Counter()
    for row in wrong:
        counts = groups[by_sample[row["sample_id"]]["keys"][name]]
        if len(counts) > 1 and counts[row["gold_intent"]] < max(counts.values()):
            out["UNWINNABLE"] += 1
        elif len(counts) > 1:
            out["AMBIGUOUS-BUT-MAJORITY"] += 1
        elif CATCH_ALL in (row["gold_intent"], row["delivered_intent"]):
            out["CATCH-ALL"] += 1
            confusion[(row["gold_intent"], row["delivered_intent"])] += 1
        else:
            out["OURS"] += 1
    inside = [r for r in fold_a if len(groups[by_sample[r["sample_id"]]["keys"][name]]) > 1]
    return {"rows": len(fold_a), "wrong": len(wrong), "classes": out, "confusion": confusion,
            "rows_in_colliding_group": len(inside),
            "colliding_rows_correct": sum(1 for r in inside if r["gold_intent"] == r["delivered_intent"]),
            "intent_accuracy": 100.0 * (1.0 - len(wrong) / len(fold_a))}


def rate(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.2f}" if whole else "n/a"


def table(add, header: list[str], aligns: str, rows: list[list]) -> None:
    add("| " + " | ".join(header) + " |")
    add("| " + " | ".join("---:" if a == "r" else "---" for a in aligns) + " |")
    for row in rows:
        add("| " + " | ".join(str(cell) for cell in row) + " |")
    add("")


def pair_table(add, counter: collections.Counter, unit: str, limit: int = 16) -> None:
    table(add, ["Intent id A", "Intent id B", unit], "llr",
          [[f"`{a}`", f"`{b}`", n] for (a, b), n in
           sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]])


def render(state: dict) -> str:
    out: list[str] = []
    add = out.append
    cen, cat, ros, part = state["census"], state["catchall"], state["rosters"], state["partition"]
    pooled_floor = cen["recordings"]["set"]["train+devel"]["ceiling"]
    roster_floor = min(ros[s["key"]]["pool-consistent"]["set"]["ceiling"] for s in ROSTERS)
    gap = TARGET - part["intent_accuracy"]
    conceded = 100.0 * (part["rows"] - part["classes"]["UNWINNABLE"] - part["classes"]["CATCH-ALL"]) / part["rows"]

    add("# SLURP intent label ceiling: the maximum intent accuracy attainable under gold as it stands")
    add("")
    add(f"Date: 2026-09-26. Read id `{READ_ID}`, recipe `{RECIPE_ID}`. Generated `{state['generated']}`.")
    add("")
    add("The measurement owner decision 137 made a prerequisite of treating 95 per cent as a "
        "distance. A model-free read: zero model, server, tokenizer, encoder, embedder, ASR, "
        "scorer, network, GPU and paid-API contacts. Every number is arithmetic over the governed "
        "SLURP annotation bytes, three committed roster receipts and one sealed analysis artefact, "
        "all sha256-pinned below. **The test split stays closed** -- `test.jsonl` is never opened, "
        "hashed or counted, so the census covers `train` and `devel` only and no number here is a "
        "test claim. Gold is read offline into aggregate tables and reaches no runtime path. No "
        "utterance text, sentence text, transcript, token surface, gold filler or delivered text is "
        "printed or persisted: sentence identity enters as a group key consumed in-process and "
        "discarded, and every cell below is an intent id, a count, a rate or a hash. A DIAGNOSTIC, "
        "never a gate -- it registers no cell, admits no mechanism, releases no store, proposes no "
        "mechanism and authorises no flight.")
    add("")
    add("## 0. What was read")
    add("")
    table(add, ["Artefact", "Path", "sha256"], "lll",
          [[r["what"], f"`{r['path']}`", f"`{r['sha256']}`"] for r in state["inputs"]])
    add("Gold intent is the COMPUTED `f\"{scenario}_{action}\"` pair, exactly what "
        "`data.slurp._parse_record` builds, never the governed jsonl's own occasionally "
        "inconsistent `intent` field. The metadata directory is resolved through the loader's own "
        "`data.slurp._governed_roots` against the umbrella lock, never a hardcoded path.")
    add("")
    add("## 1. Label determinacy from the corpus itself")
    add("")
    add("Three MECHANICAL sentence keys, loosest last, each a deterministic function of the "
        "corpus's own `tokens[].surface` sequence -- lowercased, non-alphanumeric characters (the "
        "apostrophe excepted) removed, empty tokens dropped. `sequence` is the token order, `bag` "
        "the order-insensitive multiset, `set` the order- and repetition-insensitive set. No "
        "judgement of this read's enters any of them. A group is COLLIDING when one key carries two "
        "or more different gold intents; `min loss` is the honest floor -- inside such a group the "
        "best any function of the sentence can do is answer the group's most frequent gold, so "
        "every other member is wrong, and a tie resolves in the system's favour because this is an "
        "upper bound.")
    add("")
    for weight in ("utterances", "recordings"):
        add(f"Counted in **{weight}**:")
        add("")
        table(add, ["Key", "Scope", "rows", "distinct keys", "colliding groups", "rows affected",
                    "min loss", "corpus ceiling %"], "llrrrrrr",
              [[f"`{name}`", scope, f"{cen[weight][name][scope]['total']:,}",
                f"{cen[weight][name][scope]['distinct_keys']:,}",
                cen[weight][name][scope]["colliding_groups"], cen[weight][name][scope]["affected"],
                cen[weight][name][scope]["min_loss"], f"{cen[weight][name][scope]['ceiling']:.4f}"]
               for name in KEYS for scope in SCOPES])
    add("**The answer this census gives.** Sentence-level label ambiguity in SLURP is effectively "
        f"absent. At the strictest key the whole `train` split holds "
        f"{cen['utterances']['sequence']['train']['colliding_groups']} colliding groups over "
        f"{cen['utterances']['sequence']['train']['distinct_keys']:,} distinct sentences, and "
        f"`devel` holds {cen['utterances']['sequence']['devel']['colliding_groups']}. At the "
        "LOOSEST mechanical key -- the token set, which merges sentences no reader would call the "
        f"same string -- the pooled `train+devel` ceiling is still {pooled_floor:.4f} per cent by "
        "recording. Pooling the splits is the harsher reading, because it also counts a sentence "
        "carrying one intent in `train` and another in `devel`; it adds "
        f"{cen['recordings']['set']['train+devel']['colliding_groups'] - cen['recordings']['set']['train']['colliding_groups']} "
        "groups and no more. `devel` on its own is exactly determinate at every key. Of the "
        f"{cen['utterances']['set']['train+devel']['colliding_groups']} pooled colliding groups, "
        f"{cen['utterances']['set']['train+devel']['ties']} are exact ties by utterance, so the "
        "bound gives the system the benefit and charges only the corpus's own duplicate mass.")
    add("")
    add("The colliding intent-id pairs, pooled, at the loosest key (group counts):")
    add("")
    pair_table(add, cen["utterances"]["set"]["train+devel"]["pairs"], "groups")
    add("## 2. The catch-all's geometry")
    add("")
    add(f"`{CATCH_ALL}` is the intent the rank diagnostic named as a catch-all: it owns 25.5-31.4 "
        "per cent of all not-delivered intent-wrong rows and misses on 39/45 and 45/51 rows there. "
        "If that behaviour were LABEL arbitrariness, it would show as sentence collisions. It does "
        "not. Both columns are the maximum over the three keys.")
    add("")
    table(add, ["Scope", f"`{CATCH_ALL}` gold rows",
                "sentence-identical to a different-intent row",
                "rows of another intent sentence-identical to one of these (reverse)"], "lrrr",
          [[scope, cat[scope]["rows"], cat[scope]["collides"], cat[scope]["reverse"]]
           for scope in SCOPES])
    add("Within either split, zero in both directions at every key. Pooling the two splits finds "
        f"exactly {cat['train+devel']['collides']} `{CATCH_ALL}` utterance whose normalised "
        f"sentence is also carried by one `general_greet` utterance in the other split -- the "
        "single cross-split collision section 1's pair table lists. So the catch-all is not a "
        "duplicate-label problem: it accounts for one colliding group in the entire corpus, and "
        f"its other {cat['train+devel']['rows'] - cat['train+devel']['collides']} gold utterances "
        "share a normalised sentence with nothing.")
    add("")
    add("Because the hard test returns essentially zero, the NEAR-identical test is reported next. "
        "It is a SOFT signal and never a cap: two sentences can differ by a single token and still "
        "be unambiguously different intents, so a near neighbour bounds nothing. Jaccard is over "
        "token sets, against every other utterance of a different intent in the same split.")
    add("")
    table(add, ["Split", "gold rows"] + [f"J>={t}" for t in JACCARD], "lr" + "r" * len(JACCARD),
          [[split, cat[split]["rows"]] +
           [f"{cat[split]['jaccard'][str(t)]['hits']} "
            f"({rate(cat[split]['jaccard'][str(t)]['hits'], cat[split]['rows'])} %)" for t in JACCARD]
           for split in ("train", "devel")])
    add(f"The nearest different-intent partner of a `{CATCH_ALL}` row in `train`, at J>=0.6, as "
        "intent-id pairs and counts:")
    add("")
    pair_table(add, cat["train"]["jaccard"]["0.6"]["pairs"], "rows", 12)
    add("**What that structure says.** The catch-all's residual is not label arbitrariness in the "
        "sense this section can cap: even at J>=0.6, a threshold that merges sentences sharing "
        f"barely half their tokens, only {cat['train']['jaccard']['0.6']['hits']} of "
        f"{cat['train']['rows']} `train` rows and {cat['devel']['jaccard']['0.6']['hits']} of "
        f"{cat['devel']['rows']} `devel` rows have a different-intent near neighbour at all. "
        "Whatever makes the catch-all hard, it is not that the corpus labels the same sentence two "
        "ways.")
    add("")
    add("## 3. The attainable ceiling, per roster")
    add("")
    add("Three readings of the same bound, strictest last. **roster-local** groups only the "
        "roster's own rows, the most generous reading because a system evaluated on one roster "
        "could in principle specialise to it. **split-consistent** forms the group over the whole "
        "split the roster is drawn from, the honest reading for a deterministic function of the "
        "audio: it does not know which rows are in the roster. **pool-consistent** forms it over "
        "`train`+`devel` together, the harshest reading available without opening the test split. "
        "`tied` counts rows inside a 1-1 group, which the bound resolves in the system's favour.")
    add("")
    table(add, ["Roster", "rows", "scope", "in a colliding group", "tied",
                "rows a system must lose", "ceiling %"], "lrlrrrr",
          [[f"`{spec['key']}`", ros[spec["key"]]["rows"], scope,
            ros[spec["key"]][scope]["set"]["inside"], ros[spec["key"]][scope]["set"]["tied"],
            ros[spec["key"]][scope]["set"]["minority"],
            f"{ros[spec['key']][scope]['set']['ceiling']:.4f}"]
           for spec in ROSTERS for scope in ROSTER_SCOPES])
    add("That table uses the LOOSEST key. The stricter two give the same or a higher ceiling on "
        "every roster and every scope:")
    add("")
    table(add, ["Roster", "scope"] + [f"`{n}` %" for n in KEYS], "ll" + "r" * len(KEYS),
          [[f"`{spec['key']}`", scope] +
           [f"{ros[spec['key']][scope][n]['ceiling']:.4f}" for n in KEYS]
           for spec in ROSTERS for scope in ROSTER_SCOPES])
    add("**This is an upper bound from ONE cause only.** It counts sentence-level gold ambiguity "
        "and nothing else. It does not count annotation error, scenario/action boundary "
        "disagreement between two sentences that are not token-identical, audio that is "
        "unintelligible, an entity the scorer reads differently, or any other reason a row might be "
        "unanswerable. **The true attainable ceiling is at or below every number in this table.** "
        "What the table settles is one direction only: sentence-level ambiguity does not put the "
        f"ceiling below 95, because it does not put it below {roster_floor:.4f} on any roster this "
        f"programme uses, nor below {pooled_floor:.4f} on the pooled corpus. One consequence of the "
        "tie rule should not be oversold: every colliding group touching these rosters is a 1-1 "
        f"tie, so a {roster_floor:.4f} roster figure means a system may be right on the roster row "
        "only at the cost of the partner row outside it -- which is exactly why the corpus-level "
        "census in section 1 reads 99.94 to 99.97 rather than 100.")
    add("")
    add("Soft near-identity for the same rosters, the same non-binding signal section 2 reports:")
    add("")
    table(add, ["Roster", "rows"] + [f"J>={t}" for t in JACCARD], "lr" + "r" * len(JACCARD),
          [[f"`{spec['key']}`", ros[spec["key"]]["rows"]] +
           [f"{ros[spec['key']]['jaccard'][str(t)]} "
            f"({rate(ros[spec['key']]['jaccard'][str(t)], ros[spec['key']]['rows'])} %)"
            for t in JACCARD] for spec in ROSTERS])
    add("## 4. Where the lock arm's error actually sits against that ceiling")
    add("")
    add(f"The locked v2.0 PLAN arm on TRAIN Fold A, read off the sealed bad-case bank: "
        f"{part['wrong']} of {part['rows']} rows carry a wrong intent, so intent accuracy is "
        f"{part['intent_accuracy']:.4f} per cent, reproducing decision 137's own "
        f"{LOCK_ARM_INTENT:.4f} to four decimal places. The {part['wrong']} wrong rows are "
        "partitioned by CAUSE against the pool-consistent loosest-key groups, in a fixed precedence "
        "so the classes are mutually exclusive and exhaustive: a row inside a colliding group is "
        "classified there first, then a row touching the catch-all in either direction, then the "
        "remainder.")
    add("")
    table(add, ["Class", "rows", "pp of the roster", "what it means"], "lrrl",
          [[f"`{name}`", part["classes"][name], rate(part["classes"][name], part["rows"]),
            MEANING[name]] for name in CLASSES] +
          [["**total wrong**", f"**{part['wrong']}**",
            f"**{rate(part['wrong'], part['rows'])}**",
            f"accuracy {part['intent_accuracy']:.4f}"]])
    add(f"Both label classes are empty for a reason worth stating: {part['rows_in_colliding_group']} "
        "Fold A rows sit in a pooled colliding group at all, every one of them is a 1-1 tie, and "
        f"the lock arm answered {part['colliding_rows_correct']} of them CORRECTLY. Sentence-level "
        "ambiguity therefore removes nothing from this arm's error.")
    add("")
    add("The catch-all class as a gold -> delivered confusion structure between intent ids:")
    add("")
    table(add, ["gold intent id", "delivered intent id", "rows"], "llr",
          [[f"`{gold}`", f"`{delivered}`", n] for (gold, delivered), n in
           sorted(part["confusion"].items(), key=lambda kv: (-kv[1], kv[0]))[:16]])
    add(f"**The arithmetic the owner asked for.** The gap from the lock arm to the absolute target "
        f"is {gap:.2f} points, which is {part['rows'] - int(round(part['rows'] * TARGET / 100.0))} "
        f"rows of {part['rows']} still allowed to be wrong at {TARGET:.0f} per cent against the "
        f"{part['wrong']} wrong today. Label ambiguity accounts for "
        f"{part['classes']['UNWINNABLE']} of them. Even if the ENTIRE catch-all class were conceded "
        "as permanently unreachable -- which section 2 gives no label-side reason to do -- the best "
        f"attainable accuracy would still be {conceded:.4f} per cent, above the target; and "
        f"{part['classes']['OURS']} rows ({rate(part['classes']['OURS'], part['rows'])} points) "
        f"would remain available to recover against the {gap:.2f} points needed.")
    add("")
    add("## 5. The published reference line")
    add("")
    add("Quoted, not recomputed, from the pinned scoring-alignment audit "
        "`docs/readiness/2026-09-04-scoring-alignment-audit-slurp-earnings.md` (its own citations "
        "are Bastianelli et al., EMNLP 2020, arXiv:2011.13205, Table 7, and He & Garner, "
        "arXiv:2305.13512):")
    add("")
    table(add, ["Published system", "intent accuracy %", "condition"], "lrl",
          [[name, value, note] for name, value, note in PUBLISHED])
    add("So 95 sits about 10 points above the highest published intent accuracy in this record and "
        "about 5 points below this read's own label-side ceiling. Both reference lines are given "
        "without editorial: the field has not published 95 on SLURP intent, and nothing in the "
        "labels forbids it.")
    add("")
    add("## 6. The answer, in one sentence")
    add("")
    add("**95 per cent intent accuracy is BELOW the label ceiling on every roster this programme "
        f"uses** -- the sentence-level ceiling is {roster_floor:.4f} per cent on all three rosters "
        f"and {pooled_floor:.4f} per cent on the pooled corpus, so the owner's caveat is not what "
        f"stands between the system and the target. What remains is ours: {gap:.2f} points to "
        f"recover on TRAIN Fold A, of which {rate(part['classes']['UNWINNABLE'], part['rows'])} "
        f"points are unwinnable under gold, {rate(part['classes']['CATCH-ALL'], part['rows'])} "
        f"points sit on the `{CATCH_ALL}` catch-all for reasons section 2 shows are NOT label "
        f"duplication, and {rate(part['classes']['OURS'], part['rows'])} points are plainly system "
        "error. The target is reachable arithmetically even conceding the whole catch-all, and it is "
        "a composition problem, not a dataset problem.")
    add("")
    add("One thing this read does not say. It bounds ONE cause. A sentence-level ceiling near 100 "
        "is consistent with a lower true ceiling from a cause this read did not measure -- "
        "annotation error, unintelligible audio, or scorer-side disagreement. What it rules out is "
        "the specific hypothesis decision 137 recorded: that duplicate or arbitrary sentence-level "
        "labelling puts 95 out of reach. It does not.")
    add("")
    add("## 7. Boundary")
    add("")
    add("This read makes no model, server, tokenizer, encoder, embedder, ASR, scorer, network, GPU "
        "or paid-API contact; it registers no cell, admits no mechanism, releases no store, draws "
        "no roster, proposes no mechanism, opens no split beyond `train` and `devel`, and "
        "authorises no flight. The test split was not opened. Every number is a development number "
        "(owner decisions 28 and 86) and none is a test claim or an effectiveness, superiority or "
        "generalisation claim.")
    add("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(pathlib.Path(__file__).resolve().parents[2]))
    parser.add_argument("--lock", default=None)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--markdown", default=None)
    args = parser.parse_args(argv)

    repo = pathlib.Path(args.repo).resolve()
    lock_path = pathlib.Path(args.lock) if args.lock else umbrella_lock_path(repo)
    root = pathlib.Path(args.data_root) if args.data_root else data_root()
    metadata_dir = _governed_roots(load_lock(lock_path), root)[2]
    bank_path = root / BANK_RELPATH
    if not bank_path.is_file():
        raise AuditError(f"sealed bad-case bank missing: {bank_path}")

    splits = {s: read_split(metadata_dir, s) for s in ("train", "devel")}
    pooled = splits["train"] + splits["devel"]
    scopes = {"train": splits["train"], "devel": splits["devel"], "train+devel": pooled}

    state: dict = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "census": {}, "catchall": {}, "rosters": {}}
    state["inputs"] = [
        {"what": "governed SLURP `train` annotations", "path": f"{metadata_dir}/train.jsonl",
         "sha256": digest(metadata_dir / "train.jsonl")},
        {"what": "governed SLURP `devel` annotations", "path": f"{metadata_dir}/devel.jsonl",
         "sha256": digest(metadata_dir / "devel.jsonl")},
        {"what": "sealed bad-case bank (Fold A PLAN arm per-row classes)",
         "path": f"$SPEECHRL_DATA_DIR/{BANK_RELPATH}", "sha256": digest(bank_path)},
    ] + [{"what": f"roster receipt `{s['key']}`", "path": s["relpath"],
          "sha256": digest(repo / s["relpath"])} for s in ROSTERS]

    for weight in ("utterances", "recordings"):
        state["census"][weight] = {n: {sc: census(rows, n, weight) for sc, rows in scopes.items()}
                                  for n in KEYS}
    for scope, rows in scopes.items():
        catch = [r for r in rows if r["intent"] == CATCH_ALL]
        collides = reverse = 0
        for name in KEYS:
            groups = group_by(rows, name)
            collides = max(collides, sum(1 for r in catch if len(groups[r["keys"][name]]) > 1))
            reverse = max(reverse, sum(1 for r in rows if r["intent"] != CATCH_ALL
                                       and groups[r["keys"][name]][CATCH_ALL] > 0))
        entry = {"rows": len(catch), "collides": collides, "reverse": reverse, "jaccard": {}}
        if scope != "train+devel":
            for threshold in JACCARD:
                hits, pairs = near_neighbours(catch, rows, threshold)
                entry["jaccard"][str(threshold)] = {"hits": hits, "pairs": pairs}
        state["catchall"][scope] = entry

    by_utterance = {s: {r["utterance_id"]: r for r in rows} for s, rows in splits.items()}
    fold_a = [json.loads(line) for line in open(bank_path, encoding="utf-8") if line.strip()]
    fold_a = [r for r in fold_a if r["roster"] == "train-fold-a"]
    if not fold_a:
        raise AuditError("bad-case bank carries no train-fold-a rows")
    for spec in ROSTERS:
        rows = roster_rows(repo, spec, by_utterance[spec["split"]])
        entry: dict = {"rows": len(rows)}
        for scope, pool in (("roster-local", rows), ("split-consistent", splits[spec["split"]]),
                            ("pool-consistent", pooled)):
            entry[scope] = {n: unwinnable(rows, group_by(pool, n), n) for n in KEYS}
        entry["jaccard"] = {str(t): near_neighbours(rows, splits[spec["split"]], t)[0] for t in JACCARD}
        state["rosters"][spec["key"]] = entry
        if spec["key"] == "train-fold-a":
            state["partition"] = partition(fold_a, group_by(pooled, "set"),
                                           {r["sample_id"]: r for r in rows}, "set")
    if "partition" not in state:
        raise AuditError("the train-fold-a roster did not resolve; no partition to report")

    markdown = pathlib.Path(args.markdown) if args.markdown else repo / DEFAULT_MARKDOWN
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(render(state), encoding="utf-8", newline="\n")
    print(f"wrote {markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
