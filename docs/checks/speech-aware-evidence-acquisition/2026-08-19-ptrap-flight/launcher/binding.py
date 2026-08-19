"""P-TRAP BINDING PHASE -- OFFLINE, ZERO MODEL CALLS.

``configs/probes/g0-binding/ptrap-flight.json``'s own ``phases.binding``:

    analysis.ptrap_read.harvest_a0_wrong_values (consumed P-SLU attempt)
      -> rails.probes.ptrap_flight.build_trap_sets (K-cap, binding-time
         fail-closed gold zero-overlap check, seeded V2 cross-sample draw)

The harvester is the SINGLE registered exception to this session's
never-run-an-analysis-reader-against-real-outputs rule: preregistration
section 2 makes the trap CONTENT itself derived data sourced from the
consumed A0 attempt's own model-generated wrong values, so sourcing it IS
the binding step, not a result read. Nothing here scores, ranks or
interprets a response; this module reaches A0 responses only through
``analysis.ptrap_read.harvest_a0_wrong_values`` (which parses them into
predicted entities and subtracts gold), and the only things it ever prints
are COUNTS.

Two artifacts are written:

  trap-binding.json        the full per-sample SampleTrapSet table (V1/V2
                           entries with their origin sample ids, plus the
                           gold-overlap exclusions the fail-closed check
                           dropped) -- this is the SUPPLY CONTENT the flight
                           renders, and the "trap binding manifest" the
                           exposure row names. Model-generated text; stays
                           under SPEECHRL_DATA_DIR / the scratchpad, never
                           committed.
  trap-binding-stats.json  STRUCTURAL ONLY: per-sample K for V1 and V2, the
                           K distribution, the K=0 exclusion list, and the
                           gold-overlap drop counts. This is the artifact the
                           flight receipt and the docs/checks archive carry.

``binding_hash`` is the sha256 of the canonical trap-binding.json document;
the launcher recomputes the table from the SAME deterministic inputs and
refuses to fly if its own hash disagrees, so the flight can never render a
table other than the one this reviewed binding step produced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.analysis.ptrap_read import (  # noqa: E402
    harvest_a0_wrong_values,
)
from speech_aware_evidence_acquisition.analysis.pslu_read import (  # noqa: E402
    load_gold_by_sample_id,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_sample_manifest,
)
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import (  # noqa: E402
    DEFAULT_TRAP_SEED,
    TRAP_K_CAP,
    SampleTrapSet,
    TrapEntry,
    assert_split_identity_hash,
    build_trap_sets,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/ptrap-flight.json").read_text(encoding="utf-8")
)


def consumed_attempt_dir() -> Path:
    import os

    data_dir = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_dir:
        raise RuntimeError("SPEECHRL_DATA_DIR is unset; cannot resolve the consumed P-SLU attempt")
    attempt_id = str(FLIGHT_CFG["trap_source"]["consumed_pslu_attempt_id"])
    return Path(data_dir.rstrip("/")) / "runs" / "SAEA-PROBE-pslu-n60" / attempt_id


def build_binding() -> tuple[dict[str, SampleTrapSet], dict[str, object]]:
    """Deterministic, pure-given-inputs: returns the trap-set table plus the
    JSON document that gets hashed. Called by BOTH this script and the
    launcher (which cross-checks the hash)."""

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    assert_split_identity_hash(manifest.split_identity_hash)

    gold_by_id = load_gold_by_sample_id(lock, root, manifest.sample_ids)  # RUNTIME_PROHIBITED
    gold_entities_by_sample_id = {
        sample_id: gold_by_id[sample_id].entities for sample_id in manifest.sample_ids
    }

    harvest = harvest_a0_wrong_values(consumed_attempt_dir(), gold_by_id)
    trap_sets = build_trap_sets(
        wrong_values_by_sample=harvest.wrong_values_by_sample,
        gold_entities_by_sample_id=gold_entities_by_sample_id,
        sample_ids=manifest.sample_ids,
        k_cap=TRAP_K_CAP,
        seed=DEFAULT_TRAP_SEED,
    )

    document = {
        "schema": "saea-ptrap-trap-binding-v1",
        "run_id": "SAEA-PROBE-ptrap-120",
        "preregistration": FLIGHT_CFG["preregistration"],
        "split_identity_hash": manifest.split_identity_hash,
        "consumed_pslu_attempt_id": FLIGHT_CFG["trap_source"]["consumed_pslu_attempt_id"],
        "consumed_pslu_arm": FLIGHT_CFG["trap_source"]["consumed_pslu_arm"],
        "trap_k_cap": TRAP_K_CAP,
        "trap_donor_seed": DEFAULT_TRAP_SEED,
        "harvest": {
            "total_wrong_value_count": harvest.total_wrong_value_count,
            "samples_with_zero_wrong_values": list(harvest.samples_with_zero_wrong_values),
            "per_sample_wrong_value_counts": dict(sorted(harvest.per_sample_wrong_value_counts.items())),
        },
        "trap_sets": {
            sample_id: {
                "v1_entries": [entry.as_json() for entry in ts.v1_entries],
                "v2_entries": [entry.as_json() for entry in ts.v2_entries],
                "v1_excluded_gold_overlap": [entry.as_json() for entry in ts.v1_excluded_gold_overlap],
                "v2_excluded_gold_overlap": [entry.as_json() for entry in ts.v2_excluded_gold_overlap],
                "own_pool_size": ts.own_pool_size,
            }
            for sample_id, ts in sorted(trap_sets.items())
        },
    }
    return trap_sets, document


def canonical_hash(document: dict[str, object]) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def trap_sets_from_document(document: dict) -> dict[str, SampleTrapSet]:
    out: dict[str, SampleTrapSet] = {}
    for sample_id, block in document["trap_sets"].items():
        out[sample_id] = SampleTrapSet(
            sample_id=sample_id,
            v1_entries=tuple(TrapEntry.from_json(e) for e in block["v1_entries"]),
            v2_entries=tuple(TrapEntry.from_json(e) for e in block["v2_entries"]),
            v1_excluded_gold_overlap=tuple(
                TrapEntry.from_json(e) for e in block["v1_excluded_gold_overlap"]
            ),
            v2_excluded_gold_overlap=tuple(
                TrapEntry.from_json(e) for e in block["v2_excluded_gold_overlap"]
            ),
            own_pool_size=int(block["own_pool_size"]),
        )
    return out


def stats_document(document: dict[str, object], binding_hash: str) -> dict[str, object]:
    trap_sets = document["trap_sets"]  # type: ignore[index]
    v1_k = {sid: len(block["v1_entries"]) for sid, block in trap_sets.items()}
    v2_k = {sid: len(block["v2_entries"]) for sid, block in trap_sets.items()}
    v1_excl = {sid: len(block["v1_excluded_gold_overlap"]) for sid, block in trap_sets.items()}
    v2_excl = {sid: len(block["v2_excluded_gold_overlap"]) for sid, block in trap_sets.items()}
    harvest = document["harvest"]  # type: ignore[index]
    return {
        "schema": "saea-ptrap-trap-binding-stats-v1",
        "binding_hash": binding_hash,
        "run_id": document["run_id"],
        "split_identity_hash": document["split_identity_hash"],
        "consumed_pslu_attempt_id": document["consumed_pslu_attempt_id"],
        "consumed_pslu_arm": document["consumed_pslu_arm"],
        "trap_k_cap": document["trap_k_cap"],
        "trap_donor_seed": document["trap_donor_seed"],
        "n_samples": len(trap_sets),
        "harvest_total_wrong_value_count": harvest["total_wrong_value_count"],
        "harvest_samples_with_zero_wrong_values": harvest["samples_with_zero_wrong_values"],
        "harvest_zero_wrong_value_sample_count": len(harvest["samples_with_zero_wrong_values"]),
        "v1_k_distribution": dict(sorted(Counter(v1_k.values()).items())),
        "v2_k_distribution": dict(sorted(Counter(v2_k.values()).items())),
        "v1_k_zero_sample_ids": sorted(sid for sid, k in v1_k.items() if k == 0),
        "v1_k_total": sum(v1_k.values()),
        "v2_k_total": sum(v2_k.values()),
        "v1_k_by_sample": dict(sorted(v1_k.items())),
        "v2_k_by_sample": dict(sorted(v2_k.items())),
        "v2_shorter_than_v1_sample_ids": sorted(sid for sid in v1_k if v2_k[sid] < v1_k[sid]),
        "v1_gold_overlap_exclusions_total": sum(v1_excl.values()),
        "v2_gold_overlap_exclusions_total": sum(v2_excl.values()),
        "v1_gold_overlap_exclusion_sample_ids": sorted(sid for sid, c in v1_excl.items() if c),
        "v2_gold_overlap_exclusion_sample_ids": sorted(sid for sid, c in v2_excl.items() if c),
        "common_denominator_n": sum(1 for k in v1_k.values() if k >= 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _trap_sets, document = build_binding()
    binding_hash = canonical_hash(document)
    stats = stats_document(document, binding_hash)

    (out_dir / "trap-binding.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "trap-binding-stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )

    print(f"consumed A0 attempt: {consumed_attempt_dir()}")
    print(f"binding_hash: {binding_hash}")
    print(f"samples: {stats['n_samples']}")
    print(f"harvest total wrong values: {stats['harvest_total_wrong_value_count']}")
    print(f"harvest samples with ZERO wrong values: {stats['harvest_zero_wrong_value_sample_count']}")
    print(f"V1 K distribution (K -> n samples): {json.dumps(stats['v1_k_distribution'], sort_keys=True)}")
    print(f"V2 K distribution (K -> n samples): {json.dumps(stats['v2_k_distribution'], sort_keys=True)}")
    print(
        "V1 K=0 sample count (EXCLUDED from the capture denominator): "
        f"{len(stats['v1_k_zero_sample_ids'])}"
    )
    print(f"V1 total appended entries: {stats['v1_k_total']}")
    print(f"V2 total appended entries: {stats['v2_k_total']}")
    print(
        f"V2 shorter than V1 (donor pool ran dry) on "
        f"{len(stats['v2_shorter_than_v1_sample_ids'])} sample(s)"
    )
    print(
        f"gold zero-overlap exclusions: V1 {stats['v1_gold_overlap_exclusions_total']}, "
        f"V2 {stats['v2_gold_overlap_exclusions_total']}"
    )
    print(f"common denominator (V1 K>=1): {stats['common_denominator_n']}")
    print(f"wrote {out_dir / 'trap-binding.json'} and {out_dir / 'trap-binding-stats.json'}")
    print("BINDING DONE (zero model calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
