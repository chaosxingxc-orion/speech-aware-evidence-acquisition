#!/usr/bin/env python3
"""Prove that the agreement-term change is an EXACT IDENTITY at ``w_agree`` 0.0.

THE OBLIGATION. The 2026-09-26 agreement-term change edits three modules that
every prepared first-phase supply artifact binds by implementation hash
(``core.flight.FlightRuntime._phase_seed_inputs``, key
``sources.implementation``). Every such artifact's FILE hash therefore moves,
for every cell in the repository, whether or not that cell declares an agreement
signal. What must NOT move is the artifact's OUTPUT -- the first-phase selection
the flight consumes and renders -- because a cell that declares no
``agreement_source`` has to fly exactly the bytes it flies today.

HOW IT IS PROVEN RATHER THAN ASSERTED. The A/A replicate cell is the locked plan
with ``w_agree`` 0.0, no ``agreement_source``, and no committed
``prepared_phase_supply`` pin, so its own supply is minted fresh at the CURRENT
implementation. This script compares that artifact's ``output_sha256`` against
the ``output_sha256`` embedded in the SEALED artifact the comparator arm already
flew. That is a stronger comparison than re-running the pre-change code: it binds
the new arithmetic to bytes a real flight consumed.

Equal ``output_sha256`` means the ``{facets, values}`` payload is byte-identical
under ``core.preparation.digest`` (canonical JSON, sorted keys, no NaN) -- so the
seeded value ids, their order, the typed content blocks built from them and the
rendered Perception block are all unchanged. Unequal FILE hashes are EXPECTED and
are printed beside it, so the pair is legible instead of alarming.

The script also reports the TREATMENT cell's output digest when one is named, so
the same receipt shows both halves of the obligation: the default unchanged and
the treatment actually changed.

ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API
contacts: it reads three already-prepared artifacts and hashes them.

Usage:

    python scripts/slurp_agreement_default_identity_proof.py \
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \
        --sealed prepared/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/phase-supply-v1.json \
        --recomputed prepared/SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1/phase-supply-v1.json \
        --treatment prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def file_sha256(path: Path) -> str:
    measured = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def read_artifact(data_root: Path, relpath: str) -> dict:
    path = data_root / relpath
    raw = path.read_bytes()
    document = json.loads(raw)
    values = document["output"]["values"]
    return {
        "relpath": relpath,
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": document["output_sha256"],
        "kind": document["kind"],
        "contact_class": document["contact_class"],
        "rows": sum(len(rows) for rows in values.values()),
        "selected_value_ids": sum(
            len(ids) for rows in values.values() for ids in rows.values()
        ),
        "implementation": document["inputs"]["sources"]["implementation"],
        "supply_spec_declares_agreement_source": (
            "agreement_source" in document["inputs"]["sources"]["supply_spec"]
        ),
        "supply_spec_rank_weights": document["inputs"]["sources"]["supply_spec"][
            "rank_weights"
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--sealed", required=True)
    parser.add_argument("--recomputed", required=True)
    parser.add_argument("--treatment", default=None)
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1

    data_root = Path(args.data_root).resolve()
    sealed = read_artifact(data_root, args.sealed)
    recomputed = read_artifact(data_root, args.recomputed)
    treatment = (
        None if args.treatment is None else read_artifact(data_root, args.treatment)
    )

    report = {
        "schema": "saea-agreement-default-identity-proof-v1",
        "contact_class": "model-free",
        "contacts": {
            "model": 0, "server": 0, "encoder": 0, "embedder": 0,
            "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
        },
        "sealed_comparator": sealed,
        "recomputed_default_at_this_implementation": recomputed,
        "treatment": treatment,
        "verdict": {
            "default_output_identical": sealed["output_sha256"] == recomputed["output_sha256"],
            "default_file_hash_moved_as_expected": (
                sealed["file_sha256"] != recomputed["file_sha256"]
            ),
            "default_implementation_moved": (
                sealed["implementation"] != recomputed["implementation"]
            ),
            "rows_match": sealed["rows"] == recomputed["rows"],
            "selected_value_ids_match": (
                sealed["selected_value_ids"] == recomputed["selected_value_ids"]
            ),
            "treatment_output_differs_from_default": (
                None
                if treatment is None
                else treatment["output_sha256"] != recomputed["output_sha256"]
            ),
        },
        "what_this_does_and_does_not_prove": (
            "PROVES: at w_agree 0.0 and with no agreement_source declared, the "
            "first-phase selection this repository prepares at the changed "
            "implementation is byte-identical to the selection a real flight "
            "already consumed -- same value ids, same order, same canonical bytes, "
            "on every row -- so the rendered Perception block is unchanged. DOES "
            "NOT PROVE: anything about the treatment's effect on any score. The "
            "treatment digest is reported only to show the change is not inert."
        ),
    }
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    ok = report["verdict"]["default_output_identical"] and report["verdict"]["rows_match"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
