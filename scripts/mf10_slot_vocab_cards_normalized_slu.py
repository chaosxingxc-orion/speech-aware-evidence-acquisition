#!/usr/bin/env python3
"""MF-10 -- slot vocabulary cards and the normalized SLU scorer (model-free).

Opened by the owner's two questions of 2026-09-08:

  (a) ``date`` and ``time`` slots look like FORMAT knowledge that should be
      pre-loaded into the context -- the expected surface conventions -- while
      ``place`` needs PROPER-NOUN recognition; would statistically pre-loading
      that knowledge into context engineering pay?
  (b) refer to the Whisper-normalizer WER pattern and adjust the evaluation and
      the statistics accordingly.

Readiness note and boundary:
``docs/readiness/2026-09-08-mf10-slot-vocabulary-cards-and-normalized-slu-v1.md``.
Exposure row ``SAEA-SLURP-MF10-VOCAB-CARDS-NORMALIZED-SLU-V1``.

**Zero model, GPU, tool, embedding, network and audio-decode contacts.** The one
subprocess this script runs is the PINNED official SLURP ``evaluate.py`` in
``~/.venvs/slurp-official-eval`` -- the scorer, never a model. No server is
started, no model is loaded, no waveform is decoded, and NO TOKENIZER IS CALLED:
every token figure here is the stated whitespace-times-1.3 proxy of
``analysis.slurp_slot_vocabulary`` and is labelled as such.

Boundary enforced in code, not only in prose: no devel ``sentence`` string is
ever read; the DEV gold ENTITY ANNOTATIONS that do enter are read on the
SCORING side, exactly where the official scorer already reads them, and the
normalizer of question 3 applies to gold and prediction ALIKE, which is what
makes it a metric rather than a mechanism input; the DEV verbatim-coverage
statistic of question 1 is READ out of MF-9's committed receipt and never
recomputed from DEV text; the held-out ``test`` split is never named, loaded,
hashed or scored.

MF-9's own attribution engine is imported BY PATH and reused rather than
re-implemented (:func:`mf9_module`), so the two audits cannot disagree about
what "missing", "surface" or "spurious" mass means, and MF-9's identity anchors
run inside every read this script makes through it.

Subcommands
-----------
``classes``
    Question 1: the 55 slot types classified into CLOSED/FORMAT,
    OPEN/PROPER-NOUN and MIXED from three TRAIN-only statistics, and the FULL
    TRAIN vocabulary card of every closed type, priced per intent.
``views``
    Question 2: the KU-S3v knowledge views -- static cards for the closed
    types, KU-S3's speech-keyed retrieval for the open ones, and the combined
    view -- each priced by reachable SLU-F1, token cost, containment and its
    token-matched twin. PRICED, NOT PREREGISTERED.
``normalized``
    Question 3: the sealed comparator, KC-S1b and the value-projected KC-S1b
    re-scored under ``slurp-slu-f1-normalized-v1``, official beside normalized,
    per type, with paired CI90.
``ladder``
    Question 4: MF-9's improvement ladder re-priced under both scorers, and the
    admission primary for slot modules.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ROW_ID = "SAEA-SLURP-MF10-VOCAB-CARDS-NORMALIZED-SLU-V1"
RECEIPT_DIRNAME = "2026-09-08-mf10-slot-vocab-cards-normalized-slu"
DEFAULT_OUT_DIR = (
    REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition" / RECEIPT_DIRNAME
)

SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90

MF9_RECEIPT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-08-mf9-slurp-slot-gap-audit"
)
MF9_SCRIPT = REPO_ROOT / "scripts/mf9_slurp_slot_gap_audit.py"

#: The value-projection operating point MF-9 named: the ``normalized`` family at
#: tau = 0.20, which reached within 0.02 SLU-F1 of the arithmetic maximum with
#: the tightest interval in its table and ONE harm instead of seventeen.
PROJECTION_FAMILY = "normalized"
PROJECTION_TAU = 0.20

#: MF-9's own published numbers, hard-coded so every read below FAILS CLOSED if
#: the same sealed bytes stop reproducing them.
MF9_PUBLISHED = {
    "kc_s1b_slu_f1": 44.35,
    "kc_s1b_entities_strict": 31.37,
    "kc_s1b_word_f1": 41.58,
    "kc_s1b_char_f1": 47.51,
    "projected_slu_f1": 45.09,
    "ceiling_no_missing": 75.75,
    "ceiling_surface_perfect": 51.84,
    "corpus_true_positive_mass": 846.0,
    "corpus_loss_mass": 2123.085,
}
#: The sealed comparator's own published entity columns
#: (``docs/readiness/2026-09-05-slurp-slot-stage-kc-s1-v1-verdict.md`` section 1).
COMPARATOR_PUBLISHED = {
    "entities_strict": 21.91,
    "word_f1": 33.69,
    "char_f1": 38.20,
    "slu_f1": 35.80,
}

#: A handful of MF-9 value-headroom rows, checked before the classifier is
#: allowed to read the rest of that receipt.
MF9_VERBATIM_ANCHORS = {
    "date": 90.57,
    "transport_type": 100.0,
    "person": 57.14,
    "song_name": 0.0,
}

PAIRED_METRICS = (
    "slu_f1_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slot_f1_exact_f1",
)

#: KU-S3's own measured supplied volume, five typed blocks per row over its
#: first 30 DEV-1000 rows (that cell's preregistration section 1.4). Carried
#: rather than recomputed: this audit prices a view against it, it does not
#: re-measure the cell.
KU_S3_SUPPLIED_CHARS = {"min": 354, "p50": 422, "max": 570, "blocks_per_row": 5}

#: The serving geometry a SLURP packet cell flies at: a 65,536-token server
#: context divided into 8 slots. Stated so a card cost has something to be
#: measured against; the arm that actually flew (KC-S1b, KU-S3) used ``-np 4``
#: and a 16,384-token slot, and both figures are reported.
SLOT_TOKENS_NP8 = 8192
SLOT_TOKENS_NP4 = 16384


# ---------------------------------------------------------------------------
# Shared I/O -- MF-9's own helpers, imported rather than re-implemented
# ---------------------------------------------------------------------------


_MF9_CACHE: dict[str, object] = {}


def mf9_module():
    """MF-9's audit module, loaded BY PATH.

    Imported rather than copied so the loss attribution, the sealed-output
    reader, the population split, the canonical prediction envelope and the
    identity anchors are the SAME code in both audits. A path import is what
    the repository's own ``scripts/`` layout allows -- ``import scripts.x``
    collides with a top-level ``scripts`` package the shared venv installs.
    """

    cached = _MF9_CACHE.get("module")
    if cached is None:
        spec = importlib.util.spec_from_file_location("saea_mf9_audit", MF9_SCRIPT)
        if spec is None or spec.loader is None:
            raise SystemExit(f"cannot load MF-9's audit module from {MF9_SCRIPT}")
        cached = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cached)  # type: ignore[union-attr]
        _MF9_CACHE["module"] = cached
    return cached


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, document: object) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def contacts_block() -> dict[str, object]:
    return {
        "model": 0,
        "tool": 0,
        "embedding": 0,
        "network": 0,
        "audio_decode": 0,
        "gpu_hours": 0.0,
        "tokenizer": 0,
        "note": (
            "the only subprocess is the pinned official SLURP evaluate.py, which is "
            "the scorer and not a model; every token figure is the stated "
            "whitespace x 1.3 proxy and no tokenizer was called"
        ),
    }


def mf9_verbatim_table() -> dict[str, tuple[int, float]]:
    """``{entity type: (DEV gold mentions, verbatim share %)}``, READ from MF-9.

    Fail-closed against :data:`MF9_VERBATIM_ANCHORS` before the rest of the
    table is trusted. This is the ONLY place a DEV-derived statistic enters
    question 1, and it enters as a committed number rather than as a fresh read
    of DEV text.
    """

    document = read_json(MF9_RECEIPT_DIR / "value-headroom.json")
    table = {
        str(row["entity_type"]): (
            int(row["gold_mentions"]),
            float(row["verbatim_share_pct"]),
        )
        for row in document["per_entity_type"]
    }
    for entity_type, expected in MF9_VERBATIM_ANCHORS.items():
        actual = table.get(entity_type)
        if actual is None or abs(actual[1] - expected) > 1e-9:
            raise SystemExit(
                f"IDENTITY ANCHOR FAILED: MF-9 value-headroom {entity_type} verbatim "
                f"share is {actual}, the published note says {expected}"
            )
    return table


def mf9_loss_table() -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    """MF-9's per-type loss table and its corpus totals, checked against the
    two ceilings that audit published."""

    document = read_json(MF9_RECEIPT_DIR / "loss-decomposition.json")
    corpus = document["corpus"]
    per_type = {
        str(row["entity_type"]): {
            "gold_mentions": float(row["gold_mentions"]),
            "exact_matches": float(row["exact_matches"]),
            "surface_pairs": float(row["surface_pairs"]),
            "missing": float(row["missing"]),
            "spurious": float(row["spurious"]),
            "type_swaps": float(row["type_swaps"]),
            "missing_mass": float(row["missing_mass"]),
            "surface_mass": float(row["surface_mass"]),
            "spurious_mass": float(row["spurious_mass"]),
            "type_swap_mass": float(row["type_swap_mass"]),
            "total_mass": float(row["total_mass"]),
        }
        for row in document["per_entity_type"]
    }
    totals = {
        "true_positive_mass": float(corpus["true_positive_mass"]),
        "loss_mass": float(corpus["loss_mass"]),
        "slu_f1": float(corpus["slu_f1"]),
        "gold_mentions": float(corpus["gold_mentions"]),
        "predicted_mentions": float(corpus["predicted_mentions"]),
    }
    if abs(totals["true_positive_mass"] - MF9_PUBLISHED["corpus_true_positive_mass"]) > 1e-9:
        raise SystemExit("IDENTITY ANCHOR FAILED: MF-9 corpus TP mass moved")
    if abs(totals["loss_mass"] - MF9_PUBLISHED["corpus_loss_mass"]) > 1e-9:
        raise SystemExit("IDENTITY ANCHOR FAILED: MF-9 corpus loss mass moved")
    missing = sum(row["missing_mass"] for row in per_type.values())
    surface = sum(row["surface_mass"] for row in per_type.values())
    if abs(ceiling_slu_f1(totals, missing, surface * 0.0) - MF9_PUBLISHED["ceiling_no_missing"]) > 0.01:
        raise SystemExit("IDENTITY ANCHOR FAILED: the no-missing ceiling does not rebuild")
    if abs(ceiling_slu_f1(totals, 0.0, surface) - MF9_PUBLISHED["ceiling_surface_perfect"]) > 0.01:
        raise SystemExit("IDENTITY ANCHOR FAILED: the surface-perfect ceiling does not rebuild")
    return per_type, totals


def ceiling_slu_f1(
    totals: Mapping[str, float], missing_repaired: float, surface_repaired: float
) -> float:
    """SLU-F1 after moving ``missing_repaired`` mass from FN to TP and deleting
    ``surface_repaired`` mass outright.

    The official SLU-F1 is ``2 TP / (2 TP + FP + FN)`` summed over the word- and
    char-distance blocks, so a corpus's loss mass is exactly ``FP + FN`` and
    every counterfactual is this one line. Answering a missed gold mention
    exactly turns its 2.0 of FN mass into 2.0 of TP; writing a matched pair's
    surface form exactly removes the distance the metric charged and adds
    nothing, because the pair was already a true positive.
    """

    tp = totals["true_positive_mass"] + missing_repaired
    loss = totals["loss_mass"] - missing_repaired - surface_repaired
    return round(100.0 * (2.0 * tp) / (2.0 * tp + loss), 2)


# ---------------------------------------------------------------------------
# Question 1 -- the slot-type classes and the vocabulary cards
# ---------------------------------------------------------------------------


def command_classes(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
        CARD_HEADER,
        CLOSED_MAX_NOVELTY,
        CLOSED_MIN_VERBATIM_PCT,
        NOVELTY_MIN_MENTIONS,
        OPEN_MAX_VERBATIM_PCT,
        OPEN_MIN_NOVELTY,
        SLOT_CLASS_CLOSED,
        SLOT_CLASS_MIXED,
        SLOT_CLASS_OPEN,
        SLOT_CLASS_RULE_V1,
        SLOT_CLASS_RULE_V2,
        TOKEN_PROXY_FACTOR,
        build_vocabulary_card,
        classify_slot_types,
        price_intent_cards,
        render_card_set,
        token_proxy,
    )
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_ontology,
        load_slurp_train_material,
    )

    mf9 = mf9_module()
    lock, root, lock_path = mf9.resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train = load_slurp_train_material(lock, root)
    ontology = load_slurp_ontology(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for utterance in train:
        for entity in utterance.entities:
            entity_type = str(entity.type).strip()
            filler = str(entity.filler).strip()
            if entity_type and filler:
                counts[entity_type][filler] += 1
    train_counts = {name: dict(table) for name, table in sorted(counts.items())}

    verbatim = mf9_verbatim_table()
    declared = classify_slot_types(train_counts, verbatim, rule=SLOT_CLASS_RULE_V1)
    stats = classify_slot_types(train_counts, verbatim, rule=SLOT_CLASS_RULE_V2)
    by_class: dict[str, list[str]] = defaultdict(list)
    for stat in stats:
        by_class[stat.slot_class].append(stat.entity_type)
    declared_by_class: dict[str, list[str]] = defaultdict(list)
    for stat in declared:
        declared_by_class[stat.slot_class].append(stat.entity_type)
    declared_class_of = {stat.entity_type: stat.slot_class for stat in declared}
    reclassified = sorted(
        stat.entity_type
        for stat in stats
        if declared_class_of[stat.entity_type] != stat.slot_class
    )

    closed_types = tuple(by_class[SLOT_CLASS_CLOSED])
    cards = {
        name: build_vocabulary_card(name, train_counts[name]) for name in closed_types
    }

    block_types = {
        intent: profile.entity_types for intent, profile in schema.intents.items()
    }
    priced = price_intent_cards(block_types, cards)
    worst = max(priced, key=lambda cost: cost.token_proxy) if priced else None

    # The 42 KC-S1b rows that fell back to the FULL schema receive every type
    # the whole schema lists, so their card set is every card. That is the real
    # worst case and it is reported as its own row rather than folded in.
    full_block_types = sorted(
        {name for profile in schema.intents.values() for name in profile.entity_types}
    )
    full_cards = [cards[name] for name in full_block_types if name in cards]
    full_text = render_card_set(full_cards, header=CARD_HEADER)

    document = {
        "schema": "saea-slurp-mf10-type-classes-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": contacts_block(),
        "sources": {
            "umbrella_lock": str(lock_path),
            "train_material": "data.slurp.load_slurp_train_material (TRAIN only)",
            "intent_slot_schema": {
                "schema_id": schema.schema_id,
                "source_split": schema.source_split,
                "source_identity_hash": schema.source_identity_hash,
                "utterance_count": schema.utterance_count,
                "min_share": schema.min_share,
                "intents": len(schema.intents),
            },
            "dev_verbatim_share": (
                "READ from docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-08-mf9-slurp-slot-gap-audit/value-headroom.json; never "
                "recomputed from DEV text"
            ),
            "mf9_value_headroom_sha256": sha256_file(
                MF9_RECEIPT_DIR / "value-headroom.json"
            ),
        },
        "rules": {
            "operative": SLOT_CLASS_RULE_V2,
            SLOT_CLASS_RULE_V1: {
                "status": "DECLARED BEFORE THE READ, and reported because it is WRONG",
                "closed": (
                    f"novelty_ratio <= {CLOSED_MAX_NOVELTY} AND dev_verbatim_share_pct "
                    f">= {CLOSED_MIN_VERBATIM_PCT}"
                ),
                "open": (
                    f"novelty_ratio >= {OPEN_MIN_NOVELTY} OR dev_verbatim_share_pct "
                    f"<= {OPEN_MAX_VERBATIM_PCT}"
                ),
                "mixed": "everything else",
                "defect": (
                    "the novelty ratio is a RATE ESTIMATE bounded from below by "
                    "1 / mentions, so a rare type cannot have a low one: alarm_type "
                    "has four distinct surface forms and nine TRAIN mentions, and "
                    "this rule calls it open. The defect is in the statistic, not in "
                    "the corpus, and it is reported rather than repaired in silence"
                ),
            },
            SLOT_CLASS_RULE_V2: {
                "status": "OPERATIVE -- the views of question 2 are built on this",
                "closed": (
                    f"dev_verbatim_share_pct >= {CLOSED_MIN_VERBATIM_PCT} AND NOT "
                    f"(train_mentions >= {NOVELTY_MIN_MENTIONS} AND novelty_ratio >= "
                    f"{OPEN_MIN_NOVELTY})"
                ),
                "open": (
                    f"dev_verbatim_share_pct <= {OPEN_MAX_VERBATIM_PCT} OR "
                    f"(train_mentions >= {NOVELTY_MIN_MENTIONS} AND novelty_ratio >= "
                    f"{OPEN_MIN_NOVELTY})"
                ),
                "mixed": "everything else, and every type with no DEV gold to cover",
                "roles": {
                    "coverage": "decides -- a card pays exactly when DEV gold is inside it",
                    "reuse": (
                        "disqualifies, but only where the ratio is estimable "
                        f"(>= {NOVELTY_MIN_MENTIONS} TRAIN mentions)"
                    ),
                    "size": (
                        "checked, not capped: the enumerability question is asked of "
                        "the per-intent card SET against the arm's own measured "
                        "prompt headroom, below"
                    ),
                },
            },
            "novelty_ratio": "distinct TRAIN surface forms / TRAIN mentions",
        },
        "token_cost": {
            "proxy": f"ceil(whitespace tokens * {TOKEN_PROXY_FACTOR})",
            "is_a_tokenizer_measurement": False,
            "note": (
                "a cell that ever flies a card must measure its own envelope through "
                "the serving /apply-template + /tokenize seam, as KC-S1b did"
            ),
        },
        "corpus": {
            "train_utterances": len(train),
            "slot_types_in_train": len(train_counts),
            "slot_types_in_ontology": len(ontology.entity_types),
            "train_mentions": sum(
                sum(table.values()) for table in train_counts.values()
            ),
            "distinct_train_fillers": sum(len(table) for table in train_counts.values()),
        },
        "class_counts": {
            SLOT_CLASS_CLOSED: len(by_class[SLOT_CLASS_CLOSED]),
            SLOT_CLASS_MIXED: len(by_class[SLOT_CLASS_MIXED]),
            SLOT_CLASS_OPEN: len(by_class[SLOT_CLASS_OPEN]),
        },
        "classes": {
            SLOT_CLASS_CLOSED: sorted(by_class[SLOT_CLASS_CLOSED]),
            SLOT_CLASS_MIXED: sorted(by_class[SLOT_CLASS_MIXED]),
            SLOT_CLASS_OPEN: sorted(by_class[SLOT_CLASS_OPEN]),
        },
        "declared_rule_v1": {
            "class_counts": {
                SLOT_CLASS_CLOSED: len(declared_by_class[SLOT_CLASS_CLOSED]),
                SLOT_CLASS_MIXED: len(declared_by_class[SLOT_CLASS_MIXED]),
                SLOT_CLASS_OPEN: len(declared_by_class[SLOT_CLASS_OPEN]),
            },
            "classes": {
                SLOT_CLASS_CLOSED: sorted(declared_by_class[SLOT_CLASS_CLOSED]),
                SLOT_CLASS_MIXED: sorted(declared_by_class[SLOT_CLASS_MIXED]),
                SLOT_CLASS_OPEN: sorted(declared_by_class[SLOT_CLASS_OPEN]),
            },
            "types_the_operative_rule_moves": reclassified,
            "per_entity_type": [stat.as_json() for stat in declared],
        },
        "per_entity_type": [stat.as_json() for stat in stats],
        "cards": {
            "header": CARD_HEADER,
            "header_token_proxy": token_proxy(CARD_HEADER),
            "carded_types": len(cards),
            "total_token_proxy": sum(card.token_proxy for card in cards.values()),
            "total_forms": sum(len(card.forms) for card in cards.values()),
            "per_type": [cards[name].as_json() for name in sorted(cards)],
        },
        "per_intent_card_cost": [cost.as_json() for cost in priced],
        "budget_check": {
            "what_it_is": (
                "the enumerability condition the v2 rule declines to cap per type: "
                "the WORST per-intent card set against the arm's own measured "
                "headroom. KC-S1b's measured worst prompt envelope is 10,006 tokens "
                "in a 16,384-token slot at -np 4 (its own prompt-fit receipt and the "
                "KU-S3 preregistration section 5), so a card set has 6,378 tokens to "
                "live in"
            ),
            "kc_s1b_worst_envelope_tokens": 10006,
            "slot_tokens_np4": SLOT_TOKENS_NP4,
            "headroom_tokens": SLOT_TOKENS_NP4 - 10006,
            "worst_intent_card_proxy": worst.token_proxy if worst is not None else 0,
            "fits": bool(
                worst is not None and worst.token_proxy <= SLOT_TOKENS_NP4 - 10006
            ),
            "margin_tokens": (
                SLOT_TOKENS_NP4 - 10006 - worst.token_proxy if worst is not None else 0
            ),
        },
        "worst_intent": (
            {
                **worst.as_json(),
                "slot_tokens_np8": SLOT_TOKENS_NP8,
                "share_of_np8_slot_pct": round(
                    100.0 * worst.token_proxy / SLOT_TOKENS_NP8, 2
                ),
                "slot_tokens_np4": SLOT_TOKENS_NP4,
                "share_of_np4_slot_pct": round(
                    100.0 * worst.token_proxy / SLOT_TOKENS_NP4, 2
                ),
            }
            if worst is not None
            else None
        ),
        "full_schema_fallback_card_set": {
            "what_it_is": (
                "the 42 KC-S1b rows whose block was the FULL schema would receive "
                "every card; this is the real worst case and is reported separately"
            ),
            "carded_types": len(full_cards),
            "token_proxy": token_proxy(full_text),
            "chars": len(full_text),
            "share_of_np8_slot_pct": round(
                100.0 * token_proxy(full_text) / SLOT_TOKENS_NP8, 2
            ),
            "share_of_np4_slot_pct": round(
                100.0 * token_proxy(full_text) / SLOT_TOKENS_NP4, 2
            ),
        },
    }
    path = write_json(out_dir / "type-classes.json", document)
    print(f"wrote {path}")
    print(
        f"  operative v2 classes: {document['class_counts']} over "
        f"{document['corpus']['slot_types_in_train']} TRAIN types"
    )
    print(f"  declared v1 classes: {document['declared_rule_v1']['class_counts']}")
    print(f"  types v2 moves: {len(reclassified)}")
    print(
        f"  budget: worst intent {document['budget_check']['worst_intent_card_proxy']} "
        f"proxy tokens in {document['budget_check']['headroom_tokens']} of headroom, "
        f"fits={document['budget_check']['fits']}"
    )
    if worst is not None:
        print(
            f"  worst intent card set: {worst.intent} at {worst.token_proxy} proxy "
            f"tokens ({document['worst_intent']['share_of_np8_slot_pct']} % of an "
            f"8,192 slot)"
        )
    print(
        "  full-schema fallback card set: "
        f"{document['full_schema_fallback_card_set']['token_proxy']} proxy tokens"
    )
    return 0


# ---------------------------------------------------------------------------
# Question 2 -- the knowledge views, priced
# ---------------------------------------------------------------------------


def _view_ceiling(
    totals: Mapping[str, float],
    per_type: Mapping[str, Mapping[str, float]],
    types: Sequence[str],
    verbatim: Mapping[str, tuple[int, float]],
    *,
    vocabulary_limited: bool,
) -> dict[str, object]:
    """What a PERFECT reader of a card set over ``types`` could reach.

    ``vocabulary_limited`` is the honest version and the one this note leads
    with: a card can only supply a value TRAIN actually carries, so the mass it
    can repair is scaled by the share of that type's DEV gold that occurs
    verbatim in TRAIN -- MF-9's own measurement, read from its receipt. The
    unrestricted version assumes every mention of the type is reachable and is
    reported beside it so the gap between the two is visible.

    Both are ORACLES in MF-9's sense: they assume the model answers every slot
    the card covers, exactly. A card supplies a vocabulary, not a decision, and
    nothing here claims a cell would reach this.
    """

    missing = 0.0
    surface = 0.0
    covered_mentions = 0.0
    for name in types:
        row = per_type.get(name)
        if row is None:
            continue
        scale = 1.0
        if vocabulary_limited:
            share = verbatim.get(name, (0, 0.0))[1]
            scale = float(share) / 100.0
        missing += row["missing_mass"] * scale
        surface += row["surface_mass"] * scale
        covered_mentions += row["missing"] * scale
    return {
        "types": len(list(types)),
        "missing_mass_repaired": round(missing, 3),
        "surface_mass_repaired": round(surface, 3),
        "gold_mentions_newly_answered": round(covered_mentions, 1),
        "slu_f1": ceiling_slu_f1(totals, missing, surface),
        "gain": round(ceiling_slu_f1(totals, missing, surface) - totals["slu_f1"], 2),
        "vocabulary_limited": vocabulary_limited,
    }


def _retrieval_bound(
    totals: Mapping[str, float],
    per_type: Mapping[str, Mapping[str, float]],
    retrieved: Mapping[str, int],
    types: Sequence[str],
) -> dict[str, object]:
    """An UPPER BOUND on what KU-S3's retrieved top-5 could repair over
    ``types``, computed from MF-9's committed per-type counts alone.

    ``in_retrieved_top_k`` counts the DEV gold mentions of a type that appear
    as a ``(type, filler)`` pair inside the row's retrieved union. The missing
    mentions of that type are a SUBSET of its gold mentions, so retrieval can
    repair at most ``min(missing, in_retrieved)`` of them; whatever retrieved
    capacity is left over can at best repair surface-form pairs. Both steps are
    upper bounds and are stated as such -- this is deliberately not a
    re-measurement of the retrieval, which MF-9 already published, and its
    global version is checked against MF-9's own measured oracle below.
    """

    missing_mass = 0.0
    surface_mass = 0.0
    repaired_missing = 0.0
    for name in types:
        row = per_type.get(name)
        if row is None:
            continue
        capacity = float(retrieved.get(name, 0))
        take_missing = min(row["missing"], capacity)
        repaired_missing += take_missing
        missing_mass += 2.0 * take_missing
        left = max(0.0, capacity - take_missing)
        pairs = row["surface_pairs"]
        if pairs > 0 and left > 0:
            surface_mass += row["surface_mass"] * (min(pairs, left) / pairs)
    return {
        "types": len(list(types)),
        "missing_mass_repaired": round(missing_mass, 3),
        "surface_mass_repaired": round(surface_mass, 3),
        "gold_mentions_newly_answered": round(repaired_missing, 1),
        "slu_f1": ceiling_slu_f1(totals, missing_mass, surface_mass),
        "gain": round(
            ceiling_slu_f1(totals, missing_mass, surface_mass) - totals["slu_f1"], 2
        ),
        "is_an_upper_bound": True,
    }


def command_views(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
        CARD_HEADER,
        CONTAINMENT_MIN_LENGTH,
        SLOT_CLASS_CLOSED,
        SLOT_CLASS_MIXED,
        SLOT_CLASS_OPEN,
        build_vocabulary_card,
        containment_collisions,
        derange_card_mapping,
        price_intent_cards,
        render_card_set,
        token_proxy,
        twin_pool_types,
    )
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_train_material,
        render_slurp_intent_slot_schema,
    )

    mf9 = mf9_module()
    lock, root, lock_path = mf9.resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    classes_path = out_dir / "type-classes.json"
    if not classes_path.is_file():
        raise SystemExit(f"run the `classes` subcommand first: {classes_path} is missing")
    classes = read_json(classes_path)
    closed = tuple(classes["classes"][SLOT_CLASS_CLOSED])
    mixed = tuple(classes["classes"][SLOT_CLASS_MIXED])
    open_types = tuple(classes["classes"][SLOT_CLASS_OPEN])

    per_type, totals = mf9_loss_table()
    verbatim = mf9_verbatim_table()
    headroom = read_json(MF9_RECEIPT_DIR / "value-headroom.json")
    retrieved = {
        str(row["entity_type"]): int(row["in_retrieved_top_k"])
        for row in headroom["per_entity_type"]
    }
    measured_retrieval_oracle = float(
        headroom["retrieved_top_k"]["oracle_ceiling"]["slu_f1"]
    )

    train = load_slurp_train_material(lock, root)
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for utterance in train:
        for entity in utterance.entities:
            entity_type = str(entity.type).strip()
            filler = str(entity.filler).strip()
            if entity_type and filler:
                counts[entity_type][filler] += 1
    cards = {
        name: build_vocabulary_card(name, dict(counts[name]))
        for name in closed
        if counts.get(name)
    }

    schema = load_slurp_intent_slot_schema(lock, root)
    block_types = {
        intent: profile.entity_types for intent, profile in schema.intents.items()
    }
    priced = price_intent_cards(block_types, cards)

    # --- the twin, token-matched by construction --------------------------
    twin_map = derange_card_mapping(block_types, cards)
    twin_priced = price_intent_cards(block_types, cards, remap=twin_map)
    pooled = twin_pool_types(block_types, cards)
    arm_by_intent = {cost.intent: cost for cost in priced}
    twin_by_intent = {cost.intent: cost for cost in twin_priced}
    rotatable = sorted(
        intent for intent, mapping in twin_map.items() if len(mapping) >= 2
    )
    volume_mismatches = sorted(
        intent
        for intent in rotatable
        if arm_by_intent[intent].char_count != twin_by_intent[intent].char_count
    )
    pooled_intents = sorted(
        intent for intent, mapping in twin_map.items() if len(mapping) == 1
    )
    pooled_volume_delta = {
        intent: twin_by_intent[intent].char_count - arm_by_intent[intent].char_count
        for intent in pooled_intents
        if twin_by_intent[intent].char_count != arm_by_intent[intent].char_count
    }

    # --- containment, on the instruction the cell would actually send ------
    roster = mf9.roster_sample_ids(REPO_ROOT / mf9.DEV1000_CONFIG)
    states = mf9.read_sealed_outputs(
        mf9.sealed_outputs_path(root, mf9.CLOSED_LIST_RUN, mf9.CLOSED_LIST_ATTEMPT)
    )
    fit_document = read_json(REPO_ROOT / mf9.KC_S1B_PROMPT_FIT)
    fit_rows = {
        row["sample_id"]: row
        for row in fit_document["rows"]
        if row["cell_id"] == "kc-s1b"
    }
    directive = (REPO_ROOT / "configs/probes/slurp_phase_slots.txt").read_text(
        encoding="utf-8"
    )
    # The RESOLUTION variant: the same per-intent schema block with its own five
    # example fillers dropped. `examples_per_type=0` is a parameter the loader
    # already takes, so this is the schema block the study would send if the
    # card became the one place a filler is written, not a new renderer.
    schema_no_examples = load_slurp_intent_slot_schema(lock, root, examples_per_type=0)
    full_block_text = render_slurp_intent_slot_schema(schema)
    full_block_no_examples = render_slurp_intent_slot_schema(schema_no_examples)
    block_text_cache: dict[str, str] = {}
    block_no_examples_cache: dict[str, str] = {}
    card_payloads = sorted(
        {form for card in cards.values() for form, _count in card.forms}
    )
    checked_payloads = [
        payload for payload in card_payloads if len(payload) >= CONTAINMENT_MIN_LENGTH
    ]
    directive_hits = containment_collisions(checked_payloads, directive)
    surfaces = {
        "directive": 0,
        "sealed_state": 0,
        "schema_block": 0,
        "schema_block_without_examples": 0,
        "whole_instruction": 0,
        "whole_instruction_without_schema_examples": 0,
    }
    collision_examples: dict[str, int] = {}
    residual_examples: dict[str, int] = {}
    schema_example_overlap = 0
    for sample_id in roster:
        fit = fit_rows[sample_id]
        if bool(fit["schema_full_fallback"]):
            block, block_bare = full_block_text, full_block_no_examples
        else:
            intent = str(fit["schema_block_intent"])
            block = block_text_cache.get(intent)
            if block is None:
                block = render_slurp_intent_slot_schema(schema, intents=(intent,))
                block_text_cache[intent] = block
            block_bare = block_no_examples_cache.get(intent)
            if block_bare is None:
                block_bare = render_slurp_intent_slot_schema(
                    schema_no_examples, intents=(intent,)
                )
                block_no_examples_cache[intent] = block_bare
        state = states[sample_id]
        instruction = f"{directive}\n{state}\n{block}"
        instruction_bare = f"{directive}\n{state}\n{block_bare}"
        if directive_hits:
            surfaces["directive"] += 1
        if containment_collisions(checked_payloads, state):
            surfaces["sealed_state"] += 1
        if containment_collisions(checked_payloads, block):
            surfaces["schema_block"] += 1
        if containment_collisions(checked_payloads, block_bare):
            surfaces["schema_block_without_examples"] += 1
        hits = containment_collisions(checked_payloads, instruction)
        if hits:
            surfaces["whole_instruction"] += 1
            for hit in hits:
                collision_examples[hit] = collision_examples.get(hit, 0) + 1
        residual = containment_collisions(checked_payloads, instruction_bare)
        if residual:
            surfaces["whole_instruction_without_schema_examples"] += 1
            for hit in residual:
                residual_examples[hit] = residual_examples.get(hit, 0) + 1
    rows_with_collisions = surfaces["whole_instruction"]
    # A residual collision is a LEAK only if it is not a substring of the block's
    # own structural vocabulary: the schema prints entity TYPE names and intent
    # names, so a card form like `audiobook` matches inside `audiobook_name` and
    # `takeaway` inside `takeaway_order`. That is a false positive of a raw
    # substring rule, the same class MF-8 and KU-S3 already recorded, and it is
    # counted rather than argued.
    structural = " ".join(
        sorted(
            {name for profile in schema.intents.values() for name in profile.entity_types}
            | set(schema.intents)
        )
    )
    structural = f"{structural} {structural.replace('_', ' ')}"
    structural_residual = sorted(
        form for form in residual_examples if form in structural
    )
    # How much of that is the schema block's own five example fillers, which a
    # card would restate: the number that decides how the view must be rendered.
    for intent, profile in schema.intents.items():
        for entity_type in profile.entity_types:
            if entity_type not in cards:
                continue
            for filler in profile.fillers.get(entity_type, ()):
                if len(filler) >= CONTAINMENT_MIN_LENGTH:
                    schema_example_overlap += 1

    # --- the views, priced -------------------------------------------------
    card_set_text = render_card_set(
        [cards[name] for name in sorted(cards)], header=CARD_HEADER
    )
    ku_s3_token_proxy = int(
        round(KU_S3_SUPPLIED_CHARS["p50"] / 4.0)
    )  # 4 chars/token, the same rough proxy KU-S3's own prompt-fit used
    worst_intent_cost = max(cost.token_proxy for cost in priced) if priced else 0

    global_bound = _retrieval_bound(
        totals, per_type, retrieved, sorted(per_type)
    )
    bound_is_consistent = global_bound["slu_f1"] >= measured_retrieval_oracle - 0.01

    views = {
        "KU-S3v-cards-closed": {
            "what_it_is": (
                "a per-intent STATIC slot value card for the CLOSED/FORMAT types, "
                "rendered as typed content beside the schema block: the whole TRAIN "
                "vocabulary with counts, deterministic, no retrieval, no query, no "
                "vector and no echo risk from a retrieved neighbour"
            ),
            "types_supplied": len(cards),
            "reachable_slu_f1_vocabulary_limited": _view_ceiling(
                totals, per_type, closed, verbatim, vocabulary_limited=True
            ),
            "reachable_slu_f1_unrestricted": _view_ceiling(
                totals, per_type, closed, verbatim, vocabulary_limited=False
            ),
            "token_cost_proxy": {
                "worst_intent": worst_intent_cost,
                "median_intent": sorted(cost.token_proxy for cost in priced)[
                    len(priced) // 2
                ]
                if priced
                else 0,
                "all_cards_at_once": token_proxy(card_set_text),
            },
            "retrieval_contacts": 0,
            "seed_gpu_hours": 0.0,
        },
        "KU-S3-retrieval-open": {
            "what_it_is": (
                "KU-S3 exactly as preregistered -- the speech-keyed top-5 TRAIN "
                "neighbour fillers as typed content -- restricted here to the "
                "OPEN/PROPER-NOUN types, which are the ones a card cannot enumerate"
            ),
            "types_supplied": len(open_types),
            "reachable_slu_f1_bound": _retrieval_bound(
                totals, per_type, retrieved, open_types
            ),
            "token_cost_proxy": {
                "per_row": ku_s3_token_proxy,
                "measured_chars_per_row": KU_S3_SUPPLIED_CHARS,
            },
            "retrieval_contacts": 0,
            "seed_gpu_hours": 0.85,
        },
        "combined-cards-plus-retrieval": {
            "what_it_is": (
                "cards for the CLOSED types and the retrieved top-5 for the OPEN "
                "ones, in one supplied block"
            ),
            "types_supplied": len(cards) + len(open_types),
            "reachable_slu_f1_bound": {
                "note": (
                    "the two halves act on DISJOINT type sets, so their repaired "
                    "masses add exactly; the result is still an oracle bound"
                ),
                **_combined_bound(
                    totals, per_type, retrieved, verbatim, closed, open_types
                ),
            },
            "token_cost_proxy": {
                "worst_intent": worst_intent_cost + ku_s3_token_proxy,
            },
            "retrieval_contacts": 0,
            "seed_gpu_hours": 0.85,
        },
    }

    document = {
        "schema": "saea-slurp-mf10-knowledge-views-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PRICED, NOT PREREGISTERED. Admits nothing, promotes nothing.",
        "contacts": contacts_block(),
        "sources": {
            "umbrella_lock": str(lock_path),
            "mf9_loss_decomposition_sha256": sha256_file(
                MF9_RECEIPT_DIR / "loss-decomposition.json"
            ),
            "mf9_value_headroom_sha256": sha256_file(
                MF9_RECEIPT_DIR / "value-headroom.json"
            ),
            "type_classes_sha256": sha256_file(classes_path),
            "sealed_closed_list_states": str(
                mf9.sealed_outputs_path(root, mf9.CLOSED_LIST_RUN, mf9.CLOSED_LIST_ATTEMPT)
            ),
            "kc_s1b_prompt_fit": mf9.KC_S1B_PROMPT_FIT,
        },
        "baseline": {
            "arm": mf9.KC_S1B_RUN,
            "slu_f1": totals["slu_f1"],
            "true_positive_mass": totals["true_positive_mass"],
            "loss_mass": totals["loss_mass"],
        },
        "class_sizes": {
            SLOT_CLASS_CLOSED: len(closed),
            SLOT_CLASS_MIXED: len(mixed),
            SLOT_CLASS_OPEN: len(open_types),
        },
        "views": views,
        "retrieval_bound_consistency": {
            "what_it_is": (
                "the global version of the retrieval upper bound, checked against "
                "MF-9's own MEASURED KU-S3 oracle: a bound that came out below the "
                "measured oracle would be wrong"
            ),
            "global_upper_bound_slu_f1": global_bound["slu_f1"],
            "mf9_measured_oracle_slu_f1": measured_retrieval_oracle,
            "bound_holds": bool(bound_is_consistent),
        },
        "containment": {
            "rule": (
                "the raw-substring rule rails.runner."
                "_assert_agent_control_excludes_knowledge_payloads applies to a bound "
                "snapshot, at its own 8-character floor, run here BEFORE anything is "
                "built"
            ),
            "instruction": "directive + sealed closed-list state + per-intent schema block",
            "rows_checked": len(roster),
            "card_forms_total": len(card_payloads),
            "card_forms_at_or_above_floor": len(checked_payloads),
            "rows_with_a_collision": rows_with_collisions,
            "distinct_colliding_forms": len(collision_examples),
            "top_collisions": dict(
                sorted(collision_examples.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
            ),
            "containment_decomposition_rows": surfaces,
            "schema_block_example_fillers_a_card_would_restate": schema_example_overlap,
            "resolution": {
                "what_it_is": (
                    "the SAME per-intent schema block with its five example fillers "
                    "dropped (`examples_per_type=0`, a parameter the loader already "
                    "takes), so the card becomes the ONE place a filler is written "
                    "instead of the second place"
                ),
                "rows_still_colliding": surfaces[
                    "whole_instruction_without_schema_examples"
                ],
                "distinct_forms_still_colliding": len(residual_examples),
                "top_residual_collisions": dict(
                    sorted(residual_examples.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
                ),
                "residual_forms_that_are_substrings_of_a_type_or_intent_name": (
                    structural_residual
                ),
                "note": (
                    "what survives the resolution is the SEALED STATE, which carries "
                    "the previous phase's own predicted fillers -- a row whose intent "
                    "response happened to name a value the card also carries. That is "
                    "a property of the two-contact shape, not of the card, and it is "
                    "the same false-positive class MF-8 and KU-S3 already recorded "
                    "for a raw-substring rule over one- and two-word English"
                ),
            },
            "verdict": (
                "CLEAN -- no card form of 8 characters or more occurs in the "
                "instruction"
                if rows_with_collisions == 0
                else "COLLIDES AS SENT -- a card cannot be shipped beside a schema "
                "block that already prints example fillers; the view must send the "
                "block WITHOUT its examples, and the residual is reported above"
            ),
        },
        "twin": {
            "rule": (
                "saea-mf10-within-intent-card-derangement-v1: an intent's carded "
                "types are rotated among THEMSELVES, so that intent's block holds "
                "the same MULTISET of vocabularies and is token-matched by "
                "construction rather than by a cap. The mapping is per intent for "
                "exactly this reason -- one global map would carry an intent's "
                "rotation into another intent that shares a type and break the "
                "match. An intent listing a single carded type cannot rotate in "
                "place, and neither can a carded type no block lists at all; both "
                "are pooled and rotated among themselves, as KU-S3's derangement "
                "does for its singleton scenario buckets, and the volume difference "
                "that leaves is reported as a covariate rather than claimed as a "
                "match"
            ),
            "mapping_per_intent": twin_map,
            "types_keeping_their_own_vocabulary": 0,
            "intents_rotating_in_place": len(rotatable),
            "intents_whose_volume_differs_from_the_arm": volume_mismatches,
            "token_matched_by_construction_on_rotating_intents": not volume_mismatches,
            "pooled_types": list(pooled),
            "pooled_intents": pooled_intents,
            "pooled_intent_volume_delta_chars": pooled_volume_delta,
        },
        "what_this_is_not": (
            "no cell is preregistered, no roster is opened, no owner decision is "
            "anticipated and every reachable number here is an ORACLE: it assumes a "
            "perfect reader of the supplied block. A card supplies a vocabulary, "
            "never a decision, and cannot make the core answer a slot it did not hear"
        ),
    }
    path = write_json(out_dir / "knowledge-views.json", document)
    print(f"wrote {path}")
    for name, view in views.items():
        reach = (
            view.get("reachable_slu_f1_vocabulary_limited")
            or view.get("reachable_slu_f1_bound")
            or {}
        )
        print(f"  {name}: reachable SLU-F1 {reach.get('slu_f1')} ({reach.get('gain')})")
    print(
        f"  containment: {rows_with_collisions} of {len(roster)} rows collide as "
        f"sent ({schema_example_overlap} schema example fillers a card restates); "
        f"{surfaces['whole_instruction_without_schema_examples']} still collide "
        "with the examples dropped"
    )
    print(
        f"  twin: {len(rotatable)} intents rotate in place, "
        f"{len(volume_mismatches)} of them differ in volume; "
        f"{len(pooled_intents)} pooled intents, "
        f"{len(pooled_volume_delta)} of them differ"
    )
    return 0


def _combined_bound(
    totals: Mapping[str, float],
    per_type: Mapping[str, Mapping[str, float]],
    retrieved: Mapping[str, int],
    verbatim: Mapping[str, tuple[int, float]],
    closed: Sequence[str],
    open_types: Sequence[str],
) -> dict[str, object]:
    """Cards on the closed half plus retrieval on the open half.

    The two halves act on DISJOINT type sets, so the masses they repair add
    exactly and the combined ceiling is one call to :func:`ceiling_slu_f1`.
    """

    card = _view_ceiling(totals, per_type, closed, verbatim, vocabulary_limited=True)
    retrieval = _retrieval_bound(totals, per_type, retrieved, open_types)
    missing = float(card["missing_mass_repaired"]) + float(
        retrieval["missing_mass_repaired"]
    )
    surface = float(card["surface_mass_repaired"]) + float(
        retrieval["surface_mass_repaired"]
    )
    return {
        "missing_mass_repaired": round(missing, 3),
        "surface_mass_repaired": round(surface, 3),
        "slu_f1": ceiling_slu_f1(totals, missing, surface),
        "gain": round(ceiling_slu_f1(totals, missing, surface) - totals["slu_f1"], 2),
        "is_an_upper_bound": True,
    }


# ---------------------------------------------------------------------------
# Question 3 -- the normalized SLU scorer against the official one
# ---------------------------------------------------------------------------


def _per_type_strict(gold_by_id, parsed, roster, normalize=None) -> dict[str, dict]:
    """Per-type exact ``{type, filler}`` TP/FP/FN over the whole corpus."""

    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    table: dict[str, dict[str, float]] = defaultdict(
        lambda: {"tp": 0.0, "fp": 0.0, "fn": 0.0, "gold": 0.0}
    )
    for sample_id in roster:
        gold_entities = list(gold_by_id[sample_id].entities)
        predicted = list(parsed[sample_id][2])
        if normalize is not None:
            gold_entities = list(normalize(gold_entities))
            predicted = list(normalize(predicted))
        remaining = list(gold_entities)
        for entity in gold_entities:
            table[entity.type]["gold"] += 1.0
        for entity in predicted:
            key = SlotEntity(type=entity.type, filler=entity.filler)
            if key in remaining:
                table[entity.type]["tp"] += 1.0
                remaining.remove(key)
            else:
                table[entity.type]["fp"] += 1.0
        for entity in remaining:
            table[entity.type]["fn"] += 1.0
    mf9 = mf9_module()
    return {
        entity_type: {
            **{key: value for key, value in row.items()},
            "f1_pct": round(100.0 * mf9._f1(row["tp"], row["fp"], row["fn"]), 2),
        }
        for entity_type, row in sorted(table.items())
    }


def command_normalized(args: argparse.Namespace) -> int:
    from concurrent.futures import ThreadPoolExecutor

    from speech_aware_evidence_acquisition.analysis.paired import paired_contrast
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        score_slurp_outputs_slu_normalized,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        SlotEntity,
        parse_slu_response,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_slot_normalizer import (
        SLURP_SLOT_NORMALIZER_ID,
        SLURP_SLOT_NORMALIZER_RULES,
        SLURP_SLU_NORMALIZED_SCORER_ID,
        load_slot_normalizer_inventory,
        normalize_slot_entities,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
        SLURP_VALUE_PROJECTION_ID,
        VALUE_BRANCH_NO_INVENTORY,
        VALUE_BRANCH_TOO_FAR,
        load_value_projection_inventory,
        normalize_filler,
        project_slu_entities,
    )

    mf9 = mf9_module()
    lock, root, lock_path = mf9.resolve_lock_and_root()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = mf9.roster_sample_ids(REPO_ROOT / mf9.DEV1000_CONFIG)
    pops = mf9.populations(roster)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    kc_texts = mf9.read_sealed_outputs(
        mf9.sealed_outputs_path(root, mf9.KC_S1B_RUN, mf9.KC_S1B_ATTEMPT)
    )
    cl_texts = mf9.read_sealed_outputs(
        mf9.sealed_outputs_path(root, mf9.CLOSED_LIST_RUN, mf9.CLOSED_LIST_ATTEMPT)
    )

    projection_inventory = load_value_projection_inventory(lock, root)
    kc_parsed = {sample_id: parse_slu_response(kc_texts[sample_id]) for sample_id in roster}
    cache: dict[tuple[str, str], tuple[str, float] | None] = {}

    workdir = Path(tempfile.mkdtemp(prefix="saea-mf10-normalized-", dir=str(root)))
    try:
        arms: dict[str, Path] = {}
        arms["comparator"] = mf9.write_outputs(
            [{"sample_id": sid, "text": cl_texts[sid]} for sid in roster],
            workdir / "comparator.outputs.jsonl",
        )
        arms["kc_s1b"] = mf9.write_outputs(
            [{"sample_id": sid, "text": kc_texts[sid]} for sid in roster],
            workdir / "kc_s1b.outputs.jsonl",
        )
        projected_rows = []
        for sample_id in roster:
            scenario, action, entities, parsed = kc_parsed[sample_id]
            if not parsed:
                projected_rows.append({"sample_id": sample_id, "text": kc_texts[sample_id]})
                continue
            projected, outcomes = project_slu_entities(
                entities, projection_inventory, threshold=PROJECTION_TAU, nearest_cache=cache
            )
            projected = tuple(
                SlotEntity(type=entity.type, filler=normalize_filler(entity.filler))
                if outcome.branch in (VALUE_BRANCH_TOO_FAR, VALUE_BRANCH_NO_INVENTORY)
                else entity
                for entity, outcome in zip(projected, outcomes)
            )
            projected_rows.append(
                {
                    "sample_id": sample_id,
                    "text": mf9.prediction_text(scenario, action, projected),
                }
            )
        arms["kc_s1b_value_projected"] = mf9.write_outputs(
            projected_rows, workdir / "kc_s1b_value_projected.outputs.jsonl"
        )
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            scored = dict(
                zip(
                    arms,
                    pool.map(
                        lambda path: score_slurp_outputs_slu_normalized(
                            path, lock, root, split_id="devel"
                        ),
                        arms.values(),
                    ),
                )
            )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    # --- identity anchors, fail-closed ------------------------------------
    kc_official = mf9.official_block(scored["kc_s1b"])
    mf9.assert_published(
        kc_official,
        {
            "entities_strict": MF9_PUBLISHED["kc_s1b_entities_strict"],
            "word_f1": MF9_PUBLISHED["kc_s1b_word_f1"],
            "char_f1": MF9_PUBLISHED["kc_s1b_char_f1"],
            "slu_f1": MF9_PUBLISHED["kc_s1b_slu_f1"],
        },
        "KC-S1b under the normalized scorer's own official half",
    )
    comparator_official = mf9.official_block(scored["comparator"])
    mf9.assert_published(
        comparator_official, COMPARATOR_PUBLISHED, "the sealed closed-list comparator"
    )
    projected_official = mf9.official_block(scored["kc_s1b_value_projected"])
    if abs(projected_official["slu_f1"] - MF9_PUBLISHED["projected_slu_f1"]) > 1e-9:
        raise SystemExit(
            "IDENTITY ANCHOR FAILED: the rebuilt value-projected arm scores "
            f"{projected_official['slu_f1']}, MF-9 published "
            f"{MF9_PUBLISHED['projected_slu_f1']}"
        )

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    def official_samples(name: str) -> dict[str, dict]:
        return {row["sample_id"]: row for row in scored[name]["per_sample"]}

    def normalized_samples(name: str) -> dict[str, dict]:
        return {
            row["sample_id"]: dict(row["normalized"]) for row in scored[name]["per_sample"]
        }

    def contrast(left, right, ids) -> dict[str, dict]:
        contrasts = paired_contrast(
            left,
            right,
            metrics=list(PAIRED_METRICS),
            sample_ids=sorted(ids),
            strata_of=stratum_of,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
        )
        out: dict[str, dict] = {}
        for metric, item in contrasts.items():
            doc = item.as_dict()
            bootstrap = doc.get("bootstrap") or {}
            out[metric] = {
                "n": doc["n"],
                "left_pct": round(100.0 * doc["left_mean"], 2),
                "right_pct": round(100.0 * doc["right_mean"], 2),
                "delta_pp": round(100.0 * doc["delta"], 2),
                "saves": doc["saves"],
                "harms": doc["harms"],
                "ties": doc["ties"],
                "sign_test_p": doc["sign_test_p"],
                "ci90_pp": [
                    round(100.0 * bootstrap.get("ci_low", 0.0), 2),
                    round(100.0 * bootstrap.get("ci_high", 0.0), 2),
                ],
            }
        return out

    # --- the surface-form mass the normalizer removes ---------------------
    inventory = load_slot_normalizer_inventory(lock, root)
    norm_cache: dict[tuple[str, str], str] = {}

    def normalize(entities):
        return normalize_slot_entities(
            entities, inventory, rules=SLURP_SLOT_NORMALIZER_RULES, cache=norm_cache
        )

    surface_before = 0.0
    surface_after = 0.0
    mass_before = 0.0
    mass_after = 0.0
    tp_after = 0.0
    # The SAME attribution MF-9 publishes, per type, with the normalizer applied
    # to both sides -- so question 4 can re-price every ceiling rung under the
    # normalized metric instead of asserting which way it would move.
    normalized_loss_table: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "gold_mentions": 0.0,
            "exact_matches": 0.0,
            "surface_pairs": 0.0,
            "missing": 0.0,
            "spurious": 0.0,
            "type_swaps": 0.0,
            "missing_mass": 0.0,
            "surface_mass": 0.0,
            "spurious_mass": 0.0,
            "type_swap_mass": 0.0,
        }
    )
    for sample_id in roster:
        gold_entities = tuple(gold[sample_id].entities)
        predicted = tuple(kc_parsed[sample_id][2])
        before = mf9.attribute_row(gold_entities, predicted)
        after = mf9.attribute_row(normalize(gold_entities), normalize(predicted))
        surface_before += before["surface_mass"]
        surface_after += after["surface_mass"]
        mass_before += before["mass"]
        mass_after += after["mass"]
        tp_after += after["tp"]
        for entity in gold_entities:
            normalized_loss_table[str(entity.type)]["gold_mentions"] += 1.0
        for pair in after["surface_pairs"]:
            block = 2.0 * (
                float(pair["word_distance"]) + float(pair["char_distance"])
            )
            row = normalized_loss_table[str(pair["type"])]
            row["surface_mass"] += block
            if block == 0.0:
                row["exact_matches"] += 1.0
            else:
                row["surface_pairs"] += 1.0
        for swap in after["type_swaps"]:
            row = normalized_loss_table[str(swap["gold_type"])]
            row["type_swap_mass"] += 4.0
            row["type_swaps"] += 1.0
        for entity_type, _filler in after["spurious"]:
            row = normalized_loss_table[str(entity_type)]
            row["spurious_mass"] += 2.0
            row["spurious"] += 1.0
        for entity_type, _filler in after["missing"]:
            row = normalized_loss_table[str(entity_type)]
            row["missing_mass"] += 2.0
            row["missing"] += 1.0
    for row in normalized_loss_table.values():
        row["total_mass"] = (
            row["missing_mass"]
            + row["surface_mass"]
            + row["spurious_mass"]
            + row["type_swap_mass"]
        )
    attributed = sum(row["total_mass"] for row in normalized_loss_table.values())
    if abs(attributed - mass_after) > 1e-6:
        raise SystemExit(
            f"the NORMALIZED per-type attribution does not close: {attributed} "
            f"against {mass_after}"
        )

    per_type_official = _per_type_strict(gold, kc_parsed, roster)
    per_type_normalized = _per_type_strict(gold, kc_parsed, roster, normalize=normalize)

    # The evidence for R3's declared candidate set: the SAME rung with the
    # semantic filter dropped, and the gold values it collapses. This is the
    # measurement that made the filter a rule instead of a preference, and it is
    # reported rather than described.
    unrestricted = load_slot_normalizer_inventory(lock, root, candidates=None)
    unrestricted_cache: dict[tuple[str, str], str] = {}
    merged: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for record in gold.values():
        for entity in record.entities:
            image = normalize_slot_entities(
                (entity,),
                unrestricted,
                rules=SLURP_SLOT_NORMALIZER_RULES,
                cache=unrestricted_cache,
            )[0].filler
            bucket = merged[str(entity.type)][image]
            if entity.filler not in bucket:
                bucket.append(entity.filler)
    unrestricted_merges = {
        f"{entity_type}:{image}": sorted(sources)
        for entity_type, buckets in sorted(merged.items())
        for image, sources in sorted(buckets.items())
        if len(sources) > 1
    }

    arms_table: dict[str, dict] = {}
    for name in arms:
        official = mf9.official_block(scored[name])
        normalized = scored[name]["aggregate"]["normalized"]["micro"]
        arms_table[name] = {
            "official": official,
            "normalized": {
                "slu_f1": round(100.0 * float(normalized["slu_f1"]), 2),
                "entities_strict": round(100.0 * float(normalized["span_f1"]), 2),
                "word_f1": round(100.0 * float(normalized["word_f1"]), 2),
                "char_f1": round(100.0 * float(normalized["char_f1"]), 2),
            },
            "normalized_minus_official": {
                "slu_f1": round(
                    100.0 * float(normalized["slu_f1"]) - float(official["slu_f1"]), 2
                ),
                "entities_strict": round(
                    100.0 * float(normalized["span_f1"])
                    - float(official["entities_strict"]),
                    2,
                ),
                "word_f1": round(
                    100.0 * float(normalized["word_f1"]) - float(official["word_f1"]), 2
                ),
                "char_f1": round(
                    100.0 * float(normalized["char_f1"]) - float(official["char_f1"]), 2
                ),
            },
            "per_rule": {
                rule: {
                    "slu_f1": round(100.0 * float(block["slu_f1"]), 2),
                    "entities_strict": round(100.0 * float(block["span_f1"]), 2),
                    "word_f1": round(100.0 * float(block["word_f1"]), 2),
                    "char_f1": round(100.0 * float(block["char_f1"]), 2),
                }
                for rule, block in scored[name]["aggregate"][
                    "normalized_per_rule"
                ].items()
            },
        }

    contrasts = {}
    for population, ids in pops.items():
        contrasts[population] = {
            "kc_s1b_minus_comparator_official": contrast(
                official_samples("comparator"), official_samples("kc_s1b"), ids
            ),
            "kc_s1b_minus_comparator_normalized": contrast(
                normalized_samples("comparator"), normalized_samples("kc_s1b"), ids
            ),
            "projected_minus_kc_s1b_official": contrast(
                official_samples("kc_s1b"),
                official_samples("kc_s1b_value_projected"),
                ids,
            ),
            "projected_minus_kc_s1b_normalized": contrast(
                normalized_samples("kc_s1b"),
                normalized_samples("kc_s1b_value_projected"),
                ids,
            ),
            "kc_s1b_normalized_minus_official": contrast(
                official_samples("kc_s1b"), normalized_samples("kc_s1b"), ids
            ),
        }

    normalized_block = scored["kc_s1b"]["aggregate"]["normalized"]
    document = {
        "schema": "saea-slurp-mf10-normalized-slu-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": contacts_block(),
        "scorer": {
            "id": SLURP_SLU_NORMALIZED_SCORER_ID,
            "normalizer_id": SLURP_SLOT_NORMALIZER_ID,
            "rules": list(SLURP_SLOT_NORMALIZER_RULES),
            "applies_to": "gold AND prediction, before the official distance blocks",
            "replaces_the_official_number": False,
            "reporting_rule": (
                "the paper-facing SLURP number stays the official evaluate.py one; "
                "the normalized number is reported BESIDE it, exactly as "
                "asr-wer-whisper sits beside raw asr-wer. No verdict, lock or "
                "admission in this repository is restated under it"
            ),
            "inventory": normalized_block["inventory"],
            "false_merge_count": normalized_block["false_merge_count"],
            "false_merges": normalized_block["false_merges"],
            "r3_candidate_filter_evidence": {
                "what_it_is": (
                    "the SAME R3 rung with its declared candidate set dropped, so "
                    "the token list comes from the corpus alone. This is the version "
                    "this audit built first; the false-merge audit below is what "
                    "refused it"
                ),
                "tokens_the_corpus_alone_admits": list(unrestricted.leading_tokens),
                "tokens_the_candidate_set_rejects": list(
                    normalized_block["inventory"]["rejected_tokens"]
                ),
                "false_merge_count": len(unrestricted_merges),
                "false_merges": unrestricted_merges,
                "verdict": (
                    "REFUSED. A metric that maps `next week`, `last week`, "
                    "`this week` and `one week` onto `week` does not clarify the "
                    "score, it forgives a real error. No corpus statistic separates "
                    "`next` from `on`, so the candidate set is declared and the "
                    "corpus only confirms"
                ),
            },
            "on_wednesday_is_not_repaired": (
                "MF-9 section 1.4's `on wednesday` -> `wednesday` example is NOT "
                "repaired by this rule: `on` is in the declared candidate set but "
                "TRAIN never carries `on X` and `X` as fillers of the same type, so "
                "the confirmation floor refuses it at zero witnesses. The rule "
                "declines to act where the corpus gives it no evidence, and the "
                "residual is charged to the arm rather than forgiven"
            ),
        },
        "sources": {
            "umbrella_lock": str(lock_path),
            "kc_s1b_outputs_sha256": sha256_file(
                mf9.sealed_outputs_path(root, mf9.KC_S1B_RUN, mf9.KC_S1B_ATTEMPT)
            ),
            "comparator_outputs_sha256": sha256_file(
                mf9.sealed_outputs_path(root, mf9.CLOSED_LIST_RUN, mf9.CLOSED_LIST_ATTEMPT)
            ),
            "value_projection": {
                "projection_id": SLURP_VALUE_PROJECTION_ID,
                "family": PROJECTION_FAMILY,
                "threshold": PROJECTION_TAU,
                "inventory_identity_hash": projection_inventory.source_identity_hash,
            },
        },
        "identity_anchors": {
            "kc_s1b_official": kc_official,
            "comparator_official": comparator_official,
            "value_projected_official_slu_f1": projected_official["slu_f1"],
            "all_passed": True,
        },
        "arms": arms_table,
        "surface_form_mass": {
            "what_it_is": (
                "MF-9's own attribution engine re-run over the SAME sealed KC-S1b "
                "rows with the normalizer applied to gold and prediction alike"
            ),
            "surface_mass_official": round(surface_before, 3),
            "surface_mass_normalized": round(surface_after, 3),
            "surface_mass_removed": round(surface_before - surface_after, 3),
            "surface_mass_removed_pct": round(
                100.0 * (surface_before - surface_after) / surface_before, 2
            )
            if surface_before
            else 0.0,
            "total_loss_mass_official": round(mass_before, 3),
            "total_loss_mass_normalized": round(mass_after, 3),
            "true_positive_mass_normalized": round(tp_after, 3),
        },
        "normalized_loss_table": {
            "what_it_is": (
                "MF-9's per-type loss attribution, recomputed with the normalizer "
                "applied to gold and prediction alike, so question 4 can RE-PRICE "
                "every ceiling rung under the normalized metric rather than assert "
                "which way it would move. The per-type masses close against the "
                "corpus total, or this read raises"
            ),
            "true_positive_mass": round(tp_after, 3),
            "loss_mass": round(mass_after, 3),
            "per_entity_type": {
                entity_type: {key: round(value, 3) for key, value in sorted(row.items())}
                for entity_type, row in sorted(normalized_loss_table.items())
            },
        },
        "per_entity_type_strict": {
            "official": per_type_official,
            "normalized": per_type_normalized,
            "delta_f1_pct": {
                entity_type: round(
                    per_type_normalized.get(entity_type, {}).get("f1_pct", 0.0)
                    - row["f1_pct"],
                    2,
                )
                for entity_type, row in per_type_official.items()
            },
        },
        "paired": {
            "design": {
                "seed": SEED,
                "replicates": N_REPLICATES,
                "ci_level": CI_LEVEL,
                "strata": "gold scenario",
                "decision_population": "new500 (unexposed)",
            },
            "by_population": contrasts,
        },
    }
    path = write_json(out_dir / "normalized-slu.json", document)
    print(f"wrote {path}")
    for name, row in arms_table.items():
        print(
            f"  {name}: official SLU-F1 {row['official']['slu_f1']} -> normalized "
            f"{row['normalized']['slu_f1']} "
            f"({row['normalized_minus_official']['slu_f1']:+.2f}); strict "
            f"{row['official']['entities_strict']} -> "
            f"{row['normalized']['entities_strict']}"
        )
    print(
        "  surface-form mass removed: "
        f"{document['surface_form_mass']['surface_mass_removed']} of "
        f"{document['surface_form_mass']['surface_mass_official']} "
        f"({document['surface_form_mass']['surface_mass_removed_pct']} %)"
    )
    print(f"  false merges: {normalized_block['false_merge_count']}")
    return 0


# ---------------------------------------------------------------------------
# Question 4 -- the ladder under both scorers
# ---------------------------------------------------------------------------


def command_ladder(args: argparse.Namespace) -> int:
    mf9 = mf9_module()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    normalized_path = out_dir / "normalized-slu.json"
    views_path = out_dir / "knowledge-views.json"
    for path in (normalized_path, views_path):
        if not path.is_file():
            raise SystemExit(f"run the earlier subcommands first: {path} is missing")
    normalized = read_json(normalized_path)
    views = read_json(views_path)
    mf9_ladder = read_json(MF9_RECEIPT_DIR / "improvement-ladder.json")

    per_type, totals = mf9_loss_table()
    arms = normalized["arms"]
    official_base = float(arms["kc_s1b"]["official"]["slu_f1"])
    normalized_base = float(arms["kc_s1b"]["normalized"]["slu_f1"])

    # Rung 1 is the ONLY measured rung, and it is measured under both scorers.
    rung1 = {
        "module": "value projection (MF-9 section 2), scoring-side",
        "measured": True,
        "official": {
            "slu_f1": float(arms["kc_s1b_value_projected"]["official"]["slu_f1"]),
            "gain": round(
                float(arms["kc_s1b_value_projected"]["official"]["slu_f1"])
                - official_base,
                2,
            ),
        },
        "normalized": {
            "slu_f1": float(arms["kc_s1b_value_projected"]["normalized"]["slu_f1"]),
            "gain": round(
                float(arms["kc_s1b_value_projected"]["normalized"]["slu_f1"])
                - normalized_base,
                2,
            ),
        },
    }
    for population in ("pooled_1000", "new500"):
        block = normalized["paired"]["by_population"][population]
        rung1["official"][f"paired_{population}"] = block[
            "projected_minus_kc_s1b_official"
        ]["slu_f1_f1"]
        rung1["normalized"][f"paired_{population}"] = block[
            "projected_minus_kc_s1b_normalized"
        ]["slu_f1_f1"]

    # The remaining rungs are CEILINGS, and every one of them is the same one
    # line of arithmetic over a mass the decomposition already attributes. Under
    # the normalized metric the base moves and the surface mass shrinks, so a
    # module aimed at surface loses most of its ceiling and a module aimed at
    # recall keeps its own.
    normalized_table = normalized["normalized_loss_table"]
    normalized_per_type = {
        entity_type: {key: float(value) for key, value in row.items()}
        for entity_type, row in normalized_table["per_entity_type"].items()
    }
    normalized_totals = {
        "true_positive_mass": float(normalized_table["true_positive_mass"]),
        "loss_mass": float(normalized_table["loss_mass"]),
        "slu_f1": normalized_base,
    }
    if abs(ceiling_slu_f1(normalized_totals, 0.0, 0.0) - normalized_base) > 0.01:
        raise SystemExit(
            "the normalized loss table does not rebuild the normalized base"
        )

    def under_both(types: Sequence[str], *, missing: bool, surface: bool) -> dict:
        """One counterfactual, priced under BOTH metrics from their own tables."""

        def price(table, totals):
            m = sum(table.get(name, {}).get("missing_mass", 0.0) for name in types)
            s = sum(table.get(name, {}).get("surface_mass", 0.0) for name in types)
            m = m if missing else 0.0
            s = s if surface else 0.0
            return {
                "slu_f1": ceiling_slu_f1(totals, m, s),
                "gain": round(ceiling_slu_f1(totals, m, s) - totals["slu_f1"], 2),
                "missing_mass_repaired": round(m, 3),
                "surface_mass_repaired": round(s, 3),
            }

        return {
            "official": price(per_type, totals),
            "normalized": price(normalized_per_type, normalized_totals),
        }

    all_types = sorted(set(per_type) | set(normalized_per_type))
    ceilings = {
        "surface_perfect": under_both(all_types, missing=False, surface=True),
        "no_missing": under_both(all_types, missing=True, surface=False),
    }

    classes = read_json(out_dir / "type-classes.json")["classes"]
    closed_types = tuple(classes["CLOSED/FORMAT"])

    cards_view = views["views"]["KU-S3v-cards-closed"]
    combined_view = views["views"]["combined-cards-plus-retrieval"]

    def ceiling_rung(number, module, official_slu, *, both=None, note=None):
        entry = {
            "n": number,
            "module": module,
            "measured": False,
            "official": {
                "slu_f1": official_slu,
                "gain": round(official_slu - official_base, 2),
            },
        }
        if both is not None:
            entry["normalized"] = {
                "slu_f1": both["normalized"]["slu_f1"],
                "gain": both["normalized"]["gain"],
                "official_gain_for_comparison": both["official"]["gain"],
            }
        else:
            entry["normalized"] = {"slu_f1": None, "gain": None}
        if note:
            entry["normalized"]["note"] = note
        return entry

    cards_both = under_both(closed_types, missing=True, surface=True)
    rungs = [
        {"n": 1, **rung1},
        ceiling_rung(
            2,
            "constrained decoding, structure + 55-type enum (MF-9 section 3)",
            45.16,
            note=(
                "the 3 unparsed rows carry 10 gold mentions and the normalizer never "
                "touches a row that did not parse, so this rung is a pure RECALL "
                "channel and its gain does not depend on the metric's spelling "
                "tolerance"
            ),
        ),
        ceiling_rung(
            3,
            "intent narrowing -> better block selection (MF-9 section 1.2)",
            48.40,
            note="a recall channel; the normalizer does not touch it",
        ),
        ceiling_rung(
            4,
            "retrieved fillers, KU-S3 (MF-9 section 4.2)",
            58.06,
            note="a recall channel; the normalizer does not touch it",
        ),
        ceiling_rung(
            "4v",
            "MF-10 KU-S3v static vocabulary cards on the CLOSED/FORMAT types",
            cards_view["reachable_slu_f1_unrestricted"]["slu_f1"],
            both=cards_both,
            note=(
                "priced on BOTH per-type tables, unrestricted oracle on the 18 "
                "closed types. The gain does NOT shrink under the normalized "
                "metric, and the split says why: 480 of the 565 mass units this "
                "card repairs are MISSING and only 85 are surface. A vocabulary "
                "card is a RECALL module that also happens to fix spelling, not a "
                "spelling module -- which is the opposite of rung 1"
            ),
        ),
        ceiling_rung(
            "4c",
            "MF-10 combined view: cards on closed + KU-S3 retrieval on open",
            combined_view["reachable_slu_f1_bound"]["slu_f1"],
        ),
        ceiling_rung(
            6,
            "targeted slot re-ask on judge-flagged rows (MF-9 section 5.2)",
            72.87,
            note="a recall channel; the normalizer does not touch it",
        ),
    ]

    document = {
        "schema": "saea-slurp-mf10-ladder-both-scorers-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PRICED, NOT PREREGISTERED. Admits nothing, promotes nothing.",
        "contacts": contacts_block(),
        "sources": {
            "mf9_improvement_ladder_sha256": sha256_file(
                MF9_RECEIPT_DIR / "improvement-ladder.json"
            ),
            "normalized_slu_sha256": sha256_file(normalized_path),
            "knowledge_views_sha256": sha256_file(views_path),
        },
        "base": {
            "arm": mf9.KC_S1B_RUN,
            "official_slu_f1": official_base,
            "normalized_slu_f1": normalized_base,
            "normalized_minus_official": round(normalized_base - official_base, 2),
        },
        "ceilings_under_both": ceilings,
        "normalized_base_rebuilds": True,
        "closed_types_priced": list(closed_types),
        "rungs": rungs,
        "admission_primary": {
            "recommendation": (
                "the OFFICIAL SLU-F1 stays the primary for admitting a slot module; "
                "the normalized SLU-F1 is the SECONDARY and must AGREE IN SIGN"
            ),
            "why_official_is_primary": (
                "it is the dataset's standard scorer at a pinned commit, it is the "
                "number every published SLURP line is stated in, and every verdict "
                "and lock in this repository already stands on it. A study that "
                "moved its primary to a metric of its own making after seeing the "
                "gap would be choosing the metric that flatters it"
            ),
            "why_normalized_is_reported_beside_it": (
                "the official metric charges a full word distance of 1.0 for a pure "
                "case or spacing difference, so a module can look effective by "
                "repairing spelling and a module aimed at RECALL can look weaker "
                "than it is. The normalized column separates the two: a gain that "
                "survives it is a gain in what was heard, and a gain that vanishes "
                "under it was a gain in how it was written"
            ),
            "disagreement_rule": (
                "a module whose two columns disagree in SIGN is NOT admitted on the "
                "strength of either; the disagreement is itself the finding and is "
                "reported with the per-type table that produced it"
            ),
            "precedent": "asr-wer-whisper beside asr-wer, Earnings-21/22",
        },
        "what_this_is_not": (
            "no rung is admitted, promoted or preregistered; the ceilings are "
            "oracles and overlap heavily, so they do not add; no superiority, "
            "generalization or Stage-3 conclusion is reached"
        ),
        "mf9_ladder_reference": {
            "receipt": "docs/checks/.../2026-09-08-mf9-slurp-slot-gap-audit/improvement-ladder.json",
            "schema": mf9_ladder.get("schema"),
        },
    }
    path = write_json(out_dir / "ladder-both-scorers.json", document)
    print(f"wrote {path}")
    print(
        f"  base: official {official_base} / normalized {normalized_base} "
        f"({document['base']['normalized_minus_official']:+.2f})"
    )
    for rung in rungs:
        normalized_slu = rung["normalized"]["slu_f1"]
        print(
            f"  rung {rung['n']}: official {rung['official']['slu_f1']} "
            f"(+{rung['official']['gain']})"
            + (
                f" | normalized {normalized_slu} (+{rung['normalized']['gain']})"
                if normalized_slu is not None
                else ""
            )
        )
    print(
        "  ceilings: surface-perfect "
        f"{ceilings['surface_perfect']['official']['slu_f1']} official vs "
        f"{ceilings['surface_perfect']['normalized']['slu_f1']} normalized; "
        f"no-missing {ceilings['no_missing']['official']['slu_f1']} vs "
        f"{ceilings['no_missing']['normalized']['slu_f1']}"
    )
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="receipt directory (default: the MF-10 checks directory)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("classes", help="question 1: type classes and vocabulary cards")
    sub.add_parser("views", help="question 2: the priced knowledge views")
    normalized = sub.add_parser(
        "normalized", help="question 3: the normalized SLU scorer against the official"
    )
    normalized.add_argument("--workers", type=int, default=3)
    sub.add_parser("ladder", help="question 4: the ladder under both scorers")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "classes": command_classes,
        "views": command_views,
        "normalized": command_normalized,
        "ladder": command_ladder,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
