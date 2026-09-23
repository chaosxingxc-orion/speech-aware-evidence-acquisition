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
   three-field ``task_target`` (``NODE:DELTA-KIND:TARGET``);
   ``associated_facet_ids`` is the bare ``TARGET`` (what a candidate-bound
   route actually intersects against); and one further curation rule drops
   any statement repeating six or more consecutive tokens of a construction
   transcript (``--construction-transcripts``; counts reported, no text
   printed or persisted). ``--schema-version 1`` keeps every pre-S3-4s byte.
4. Loads version t-1's authored rows (``--predecessor``, or the literal
   string ``none`` for iteration 1) and keeps them VERBATIM as the base of
   version t's set (append-only).
5. Dedups the whole set (predecessor rows first, in their existing order,
   then new candidates in input order) by EXACT normalised text, then by
   token-Jaccard >= 0.8 against every earlier SURVIVOR: a match drops the
   later row and merges its ``provenance_refs``/``source_sample_ids`` into
   the survivor; predecessor rows are never edited even when they absorb a
   new row's provenance.
6. Writes the merged, sorted rows to ``--out-authored``.
7. With ``--release <registration.json> --repo-root <path> --data-root
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
#: The per-row field names a JSONL transcript file may carry its text in.
#: Their presence at the TOP level of a parsed file is what tells one
#: JSONL row apart from a whole-file {sample_id: text} object.
_ROW_TEXT_FIELDS = frozenset({"text", "transcript", "sentence"})
RELEASE_PINS_SCHEMA = "saea-reviewed-semantic-store-release-pins-v2"
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

    ``associated_facet_ids`` is the TARGET itself, not a
    ``stage3-delta-target:`` prefixed form: a candidate-bound route
    intersects a row's Perception candidate INTENT ids against exactly this
    field (``rails.stage3_delta_supply.select_stage3_delta_values``), so a
    prefixed id could never intersect one and the store would be unroutable.
    The facet DIMENSION stays ``stage3-delta-target``
    (``rails.semantic_knowledge_build.STAGE3_DELTA_DIMENSION``), which is
    where the namespace lives.
    """

    candidates: list[dict[str, object]] = []
    counts = {
        "total": 0, "legal": 0, "illegal": 0, "unmatched_pair": 0,
        "blocks_total": 0, "blocks_legal": 0, "blocks_illegal": 0,
        "blocks_contained": 0,
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
            counts["blocks_legal"] += 1
            per_node[block.node] += 1
            kept += 1
            candidates.append(
                {
                    "value_id": f"delta:{iteration}:{block.statement_sha256()[:12]}",
                    "content": block.statement,
                    "associated_facet_ids": [block.target],
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


def curate(
    *,
    predecessor_rows: Sequence[Mapping[str, object]],
    candidate_rows: Sequence[Mapping[str, object]],
    jaccard_threshold: float = 0.8,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Append-only curation: predecessor rows verbatim, then new candidates,
    deduped by exact normalised text and by token-Jaccard against every
    earlier survivor. Returns ``(survivors, counts)``."""

    survivors: list[dict[str, object]] = []
    normalised: list[str] = []
    tokens: list[frozenset[str]] = []
    counts = {"predecessor": 0, "new_accepted": 0, "exact_duplicate": 0, "near_duplicate": 0}

    def _absorb(index: int, row: Mapping[str, object]) -> None:
        survivor = survivors[index]
        merged_provenance = sorted(set(survivor["provenance_refs"]) | set(row["provenance_refs"]))
        merged_sources = sorted(set(survivor["source_sample_ids"]) | set(row["source_sample_ids"]))
        survivor["provenance_refs"] = merged_provenance
        survivor["source_sample_ids"] = merged_sources

    for row in predecessor_rows:
        survivors.append(dict(row))
        normalised.append(_normalise(str(row["content"])))
        tokens.append(_tokens(str(row["content"])))
        counts["predecessor"] += 1

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
        survivors.append(dict(row))
        normalised.append(row_normalised)
        tokens.append(row_tokens)
        counts["new_accepted"] += 1

    survivors.sort(key=lambda row: str(row["value_id"]))
    return survivors, counts


def write_authored_document(
    path: Path, *, iteration: int, rows: Sequence[Mapping[str, object]],
    schema: str = AUTHORED_SCHEMA,
) -> str:
    document = {"schema": schema, "iteration": iteration, "rows": list(rows)}
    raw = canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--advantage-outputs", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--predecessor", default="none")
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-authored", required=True, type=Path)
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
        "--construction-transcripts", default=None, type=Path,
        help=(
            "schema version 2 only: the construction rows' transcripts, read ONLY "
            "to reject statements that repeat six or more consecutive transcript "
            "tokens. Reduced to token n-grams on read; no text is printed or "
            "persisted. Omitting it disables the rule and the report says so."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.iteration < 1:
        raise Stage3DeltaStoreError("--iteration must be >= 1")

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
    survivors, curation_counts = curate(
        predecessor_rows=predecessor_rows,
        candidate_rows=candidates,
        jaccard_threshold=args.jaccard_threshold,
    )
    out_sha256 = write_authored_document(
        args.out_authored, iteration=args.iteration, rows=survivors,
        schema=authored_schema,
    )

    report = {
        "schema": "saea-stage3-delta-curation-report-v1",
        "iteration": args.iteration,
        "schema_version": args.schema_version,
        "authored_schema": authored_schema,
        "containment": containment,
        "parse": parse_counts,
        "curation": curation_counts,
        "survivor_count": len(survivors),
        "out_authored": {"relpath": str(args.out_authored), "sha256": out_sha256},
    }
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
