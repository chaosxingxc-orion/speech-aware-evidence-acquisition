#!/usr/bin/env python3
"""Freeze the FILLER roster (owner decision 162) and its chunk rosters. MODEL-FREE.

WHAT IT PROVES BEFORE IT WRITES ANYTHING.

1. The ADMISSIBLE UNIVERSE is exactly TRAIN Fold B. The current best system retrieves TRAIN exemplars
   from ``size-pool-annotated-exemplars`` and the runner refuses a query row that is a source of any
   composed knowledge store (``rails.runner`` BUILD/USE guard). The composite source set is computed the
   way the flight computes it (``core.config.compose`` of cell ROLL-2's fragments over the Fold B view,
   then ``rails.knowledge_stores.load_knowledge_store_binding``), and the proof is id arithmetic: the pool
   utterances, the TRAIN Fold A utterances and the TRAIN Fold B utterances are pairwise disjoint and their
   union is 11,514 utterances -- every SLURP TRAIN utterance -- so a TRAIN utterance outside the composite
   source set and outside Fold A is a Fold B utterance, and every Fold B recording is outside the composite.
2. DISJOINTNESS, id by id and utterance by utterance, from every SLURP roster receipt under
   ``docs/receipts/rosters/`` and every SLURP probe-sample receipt under ``docs/receipts/probe-samples/``
   (DEV-2000-ADDED, DEV-2000, DEV-1000, the devel remainder with its FINAL60 / probe-60 carve-outs, the
   test sample / closure / full, R01 / R01C, Fold A and every Stage-3 subset), and from the governed devel
   and test id enumerations of ``docs/receipts/knowledge/slurp-split-identity.json``.

THE DRAW. Seed 20260927, one ``random.Random`` advanced across the 18 scenarios in ascending name order;
each scenario's 60 Fold B recordings (id-sorted) are shuffled and dealt ten to each of six chunks, so
every chunk is 180 rows, ten per scenario -- stratified exactly like the parent, never a prefix. Items are
the parent's items verbatim (plus a ``chunk`` field on the family receipt); a chunk receipt lists its items
in the parent's order. The chunk-1 four-row smoke roster is the first four rows of chunk 1 by that order.

No sentence, transcript, label, gold or score is read anywhere in this file; only ids, strata, counts,
durations and hashes that the committed receipts already carry. Zero model, server, encoder, embedder,
tokenizer, scorer and network contacts (an offline socket guard is armed before the first input opens).

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src SPEECHRL_DATA_DIR=<data> \\
      python scripts/flights/filler/build_filler_roster.py [--write | --check]
"""

from __future__ import annotations
import os

import argparse
import glob
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import filler_family as ff  # noqa: E402

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import arm_offline_guard  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.roster import verify_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding  # noqa: E402

GENERATOR = "scripts/flights/filler/build_filler_roster.py"
SLURP_TRAIN_UTTERANCES = 11514
AUTHORITY = (
    f"owner decision {ff.OWNER_DECISION} ({ff.OWNER_DECISIONS}): a standing, pre-approved rollout FILLER family "
    "-- sealed five-sample pools of the current best SLURP system on TRAIN rows outside Fold A and outside every "
    "evaluation roster, in chunks of about 200 rows, each chunk its own run id, exposure rows and receipt."
)
ROLE_NOTE = (
    "construction: TRAIN rows whose five-sample pools are the rollout substrate of the training-free RL inner "
    "loop. No filler flight reads gold at runtime or produces an admission verdict; the offline pool read scores "
    "the sealed samples against TRAIN gold (development numbers only, owner decisions 28 and 86)."
)
EXCLUDED_FROM_PROOF = {
    ff.PARENT_ROSTER,
    "docs/receipts/probe-samples/SLURP-EVO-FOLD-B-V2.json",
}


def _item_ids(document) -> list[str]:
    items = document.get("items") if isinstance(document, dict) else None
    ids: list[str] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                value = item.get("sample_id") or item.get("id")
                if isinstance(value, str) and value.startswith("slurp:"):
                    ids.append(value)
            elif isinstance(item, str) and item.startswith("slurp:"):
                ids.append(item)
    return ids


def disjointness(filler_ids: list[str], superseded: set[str]) -> dict:
    """``superseded`` are the parent's own superseded V1 draws (its ``supersedes.rosters``): identity
    statements that were never contacted and that the V2 re-draw re-used no identity of on purpose, so an
    overlap with them is reported, never refused -- they are neither evaluation rosters nor exposure."""

    mine = set(filler_ids)
    mine_utt = {ff.utterance_of(s) for s in mine}
    checked, skipped, superseded_overlap = {}, {}, {}
    paths = sorted(glob.glob(str(REPO_ROOT / "docs/receipts/rosters/*.json"))) + sorted(
        glob.glob(str(REPO_ROOT / "docs/receipts/probe-samples/*.json"))
    )
    for path in paths:
        rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
        if rel in EXCLUDED_FROM_PROOF or "filler" in rel:
            continue
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        ids = _item_ids(document)
        if not ids:
            carrier = document.get("carrier_lock_key") or document.get("carrier") if isinstance(document, dict) else None
            skipped[rel] = f"no slurp item ids (carrier {carrier!r})"
            continue
        shared = mine & set(ids)
        shared_utt = mine_utt & {ff.utterance_of(s) for s in ids}
        entry = {"items": len(ids), "shared_recordings": len(shared), "shared_utterances": len(shared_utt)}
        if rel in superseded:
            superseded_overlap[rel] = {**entry, "status": "superseded by the parent's V2 re-draw, never contacted"}
            continue
        checked[rel] = entry
        if shared or shared_utt:
            raise SystemExit(f"the filler roster shares {len(shared)} recordings / {len(shared_utt)} utterances with {rel}")
    identity = json.loads((REPO_ROOT / "docs/receipts/knowledge/slurp-split-identity.json").read_text(encoding="utf-8"))
    governed = {}
    for split in ("devel", "test"):
        ids = identity["splits"][split]["ids"]
        shared = mine & set(ids)
        shared_utt = mine_utt & {ff.utterance_of(s) for s in ids}
        governed[split] = {"ids": len(ids), "shared_recordings": len(shared), "shared_utterances": len(shared_utt)}
        if shared or shared_utt:
            raise SystemExit(f"the filler roster shares ids with the governed {split} split")
    non_train = sorted(s for s in mine if not s.startswith("slurp:train:"))
    if non_train:
        raise SystemExit(f"non-TRAIN ids in the filler roster: {non_train[:3]}")
    return {
        "method": (
            "set intersection by sample id AND by utterance identity (the first three colon fields, so a "
            "-headset sibling counts) against every SLURP receipt under docs/receipts/rosters/ and "
            "docs/receipts/probe-samples/ that carries item ids, except the parent TRAIN Fold B receipt and its "
            "own probe-sample view; plus the governed devel and test id enumerations"
        ),
        "non_train_ids": 0,
        "receipts_checked": checked,
        "receipts_without_item_ids": skipped,
        "superseded_never_contacted_reported_not_refused": superseded_overlap,
        "governed_splits": governed,
        "total_shared_recordings": 0,
        "total_shared_utterances": 0,
    }


def knowledge_guard(data_root: Path, fold_b_ids: list[str]) -> dict:
    arm = ff.ROLL2["arm"]
    composed = compose(REPO_ROOT, ff.MODEL_FRAGMENT, ff.DATASET_FRAGMENT, arm["baseline"], arm["cell"])
    binding = load_knowledge_store_binding(composed.values, data_root=data_root)
    if binding is None:
        raise SystemExit("cell ROLL-2 binds no named knowledge stores")
    composite = set(binding.composite_snapshot.source_sample_ids)
    fold_b = set(fold_b_ids)
    fold_b_utt = {ff.utterance_of(s) for s in fold_b}
    stores = {}
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        ids = set(store.snapshot.source_sample_ids)
        stores[store_id] = {
            "snapshot_relpath": store.snapshot_pin["relpath"],
            "snapshot_sha256": store.snapshot_pin["sha256"],
            "source_sample_ids": len(ids),
            "shared_recordings_with_filler": len(fold_b & ids),
            "shared_utterances_with_filler": len(fold_b_utt & {ff.utterance_of(s) for s in ids}),
        }
    shared = fold_b & composite
    shared_utt = fold_b_utt & {ff.utterance_of(s) for s in composite}
    if shared or shared_utt:
        raise SystemExit(f"TRAIN Fold B overlaps the composite knowledge sources: {len(shared)} / {len(shared_utt)}")

    pool = binding.store("train-exemplars")
    pool_utt = {ff.utterance_of(s) for s in pool.snapshot.source_sample_ids}
    fold_a = json.loads((REPO_ROOT / ff.ROLL2_ROSTER).read_text(encoding="utf-8"))
    fold_a_utt = {item["utterance_id"] for item in fold_a["items"]}
    if pool_utt & fold_a_utt or pool_utt & fold_b_utt or fold_a_utt & fold_b_utt:
        raise SystemExit("the pool, Fold A and Fold B are not pairwise disjoint by utterance")
    union = len(pool_utt | fold_a_utt | fold_b_utt)
    if union != SLURP_TRAIN_UTTERANCES:
        raise SystemExit(f"pool + Fold A + Fold B cover {union} TRAIN utterances, not {SLURP_TRAIN_UTTERANCES}")
    return {
        "derivation": (
            "core.config.compose of cell ROLL-2's fragments (model, the TRAIN Fold B view, ROLL-2's baseline and "
            "experiment) then rails.knowledge_stores.load_knowledge_store_binding; the guard set is the composite "
            "snapshot's source_sample_ids, exactly the intersection rails.runner computes before it dispatches a "
            "row. The filler cells compose the SAME three stores (only query files and the agreement pin move), "
            "so this set is theirs."
        ),
        "binding_sha256": binding.binding_sha256,
        "composite_snapshot_sha256": binding.composite_snapshot.content_hash(),
        "composite_source_sample_ids": len(composite),
        "shared_recordings_with_filler": 0,
        "shared_utterances_with_filler": 0,
        "stores": stores,
        "admissible_universe": {
            "statement": (
                "pool utterances, TRAIN Fold A utterances and TRAIN Fold B utterances are pairwise disjoint and "
                f"together cover all {SLURP_TRAIN_UTTERANCES} SLURP TRAIN utterances, so every TRAIN row outside "
                "the composite knowledge sources and outside Fold A is a TRAIN Fold B row: the filler roster is "
                "the WHOLE admissible universe for the current best system, and six chunks of 180 exhaust it."
            ),
            "pool_utterances": len(pool_utt),
            "fold_a_utterances": len(fold_a_utt),
            "fold_b_utterances": len(fold_b_utt),
            "union": union,
            "slurp_train_utterances": SLURP_TRAIN_UTTERANCES,
            "source_of_the_total": (
                "the SLURP TRAIN split's 11,514 utterances (vectors/slurp-kus3/facet-vectors.jsonl embeds one "
                "vector per governed TRAIN utterance, 11,514; the pool receipt "
                "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json selects all 9,354 remaining "
                "after excluding Fold A and Fold B)"
            ),
        },
    }


def draw(parent: dict) -> dict[int, list[dict]]:
    by_stratum: dict[str, list[dict]] = {}
    for item in parent["items"]:
        by_stratum.setdefault(item["stratum"], []).append(item)
    counts = {k: len(v) for k, v in by_stratum.items()}
    per = ff.PER_SCENARIO_PER_CHUNK
    sizes = set(counts.values())
    if len(sizes) != 1 or next(iter(sizes)) % per:
        raise SystemExit(f"the parent's strata are not equal multiples of {per}: {counts}")
    n_chunks = next(iter(sizes)) // per
    rng = random.Random(ff.SEED)
    chunks: dict[int, list[dict]] = {k: [] for k in range(1, n_chunks + 1)}
    for stratum in sorted(by_stratum):
        pool = sorted(by_stratum[stratum], key=lambda item: item["sample_id"])
        rng.shuffle(pool)
        for index in range(n_chunks):
            chunks[index + 1].extend(pool[index * per:(index + 1) * per])
    order = {item["sample_id"]: i for i, item in enumerate(parent["items"])}
    for k in chunks:
        chunks[k].sort(key=lambda item: order[item["sample_id"]])
    return chunks


def _receipt(*, roster_id: str, items: list[dict], selection_rule: str, draw_method: str, parent_block: dict,
             extra: dict) -> dict:
    ids = [item["sample_id"] for item in items]
    strata = Counter(item["stratum"] for item in items)
    document = {
        "authority": AUTHORITY,
        "carrier_lock_key": "slurp",
        "draw_method": draw_method,
        "excluded_count": 0,
        "generator": GENERATOR,
        "items": items,
        "offline_guard": None,
        "parent": parent_block,
        "per_stratum": dict(sorted(strata.items())),
        "roster_id": roster_id,
        "roster_role": "construction",
        "roster_role_note": ROLE_NOTE,
        "schema": "saea-roster-receipt-v1",
        "seed": ff.SEED,
        "selection_rule": selection_rule,
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "split_role": "discovery",
        "strata_counts": dict(sorted(strata.items())),
        "audio_seconds_total": round(sum(float(item["audio_seconds"]) for item in items), 6),
        "headset_recordings": sum(1 for item in items if item.get("headset")),
        "distinct_utterances": len({item["utterance_id"] for item in items}),
    }
    document.update(extra)
    return document


def build(data_root: Path) -> dict[str, dict]:
    guard = arm_offline_guard()
    parent = json.loads((REPO_ROOT / ff.PARENT_ROSTER).read_text(encoding="utf-8"))
    parent_hash = verify_roster(parent)
    parent_file_sha = ff.sha_file(ff.PARENT_ROSTER)
    ids = [item["sample_id"] for item in parent["items"]]
    kg = knowledge_guard(data_root, ids)
    superseded = {entry["relpath"] for entry in (parent.get("supersedes") or {}).get("rosters", [])}
    proof = disjointness(ids, superseded)
    chunks = draw(parent)
    parent_block = {
        "count": len(ids),
        "file_sha256": parent_file_sha,
        "relpath": ff.PARENT_ROSTER,
        "roster_id": ff.PARENT_ROSTER_ID,
        "split_identity_hash": parent_hash,
    }
    chunk_of = {item["sample_id"]: k for k, items in chunks.items() for item in items}
    family_items = [dict(item, chunk=chunk_of[item["sample_id"]]) for item in parent["items"]]
    out: dict[str, dict] = {}
    family = _receipt(
        roster_id=ff.FAMILY_ROSTER_ID,
        items=family_items,
        selection_rule=(
            "The WHOLE of TRAIN Fold B (docs/receipts/rosters/slurp-evo-fold-b-v2.json), every item verbatim in the "
            "parent's order, each tagged with its chunk. Chunk assignment: seed 20260927, one random.Random advanced "
            "across the 18 scenarios in ascending name order; each scenario's 60 recordings, id-sorted, shuffled and "
            "dealt ten to each chunk in chunk order, so every chunk holds 180 rows, ten per scenario."
        ),
        draw_method="No new draw of rows: the family is the parent verbatim. The seed drives the CHUNK ASSIGNMENT only.",
        parent_block=parent_block,
        extra={
            "chunks": {
                f"c{k:02d}": {
                    "count": len(items),
                    "roster": ff.names(k)["roster"],
                    "roster_id": ff.names(k)["roster_id"],
                    "split_identity_hash": split_identity_hash(prefixed("slurp", [i["sample_id"] for i in items])),
                    "per_stratum": dict(sorted(Counter(i["stratum"] for i in items).items())),
                }
                for k, items in sorted(chunks.items())
            },
            "chunk_rule": "ten rows per scenario per chunk; chunks are pairwise disjoint and their union is the family",
            "disjointness_proof": proof,
            "knowledge_source_guard": kg,
        },
    )
    out[ff.FAMILY_ROSTER] = family
    for k, items in sorted(chunks.items()):
        n = ff.names(k)
        out[n["roster"]] = _receipt(
            roster_id=n["roster_id"],
            items=items,
            selection_rule=f"Chunk c{k:02d} of {ff.FAMILY_ROSTER_ID}: the items the family receipt tags chunk {k}, in the parent's order.",
            draw_method="No draw: a pure SELECTION of the family receipt's items by their chunk tag.",
            parent_block={**parent_block, "family": ff.FAMILY_ROSTER, "family_roster_id": ff.FAMILY_ROSTER_ID},
            extra={
                "chunk": k,
                "disjointness_proof": {
                    "inherited_from": ff.FAMILY_ROSTER,
                    "statement": "a subset of the family roster, whose proof (every roster, every probe sample, devel, test, every knowledge source) holds for it verbatim",
                },
                "knowledge_source_guard": {"inherited_from": ff.FAMILY_ROSTER, "shared_recordings_with_filler": 0},
            },
        )
    smoke_n = ff.names(1, smoke=True)
    smoke_items = chunks[1][: ff.SMOKE_ROWS]
    out[smoke_n["roster"]] = _receipt(
        roster_id=smoke_n["roster_id"],
        items=smoke_items,
        selection_rule=f"The FIRST {ff.SMOKE_ROWS} items of chunk c01 in the parent's order: the structural form smoke of the family's composed form.",
        draw_method="No draw: a prefix of the chunk c01 receipt.",
        parent_block={**parent_block, "family": ff.FAMILY_ROSTER, "chunk_roster": ff.names(1)["roster"]},
        extra={
            "chunk": 1,
            "disjointness_proof": {"inherited_from": ff.FAMILY_ROSTER},
            "knowledge_source_guard": {"inherited_from": ff.FAMILY_ROSTER, "shared_recordings_with_filler": 0},
        },
    )
    for document in out.values():
        document["offline_guard"] = {"attempted_targets": list(guard.targets), "outbound_connection_attempts": guard.count}
        verify_roster(document)
    union = [i["sample_id"] for k in chunks for i in chunks[k]]
    if sorted(union) != sorted(ids) or len(set(union)) != len(union):
        raise SystemExit("the chunks do not partition the family roster")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write receipts that do not exist yet")
    mode.add_argument("--check", action="store_true", help="recompute and compare against the committed receipts")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    data_root = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
    receipts = build(data_root)
    report = {}
    for relpath, document in receipts.items():
        # core.roster.write_roster's own serialisation (sorted keys, indent 2, trailing newline)
        payload = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        target = REPO_ROOT / relpath
        if args.check:
            same = target.is_file() and target.read_bytes() == payload
            report[relpath] = "identical" if same else "DIFFERS"
        elif args.write:
            if target.exists():
                if target.read_bytes() != payload:
                    raise SystemExit(f"refusing to overwrite a different existing receipt: {relpath}")
                report[relpath] = "exists-identical"
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                report[relpath] = "written"
        else:
            report[relpath] = "dry"
        report[relpath] = {"state": report[relpath], "count": len(document["items"]),
                           "split_identity_hash": document["split_identity_hash"]}
    family = receipts[ff.FAMILY_ROSTER]
    print(json.dumps({"receipts": report,
                      "chunks": {k: v["count"] for k, v in family["chunks"].items()},
                      "knowledge_source_guard": {k: v for k, v in family["knowledge_source_guard"].items() if k != "stores"},
                      "disjointness": {"receipts_checked": len(family["disjointness_proof"]["receipts_checked"]),
                                       "receipts_without_item_ids": len(family["disjointness_proof"]["receipts_without_item_ids"]),
                                       "governed_splits": family["disjointness_proof"]["governed_splits"]},
                      "offline_guard": family["offline_guard"]}, indent=2))
    if args.check and any(v["state"] == "DIFFERS" for v in report.values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
