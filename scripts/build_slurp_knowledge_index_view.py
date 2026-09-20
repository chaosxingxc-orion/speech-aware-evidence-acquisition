#!/usr/bin/env python3
"""CLI: build the SLURP KNOWLEDGE INDEX construction view.

Item E21 (the knowledge index; NOT the Earnings-21 carrier, whose scripts share
the same shorthand -- this one is named for what it builds, not for a carrier).

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
tokenizer, scorer, GPU or network contacts. Every byte this script reads was
produced by an earlier, already-paid pass: the three RELEASED construction
stores it indexes, and the governed TRAIN metadata the closed contract
inventory is mined from. Nothing is embedded, nothing is re-encoded, and no
server is contacted.

The output is the pinned view the constant index is rendered from
(``rails.knowledge_index``), in the three-file shape every released SLURP
semantic view already uses::

    <out-root>/knowledge/slurp/semantic/slurp-knowledge-index-v1/snapshot.json
    .../release.json
    .../completion.json

``--out-root`` is REQUIRED and has no default: the coordinator's release job
passes ``$SPEECHRL_DATA_DIR``; every other run passes a scratch directory, so
this builder can never write into the controlled data root by accident. It
writes NO release-pins registration file: registering the release is a
separate, zero-contact job.

WHAT THE VIEW CARRIES, and where each field comes from:

* ``intent`` entries (60) -- one per legal intent of the closed inventory.
  ``l1`` carries that intent's ``Activation boundary`` and its
  ``Confusable exclusions`` operative lines, read from the released
  ``intent-boundaries-v1`` cards (NOT v2: v2 read HARMFUL in cell B4a).
  ``group`` is the intent's scenario, taken from the ontology's own
  ``actions_by_scenario`` pairing, never from splitting the id on an
  underscore. ``rank`` is the intent's CONSTRUCTION ROW COUNT from
  ``scenario-hints-v1``.
* ``slot`` entries (54 carded of 55 legal) -- one per carded entity type,
  from the released ``slot-contracts-v2`` cards (admitted as module M4b).
  ``rank`` is the number of intents the card binds the type to, which is a
  construction statistic of the same pool.
* ``edge`` entries (81 over 44 intents) -- one per ``(intent, neighbour)``
  construction confusion pair of ``scenario-hints-v1`` (item E14). Design
  question Q3 is answered here: ``Confusable exclusions`` is FOLDED INTO the
  edge, so "what distinguishes A from B" is attached to the pair rather than
  to A. ``rank`` is the pair's leaked-neighbour count.
* the ``exemplar`` kind is NEVER built: 9,354 entries at about 124 characters
  each is 1.16 MB and the schema's own rule keeps it pointer-and-expansion
  only (design section 3.1).
* ``shared_sections`` -- design question Q6, answered INSIDE THE RENDERER.
  The card sections whose text is shared across a kind's cards
  (``Uncertainty behavior``: ONE identical 199-character string on all 60
  intent cards, 28.3 % of that store; ``Missing behavior``: 8 distinct values
  over 54 slot cards) are lifted here, once, and each entry keeps the exact
  byte offset they were removed from. No released store is touched and
  nothing is re-pinned; :func:`rails.knowledge_index.restore_card` splices
  every card back byte-for-byte, which this builder checks on every card
  before it writes anything.

CONSTRUCTION DATA ONLY. Three guards, none of them a comment:

1. every input is a RELEASED store, read through its own declared sha256 pin;
   a store whose bytes moved stops the build;
2. the ordering statistics come from ``scenario-hints-v1``, whose own release
   binds the 9,354-utterance construction pool (governed TRAIN minus every
   utterance with a recording in TRAIN Fold A, Fold B or DEV-1000) and whose
   split identity hash this build records and re-checks;
3. the closed inventory is mined from ``train.jsonl`` alone, through
   ``data.slurp.load_slurp_ontology`` with ``include_synthetic=False`` -- the
   same legal-tier source ``render_slurp_label_inventory`` uses -- and every
   entry id must be a MEMBER of it, which is checked per entry rather than
   assumed.

THE DERANGEMENT TWIN (item E24, 2026-09-20; design section 7.2, owner
decisions 48, 50 and 53). ``--twin-seed <int>`` builds
``slurp-knowledge-index-twin-v1`` instead: the SAME entries, ids, groups,
construction ranks, shared sections and ordering as the source view, with
ONLY the per-entry L1 lines and their L2 cards permuted ACROSS IDS WITHIN
EACH KIND by a Sattolo derangement seeded by that integer -- an intent line
among intents, a slot line among slots, an edge line among edges, zero fixed
points. The L1 lines and the L2 card move TOGETHER, so an expansion of id X
shows the deranged entry's card consistently with the line X carries in the
prefix. The twin's ``release.json`` records ``twin_of`` (the source view id
and its snapshot content hash), ``derangement`` (the seed, the deranged
kinds, the permutation sha256 and ``fixed_points: 0``) and
``gold_read: false``.

Before it writes a byte, the twin build PROVES the three properties the
control rests on, and refuses on any of them:

* **T1** zero fixed points -- by CONTENT, not only by position;
* **T2** the per-kind multiset of L1 lines and L2 cards is unchanged;
* **T3** the rendered index, at the recommended defaults, has the SAME
  character count as the source's.

T3 holds because the rendered header states the SOURCE view's id on both
arms (``rails.knowledge_index.KnowledgeIndexTable.header_view_id``): a
form-matched control whose own prefix announces "twin" is readable by the
model and is therefore not a control. Which arm flew is a fact of the
release, the pins and the receipt, never of the token stream.

Usage::

    python scripts/build_slurp_knowledge_index_view.py --out-root <dir>
    python scripts/build_slurp_knowledge_index_view.py --out-root <dir> --check
    python scripts/build_slurp_knowledge_index_view.py --out-root <dir> \\
        --twin-seed 20260920
    python scripts/build_slurp_knowledge_index_view.py --out-root <dir> \\
        --twin-seed 20260920 --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_ontology,
)
from speech_aware_evidence_acquisition.rails.knowledge_index import (  # noqa: E402
    HOISTED_SECTIONS,
    KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
    KNOWLEDGE_INDEX_CARRIER,
    KNOWLEDGE_INDEX_COMPLETION_SCHEMA,
    KNOWLEDGE_INDEX_RELEASE_SCHEMA,
    KNOWLEDGE_INDEX_TWIN_VIEW_ID,
    KNOWLEDGE_INDEX_VIEW_ID,
    KNOWLEDGE_INDEX_VIEW_SCHEMA,
    MAX_HOISTED_DISTINCT,
    TAXONOMY_FREQUENCY_ORDERING,
    IndexEntry,
    SharedSection,
    default_index_plan,
    derange_snapshot,
    edge_id,
    hoist_sections,
    intent_id,
    labelled_bullets,
    parse_card_sections,
    render_constant_index,
    restore_card,
    section_body,
    slot_id,
    table_from_snapshot,
    twin_line_multisets,
)

GENERATOR = "scripts/build_slurp_knowledge_index_view.py"
AUTHORITY = (
    "docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md "
    "sections 3 and 4 (owner decisions 48 and 50); "
    "docs/superpowers/specs/2026-09-19-e21-knowledge-index-design.md"
)
LEDGER_ROW = "SAEA-SLURP-E21-KNOWLEDGE-INDEX-VIEW-V1"
TWIN_AUTHORITY = (
    "docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md "
    "section 7.2 (owner decisions 48, 50 and 53); "
    "docs/superpowers/specs/2026-09-20-e24-knowledge-index-twin-design.md"
)

NAMESPACE = f"knowledge/slurp/semantic/{KNOWLEDGE_INDEX_VIEW_ID}"
SNAPSHOT_RELPATH = f"{NAMESPACE}/snapshot.json"
RELEASE_RELPATH = f"{NAMESPACE}/release.json"
COMPLETION_RELPATH = f"{NAMESPACE}/completion.json"

#: The E24 twin writes the same three files under its OWN namespace, beside
#: the source view: it is a released view in its own right, pinned the same
#: way, and a cell arms it by changing one config field.
TWIN_NAMESPACE = f"knowledge/slurp/semantic/{KNOWLEDGE_INDEX_TWIN_VIEW_ID}"
TWIN_LEDGER_ROW = "SAEA-SLURP-E24-KNOWLEDGE-INDEX-TWIN-V1"


def relpaths(view_id: str) -> dict[str, str]:
    """The three released relpaths of one view id."""

    namespace = f"knowledge/slurp/semantic/{view_id}"
    return {
        "snapshot": f"{namespace}/snapshot.json",
        "release": f"{namespace}/release.json",
        "completion": f"{namespace}/completion.json",
    }

#: The three released source stores and the pins every committed B1/B5e
#: baseline fragment already carries for them. Read here, never rebuilt.
#: ``intent-boundaries-v1`` and NOT v2: the v2 re-pin read HARMFUL in cell
#: B4a (2026-09-19), so v1 is the admitted intent store.
#:
#: ``hash`` names WHICH digest a pin is, because the repository has two
#: conventions and reading one as the other is how a build "verifies" nothing:
#: a ``release.json`` is pinned by its FILE BYTES, while a
#: ``KnowledgeSnapshot`` store's ``snapshot.json`` is pinned by its
#: ``content_hash()`` (the canonical content digest
#: ``rails.knowledge_stores`` itself checks, and the one every committed
#: baseline fragment carries). ``scenario-hints-v1`` is not a
#: ``KnowledgeSnapshot`` at all and is pinned by file bytes on both files, the
#: convention ``rails.scenario_hints`` enforces.
SOURCE_STORES: dict[str, dict[str, object]] = {
    "intent-boundaries": {
        "release": {
            "relpath": "knowledge/slurp/semantic/intent-boundaries-v1/release.json",
            "root": "data",
            "sha256": "2e51c14b4f1c3a122968bc0fd7809523470aad80923ff87c1ce9992ed8d3beb4",
            "hash": "file",
        },
        "snapshot": {
            "relpath": "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json",
            "root": "data",
            "sha256": "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe",
            "hash": "snapshot-content",
        },
        "value_prefix": "intent-boundary:",
    },
    "slot-contracts": {
        "release": {
            "relpath": "knowledge/slurp/semantic/slot-contracts-v2/release.json",
            "root": "data",
            "sha256": "f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b",
            "hash": "file",
        },
        "snapshot": {
            "relpath": "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
            "root": "data",
            "sha256": "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec",
            "hash": "snapshot-content",
        },
        "value_prefix": "slot-contract:",
    },
    "scenario-hints": {
        "release": {
            "relpath": "knowledge/slurp/semantic/scenario-hints-v1/release.json",
            "root": "data",
            "sha256": "44716de634c788f72886f31762077052e5f109f479194e524f8dcef89f98103e",
            "hash": "file",
        },
        "snapshot": {
            "relpath": "knowledge/slurp/semantic/scenario-hints-v1/snapshot.json",
            "root": "data",
            "sha256": "079b2bf49404b5b5ee525c0f201faa8b022ae9f63781797ad4708da7826c98a1",
            "hash": "file",
        },
    },
}

#: The construction pool the ordering statistics are measured on, and the
#: identity this view binds itself to. Same pool E12, E14 and M1 all pin.
CONSTRUCTION_SPLIT_IDENTITY = (
    "67e53fb5f712c40b21b8b54b74e867e6da209f057c68cd40dd987aaa99b19875"
)
EXPECTED_CONSTRUCTION_UTTERANCES = 9354
EXPECTED_INTENTS = 60
EXPECTED_SLOT_CARDS = 54
EXPECTED_EDGES = 81

#: How a shared-section group is labelled: the kind's sigil, the section's
#: initial, and a one-based index by descending card count then text.
_LABEL_INITIALS = {"Uncertainty behavior": "U", "Missing behavior": "M"}
_KIND_SIGILS = {"intent": "I", "slot": "S"}


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_bytes(document: object) -> bytes:
    return json.dumps(
        document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(document: object) -> str:
    return hashlib.sha256(_canonical_bytes(document)).hexdigest()


def read_pinned(root: Path, pin: dict[str, object]) -> object:
    """One released file, refused unless it hashes to its declared pin.

    ``pin["hash"]`` says WHICH digest the pin is: ``"file"`` for a plain
    file-byte sha256, ``"snapshot-content"`` for the canonical
    ``KnowledgeSnapshot.content_hash()`` a store's ``snapshot.json`` is
    pinned by. Reading one as the other is how a build verifies nothing, so
    the convention is declared per pin rather than guessed.
    """

    path = Path(root) / str(pin["relpath"])
    if not path.is_file():
        raise SystemExit(f"REFUSED: {path} is not released")
    document = json.loads(path.read_text(encoding="utf-8"))
    convention = pin.get("hash", "file")
    if convention == "file":
        measured = _sha256_path(path)
    elif convention == "snapshot-content":
        from speech_aware_evidence_acquisition.rails.knowledge_stores import (
            KnowledgeSnapshot,
        )

        measured = KnowledgeSnapshot.from_frozen_json(document).content_hash()
    else:
        raise SystemExit(f"REFUSED: unknown pin hash convention {convention!r}")
    if measured != pin["sha256"]:
        raise SystemExit(
            f"REFUSED: {pin['relpath']} hashes to {measured} ({convention}), not the "
            f"pinned {pin['sha256']}; the knowledge index may only be built from the "
            "released store bytes its own release pins"
        )
    return document


def shared_groups(
    cards: dict[str, str], *, kind: str,
) -> tuple[list[SharedSection], dict[str, dict[str, str]]]:
    """The hoisted sections of one kind, labelled, plus each card's labels.

    Grouping is by the section's EXACT text, so a card whose section drifted
    by one character lands in its own group rather than being silently
    folded into another one.
    """

    labels: list[SharedSection] = []
    per_card: dict[str, dict[str, str]] = {name: {} for name in cards}
    for section_name in HOISTED_SECTIONS.get(kind, ()):
        counts: Counter[str] = Counter()
        for content in cards.values():
            found = [
                section for section in parse_card_sections(content)
                if section.name == section_name
            ]
            if len(found) != 1:
                raise SystemExit(
                    f"REFUSED: a {kind} card carries {len(found)} {section_name!r} "
                    "sections; the hoist addresses exactly one"
                )
            counts[found[0].text] += 1
        if len(counts) > MAX_HOISTED_DISTINCT:
            raise SystemExit(
                f"REFUSED: {kind} section {section_name!r} has {len(counts)} distinct "
                f"values over {len(cards)} cards, above the registered ceiling of "
                f"{MAX_HOISTED_DISTINCT}; hoisting a section with a value per card "
                "saves nothing and makes the index header a second copy of the store"
            )
        ordered = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
        initial = _LABEL_INITIALS[section_name]
        for index, (text, _count) in enumerate(ordered, start=1):
            label = f"{_KIND_SIGILS[kind]}{initial}-{index}"
            labels.append(
                SharedSection(label=label, kind=kind, section=section_name, text=text)
            )
            for name, content in cards.items():
                section = next(
                    part for part in parse_card_sections(content)
                    if part.name == section_name
                )
                if section.text == text:
                    per_card[name][text] = label
    return labels, per_card


def build_entries(
    *,
    intent_cards: dict[str, str],
    slot_cards: dict[str, str],
    hints: dict[str, dict],
    scenario_of: dict[str, str],
) -> tuple[list[IndexEntry], list[SharedSection]]:
    intent_labels, intent_per_card = shared_groups(intent_cards, kind="intent")
    slot_labels, slot_per_card = shared_groups(slot_cards, kind="slot")
    shared = intent_labels + slot_labels
    shared_text = {row.label: row.text for row in shared}
    entries: list[IndexEntry] = []

    for name in sorted(intent_cards):
        content = intent_cards[name]
        sections = parse_card_sections(content)
        by_name = {section.name: section for section in sections}
        hoisted_sections = [
            by_name[section_name]
            for section_name in HOISTED_SECTIONS["intent"]
            if section_name in by_name
        ]
        residue, hoisted = hoist_sections(
            content, sections=hoisted_sections, labels=intent_per_card[name]
        )
        if restore_card(residue, hoisted, shared_text) != content:
            raise SystemExit(
                f"REFUSED: the hoist of intent card {name!r} is not lossless"
            )
        entries.append(
            IndexEntry(
                entry_id=intent_id(name),
                kind="intent",
                group=scenario_of[name],
                rank=int(hints.get(name, {}).get("rows", 0)),
                l1={
                    section_name: section_body(by_name[section_name])
                    for section_name in ("Activation boundary", "Confusable exclusions")
                    if section_name in by_name
                },
                residue=residue,
                hoisted=hoisted,
            )
        )

    for name in sorted(slot_cards):
        content = slot_cards[name]
        sections = parse_card_sections(content)
        by_name = {section.name: section for section in sections}
        hoisted_sections = [
            by_name[section_name]
            for section_name in HOISTED_SECTIONS["slot"]
            if section_name in by_name
        ]
        residue, hoisted = hoist_sections(
            content, sections=hoisted_sections, labels=slot_per_card[name]
        )
        if restore_card(residue, hoisted, shared_text) != content:
            raise SystemExit(
                f"REFUSED: the hoist of slot card {name!r} is not lossless"
            )
        bindings = by_name.get("Intent bindings and semantic roles")
        entries.append(
            IndexEntry(
                entry_id=slot_id(name),
                kind="slot",
                group="",
                rank=len(labelled_bullets(bindings)) if bindings is not None else 0,
                l1={
                    section_name: section_body(by_name[section_name])
                    for section_name in ("Admissible formats", "Extraction cues")
                    if section_name in by_name
                },
                residue=residue,
                hoisted=hoisted,
            )
        )

    for name in sorted(hints):
        profile = hints[name]
        exclusions = {}
        if name in intent_cards:
            by_name = {
                section.name: section
                for section in parse_card_sections(intent_cards[name])
            }
            if "Confusable exclusions" in by_name:
                exclusions = labelled_bullets(by_name["Confusable exclusions"])
        for neighbour in profile.get("neighbours", ()):
            other = neighbour["intent"]
            statement = exclusions.get(other)
            if statement is None:
                # The released card states no exclusion for this construction
                # neighbour. The edge still exists -- the leakage measured it
                # -- so it states the construction fact instead of nothing:
                # the leakage rate and the cue words that favour this intent.
                cues = ", ".join(cue["word"] for cue in neighbour.get("cues", ()))
                statement = (
                    f"{neighbour['leaked']} of {neighbour['of_neighbours']} nearest "
                    f"construction neighbours of {name} carry {other}"
                    + (f"; cues favouring {name}: {cues}" if cues else "")
                )
            entries.append(
                IndexEntry(
                    entry_id=edge_id(name, other),
                    kind="edge",
                    group=scenario_of.get(name, ""),
                    rank=int(neighbour["leaked"]),
                    l1={"Confusable exclusions": statement},
                )
            )
    return entries, shared


def build_documents(root: Path, lock_path: Path) -> dict[str, object]:
    started = time.monotonic()
    stores = {
        name: {
            "release": read_pinned(root, spec["release"]),
            "snapshot": read_pinned(root, spec["snapshot"]),
        }
        for name, spec in SOURCE_STORES.items()
    }
    hints_snapshot = stores["scenario-hints"]["snapshot"]
    if hints_snapshot["source_split_identity_hash"] != CONSTRUCTION_SPLIT_IDENTITY:
        raise SystemExit(
            "REFUSED: the scenario-hints view binds construction identity "
            f"{hints_snapshot['source_split_identity_hash']}, not the registered "
            f"{CONSTRUCTION_SPLIT_IDENTITY}"
        )
    if hints_snapshot["construction_utterance_count"] != EXPECTED_CONSTRUCTION_UTTERANCES:
        raise SystemExit(
            "REFUSED: the construction pool is "
            f"{hints_snapshot['construction_utterance_count']} utterances, not the "
            f"registered {EXPECTED_CONSTRUCTION_UTTERANCES}"
        )
    hints = {row["intent"]: row for row in hints_snapshot["intents"]}

    lock = load_lock(lock_path)
    ontology = load_slurp_ontology(lock, root)
    scenario_of: dict[str, str] = {}
    for scenario, actions in ontology.actions_by_scenario.items():
        for action in actions:
            scenario_of[f"{scenario}_{action}"] = scenario
    legal_intents = tuple(sorted(scenario_of))
    legal_slot_types = tuple(sorted(ontology.entity_types))
    if len(legal_intents) != EXPECTED_INTENTS:
        raise SystemExit(
            f"REFUSED: the closed inventory names {len(legal_intents)} intents, not "
            f"the registered {EXPECTED_INTENTS}"
        )

    intent_cards = {
        value["value_id"][len("intent-boundary:"):]: value["content"]
        for value in stores["intent-boundaries"]["snapshot"]["values"]
    }
    slot_cards = {
        value["value_id"][len("slot-contract:"):]: value["content"]
        for value in stores["slot-contracts"]["snapshot"]["values"]
    }
    unknown_intents = sorted(set(intent_cards) - set(legal_intents))
    unknown_slots = sorted(set(slot_cards) - set(legal_slot_types))
    if unknown_intents or unknown_slots:
        raise SystemExit(
            "REFUSED: the stores card entries the closed inventory does not legalise: "
            f"intents {unknown_intents}, slots {unknown_slots}"
        )
    if len(intent_cards) != EXPECTED_INTENTS or len(slot_cards) != EXPECTED_SLOT_CARDS:
        raise SystemExit(
            f"REFUSED: {len(intent_cards)} intent cards and {len(slot_cards)} slot "
            f"cards, not the registered {EXPECTED_INTENTS} and {EXPECTED_SLOT_CARDS}"
        )

    entries, shared = build_entries(
        intent_cards=intent_cards, slot_cards=slot_cards, hints=hints,
        scenario_of=scenario_of,
    )
    edges = sum(1 for entry in entries if entry.kind == "edge")
    if edges != EXPECTED_EDGES:
        raise SystemExit(
            f"REFUSED: {edges} construction confusion pairs, not the registered "
            f"{EXPECTED_EDGES}"
        )
    snapshot = {
        "schema": KNOWLEDGE_INDEX_VIEW_SCHEMA,
        "view_id": KNOWLEDGE_INDEX_VIEW_ID,
        "builder_policy_id": KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
        "carrier": KNOWLEDGE_INDEX_CARRIER,
        "ordering": TAXONOMY_FREQUENCY_ORDERING,
        "source_split": "train",
        "source_split_identity_hash": CONSTRUCTION_SPLIT_IDENTITY,
        "construction_utterance_count": EXPECTED_CONSTRUCTION_UTTERANCES,
        "legal_intents": list(legal_intents),
        "legal_slot_types": list(legal_slot_types),
        "store_pins": {
            name: {
                "release": dict(spec["release"]),
                "snapshot": dict(spec["snapshot"]),
            }
            for name, spec in SOURCE_STORES.items()
        },
        "shared_sections": [row.as_json() for row in shared],
        "entries": [entry.as_json() for entry in entries],
    }
    return {
        "snapshot": snapshot,
        "timing_seconds": round(time.monotonic() - started, 3),
    }


def release_document(
    snapshot_sha256: str, snapshot: dict, *, twin: dict | None = None,
) -> dict[str, object]:
    view_id = str(snapshot["view_id"])
    document = {
        "schema": KNOWLEDGE_INDEX_RELEASE_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": KNOWLEDGE_INDEX_BUILDER_POLICY_ID,
        "carrier": snapshot["carrier"],
        "ordering": snapshot["ordering"],
        "snapshot": {"relpath": relpaths(view_id)["snapshot"], "root": "data"},
        "snapshot_sha256": snapshot_sha256,
        "source": {
            "carrier": snapshot["carrier"],
            "split": snapshot["source_split"],
            "construction_utterance_count": snapshot["construction_utterance_count"],
            "stores": snapshot["store_pins"],
        },
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
    }
    if twin is not None:
        # Item E24. The three fields ``rails.knowledge_index`` refuses a twin
        # without, in both directions: a twin view id whose release declares
        # no derangement is an unproven control, and a source view id whose
        # release declares one is a twin wearing the source's name.
        document["twin_of"] = dict(twin["twin_of"])
        document["derangement"] = dict(twin["derangement"])
        document["gold_read"] = False
    return document


def completion_document(
    snapshot_sha256: str, release_sha256: str, snapshot: dict, *,
    twin: dict | None = None,
) -> dict[str, object]:
    view_id = str(snapshot["view_id"])
    paths = relpaths(view_id)
    statement = (
        "Authored from three RELEASED construction stores, each read through its "
        "own declared sha256 pin, plus the closed contract inventory mined from "
        "train.jsonl alone. The ordering statistics are the construction row "
        "counts and leakage counts of the 9,354-utterance pool (governed TRAIN "
        "minus every utterance with a recording in TRAIN Fold A, Fold B or "
        "DEV-1000). The exemplar kind is not built at all. No gold of any "
        "evaluated row is read, keyed on or conditioned upon; no utterance id, "
        "no recording and no entity filler of an evaluated row appears."
    )
    document = {
        "schema": KNOWLEDGE_INDEX_COMPLETION_SCHEMA,
        "view_id": view_id,
        "generator": GENERATOR if twin is None else f"{GENERATOR} --twin-seed",
        "authority": AUTHORITY if twin is None else TWIN_AUTHORITY,
        "exposure_ledger_row": LEDGER_ROW if twin is None else TWIN_LEDGER_ROW,
        "execution_profile": "model-free-check",
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "encoder": 0, "tokenizer": 0},
        "release": {
            "relpath": paths["release"], "root": "data", "sha256": release_sha256,
        },
        "snapshot": {
            "relpath": paths["snapshot"], "root": "data", "sha256": snapshot_sha256,
        },
        "entry_counts": totals(snapshot),
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "statement": statement if twin is None else (
            statement + " This view is the DERANGEMENT TWIN of "
            f"{twin['twin_of']['view_id']}: the same entries, ids, groups, "
            "construction ranks, shared sections and rendered length, with the L1 "
            "lines and their L2 cards permuted across ids within each kind by a "
            "Sattolo derangement of the recorded seed (zero fixed points). It "
            "reads no gold and adds no knowledge: it destroys correspondence and "
            "holds form."
        ),
    }
    if twin is not None:
        document["twin_of"] = dict(twin["twin_of"])
        document["derangement"] = dict(twin["derangement"])
        document["gold_read"] = False
        document["form_match"] = dict(twin["form_match"])
    return document


def totals(snapshot: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in snapshot["entries"]:
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1
    counts["shared_sections"] = len(snapshot["shared_sections"])
    counts["legal_intents"] = len(snapshot["legal_intents"])
    counts["legal_slot_types"] = len(snapshot["legal_slot_types"])
    return counts


def rendered_index(snapshot: dict, *, render_label: str = "") -> str:
    """The snapshot rendered at the RECOMMENDED DEFAULTS, model-free.

    The same renderer a flight uses, over a table built from the snapshot
    document alone -- no pin, no data root, no contact of any kind.
    """

    view_id = str(snapshot["view_id"])
    table = table_from_snapshot(snapshot, render_label=render_label)
    return render_constant_index(table, default_index_plan(view_id))


def build_twin(source_snapshot: dict, *, seed: int) -> dict[str, object]:
    """The twin snapshot and its proofs, or a refusal. Writes nothing.

    T1 (zero fixed points) is proved inside :func:`derange_snapshot`, which
    refuses on a single one and checks by CONTENT rather than by position.
    T2 and T3 are proved here, and every one of them before a byte is
    written -- the source view's own hoist check sets that precedent.
    """

    twin_snapshot, derangement = derange_snapshot(source_snapshot, seed=seed)

    before = twin_line_multisets(source_snapshot)
    after = twin_line_multisets(twin_snapshot)
    if before != after:
        raise SystemExit(
            "REFUSED: the derangement changed a kind's multiset of L1 lines or L2 "
            "cards; a twin is a RE-ASSIGNMENT of the source's own lines, never a "
            "rewrite of them"
        )
    for field in ("id", "kind", "group", "rank"):
        if [row[field] for row in source_snapshot["entries"]] != [
            row[field] for row in twin_snapshot["entries"]
        ]:
            raise SystemExit(
                f"REFUSED: the derangement moved the entries' {field!r}; the ids, "
                "the taxonomy groups and the construction ranks are the ORDERING "
                "and must be held byte for byte"
            )
    if source_snapshot["shared_sections"] != twin_snapshot["shared_sections"]:
        raise SystemExit(
            "REFUSED: the derangement moved the hoisted shared sections; they are "
            "the index's own header and are shared by every entry"
        )

    source_text = rendered_index(source_snapshot)
    twin_text = rendered_index(
        twin_snapshot, render_label=str(source_snapshot["view_id"])
    )
    if len(source_text) != len(twin_text):
        raise SystemExit(
            f"REFUSED: the twin renders {len(twin_text)} characters against the "
            f"source's {len(source_text)}; a control that is not form-matched "
            "measures form, which is the very thing it exists to hold"
        )
    if source_text == twin_text:
        raise SystemExit(
            "REFUSED: the twin renders the SOURCE's text; nothing was deranged"
        )
    source_lines = source_text.split("\n")
    twin_lines = twin_text.split("\n")
    if len(source_lines) != len(twin_lines):
        raise SystemExit("REFUSED: the twin renders a different number of lines")
    moved = sum(
        1 for left, right in zip(source_lines, twin_lines) if left != right
    )
    return {
        "snapshot": twin_snapshot,
        "twin_of": {
            "view_id": str(source_snapshot["view_id"]),
            "snapshot_content_hash": _canonical_sha256(source_snapshot),
        },
        "derangement": derangement,
        "form_match": {
            "rendered_chars": len(twin_text),
            "source_rendered_chars": len(source_text),
            "rendered_lines": len(twin_lines),
            "reassigned_lines": moved,
            "rendered_sha256": hashlib.sha256(twin_text.encode("utf-8")).hexdigest(),
            "source_rendered_sha256": hashlib.sha256(
                source_text.encode("utf-8")
            ).hexdigest(),
            "granularity": "the recommended defaults (intent L1 / slot L1 / edge L0)",
        },
    }


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical_bytes(document)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-root", type=Path, required=True,
        help="where the three released files are written (the release job passes "
             "$SPEECHRL_DATA_DIR; every other run passes a scratch directory)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="verify the files under --out-root reproduce; write nothing",
    )
    parser.add_argument(
        "--twin-seed", type=int, default=None,
        help="build the E24 DERANGEMENT TWIN (slurp-knowledge-index-twin-v1) "
             "instead: the same entries, ids, ordering statistics, shared sections "
             "and rendered length, with only the L1 lines and their L2 cards "
             "permuted across ids within each kind by a Sattolo derangement of "
             "this seed (zero fixed points)",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--lock", type=Path, default=None,
        help="the umbrella datasets lock (default: the adjacent-checkout layout)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    lock_path = (
        Path(args.lock).resolve() if args.lock is not None
        else umbrella_lock_path(repo_root)
    )
    root = data_root()
    out_root = Path(args.out_root).resolve()
    built = build_documents(root, lock_path)
    snapshot = built["snapshot"]
    twin: dict | None = None
    if args.twin_seed is not None:
        # The twin is deranged from the SOURCE snapshot this build just
        # produced in memory -- never from a file on disk, so a twin can
        # never be a derangement of bytes nobody verified.
        twin = build_twin(snapshot, seed=int(args.twin_seed))
        snapshot = twin["snapshot"]
    counts = totals(snapshot)

    paths = relpaths(str(snapshot["view_id"]))
    snapshot_path = out_root / paths["snapshot"]
    release_path = out_root / paths["release"]
    completion_path = out_root / paths["completion"]

    if args.check:
        for path in (snapshot_path, release_path, completion_path):
            if not path.is_file():
                print(f"MISSING: {path} is not released")
                return 1
        if json.loads(snapshot_path.read_text(encoding="utf-8")) != snapshot:
            print("DIFFERS: the released snapshot is not what this build produces")
            return 1
        snapshot_sha256 = _sha256_path(snapshot_path)
        if json.loads(release_path.read_text(encoding="utf-8")) != release_document(
            snapshot_sha256, snapshot, twin=twin
        ):
            print("DIFFERS: the released release is not what this build produces")
            return 1
        release_sha256 = _sha256_path(release_path)
        if json.loads(
            completion_path.read_text(encoding="utf-8")
        ) != completion_document(
            snapshot_sha256, release_sha256, snapshot, twin=twin
        ):
            print("DIFFERS: the released completion is not what this build produces")
            return 1
        print(
            f"OK  entries={counts}  snapshot_sha256={snapshot_sha256[:16]}..."
        )
        if twin is not None:
            print(
                f"OK  twin seed={twin['derangement']['seed']} "
                f"fixed_points={twin['derangement']['fixed_points']} "
                f"permutation_sha256={twin['derangement']['permutation_sha256'][:16]}..."
            )
        return 0

    snapshot_sha256 = _write(snapshot_path, snapshot)
    release_sha256 = _write(
        release_path, release_document(snapshot_sha256, snapshot, twin=twin)
    )
    completion_sha256 = _write(
        completion_path,
        completion_document(snapshot_sha256, release_sha256, snapshot, twin=twin),
    )
    print(f"wrote {paths['snapshot']}  sha256={snapshot_sha256}")
    print(f"wrote {paths['release']}  sha256={release_sha256}")
    print(f"wrote {paths['completion']}  sha256={completion_sha256}")
    print(f"  content_hash={_canonical_sha256(snapshot)}")
    print(f"  entries={counts}")
    print(f"  timing_seconds={built['timing_seconds']}")
    if twin is not None:
        record = twin["derangement"]
        form = twin["form_match"]
        print(f"  twin_of={twin['twin_of']['view_id']}"
              f"@{twin['twin_of']['snapshot_content_hash']}")
        print(f"  derangement seed={record['seed']} kinds={record['kinds']} "
              f"fixed_points={record['fixed_points']}")
        print(f"  permutation_sha256={record['permutation_sha256']}")
        print(f"  T1 fixed points 0; T2 per-kind multiset of L1 lines and L2 cards "
              f"unchanged; T3 rendered {form['rendered_chars']} chars against the "
              f"source's {form['source_rendered_chars']}")
        print(f"  rendered_sha256={form['rendered_sha256']}  "
              f"source_rendered_sha256={form['source_rendered_sha256']}")
        print(f"  reassigned_lines={form['reassigned_lines']} of "
              f"{form['rendered_lines']}")
    print(
        "  NOTE: no release-pins registration file was written; registering the "
        "release is a separate, zero-contact job."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
