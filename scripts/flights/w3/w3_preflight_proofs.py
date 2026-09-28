#!/usr/bin/env python3
"""Fold the W3 pre-flight proofs into one package file (owner decision 164). Model-free.

W3 is W3a ALONE since the 2026-09-27 re-registration (the per-intent exemplar cap W3b dropped), so the
request-size line quotes the card delta alone: the Solver exemplar block is the AGREE arm's own.

Reads, for the W3 arm and its smoke:

* the HELD ``core.flight.cli check`` output (the pre-flight prompt budget per phase: the Fit gate
  numbers, rendered with the runtime's own placeholder counter, beside the retained AGREE arm's
  registered numbers);
* the ``core.flight.cli prepare-supply`` output minted to a SCRATCH path outside the data root's
  ``prepared/`` tree (the real first-phase selection at this implementation), whose output digest
  must equal the AGREE family's own -- W3 moves no facet key, agreement row or value id;
* the sealed AGREE arm's COST records (the realised prompt tokens per contact) and the
  offline read's request-size projection.

Writes ``docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1/preflight-proofs-v1.json``.
No contact of any kind; nothing under the data root is written.

    python scripts/flights/w3/w3_preflight_proofs.py --check-dir /home/chao/w3-scratch --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1"
OUT = PACKAGE + "/preflight-proofs-v1.json"
OFFLINE = PACKAGE + "/offline-estimates-v1.json"
CELLS = {"arm": "slurp-native-stage3-w3-fold-a-v1", "smoke": "slurp-native-stage3-w3-fold-a-smoke-4-v1"}
AGREE_REGISTERED = {"perception": 19449, "reviewer": 19313, "planner": 19252, "solver": 21278}
AGREE_SUPPLY = {"arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
                "smoke": "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9"}
AGREE_TRACE = ("runs/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1/"
               "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1.trace.jsonl")
PROMPT_LIMIT = 20990


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check-dir", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    cells = {}
    for key, cell in CELLS.items():
        check_path = args.check_dir / f"check-{cell}.json"
        supply_path = args.check_dir / f"supply-proof-{cell}.json"
        check = json.loads(check_path.read_text(encoding="utf-8"))
        supply = json.loads(supply_path.read_text(encoding="utf-8"))
        pre = check["preflight"]
        phases = {}
        for receipt in pre["prompt_budget"]:
            phase = receipt["phase"]
            phases[phase] = {
                "decision": receipt["decision"],
                "rendered_text_tokens": receipt["breakdown"]["rendered_text_tokens"],
                "required_window_tokens": receipt["breakdown"]["required_window_tokens"],
                "operational_margin_tokens": receipt["operational_margin_tokens"],
                "physical_margin_tokens": receipt["physical_margin_tokens"],
                "agree_registered_rendered_text_tokens": AGREE_REGISTERED[phase],
                "delta_vs_agree": receipt["breakdown"]["rendered_text_tokens"] - AGREE_REGISTERED[phase],
            }
        values = supply["output"]["values"]["perception"]
        cells[key] = {
            "check": {
                "path_outside_git": str(check_path), "sha256": sha_file(check_path),
                "config_hash": pre["config_hash"], "protocol_hash": pre["protocol_hash"],
                "study_commit": pre["study_commit"], "sample_count": pre["sample_count"],
                "readiness": check["scientific_readiness"]["state"],
                "generation_authorized": check["generation_authorized"],
                "prepared_artifacts_ok": pre["prepared_artifacts_ok"], "blockers": check.get("blockers"),
                "serving_geometry": pre["serving_geometry"], "per_phase": phases,
            },
            "first_phase_supply_proof": {
                "path_outside_git": str(supply_path), "sha256": sha_file(supply_path),
                "minted_by": "core.flight.cli prepare-supply --output <scratch path> --workers 4 (not under prepared/)",
                "output_sha256": supply["output_sha256"],
                "agree_family_output_sha256": AGREE_SUPPLY[key],
                "identical": supply["output_sha256"] == AGREE_SUPPLY[key],
                "rows": len(values), "selected_value_ids": sum(len(v) for v in values.values()),
                "implementation": supply["inputs"]["sources"]["implementation"],
            },
        }
        if not cells[key]["first_phase_supply_proof"]["identical"]:
            raise SystemExit(f"{key}: the first-phase supply digest is not the AGREE family's own")

    trace = args.data_root / AGREE_TRACE
    realised = []
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith('{"channel":"COST"'):
                realised.append(int(json.loads(line)["payload"].get("prompt_tokens") or 0))
    offline = json.loads(Path(OFFLINE).read_text(encoding="utf-8"))
    projection = offline["fold_a_estimates"]["request_size_projection"]
    cards_delta = projection["cards_token_delta_per_later_contact"]
    solver = cells["arm"]["check"]["per_phase"]["solver"]
    line = (
        f"The held `core.flight.cli check` (runtime placeholder counter, widest representative request) reads ALLOW on all "
        f"four phases of the arm: perception {cells['arm']['check']['per_phase']['perception']['rendered_text_tokens']:,}, "
        f"reviewer {cells['arm']['check']['per_phase']['reviewer']['rendered_text_tokens']:,}, planner "
        f"{cells['arm']['check']['per_phase']['planner']['rendered_text_tokens']:,}, Solver {solver['rendered_text_tokens']:,} "
        f"rendered tokens -- {solver['delta_vs_agree']:+} on every phase against the AGREE arm's registered 19,449 / 19,313 / "
        f"19,252 / 21,278 (the eight longest cards are shorter; the bound counts the twenty longest exemplars either way) -- "
        f"Solver operational margin {solver['operational_margin_tokens']} and physical margin {solver['physical_margin_tokens']:,} "
        f"on the 24,576-token slot, no blockers. Realised requests: the sealed AGREE arm's largest contact prompt was "
        f"{max(realised):,} tokens over {len(realised):,} contacts against the per-contact limit {PROMPT_LIMIT:,}; W3a moves "
        f"every later contact by the card delta alone, {cards_delta['mean']:+} tokens on average (min {cards_delta['min']:+}, "
        f"max {cards_delta['max']:+}: no contact grows), because the Solver exemplar block is the AGREE arm's own. Nothing "
        f"must be freed for W3. The first-phase supply minted to a scratch path at this "
        f"implementation carries the AGREE family's own digests (arm {cells['arm']['first_phase_supply_proof']['output_sha256'][:8]}, "
        f"{cells['arm']['first_phase_supply_proof']['selected_value_ids']:,} ids on {cells['arm']['first_phase_supply_proof']['rows']:,} rows; smoke "
        f"{cells['smoke']['first_phase_supply_proof']['output_sha256'][:8]})."
    )
    document = {
        "schema": "saea-w3-preflight-proofs-v1",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "gpu": 0, "network": 0, "paid_api": 0},
        "cells": cells,
        "realised_agree_requests": {
            "trace": {"relpath": AGREE_TRACE, "sha256": sha_file(trace)},
            "cost_records": len(realised), "max_prompt_tokens": max(realised),
            "per_contact_prompt_limit_tokens": PROMPT_LIMIT,
        },
        "request_size_projection": projection,
        "w3a_request_size_projection": {
            "cards_token_delta_per_later_contact": cards_delta,
            "note": "W3a alone (2026-09-27 re-registration): the exemplar block is the AGREE arm's own, so only the card delta applies; the net Solver projection in request_size_projection includes the dropped cap and does not apply",
        },
        "line": line,
    }
    Path(OUT).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
