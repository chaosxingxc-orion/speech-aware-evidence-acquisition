"""P-CORR-F BINDING PHASE -- OFFLINE, ZERO MODEL CALLS, ZERO GOLD.

The registered construction (preregistration section 1):

    assert_ledger_row_consumed("SAEA-PROBE-pslu-n60")           (consumed=yes)
      -> rails.probes.pcorrf_flight.harvest_a0_emitted_slots     (ALL emitted
             (type, filler) slots of the consumed A0 attempt -- never a
             wrong-only subset, which would be an oracle here)
      -> rails.probes.pcorrf_flight.mine_train_pool              (SLURP
             train.jsonl ONLY, full pairs, never load_slurp_ontology)
         + assert_train_pool_sha256                              (pinned pin)
      -> rails.probes.pcorrf_flight.build_corrective_binding      (tri-derivation
             site #1: L1 per sample, W4-additional L2b widening, seeded
             fixed-point-free W2 cross-sample draw)
      -> rails.probes.pcorrf_flight.assert_corrective_binding_hash (site #2)

Unlike the P-TRAP binding this file is modelled on, NOTHING here touches gold:
``harvest_a0_emitted_slots`` parses the consumed A0 responses with
``reproduction.slurp_scoring.parse_slu_response`` alone, and the pool comes
from ``train.jsonl``. "Wrong" is never computed, so no gold loader is imported
and none may be -- ``rails.probes.pcorrf_flight``'s own import-time AST guard
(``assert_never_references_forbidden_gold_symbols``) enforces the same ban on
the machinery side. Nothing here scores, ranks or interprets a response; the
only things this file ever prints are COUNTS.

Two artifacts are written:

  corrective-binding.json        the full per-sample SampleCorrectiveSet table
                                 (L1 / W2 / W4-additional entries with their
                                 origin sample ids) -- this is the SUPPLY
                                 CONTENT the flight renders. Percept-selected
                                 text; stays under the scratchpad /
                                 SPEECHRL_DATA_DIR, never committed.
  corrective-binding-stats.json  STRUCTURAL ONLY: per-arm corrective-entry
                                 count (K) distributions, K=0 sample lists,
                                 totals, donor breadth. This is the artifact
                                 the flight receipt and the docs/checks archive
                                 carry.

``binding_hash`` is the machinery's OWN tri-derivation
``compute_corrective_binding_hash`` value (a pure function of the per-sample A0
response sha256 set, the train-pool sha256, and the seed). ``document_hash``
is additionally the sha256 of the canonical corrective-binding.json document;
the launcher recomputes BOTH from the SAME deterministic inputs and refuses to
fly if either disagrees, so the flight can never render a table other than the
one this reviewed binding step produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (  # noqa: E402
    CONSUMED_PSLU_ATTEMPT_ID,
    CONSUMED_PSLU_ARM,
    CONSUMED_PSLU_RUN_EXPERIMENT_ID,
    DEFAULT_SEED,
    PCORRF_ARMS,
    W1_ARM,
    W2_ARM,
    W3_ARM,
    W4_ARM,
    PCorrFBindingTable,
    SampleCorrectiveSet,
    CorrectiveEntry,
    assert_binding_config_sha256,
    assert_corrective_binding_hash,
    assert_ledger_row_consumed,
    assert_split_identity_hash,
    assert_train_pool_sha256,
    binding_config_sha256,
    build_corrective_binding,
    harvest_a0_emitted_slots,
    mine_train_pool,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_sample_manifest,
)

SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"


def consumed_attempt_dir() -> Path:
    data_dir = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_dir:
        raise RuntimeError("SPEECHRL_DATA_DIR is unset; cannot resolve the consumed P-SLU attempt")
    return (
        Path(data_dir.rstrip("/"))
        / "runs"
        / CONSUMED_PSLU_RUN_EXPERIMENT_ID
        / CONSUMED_PSLU_ATTEMPT_ID
    )


def build_binding() -> tuple[PCorrFBindingTable, dict[str, object]]:
    """Deterministic, pure-given-inputs: the machinery's own binding table plus
    the JSON document that gets hashed. Thin wrapper over
    :func:`build_binding_full` for callers that do not need the harvest."""

    table, document, _harvested = build_binding_full()
    return table, document


def build_binding_full():
    """As :func:`build_binding`, but also returns the ``harvested`` mapping the
    flight needs: ``run_pcorrf_flight`` re-derives the tri-derivation binding
    hash from it at guard site #3, before it issues any request."""

    assert_binding_config_sha256()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    assert_split_identity_hash(manifest.split_identity_hash)

    # Mission instruction / machinery docstring: the consumed-artifact ledger
    # anchor is verified BEFORE the artifact is opened.
    assert_ledger_row_consumed(
        (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"),
        run_experiment_id=CONSUMED_PSLU_RUN_EXPERIMENT_ID,
    )

    harvested = harvest_a0_emitted_slots(consumed_attempt_dir())
    pool = mine_train_pool(lock, root)
    assert_train_pool_sha256(pool)

    table = build_corrective_binding(
        harvested=harvested, pool=pool, sample_ids=manifest.sample_ids, seed=DEFAULT_SEED
    )
    # Tri-derivation site #2, standalone, immediately after the builder.
    assert_corrective_binding_hash(table, harvested=harvested, seed=DEFAULT_SEED)

    document = {
        "schema": "saea-pcorrf-corrective-binding-v1",
        "run_id": "SAEA-PROBE-pcorrf-240",
        "preregistration": "docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md",
        "split_identity_hash": manifest.split_identity_hash,
        "binding_config_sha256": binding_config_sha256(),
        "consumed_pslu_run_experiment_id": CONSUMED_PSLU_RUN_EXPERIMENT_ID,
        "consumed_pslu_attempt_id": CONSUMED_PSLU_ATTEMPT_ID,
        "consumed_pslu_arm": CONSUMED_PSLU_ARM,
        "train_pool": {
            "sha256": pool.sha256,
            "n_pairs": pool.n_pairs,
            "n_values": pool.n_values,
            "n_types": pool.n_types,
        },
        "seed": DEFAULT_SEED,
        "binding_hash": table.binding_hash,
        "a0_response_sha256_by_sample": {
            sample_id: harvested[sample_id].response_sha256
            for sample_id in sorted(harvested)
            if sample_id in table.corrective_sets
        },
        "corrective_sets": {
            sample_id: {
                "l1_entries": [entry.as_json() for entry in cs.l1_entries],
                "w2_entries": [entry.as_json() for entry in cs.w2_entries],
                "w4_added_entries": [entry.as_json() for entry in cs.w4_added_entries],
                "emitted_slot_count": cs.emitted_slot_count,
            }
            for sample_id, cs in sorted(table.corrective_sets.items())
        },
    }
    return table, document, harvested


def canonical_hash(document: dict[str, object]) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def binding_table_from_document(document: dict) -> PCorrFBindingTable:
    """Reconstructs the machinery table from a reviewed document -- used only
    by tests/inspection; the flight itself always REBUILDS from the consumed
    inputs and cross-checks the hash, never trusts a file."""

    from types import MappingProxyType

    sets = {}
    for sample_id, block in document["corrective_sets"].items():
        sets[sample_id] = SampleCorrectiveSet(
            sample_id=sample_id,
            l1_entries=tuple(CorrectiveEntry.from_json(e) for e in block["l1_entries"]),
            w2_entries=tuple(CorrectiveEntry.from_json(e) for e in block["w2_entries"]),
            w4_added_entries=tuple(CorrectiveEntry.from_json(e) for e in block["w4_added_entries"]),
            emitted_slot_count=int(block["emitted_slot_count"]),
        )
    return PCorrFBindingTable(
        corrective_sets=MappingProxyType(sets),
        pool_sha256=str(document["train_pool"]["sha256"]),
        seed=int(document["seed"]),
        binding_hash=str(document["binding_hash"]),
    )


def arm_k_by_sample(document: dict[str, object]) -> dict[str, dict[str, int]]:
    """The per-arm corrective-entry count each arm will actually render.
    CONSTRUCTION metadata (how much supply was built), never a result."""

    sets = document["corrective_sets"]  # type: ignore[index]
    k: dict[str, dict[str, int]] = {arm: {} for arm in PCORRF_ARMS}
    for sample_id, block in sets.items():
        n_l1 = len(block["l1_entries"])
        k[W1_ARM][sample_id] = n_l1
        k[W2_ARM][sample_id] = len(block["w2_entries"])
        k[W3_ARM][sample_id] = n_l1
        k[W4_ARM][sample_id] = n_l1 + len(block["w4_added_entries"])
    return k


def stats_document(document: dict[str, object], document_hash: str) -> dict[str, object]:
    sets = document["corrective_sets"]  # type: ignore[index]
    k_by_arm = arm_k_by_sample(document)
    emitted = {sid: int(block["emitted_slot_count"]) for sid, block in sets.items()}
    donor_ids = Counter(
        entry["origin_sample_id"] for block in sets.values() for entry in block["w2_entries"]
    )
    per_arm: dict[str, object] = {}
    for arm in PCORRF_ARMS:
        ks = k_by_arm[arm]
        values = list(ks.values())
        per_arm[arm] = {
            "k_distribution": dict(sorted(Counter(values).items())),
            "k_total": sum(values),
            "k_mean": round(sum(values) / max(len(values), 1), 4),
            "k_max": max(values) if values else 0,
            "k_zero_sample_count": sum(1 for v in values if v == 0),
            "k_zero_sample_ids": sorted(sid for sid, v in ks.items() if v == 0),
            "k_by_sample": dict(sorted(ks.items())),
        }
    return {
        "schema": "saea-pcorrf-corrective-binding-stats-v1",
        "document_hash": document_hash,
        "binding_hash": document["binding_hash"],
        "binding_config_sha256": document["binding_config_sha256"],
        "run_id": document["run_id"],
        "split_identity_hash": document["split_identity_hash"],
        "consumed_pslu_attempt_id": document["consumed_pslu_attempt_id"],
        "consumed_pslu_arm": document["consumed_pslu_arm"],
        "train_pool": document["train_pool"],
        "seed": document["seed"],
        "n_samples": len(sets),
        "arms": list(PCORRF_ARMS),
        "emitted_slot_total": sum(emitted.values()),
        "emitted_slot_distribution": dict(sorted(Counter(emitted.values()).items())),
        "per_arm": per_arm,
        "w2_length_matched_to_w1": all(
            k_by_arm[W2_ARM][sid] == k_by_arm[W1_ARM][sid] for sid in k_by_arm[W1_ARM]
        ),
        "w2_shortfall_sample_ids": sorted(
            sid for sid in k_by_arm[W1_ARM] if k_by_arm[W2_ARM][sid] < k_by_arm[W1_ARM][sid]
        ),
        "w2_donor_breadth": len(donor_ids),
        "w2_donor_entry_total": sum(donor_ids.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    table, document, _harvested = build_binding_full()
    document_hash = canonical_hash(document)
    stats = stats_document(document, document_hash)

    (out_dir / "corrective-binding.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "corrective-binding-stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )

    print(f"consumed A0 attempt: {consumed_attempt_dir()}")
    print(f"binding_config_sha256: {stats['binding_config_sha256']}")
    print(f"binding_hash (tri-derivation): {table.binding_hash}")
    print(f"document_hash: {document_hash}")
    print(f"samples: {stats['n_samples']}")
    print(f"train pool: {json.dumps(stats['train_pool'], sort_keys=True)}")
    print(f"A0 emitted slots total: {stats['emitted_slot_total']}")
    for arm in PCORRF_ARMS:
        block = stats["per_arm"][arm]  # type: ignore[index]
        print(
            f"{arm}: K distribution {json.dumps(block['k_distribution'], sort_keys=True)} "
            f"| total {block['k_total']} mean {block['k_mean']} max {block['k_max']} "
            f"| K=0 samples {block['k_zero_sample_count']}"
        )
    print(f"W2 length-matched to W1 on every sample: {stats['w2_length_matched_to_w1']}")
    print(f"W2 donor breadth: {stats['w2_donor_breadth']} distinct origin samples "
          f"across {stats['w2_donor_entry_total']} entries")
    print(f"wrote {out_dir / 'corrective-binding.json'} and {out_dir / 'corrective-binding-stats.json'}")
    print("BINDING DONE (zero model calls, zero gold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
