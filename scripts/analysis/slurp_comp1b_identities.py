#!/usr/bin/env python3
"""Print cell COMP-1b's identities (composed config hash, protocol hash, split
identity hash) for the registration package. Config only: no contact.

    python scripts/analysis/slurp_comp1b_identities.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402


def composed_of(experiment: str):
    document = json.loads((REPO_ROOT / f"configs/experiment/{experiment}.json").read_text(encoding="utf-8"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def identity(experiment: str) -> dict:
    document, cell, composed = composed_of(experiment)
    split = document["population"]["split_identity_hash"]
    fit = composed.values["native_contact_fit"]
    return {
        "cell": cell["cell_id"],
        "experiment": experiment,
        "run_id": cell["run_id"],
        "attempt_id": cell["attempt_id"],
        "fit_run_id": fit["run_id"],
        "fit_attempt_id": fit["attempt_id"],
        "fit_contact_cap": fit["contact_cap"],
        "baseline_fragment": cell["baseline_fragment"],
        "dataset_fragment": cell["dataset_fragment"],
        "model_fragment": cell["model_fragment"],
        "rows": document["population"]["count"],
        "split_identity_hash": split,
        "composed_config_hash": composed.config_hash,
        "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
        "family_budget": document["family_budget"],
        "readiness_state": cell["readiness"]["state"],
        "policy": composed.values["policy"],
        "solver_material": composed.values["phase_material"]["solver"],
        "deliver_normaliser": composed.values["native_episode"]["deliver_normaliser"],
        "boundary": {k: composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"].get(k) for k in ("k", "tau", "rank_weights", "fuse_coverage")},
        "boundary_facet_source_sha256": composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["facet_source"]["sha256"],
        "declares_agreement_source": "agreement_source" in composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"],
    }


def main() -> int:
    out = {
        "arm": identity("slurp-native-stage3-comp1b-fold-a-v1"),
        "smoke": identity("slurp-native-stage3-comp1b-fold-a-smoke-4-v1"),
        "comp1_arm_for_reference": identity("slurp-native-stage3-comp1-fold-a-v1"),
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
