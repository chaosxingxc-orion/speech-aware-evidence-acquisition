#!/usr/bin/env python3
"""Pre-compute the EXEMPLAR-INTENT AGREEMENT table the intent-boundary channel
ranks with, on the boundary channel's own pre-flight bootstrap pattern.

WHY THIS EXISTS. The flown Perception boundary retrieval ranks 60 written
boundary descriptions against one speech vector at pure cosine, and on
intent-wrong rows the gold intent's median rank is 10-14 against 1 on correct
rows, spread down the whole tail
(``docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md`` section
2). The same row's EXEMPLAR channel scores the same speech vector against
thousands of other utterances and puts the gold intent at rank 1 on 76.1 % of
rows against 65.6 % for the boundary cosine (section 3), so the boundary
channel's weakness is its key space, not its budget. The agreement term lets
the boundary ranker borrow the stronger signal the system already computes.

WHY IT IS PRE-COMPUTED RATHER THAN A WEIGHT FLIP. The flown program runs
Perception BEFORE the Solver's exemplar recall, so at the moment the boundary
channel ranks, the exemplar recall has not happened yet. This script performs
that recall offline, exactly as the boundary channel's own key vectors were
encoded offline and pinned by ``facet_source``; the output is pinned the same
way by ``agreement_source`` and hash-verified by
``rails.phase_supply.load_sealed_agreement``.

WHAT IT IS ARITHMETIC OVER. Two receipt-pinned vector files and one frozen
snapshot, each verified against its configured sha256 by this repository's own
loaders before a number is taken from it, through this repository's own
``rails.phase_supply.build_bootstrap_selection`` -- the same recall, the same
registered ranker and the same registered fuser the flight runs at the Solver.
ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API
contacts: no server is started, stopped or probed, no waveform is decoded and
no embedding is computed.

WHAT NEVER ENTERS IT. No gold label, no reference transcript, no future turn
and no evaluation-row annotation. The vote key is each pool value's own frozen
build-time ``task_target``, a property of the released store; the query is the
row's own sealed speech vector. The vote is SELF-EXCLUDED: any pool value that
covers the evaluated row's own utterance is dropped before the shares are
formed, so a roster drawn from the same split the pool is built from cannot
vote for itself.

WHAT IT PRINTS. Ids, counts, rates and hashes. No utterance text, transcript,
intent name, knowledge body or delivered answer is printed or persisted as
content: the artifact's keys are sample ids and facet ids, and its values are
shares.

Usage (model-free; run it against the COMPARATOR cell, whose committed config
declares no ``agreement_source``, so there is no chicken-and-egg with the pin
this artifact is about to receive):

    python scripts/build_slurp_intent_exemplar_agreement.py \
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \
        --runtime-root /home/chao --lock-path ../../docs/datasets.lock.json \
        --experiment slurp-native-default-plan-lock-v1 \
        --cell slurp-native-default-plan-lock-v1 \
        --vote-store train-exemplars --vote-phase solver \
        --target-store intent-boundaries \
        --target-facet-template "intent-boundary:{key}" \
        --output prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1 \
        --artifact-id SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1 --workers 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.flight.factory import (  # noqa: E402
    build_flight_runtime,
)
from speech_aware_evidence_acquisition.core.flight.campaign import (  # noqa: E402
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.rails.controllers import (  # noqa: E402
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    SEALED_AGREEMENT_SCHEMA,
    build_bootstrap_selection,
    build_supply_for_phase,
    load_phase_supply_specs,
)

BUILDER_ID = "saea-slurp-intent-exemplar-agreement-builder-v1"


class BuildError(RuntimeError):
    """Refuse an incomplete, unmappable or self-referential vote."""


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def utterance_identity(sample_id: str) -> str:
    """The recording-independent identity of one utterance: the first three
    colon-separated fields of a sample id (``slurp:train:000007``).

    This is the key the SELF-EXCLUSION compares. It is deliberately coarser
    than the sample id, because one utterance has several recordings
    (headset/far-field) and a pool value that covers ANY recording of the
    evaluated row's utterance would make the vote circular. Refuses a sample
    id too short to carry an utterance identity rather than guessing one.
    """

    parts = sample_id.split(":")
    if len(parts) < 3 or not all(parts[:3]):
        raise BuildError(
            "a sample id carries no three-field utterance identity, so the vote's "
            "self-exclusion cannot be evaluated for it"
        )
    return ":".join(parts[:3])


def form_vote(
    selected_value_ids,
    *,
    own_utterance: str,
    target_of_value: dict,
    utterances_of_value: dict,
    target_facet_template: str,
    target_facets: set,
) -> tuple[dict, int, int, int]:
    """``(shares, vote_total, self_excluded, untargeted)`` for ONE row.

    A pure function of its arguments, so it is deterministic, order-independent
    and worker-count independent by construction: the selection is walked in
    sorted order, the counts are integers, and the shares are those counts over
    their own total.

    SELF-EXCLUSION, which is the property that keeps the vote non-circular. Two
    of the three rosters the 2026-09-26 read measured are drawn from the same
    TRAIN split the exemplar pool is built from, so a pool value covering the
    evaluated row's own utterance is dropped BEFORE the shares are formed. The
    comparison is on the utterance identity, not the sample id, so another
    recording of the same utterance is dropped too
    (:func:`utterance_identity`).

    REFUSALS, never silent skips: a selected value the vote snapshot does not
    declare, and a build-time target that does not map to a facet of the target
    snapshot, both raise. A value with NO build-time target is counted as
    ``untargeted`` and reported, not silently dropped.
    """

    votes: Counter[str] = Counter()
    dropped = 0
    untargeted = 0
    for value_id in sorted(selected_value_ids):
        if value_id not in target_of_value:
            raise BuildError(
                "the vote channel selected a value id the vote snapshot does not declare"
            )
        if own_utterance in utterances_of_value[value_id]:
            dropped += 1
            continue
        key = target_of_value[value_id]
        if key is None:
            untargeted += 1
            continue
        facet_id = target_facet_template.format(key=key)
        if facet_id not in target_facets:
            raise BuildError(
                "a pool value's build-time target does not map to any facet of the "
                "target snapshot under the configured template; refusing rather than "
                "dropping the vote"
            )
        votes[facet_id] += 1
    total = sum(votes.values())
    shares = (
        {facet_id: votes[facet_id] / total for facet_id in sorted(votes)} if total else {}
    )
    return shares, total, dropped, untargeted


def load_snapshot(data_root: Path, pin: dict) -> tuple[KnowledgeSnapshot, str]:
    path = data_root / str(pin["relpath"])
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != str(pin["sha256"]):
        raise BuildError("a knowledge snapshot does not hash to its configured pin")
    return snapshot, snapshot.content_hash()


def build(args: argparse.Namespace) -> dict:
    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    cells = [
        cell
        for cell in load_campaign_cells(repo, args.experiment)
        if cell.document["cell_id"] == args.cell
    ]
    if len(cells) != 1:
        raise BuildError("the experiment does not declare exactly one such cell")
    cell = cells[0]
    runtime = build_flight_runtime(
        repo,
        data_root,
        model=cell.document["model_fragment"],
        dataset=cell.document["dataset_fragment"],
        baseline=cell.document["baseline_fragment"],
        experiment=args.experiment,
        run_id=cell.run_id,
        attempt_id=cell.attempt_id,
        runtime_root=Path(args.runtime_root),
        lock_path=Path(args.lock_path),
    )
    # The roster, the packet bindings and the split identity come from the
    # runtime's OWN identity computation (item E16), so the vote is formed over
    # exactly the rows the cell flies, under exactly the split identity its
    # prepared artifacts bind.
    program, binding, _specs, _first, split_identity, _inputs = (
        runtime.phase_supply_artifact_identity()
    )
    values = runtime._composed.values  # noqa: SLF001 -- the composed config, read-only
    stores = values.get("knowledge_stores") or {}
    if args.vote_store not in stores:
        raise BuildError("the cell declares no such vote store")
    if args.target_store not in stores:
        raise BuildError("the cell declares no such target store")

    vote_store = stores[args.vote_store]
    vote_program = default_phase_program(str(values["policy"]))
    vote_specs = load_phase_supply_specs(
        {"phase_supply": vote_store.get("phase_supply") or {}}, vote_program
    )
    vote_spec = vote_specs.get(args.vote_phase)
    if vote_spec is None:
        raise BuildError("the vote store declares no phase_supply for that phase")
    if vote_spec.agreement_source is not None:
        raise BuildError(
            "the vote channel itself declares an agreement_source; this builder "
            "refuses to form a vote out of a vote"
        )
    vote_snapshot, vote_sha = load_snapshot(data_root, vote_store["snapshot"])
    target_snapshot, target_sha = load_snapshot(data_root, stores[args.target_store]["snapshot"])
    target_facets = {facet.facet_id for facet in target_snapshot.facets}

    # ONE construction of the vote channel, through the same seam the flight
    # uses: build_supply_for_phase loads the pinned vectors and hands back the
    # registered provider factory and the query table for that phase.
    callback = build_supply_for_phase(
        {args.vote_phase: vote_spec},
        snapshot=vote_snapshot,
        snapshot_sha256=vote_sha,
        data_root=data_root,
        seed_phases=(args.vote_phase,),
    )
    if callback is None:
        raise BuildError("the vote channel built no supply callable")
    provider = callback.provider_factories[args.vote_phase]()
    query_table = callback.query_tables.get(args.vote_phase) or {}
    packets = dict(binding["speech_packet_bindings"])
    missing = sorted(set(packets) - set(query_table))
    if missing:
        # THE REFUSAL THE 2026-09-26 READ ASKED FOR. A row whose exemplar query
        # vector is absent would silently receive an empty vote and fly the
        # comparator's ranking under the treatment's identity. It is named and
        # refused, never skipped.
        raise BuildError(
            f"{len(missing)} of {len(packets)} roster rows have no exemplar query "
            "vector in the pinned file; a missing vector is refused rather than "
            "scored 0.0"
        )

    _facets, selections = build_bootstrap_selection(
        vote_spec,
        provider=provider,
        query_vectors_by_sample=query_table,
        speech_packet_bindings=packets,
        split_identity_hash=split_identity,
        source_audio_bindings=getattr(callback, "source_audio_bindings", None),
        workers=args.workers,
    )

    # The vote key is each pool value's own frozen build-time task_target.
    target_of_value = {
        value.value_id: value.task_target for value in vote_snapshot.values
    }
    utterances_of_value = {
        value.value_id: {
            utterance_identity(sample_id) for sample_id in value.source_sample_ids
        }
        for value in vote_snapshot.values
    }

    rows: list[dict] = []
    vote_totals: Counter[int] = Counter()
    self_excluded_rows = 0
    self_excluded_total = 0
    untargeted = 0
    zero_vote_rows = 0
    for sample_id in sorted(packets):
        shares, total, dropped, row_untargeted = form_vote(
            selections.get(sample_id, ()),
            own_utterance=utterance_identity(sample_id),
            target_of_value=target_of_value,
            utterances_of_value=utterances_of_value,
            target_facet_template=args.target_facet_template,
            target_facets=target_facets,
        )
        untargeted += row_untargeted
        vote_totals[total] += 1
        self_excluded_total += dropped
        self_excluded_rows += int(dropped > 0)
        zero_vote_rows += int(total == 0)
        rows.append(
            {
                "schema": SEALED_AGREEMENT_SCHEMA,
                "id": sample_id,
                "dimension": EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
                "scores": shares,
                "vote_total": total,
                "self_excluded": dropped,
            }
        )

    out_dir = data_root / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    artifact = out_dir / "agreement.jsonl"
    artifact.write_bytes(payload)

    receipt = {
        "schema": "saea-phase-agreement-receipt-v1",
        "artifact_id": args.artifact_id,
        "builder_id": BUILDER_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contact_class": "model-free",
        "contacts": {
            "model": 0,
            "server": 0,
            "encoder": 0,
            "embedder": 0,
            "scorer": 0,
            "network": 0,
            "gpu": 0,
            "paid_api": 0,
        },
        "artifact": {
            "relpath": str(Path(args.output) / "agreement.jsonl"),
            "sha256": digest_bytes(payload),
            "rows": len(rows),
            "dimension": EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
            "line_schema": SEALED_AGREEMENT_SCHEMA,
        },
        "derived_from": {
            "experiment": args.experiment,
            "cell": args.cell,
            "run_id": cell.run_id,
            "split_identity_hash": split_identity,
            "program_id": program.program_id,
            "vote_store": args.vote_store,
            "vote_phase": args.vote_phase,
            "vote_spec": vote_spec.as_json(),
            "vote_snapshot_sha256": vote_sha,
            "target_store": args.target_store,
            "target_snapshot_sha256": target_sha,
            "target_facets": len(target_facets),
            "target_facet_template": args.target_facet_template,
            "vote_key": "task_target",
            "self_exclusion": "sample-id utterance identity (first three fields)",
        },
        "implementation": {
            module: digest_file(Path(path))
            for module, path in sorted(
                (
                    name,
                    sys.modules[name].__file__,
                )
                for name in (
                    "speech_aware_evidence_acquisition.rails.kb_policy",
                    "speech_aware_evidence_acquisition.rails.knowledge_provider",
                    "speech_aware_evidence_acquisition.rails.phase_supply",
                )
            )
        },
        "builder_sha256": digest_file(Path(__file__)),
        "measured": {
            "roster_rows": len(packets),
            "vote_total_histogram": {
                str(total): count for total, count in sorted(vote_totals.items())
            },
            "rows_with_a_self_excluded_exemplar": self_excluded_rows,
            "self_excluded_exemplars": self_excluded_total,
            "rows_with_no_vote": zero_vote_rows,
            "pool_values_without_a_build_time_target": untargeted,
            "distinct_facets_ever_voted_for": len(
                {facet for row in rows for facet in row["scores"]}
            ),
        },
        "boundary": (
            "A pre-computed model-free input, never an authorization: it opens no "
            "attempt, reserves no contact, admits no mechanism and states no "
            "effectiveness claim. No gold label, reference transcript or future turn "
            "enters it; the vote key is each pool value's frozen build-time "
            "task_target and the query is the row's own sealed speech vector."
        ),
    }
    receipt_bytes = (
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    (out_dir / "receipt.json").write_bytes(receipt_bytes)
    return receipt


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "data-root", "runtime-root", "lock-path"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--vote-store", required=True)
    parser.add_argument("--vote-phase", required=True)
    parser.add_argument("--target-store", required=True)
    parser.add_argument("--target-facet-template", default="intent-boundary:{key}")
    parser.add_argument("--output", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--workers", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(
            json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}),
            file=sys.stderr,
        )
        return 1
    try:
        receipt = build(args)
    except (BuildError, OSError, ValueError) as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}), file=sys.stderr)
        return 1
    print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
