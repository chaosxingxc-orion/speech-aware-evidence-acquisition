#!/usr/bin/env python3
"""Build cell W5's knowledge (knowledge-wave item W5, slot-side retrieval; owner decision 170):
a SECOND speech-keyed exemplar route for the Solver, scoped by the row's own retrieval
shortlist, over the R01-excluded TRAIN exemplar pool.

WHAT W5 DELIVERS. The retained AGREE arm already hands the Solver the row's 20 nearest TRAIN
exemplars by speech (module M1, the 9,354-utterance pool, pure cosine). W5 adds ONE route: up to
N = S x P further TRAIN exemplars from the R01-excluded 8,554-utterance pool, each an utterance
that CARRIES AT LEAST ONE SLOT, chosen by

  1. the row's own speech vector (the same sealed query vector M1 uses), and
  2. the row's retrieval SHORTLIST: the first S = 3 intents of the ordered intent-boundary block
     the AGREE arm's Perception channel delivers (written-key cosine + 1.0 x the pinned,
     self-excluded exemplar-intent vote, fuse 8-1-8) -- the retrieval-side analogue of the <= 3
     candidates Perception names,

round-robin over the shortlist (the nearest slot-bearing exemplar of intent 1, of intent 2, of
intent 3, then the second nearest of each, ...), P per intent, never an utterance M1 already
delivers on that row; when a shortlist intent has fewer than P such exemplars inside the recall,
the remaining slots are filled by the nearest other slot-bearing exemplars not already listed
(tier B), so every row receives exactly N and no slot is ever filled by an arbitrary facet.

HOW IT FLIES WITHOUT NEW CODE. The route is an ordinary later-phase ``phase_supply.solver`` on a
new store id ``slot-exemplars`` (a release file that binds the ALREADY RELEASED R01-excluded pool
snapshot; no snapshot is copied or rebuilt). The ordering above is pre-computed here, per row, as
a receipt-pinned table in the ``sealed-agreement`` line format and read by the registered ranker
``saea-rank-wcos-prior-agree-v1`` through its own ``w_agree`` term (``w_cos`` 0, ``w_prior`` 0,
``w_agree`` 1): each listed facet carries a strictly decreasing share (``(L - j) / sum``, summing to
1 per row), every other recalled facet scores 0, and ``saea-fuse-associated-values-v1`` (m = K,
c = 1, top_l = N) delivers the first N. The table reuses the ranker's one reserved agreement
dimension; its ``embedded_signal`` says what it carries.

WHAT IT IS ARITHMETIC OVER. The AGREE arm's composed config (roster, packets, split identity, the
two flown channel specs), two pinned vector files, the pinned agreement table and two released
snapshots -- each verified against its sha256 by this repository's own loaders -- through this
repository's own ``build_supply_for_phase`` and ``KbFacetProvider`` (the recall, ranker and fuser
the flight runs). ZERO model, server, tokenizer, encoder, embedder, scorer, network, GPU and
paid-API contacts: no server is started or probed, no waveform is decoded, no embedding computed.

WHAT NEVER ENTERS IT. No Fold A gold label, reference transcript, flight output, score or future
turn: the Fold A side is the row's own sealed speech vector and the deterministic retrieval
ranking over it; the TRAIN side is each pool value's frozen build-time ``task_target`` and its
released content. The pool is the R01-excluded construction pool, and this script PROVES that no
Fold A utterance is in it (roster exclusion proof, written to the receipt).

WHAT IT PRINTS AND WRITES. Ids, counts, rates and hashes only; no utterance text, filler or
knowledge body. Outputs under ``$SPEECHRL_DATA_DIR``:
  prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/agreement.jsonl   (the pinned table)
  prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/selection-v1.jsonl (ids: shortlist, M1 ids, W5 ids)
  prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1/receipt.json
  knowledge/slurp/saea-kb-distmodel-v1/slot-exemplars-w5-v1/release.json

    python scripts/build_slurp_slot_exemplar_scope_w5.py --data-root "$SPEECHRL_DATA_DIR" \\
        --runtime-root /home/chao --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \\
        [--measure]   # print the recall-width table and write nothing
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

from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.kb_policy import EXEMPLAR_INTENT_AGREEMENT_DIMENSION  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    SEALED_AGREEMENT_SCHEMA,
    SEED_QUERY_ID_PREFIX,
    SealedSegmentQuery,
    build_supply_for_phase,
    load_phase_supply_specs,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState  # noqa: E402

BUILDER_ID = "saea-slurp-w5-slot-exemplar-scope-builder-v1"
ARTIFACT_ID = "SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
OUT = "prepared/" + ARTIFACT_ID
BASE_EXPERIMENT = "slurp-native-stage3-agree-w1-fold-a-v1"
BOUNDARY_STORE, BOUNDARY_PHASE = "intent-boundaries", "perception"
M1_STORE, SOLVER = "train-exemplars", "solver"
BOUNDARY_PREFIX = "intent-boundary:"
POOL_DIR = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01"
POOL_SNAPSHOT = {"relpath": POOL_DIR + "/snapshot.json",
                 "sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"}
POOL_RELEASE = {"relpath": POOL_DIR + "/release.json"}
NEW_STORE_ID = "slot-exemplars"
NEW_RELEASE_DIR = "knowledge/slurp/saea-kb-distmodel-v1/slot-exemplars-w5-v1"
DEFAULT_K, DEFAULT_S, DEFAULT_P = 300, 3, 3

EMBEDDED_SIGNAL = (
    "derived: a strictly decreasing per-row ORDER over this store's recalled facets, pre-computed "
    "model-free by scripts/build_slurp_slot_exemplar_scope_w5.py: the nearest slot-bearing exemplars "
    "(by the row's own sealed speech vector) of each of the first three intents of the row's AGREE "
    "intent-boundary ranking (written-key cosine + 1.0 x the pinned self-excluded exemplar-intent vote), "
    "round-robin, never an utterance the row's M1 exemplar route already delivers, then the nearest other "
    "slot-bearing exemplars as fill; shares (L - j) / sum. Speech-keyed and gold-free: no label, "
    "transcript, flight output or future turn of the evaluated row enters it. The reserved agreement "
    "dimension is reused as the ranker's one pre-computed per-row signal slot."
)


class BuildError(RuntimeError):
    pass


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utterance_identity(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) < 3 or not all(parts[:3]):
        raise BuildError("a sample id carries no three-field utterance identity")
    return ":".join(parts[:3])


def slot_bearing(content: str) -> bool:
    """The released annotated-exemplar view renders '<utterance> | <intent> | <slots>'; the third
    segment is a single word when the utterance carries no slot and 'type=filler; ...' otherwise."""
    parts = content.split(" | ")
    if len(parts) != 3:
        raise BuildError("an exemplar value does not carry the three-part annotated view")
    return "=" in parts[2]


def load_snapshot(data_root: Path, pin: dict) -> KnowledgeSnapshot:
    snapshot = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / pin["relpath"]).read_text(encoding="utf-8")))
    if snapshot.content_hash() != pin["sha256"]:
        raise BuildError(f"{pin['relpath']} does not hash to its pin")
    return snapshot


def rank_and_fuse(spec, provider, query_record, descriptor, sample_id, split_identity):
    """Exactly ``rails.phase_supply._bootstrap_select``, returning the RankResult too."""
    seed_state = QueryState(
        query_id=f"{SEED_QUERY_ID_PREFIX}:{spec.phase}:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=str(descriptor["packet_id"]),
        speech_packet_sha256=str(descriptor["sha256"]),
        use_split_identity_hash=split_identity,
        query_source="speech_audio" if isinstance(query_record, SealedSegmentQuery) else "speech_features",
    ).validate()
    if isinstance(query_record, SealedSegmentQuery):
        provider_query = {"query_state": seed_state, "query_segments": query_record.segments}
    else:
        provider_query = {"query_state": seed_state, "query_vectors": dict(query_record)}
    ranking = provider.candidates(provider_query, k=spec.k)
    fusion = provider.fuse([ranking], k=spec.k, policy_id=spec.fuse_policy)
    return ranking, fusion


def channel(spec_raw: dict, phase: str, program, snapshot, data_root: Path):
    specs = load_phase_supply_specs({"phase_supply": {phase: spec_raw}}, program)
    spec = specs[phase]
    callback = build_supply_for_phase({phase: spec}, snapshot=snapshot, snapshot_sha256=snapshot.content_hash(),
                                      data_root=data_root, seed_phases=(phase,))
    if callback is None:
        raise BuildError(f"no supply callable for {phase}")
    return spec, callback.provider_factories[phase](), callback.query_tables.get(phase) or {}


def w5_spec(m1_raw: dict, *, k: int, n: int, table: dict | None) -> dict:
    spec = {
        "dimensions": list(m1_raw["dimensions"]), "expose_facets": False,
        "facet_source": dict(m1_raw["facet_source"]), "query_source": dict(m1_raw["query_source"]),
        "provider": "kb-facet-v1", "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-associated-values-v1", "fuse_coverage": {"m": k, "c": 1, "top_l": n},
        "k": k, "tau": 0.0,
        "rank_weights": {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0} if table is None
        else {"w_cos": 0.0, "w_prior": 0.0, "w_agree": 1.0},
    }
    if table is not None:
        spec["agreement_source"] = table
    return spec


def build(args) -> dict:
    data_root = Path(args.data_root).resolve()
    cells = [c for c in load_campaign_cells(REPO_ROOT, BASE_EXPERIMENT) if c.document["cell_id"] == BASE_EXPERIMENT]
    if len(cells) != 1:
        raise BuildError("the AGREE experiment does not declare exactly one arm cell")
    cell = cells[0]
    runtime = build_flight_runtime(
        REPO_ROOT, data_root, model=cell.document["model_fragment"], dataset=cell.document["dataset_fragment"],
        baseline=cell.document["baseline_fragment"], experiment=BASE_EXPERIMENT, run_id=cell.run_id,
        attempt_id=cell.attempt_id, runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
    )
    _program, binding, _specs, _first, split_identity, _inputs = runtime.phase_supply_artifact_identity()
    values = runtime._composed.values  # noqa: SLF001 -- read-only
    stores = values["knowledge_stores"]
    program = default_phase_program(str(values["policy"]))
    packets = dict(binding["speech_packet_bindings"])
    roster = sorted(packets)

    # --- the roster exclusion proof: no Fold A utterance in the construction pool ---------------
    pool = load_snapshot(data_root, POOL_SNAPSHOT)
    pool_release = json.loads((data_root / POOL_RELEASE["relpath"]).read_text(encoding="utf-8"))
    if pool_release["snapshot_sha256"] != POOL_SNAPSHOT["sha256"]:
        raise BuildError("the R01-excluded pool release does not bind the pinned snapshot")
    roster_utts = {utterance_identity(s) for s in roster}
    pool_utts = {utterance_identity(s) for v in pool.values for s in v.source_sample_ids}
    overlap = roster_utts & pool_utts
    if overlap:
        raise BuildError(f"{len(overlap)} Fold A utterances are in the construction pool; refusing")
    m1_snapshot = load_snapshot(data_root, stores[M1_STORE]["snapshot"])
    m1_utts = {utterance_identity(s) for v in m1_snapshot.values for s in v.source_sample_ids}
    exclusion = {
        "roster_rows": len(roster), "roster_utterances": len(roster_utts), "split_identity_hash": split_identity,
        "pool_values": len(pool.values), "pool_utterances": len(pool_utts), "pool_recordings": len(pool.source_sample_ids),
        "pool_snapshot_content_sha256": POOL_SNAPSHOT["sha256"],
        "pool_source_split_identity_hash": pool.source_split_identity_hash,
        "fold_a_utterances_in_pool": 0,
        "pool_utterances_outside_the_flown_m1_pool": len(pool_utts - m1_utts),
        "m1_pool_utterances_outside_this_pool": len(m1_utts - pool_utts),
        "rule": "utterance identity = the first three fields of a sample id; any recording of a Fold A utterance would refuse the build",
    }

    # --- the three channels, through the flight's own seams -------------------------------------
    b_spec, b_provider, b_queries = channel(stores[BOUNDARY_STORE]["phase_supply"][BOUNDARY_PHASE], BOUNDARY_PHASE,
                                            program, load_snapshot(data_root, stores[BOUNDARY_STORE]["snapshot"]), data_root)
    m1_raw = stores[M1_STORE]["phase_supply"][SOLVER]
    m_spec, m_provider, m_queries = channel(m1_raw, SOLVER, program, m1_snapshot, data_root)
    k, s, p = args.recall_k, args.shortlist, args.per_candidate
    n = s * p
    r_spec, r_provider, r_queries = channel(w5_spec(m1_raw, k=k, n=n, table=None), SOLVER, program, pool, data_root)
    for name, table in (("boundary", b_queries), ("m1", m_queries), ("recall", r_queries)):
        missing = [x for x in roster if x not in table]
        if missing:
            raise BuildError(f"{len(missing)} roster rows have no {name} query vector; refusing")

    value_of_facet = {}
    for v in pool.values:
        for f in v.associated_facet_ids:
            value_of_facet[f] = v
    bearing = {v.value_id: slot_bearing(v.content) for v in pool.values}
    intent_of = {v.value_id: v.task_target for v in pool.values}
    pool_by_intent = Counter(v.task_target for v in pool.values if bearing[v.value_id])

    rows, selection, stats = [], [], Counter()
    tierA_hist, fill_hist = Counter(), Counter()
    for sample_id in roster:
        desc = packets[sample_id]
        b_rank, b_fuse = rank_and_fuse(b_spec, b_provider, b_queries[sample_id], desc, sample_id, split_identity)
        order = [e.entry_id for e in b_rank.entries]
        top8 = order[: b_spec.fuse_knobs().top_l]
        if set(top8) != set(b_fuse.selected_value_ids):
            raise BuildError("the replayed boundary order does not reproduce the delivered eight")
        shortlist = [f[len(BOUNDARY_PREFIX):] for f in order[:s]]
        _m_rank, m_fuse = rank_and_fuse(m_spec, m_provider, m_queries[sample_id], desc, sample_id, split_identity)
        m1_ids = set(m_fuse.selected_value_ids)
        r_rank, _ = rank_and_fuse(r_spec, r_provider, r_queries[sample_id], desc, sample_id, split_identity)
        recall = [e.entry_id for e in r_rank.entries]
        own = utterance_identity(sample_id)
        eligible = [f for f in recall
                    if bearing[value_of_facet[f].value_id] and value_of_facet[f].value_id not in m1_ids
                    and own not in {utterance_identity(x) for x in value_of_facet[f].source_sample_ids}]
        per_intent = {i: [f for f in eligible if intent_of[value_of_facet[f].value_id] == i][:p] for i in shortlist}
        tier_a = [per_intent[i][d] for d in range(p) for i in shortlist if d < len(per_intent[i])]
        tier_b = [f for f in eligible if f not in set(tier_a)][: n]
        listed = tier_a + tier_b
        if len(listed) < n:
            raise BuildError("a row cannot list N eligible facets inside the recall; widen the recall")
        weights = [len(listed) - j for j in range(len(listed))]
        total = float(sum(weights))
        scores = {f: w / total for f, w in zip(listed, weights)}
        rows.append({"schema": SEALED_AGREEMENT_SCHEMA, "id": sample_id, "dimension": EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
                     "scores": dict(sorted(scores.items())), "vote_total": len(listed), "self_excluded": 0})
        delivered = [value_of_facet[f].value_id for f in listed[:n]]
        selection.append({"id": sample_id, "shortlist": shortlist, "m1_value_ids": sorted(m1_ids),
                          "w5_value_ids": sorted(delivered), "tier_a": len(tier_a), "fill": n - min(n, len(tier_a))})
        tierA_hist[min(len(tier_a), n)] += 1
        fill_hist[n - min(n, len(tier_a))] += 1
        stats["rows"] += 1
        stats["shortlist_intents_with_p_items"] += sum(1 for i in shortlist if len(per_intent[i]) >= p)
        stats["shortlist_intents_with_no_item"] += sum(1 for i in shortlist if not per_intent[i])
        stats["shortlist_intents_without_slot_bearing_pool_items"] += sum(1 for i in shortlist if pool_by_intent[i] == 0)
        stats["delivered_values"] += n
        stats["delivered_tier_a"] += min(n, len(tier_a))
    report = {
        "recall_k": k, "shortlist": s, "per_candidate": p, "n": n,
        "rows": stats["rows"], "tier_a_items_per_row_histogram": dict(sorted(tierA_hist.items())),
        "fill_items_per_row_histogram": dict(sorted(fill_hist.items())),
        "delivered_tier_a_share": round(stats["delivered_tier_a"] / stats["delivered_values"], 4),
        "shortlist_intents_with_full_p": stats["shortlist_intents_with_p_items"],
        "shortlist_intents_with_no_item": stats["shortlist_intents_with_no_item"],
        "shortlist_intents_without_slot_bearing_pool_items": stats["shortlist_intents_without_slot_bearing_pool_items"],
        "slot_bearing_pool_values": sum(1 for x in bearing.values() if x),
    }
    if args.measure:
        return {"measure": report}

    out_dir = data_root / OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n" for r in rows).encode("utf-8")
    (out_dir / "agreement.jsonl").write_bytes(payload)
    table_pin = {"embedded_signal": EMBEDDED_SIGNAL, "kind": "sealed-agreement",
                 "relpath": OUT + "/agreement.jsonl", "sha256": digest_bytes(payload),
                 "tool_contact_ledger_row": ARTIFACT_ID}
    sel_payload = "".join(json.dumps(r, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n" for r in selection).encode("utf-8")
    (out_dir / "selection-v1.jsonl").write_bytes(sel_payload)

    # --- the release that binds the already-released pool snapshot under the new store id ------
    release = {
        "builder_policy_id": pool.builder_policy_id, "schema": pool_release["schema"],
        "snapshot_sha256": POOL_SNAPSHOT["sha256"], "source": dict(pool_release["source"]),
        "source_split_identity_hash": pool.source_split_identity_hash,
        "store_id": NEW_STORE_ID, "store_role": pool_release["store_role"],
    }
    rel_dir = data_root / NEW_RELEASE_DIR
    rel_dir.mkdir(parents=True, exist_ok=True)
    rel_bytes = (json.dumps(release, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (rel_dir / "release.json").write_bytes(rel_bytes)

    # --- verification: the W5 route as it will fly selects exactly the intended N per row --------
    v_spec, v_provider, v_queries = channel(w5_spec(m1_raw, k=k, n=n, table=table_pin), SOLVER, program, pool, data_root)
    agree = 0
    for sel in selection:
        sid = sel["id"]
        _r, fuse = rank_and_fuse(v_spec, v_provider, v_queries[sid], packets[sid], sid, split_identity)
        agree += int(sorted(fuse.selected_value_ids) == sel["w5_value_ids"])
    if agree != len(selection):
        raise BuildError(f"the flown route reproduces the intended selection on {agree} of {len(selection)} rows")

    receipt = {
        "schema": "saea-phase-agreement-receipt-v1", "artifact_id": ARTIFACT_ID, "builder_id": BUILDER_ID,
        "builder_sha256": digest_file(Path(__file__)),
        "generated_at": datetime.now(timezone.utc).isoformat(), "contact_class": "model-free",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                     "network": 0, "gpu": 0, "paid_api": 0},
        "artifact": {"relpath": table_pin["relpath"], "sha256": table_pin["sha256"], "rows": len(rows),
                     "dimension": EXEMPLAR_INTENT_AGREEMENT_DIMENSION, "line_schema": SEALED_AGREEMENT_SCHEMA},
        "selection": {"relpath": OUT + "/selection-v1.jsonl", "sha256": digest_bytes(sel_payload)},
        "release": {"relpath": NEW_RELEASE_DIR + "/release.json", "sha256": digest_bytes(rel_bytes),
                    "store_id": NEW_STORE_ID, "binds_snapshot": POOL_SNAPSHOT},
        "table_pin": table_pin,
        "w5_phase_supply_solver": v_spec.as_json(),
        "derived_from": {"experiment": BASE_EXPERIMENT, "run_id": cell.run_id, "split_identity_hash": split_identity,
                         "boundary_spec": b_spec.as_json(), "m1_spec": m_spec.as_json()},
        "roster_exclusion_proof": exclusion,
        "measure": report,
        "verification": {"rows": len(selection), "flown_route_reproduces_intended_selection": agree,
                         "replayed_boundary_order_reproduces_delivered_eight": len(selection)},
        "implementation": {name: digest_file(Path(sys.modules[name].__file__)) for name in sorted((
            "speech_aware_evidence_acquisition.rails.kb_policy",
            "speech_aware_evidence_acquisition.rails.knowledge_provider",
            "speech_aware_evidence_acquisition.rails.phase_supply"))},
        "boundary": "A pre-computed model-free input, never an authorization: it opens no attempt, reserves no contact and states no effectiveness claim. No Fold A gold label, reference transcript, flight output or future turn enters it.",
    }
    (out_dir / "receipt.json").write_bytes((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {"table": table_pin["sha256"], "release": receipt["release"]["sha256"],
            "selection": receipt["selection"]["sha256"], "receipt": digest_file(out_dir / "receipt.json"),
            "measure": report, "exclusion": exclusion, "verification": receipt["verification"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--runtime-root", default="/home/chao")
    parser.add_argument("--lock-path", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    parser.add_argument("--recall-k", type=int, default=DEFAULT_K)
    parser.add_argument("--shortlist", type=int, default=DEFAULT_S)
    parser.add_argument("--per-candidate", type=int, default=DEFAULT_P)
    parser.add_argument("--measure", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(build(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
