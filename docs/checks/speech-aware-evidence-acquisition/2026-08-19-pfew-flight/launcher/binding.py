"""P-FEW BINDING PHASE -- OFFLINE, ZERO MODEL CALLS.

``docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md`` section 2
("demo assignments fixed per sample at binding, hash-pinned") and section 5
("demo content TRAIN-split only (binding-time fail-closed check: no demo
recording id in devel; no devel gold anywhere in any prompt)") made executable:

    rails.probes.pfew_flight.load_train_demo_pool   (raw governed train.jsonl,
                                                     text-only, no audio opened)
      -> rails.probes.pfew_flight.build_demo_binding (global seeded skew label
         chosen BEFORE any gold read; FS-BAL K=4 distinct-label draws; the
         binding-time fail-closed devel-exclusion + canonical-label checks)

This is REGISTERED SUPPLY SOURCING, not a result read: nothing here opens a
model session, scores a response, or touches devel gold. The only devel-side
values it consults are the frozen manifest's own sample ids and utterance ids
(needed for the fail-closed "no demo recording id in devel" scan); the
FS-SKEW label is drawn from the 18 canonical roster labels by a seeded RNG
with no gold input whatsoever (``build_demo_binding``'s own docstring gives
the full legal resolution of the registration's "wrong-for-most-samples"
wording).

Two artifacts are written:

  demo-binding.json        the full per-sample demo assignment table (the
                           SUPPLY CONTENT the flight renders) plus the
                           machinery's OWN ``DemoBinding.sha256`` pin. TRAIN
                           transcript text; stays under the scratchpad / the
                           attempt directory, never committed.
  demo-binding-stats.json  STRUCTURAL ONLY: label-balance distribution, the
                           skew label, per-arm demo counts, distinct TRAIN
                           donor breadth, pool coverage and the devel-overlap
                           scan result. This is the artifact the flight
                           receipt and the docs/checks archive carry.

The pin is ``DemoBinding.sha256`` -- computed by the committed machinery
(``rails.probes.pfew_flight.compute_demo_binding_sha256`` over
``_demo_binding_document``), never by a second hash formula in this launcher.
The launcher re-derives the table from the SAME deterministic inputs and
refuses to fly unless its own ``DemoBinding.sha256`` equals the value recorded
here, so the flight can never render a demo table other than the one this
reviewed binding step produced.

``_demo_binding_document`` is imported privately and deliberately: it is the
EXACT structure the machinery hashes, so serializing anything else here would
let the on-disk artifact drift from what the pin actually covers. (Private
cross-module reuse inside this probe family is already precedented --
``rails.probes.pfew_flight.load_train_demo_pool`` itself reads
``data.slurp._governed_roots``/``_read_jsonl``.)
"""

from __future__ import annotations

import argparse
import json
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
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import (  # noqa: E402
    DEFAULT_DEMO_SEED,
    FS_BAL_K,
    FS_SKEW_K,
    TRAIN_SAMPLE_ID_PREFIX,
    DemoBinding,
    _demo_binding_document,
    assert_split_identity_hash,
    build_demo_binding,
    load_train_demo_pool,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (  # noqa: E402
    canonical_scenario_labels,
)

from flight_identity import (  # noqa: E402
    PREREGISTRATION_RELPATH,
    ROSTER_TABLE_RELPATH,
    RUN_ID,
    SAMPLE_MANIFEST_RELPATH,
)

BINDING_SCHEMA = "saea-pfew-demo-binding-v1"
BINDING_STATS_SCHEMA = "saea-pfew-demo-binding-stats-v1"


def build_binding(adapter: SlurpAdapter | None = None) -> tuple[DemoBinding, dict[str, object]]:
    """Deterministic, pure-given-inputs: returns the machinery's own
    :class:`DemoBinding` plus the JSON document written to disk. Called by
    BOTH this script and the launcher (which cross-checks ``sha256``).

    ``adapter`` is injectable purely so a caller that has ALREADY paid for the
    (slow, media-sha256-hashing) devel split load can hand its own adapter in
    rather than paying twice."""

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    assert_split_identity_hash(manifest.split_identity_hash)

    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    canonical = canonical_scenario_labels(rosters)

    slurp = adapter if adapter is not None else SlurpAdapter(lock, root, repo_root=REPO)
    samples = select_pslu_samples(slurp.load_split("devel"), manifest)

    demo_pool = load_train_demo_pool(lock, root)
    binding = build_demo_binding(
        demo_pool=demo_pool,
        canonical_labels=canonical,
        target_samples=samples,
        seed=DEFAULT_DEMO_SEED,
    )

    inner = _demo_binding_document(
        skew_label=binding.skew_label,
        canonical_labels=binding.canonical_labels,
        per_sample=binding.per_sample,
    )
    document = {
        "schema": BINDING_SCHEMA,
        "run_id": RUN_ID,
        "preregistration": PREREGISTRATION_RELPATH,
        "split_identity_hash": manifest.split_identity_hash,
        "sample_manifest": SAMPLE_MANIFEST_RELPATH,
        "roster_table": ROSTER_TABLE_RELPATH,
        "demo_seed": DEFAULT_DEMO_SEED,
        "fs_bal_k": FS_BAL_K,
        "fs_skew_k": FS_SKEW_K,
        # The machinery's OWN pin over the hashed structure below -- never a
        # second hash formula authored in this launcher (module docstring).
        "demo_binding_sha256": binding.sha256,
        "hashed_document": inner,
        "train_demo_pool_label_coverage": {
            label: len(demo_pool.get(label, ())) for label in sorted(canonical)
        },
    }
    return binding, document


def stats_document(binding: DemoBinding, document: dict[str, object]) -> dict[str, object]:
    """STRUCTURAL ONLY (module docstring): counts, distributions, ids. Carries
    no transcript text, so this is the artifact the docs/checks archive gets."""

    per_sample = binding.per_sample
    bal_label_counts: Counter = Counter()
    bal_donor_ids: set[str] = set()
    skew_donor_ids: set[str] = set()
    bal_k_counts: Counter = Counter()
    skew_k_counts: Counter = Counter()
    bal_distinct_label_counts: Counter = Counter()
    for demo_set in per_sample.values():
        bal_k_counts[len(demo_set.fs_bal_demos)] += 1
        skew_k_counts[len(demo_set.fs_skew_demos)] += 1
        bal_distinct_label_counts[len({d.scenario_label for d in demo_set.fs_bal_demos})] += 1
        for demo in demo_set.fs_bal_demos:
            bal_label_counts[demo.scenario_label] += 1
            bal_donor_ids.add(demo.train_sample_id)
        for demo in demo_set.fs_skew_demos:
            skew_donor_ids.add(demo.train_sample_id)

    coverage = document["train_demo_pool_label_coverage"]  # type: ignore[index]
    return {
        "schema": BINDING_STATS_SCHEMA,
        "run_id": RUN_ID,
        "demo_binding_sha256": binding.sha256,
        "split_identity_hash": document["split_identity_hash"],
        "demo_seed": DEFAULT_DEMO_SEED,
        "fs_bal_k": FS_BAL_K,
        "fs_skew_k": FS_SKEW_K,
        "n_samples": len(per_sample),
        "skew_label": binding.skew_label,
        "canonical_label_count": len(binding.canonical_labels),
        "canonical_labels": list(binding.canonical_labels),
        "fs_bal_k_distribution": dict(sorted(bal_k_counts.items())),
        "fs_skew_k_distribution": dict(sorted(skew_k_counts.items())),
        "fs_bal_distinct_label_count_distribution": dict(sorted(bal_distinct_label_counts.items())),
        "fs_bal_label_usage": dict(sorted(bal_label_counts.items())),
        "fs_bal_distinct_train_donors": len(bal_donor_ids),
        "fs_skew_distinct_train_donors": len(skew_donor_ids),
        "fs_bal_demo_total": sum(len(d.fs_bal_demos) for d in per_sample.values()),
        "fs_skew_demo_total": sum(len(d.fs_skew_demos) for d in per_sample.values()),
        "train_demo_pool_label_coverage": coverage,
        "train_demo_pool_labels_with_candidates": sum(1 for n in coverage.values() if n),  # type: ignore[union-attr]
        "all_demo_ids_are_train_namespaced": all(
            demo.train_sample_id.startswith(TRAIN_SAMPLE_ID_PREFIX)
            for demo_set in per_sample.values()
            for demo in tuple(demo_set.fs_bal_demos) + tuple(demo_set.fs_skew_demos)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    binding, document = build_binding()
    stats = stats_document(binding, document)

    (out_dir / "demo-binding.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    (out_dir / "demo-binding-stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )

    print(f"demo_binding_sha256: {binding.sha256}")
    print(f"samples: {stats['n_samples']}")
    print(f"canonical labels: {stats['canonical_label_count']}")
    print(f"seeded GLOBAL skew label (chosen with zero gold input): {binding.skew_label!r}")
    print(f"FS-BAL K distribution: {json.dumps(stats['fs_bal_k_distribution'], sort_keys=True)}")
    print(f"FS-SKEW K distribution: {json.dumps(stats['fs_skew_k_distribution'], sort_keys=True)}")
    print(
        "FS-BAL distinct-label-per-sample distribution: "
        f"{json.dumps(stats['fs_bal_distinct_label_count_distribution'], sort_keys=True)}"
    )
    print(f"FS-BAL label usage: {json.dumps(stats['fs_bal_label_usage'], sort_keys=True)}")
    print(f"FS-BAL distinct TRAIN donors: {stats['fs_bal_distinct_train_donors']}")
    print(f"FS-SKEW distinct TRAIN donors: {stats['fs_skew_distinct_train_donors']}")
    print(f"FS-BAL demos total: {stats['fs_bal_demo_total']}; FS-SKEW demos total: {stats['fs_skew_demo_total']}")
    print(
        "TRAIN pool coverage (label -> candidates): "
        f"{json.dumps(stats['train_demo_pool_label_coverage'], sort_keys=True)}"
    )
    print(f"every demo id TRAIN-namespaced: {stats['all_demo_ids_are_train_namespaced']}")
    print(
        "binding-time fail-closed checks (canonical-label legality, TRAIN namespace, "
        "no demo slurp_id shared with a target devel utterance) PASSED inside build_demo_binding"
    )
    print(f"wrote {out_dir / 'demo-binding.json'} and {out_dir / 'demo-binding-stats.json'}")
    print("BINDING DONE (zero model calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
