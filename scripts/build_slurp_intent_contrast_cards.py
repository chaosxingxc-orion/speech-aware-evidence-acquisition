#!/usr/bin/env python3
"""Build and release the W3 intent CONTRAST cards (owner decision 164, knowledge-wave item W3).

WHAT IT BUILDS. A new release of the ``intent-boundaries`` store,
``knowledge/slurp/semantic/intent-boundaries-contrast-v1``, from the flown
``intent-boundaries-v1`` snapshot. Every card keeps its header, its activation
boundary and its authored confusable exclusion VERBATIM, and keeps any
card-specific limitation bullet. What it loses is the boilerplate the 2026-09-27
knowledge content audit (K1) measured at 57.7 % of every card: the uncertainty
sentence that is identical on all 60 cards and the limitation bullet every card
shares. What it gains, in their place, is CONTENT: a contrast line for each of
the card's nearest rival intents, derived from TRAIN alone --

  * the rivals are the intent's nearest neighbours by cosine between the
    pinned centroid boundary keys KPROBE built
    (``prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl``),
    nearest first, never the card itself;
  * each line names, for this intent and for the rival, the words most typical
    of that intent's TRAIN requests against the other (largest difference of
    utterance-level document frequency, a word counted only outside the
    annotated slot spans, only when at least MIN_SUPPORT distinct utterances of
    that intent carry it, function words and the wake word excluded), and the
    slot TYPES one side carries and the other does not (share difference at
    least TYPE_GAP), both read from the R01-excluded exemplar pool's frozen
    annotations (``size-pool-annotated-exemplars-minus-r01``, 8,554 TRAIN
    utterances; the pool the centroid keys were built from). No utterance, span
    or filler is copied into a card: a cue is a single aggregated word, and a
    slot is a type name.

THE TOKEN RULE. Rivals are added nearest-first, at most MAX_RIVALS, and only
while the rebuilt card tokenises to NO MORE tokens than the flown card (the
local vocab-only ``llama-tokenize`` over the pinned GGUF, the G5 measurement's
own tokenizer). Every card therefore costs at most what it cost before, so no
request in any phase grows from this change -- the Solver's registered
envelope has 226 tokens of headroom and W3's cards spend none of it.

WHAT STAYS FIXED. Facet ids, facet representations (the encoded keys) and value
ids are the v1 store's, byte for byte, so the boundary retrieval -- the written
key vectors, the agreement table and the delivered set -- is unchanged; only
the bodies behind the delivered ids change. The release is proved by
re-loading it through ``rails.knowledge_stores.load_knowledge_store_binding``.

BOUNDARY. Model-free: zero model, server, encoder, embedder, ASR, scorer,
network, GPU and paid-API contacts; the tokenizer is a local vocab-only process
whose invocations are counted in the receipt. TRAIN only: the pool is asserted
disjoint from TRAIN Fold A, TRAIN Fold B and the R01 construction roster. No
gold label of any evaluated row is read. Writes only under the data root
(write-once: an existing file with different bytes is refused) and the
repository receipt, which carries hashes, counts, rival ids and token counts,
never a cue word or any card text.

    python scripts/build_slurp_intent_contrast_cards.py --data-root "$SPEECHRL_DATA_DIR" [--dry]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (  # noqa: E402
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors  # noqa: E402

BUILDER_ID = "saea-slurp-intent-contrast-cards-v1"
ARTIFACT_ID = "SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-V1"
LEDGER_ROW = "SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-BUILD-V1"
OUT_NAMESPACE = "knowledge/slurp/semantic/intent-boundaries-contrast-v1"
SOURCE_RELPATH = f"prepared/{ARTIFACT_ID}/source-v1.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json"

BASE = {
    "snapshot": ("knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json",
                 "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"),
    "release": ("knowledge/slurp/semantic/intent-boundaries-v1/release.json",
                "2e51c14b4f1c3a122968bc0fd7809523470aad80923ff87c1ce9992ed8d3beb4"),
}
CENTROIDS = ("prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl",
             "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532")
POOL = ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
        "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63")
FORBIDDEN_ROSTERS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/rosters/slurp-stage3-construction-r01.json",
)
GGUF_RELPATH = "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
DEFAULT_TOKENIZE = "/home/chao/llama.cpp/build/bin/llama-tokenize"
DIMENSION = "intent-boundary"

MAX_RIVALS = 5
CUES_PER_SIDE = 2
MIN_SUPPORT = 3
MIN_DF_GAP = 0.05
TYPE_GAP = 0.30
TYPES_PER_SIDE = 1
#: Function words and the SLURP wake word: never a cue.
STOPWORDS = frozenset(
    """a an the i me my mine you your yours we us our he him his she her it its they them their
    to of for in on at by with and or but if so as is are was were be been am do does did can
    could would will shall should may might must this that these those there here what whats
    which who whom how please olly ollie hey ok okay just""".split()
    + ["what's"]
)
CONTRAST_HEADER = "Nearest rivals, typical TRAIN words (this intent | rival):"
SECTIONS = ("Activation boundary", "Confusable exclusions", "Uncertainty behavior", "Limitations")
_SECTION_LINE = re.compile(
    r"^(Activation boundary|Confusable exclusions|Uncertainty behavior|Limitations):(.*)$"
)


class BuildError(RuntimeError):
    pass


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


class Tokenizer:
    """The G5 measurement's tokenizer: one vocab-only llama-tokenize process per distinct text."""

    def __init__(self, binary: str, model: Path, scratch: Path) -> None:
        self.binary, self.model, self.scratch = binary, model, scratch
        self.cache: dict[str, int] = {}
        self.invocations = 0

    def count(self, text: str) -> int:
        key = sha_bytes(text.encode("utf-8"))
        if key in self.cache:
            return self.cache[key]
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / f"{key}.txt"
        path.write_bytes(text.encode("utf-8"))
        argv = [self.binary, "-m", str(self.model), "-f", str(path), "--no-bos", "--no-escape",
                "--show-count", "--log-disable", "--ids"]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.invocations += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                self.cache[key] = int(line.split(":")[1].strip())
                return self.cache[key]
        raise BuildError("the local tokenizer produced no count")


def split_card(content: str) -> dict:
    """``{"head": "Intent x.", section: [lines]}`` for the four authored sections, in order."""

    lines = content.split("\n")
    head = lines[0]
    if not re.fullmatch(r"Intent [a-z_]+\.", head):
        raise BuildError("a card does not open with its intent header")
    parts: dict[str, list[str]] = {}
    current = None
    for line in lines[1:]:
        match = _SECTION_LINE.match(line)
        if match:
            current = match.group(1)
            if current in parts:
                raise BuildError(f"section {current!r} repeats")
            parts[current] = [match.group(2).strip()] if match.group(2).strip() else []
            continue
        if current is None:
            raise BuildError("text before the first section")
        parts[current].append(line)
    if tuple(parts) != SECTIONS:
        raise BuildError(f"card sections are {tuple(parts)}, not the authored four")
    return {"head": head, **parts}


def load_pool(root: Path) -> dict:
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((root / POOL[0]).read_text(encoding="utf-8")))
    if snap.content_hash() != POOL[1]:
        raise BuildError("the R01-excluded pool is not the pinned content hash")
    per_intent: dict[str, list[tuple[frozenset, frozenset]]] = defaultdict(list)
    recordings: dict[str, list[str]] = defaultdict(list)
    utterances: set[str] = set()
    for value in snap.values:
        parts = [part.strip() for part in value.content.split("|")]
        if len(parts) < 2 or parts[1] != value.task_target:
            raise BuildError("a pool value's rendered label is not its task_target")
        sentence, slots = parts[0], (parts[2] if len(parts) > 2 else "")
        types, filler_words = set(), set()
        for chunk in slots.split(";"):
            if "=" in chunk:
                name, filler = chunk.split("=", 1)
                types.add(name.strip())
                filler_words.update(re.findall(r"[a-z']+", filler.lower()))
        words = frozenset(
            word for word in re.findall(r"[a-z']+", sentence.lower())
            if word not in filler_words and word not in STOPWORDS
        )
        per_intent[value.task_target].append((words, frozenset(types)))
        recordings[value.task_target].extend(value.source_sample_ids)
        for sample in value.source_sample_ids:
            utterances.add(":".join(sample.split(":")[:3]))
    return {"snapshot": snap, "per_intent": per_intent, "recordings": recordings, "utterances": utterances}


def intent_stats(rows: list[tuple[frozenset, frozenset]]) -> dict:
    words, types = Counter(), Counter()
    for word_set, type_set in rows:
        words.update(word_set)
        types.update(type_set)
    n = len(rows)
    return {"n": n, "count": words, "df": {w: c / n for w, c in words.items()},
            "type_share": {t: c / n for t, c in types.items()}}


def cues(a: dict | None, b: dict | None) -> list[str]:
    if a is None or a["n"] == 0:
        return []
    other = b["df"] if b is not None else {}
    scored = sorted(
        ((a["df"][w] - other.get(w, 0.0), w) for w in a["df"] if a["count"][w] >= MIN_SUPPORT),
        key=lambda item: (-item[0], item[1]),
    )
    return [w for gap, w in scored[:CUES_PER_SIDE] if gap > MIN_DF_GAP]


def typed(a: dict | None, b: dict | None) -> list[str]:
    if a is None or a["n"] == 0:
        return []
    other = b["type_share"] if b is not None else {}
    scored = sorted(
        ((share - other.get(t, 0.0), t) for t, share in a["type_share"].items()),
        key=lambda item: (-item[0], item[1]),
    )
    return [t for gap, t in scored[:TYPES_PER_SIDE] if gap >= TYPE_GAP]


def contrast_line(intent: str, rival: str, stats: dict) -> tuple[str, dict]:
    """``- rival: w, w, w [type] | w, w, w [type]`` -- this intent's side first."""

    a, b = stats.get(intent), stats.get(rival)
    mine, theirs = cues(a, b), cues(b, a)
    my_types, their_types = typed(a, b), typed(b, a)

    def side(words: list[str], types: list[str]) -> str:
        text = ", ".join(words) if words else "-"
        return text + (f" [{', '.join(types)}]" if types else "")

    return f"- {rival}: {side(mine, my_types)} | {side(theirs, their_types)}", {
        "rival": rival, "cue_words_this": len(mine), "cue_words_rival": len(theirs),
        "types_this": my_types, "types_rival": their_types,
    }


def render(parts: dict, lines: list[str], special_limitations: list[str]) -> str:
    out = [parts["head"], "Activation boundary:", *parts["Activation boundary"],
           "Confusable exclusions:", *parts["Confusable exclusions"]]
    if lines:
        out += [CONTRAST_HEADER, *lines]
    if special_limitations:
        out += ["Limitations:", *special_limitations]
    return "\n".join(out)


def write_once(path: Path, data: bytes, *, dry: bool) -> str:
    digest = sha_bytes(data)
    if dry:
        return digest
    if path.exists():
        if sha_file(path) != digest:
            raise BuildError(f"refusing to overwrite {path} with different bytes")
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest


def build(root: Path, tokenizer: Tokenizer) -> dict:
    """Everything but the writes: the snapshot, the per-card facts and the documents."""

    base = KnowledgeSnapshot.from_frozen_json(json.loads((root / BASE["snapshot"][0]).read_text(encoding="utf-8")))
    if base.content_hash() != BASE["snapshot"][1]:
        raise BuildError("intent-boundaries-v1 is not the flown content hash")
    if sha_file(root / BASE["release"][0]) != BASE["release"][1]:
        raise BuildError("intent-boundaries-v1 release.json is not the flown pin")
    base_release = json.loads((root / BASE["release"][0]).read_text(encoding="utf-8"))

    cards = {value.value_id.split("intent-boundary:", 1)[1]: value for value in base.values}
    if len(cards) != 60:
        raise BuildError("intent-boundaries-v1 is not the 60-card store")
    split = {intent: split_card(value.content) for intent, value in cards.items()}
    if len({tuple(parts["Uncertainty behavior"]) for parts in split.values()}) != 1:
        raise BuildError("the uncertainty section is not identical on every card")
    shared = 0
    for column in zip(*[parts["Limitations"] for parts in split.values()], strict=False):
        if len(set(column)) != 1:
            break
        shared += 1
    if shared == 0:
        raise BuildError("no limitation bullet is shared by every card")

    centroids = load_sealed_vectors(root / CENTROIDS[0], expected_sha256=CENTROIDS[1], dimensions=(DIMENSION,))
    order = sorted(cards)
    if set(centroids) != {f"{DIMENSION}:{intent}" for intent in order}:
        raise BuildError("the centroid keys do not cover the 60 cards exactly")
    matrix = np.asarray([centroids[f"{DIMENSION}:{intent}"][DIMENSION] for intent in order], dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    cosine = matrix @ matrix.T

    pool = load_pool(root)
    forbidden: set[str] = set()
    for relpath in FORBIDDEN_ROSTERS:
        roster = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        forbidden.update(":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"])
    overlap = pool["utterances"] & forbidden
    if overlap:
        raise BuildError(f"the construction pool intersects a forbidden roster on {len(overlap)} utterances")
    stats = {intent: intent_stats(rows) for intent, rows in pool["per_intent"].items()}

    new_values, per_card = {}, {}
    for index, intent in enumerate(order):
        parts, original = split[intent], cards[intent]
        special = parts["Limitations"][shared:]
        rivals = [order[j] for j in np.argsort(-cosine[index], kind="stable") if order[j] != intent]
        old_tokens = tokenizer.count(original.content)
        lines, facts, used = [], [], []
        content = render(parts, [], special)
        for rival in rivals[:MAX_RIVALS]:
            line, fact = contrast_line(intent, rival, stats)
            candidate = render(parts, lines + [line], special)
            if tokenizer.count(candidate) > old_tokens:
                break
            lines.append(line)
            facts.append(fact)
            used.append(rival)
            content = candidate
        new_tokens = tokenizer.count(content)
        if new_tokens > old_tokens:
            raise BuildError(f"{intent}: the rebuilt card is longer than the flown card")
        extra_sources = {s for name in [intent, *used] for s in pool["recordings"].get(name, ())}
        new_values[intent] = ValueBundle(
            value_id=original.value_id,
            content=content,
            associated_facet_ids=original.associated_facet_ids,
            source_sample_ids=tuple(sorted(set(original.source_sample_ids) | extra_sources)),
            provenance_refs=tuple(sorted(set(original.provenance_refs) | {
                f"knowledge-snapshot:{BASE['snapshot'][1]}#{original.value_id}",
                f"sealed-vectors:{CENTROIDS[1]}#nearest-centroid-rivals",
                *(f"knowledge-snapshot:{POOL[1]}#task_target={name}" for name in [intent, *used] if name in stats),
            })),
            task_target=original.task_target,
            prior_score=original.prior_score,
        ).validate()
        per_card[intent] = {
            "rivals_by_centroid": rivals[:MAX_RIVALS],
            "rivals_carried": used,
            "authored_exclusion_named": [
                line.split(":", 1)[0].lstrip("- ").strip() for line in parts["Confusable exclusions"]
            ],
            "tokens_flown": old_tokens,
            "tokens_rebuilt": new_tokens,
            "chars_flown": len(original.content),
            "chars_rebuilt": len(content),
            "pool_utterances_this_intent": stats[intent]["n"] if intent in stats else 0,
            "card_specific_limitations_kept": len(special),
            "lines": facts,
        }

    source_ids = sorted({s for facet in base.facets for s in facet.source_sample_ids}
                        | {s for value in new_values.values() for s in value.source_sample_ids})
    split_identity = split_identity_hash(prefixed("slurp", source_ids))
    snapshot = KnowledgeSnapshot(
        snapshot_id=f"{BUILDER_ID}:{split_identity[:16]}",
        source_split_identity_hash=split_identity,
        source_sample_ids=tuple(source_ids),
        builder_policy_id=BUILDER_ID,
        facets=base.facets,
        values=tuple(new_values[intent] for intent in order),
        source_partition_role=base.source_partition_role,
    ).validate()
    if [facet.as_json() for facet in snapshot.facets] != [facet.as_json() for facet in base.facets]:
        raise BuildError("facets moved; the retrieval would not be the flown one")
    if [value.value_id for value in snapshot.values] != sorted(value.value_id for value in base.values):
        raise BuildError("value ids moved")
    return {
        "snapshot": snapshot, "per_card": per_card, "order": order, "shared_limitations": shared,
        "base_release": base_release, "pool_utterances": len(pool["utterances"]),
        "split_identity": split_identity, "new_values": new_values,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--tokenizer", default=DEFAULT_TOKENIZE)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/saea-w3-tokenize"))
    parser.add_argument("--dry", action="store_true", help="build and measure, write nothing")
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")

    tokenizer = Tokenizer(args.tokenizer, root / GGUF_RELPATH, args.scratch)
    built = build(root, tokenizer)
    snapshot, per_card, order = built["snapshot"], built["per_card"], built["order"]
    snapshot_bytes = canonical(snapshot.frozen_json())
    snapshot_hash = snapshot.content_hash()
    builder_sha = sha_file(Path(__file__))
    inputs = {
        "base_snapshot": {"relpath": BASE["snapshot"][0], "content_sha256": BASE["snapshot"][1]},
        "base_release": {"relpath": BASE["release"][0], "sha256": BASE["release"][1]},
        "centroid_keys": {"relpath": CENTROIDS[0], "sha256": CENTROIDS[1]},
        "construction_pool": {"relpath": POOL[0], "content_sha256": POOL[1],
                              "utterances": built["pool_utterances"]},
        "forbidden_rosters": {relpath: sha_file(REPO_ROOT / relpath) for relpath in FORBIDDEN_ROSTERS},
    }
    rule = {
        "max_rivals": MAX_RIVALS, "cues_per_side": CUES_PER_SIDE, "min_support_utterances": MIN_SUPPORT,
        "min_df_gap": MIN_DF_GAP, "type_gap": TYPE_GAP, "types_per_side": TYPES_PER_SIDE,
        "header": CONTRAST_HEADER, "stopword_count": len(STOPWORDS),
        "removed_boilerplate": {"uncertainty_behavior_identical_on_all_cards": True,
                                "shared_limitation_bullets": built["shared_limitations"]},
        "token_rule": "rivals nearest-first while the rebuilt card tokenises to no more tokens than the flown card",
    }
    source_doc = {
        "schema": "saea-slurp-intent-contrast-cards-source-v1",
        "artifact_id": ARTIFACT_ID,
        "builder_id": BUILDER_ID,
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_cards.py", "sha256": builder_sha},
        "inputs": inputs,
        "rule": rule | {"stopwords": sorted(STOPWORDS)},
        "cards": {intent: {"content": built["new_values"][intent].content, **per_card[intent]} for intent in order},
    }
    source_bytes = canonical(source_doc)
    release = {
        "builder_policy_id": BUILDER_ID,
        "schema": "saea-knowledge-store-release-v1",
        "snapshot_sha256": snapshot_hash,
        "source": {"relpath": SOURCE_RELPATH, "sha256": sha_bytes(source_bytes)},
        "source_split_identity_hash": built["split_identity"],
        "store_id": built["base_release"]["store_id"],
        "store_role": built["base_release"]["store_role"],
    }
    release_bytes = canonical(release)
    contacts = {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "asr": 0, "scorer": 0,
                "network": 0, "gpu": 0, "paid_api": 0,
                "tokenizer_process_vocab_only": tokenizer.invocations}
    completion = {
        "schema": "saea-slurp-intent-contrast-cards-completion-v1",
        "artifact_id": ARTIFACT_ID,
        "exposure_ledger_row": LEDGER_ROW,
        "builder_id": BUILDER_ID,
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_cards.py", "sha256": builder_sha},
        "contacts": contacts,
        "outputs": {
            "snapshot": {"relpath": f"{OUT_NAMESPACE}/snapshot.json", "content_sha256": snapshot_hash,
                         "file_sha256": sha_bytes(snapshot_bytes)},
            "release": {"relpath": f"{OUT_NAMESPACE}/release.json", "sha256": sha_bytes(release_bytes)},
            "source": {"relpath": SOURCE_RELPATH, "sha256": sha_bytes(source_bytes)},
        },
        "source_split_identity_hash": built["split_identity"],
        "facets_unchanged": True,
        "value_ids_unchanged": True,
        "boundary": (
            "TRAIN-only construction from the R01-excluded exemplar pool and the pinned centroid keys; "
            "disjoint from TRAIN Fold A, TRAIN Fold B and R01 (checked)."
        ),
    }
    completion_bytes = canonical(completion)

    written = {
        "snapshot": write_once(root / OUT_NAMESPACE / "snapshot.json", snapshot_bytes, dry=args.dry),
        "source": write_once(root / SOURCE_RELPATH, source_bytes, dry=args.dry),
        "release": write_once(root / OUT_NAMESPACE / "release.json", release_bytes, dry=args.dry),
        "completion": write_once(root / OUT_NAMESPACE / "completion.json", completion_bytes, dry=args.dry),
    }
    if not args.dry:
        binding = load_knowledge_store_binding({"knowledge_stores": {"intent-boundaries": {
            "store_role": "intent-boundaries",
            "snapshot": {"relpath": f"{OUT_NAMESPACE}/snapshot.json", "sha256": snapshot_hash},
            "release": {"relpath": f"{OUT_NAMESPACE}/release.json", "sha256": written["release"]},
        }}}, data_root=root)
        if binding.snapshot_for("intent-boundaries").content_hash() != snapshot_hash:
            raise BuildError("the released store does not re-load to its own content hash")

    tokens_old = sum(card["tokens_flown"] for card in per_card.values())
    tokens_new = sum(card["tokens_rebuilt"] for card in per_card.values())
    carried = Counter(len(card["rivals_carried"]) for card in per_card.values())
    receipt = {
        "schema": "saea-slurp-intent-contrast-cards-receipt-v1",
        "artifact_id": ARTIFACT_ID,
        "exposure_ledger_row": LEDGER_ROW,
        "owner_decision": 164,
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_cards.py", "sha256": builder_sha},
        "inputs": inputs,
        "rule": rule,
        "release": {
            "namespace": OUT_NAMESPACE,
            "snapshot": {"relpath": f"{OUT_NAMESPACE}/snapshot.json", "content_sha256": snapshot_hash,
                         "file_sha256": written["snapshot"]},
            "release": {"relpath": f"{OUT_NAMESPACE}/release.json", "sha256": written["release"]},
            "completion": {"relpath": f"{OUT_NAMESPACE}/completion.json", "sha256": written["completion"]},
            "source": {"relpath": SOURCE_RELPATH, "sha256": written["source"]},
            "source_split_identity_hash": built["split_identity"],
            "builder_policy_id": BUILDER_ID,
            "reloaded_through_load_knowledge_store_binding": not args.dry,
        },
        "invariants": {"facets_unchanged": True, "value_ids_unchanged": True,
                       "every_card_tokens_not_above_flown": True},
        "tokens": {
            "tokenizer": {"binary": args.tokenizer, "model": GGUF_RELPATH, "invocations": tokenizer.invocations,
                          "same_as": "scripts/analysis/slurp_g5_reviewer_instruction_token_measurement.py"},
            "all_60_cards_flown": tokens_old, "all_60_cards_rebuilt": tokens_new,
            "delta_all_60": tokens_new - tokens_old,
            "max_card_delta": max(card["tokens_rebuilt"] - card["tokens_flown"] for card in per_card.values()),
            "min_card_delta": min(card["tokens_rebuilt"] - card["tokens_flown"] for card in per_card.values()),
        },
        "rivals_carried_distribution": {str(k): carried[k] for k in sorted(carried)},
        "cards": {intent: {k: v for k, v in card.items() if k != "lines"} | {
            "lines": [{k: line[k] for k in ("rival", "cue_words_this", "cue_words_rival", "types_this", "types_rival")}
                      for line in card["lines"]]} for intent, card in per_card.items()},
        "contacts": contacts,
        "boundary": (
            "No card text, cue word, utterance, span or filler appears in this receipt: intent ids, slot TYPE "
            "names, counts, token counts and hashes only."
        ),
    }
    receipt_bytes = canonical(receipt)
    if not args.dry:
        (REPO_ROOT / RECEIPT_RELPATH).parent.mkdir(parents=True, exist_ok=True)
        io.open(REPO_ROOT / RECEIPT_RELPATH, "wb").write(receipt_bytes)
    print(json.dumps({
        "dry": args.dry, "snapshot_content_sha256": snapshot_hash, "written": written,
        "receipt": RECEIPT_RELPATH, "receipt_sha256": sha_bytes(receipt_bytes),
        "tokens": receipt["tokens"], "rivals_carried_distribution": receipt["rivals_carried_distribution"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
