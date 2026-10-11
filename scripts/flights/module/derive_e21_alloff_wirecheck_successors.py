#!/usr/bin/env python3
"""Derive the wire-check-only SUCCESSOR cells of the two registered E21 module ALL-OFF cells. Model-free, HELD.

The registered cells ``earnings21-native-stage3-module-alloff-v1`` and ``-smoke-4-v1`` declare
``allowed_execution_stages = [check, worker, campaign]``; ``core.flight.campaign.CampaignCell.assert_mode`` therefore
refuses ``core.flight.cli wire-check`` on them (the A2T siblings declare it). Registered bytes are never edited in
place, so this script writes one SUCCESSOR experiment fragment per cell, following the ``-v2`` / new-identity
precedent for HELD fragments (``e21-dr-shared-two-generation-v2``):

* every field of the parent is copied byte for byte (population, budgets, scorers, ``stage3_measurement``,
  ``consumption_module_declaration``, baseline / dataset / model fragments) EXCEPT the cell, run, attempt and
  experiment identities (suffix ``-wire-v1`` / ``-WIRE-V1``), the readiness reason, the purpose prefix and
  ``allowed_execution_stages``;
* the successor admits ONLY ``[check, wire-check]``. It can never reach ``worker`` or ``campaign``, so it authorises no
  model contact, needs no exposure-ledger row and cannot be flown or flipped ready by a re-pin.

    python -B scripts/flights/module/derive_e21_alloff_wirecheck_successors.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PARENTS = (
    "earnings21-native-stage3-module-alloff-v1",
    "earnings21-native-stage3-module-alloff-smoke-4-v1",
)
STAGES = ["check", "wire-check"]
SUFFIX = "-wire-v1"
RUN_SUFFIX = "-WIRE-V1"
READINESS_REASON = (
    "Wire-check-only successor of {parent} (registered 2026-09-30, unflown, HELD). It exists because the parent "
    "declares allowed_execution_stages [check, worker, campaign] and core.flight.campaign refuses `cli wire-check` on "
    "it; registered bytes are not edited in place. This fragment copies the parent's composed content and admits ONLY "
    "[check, wire-check]: it can never reach worker or campaign, so it authorises no model contact, no fit, no "
    "preparation and no scoring of a real run. Produced by scripts/flights/module/"
    "derive_e21_alloff_wirecheck_successors.py. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def successor_document(parent: str, document: dict) -> dict:
    out = json.loads(json.dumps(document))
    cell = out["cells"][0]
    name = parent + SUFFIX
    run_id = cell["run_id"][: -len("-V1")] + RUN_SUFFIX
    cell.update({
        "cell_id": name, "run_id": run_id, "attempt_id": f"attempt-{name}-generation-v1",
        "allowed_execution_stages": list(STAGES),
    })
    cell["readiness"] = {
        "reason": READINESS_REASON.format(parent=parent), "requirements": [], "state": "held",
    }
    out["experiment_id"] = run_id
    out["purpose"] = f"WIRE-CHECK-ONLY successor of {parent}. " + out["purpose"]
    return out


def render(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    for parent in PARENTS:
        text = io.open(REPO_ROOT / f"configs/experiment/{parent}.json", encoding="utf-8", newline="").read()
        successor = successor_document(parent, json.loads(text))
        name = parent + SUFFIX
        for relpath, payload in (
            (f"configs/experiment/{name}.json", render(successor)),
            (f"configs/campaign/{name}.json", render({
                "cells": [{"cell": name, "experiment": name}], "schema": "saea-campaign-plan-v1"})),
        ):
            io.open(REPO_ROOT / relpath, "w", encoding="utf-8", newline="").write(payload)
            print("wrote", relpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
