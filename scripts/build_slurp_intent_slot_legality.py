#!/usr/bin/env python3
"""Build the intent -> slot-type LEGALITY table cell W1 narrows its slot cards with.

W1, owner decision 164 (2026-09-27): the Solver receives ONLY the slot-contract cards
for slot types legal under the row's candidate intents. The flown route already selects
cards through the authored ``intent_bindings`` of ``slot-contracts-v2``; measured here,
those 402 bindings are exactly the (intent, slot type) pairs the released 9,354-utterance
exemplar store carries at least once. The cards the audit calls unused are therefore not
illegal bindings but ANECDOTAL ones: a binding witnessed by a single pool utterance.

THE RULE (``pool-utterance-support-at-least-2-v1``): a slot type is legal under an intent
when at least ``--min-support`` (2) distinct utterances of that intent in the released
exemplar store carry an entity of that type. A binding witnessed once is not a convention
of the intent. The table can only NARROW the authored bindings; the runtime refuses a
table that adds one (``rails.candidate_semantic_supply.narrow_candidate_index``).

WHAT IT READS. The released exemplar store the flown Solver already consumes
(``train-exemplars``: ``size-pool-annotated-exemplars``, content hash verified), whose
values carry the utterance's own annotation as knowledge text -- its intent
(``task_target``) and its ``type=filler`` pairs; only the TYPE names are used. The
authored slot-contract source, to prove the narrowing property. The Fold A roster's
sample ids (from the cell's experiment fragment), only to prove the store holds no Fold A
utterance. It never opens a governed label file, a transcript, a devel or test file, or
any evaluation row's annotation.

ZERO model, server, tokenizer, encoder, embedder, scorer, network, GPU and paid-API
contacts. Prints ids, counts and hashes only.

    python scripts/build_slurp_intent_slot_legality.py --data-root "$SPEECHRL_DATA_DIR" \\
        --roster-experiment slurp-native-stage3-agree-w1-fold-a-v1 \\
        --output prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (  # noqa: E402
    SLOT_LEGALITY_SCHEMA,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402

ARTIFACT_ID = "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1"
RULE_ID = "pool-utterance-support-at-least-2-v1"
POOL_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
POOL_CONTENT_HASH = "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"
AUTHORED_RELPATH = "prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json"
AUTHORED_SHA256 = "34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5"
SLOT_SNAPSHOT_RELPATH = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
SLOT_CONTENT_HASH = "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"


class LegalityBuildError(RuntimeError):
    pass


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def annotation_types(content: str) -> list[str]:
    """The TYPE names of a released exemplar's ``text | intent | type=filler; ...`` body."""

    parts = [part.strip() for part in content.split(" | ")]
    if len(parts) < 2:
        raise LegalityBuildError("an exemplar body is not 'text | intent | annotation'")
    if len(parts) != 3:
        raise LegalityBuildError("an exemplar body is not 'text | intent | annotation'")
    if parts[-1] == "none":  # the store's rendering of an utterance with no entity
        return []
    types = []
    for chunk in parts[-1].split("; "):
        name, sep, _filler = chunk.partition("=")
        if not sep or not name.strip():
            raise LegalityBuildError("an exemplar annotation chunk is not 'type=filler'")
        types.append(name.strip())
    return types


def utterance_of(sample_id: str) -> str:
    # slurp:train:<slurp id>:<recording>
    return sample_id.split(":")[2]


def build(data_root: Path, roster_ids: list[str], min_support: int) -> tuple[dict, dict]:
    pool_path = data_root / POOL_RELPATH
    pool_raw = pool_path.read_bytes()
    snapshot = KnowledgeSnapshot.from_frozen_json(json.loads(pool_raw))
    if snapshot.content_hash() != POOL_CONTENT_HASH:
        raise LegalityBuildError("the exemplar store is not the flown pin")
    authored_raw = (data_root / AUTHORED_RELPATH).read_bytes()
    if sha_bytes(authored_raw) != AUTHORED_SHA256:
        raise LegalityBuildError("the authored slot-contract source is not the pinned file")
    authored = json.loads(authored_raw)
    slot_raw = (data_root / SLOT_SNAPSHOT_RELPATH).read_bytes()
    slot_snapshot = KnowledgeSnapshot.from_frozen_json(json.loads(slot_raw))
    if slot_snapshot.content_hash() != SLOT_CONTENT_HASH:
        raise LegalityBuildError("the slot-contract store is not the flown pin")
    card_types = {value.value_id.split("slot-contract:", 1)[-1] for value in slot_snapshot.values}
    bindings = {(b["intent_id"], row["slot_id"]) for row in authored["rows"] for b in row["intent_bindings"]}

    roster_utts = {utterance_of(sample_id) for sample_id in roster_ids}
    pool_utts: set[str] = set()
    support: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    utterances_per_intent: dict[str, set[str]] = defaultdict(set)
    for value in snapshot.values:
        intent = value.task_target
        if not isinstance(intent, str) or not intent:
            raise LegalityBuildError("an exemplar value carries no task_target")
        utts = {utterance_of(sample_id) for sample_id in value.source_sample_ids}
        if len(utts) != 1:
            raise LegalityBuildError("an exemplar value spans more than one utterance")
        utt = next(iter(utts))
        pool_utts.add(utt)
        utterances_per_intent[intent].add(utt)
        for slot_type in set(annotation_types(value.content)):
            support[intent][slot_type].add(utt)
    overlap = pool_utts & roster_utts
    if overlap:
        raise LegalityBuildError(f"{len(overlap)} roster utterances are in the exemplar store")

    observed = {(intent, t) for intent, types in support.items() for t in types}
    carded = {pair for pair in observed if pair[1] in card_types}
    if carded != bindings:
        raise LegalityBuildError(
            "the store's observed carded pairs are not the authored bindings: "
            f"{len(carded - bindings)} extra, {len(bindings - carded)} missing"
        )
    legal: dict[str, list[str]] = {}
    counts: dict[str, dict[str, int]] = {}
    removed = []
    for intent in sorted(support):
        counts[intent] = {t: len(u) for t, u in sorted(support[intent].items())}
        kept = sorted(t for t, u in support[intent].items() if len(u) >= min_support and t in card_types)
        if kept:
            legal[intent] = kept
        removed.extend(
            {"intent_id": intent, "slot_type": t, "support_utterances": len(u)}
            for t, u in sorted(support[intent].items())
            if len(u) < min_support and t in card_types
        )
    kept_pairs = sum(len(v) for v in legal.values())
    table = {
        "schema": SLOT_LEGALITY_SCHEMA,
        "artifact_id": ARTIFACT_ID,
        "rule": {
            "id": RULE_ID,
            "min_support_utterances": min_support,
            "statement": (
                "a slot type is legal under an intent when at least min_support_utterances distinct "
                "utterances of that intent in the released exemplar store carry an entity of that type"
            ),
        },
        "source_store": {
            "relpath": POOL_RELPATH, "content_hash": POOL_CONTENT_HASH, "file_sha256": sha_bytes(pool_raw),
            "values": len(snapshot.values), "utterances": len(pool_utts), "recordings": len(snapshot.source_sample_ids),
        },
        "legal_slot_types": legal,
        "support_utterances": counts,
    }
    receipt = {
        "schema": "saea-slurp-intent-slot-legality-receipt-v1",
        "artifact_id": ARTIFACT_ID,
        "rule": table["rule"],
        "inputs": {
            "exemplar_store": table["source_store"],
            "authored_slot_contracts": {"relpath": AUTHORED_RELPATH, "sha256": AUTHORED_SHA256},
            "slot_contract_store": {"relpath": SLOT_SNAPSHOT_RELPATH, "content_hash": SLOT_CONTENT_HASH, "file_sha256": sha_bytes(slot_raw)},
            "roster": {"sample_ids": len(roster_ids), "utterances": len(roster_utts), "sha256_of_sorted_ids": sha_bytes("\n".join(sorted(roster_ids)).encode())},
        },
        "proofs": {
            "roster_utterances_in_store": 0,
            "observed_carded_pairs_equal_authored_bindings": True,
            "authored_bindings": len(bindings),
            "pairs_kept": kept_pairs,
            "pairs_removed": len(removed),
            "intents_with_a_legal_type": len(legal),
            "intents_in_store": len(support),
        },
        "removed_pairs": removed,
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "never_read": "governed label files, transcripts, devel and test files, any evaluation row's annotation",
    }
    return table, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--roster-experiment", required=True)
    parser.add_argument("--output", default=f"prepared/{ARTIFACT_ID}")
    parser.add_argument("--min-support", type=int, default=2)
    parser.add_argument("--force", action="store_true", help="overwrite an existing artifact")
    args = parser.parse_args(argv)
    fragment = json.loads((REPO_ROOT / "configs/experiment" / f"{args.roster_experiment}.json").read_text(encoding="utf-8"))
    roster_ids = [sample_id for block in fragment["populations"] for sample_id in block["ids"]]
    if len(roster_ids) != fragment["population"]["count"]:
        raise SystemExit("the fragment's populations do not carry its population count")
    table, receipt = build(args.data_root, roster_ids, args.min_support)
    out = args.data_root / args.output
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / "legality.json"
    payload = (json.dumps(table, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if artifact.exists() and artifact.read_bytes() != payload and not args.force:
        raise SystemExit(f"refusing to overwrite a different {artifact}")
    artifact.write_bytes(payload)
    receipt["artifact"] = {"relpath": f"{args.output}/legality.json", "sha256": sha_bytes(payload)}
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / "receipt.json").write_bytes(receipt_bytes)
    print(json.dumps({
        "artifact": receipt["artifact"],
        "receipt": {"relpath": f"{args.output}/receipt.json", "sha256": sha_bytes(receipt_bytes)},
        "proofs": receipt["proofs"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
