#!/usr/bin/env python3
"""Knowledge-wave item W4 (owner decision 164): slot conventions mined from the
R01-excluded TRAIN exemplar pool and appended to the EXISTING slot-contract cards.

The 2026-09-27 knowledge content audit (``docs/results/2026-09-27-slurp-knowledge-content-
audit.md``, branch ``fable/kaudit``) found three slot-side deficits the released
``slot-contracts-v2`` cards do not address: K2 (no value vocabulary for closed and
semi-closed types), K3 (no annotation-scope, i.e. "what SLURP leaves untagged",
conventions) and K4 (no span-extent rules). The audit CHOOSES which cards are
revised (its per-type loss table), exactly as the A3 audit chose M4b's eight cards;
every number and every value written into a card is derived here from the
**R01-excluded TRAIN exemplar pool only** (``size-pool-annotated-exemplars-minus-r01``,
8,554 utterances, content hash ``6eaa03aea96a...``), which excludes every Fold A,
Fold B and R01 utterance by construction. No Fold A, Fold B, DEV or test byte, no
flight output, no score and no error list is read to author a value.

What is derived, per slot type, from the pool's frozen ``task_target`` annotations
(``"<sentence> | <intent> | type=filler; ..."``, the exact bytes the flights consume):

* **K2, value vocabulary.** ``closed`` = leave-one-utterance-out value coverage
  >= 0.90 (the audit's own class rule): every distinct value is listed.
  ``semi-closed`` = not closed and the most frequent ``N90`` values cover >= 90 % of
  the type's utterance-deduplicated mentions with ``N90 <= LIST_CAP`` (20): those
  ``N90`` values are listed with the covered share. Every other type gets no list.
* **K3, annotation scope.** For each value ``v`` of type ``t`` with at least
  ``SCOPE_MIN_OCCURRENCES`` spoken occurrences in pool utterances of an intent the
  pool pairs with ``t``: how often the spoken ``v`` is annotated as ``t`` versus
  left untagged (no annotated span of any type overlaps it). Rates >=
  ``TAG_RATE_HIGH`` become "tagged when spoken", rates <= ``TAG_RATE_LOW`` become
  "usually left untagged"; the middle is not stated. Derived from annotation
  structure only: the values named are the type's own annotated values.
* **K4, span extent.** For every mention located in its sentence: whether an
  adjacent article, preposition, possessive determiner or relative-time modifier
  sits inside or outside the annotated span; a rule is stated when one side holds
  >= ``SPAN_SHARE`` of at least ``SPAN_MIN_CASES`` cases, with a schematic minimal
  pair (placeholders, never an utterance).

The additions are appended to the existing cards' ``extraction_cues`` (K2, K3) and
``admissible_formats`` (K4) lists; ``intent_bindings`` are untouched, so the facet
key text and every candidate-keyed supply decision are byte-identical to v2 and a
card still reaches a row only when the row's candidate intents already bind it
(W4 composes with any card selection). Each revised card's ``source_support`` is its
v2 support plus the pool recordings of the utterances its statistics were computed
over; the new permitted construction roster is the union.

Outputs (create-only) under ``prepared/SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1/``:
``authored-slot-contracts-w4-v1.json`` (the builder source), ``slot-support-w4-
construction-roster.json`` (the permitted roster receipt), ``conventions-v1.json``
(every statistic, per type), ``CHANGES.json`` (per-card byte deltas, rendered
hashes) and ``receipt.json``. Zero model, tokenizer, encoder, embedder, scorer,
server, network and GPU contacts. ``--dry-run`` prints the summary and writes
nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    CONSTRUCTION_ROSTER_ROLE,
    RECEIPT_SCHEMA as ROSTER_SCHEMA,
    canonical_receipt_bytes,
    read_roster,
    verify_roster,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (  # noqa: E402
    SLOT_CONTRACT_BUILD_POLICY_ID,
    _slot as render_slot,
)

SCHEMA = "saea-slurp-slot-conventions-w4-v1"
OUT_NAMESPACE = "prepared/SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

PINS = {
    # content hashes (KnowledgeSnapshot.content_hash), checked after load
    "pool_minus_r01": ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
                       "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"),
    "slot_v2_snapshot": ("knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
                         "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"),
    # file hashes
    "slot_v2_source": ("prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V2/authored-slot-contracts-v2.json",
                       "fc34b243f2e48e4e0bc3fe10d328d25601b1f1fa7c190c049d696c3ca0db4dd2"),
    "slot_v2_roster": ("prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/slot-support-construction-roster.json",
                       "f46ad1c4132344d998b1864fc62cea050cacb44f2a813f82db83641065733aa3"),
    "outer_scope": ("prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/outer-construction-roster.json",
                    "e1a4b353428eb36603757b7f3b327637a64d74bb879af7f6079390a8afbba475"),
}

#: The audit's per-type loss table (section 3.2) plus its five closed types -- the
#: cards the audit CHOOSES for revision. Content is never chosen from Fold A.
AUDIT_TARGET_TYPES = (
    "date", "business_name", "place_name", "time", "food_type", "person", "event_name",
    "media_type", "business_type", "order_type", "device_type", "list_name", "news_topic",
    "song_name", "transport_type", "house_place",
    "timeofday", "meal_type", "transport_agency",
)

LOO_CLOSED = 0.90          # the audit's closed-class rule
SEMI_COVERAGE = 0.90       # semi-closed list covers >= 90 % of mentions
LIST_CAP = 20              # ... with at most 20 values
SCOPE_MIN_OCCURRENCES = 5  # K3: spoken occurrences of a value under legal intents
TAG_RATE_HIGH = 0.85
TAG_RATE_LOW = 0.35
SCOPE_LIST_CAP = 5
SPAN_MIN_CASES = 8
SPAN_SHARE = 0.80
SPAN_RULE_CAP = 3
RECURRING_LOO = 0.70  # K3 positive list only where values recur (not proper-name types)

ARTICLES = frozenset({"the", "a", "an"})
PREPOSITIONS = frozenset({"at", "in", "on", "for", "to", "from", "by", "of", "with", "about",
                          "until", "till", "before", "after", "around", "near", "into", "during"})
POSSESSIVES = frozenset({"my", "your", "our", "his", "her", "their", "its"})
RELATIVE = frozenset({"this", "next", "last", "coming", "every", "each"})
#: Generic unit and head words a span may open or close with -- an authored closed
#: list of English units, times of day and container nouns (never a name, never an
#: utterance-specific word). A K4 rule may name only a function word above or one of
#: these, and only when it also occurs inside some annotated value of the type.
HEADS = frozenset({
    "am", "pm", "o'clock", "minute", "minutes", "hour", "hours", "second", "seconds", "day", "days",
    "week", "weeks", "weekend", "month", "months", "year", "years", "morning", "afternoon", "evening",
    "night", "tonight", "list", "lists", "meeting", "meetings", "alarm", "alarms", "room", "socket",
    "plug", "cleaner", "service", "news", "station", "song", "songs", "album", "playlist", "music",
    "radio", "show", "podcast", "book", "restaurant", "shop", "store", "time",
})


class BuildError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_file(root: Path, key: str) -> Path:
    relpath, expected = PINS[key]
    path = root / relpath
    actual = sha256_file(path)
    if actual != expected:
        raise BuildError(f"{relpath}: sha256 {actual} is not the pinned {expected}")
    return path


def load_snapshot(root: Path, key: str) -> KnowledgeSnapshot:
    relpath, expected = PINS[key]
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((root / relpath).read_text(encoding="utf-8")))
    if snap.content_hash() != expected:
        raise BuildError(f"{relpath}: content hash {snap.content_hash()} is not the pinned {expected}")
    return snap


def parse_exemplar(content: str) -> tuple[str, str, list[tuple[str, str]]]:
    parts = [part.strip() for part in content.split("|")]
    if len(parts) != 3:
        raise BuildError("a pool value is not '<sentence> | <intent> | <entities>'")
    pairs = []
    if parts[2] and parts[2] != "none":  # the pool renders an entity-free row as "none"
        for chunk in parts[2].split(";"):
            if "=" not in chunk:
                raise BuildError("a pool entity chunk carries no '='")
            name, filler = chunk.split("=", 1)
            pairs.append((name.strip(), filler.strip()))
    return parts[0], parts[1], pairs


def load_pool(root: Path) -> list[dict]:
    snap = load_snapshot(root, "pool_minus_r01")
    rows = []
    for value in snap.values:
        sentence, intent, pairs = parse_exemplar(value.content)
        if intent != value.task_target:
            raise BuildError(f"{value.value_id}: rendered intent disagrees with task_target")
        rows.append({
            "utt": value.value_id.split("value:", 1)[-1],
            "sentence": sentence, "tokens": sentence.split(), "intent": intent, "pairs": pairs,
            "recordings": tuple(value.source_sample_ids),
        })
    return rows


def locate(tokens: list[str], filler: str) -> list[tuple[int, int]]:
    words = filler.split()
    n = len(words)
    return [(i, i + n) for i in range(len(tokens) - n + 1) if tokens[i:i + n] == words] if n else []


def spans_of(row: dict) -> list[tuple[int, int, str]]:
    """Token spans of the row's annotated mentions; a filler found more than once is
    ambiguous and yields no span (it still counts for vocabulary)."""
    out = []
    for slot_type, filler in row["pairs"]:
        hits = locate(row["tokens"], filler)
        if len(hits) == 1:
            out.append((hits[0][0], hits[0][1], slot_type))
    return out


# ---------------------------------------------------------------------------
# K2


def vocabulary(pool: list[dict]) -> dict:
    mentions: dict[str, Counter] = defaultdict(Counter)
    for row in pool:
        for slot_type, filler in set(row["pairs"]):
            mentions[slot_type][filler] += 1
    out = {}
    for slot_type, counter in mentions.items():
        total = sum(counter.values())
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        loo = sum(n for _, n in ranked if n >= 2) / total
        cumulative, n90 = 0, None
        for index, (_, n) in enumerate(ranked):
            cumulative += n
            if n90 is None and cumulative / total >= SEMI_COVERAGE:
                n90 = index + 1
        if loo >= LOO_CLOSED:
            klass, listed = "closed", ranked
        elif n90 is not None and n90 <= LIST_CAP:
            klass, listed = "semi-closed", ranked[:n90]
        else:
            klass, listed = "open", []
        out[slot_type] = {
            "mentions": total, "distinct_values": len(counter), "loo_value_coverage": round(loo, 6),
            "n90": n90, "class": klass,
            "listed": [[value, n] for value, n in listed],
            "listed_coverage": round(sum(n for _, n in listed) / total, 6) if listed else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# K3


def legal_intents(pool: list[dict]) -> dict[str, set]:
    legal: dict[str, set] = defaultdict(set)
    for row in pool:
        for slot_type, _ in row["pairs"]:
            legal[slot_type].add(row["intent"])
    return legal


def annotation_scope(pool: list[dict], vocab: dict, legal: dict) -> dict:
    """Per (type, value): spoken occurrences under legal intents, tagged as the type vs left
    untagged (no annotated span of any type overlaps the occurrence)."""
    candidates: dict[str, dict[str, list[str]]] = {}
    for slot_type in vocab:
        values = {}
        for row in pool:
            for t, filler in row["pairs"]:
                if t == slot_type:
                    values.setdefault(filler, filler.split())
        candidates[slot_type] = values
    counts: dict[str, dict[str, Counter]] = {t: defaultdict(Counter) for t in vocab}
    population: dict[str, set] = defaultdict(set)
    for row in pool:
        spans = spans_of(row)
        tokens = row["tokens"]
        for slot_type, values in candidates.items():
            if row["intent"] not in legal[slot_type]:
                continue
            for value, words in values.items():
                n = len(words)
                for i in range(len(tokens) - n + 1):
                    if tokens[i:i + n] != words:
                        continue
                    overlapping = [s for s in spans if s[0] < i + n and i < s[1]]
                    if any(s[2] == slot_type for s in overlapping):
                        outcome = "tagged"
                    elif overlapping:
                        outcome = "other-type"
                    else:
                        outcome = "untagged"
                    counts[slot_type][value][outcome] += 1
                    population[slot_type].add(row["utt"])
    out = {}
    for slot_type, per_value in counts.items():
        rows = []
        for value, c in per_value.items():
            spoken = c["tagged"] + c["untagged"]
            if spoken < SCOPE_MIN_OCCURRENCES:
                continue
            rows.append({"value": value, "tagged": c["tagged"], "untagged": c["untagged"],
                         "other_type": c["other-type"], "tag_rate": round(c["tagged"] / spoken, 6)})
        rows.sort(key=lambda r: (-(r["tagged"] + r["untagged"]), r["value"]))
        high = [r for r in rows if r["tag_rate"] >= TAG_RATE_HIGH][:SCOPE_LIST_CAP]
        low = [r for r in rows if r["tag_rate"] <= TAG_RATE_LOW][:SCOPE_LIST_CAP]
        spoken_all = sum(r["tagged"] + r["untagged"] for r in rows)
        out[slot_type] = {
            "values_with_evidence": len(rows), "spoken_occurrences": spoken_all,
            "tagged_occurrences": sum(r["tagged"] for r in rows),
            "untagged_occurrences": sum(r["untagged"] for r in rows),
            "tagged_when_spoken": high, "usually_untagged": low, "all": rows,
            "population_utterances": sorted(population[slot_type], key=int),
        }
    return out


# ---------------------------------------------------------------------------
# K4


def span_extent(pool: list[dict]) -> dict:
    """Word-level span-boundary statistics per type.

    A boundary word is a closed-class function word (article, possessive, relative
    modifier) or a generic unit / head word from :data:`HEADS` that also occurs inside
    some annotated value of the SAME type (so every word a rule names is annotation
    vocabulary, never free utterance text). Leading: the value starts with the word
    (inside) vs the word immediately precedes the value (outside); trailing: the value
    ends with the word vs the word immediately follows it. Prepositions are pooled
    into one leading and one trailing class rule.
    """
    value_tokens: dict[str, set] = defaultdict(set)
    for row in pool:
        for slot_type, filler in row["pairs"]:
            value_tokens[slot_type].update(filler.split())
    function_words = ARTICLES | POSSESSIVES | RELATIVE
    counts: dict[str, Counter] = defaultdict(Counter)
    located: Counter = Counter()
    for row in pool:
        tokens = row["tokens"]
        for start, end, slot_type in spans_of(row):
            located[slot_type] += 1
            heads = HEADS & value_tokens[slot_type]
            allowed = function_words | heads
            multi = end - start > 1
            first, last = tokens[start], tokens[end - 1]
            before = tokens[start - 1] if start > 0 else None
            after = tokens[end] if end < len(tokens) else None
            if multi and first in PREPOSITIONS:
                counts[slot_type][("lead", "<preposition>", "inside")] += 1
            elif before in PREPOSITIONS:
                counts[slot_type][("lead", "<preposition>", "outside")] += 1
            if multi and first in allowed and first not in PREPOSITIONS:
                counts[slot_type][("lead", first, "inside")] += 1
            if before in allowed and before not in PREPOSITIONS:
                counts[slot_type][("lead", before, "outside")] += 1
            if multi and last in PREPOSITIONS:
                counts[slot_type][("trail", "<preposition>", "inside")] += 1
            elif after in PREPOSITIONS:
                counts[slot_type][("trail", "<preposition>", "outside")] += 1
            if multi and last in heads and last not in PREPOSITIONS:
                counts[slot_type][("trail", last, "inside")] += 1
            if after in heads and after not in PREPOSITIONS:
                counts[slot_type][("trail", after, "outside")] += 1
    out = {}
    for slot_type, n in located.items():
        pairs: dict[tuple[str, str], Counter] = defaultdict(Counter)
        for (edge, word, side), k in counts[slot_type].items():
            pairs[(edge, word)][side] += k
        rules = []
        for (edge, word), c in pairs.items():
            cases = c["inside"] + c["outside"]
            if cases < SPAN_MIN_CASES:
                continue
            side = "outside" if c["outside"] >= c["inside"] else "inside"
            share = c[side] / cases
            if share < SPAN_SHARE:
                continue
            rules.append({"edge": edge, "word": word, "side": side, "count": c[side],
                          "cases": cases, "share": round(share, 6)})
        # word-level rules first (they carry the type-specific extent), the pooled
        # preposition rules only when a slot is left
        rules.sort(key=lambda r: (r["word"] == "<preposition>", -r["cases"], r["edge"], r["word"]))
        out[slot_type] = {"located_mentions": n, "rules": rules[:SPAN_RULE_CAP]}
    return out


# ---------------------------------------------------------------------------
# rendering


def render_additions(slot_type: str, vocab: dict, scope: dict, extent: dict) -> dict:
    cues, formats = [], []
    v = vocab.get(slot_type) or {}
    klass = v.get("class")
    if klass == "closed":
        cues.append(
            f"Closed value set: TRAIN annotates {slot_type} only with these {len(v['listed'])} values, most "
            f"frequent first: {', '.join(value for value, _ in v['listed'])}. A word outside this set is not {slot_type}."
        )
    elif klass == "semi-closed":
        cues.append(
            f"Frequent values: these {len(v['listed'])} cover {round(100 * v['listed_coverage'])} % of TRAIN "
            f"{slot_type} mentions: {', '.join(value for value, _ in v['listed'])}. Other spoken values remain legal."
        )
    s = scope.get(slot_type) or {}
    recurring = klass == "semi-closed" or (klass == "open" and v.get("loo_value_coverage", 0.0) >= RECURRING_LOO)
    tagged = s.get("tagged_when_spoken", []) if recurring else []
    untagged = s.get("usually_untagged", [])
    if tagged or untagged:
        parts = []
        if tagged:
            parts.append("tagged when spoken: " + ", ".join(
                f"{r['value']} {r['tagged']}/{r['tagged'] + r['untagged']}" for r in tagged))
        if untagged:
            parts.append("usually left untagged: " + ", ".join(
                f"{r['value']} {r['tagged']}/{r['tagged'] + r['untagged']}" for r in untagged))
        line = "Annotation scope (TRAIN, tagged/spoken under this card's intents): " + "; ".join(parts) + "."
        if untagged:
            line += " Leave a usually-untagged word out unless it names the specific item requested."
        cues.append(line)
    e = extent.get(slot_type) or {}
    if e.get("rules"):
        phrases = []
        for r in e["rules"]:
            word = "a preposition" if r["word"] == "<preposition>" else f"'{r['word']}'"
            if r["edge"] == "lead":
                shape = f"on [{slot_type}: X]" if r["word"] == "<preposition>" and r["side"] == "outside" else (
                    f"[{slot_type}: on X]" if r["word"] == "<preposition>" else (
                        f"{r['word']} [{slot_type}: X]" if r["side"] == "outside" else f"[{slot_type}: {r['word']} X]"))
                where = "before stays outside" if r["side"] == "outside" else "opening is inside"
            elif r["word"] == "<preposition>":
                shape = f"[{slot_type}: X] with" if r["side"] == "outside" else f"[{slot_type}: X with]"
                where = "after stays outside" if r["side"] == "outside" else "closing is inside"
            else:
                shape = f"[{slot_type}: X] {r['word']}" if r["side"] == "outside" else f"[{slot_type}: X {r['word']}]"
                where = "after stays outside" if r["side"] == "outside" else "closing is inside"
            phrases.append(f"{word} {where} {r['count']}/{r['cases']}, {shape}")
        formats.append("Span extent (TRAIN, count/cases): " + "; ".join(phrases) + ".")
    return {"extraction_cues": cues, "admissible_formats": formats}


def build(root: Path) -> dict:
    pool = load_pool(root)
    v2_snapshot = load_snapshot(root, "slot_v2_snapshot")
    v2_source = json.loads(pinned_file(root, "slot_v2_source").read_text(encoding="utf-8"))
    v2_roster = read_roster(pinned_file(root, "slot_v2_roster"))
    scope_roster = read_roster(pinned_file(root, "outer_scope"))
    if v2_source["builder_policy_id"] != SLOT_CONTRACT_BUILD_POLICY_ID:
        raise BuildError("the v2 authored source is not a slot-contract source")
    # v2's rendered values must come back from its authored rows (same compiler path)
    rendered_v2 = {render_slot(row)[0]: render_slot(row)[2] for row in v2_source["rows"]}
    for value in v2_snapshot.values:
        slot_id = value.value_id.split("slot-contract:", 1)[-1]
        if rendered_v2.get(slot_id) != value.content:
            raise BuildError(f"v2 card {slot_id} does not re-render from its authored row")

    vocab = vocabulary(pool)
    legal = legal_intents(pool)
    scope = annotation_scope(pool, vocab, legal)
    extent = span_extent(pool)

    utt_recordings = {row["utt"]: row["recordings"] for row in pool}
    utt_of_type: dict[str, set] = defaultdict(set)
    for row in pool:
        for slot_type, _ in row["pairs"]:
            utt_of_type[slot_type].add(row["utt"])

    new_rows, changes, support_union = [], [], set()
    for row in v2_source["rows"]:
        slot_id = row["slot_id"]
        new = json.loads(json.dumps(row))
        if slot_id in AUDIT_TARGET_TYPES:
            added = render_additions(slot_id, vocab, scope, extent)
            if added["extraction_cues"] or added["admissible_formats"]:
                new["extraction_cues"] = list(row["extraction_cues"]) + added["extraction_cues"]
                new["admissible_formats"] = list(row["admissible_formats"]) + added["admissible_formats"]
                population = set(utt_of_type.get(slot_id, ())) | set(scope.get(slot_id, {}).get("population_utterances", ()))
                recordings = sorted({rec for utt in population for rec in utt_recordings[utt]})
                ids = sorted(set(row["source_support"]["source_sample_ids"]) | set(recordings))
                new["source_support"] = {
                    "provenance_refs": sorted(set(row["source_support"]["provenance_refs"]) | {
                        f"knowledge-snapshot://{PINS['pool_minus_r01'][1]}/slot-conventions-w4/{slot_id}"}),
                    "source_sample_ids": ids,
                }
                old_content, new_content = render_slot(row)[2], render_slot(new)[2]
                changes.append({
                    "slot_id": slot_id,
                    "bytes_v2": len(old_content.encode("utf-8")), "bytes_w4": len(new_content.encode("utf-8")),
                    "added_bytes": len(new_content.encode("utf-8")) - len(old_content.encode("utf-8")),
                    "added_words": len(new_content.split()) - len(old_content.split()),
                    "components": {"K2": bool(vocab.get(slot_id, {}).get("listed")),
                                   "K3": any(line.startswith("Annotation scope") for line in added["extraction_cues"]),
                                   "K4": bool(added["admissible_formats"])},
                    "v2_rendered_sha256": hashlib.sha256(old_content.encode("utf-8")).hexdigest(),
                    "w4_rendered_sha256": hashlib.sha256(new_content.encode("utf-8")).hexdigest(),
                    "key_text_unchanged": render_slot(row)[1] == render_slot(new)[1],
                    "pool_recordings_added": len(set(ids) - set(row["source_support"]["source_sample_ids"])),
                })
        support_union.update(new["source_support"]["source_sample_ids"])
        new_rows.append(new)

    if not set(v2_roster["items"][i]["sample_id"] for i in range(len(v2_roster["items"]))) <= support_union:
        raise BuildError("the v2 support is not inside the new union")
    scope_ids = {item["sample_id"] for item in scope_roster["items"]}
    if not support_union <= scope_ids:
        raise BuildError("the new support leaves the outer construction scope")

    stratum_of = {}
    for row in pool:
        for rec in row["recordings"]:
            stratum_of[rec] = row["intent"]
    for item in v2_roster["items"]:
        stratum_of.setdefault(item["sample_id"], item["stratum"])
    items = [{"sample_id": sid, "stratum": stratum_of[sid]} for sid in sorted(support_union)]
    strata = Counter(item["stratum"] for item in items)
    identity = split_identity_hash(prefixed("slurp", [item["sample_id"] for item in items]))
    roster = {
        "schema": ROSTER_SCHEMA,
        "roster_id": "slurp-slot-conventions-w4-support-v1",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": CONSTRUCTION_ROSTER_ROLE,
        "seed": 0,
        "per_stratum": dict(sorted(strata.items())),
        "strata_counts": dict(sorted(strata.items())),
        "items": items,
        "excluded_count": 0,
        "split_identity_hash": identity,
    }
    verify_roster(roster)
    source = {
        "schema": v2_source["schema"],
        "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "source_split_identity_hash": identity,
        "rows": new_rows,
    }
    return {"pool": pool, "vocab": vocab, "scope": scope, "extent": extent, "changes": changes,
            "roster": roster, "source": source, "legal": legal}


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.data_root)
    result = build(root)
    vocab, scope, extent, changes = result["vocab"], result["scope"], result["extent"], result["changes"]

    conventions = {
        "schema": SCHEMA,
        "pins": {k: {"relpath": v[0], "sha256": v[1]} for k, v in PINS.items()},
        "thresholds": {
            "loo_closed": LOO_CLOSED, "semi_closed_coverage": SEMI_COVERAGE, "list_cap": LIST_CAP,
            "scope_min_occurrences": SCOPE_MIN_OCCURRENCES, "tag_rate_high": TAG_RATE_HIGH,
            "tag_rate_low": TAG_RATE_LOW, "scope_list_cap": SCOPE_LIST_CAP,
            "span_min_cases": SPAN_MIN_CASES, "span_share": SPAN_SHARE,
        },
        "audit_target_types": list(AUDIT_TARGET_TYPES),
        "pool": {"utterances": len(result["pool"]),
                 "recordings": sum(len(r["recordings"]) for r in result["pool"])},
        "vocabulary": vocab,
        "annotation_scope": {t: {k: v for k, v in s.items() if k != "population_utterances"}
                             | {"population_utterance_count": len(s["population_utterances"])}
                             for t, s in scope.items()},
        "span_extent": extent,
        "legal_intents": {t: sorted(v) for t, v in result["legal"].items()},
    }
    changes_doc = {
        "schema": SCHEMA + "-changes",
        "changed_cards": [c["slot_id"] for c in changes],
        "cards": changes,
        "total_added_bytes": sum(c["added_bytes"] for c in changes),
        "all_key_text_unchanged": all(c["key_text_unchanged"] for c in changes),
    }
    summary = {
        "changed_cards": len(changes),
        "total_added_bytes": changes_doc["total_added_bytes"],
        "support_recordings": len(result["roster"]["items"]),
        "support_split_identity_hash": result["roster"]["split_identity_hash"],
        "per_card": {c["slot_id"]: [c["added_bytes"], c["components"]] for c in changes},
        "classes": Counter(v["class"] for v in vocab.values()),
    }
    if args.dry_run:
        print(json.dumps(summary, indent=1, default=str))
        return 0
    out = root / OUT_NAMESPACE
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "authored-slot-contracts-w4-v1.json": canonical(result["source"]),
        "slot-support-w4-construction-roster.json": canonical_receipt_bytes(result["roster"]),
        "conventions-v1.json": canonical(conventions),
        "CHANGES.json": canonical(changes_doc),
    }
    for name, raw in files.items():
        path = out / name
        if path.exists():
            if path.read_bytes() != raw:
                raise BuildError(f"{path}: exists with different bytes; refusing to overwrite")
            continue
        path.write_bytes(raw)
    receipt = {
        "schema": SCHEMA + "-receipt",
        "script": {"relpath": "scripts/build_slurp_slot_conventions_w4.py",
                   "sha256": sha256_file(Path(__file__))},
        "outputs": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
        "summary": json.loads(json.dumps(summary, default=str)),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                     "server": 0, "network": 0, "gpu": 0},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    receipt_path = out / "receipt.json"
    if not receipt_path.exists():
        receipt_path.write_bytes(canonical(receipt))
    print(json.dumps({"out": str(out), **receipt["outputs"], **summary}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
