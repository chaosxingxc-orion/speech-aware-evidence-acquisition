#!/usr/bin/env python3
"""CLI: MF-1, the Audio2Tool query-cue audit (model-free, zero contacts).

Authority ``docs/readiness/2026-09-05-a2t-query-cue-audit-v1-preregistration.md``;
exposure row ``SAEA-A2T-MF-QUERY-CUE-AUDIT-V1``, registered before the first read.

I/O ONLY: every measurement and every receipt field lives in
``analysis.a2t_query_cue_audit``. This script arms the offline guard, loads the
construction-legal Audio2Tool pool and the pinned registry, hands them to
``build_receipts``, prints the headline and writes the receipt directory with its
``MANIFEST.sha256``. No model, tokenizer, embedder, network, GPU or audio contact.

Usage (WSL2)::

    python scripts/run_a2t_query_cue_audit.py            # print only
    python scripts/run_a2t_query_cue_audit.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_query_cue_audit import (  # noqa: E402
    build_receipts,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_identity_report,
    exposed_sample_ids,
    load_tool_registry_by_name,
    propose_partition,
)

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-query-cue-audit"
)


def write_manifest(directory: Path) -> None:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = Path(data_root())
    registry = load_tool_registry_by_name(lock, root)
    pool, inventory = a2t_pool_rows(lock, root)
    exposure = exposed_identity_report(REPO_ROOT)
    exposed = exposed_sample_ids(REPO_ROOT)
    partition = propose_partition(pool, exposed)

    summary, table, decontamination = build_receipts(
        lock=lock,
        root=root,
        registry=registry,
        pool=pool,
        inventory=inventory,
        exposure=exposure,
        exposed=exposed,
        partition=partition,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )

    print(json.dumps(summary["kc_a1_gate"], indent=1))
    print(json.dumps(summary["primary_population"]["decision_counts"], indent=1))
    print(json.dumps(summary["primary_population"]["mass_by_decision"], indent=1))
    print(json.dumps(summary["primary_population"]["targets"]["targets"], indent=1))
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", summary)
    write_json_artifact(OUT_DIR / "per-pair-table.json", table)
    write_json_artifact(OUT_DIR / "decontamination.json", decontamination)
    write_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
