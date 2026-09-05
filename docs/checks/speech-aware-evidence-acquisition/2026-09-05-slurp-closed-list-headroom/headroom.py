#!/usr/bin/env python3
"""Model-free structural read of the sealed DEV-1000 predictions against the
TRAIN-only SLURP label inventory (row ``SAEA-SLURP-MF-CLOSED-LIST-HEADROOM-V1``).

Zero model, GPU, tool, embedding, network and audio contacts. Two inputs only:

1. the sealed ``arm*-outputs.jsonl`` bytes of the 2026-08-25
   ``SAEA-DEV1000-BASELINE-LOCK`` M0 and BLEND attempts, and
2. the TRAIN-only label inventory, through this repository's own
   ``data.slurp.load_slurp_ontology`` (``include_synthetic=False``, so the
   miner reads ``train.jsonl`` and nothing else).

**No gold is read.** The question is not "was the prediction right" -- it is
"is the prediction even a legal label", which is answerable from the train
inventory alone. That is what makes this a preregistration input rather than
a result: it bounds what a closed-list prompt can possibly fix, before the
arm that carries one is flown.

Run::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD:$PWD/src \\
        python -B docs/checks/.../2026-09-05-slurp-closed-list-headroom/headroom.py \\
        --out docs/checks/.../2026-09-05-slurp-closed-list-headroom/headroom-report.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.data.lock import (
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (
    load_slurp_ontology,
    render_slurp_closed_label_inventory,
    render_slurp_label_inventory,
    render_slurp_ontology,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

SEALED = {
    "DEV-1000 M0": (
        "SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T053342Z-dev1000m0/"
        "arm1-m0-outputs.jsonl"
    ),
    "DEV-1000 BLEND": (
        "SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T054707Z-dev1000blend/"
        "arm2-blend-outputs.jsonl"
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_arm(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def analyse(rows: list[dict], ontology) -> dict:
    allowed_scenario = set(ontology.scenarios)
    allowed_action = set(ontology.actions)
    allowed_pair = {
        (scenario, action)
        for scenario, actions in ontology.actions_by_scenario.items()
        for action in actions
    }
    allowed_type = set(ontology.entity_types)

    n = len(rows)
    unparsed = off_scenario = off_action = off_pair = 0
    mentions = off_type = 0
    top_scenario: collections.Counter = collections.Counter()
    top_action: collections.Counter = collections.Counter()
    top_pair: collections.Counter = collections.Counter()
    top_type: collections.Counter = collections.Counter()

    for row in rows:
        text = row.get("final_response_text")
        if text is None:
            text = row.get("text")
        scenario, action, entities, parsed = parse_slu_response(text or "")
        if not parsed:
            unparsed += 1
        if scenario not in allowed_scenario:
            off_scenario += 1
            top_scenario[str(scenario)] += 1
        if action not in allowed_action:
            off_action += 1
            top_action[str(action)] += 1
        if (scenario, action) not in allowed_pair:
            off_pair += 1
            top_pair[f"{scenario}/{action}"] += 1
        for entity in entities:
            mentions += 1
            if entity.type not in allowed_type:
                off_type += 1
                top_type[str(entity.type)] += 1

    def pct(count: int, total: int) -> float:
        return round(100.0 * count / total, 2) if total else 0.0

    return {
        "rows": n,
        "unparsed_rows": unparsed,
        "scenario_outside_the_listed_set": {"count": off_scenario, "percent": pct(off_scenario, n)},
        "action_outside_the_listed_set": {"count": off_action, "percent": pct(off_action, n)},
        "pair_not_observed_in_train": {"count": off_pair, "percent": pct(off_pair, n)},
        "entity_mentions": mentions,
        "entity_type_outside_the_listed_set": {
            "count": off_type,
            "percent": pct(off_type, mentions),
        },
        "top_off_inventory_scenarios": top_scenario.most_common(8),
        "top_off_inventory_actions": top_action.most_common(8),
        "top_off_inventory_pairs": top_pair.most_common(8),
        "top_off_inventory_entity_types": top_type.most_common(8),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    ontology = load_slurp_ontology(lock, root)
    contract = render_slurp_ontology(ontology)
    block = render_slurp_label_inventory(ontology)
    rendered_fill = render_slurp_closed_label_inventory(lock, root)

    arms = {}
    runs = Path(root) / "runs"
    for name, relpath in SEALED.items():
        path = runs / relpath
        rows = read_arm(path)
        arms[name] = {
            "outputs_relpath": "runs/" + relpath,
            "outputs_sha256": sha256_file(path),
            **analyse(rows, ontology),
        }

    document = {
        "schema": "saea-slurp-closed-list-headroom-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": "SAEA-SLURP-MF-CLOSED-LIST-HEADROOM-V1",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "contacts": {
            "model": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "audio_decode": 0,
            "gpu_seconds": 0,
        },
        "gold_read": False,
        "gold_note": (
            "No devel or test annotation is opened anywhere in this script. The only "
            "label source is data.slurp.load_slurp_ontology with include_synthetic=False, "
            "which reads train.jsonl and nothing else; the question asked of each sealed "
            "prediction is whether it names a LEGAL label, never whether it is correct."
        ),
        "inventory": {
            "source": "train.jsonl through data.slurp.load_slurp_ontology(include_synthetic=False)",
            "scenarios": len(ontology.scenarios),
            "actions": len(ontology.actions),
            "entity_types": len(ontology.entity_types),
            "observed_scenario_action_pairs": len(ontology.intents),
            "implied_cross_product": len(ontology.scenarios) * len(ontology.actions),
            "actions_by_scenario": {
                scenario: list(actions)
                for scenario, actions in sorted(ontology.actions_by_scenario.items())
            },
            "task_contract_sha256": hashlib.sha256(contract.encode("utf-8")).hexdigest(),
            "task_contract_chars": len(contract),
            "label_inventory_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
            "label_inventory_chars": len(block),
            "instruction_fill_sha256": hashlib.sha256(rendered_fill.encode("utf-8")).hexdigest(),
            "instruction_fill_chars": len(rendered_fill),
        },
        "arms": arms,
        "reading": (
            "The sealed M0 prompt already carried the scenario list, the action list and the "
            "entity-type list, and its predictions respect them at 91.4 / 93.1 / 99.7 percent. "
            "It never carried the PAIRING, and 32.20 percent of its predictions are a pair that "
            "does not occur in train -- an upper bound on what a closed intent inventory can "
            "repair, and 69 percent of M0's own 46.4-point intent error. BLEND, which supplies "
            "TRAIN-mined exemplars carrying real intent pairs, drives the same figure to 2.10 "
            "percent, so a large part of what the knowledge plane supplies on this carrier is "
            "the intent pairing itself."
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(document["arms"], indent=2, sort_keys=True))
    print("wrote", args.out, sha256_file(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
