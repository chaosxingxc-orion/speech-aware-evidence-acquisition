#!/usr/bin/env python3
"""CLI: close ``A_0`` for EVO-S1 (MODEL-FREE, TRAIN-ONLY).

Preregistration section 16 open point 1: "the loop's round 0 must start from
the exact bytes KC-S1b flew", and that had never been re-derived against the
current tree. This script re-mines the per-intent slot schema from
``train.jsonl``, reproduces the committed receipt's own hashes, and does the
same for the UNFLOORED table -- which is the authority for every count, every
share and every intent's line cap, is what a candidate is validated against,
and which nothing pinned until now.

It also proves the third thing round 1 needs and which no other receipt
states: that the exemplar roster's rows resolve through the
construction-role reader with their GOLD ENTITIES attached, because a
proposer contact that cannot show gold has nothing to propose from.

Nothing here contacts a model, a tool, an embedder or the network, and no
devel or test file is reachable: ``load_slurp_intent_slot_schema`` and
``load_slurp_train_construction_rows`` have no ``split`` parameter.

Run in WSL2::

    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/verify_slurp_evo_a0.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_intent_slot_schema,
    load_slurp_train_construction_rows,
    render_slurp_intent_slot_schema,
)
from speech_aware_evidence_acquisition.rails.evolution import LoopConfig  # noqa: E402
from speech_aware_evidence_acquisition.rails.evolution_carrier import (  # noqa: E402
    read_roster_document,
)

LOOP_CONFIG_RELPATH = "configs/knowledge/slurp-evo-s1/loop-v1.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-a0-closure"
)
PREREGISTRATION = (
    "docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md"
)

#: What KC-S1b flew, as published in preregistration section 3. Hard-coded so
#: this script RAISES rather than reports if the corpus stops reproducing it:
#: a mismatch is the cell stopping, not a number to write down.
PUBLISHED = {
    "receipt_sha256": "7e04da0ec29d0e9d6c473697d2b84bd1e0fc1d9ba28880ef2cf8b6f908bbe782",
    "content_hash": "732e500af3870216c7b311369f6f190ffdb0365e497d84cf211f478036757dcc",
    "source_identity_hash": (
        "545847bb95a9423005c71bdcc3fa74af55a3a1b6ae91409ba4070fd35bf92fef"
    ),
    "utterance_count": 11514,
    "intents": 60,
    "type_rows": 261,
    "distinct_types": 52,
    "fillers": 1008,
    "full_rendering_sha256": (
        "4e573a65e14c57598cc39ed1aa71cf0ac59018be162dbea3e0bfbf038203a5b9"
    ),
    "full_rendering_characters": 26720,
    "full_rendering_lines": 322,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _shape(schema) -> dict[str, int]:
    type_rows = sum(len(schema.intents[i].types) for i in schema.intent_ids)
    distinct = {
        entity_type
        for intent in schema.intent_ids
        for entity_type, _count, _share in schema.intents[intent].types
    }
    fillers = sum(
        len(schema.intents[intent].fillers.get(entity_type, ()))
        for intent in schema.intent_ids
        for entity_type, _count, _share in schema.intents[intent].types
    )
    return {
        "intents": len(schema.intent_ids),
        "type_rows": type_rows,
        "distinct_types": len(distinct),
        "fillers": fillers,
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"A_0 CLOSURE FAILED: {message}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    receipt_path = REPO_ROOT / RECEIPT_RELPATH
    receipt_sha = _sha256_file(receipt_path)
    _assert(
        receipt_sha == PUBLISHED["receipt_sha256"],
        f"the committed A_0 receipt hashes to {receipt_sha}, not the published "
        f"{PUBLISHED['receipt_sha256']}",
    )

    floored = load_slurp_intent_slot_schema(lock, root)
    unfloored = load_slurp_intent_slot_schema(lock, root, min_share=0.0)
    rendered = render_slurp_intent_slot_schema(floored)

    floored_shape = _shape(floored)
    unfloored_shape = _shape(unfloored)
    measured = {
        "receipt_sha256": receipt_sha,
        "content_hash": floored.content_hash(),
        "source_identity_hash": floored.source_identity_hash,
        "utterance_count": floored.utterance_count,
        **floored_shape,
        "full_rendering_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "full_rendering_characters": len(rendered),
        "full_rendering_lines": len(rendered.splitlines()),
    }
    disagreements = sorted(
        key for key, value in PUBLISHED.items() if measured[key] != value
    )
    _assert(
        not disagreements,
        "re-mining TRAIN does not reproduce what KC-S1b flew; "
        + ", ".join(f"{key}: {measured[key]!r} != {PUBLISHED[key]!r}" for key in disagreements),
    )

    # The unfloored table has never been pinned anywhere, and it is what every
    # candidate's counts, shares and line cap are re-derived from.
    unfloored_hash = unfloored.content_hash()
    _assert(
        unfloored.source_identity_hash == floored.source_identity_hash,
        "the floored and unfloored minings read different TRAIN corpora",
    )
    _assert(
        unfloored_shape["type_rows"] >= floored_shape["type_rows"],
        "the unfloored table lists fewer type rows than the floored one",
    )

    # The exemplar roster's gold, through the construction-role reader.
    config = LoopConfig.from_json(
        json.loads((REPO_ROOT / LOOP_CONFIG_RELPATH).read_text(encoding="utf-8"))
    )
    roster = read_roster_document(REPO_ROOT, config.exemplar_roster_relpath)
    _assert(
        str(roster.get("roster_role")) == "construction",
        f"the exemplar roster's roster_role is {roster.get('roster_role')!r}, not "
        "'construction'; only a construction roster's gold may reach a proposer",
    )
    sample_ids = [str(item["sample_id"]) for item in roster["items"]]
    rows = load_slurp_train_construction_rows(lock, root, sample_ids)
    _assert(len(rows) == len(sample_ids), "the construction reader dropped rows")
    with_gold = sum(1 for row in rows.values() if row["entities"])
    per_scenario: dict[str, int] = {}
    for item in roster["items"]:
        per_scenario[str(item["stratum"])] = per_scenario.get(str(item["stratum"]), 0) + 1
    _assert(
        with_gold == len(rows),
        f"{len(rows) - with_gold} exemplar row(s) carry no gold entity; the pool is "
        "supposed to be entity-bearing by construction",
    )
    _assert(
        set(per_scenario) == set(config.targets),
        "the exemplar roster's strata are not exactly the loop's eighteen targets",
    )
    thin = sorted(
        name
        for name, count in per_scenario.items()
        if count < 2 * config.exemplars_per_tool
    )
    _assert(
        not thin,
        f"scenario(s) {thin} have fewer than 2 x M exemplars; the three per-round draws "
        "could not differ in membership",
    )

    closure = {
        "schema": "saea-slurp-evo-a0-closure-v1",
        "generated_by": "scripts/verify_slurp_evo_a0.py",
        "preregistration": PREREGISTRATION,
        "verdict": "CLOSED",
        "a_0": {
            "receipt": RECEIPT_RELPATH,
            "receipt_sha256": receipt_sha,
            "content_hash": measured["content_hash"],
            "source_identity_hash": measured["source_identity_hash"],
            "utterance_count": measured["utterance_count"],
            "shape": floored_shape,
            "full_rendering": {
                "sha256": measured["full_rendering_sha256"],
                "characters": measured["full_rendering_characters"],
                "lines": measured["full_rendering_lines"],
            },
            "reproduces_kc_s1b": True,
        },
        "unfloored": {
            "min_share": 0.0,
            "content_hash": unfloored_hash,
            "source_identity_hash": unfloored.source_identity_hash,
            "shape": unfloored_shape,
            "role": (
                "the only authority for a type's TRAIN count, its share and its "
                "intent's line cap (1 + L). A candidate never writes a number: the "
                "renderer re-derives every header and every share from this table, so "
                "pinning it is pinning what a candidate CANNOT change."
            ),
        },
        "exemplar_roster": {
            "relpath": config.exemplar_roster_relpath,
            "roster_id": roster.get("roster_id"),
            "roster_role": roster.get("roster_role"),
            "split_identity_hash": roster.get("split_identity_hash"),
            "rows": len(rows),
            "rows_with_gold_entities": with_gold,
            "per_scenario": dict(sorted(per_scenario.items())),
            "exemplars_per_scenario_M": config.exemplars_per_tool,
            "gate": (
                "read through rails.evolution_carrier.read_roster_document (which "
                "verifies the receipt fail-closed) and data.slurp"
                ".load_slurp_train_construction_rows, the TRAIN-locked reader that is "
                "the one caller licensed to carry sentence text beside gold"
            ),
        },
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "paid_api_spend": 0,
        },
    }
    print(json.dumps(closure, indent=2, sort_keys=True))
    if not args.write:
        return 0
    check_dir = REPO_ROOT / CHECK_DIR
    check_dir.mkdir(parents=True, exist_ok=True)
    (check_dir / "a0-closure.json").write_text(
        json.dumps(closure, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {CHECK_DIR}/a0-closure.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
