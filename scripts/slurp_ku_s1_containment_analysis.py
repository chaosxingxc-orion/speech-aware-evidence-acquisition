#!/usr/bin/env python3
"""Model-free containment analysis for the SLURP consumption cells KU-S1c / KU-S1.

Zero model, GPU, tool, embedding, network, audio and gold contacts. It reads
two frozen knowledge snapshots, the two committed control-turn templates and
the sealed closed-list outputs, and answers three questions before any
registration:

1. does either KU-S1c control turn collide with the protected material of the
   snapshot the cell binds (``rails.runner._assert_agent_control_excludes_
   knowledge_payloads``)?
2. how many of the 1,000 sealed closed-list responses -- the best available
   proxy for the phase-1 draft that phase 2 appends to its control turn --
   collide, under each snapshot?
3. can a ``KbFacetProvider`` top-5 supply packet ride an
   ``EvidenceAgentController`` control turn at all?

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python scripts/slurp_ku_s1_containment_analysis.py <output.json>
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.phase_material import (  # noqa: E402
    PREDECESSOR_PREFIX,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    _protected_knowledge_material,
)

ROOT = data_root()
SNAPSHOTS = {
    "slurp-kb-size-full": (
        "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
    ),
    "slurp-kb-size-full-label-prior-speaker": (
        "knowledge/slurp/saea-kb-distmodel-v1/size-full-label-prior-speaker/snapshot.json"
    ),
}
CLOSED_LIST_OUTPUTS = (
    "runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/"
    "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl"
)
TEMPLATES = {
    "draft": "configs/probes/slurp_phase_direct.txt",
    "revise": "configs/probes/slurp_phase_revise.txt",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_snapshot(relpath: str) -> KnowledgeSnapshot:
    return KnowledgeSnapshot.from_frozen_json(
        json.loads((ROOT / relpath).read_text(encoding="utf-8"))
    )


def sealed_responses() -> dict[str, str]:
    out: dict[str, str] = {}
    with (ROOT / CLOSED_LIST_OUTPUTS).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sid, text = row.get("sample_id"), row.get("text")
            if isinstance(sid, str) and isinstance(text, str):
                out[sid] = text
    return out


def first_hit(text: str, protected: tuple[str, ...]) -> str | None:
    low = text.casefold()
    for material in protected:
        if material in low:
            return material
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    static_text = {
        phase: (REPO / relpath).read_text(encoding="utf-8")
        for phase, relpath in TEMPLATES.items()
    }
    sealed = sealed_responses()

    # The exact bytes phase 2's control turn carries for each sample, as
    # rails.phase_material._appended builds it, with the sealed closed-list
    # response standing in for this run's own phase-1 draft.
    revise_turns = {
        sid: (
            f"{static_text['revise']}\n\n{PREDECESSOR_PREFIX} (phase:draft):\n{text}"
        )
        for sid, text in sealed.items()
    }

    report: dict[str, object] = {
        "schema": "saea-slurp-consumption-containment-analysis-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "model_contacts": 0,
        "gpu_contacts": 0,
        "tool_contacts": 0,
        "embedding_contacts": 0,
        "gold_reads": 0,
        "rule": (
            "rails.runner._assert_agent_control_excludes_knowledge_payloads: an "
            "AgentContactPlan.instruction may not contain, casefolded, any facet "
            "representation or value content of the bound snapshot whose stripped "
            "length is at least 8 characters. It reads the CONTROL turn only; the "
            "system message (adapter.instruction plus the task contract) is not "
            "read by it."
        ),
        "control_turn_templates": {
            phase: {
                "relpath": TEMPLATES[phase],
                "chars": len(text),
                "sha256": sha256_text(text),
            }
            for phase, text in static_text.items()
        },
        "sealed_closed_list_outputs": {
            "relpath": CLOSED_LIST_OUTPUTS,
            "rows": len(sealed),
        },
        "snapshots": {},
    }

    for name, relpath in SNAPSHOTS.items():
        snap = load_snapshot(relpath)
        protected = _protected_knowledge_material(snap)
        static_hits = {
            phase: first_hit(text, protected) for phase, text in static_text.items()
        }
        turn_hits = {
            sid: first_hit(turn, protected) for sid, turn in revise_turns.items()
        }
        colliding = {sid: hit for sid, hit in turn_hits.items() if hit is not None}
        histogram = collections.Counter(colliding.values())

        # What a KbFacetProvider top-5 supply packet would put on the control
        # turn: rails.runner._supply_for_state renders KnowledgeValue.content
        # verbatim, one line per value, and
        # EvidenceAgentController._dispatch appends the whole prompt_block to
        # the phase instruction.
        top5 = tuple(snap.values)[:5]
        block = "\n".join(f"[value {v.value_id}] {v.content}" for v in top5)
        supply_turn = f"{static_text['revise']}\n\nSupplied evidence:\n{block}"
        supply_all_hits = [m for m in protected if m in supply_turn.casefold()]

        report["snapshots"][name] = {
            "relpath": relpath,
            "sha256": snap.content_hash(),
            "dimensions": sorted({f.dimension for f in snap.facets}),
            "facets": len(snap.facets),
            "values": len(snap.values),
            "protected_payloads": len(protected),
            "values_at_or_over_8_chars": sum(
                1 for v in snap.values if len(v.content.strip()) >= 8
            ),
            "static_control_turn_collisions": {
                phase: hit for phase, hit in static_hits.items()
            },
            "static_control_turn_collision_count": sum(
                1 for hit in static_hits.values() if hit is not None
            ),
            "revise_control_turn_collision_count": len(colliding),
            "revise_control_turn_collision_rate": len(colliding) / max(len(sealed), 1),
            "revise_control_turn_collision_payload_histogram": dict(
                histogram.most_common()
            ),
            "revise_control_turn_colliding_sample_ids": sorted(colliding),
            "kb_facet_top5_supply_block": {
                "chars": len(block),
                "distinct_protected_payloads_embedded": len(supply_all_hits),
                "first_payloads": supply_all_hits[:5],
                "refused": bool(supply_all_hits),
            },
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    print("wrote %s" % args.output)
    print("sha256 %s" % hashlib.sha256(args.output.read_bytes()).hexdigest())
    for name, entry in report["snapshots"].items():
        print(
            "  %-42s payloads=%5d static=%d revise=%4d supply_refused=%s"
            % (
                name,
                entry["protected_payloads"],
                entry["static_control_turn_collision_count"],
                entry["revise_control_turn_collision_count"],
                entry["kb_facet_top5_supply_block"]["refused"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
