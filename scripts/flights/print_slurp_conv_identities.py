#!/usr/bin/env python3
"""Print the composed-config and protocol hashes of cell CONV.

Config alone: no adapter, no split load, no lock, no contact. Used to fill the
registration package's plan documents BEFORE the exposure rows exist -- the gate
refuses ``core.flight.cli check`` until a run has a pre-registered row, so the
hashes cannot come from ``check`` at registration time. The coordinator's
``repin_cell.py`` recomputes and rewrites all of them at the flip, and its own
``check`` then refuses unless they agree.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

CELLS = ("slurp-native-stage3-conv-fold-a-70-v1",)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    out = {}
    for experiment in CELLS:
        document = json.loads(
            (repo / "configs" / "experiment" / f"{experiment}.json").read_text(
                encoding="utf-8"
            )
        )
        cell = document["cells"][0]
        composed = compose(
            repo,
            cell["model_fragment"],
            cell["dataset_fragment"],
            cell["baseline_fragment"],
            experiment,
        )
        split = document["population"]["split_identity_hash"]
        perception = composed.values["knowledge_stores"]["intent-boundaries"][
            "phase_supply"
        ]["perception"]
        out[experiment] = {
            "run_id": cell["run_id"],
            "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"],
            "rows": document["population"]["count"],
            "split_identity_hash": split,
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(
                composed.config_hash, composed.values["arm"], split
            ),
            "fit": composed.values["native_contact_fit"],
            "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"],
            "boundary_rank_weights": perception["rank_weights"],
            "boundary_k": perception["k"],
            "boundary_fuse_coverage": perception["fuse_coverage"],
            "agreement_source": perception.get("agreement_source", {}),
            "declares_prepared_phase_supply": "prepared_phase_supply"
            in composed.values,
            "policy": composed.values["policy"],
            "scorers": composed.values["scorers"],
            "service_session": document["service_session"],
            "native_episode_policies": {
                key: composed.values["native_episode"].get(key)
                for key in (
                    "finite_completion_policy",
                    "react_exhaustion_policy",
                )
            },
        }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
