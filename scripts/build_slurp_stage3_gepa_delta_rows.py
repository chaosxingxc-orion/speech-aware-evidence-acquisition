#!/usr/bin/env python3
"""CLI: Stage-3 layer A, the GEPA arm's CURATION into the stage3-deltas store.

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer, GPU
and network contacts: every byte read is an already-sealed local file and
everything written is pure Python curation over that text.

A THIN SIBLING of ``scripts/build_slurp_stage3_delta_store.py``, never a second
copy of it. Everything that makes a stage3-deltas row what it is -- the
``value_id`` form, the append-only predecessor rule, the exact-normalised and
token-Jaccard dedup, the provenance merge, the facet rule, the six-token
transcript containment rule, the authored document writer and the release
source wrapper -- is IMPORTED from that module and used unchanged. What this
CLI adds is the one thing that differs between the two families:

* ADV-1 joins one advantage output to one disagreeing ROW (``pairs.json``), and
  a statement's ``source_sample_ids`` is that row, its ``prior_score`` that
  row's best-minus-worst mass, and its provenance
  ``advantage:<run>:<row>:<best>:<worst>:<block>``.
* GEPA joins one proposal output to one (scenario, node) GROUP (the prepared
  groups artifact), so a statement's ``source_sample_ids`` is the group's rows,
  its ``prior_score`` the group's mean disagreement mass, and its provenance
  ``gepa:<run>:<scenario>:<node>:<block>``.

The node invariant is the GEPA parser's, not this CLI's: a block that names a
node other than its group's is RETAINED and marked illegal by
``rails.stage3_gepa.parse_gepa_proposal`` and dropped here, counted.

Inputs: ``--proposal-outputs`` (one JSON object per line: ``{"group_id",
"response_text"}``, rendered from the sealed GEPA run by
``scripts/flights/batch/gepa_render_proposal_outputs.py``) and ``--groups`` (the
prepared artifact the flight itself was pinned to). Predecessor and retirement
are the ADV-1 flags, unchanged: ``--predecessor`` names the released v1r
authored document and ``--retire-value-ids`` the decision-83 retention document
``scripts/build_slurp_stage3_delta_retention.py`` writes over the CELL-1 read.

The report prints ids, counts and digests only. No statement text, utterance,
transcript, gold label or model output is printed or persisted anywhere but in
the curated document itself.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_SRC = REPO_ROOT / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from speech_aware_evidence_acquisition.rails.hashing import (  # noqa: E402
    canonical_json_bytes,
)
from speech_aware_evidence_acquisition.rails.stage3_gepa import (  # noqa: E402
    LEGAL_GEPA_NODES,
    parse_gepa_proposal,
)


def _load_base_curator():
    """Import the ADV-1 curator BY PATH.

    Not ``import scripts.build_slurp_stage3_delta_store``: a top-level
    ``scripts`` package exists in the shared virtual environment (verl 0.8.0
    installs one), so an ordinary import of a sibling under this directory is a
    collision waiting to happen. A file-path import names exactly the file
    beside this one.
    """

    path = Path(__file__).resolve().parent / "build_slurp_stage3_delta_store.py"
    spec = importlib.util.spec_from_file_location("saea_stage3_delta_store", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the base curator from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = _load_base_curator()
Stage3DeltaStoreError = BASE.Stage3DeltaStoreError


class Stage3GepaCurationError(Stage3DeltaStoreError):
    """A proposal output, a group binding or a curation input is malformed."""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Stage3GepaCurationError(f"{path} is unreadable: {error}") from error


def load_groups(path: Path) -> dict[str, Mapping[str, object]]:
    """``{group_id: group}`` from the prepared GEPA groups artifact."""

    document = _read_json(path)
    if not isinstance(document, Mapping):
        raise Stage3GepaCurationError(f"{path} must be a JSON object")
    groups = document.get("groups")
    if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)) or not groups:
        raise Stage3GepaCurationError(f"{path} carries no non-empty 'groups'")
    out: dict[str, Mapping[str, object]] = {}
    for index, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise Stage3GepaCurationError(f"groups[{index}] must be an object")
        group_id = group.get("group_id")
        if not isinstance(group_id, str) or not group_id:
            raise Stage3GepaCurationError(f"groups[{index}] has no group_id")
        if group.get("node") not in LEGAL_GEPA_NODES:
            raise Stage3GepaCurationError(
                f"groups[{index}] node {group.get('node')!r} is not a legal node"
            )
        out[group_id] = group
    return out


def build_gepa_candidate_rows(
    *,
    proposal_outputs: Sequence[Mapping[str, object]],
    groups_by_id: Mapping[str, Mapping[str, object]],
    run_id: str,
    iteration: int,
    transcript_spans=frozenset(),
    facet_rule: str,
    gold_intents: Mapping[str, str],
    legal_intents: frozenset,
) -> tuple[list[dict], dict]:
    """Parse and join every GEPA output into NODE-TARGETED candidate rows."""

    candidates: list[dict] = []
    counts = {
        "total": 0,
        "legal": 0,
        "illegal": 0,
        "unmatched_group": 0,
        "blocks_total": 0,
        "blocks_legal": 0,
        "blocks_illegal": 0,
        "blocks_wrong_node": 0,
        "blocks_contained": 0,
        "blocks_no_facet": 0,
    }
    per_node = {node: 0 for node in LEGAL_GEPA_NODES}
    per_scenario: Counter = Counter()

    for entry in proposal_outputs:
        counts["total"] += 1
        group_id = entry.get("group_id")
        if not isinstance(group_id, str) or not group_id:
            raise Stage3GepaCurationError("a proposal-outputs row is missing group_id")
        group = groups_by_id.get(group_id)
        if group is None:
            counts["unmatched_group"] += 1
            continue
        node = str(group["node"])
        scenario = str(group["scenario"])
        source_rows = [str(row) for row in (group.get("row_sample_ids") or ())]
        if not source_rows:
            raise Stage3GepaCurationError(f"group {group_id!r} names no source rows")
        try:
            prior = float(group.get("disagreement_mean"))
        except (TypeError, ValueError):
            raise Stage3GepaCurationError(
                f"group {group_id!r} carries no numeric disagreement_mean"
            ) from None

        parsed = parse_gepa_proposal(entry.get("response_text"), node=node)
        counts["blocks_total"] += len(parsed.blocks)
        legal_blocks = parsed.legal_blocks()
        counts["blocks_illegal"] += len(parsed.blocks) - len(legal_blocks)
        counts["blocks_wrong_node"] += sum(
            1
            for block in parsed.blocks
            if any("is not this group's node" in reason for reason in block.illegal_reasons)
        )
        if not legal_blocks:
            counts["illegal"] += 1
            continue
        kept = 0
        for block in legal_blocks:
            if BASE.contains_transcript_span(block.statement, transcript_spans):
                counts["blocks_contained"] += 1
                continue
            facet_ids = BASE.facet_ids_for_statement(
                sample_ids=tuple(source_rows),
                target=block.target,
                facet_rule=facet_rule,
                gold_intents=gold_intents,
                legal_intents=legal_intents,
            )
            if not facet_ids:
                counts["blocks_no_facet"] += 1
                continue
            counts["blocks_legal"] += 1
            per_node[block.node] += 1
            per_scenario[scenario] += 1
            kept += 1
            candidates.append(
                {
                    "value_id": f"delta:{iteration}:{block.statement_sha256()[:12]}",
                    "content": block.statement,
                    "associated_facet_ids": facet_ids,
                    "node_target": block.node,
                    "source_sample_ids": list(source_rows),
                    "provenance_refs": [
                        f"gepa:{run_id}:{scenario}:{node}:{block.block_index}"
                    ],
                    "task_target": block.task_target(),
                    "prior_score": prior,
                }
            )
        if kept:
            counts["legal"] += 1
        else:
            counts["illegal"] += 1

    counts.update({f"blocks_node_{node}": per_node[node] for node in LEGAL_GEPA_NODES})
    counts["blocks_per_scenario"] = dict(sorted(per_scenario.items()))
    return candidates, counts


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal-outputs", required=True, type=Path)
    parser.add_argument("--groups", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--predecessor", default="none")
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-authored", required=True, type=Path)
    parser.add_argument("--out-source", default=None, type=Path)
    parser.add_argument("--source-split-identity-hash", default=None)
    parser.add_argument("--source-receipt", default=None, type=Path)
    parser.add_argument("--release", default=None, type=Path)
    parser.add_argument("--data-root", default=None, type=Path)
    parser.add_argument("--release-pins", default=None, type=Path)
    parser.add_argument("--jaccard-threshold", default=0.8, type=float)
    parser.add_argument(
        "--facet-rule", default=BASE.FACET_RULE_SOURCE_INTENT, choices=BASE.FACET_RULES
    )
    parser.add_argument("--gold-intents", default=None, type=Path)
    parser.add_argument("--intent-vocabulary", default=None, type=Path)
    parser.add_argument("--retire-value-ids", default=None, type=Path)
    parser.add_argument("--construction-transcripts", default=None, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.iteration < 1:
        raise Stage3GepaCurationError("--iteration must be >= 1")

    gold_intents: dict[str, str] = {}
    legal_intents: frozenset = frozenset()
    if args.facet_rule == BASE.FACET_RULE_SOURCE_INTENT:
        if args.gold_intents is None:
            raise Stage3GepaCurationError(
                "--facet-rule source-intent requires --gold-intents"
            )
        gold_intents = BASE.load_gold_intents(args.gold_intents)
        legal_intents = BASE.load_intent_vocabulary(
            args.intent_vocabulary, gold_intents=gold_intents
        )
    elif args.gold_intents is not None or args.intent_vocabulary is not None:
        raise Stage3GepaCurationError(
            "--gold-intents and --intent-vocabulary are only meaningful with "
            "--facet-rule source-intent"
        )

    spans, span_counts = BASE.load_construction_spans(args.construction_transcripts)
    containment = {"enabled": bool(spans), **span_counts}

    groups_by_id = load_groups(args.groups)
    proposal_outputs = BASE._read_jsonl(args.proposal_outputs)
    candidates, parse_counts = build_gepa_candidate_rows(
        proposal_outputs=proposal_outputs,
        groups_by_id=groups_by_id,
        run_id=args.run_id,
        iteration=args.iteration,
        transcript_spans=spans,
        facet_rule=args.facet_rule,
        gold_intents=gold_intents,
        legal_intents=legal_intents,
    )

    predecessor_rows = BASE.load_predecessor_rows(args.predecessor, schema_version=2)
    retirement = None
    retired_rows: list[dict] = []
    if args.retire_value_ids is not None:
        if not predecessor_rows:
            raise Stage3GepaCurationError(
                "--retire-value-ids requires a --predecessor to retire rows from"
            )
        retired_value_ids = BASE.load_retired_value_ids(args.retire_value_ids)
        predecessor_rows, retired_rows, retirement = BASE.partition_retired(
            predecessor_rows, retired_value_ids
        )
        retirement["source"] = str(args.retire_value_ids)

    survivors, curation_counts = BASE.curate(
        predecessor_rows=predecessor_rows,
        candidate_rows=candidates,
        jaccard_threshold=args.jaccard_threshold,
        merge_facets=args.facet_rule == BASE.FACET_RULE_SOURCE_INTENT,
        retired_rows=retired_rows,
    )
    out_sha256 = BASE.write_authored_document(
        args.out_authored,
        iteration=args.iteration,
        rows=survivors,
        schema=BASE.AUTHORED_SCHEMA_V2,
        facet_rule=args.facet_rule,
    )

    source_report = None
    if args.out_source is not None:
        if not args.source_split_identity_hash:
            raise Stage3GepaCurationError(
                "--out-source requires --source-split-identity-hash"
            )
        source_report = BASE.write_authored_source(
            args.out_authored,
            out_path=args.out_source,
            source_split_identity_hash=args.source_split_identity_hash,
            receipt_path=args.source_receipt,
        )
    elif args.source_split_identity_hash:
        raise Stage3GepaCurationError(
            "--source-split-identity-hash is only meaningful with --out-source"
        )

    # The read the design note's decision rule calls REVISION SHARE: how many
    # accepted proposals the curator absorbed into an existing row (a revision
    # of the text the contact was shown) against how many entered as new rows.
    absorbed = curation_counts["exact_duplicate"] + curation_counts["near_duplicate"]
    proposed = absorbed + curation_counts["new_accepted"]
    report = {
        "schema": "saea-stage3-gepa-curation-report-v1",
        "iteration": args.iteration,
        "authored_schema": BASE.AUTHORED_SCHEMA_V2,
        "facet_rule": args.facet_rule,
        "groups": {"relpath": str(args.groups), "count": len(groups_by_id)},
        "containment": containment,
        "parse": parse_counts,
        "curation": curation_counts,
        "revision_share": {
            "proposals_reaching_curation": proposed,
            "absorbed_into_an_existing_row": absorbed,
            "entered_as_new_rows": curation_counts["new_accepted"],
            "absorbed_fraction": (round(absorbed / proposed, 6) if proposed else None),
        },
        "survivor_count": len(survivors),
        "survivors_by_node": {
            node: sum(1 for row in survivors if row.get("node_target") == node)
            for node in LEGAL_GEPA_NODES
        },
        "facets": {
            "distinct": len(
                {facet for row in survivors for facet in row["associated_facet_ids"]}
            ),
            "gold_intent_rows": len(gold_intents),
            "legal_intent_vocabulary": len(legal_intents),
        },
        "out_authored": {"relpath": str(args.out_authored), "sha256": out_sha256},
    }
    if retirement is not None:
        report["retirement"] = retirement
    if source_report is not None:
        report["authored_source"] = source_report
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts only

    if args.release is not None:
        if args.data_root is None:
            raise Stage3GepaCurationError("--release requires --data-root")
        from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
            prepare_semantic_knowledge_store,
        )

        result = prepare_semantic_knowledge_store(
            args.release, repo_root=args.repo_root, data_root=args.data_root
        )
        if args.release_pins is not None:
            pins_document = {
                "schema": BASE.RELEASE_PINS_SCHEMA,
                "status": "RELEASED_PENDING_RUNTIME_CONSUMPTION",
                "store": result,
            }
            args.release_pins.write_bytes(canonical_json_bytes(pins_document))
        print(json.dumps({"released": True}, indent=2))  # noqa: T201

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stage3DeltaStoreError as error:  # pragma: no cover - CLI surface
        print(f"build_slurp_stage3_gepa_delta_rows: FAIL: {error}", file=sys.stderr)
        raise SystemExit(2) from None
