#!/usr/bin/env python3
"""CLI: Stage-3 S3-5, the append-only delta store curator (ACE grow-and-
refine; `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-
engineering.md` section S3-5).

MODEL-FREE. Zero frozen-core, tool, embedding, GPU or network contacts:
every byte this script reads is an already-sealed local file (S3-4's
advantage-contact outputs and S3-3's pairs.json), and everything it writes
is pure Python curation over that text.

What it does
------------
1. Parses each ADV-t response (``--advantage-outputs``, one JSON object per
   line: ``{"sample_id", "response_text", "disagreement"}``) with
   ``rails.stage3_advantage.parse_advantage_statement``; illegal statements
   are dropped, counted, never raised.
2. Joins each legal statement to its row's best/worst sample indices
   through S3-3's ``--pairs pairs.json``
   (``rails.stage3_advantage.load_advantage_pairs``).
3. Builds one candidate authored row per surviving statement: ``value_id``
   ``delta:<iteration>:<sha256(statement)[:12]>``, ``content`` the
   statement, ``associated_facet_ids`` ``(stage3-delta-target:<TARGET>,)``,
   ``source_sample_ids`` ``(<row sample_id>,)``, ``provenance_refs``
   ``(advantage:<run>:<row>:<best>:<worst>,)``, ``task_target``
   ``"<DELTA-KIND>:<TARGET>"``, ``prior_score`` the row's ``disagreement``.

   S3-4s (``--schema-version 2``, the DEFAULT; owner decision 106): the v2
   parser reads one to three NODE-attributed blocks per contact, so one
   contact yields up to three rows; each row carries ``node_target`` and a
   three-field ``task_target`` (``NODE:DELTA-KIND:TARGET``); and one further
   curation rule drops any statement repeating six or more consecutive
   tokens of a construction transcript (``--construction-transcripts``;
   counts reported, no text printed or persisted). ``--schema-version 1``
   keeps every pre-S3-4s byte.

   S3-5 revision v1r (``--facet-rule``, 2026-09-23): what goes into
   ``associated_facet_ids`` -- the ONLY field a candidate-bound route
   intersects against the row's Perception candidate INTENT ids.

   * ``source-intent`` (the DEFAULT for schema 2) writes the ordered,
     de-duplicated union of (a) the construction GOLD INTENT id
     (``<scenario>_<action>``) of every source row the statement was drawn
     from (``--gold-intents``) and (b) the bare ``TARGET`` when ``TARGET`` is
     itself a legal intent id (``--intent-vocabulary``; the default
     vocabulary is the distinct values of the gold map). A slot type never
     becomes a facet.
   * ``target-only`` is the pre-v1r rule -- the bare ``TARGET``, whatever it
     is -- kept so a released store can be reproduced byte for byte.

   The v1 store measured 121 of 379 rows reachable by ANY of the 60
   registered SLURP candidate intents (solver 11 of 151), because the 147
   slot-contract rows carry a SLOT TYPE in ``TARGET``; under
   ``source-intent`` every row carries at least one reachable facet.
4. Loads version t-1's authored rows (``--predecessor``, or the literal
   string ``none`` for iteration 1) and keeps them VERBATIM as the base of
   version t's set (append-only).

   S3-6 retirement (``--retire-value-ids``, owner decision 83): append-only
   is AMENDED exactly as that decision prescribes -- "a delta whose target
   scenario shows a net harm beyond the null band is retired in version
   t+1". The named predecessor rows are dropped from version t's set and
   their ids are recorded in the curation report. Dropping them is not
   enough on its own: version t is curated from the SAME advantage outputs,
   so every retired statement would be re-proposed as a fresh candidate and
   silently reinstated under a new iteration's ``value_id``. A retired row
   is therefore kept as a TOMBSTONE for the dedup comparison only -- a
   candidate that is an exact-normalised or Jaccard match of one is dropped
   and counted, never emitted. Without the flag not one byte moves, so
   ``--schema-version 1`` and every already-released store still reproduce
   exactly.
5. Dedups the whole set (predecessor rows first, in their existing order,
   then new candidates in input order) by EXACT normalised text, then by
   token-Jaccard >= 0.8 against every earlier SURVIVOR: a match drops the
   later row and merges its ``provenance_refs``/``source_sample_ids`` into
   the survivor; predecessor rows are never edited even when they absorb a
   new row's provenance.
6. Writes the merged, sorted rows to ``--out-authored``.
7. With ``--out-source``, ALSO writes the release-ready wrapper of that
   document (``build_authored_source_document``): the authored rows
   verbatim inside the shared ``saea-authored-semantic-knowledge-source-v1``
   envelope, which is the only shape
   ``core.semantic_knowledge_preparation.prepare_semantic_knowledge_store``
   accepts as an ``authored_source``. The curated document itself is NOT
   that shape (its schema names the curation, it carries ``iteration``, and
   it names no builder policy or split identity), so a release registration
   must pin the WRAPPER, never ``--out-authored`` directly. Writing both in
   one process is what keeps the release fail-closed: if curation ever
   stopped being deterministic, the wrapper's bytes would move with it and
   the preparer would refuse the pin instead of releasing different content.
8. With ``--release <registration.json> --repo-root <path> --data-root
   <path>``, releases the compiled snapshot through
   ``core.semantic_knowledge_preparation.prepare_semantic_knowledge_store``
   into the registration's own ``output_namespace``
   (``knowledge/slurp/semantic/stage3-deltas-v<t>/``) and writes a
   release-pins document (``--release-pins <path>``) in the form of
   ``docs/readiness/2026-09-17-slurp-semantic-store-release-pins-v2.json``.

Console output NEVER prints statement text, gold, or any model output --
only ids, counts and digests (the same discipline the study's exposure
ledger and every receipt in this repository keep).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_SRC = Path(__file__).resolve().parent.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from speech_aware_evidence_acquisition.rails.hashing import (  # noqa: E402
    canonical_json_bytes,
)
from speech_aware_evidence_acquisition.rails.stage3_advantage import (  # noqa: E402
    LEGAL_DELTA_NODES,
    Stage3AdvantageError,
    load_advantage_pairs,
    parse_advantage_statement,
    parse_advantage_statements_v2,
)

AUTHORED_SCHEMA = "saea-stage3-authored-deltas-v1"
#: S3-4s (owner decision 106, 2026-09-23): the NODE-TARGETED authored
#: document. One further row key (``node_target``), a three-field
#: ``task_target`` (``NODE:DELTA-KIND:TARGET``), and one further curation
#: rule (the six-token containment check below). Everything else -- the
#: ``value_id`` form, the append-only predecessor rule, the exact-normalised
#: and Jaccard dedup, the provenance merge -- is unchanged.
AUTHORED_SCHEMA_V2 = "saea-stage3-authored-deltas-v2"
#: The containment rule's span length (spec S3-4s): a statement that repeats
#: six or more CONSECUTIVE tokens of any construction-row transcript is a
#: transcript fragment, not a lesson, and is dropped at curation. Five or
#: fewer is a phrasing pattern and is allowed, as are slot values and intent
#: names of any length that do not reach six consecutive tokens.
CONTAINMENT_SPAN_TOKENS = 6
#: S3-5 revision v1r: the two ``associated_facet_ids`` rules. See the module
#: docstring; :func:`facet_ids_for_statement` is the whole of both.
FACET_RULE_SOURCE_INTENT = "source-intent"
FACET_RULE_TARGET_ONLY = "target-only"
FACET_RULES = (FACET_RULE_SOURCE_INTENT, FACET_RULE_TARGET_ONLY)
#: The per-row field names a JSONL transcript file may carry its text in.
#: Their presence at the TOP level of a parsed file is what tells one
#: JSONL row apart from a whole-file {sample_id: text} object.
_ROW_TEXT_FIELDS = frozenset({"text", "transcript", "sentence"})
RELEASE_PINS_SCHEMA = "saea-reviewed-semantic-store-release-pins-v2"
#: The shared envelope every released authored semantic store is read
#: from (``core.semantic_knowledge_preparation.SOURCE_SCHEMA``; the
#: intent-boundaries and slot-contracts releases use the same one). Its
#: four top-level keys are checked for EXACT equality there, so the
#: wrapper can carry no further field -- the provenance that pins the
#: authored document it was built from lives in the wrap receipt beside
#: it, never inside the envelope.
AUTHORED_SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
#: The wrap receipt: authored document -> released source document, by
#: SHA-256. Written beside the wrapper, never read by the preparer.
SOURCE_WRAP_RECEIPT_SCHEMA = "saea-stage3-delta-source-wrap-receipt-v1"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
_WORD = re.compile(r"[a-z0-9]+")


class Stage3DeltaStoreError(RuntimeError):
    """Curation input is malformed."""


def _normalise(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower()))


def _token_sequence(text: str) -> list[str]:
    """The ORDERED normalised tokens of one string (the containment rule
    needs order; :func:`_tokens` deliberately does not)."""

    return _WORD.findall(text.lower())


def _ngrams(tokens: Sequence[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def load_construction_spans(
    path: Path | None, *, span: int = CONTAINMENT_SPAN_TOKENS
) -> tuple[set, dict[str, int]]:
    """The set of ``span``-token n-grams of the construction rows'
    transcripts, plus counts.

    THE ONLY PLACE this CLI reads utterance text. The transcripts are read,
    reduced to normalised token n-grams and thrown away: no transcript, no
    fragment of one and no token is printed, returned as text or written to
    any artifact -- only the n-gram SET, which is used to REJECT statements,
    and the counts in the report. The file is one JSON object per line
    (``{"sample_id": ..., "text": ...}``) or one JSON object mapping sample
    id to text; it is a root preparation over the construction roster (the
    same rows S3-4 already showed the core), never a repository artifact.

    ``None`` -- the default -- returns an empty set and a zero count, which
    disables the rule and says so in the report rather than silently passing
    every statement as if it had been checked.
    """

    if path is None:
        return set(), {"transcripts": 0, "spans": 0, "span_tokens": span}
    raw = path.read_text(encoding="utf-8")
    texts: list[str] = []
    # Two accepted shapes, told apart by CONTENT rather than by a line count:
    # a whole-file JSON object mapping sample id to text (no row-field key),
    # or one JSON row per line carrying a row-field key.
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        document = None
    if isinstance(document, Mapping) and not (_ROW_TEXT_FIELDS & set(document)):
        texts = [value for value in document.values() if isinstance(value, str)]
    else:
        for line_number, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise Stage3DeltaStoreError(
                    f"{path}:{line_number} is not valid JSON: {error}"
                ) from error
            if isinstance(row, Mapping):
                value = row.get("text", row.get("transcript", row.get("sentence")))
                if isinstance(value, str):
                    texts.append(value)
                    continue
            raise Stage3DeltaStoreError(
                f"{path}:{line_number} carries no transcript text field"
            )
    spans: set = set()
    for value in texts:
        spans |= _ngrams(_token_sequence(value), span)
    return spans, {"transcripts": len(texts), "spans": len(spans), "span_tokens": span}


def contains_transcript_span(
    statement: str, spans: set, *, span: int = CONTAINMENT_SPAN_TOKENS
) -> bool:
    """Does ``statement`` repeat ``span`` or more CONSECUTIVE transcript
    tokens? Pure, total and text-free in its result (a bool)."""

    if not spans:
        return False
    return bool(_ngrams(_token_sequence(statement), span) & spans)


def load_gold_intents(path: Path) -> dict[str, str]:
    """The construction rows' gold intent ids, keyed by sample id.

    A JSON object mapping ``sample_id`` to ``<scenario>_<action>``. Read
    model-free and used ONLY as a routing key over the CONSTRUCTION
    population: the gold of the population a cell is READ on never enters
    this file, this store or any runtime path -- exactly as every other
    TRAIN-derived store of this study (``slot-contracts``,
    ``intent-boundaries``, ``train-exemplars``) carries TRAIN intent ids as
    facet ids. No value is printed by this CLI.
    """

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or not document:
        raise Stage3DeltaStoreError(f"{path} must be a non-empty JSON object")
    intents: dict[str, str] = {}
    for sample_id, value in document.items():
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3DeltaStoreError(f"{path} has a non-string sample id")
        if not isinstance(value, str) or not value:
            raise Stage3DeltaStoreError(
                f"{path} maps a sample id to something that is not an intent id"
            )
        intents[sample_id] = value
    return intents


def load_intent_vocabulary(
    path: Path | None, *, gold_intents: Mapping[str, str]
) -> frozenset[str]:
    """The LEGAL intent ids -- the vocabulary a Perception candidate list can
    ever name, and therefore the only ``TARGET`` values worth keeping as a
    facet under ``source-intent``.

    ``path`` accepts the registered SLURP candidate catalog
    (``{"profiles": [{"candidate_id": ...}, ...]}``), a plain JSON list of
    ids, or a JSON object keyed by id. ``None`` -- the default -- falls back
    to the distinct values of the gold map, which is the vocabulary the
    construction population itself attests.
    """

    if path is None:
        return frozenset(gold_intents.values())
    document = json.loads(path.read_text(encoding="utf-8"))
    ids: list[str] = []
    if isinstance(document, Mapping) and isinstance(document.get("profiles"), list):
        for index, profile in enumerate(document["profiles"]):
            if not isinstance(profile, Mapping) or not isinstance(
                profile.get("candidate_id"), str
            ):
                raise Stage3DeltaStoreError(
                    f"{path} profiles[{index}] carries no candidate_id"
                )
            ids.append(profile["candidate_id"])
    elif isinstance(document, Mapping):
        ids = [key for key in document if isinstance(key, str) and key]
    elif isinstance(document, list):
        ids = [item for item in document if isinstance(item, str) and item]
    else:
        raise Stage3DeltaStoreError(f"{path} is not an intent vocabulary")
    if not ids:
        raise Stage3DeltaStoreError(f"{path} names no intent id")
    return frozenset(ids)


def facet_ids_for_statement(
    *,
    sample_ids: Sequence[str],
    target: str,
    facet_rule: str,
    gold_intents: Mapping[str, str] = {},
    legal_intents: frozenset[str] = frozenset(),
) -> list[str]:
    """The ``associated_facet_ids`` of one curated row: PURE, total, ordered
    and de-duplicated.

    ``target-only`` is the bare ``TARGET``, whatever it is (the pre-v1r
    rule). ``source-intent`` is the construction gold intent id of every
    source row, in source order, then ``TARGET`` when ``TARGET`` is itself a
    legal intent id -- so an intent-boundary row keeps its target intent as a
    facet and a slot-contract row whose target is a SLOT TYPE gets the intent
    its lesson was actually learned on instead of an id no Perception
    candidate list can ever name.

    Returns ``[]`` when ``source-intent`` can attest nothing; the caller
    drops that row and counts it rather than releasing an unroutable value.
    """

    if facet_rule == FACET_RULE_TARGET_ONLY:
        return [target]
    if facet_rule != FACET_RULE_SOURCE_INTENT:
        raise Stage3DeltaStoreError(f"unknown facet rule {facet_rule!r}")
    facets: list[str] = []
    for sample_id in sample_ids:
        intent = gold_intents.get(sample_id)
        if isinstance(intent, str) and intent and intent not in facets:
            facets.append(intent)
    if target in legal_intents and target not in facets:
        facets.append(target)
    return facets


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _read_jsonl(path: Path) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            document = json.loads(stripped)
        except json.JSONDecodeError as error:
            raise Stage3DeltaStoreError(
                f"{path}:{line_number} is not valid JSON: {error}"
            ) from error
        if not isinstance(document, Mapping):
            raise Stage3DeltaStoreError(f"{path}:{line_number} must be a JSON object")
        rows.append(document)
    return rows


def build_candidate_rows(
    *,
    advantage_outputs: Sequence[Mapping[str, object]],
    pairs_by_sample: Mapping[str, object],
    run_id: str,
    iteration: int,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Parse and join every ADV-t output into a candidate authored row.

    Returns ``(rows, counts)``; ``counts`` names ``total``, ``legal`` and
    ``illegal`` -- never the statement text of an illegal row.
    """

    candidates: list[dict[str, object]] = []
    counts = {"total": 0, "legal": 0, "illegal": 0, "unmatched_pair": 0}
    for entry in advantage_outputs:
        counts["total"] += 1
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3DeltaStoreError("advantage-outputs row is missing sample_id")
        pair = pairs_by_sample.get(sample_id)
        if pair is None:
            counts["unmatched_pair"] += 1
            continue
        statement = parse_advantage_statement(entry.get("response_text"))
        if not statement.legal:
            counts["illegal"] += 1
            continue
        disagreement = entry.get("disagreement")
        if isinstance(disagreement, bool) or not isinstance(disagreement, (int, float)):
            raise Stage3DeltaStoreError(
                f"advantage-outputs row for {sample_id!r} has no numeric disagreement"
            )
        counts["legal"] += 1
        value_id = f"delta:{iteration}:{statement.statement_sha256()[:12]}"
        candidates.append(
            {
                "value_id": value_id,
                "content": statement.statement,
                "associated_facet_ids": [f"stage3-delta-target:{statement.target}"],
                "source_sample_ids": [sample_id],
                "provenance_refs": [
                    f"advantage:{run_id}:{sample_id}:"
                    f"{pair.best.sample_index}:{pair.worst.sample_index}"
                ],
                "task_target": f"{statement.delta_kind}:{statement.target}",
                "prior_score": float(disagreement),
            }
        )
    return candidates, counts


def build_candidate_rows_v2(
    *,
    advantage_outputs: Sequence[Mapping[str, object]],
    pairs_by_sample: Mapping[str, object],
    run_id: str,
    iteration: int,
    transcript_spans: set = frozenset(),
    facet_rule: str = FACET_RULE_TARGET_ONLY,
    gold_intents: Mapping[str, str] = {},
    legal_intents: frozenset[str] = frozenset(),
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """S3-4s: parse and join every ADV-t output into NODE-TARGETED rows.

    One contact now yields one to THREE blocks
    (``rails.stage3_advantage.parse_advantage_statements_v2``), so one
    advantage output can produce up to three candidate rows -- each with its
    own ``node_target``, its own ``task_target``
    (``NODE:DELTA-KIND:TARGET``) and its own ``value_id`` over its own
    statement. Illegal blocks are dropped, counted, never raised. A
    statement that repeats six or more consecutive tokens of a construction
    transcript is dropped by the containment rule, counted separately.

    ``associated_facet_ids`` is a BARE id, not a
    ``stage3-delta-target:`` prefixed form: a candidate-bound route
    intersects a row's Perception candidate INTENT ids against exactly this
    field (``rails.stage3_delta_supply.select_stage3_delta_values``), so a
    prefixed id could never intersect one and the store would be unroutable.
    The facet DIMENSION stays ``stage3-delta-target``
    (``rails.semantic_knowledge_build.STAGE3_DELTA_DIMENSION``), which is
    where the namespace lives. WHICH bare id is
    :func:`facet_ids_for_statement`'s ``facet_rule``: the v1r default
    ``source-intent`` (the source row's gold intent, plus TARGET when TARGET
    is a legal intent) or the pre-v1r ``target-only``.
    """

    candidates: list[dict[str, object]] = []
    counts = {
        "total": 0, "legal": 0, "illegal": 0, "unmatched_pair": 0,
        "blocks_total": 0, "blocks_legal": 0, "blocks_illegal": 0,
        "blocks_contained": 0, "blocks_missing_gold": 0, "blocks_no_facet": 0,
    }
    per_node = {node: 0 for node in LEGAL_DELTA_NODES}
    for entry in advantage_outputs:
        counts["total"] += 1
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise Stage3DeltaStoreError("advantage-outputs row is missing sample_id")
        pair = pairs_by_sample.get(sample_id)
        if pair is None:
            counts["unmatched_pair"] += 1
            continue
        parsed = parse_advantage_statements_v2(entry.get("response_text"))
        counts["blocks_total"] += len(parsed.blocks)
        legal_blocks = parsed.legal_blocks()
        counts["blocks_illegal"] += len(parsed.blocks) - len(legal_blocks)
        if not legal_blocks:
            counts["illegal"] += 1
            continue
        disagreement = entry.get("disagreement")
        if isinstance(disagreement, bool) or not isinstance(disagreement, (int, float)):
            raise Stage3DeltaStoreError(
                f"advantage-outputs row for {sample_id!r} has no numeric disagreement"
            )
        kept = 0
        for block in legal_blocks:
            if contains_transcript_span(block.statement, transcript_spans):
                counts["blocks_contained"] += 1
                continue
            if (
                facet_rule == FACET_RULE_SOURCE_INTENT
                and sample_id not in gold_intents
            ):
                counts["blocks_missing_gold"] += 1
            facet_ids = facet_ids_for_statement(
                sample_ids=(sample_id,),
                target=block.target,
                facet_rule=facet_rule,
                gold_intents=gold_intents,
                legal_intents=legal_intents,
            )
            if not facet_ids:
                # An unroutable value: no candidate-bound route could ever
                # select it and DeltaCandidate.validate refuses an empty
                # facet tuple. Dropped and counted, never raised.
                counts["blocks_no_facet"] += 1
                continue
            counts["blocks_legal"] += 1
            per_node[block.node] += 1
            kept += 1
            candidates.append(
                {
                    "value_id": f"delta:{iteration}:{block.statement_sha256()[:12]}",
                    "content": block.statement,
                    "associated_facet_ids": facet_ids,
                    "node_target": block.node,
                    "source_sample_ids": [sample_id],
                    "provenance_refs": [
                        f"advantage:{run_id}:{sample_id}:"
                        f"{pair.best.sample_index}:{pair.worst.sample_index}"
                        f":{block.block_index}"
                    ],
                    "task_target": block.task_target(),
                    "prior_score": float(disagreement),
                }
            )
        if kept:
            counts["legal"] += 1
        else:
            counts["illegal"] += 1
    counts.update({f"blocks_node_{node}": per_node[node] for node in LEGAL_DELTA_NODES})
    return candidates, counts


_AUTHORED_ROW_KEYS = {
    "value_id", "content", "associated_facet_ids", "source_sample_ids",
    "provenance_refs", "task_target", "prior_score",
}
_AUTHORED_ROW_KEYS_V2 = _AUTHORED_ROW_KEYS | {"node_target"}


def _validate_authored_row(
    row: Mapping[str, object], *, field: str, required: set = _AUTHORED_ROW_KEYS
) -> dict[str, object]:
    if not isinstance(row, Mapping) or set(row) != required:
        raise Stage3DeltaStoreError(f"{field} has the wrong fields")
    return dict(row)


def load_predecessor_rows(
    predecessor: str | None, *, schema_version: int = 1
) -> list[dict[str, object]]:
    required = _AUTHORED_ROW_KEYS_V2 if schema_version == 2 else _AUTHORED_ROW_KEYS
    if predecessor is None or predecessor == "none":
        return []
    document = json.loads(Path(predecessor).read_text(encoding="utf-8"))
    if not isinstance(document, Mapping) or not isinstance(document.get("rows"), list):
        raise Stage3DeltaStoreError(f"{predecessor} must be an authored-deltas document")
    return [
        _validate_authored_row(row, field=f"predecessor rows[{index}]", required=required)
        for index, row in enumerate(document["rows"])
    ]


def load_retired_value_ids(path: Path) -> list[str]:
    """The value ids version t+1 retires (S3-6, owner decision 83).

    Accepts the retention document
    ``scripts/build_slurp_stage3_delta_retention.py`` writes (schema
    ``saea-stage3-delta-retention-v1``: ``retired_value_ids``, or a
    ``decisions`` list carrying ``decision == "RETIRE"``), or a plain JSON
    list of ids. Ordered and de-duplicated; ids only, never a statement.
    """

    document = json.loads(path.read_text(encoding="utf-8"))
    raw: Sequence[object]
    if isinstance(document, list):
        raw = document
    elif isinstance(document, Mapping) and isinstance(
        document.get("retired_value_ids"), list
    ):
        raw = document["retired_value_ids"]
    elif isinstance(document, Mapping) and isinstance(document.get("decisions"), list):
        raw = [
            entry.get("value_id")
            for entry in document["decisions"]
            if isinstance(entry, Mapping) and entry.get("decision") == "RETIRE"
        ]
    else:
        raise Stage3DeltaStoreError(
            f"{path} is not a retention document or a list of value ids"
        )
    ids: list[str] = []
    for value in raw:
        if not isinstance(value, str) or not value:
            raise Stage3DeltaStoreError(f"{path} names a non-string value id")
        if value not in ids:
            ids.append(value)
    if not ids:
        raise Stage3DeltaStoreError(f"{path} retires no value id")
    return ids


def partition_retired(
    rows: Sequence[Mapping[str, object]], retired_value_ids: Sequence[str]
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    """Split the predecessor rows into the ones version t keeps and the ones
    it retires. PURE; returns ``(kept, retired, report)``.

    ``report`` names counts and ids ONLY (``requested``, ``applied``,
    ``applied_value_ids``, ``not_present_value_ids``): a retired row's
    statement never reaches it.
    """

    wanted = list(dict.fromkeys(retired_value_ids))
    present = {str(row["value_id"]) for row in rows}
    kept: list[dict[str, object]] = []
    retired: list[dict[str, object]] = []
    for row in rows:
        if str(row["value_id"]) in wanted:
            retired.append(dict(row))
        else:
            kept.append(dict(row))
    report = {
        "requested": len(wanted),
        "applied": len(retired),
        "applied_value_ids": sorted(str(row["value_id"]) for row in retired),
        "not_present_value_ids": [
            value_id for value_id in wanted if value_id not in present
        ],
        "predecessor_rows_in": len(rows),
        "predecessor_rows_kept": len(kept),
    }
    return kept, retired, report


def _matches_pool(
    normalised: str,
    tokens: frozenset[str],
    pool_normalised: Sequence[str],
    pool_tokens: Sequence[frozenset[str]],
    *,
    jaccard_threshold: float,
) -> bool:
    """Is this candidate an exact-normalised or Jaccard match of anything in
    ``pool``? The same two tests :func:`curate` applies to its survivors,
    stated once so the tombstone scan cannot drift from them."""

    for index, existing in enumerate(pool_normalised):
        if existing == normalised:
            return True
        if _jaccard(pool_tokens[index], tokens) >= jaccard_threshold:
            return True
    return False


def curate(
    *,
    predecessor_rows: Sequence[Mapping[str, object]],
    candidate_rows: Sequence[Mapping[str, object]],
    jaccard_threshold: float = 0.8,
    merge_facets: bool = False,
    retired_rows: Sequence[Mapping[str, object]] = (),
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Append-only curation: predecessor rows verbatim, then new candidates,
    deduped by exact normalised text and by token-Jaccard against every
    earlier survivor. Returns ``(survivors, counts)``.

    ``merge_facets`` (S3-5 revision v1r, set by the ``source-intent`` rule and
    NEVER by ``target-only``) extends the absorb step: a survivor that
    absorbs a duplicate also takes on that duplicate's facet ids, in the
    survivor's own order first. Under ``source-intent`` a facet id records
    WHICH construction intent the statement was learned on, so a statement
    two rows independently produced must route on both intents; under
    ``target-only`` the facet is a restatement of TARGET and merging it would
    change nothing but the bytes, which is why the pre-v1r behaviour is the
    default here.

    ``retired_rows`` (S3-6, owner decision 83) are TOMBSTONES: rows version
    t+1 has retired, which are never emitted and never absorb provenance,
    but against which every new candidate is still compared. A candidate
    matching one is dropped and counted as ``retired_suppressed``, so a
    retired lesson cannot walk back in under a fresh iteration's value id.
    Survivors are scanned FIRST, so a candidate that also matches a LIVE row
    is absorbed there as before: retirement removes a statement, it does not
    poison an unrelated survivor that happens to be close to it."""

    survivors: list[dict[str, object]] = []
    normalised: list[str] = []
    tokens: list[frozenset[str]] = []
    counts = {
        "predecessor": 0, "new_accepted": 0, "exact_duplicate": 0,
        "near_duplicate": 0, "facet_merges": 0, "retired_tombstones": 0,
        "retired_suppressed": 0,
    }

    def _absorb(index: int, row: Mapping[str, object]) -> None:
        survivor = survivors[index]
        merged_provenance = sorted(set(survivor["provenance_refs"]) | set(row["provenance_refs"]))
        merged_sources = sorted(set(survivor["source_sample_ids"]) | set(row["source_sample_ids"]))
        survivor["provenance_refs"] = merged_provenance
        survivor["source_sample_ids"] = merged_sources
        if not merge_facets:
            return
        facets = list(survivor["associated_facet_ids"])
        added = [
            facet for facet in row["associated_facet_ids"] if facet not in facets
        ]
        if added:
            survivor["associated_facet_ids"] = facets + added
            counts["facet_merges"] += 1

    for row in predecessor_rows:
        survivors.append(dict(row))
        normalised.append(_normalise(str(row["content"])))
        tokens.append(_tokens(str(row["content"])))
        counts["predecessor"] += 1

    retired_normalised = [_normalise(str(row["content"])) for row in retired_rows]
    retired_tokens = [_tokens(str(row["content"])) for row in retired_rows]
    counts["retired_tombstones"] = len(retired_normalised)

    for row in candidate_rows:
        text = str(row["content"])
        row_normalised = _normalise(text)
        row_tokens = _tokens(text)
        match_index = None
        for index, existing_normalised in enumerate(normalised):
            if existing_normalised == row_normalised:
                match_index = index
                counts["exact_duplicate"] += 1
                break
            if _jaccard(tokens[index], row_tokens) >= jaccard_threshold:
                match_index = index
                counts["near_duplicate"] += 1
                break
        if match_index is not None:
            _absorb(match_index, row)
            continue
        if _matches_pool(
            row_normalised, row_tokens, retired_normalised, retired_tokens,
            jaccard_threshold=jaccard_threshold,
        ):
            counts["retired_suppressed"] += 1
            continue
        survivors.append(dict(row))
        normalised.append(row_normalised)
        tokens.append(row_tokens)
        counts["new_accepted"] += 1

    survivors.sort(key=lambda row: str(row["value_id"]))
    return survivors, counts


def write_authored_document(
    path: Path, *, iteration: int, rows: Sequence[Mapping[str, object]],
    schema: str = AUTHORED_SCHEMA, facet_rule: str | None = None,
) -> str:
    """Write the curated document and return its SHA-256.

    ``facet_rule`` is recorded in the header, so a released store says on its
    face which rule attached its facets. It is written ONLY for a non-legacy
    rule: ``target-only`` leaves the header exactly as it was before S3-5
    revision v1r, which is what lets an earlier release be reproduced byte
    for byte.
    """

    document: dict[str, object] = {
        "schema": schema, "iteration": iteration, "rows": list(rows)
    }
    if facet_rule is not None and facet_rule != FACET_RULE_TARGET_ONLY:
        document["facet_rule"] = facet_rule
    raw = canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


#: Which registered builder compiles the rows of each authored schema
#: (``rails.semantic_knowledge_build``). The wrapper names the builder, so
#: this mapping -- not an operator-typed string -- is what puts the right
#: one in the released envelope.
BUILDER_POLICY_BY_AUTHORED_SCHEMA = {
    AUTHORED_SCHEMA: "saea-authored-stage3-deltas-v1",
    AUTHORED_SCHEMA_V2: "saea-authored-stage3-deltas-v2",
}
_ROW_KEYS_BY_AUTHORED_SCHEMA = {
    AUTHORED_SCHEMA: _AUTHORED_ROW_KEYS,
    AUTHORED_SCHEMA_V2: _AUTHORED_ROW_KEYS_V2,
}


def build_authored_source_document(
    document: Mapping[str, object],
    *,
    source_split_identity_hash: str,
    builder_policy_id: str | None = None,
) -> dict[str, object]:
    """Wrap one authored-deltas document (this CLI's own ``--out-authored``
    output, or the twin CLI's derangement of it) in the release-ready
    ``saea-authored-semantic-knowledge-source-v1`` envelope.

    PURE and MODEL-FREE: every row is carried over VERBATIM
    (``value_id``, ``content``, ``associated_facet_ids``,
    ``source_sample_ids``, ``provenance_refs``, ``task_target``,
    ``prior_score``, and ``node_target`` under the v2 schema), in the
    document's own row order, with its exact key set re-validated on the
    way through -- a row with a missing or extra field is refused here
    rather than deep inside the builder. Nothing is derived, renamed,
    reordered or dropped; the only new information is the envelope's own
    three header fields.

    ``builder_policy_id`` is DERIVED from the authored schema
    (:data:`BUILDER_POLICY_BY_AUTHORED_SCHEMA`); passing one is a
    cross-check that fails closed on a mismatch, never an override.
    """

    if not isinstance(document, Mapping):
        raise Stage3DeltaStoreError("the authored document must be a JSON object")
    schema = document.get("schema")
    if schema not in _ROW_KEYS_BY_AUTHORED_SCHEMA:
        raise Stage3DeltaStoreError(
            f"expected schema {AUTHORED_SCHEMA!r} or {AUTHORED_SCHEMA_V2!r}, "
            f"got {schema!r}"
        )
    if (
        not isinstance(source_split_identity_hash, str)
        or _SHA256_HEX.fullmatch(source_split_identity_hash) is None
    ):
        raise Stage3DeltaStoreError(
            "--source-split-identity-hash must be a lowercase 64-hex SHA-256"
        )
    expected_builder = BUILDER_POLICY_BY_AUTHORED_SCHEMA[schema]
    if builder_policy_id is not None and builder_policy_id != expected_builder:
        raise Stage3DeltaStoreError(
            f"{schema} rows are compiled by {expected_builder!r}, "
            f"not {builder_policy_id!r}"
        )
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Stage3DeltaStoreError("the authored document has no rows")
    required = _ROW_KEYS_BY_AUTHORED_SCHEMA[schema]
    return {
        "schema": AUTHORED_SOURCE_SCHEMA,
        "builder_policy_id": expected_builder,
        "source_split_identity_hash": source_split_identity_hash,
        "rows": [
            _validate_authored_row(row, field=f"rows[{index}]", required=required)
            for index, row in enumerate(rows)
        ],
    }


def default_source_receipt_path(out_path: Path) -> Path:
    """Where the wrap receipt lands when none is named: beside the wrapper."""

    return out_path.with_name(f"{out_path.stem}-wrap-receipt.json")


def write_authored_source(
    authored_path: Path,
    *,
    out_path: Path,
    source_split_identity_hash: str,
    builder_policy_id: str | None = None,
    receipt_path: Path | None = None,
) -> dict[str, object]:
    """Read one authored-deltas document, write its release-ready wrapper
    and the wrap receipt that pins BOTH digests, and return the receipt
    (plus the receipt's own pin) for the console report.

    Deterministic bytes on both files: canonical JSON, sorted keys, UTF-8,
    LF-safe (``write_bytes``, no newline translation), so re-running the
    curation and the wrap over the same inputs reproduces the digest a
    release registration pinned -- which is what lets
    ``prepare_semantic_knowledge_store`` fail closed rather than release
    content that moved.

    Ids, counts and digests only: no statement text is returned or printed.
    """

    raw_authored = authored_path.read_bytes()
    try:
        document = json.loads(raw_authored.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Stage3DeltaStoreError(
            f"{authored_path} is not valid JSON: {error}"
        ) from error
    source = build_authored_source_document(
        document,
        source_split_identity_hash=source_split_identity_hash,
        builder_policy_id=builder_policy_id,
    )
    raw_source = canonical_json_bytes(source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw_source)
    receipt = {
        "schema": SOURCE_WRAP_RECEIPT_SCHEMA,
        "authored": {
            "relpath": str(authored_path),
            "sha256": hashlib.sha256(raw_authored).hexdigest(),
            "authored_schema": str(document.get("schema")),
            "iteration": document.get("iteration"),
            "facet_rule": document.get("facet_rule"),
            "twin_of_seed": document.get("twin_of_seed"),
            "row_count": len(source["rows"]),
        },
        "source": {
            "relpath": str(out_path),
            "sha256": hashlib.sha256(raw_source).hexdigest(),
        },
        "builder_policy_id": source["builder_policy_id"],
        "source_split_identity_hash": source["source_split_identity_hash"],
    }
    raw_receipt = canonical_json_bytes(receipt)
    receipt_path = receipt_path or default_source_receipt_path(out_path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(raw_receipt)
    report = dict(receipt)
    report["receipt"] = {
        "relpath": str(receipt_path),
        "sha256": hashlib.sha256(raw_receipt).hexdigest(),
    }
    return report


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--advantage-outputs", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--predecessor", default="none")
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-authored", required=True, type=Path)
    parser.add_argument(
        "--out-source", default=None, type=Path,
        help=(
            "also write the release-ready wrapper of the curated document "
            "(schema saea-authored-semantic-knowledge-source-v1), which is what "
            "a release registration pins as its authored_source. Requires "
            "--source-split-identity-hash."
        ),
    )
    parser.add_argument(
        "--source-split-identity-hash", default=None,
        help=(
            "the split identity of the construction population the authored rows "
            "were drawn from; must equal the release registration's own "
            "source_split_identity_hash or the preparer refuses the source."
        ),
    )
    parser.add_argument(
        "--source-receipt", default=None, type=Path,
        help="wrap receipt path (default: <--out-source stem>-wrap-receipt.json)",
    )
    parser.add_argument("--release", default=None, type=Path)
    parser.add_argument("--data-root", default=None, type=Path)
    parser.add_argument("--release-pins", default=None, type=Path)
    parser.add_argument("--jaccard-threshold", default=0.8, type=float)
    parser.add_argument(
        "--schema-version", default=2, type=int, choices=(1, 2),
        help=(
            "2 (the default, S3-4s owner decision 106): NODE-TARGETED rows, the "
            "multi-block v2 advantage parser and the six-token containment rule. "
            "1 keeps the pre-S3-4s single-statement curation byte for byte."
        ),
    )
    parser.add_argument(
        "--facet-rule", default=None, choices=FACET_RULES,
        help=(
            "schema version 2 only: what goes into associated_facet_ids. "
            f"{FACET_RULE_SOURCE_INTENT!r} (the default) writes the source rows' "
            "construction gold intent ids plus TARGET when TARGET is a legal "
            f"intent id; {FACET_RULE_TARGET_ONLY!r} writes the bare TARGET, the "
            "pre-v1r rule, kept so a released store reproduces byte for byte. "
            "Schema version 1 always uses the target-only rule."
        ),
    )
    parser.add_argument(
        "--gold-intents", default=None, type=Path,
        help=(
            "the construction rows' gold intent ids, a JSON object mapping "
            "sample id to <scenario>_<action>. REQUIRED by --facet-rule "
            "source-intent. Read model-free; no value is printed or persisted "
            "other than as a routing facet id of the construction population."
        ),
    )
    parser.add_argument(
        "--intent-vocabulary", default=None, type=Path,
        help=(
            "the legal intent ids a TARGET may be kept as a facet under "
            "--facet-rule source-intent (the registered SLURP candidate "
            "catalog, a JSON list, or a JSON object keyed by id). Default: the "
            "distinct values of --gold-intents."
        ),
    )
    parser.add_argument(
        "--retire-value-ids", default=None, type=Path,
        help=(
            "S3-6 (owner decision 83): the retention document "
            "scripts/build_slurp_stage3_delta_retention.py writes (or a plain JSON "
            "list of value ids). The named PREDECESSOR rows are dropped from this "
            "version's set and their ids are recorded in the report; they are also "
            "kept as dedup tombstones so the same statements cannot re-enter as "
            "fresh candidates. Requires --predecessor."
        ),
    )
    parser.add_argument(
        "--construction-transcripts", default=None, type=Path,
        help=(
            "schema version 2 only: the construction rows' transcripts, read ONLY "
            "to reject statements that repeat six or more consecutive transcript "
            "tokens. Reduced to token n-grams on read; no text is printed or "
            "persisted. Omitting it disables the rule and the report says so."
        ),
    )
    return parser.parse_args(argv)


def resolve_facet_rule(requested: str | None, *, schema_version: int) -> str:
    """Which facet rule this run uses. Schema 1 is frozen on the pre-v1r
    rule and REFUSES an explicit ``source-intent``; schema 2 defaults to
    ``source-intent``."""

    if schema_version == 1:
        if requested == FACET_RULE_SOURCE_INTENT:
            raise Stage3DeltaStoreError(
                "--facet-rule source-intent requires --schema-version 2"
            )
        return FACET_RULE_TARGET_ONLY
    return requested or FACET_RULE_SOURCE_INTENT


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.iteration < 1:
        raise Stage3DeltaStoreError("--iteration must be >= 1")
    facet_rule = resolve_facet_rule(args.facet_rule, schema_version=args.schema_version)
    gold_intents: dict[str, str] = {}
    legal_intents: frozenset[str] = frozenset()
    if facet_rule == FACET_RULE_SOURCE_INTENT:
        if args.gold_intents is None:
            raise Stage3DeltaStoreError(
                "--facet-rule source-intent requires --gold-intents"
            )
        gold_intents = load_gold_intents(args.gold_intents)
        legal_intents = load_intent_vocabulary(
            args.intent_vocabulary, gold_intents=gold_intents
        )
    elif args.gold_intents is not None or args.intent_vocabulary is not None:
        raise Stage3DeltaStoreError(
            "--gold-intents and --intent-vocabulary are only meaningful with "
            "--facet-rule source-intent"
        )

    pairs = load_advantage_pairs(
        args.pairs, repo_root=args.repo_root, expected_rollout_run_id=None
    )
    pairs_by_sample = pairs.by_sample()
    advantage_outputs = _read_jsonl(args.advantage_outputs)
    containment = {"enabled": False, "transcripts": 0, "spans": 0, "span_tokens": 0}
    if args.schema_version == 2:
        spans, span_counts = load_construction_spans(args.construction_transcripts)
        containment = {"enabled": bool(spans), **span_counts}
        candidates, parse_counts = build_candidate_rows_v2(
            advantage_outputs=advantage_outputs,
            pairs_by_sample=pairs_by_sample,
            run_id=args.run_id,
            iteration=args.iteration,
            transcript_spans=spans,
            facet_rule=facet_rule,
            gold_intents=gold_intents,
            legal_intents=legal_intents,
        )
        authored_schema = AUTHORED_SCHEMA_V2
    else:
        candidates, parse_counts = build_candidate_rows(
            advantage_outputs=advantage_outputs,
            pairs_by_sample=pairs_by_sample,
            run_id=args.run_id,
            iteration=args.iteration,
        )
        authored_schema = AUTHORED_SCHEMA
    predecessor_rows = load_predecessor_rows(
        args.predecessor, schema_version=args.schema_version
    )
    retirement: dict[str, object] | None = None
    retired_rows: list[dict[str, object]] = []
    if args.retire_value_ids is not None:
        if not predecessor_rows:
            raise Stage3DeltaStoreError(
                "--retire-value-ids requires a --predecessor to retire rows from"
            )
        retired_value_ids = load_retired_value_ids(args.retire_value_ids)
        predecessor_rows, retired_rows, retirement = partition_retired(
            predecessor_rows, retired_value_ids
        )
        retirement["source"] = str(args.retire_value_ids)
    survivors, curation_counts = curate(
        predecessor_rows=predecessor_rows,
        candidate_rows=candidates,
        jaccard_threshold=args.jaccard_threshold,
        merge_facets=facet_rule == FACET_RULE_SOURCE_INTENT,
        retired_rows=retired_rows,
    )
    out_sha256 = write_authored_document(
        args.out_authored, iteration=args.iteration, rows=survivors,
        schema=authored_schema, facet_rule=facet_rule,
    )

    source_report = None
    if args.out_source is not None:
        if not args.source_split_identity_hash:
            raise Stage3DeltaStoreError(
                "--out-source requires --source-split-identity-hash"
            )
        source_report = write_authored_source(
            args.out_authored,
            out_path=args.out_source,
            source_split_identity_hash=args.source_split_identity_hash,
            receipt_path=args.source_receipt,
        )
    elif args.source_split_identity_hash:
        raise Stage3DeltaStoreError(
            "--source-split-identity-hash is only meaningful with --out-source"
        )

    facet_counts: dict[str, int] = {}
    for row in survivors:
        facet_counts[str(len(row["associated_facet_ids"]))] = (
            facet_counts.get(str(len(row["associated_facet_ids"])), 0) + 1
        )
    report = {
        "schema": "saea-stage3-delta-curation-report-v1",
        "iteration": args.iteration,
        "schema_version": args.schema_version,
        "authored_schema": authored_schema,
        "facet_rule": facet_rule,
        "facets": {
            "distinct": len(
                {facet for row in survivors for facet in row["associated_facet_ids"]}
            ),
            "per_row_histogram": facet_counts,
            "gold_intent_rows": len(gold_intents),
            "legal_intent_vocabulary": len(legal_intents),
        },
        "containment": containment,
        "parse": parse_counts,
        "curation": curation_counts,
        "survivor_count": len(survivors),
        "out_authored": {"relpath": str(args.out_authored), "sha256": out_sha256},
    }
    if retirement is not None:
        report["retirement"] = retirement
    if source_report is not None:
        report["authored_source"] = source_report
    if args.schema_version == 2:
        report["survivors_by_node"] = {
            node: sum(1 for row in survivors if row.get("node_target") == node)
            for node in LEGAL_DELTA_NODES
        }
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts/hashes only

    if args.release is not None:
        if args.data_root is None:
            raise Stage3DeltaStoreError("--release requires --data-root")
        from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
            prepare_semantic_knowledge_store,
        )

        result = prepare_semantic_knowledge_store(
            args.release, repo_root=args.repo_root, data_root=args.data_root
        )
        if args.release_pins is not None:
            pins_document = {
                "schema": RELEASE_PINS_SCHEMA,
                "status": "RELEASED_PENDING_RUNTIME_CONSUMPTION",
                "store": result,
            }
            args.release_pins.write_bytes(canonical_json_bytes(pins_document))
        print(json.dumps({"released": True}, indent=2))  # noqa: T201

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
