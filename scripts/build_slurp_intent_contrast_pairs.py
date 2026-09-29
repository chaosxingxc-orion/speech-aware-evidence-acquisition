#!/usr/bin/env python3
"""Build the Perception-branch TOP-2 intent CONTRAST-PAIR table (same-flight instrument phase 2,
merge set C, item 5/6, design docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-
perception-variants-design.md sections 3 and 6, P-SV-1).

WHAT IT BUILDS. A pinned, model-free lookup table,
``prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1/table-v1.json``: one row per intent-pair the
``top2-contrast-v1`` Perception presentation (``rails.perception_presentations.
_Top2ContrastPresentation``) may render, keyed by the pair's two intent ids, each row carrying
exactly ``activation_sentence`` (what picks one intent over the other) and ``exclusion_sentence``
(what rules the other one out) -- two full English sentences, never a raw utterance, span or
filler. This script mines the pairs and writes the table; it does not render anything at
inference time (that is ``rails.perception_presentations``'s job against whatever table a caller
loads and pins) and it is NOT invoked by the runtime at all.

TOP-2 PAIR SELECTION. For each of the 60 SLURP intents, its SINGLE nearest rival by cosine
between the pinned centroid boundary keys KPROBE built (the SAME
``prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl`` cell W3a's contrast cards
read) -- never the intent itself. This is exactly the confusion pair a Perception ranker's own
rank-1/rank-2 shortlist would produce when it is wrong at the margin, which is what the
``top2-contrast-v1`` presentation renders. Pairs are deduplicated by their unordered
``frozenset({x, y})`` (a mutual nearest-neighbour pair collapses to one row), so the table has at
most 60 and typically fewer rows.

W3A'S WORD-GAP METHOD, REUSED VERBATIM. The per-intent word and slot-type statistics
(``load_pool``, ``intent_stats``, ``cues``, ``typed``) are the SAME functions
``scripts/build_slurp_intent_contrast_cards.py`` (owner decision 164, cell W3a) already computes
over the SAME R01-excluded TRAIN exemplar pool
(``size-pool-annotated-exemplars-minus-r01``, verified disjoint from TRAIN Fold A, TRAIN Fold B
and the R01 construction roster) -- loaded here through that module directly (not reimplemented),
so a change to the word-gap rule changes both scripts' outputs identically. THE ONE DIFFERENCE:
W3a embeds a compact ``- rival: word, word [type] | word, word [type]`` bullet line into a card;
this script instead composes two FULL SENTENCES per pair (design section 6: "the narrower
pair-only form"), because ``top2-contrast-v1`` is deliberately narrower than W3a's closed
contrast-card line (O5 ruling: it is never a fallback for it, and vice versa).

O5 FLOOR, THIS SCRIPT'S OWN. A pair mines to nothing (omitted from the table, receipted why) when
either intent's own pool support is below :data:`MIN_PAIR_POOL_SUPPORT` utterances, or when the
word-gap method finds no distinguishing cue word or slot type on one side (``cues``/``typed``
both empty) -- the caller that BUILDS the table is the one that knows the pool-support count
(``rails.perception_presentations``'s own docstring), and this is that count and that decision.

PAIR SCOPE, ``--pair-scope`` (O7 ruling, docs/superpowers/specs/2026-09-28-same-flight-instrument-
phase2-perception-variants-design.md). ``nearest-rival`` (default) is the ORIGINAL selection above:
its CONTENT (the mined ``rows``, and every other field except ``builder.sha256``) is unchanged and
reproducible, proven by ``--check``. ``builder.sha256`` is this script file's own hash at build
time, so it drifts the moment the script is edited for any reason -- even to add ``--pair-scope``
itself -- regardless of whether the mined rows changed; ``--check`` reports it but never gates on
it, and this is also why a real (non-``--dry``, non-``--check``) re-run of ``nearest-rival`` after
an edit to this file will refuse to overwrite the pinned v1 table (``write_once``'s own guard) --
which is correct: the pinned file must never be touched, and ``--check`` is how it is verified
instead. ``all-pairs`` writes EVERY unordered pair of distinct SLURP intents (O5's
floor still applies per pair, unchanged), roster-agnostic -- pairs are never selected from a
roster's seeds, only from the full released intent set -- because the P-SV-1 B branch only renders
a block when a row's own rank-1/rank-2 pair is in the table, and the nearest-rival table covers
just 415 of 1,078 P-SV-1 rows (38.5 %; scripts/analysis/slurp_contrast_pair_coverage.py). It writes
a SEPARATE artifact (``SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2``, its own table relpath, receipt and
exposure-ledger row) under the SAME method, pool, pins and forbidden-roster disjointness check --
never a mutation of the ``nearest-rival`` output. The table's own ``schema`` field never changes
between scopes: ``core.flight.runtime`` and the tests hard-validate it as
``saea-slurp-perception-contrast-pairs-v1``, and the per-pair row shape
(``activation_sentence``/``exclusion_sentence`` keyed by the two intent ids) is identical either
way, so the runtime loader and ``rails.perception_presentations`` read either table unchanged.

BOUNDARY. Model-free: zero model, server, encoder, embedder, ASR, scorer, network, GPU and
paid-API contact. TRAIN only, same pins and same forbidden-roster disjointness check as W3a. No
gold label of any evaluated row is read (this reads only the label a TRAIN exemplar itself
carries, exactly as W3a's own construction pool does). Writes only under the data root
(write-once: an existing file with different bytes is refused) and the repository receipt, which
carries pair ids, counts and hashes only -- never a cue word, a sentence or any card text (the
same "counts only" discipline W3a's own receipt keeps).

    python scripts/build_slurp_intent_contrast_pairs.py --data-root "$SPEECHRL_DATA_DIR" [--dry]
    python scripts/build_slurp_intent_contrast_pairs.py --data-root "$SPEECHRL_DATA_DIR" \\
        --pair-scope all-pairs
    python scripts/build_slurp_intent_contrast_pairs.py --data-root "$SPEECHRL_DATA_DIR" --check
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors  # noqa: E402

#: The table document's OWN ``schema`` field -- fixed across every ``--pair-scope``, never bumped.
#: ``core.flight.runtime.FlightRuntime`` and ``tests/unit/test_perception_branch_contrast_and_
#: contract.py`` hard-validate this exact string; an ``all-pairs`` table is a different artifact
#: with a different id, relpath and receipt, but the SAME row shape and the SAME table schema, so
#: the runtime loader and ``rails.perception_presentations`` read it unchanged (O7 ruling).
TABLE_SCHEMA = "saea-slurp-perception-contrast-pairs-v1"

#: One entry per ``--pair-scope`` choice: everything that differs between the ORIGINAL
#: nearest-rival table (byte-reproducible v1, unchanged default) and the O7 all-pairs table (a
#: separate artifact, never a mutation of v1's bytes).
PAIR_SCOPE_CONFIG: dict[str, dict[str, str]] = {
    "nearest-rival": {
        "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1",
        "ledger_row": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-BUILD-V1",
        "builder_id": "saea-slurp-perception-contrast-pairs-v1",
        "receipt_schema": "saea-slurp-perception-contrast-pairs-receipt-v1",
        "receipt_relpath": "docs/receipts/knowledge/slurp-perception-contrast-pairs-v1.json",
        "pair_selection": (
            "one pair per intent: its single nearest rival by centroid cosine, deduplicated by "
            "unordered pair"
        ),
    },
    "all-pairs": {
        "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2",
        "ledger_row": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-BUILD-V2",
        "builder_id": "saea-slurp-perception-contrast-pairs-v2",
        "receipt_schema": "saea-slurp-perception-contrast-pairs-receipt-v2",
        "receipt_relpath": "docs/receipts/knowledge/slurp-perception-contrast-pairs-v2.json",
        "pair_selection": (
            "every unordered pair of distinct SLURP intents whose pool support meets the "
            "registered floor (min_pair_pool_support), roster-agnostic: pairs are never selected "
            "from any roster's seeds, only from the full released intent set (O7 ruling, "
            "docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-"
            "design.md)"
        ),
    },
}

#: Back-compat module-level defaults -- the ``nearest-rival`` scope's own constants, unchanged
#: from before ``--pair-scope`` existed, so a caller importing these names (the unit tests) keeps
#: seeing exactly what it always has.
ARTIFACT_ID = PAIR_SCOPE_CONFIG["nearest-rival"]["artifact_id"]
LEDGER_ROW = PAIR_SCOPE_CONFIG["nearest-rival"]["ledger_row"]
OUT_NAMESPACE = f"prepared/{ARTIFACT_ID}"
TABLE_RELPATH = f"{OUT_NAMESPACE}/table-v1.json"
RECEIPT_RELPATH = PAIR_SCOPE_CONFIG["nearest-rival"]["receipt_relpath"]
BUILDER_ID = PAIR_SCOPE_CONFIG["nearest-rival"]["builder_id"]
DIMENSION = "intent-boundary"

#: A pair is minable at all only when EACH intent's own R01-excluded pool support is at least
#: this many distinct utterances -- this script's own floor (O5 ruling: the caller that builds the
#: table is the one that knows the pool-support count). Stricter than W3a's per-WORD
#: ``MIN_SUPPORT`` (3): this gates the whole PAIR, not one candidate cue word.
MIN_PAIR_POOL_SUPPORT = 5


class BuildError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    """Load a sibling script as a module, without a ``scripts`` package (the same helper
    ``scripts/analysis/slurp_node_gain_ledger.py`` uses to reuse another script's functions)."""

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


W3A = import_path(REPO_ROOT / "scripts" / "build_slurp_intent_contrast_cards.py", "build_slurp_intent_contrast_cards")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


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


def select_top2_pairs(order: list[str], cosine: np.ndarray) -> list[tuple[str, str]]:
    """One pair per intent -- its SINGLE nearest rival by cosine -- deduplicated and
    alphabetically ordered within each pair, for a deterministic, order-independent table.

    ``order`` is the intent id list in the SAME order as ``cosine``'s rows/columns (as
    :func:`build_slurp_intent_contrast_cards.build` constructs both). A mutual nearest-neighbour
    pair (X's nearest is Y, and Y's nearest is X) collapses to one row via the frozenset dedup;
    a one-directional pair (X's nearest is Y, but Y's nearest is some Z != X) still contributes
    its own row, because the ``top2-contrast-v1`` render needs a table entry whichever of the two
    a row's own rank-1/rank-2 shortlist happens to surface.
    """

    if len(order) != cosine.shape[0] or cosine.shape[0] != cosine.shape[1]:
        raise BuildError("order and cosine must be a matching square matrix")
    seen: set[frozenset] = set()
    pairs: list[tuple[str, str]] = []
    for index, intent in enumerate(order):
        ranked = [order[j] for j in np.argsort(-cosine[index], kind="stable") if order[j] != intent]
        if not ranked:
            continue
        nearest = ranked[0]
        key = frozenset({intent, nearest})
        if key in seen:
            continue
        seen.add(key)
        pairs.append(tuple(sorted(key)))
    return sorted(pairs)


def select_all_pairs(order: list[str]) -> list[tuple[str, str]]:
    """Every unordered pair of distinct intents in ``order`` (O7 ruling): the roster-agnostic
    all-pairs selection, never a per-intent nearest-rival subset. Needs no cosine matrix -- the
    pair SPACE is the whole released intent set, not a similarity-ranked shortlist of it. Sorted
    for the same deterministic, order-independent contract :func:`select_top2_pairs` keeps.
    """

    return sorted(tuple(sorted(pair)) for pair in itertools.combinations(order, 2))


def select_pairs(order: list[str], cosine: np.ndarray, pair_scope: str) -> list[tuple[str, str]]:
    """Dispatch on ``--pair-scope``: ``nearest-rival`` (default) or ``all-pairs`` (O7)."""

    if pair_scope == "nearest-rival":
        return select_top2_pairs(order, cosine)
    if pair_scope == "all-pairs":
        return select_all_pairs(order)
    raise BuildError(f"unknown --pair-scope {pair_scope!r}")


def _word_list(words: list[str]) -> str:
    return ", ".join(words) if words else ""


def contrast_sentences(
    x_id: str, y_id: str, x_stats: dict | None, y_stats: dict | None,
) -> tuple[str, str] | None:
    """One pair's ``(activation_sentence, exclusion_sentence)``, or ``None`` below the floor.

    Reuses :func:`build_slurp_intent_contrast_cards.cues`/``typed`` verbatim -- the SAME
    utterance-level document-frequency gap and slot-type share gap W3a's cards use, over the SAME
    per-intent statistics (:func:`build_slurp_intent_contrast_cards.intent_stats`). Returns
    ``None`` (mine nothing) when either side's own pool support is below
    :data:`MIN_PAIR_POOL_SUPPORT`, or when the word-gap method names no distinguishing cue word or
    slot type on either side -- there is then nothing non-generic to write, and O5 refuses a
    fallback to W3a's closed card line.
    """

    if (
        x_stats is None or y_stats is None
        or x_stats["n"] < MIN_PAIR_POOL_SUPPORT or y_stats["n"] < MIN_PAIR_POOL_SUPPORT
    ):
        return None
    x_words, y_words = W3A.cues(x_stats, y_stats), W3A.cues(y_stats, x_stats)
    x_types, y_types = W3A.typed(x_stats, y_stats), W3A.typed(y_stats, x_stats)
    if not (x_words or x_types) or not (y_words or y_types):
        return None

    def side(intent: str, words: list[str], types: list[str]) -> str:
        clauses = []
        if words:
            clauses.append(f"words like {_word_list(words)}")
        if types:
            clauses.append(f"a {', '.join(types)} slot")
        return f"{intent} requests typically use {' and '.join(clauses)}"

    activation_sentence = (
        f"{side(x_id, x_words, x_types)}; {side(y_id, y_words, y_types)}."
    )
    exclusion_sentence = (
        f"If the request matches neither pattern, treat {x_id} and {y_id} as easily confused "
        "and decide from the rest of the utterance rather than these cues alone."
    )
    return activation_sentence, exclusion_sentence


def build_table(
    order: list[str], cosine: np.ndarray, stats: dict[str, dict], *, pair_scope: str = "nearest-rival",
) -> dict:
    """The whole table: minted rows plus a receipted list of skipped pairs and why.

    ``pair_scope`` selects the pair SPACE (:func:`select_pairs`); the default ``"nearest-rival"``
    is byte-identical to this function's behaviour before ``--pair-scope`` existed. O5's own floor
    (:func:`contrast_sentences`) applies per pair, unchanged, under either scope.
    """

    rows: dict[str, dict] = {}
    skipped: list[dict] = []
    for x_id, y_id in select_pairs(order, cosine, pair_scope):
        sentences = contrast_sentences(x_id, y_id, stats.get(x_id), stats.get(y_id))
        pair_key = f"{x_id}|{y_id}"
        if sentences is None:
            skipped.append({
                "intents": [x_id, y_id],
                "reason": "insufficient-pool-support",
                "pool_utterances": [
                    stats.get(x_id, {}).get("n", 0), stats.get(y_id, {}).get("n", 0),
                ],
            })
            continue
        activation_sentence, exclusion_sentence = sentences
        rows[pair_key] = {
            "intents": [x_id, y_id],
            "activation_sentence": activation_sentence,
            "exclusion_sentence": exclusion_sentence,
        }
    return {"rows": rows, "skipped": skipped}


def load_stats(root: Path) -> tuple[list[str], np.ndarray, dict[str, dict], dict]:
    """``(order, cosine, stats, inputs)`` -- the SAME pins and disjointness check W3a's own
    ``build()`` uses, read directly off the imported module so a pin can never drift between the
    two scripts."""

    base = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / W3A.BASE["snapshot"][0]).read_text(encoding="utf-8"))
    )
    if base.content_hash() != W3A.BASE["snapshot"][1]:
        raise BuildError("intent-boundaries-v1 is not the flown content hash")
    cards = {value.value_id.split("intent-boundary:", 1)[1]: value for value in base.values}
    if len(cards) != 60:
        raise BuildError("intent-boundaries-v1 is not the 60-card store")
    order = sorted(cards)

    centroids = load_sealed_vectors(
        root / W3A.CENTROIDS[0], expected_sha256=W3A.CENTROIDS[1], dimensions=(DIMENSION,),
    )
    if set(centroids) != {f"{DIMENSION}:{intent}" for intent in order}:
        raise BuildError("the centroid keys do not cover the 60 cards exactly")
    matrix = np.asarray(
        [centroids[f"{DIMENSION}:{intent}"][DIMENSION] for intent in order], dtype=np.float64,
    )
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    cosine = matrix @ matrix.T

    pool = W3A.load_pool(root)
    forbidden: set[str] = set()
    for relpath in W3A.FORBIDDEN_ROSTERS:
        roster = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
        forbidden.update(":".join(str(item["sample_id"]).split(":")[:3]) for item in roster["items"])
    overlap = pool["utterances"] & forbidden
    if overlap:
        raise BuildError(f"the construction pool intersects a forbidden roster on {len(overlap)} utterances")
    stats = {intent: W3A.intent_stats(rows) for intent, rows in pool["per_intent"].items()}
    inputs = {
        "base_snapshot": {"relpath": W3A.BASE["snapshot"][0], "content_sha256": W3A.BASE["snapshot"][1]},
        "centroid_keys": {"relpath": W3A.CENTROIDS[0], "sha256": W3A.CENTROIDS[1]},
        "construction_pool": {
            "relpath": W3A.POOL[0], "content_sha256": W3A.POOL[1], "utterances": len(pool["utterances"]),
        },
        "forbidden_rosters": {relpath: sha_file(REPO_ROOT / relpath) for relpath in W3A.FORBIDDEN_ROSTERS},
    }
    return order, cosine, stats, inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--dry", action="store_true", help="build and measure, write nothing")
    parser.add_argument(
        "--pair-scope", choices=sorted(PAIR_SCOPE_CONFIG), default="nearest-rival",
        help="'nearest-rival' (default): one pair per intent, its single nearest rival by "
             "centroid cosine -- byte-reproducible, proven by --check. 'all-pairs' (O7): every "
             "unordered pair of distinct intents above the pool-support floor, roster-agnostic; "
             "writes a separate V2 artifact, never a mutation of the nearest-rival table.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="re-derive the table for the selected --pair-scope and diff its CONTENT (schema, "
             "artifact_id, builder_id, min_pair_pool_support, rows) against the file already "
             "written at that scope's table relpath; writes nothing. builder.sha256 (this script "
             "file's own hash) is reported but never gates the verdict, since it drifts on any "
             "script edit even when the mined rows do not; exits 1 on a content mismatch or a "
             "missing file.",
    )
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")

    scope = PAIR_SCOPE_CONFIG[args.pair_scope]
    artifact_id = scope["artifact_id"]
    out_namespace = f"prepared/{artifact_id}"
    table_relpath = f"{out_namespace}/table-v1.json"
    receipt_relpath = scope["receipt_relpath"]

    order, cosine, stats, inputs = load_stats(root)
    table = build_table(order, cosine, stats, pair_scope=args.pair_scope)
    builder_sha = sha_file(Path(__file__))

    table_doc = {
        "schema": TABLE_SCHEMA,
        "artifact_id": artifact_id,
        "builder_id": scope["builder_id"],
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_pairs.py", "sha256": builder_sha},
        "min_pair_pool_support": MIN_PAIR_POOL_SUPPORT,
        "rows": table["rows"],
    }
    table_bytes = canonical(table_doc)
    table_sha = sha_bytes(table_bytes)

    if args.check:
        target = root / table_relpath
        if not target.exists():
            print(json.dumps({
                "check": "FAIL", "pair_scope": args.pair_scope, "relpath": table_relpath,
                "reason": "table not found",
            }, indent=2))
            return 1
        existing_bytes = target.read_bytes()
        existing_sha = sha_bytes(existing_bytes)
        try:
            existing_doc = json.loads(existing_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            print(json.dumps({
                "check": "FAIL", "pair_scope": args.pair_scope, "relpath": table_relpath,
                "reason": f"existing table is not valid JSON: {error}",
            }, indent=2))
            return 1
        # The CONTENT fields this check proves unchanged. ``builder.sha256`` is excluded on
        # purpose: it is the hash of THIS SCRIPT FILE at build time, so it necessarily drifts the
        # moment the script itself is edited for any reason at all (a new --pair-scope/--check
        # flag, a docstring fix, ...) -- even when the mined pairs and sentences are byte-for-byte
        # unchanged. A raw whole-file byte comparison would report a false FAIL after every such
        # edit; comparing the substantive fields below is what "v1 is unchanged" actually means.
        content_fields = ("schema", "artifact_id", "builder_id", "min_pair_pool_support", "rows")
        mismatches = [field for field in content_fields if existing_doc.get(field) != table_doc[field]]
        if existing_doc.get("builder", {}).get("relpath") != table_doc["builder"]["relpath"]:
            mismatches.append("builder.relpath")
        match = not mismatches
        existing_builder_sha = existing_doc.get("builder", {}).get("sha256")
        print(json.dumps({
            "check": "PASS" if match else "FAIL",
            "pair_scope": args.pair_scope,
            "relpath": table_relpath,
            "content_matches": match,
            "mismatched_fields": mismatches,
            "existing_file_sha256": existing_sha,
            "existing_builder_sha256": existing_builder_sha,
            "derived_builder_sha256": builder_sha,
            "builder_sha256_unchanged": existing_builder_sha == builder_sha,
            "note": (
                "builder.sha256 is this script file's own hash at build time and is expected to "
                "differ once the script is edited, even when the mined rows are unchanged; the "
                "content fields (schema, artifact_id, builder_id, min_pair_pool_support, rows) "
                "are the real proof that this pair-scope's output is unchanged."
            ),
        }, indent=2))
        return 0 if match else 1

    written = {"table": write_once(root / table_relpath, table_bytes, dry=args.dry)}

    pairs_considered = len(table["rows"]) + len(table["skipped"])
    receipt = {
        "schema": scope["receipt_schema"],
        "artifact_id": artifact_id,
        "exposure_ledger_row": scope["ledger_row"],
        "builder": {"relpath": "scripts/build_slurp_intent_contrast_pairs.py", "sha256": builder_sha},
        "method": {
            "pair_selection": scope["pair_selection"],
            "word_gap_method": {
                "reused_from": "scripts/build_slurp_intent_contrast_cards.py",
                "functions": ["load_pool", "intent_stats", "cues", "typed"],
                "min_support_utterances_per_word": W3A.MIN_SUPPORT,
                "min_df_gap": W3A.MIN_DF_GAP,
                "type_gap": W3A.TYPE_GAP,
            },
            "min_pair_pool_support": MIN_PAIR_POOL_SUPPORT,
        },
        "inputs": inputs,
        "pairs_considered": pairs_considered,
        "pairs_written": len(table["rows"]),
        "pairs_skipped": len(table["skipped"]),
        "skipped": [{"intents": row["intents"], "reason": row["reason"]} for row in table["skipped"]],
        "output": {"relpath": table_relpath, "sha256": written["table"], "content_sha256": table_sha},
        "contacts": {
            "model": 0, "server": 0, "encoder": 0, "embedder": 0, "asr": 0, "scorer": 0,
            "network": 0, "gpu": 0, "paid_api": 0, "tokenizer_process_vocab_only": 0,
        },
        "boundary": (
            "No card text, cue word, sentence or utterance appears in this receipt: intent ids, "
            "counts, the skip reason and hashes only."
        ),
    }
    receipt_bytes = canonical(receipt)
    if not args.dry:
        (REPO_ROOT / receipt_relpath).parent.mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / receipt_relpath).write_bytes(receipt_bytes)

    print(json.dumps({
        "dry": args.dry, "pair_scope": args.pair_scope, "written": written, "receipt": receipt_relpath,
        "receipt_sha256": sha_bytes(receipt_bytes), "pairs_considered": pairs_considered,
        "pairs_written": len(table["rows"]), "pairs_skipped": len(table["skipped"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
