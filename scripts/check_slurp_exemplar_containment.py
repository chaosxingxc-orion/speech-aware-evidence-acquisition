#!/usr/bin/env python3
"""CLI: containment preflight for the E3 exemplar supply (deliverable 3).

MODEL-FREE. Reproduces ``rails.runner._assert_agent_control_excludes_
knowledge_payloads``'s exact rule (casefolded substring test, an 8-character
protected-payload floor) over the new ``annotated-exemplars`` snapshot's
9,354 rendered VALUES against the anchor's actual composed instruction text
for every phase.

Why this is a template check rather than a 1,080-row replay: the anchor's
``configs/baseline/slurp-native-dual-store-train-fold-a-anchor-v1.json``
declares ``instruction_fill: null`` and ``state_fill: null`` on all FOUR
phases (perception, reviewer, planner, solver) -- verified directly from
the fragment, not inferred -- and its one instruction-affecting fill,
``task_instruction_fill: "slurp-label-inventory"``
(``data.slurp.render_slurp_closed_label_inventory``), takes only
``(lock, root)``, no per-row argument. The composed instruction text this
program sends is therefore BYTE-IDENTICAL across all 1,080 TRAIN Fold A
rows (confirmed independently: the sealed run's own ``MODEL_REQUEST`` trace
carries zero distinct ``task_instruction`` hashes over its first 3,000
requests) -- so checking the actual composed instruction ONCE per phase is
equivalent to checking it for every row, and a per-row loop would repeat
the identical string 1,080 times. Solver's own instruction, which is what
the E3 store's exemplar VALUES ride alongside on the acquire transition, is
plain ``configs/probes/slurp_native_role_solver_v2.txt`` verbatim -- no fill
of any kind.

Usage::

    python scripts/check_slurp_exemplar_containment.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    render_slurp_closed_label_inventory,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402

SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
CATALOG_RELPATH = "prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json"

PROBE_DIR = REPO_ROOT / "configs" / "probes"
TEMPLATES = {
    "context (task_instruction_template + task_instruction_fill)": (
        "slurp_native_role_context_v3.txt"
    ),
    "perception": "slurp_native_role_perception_v3.txt",
    "planner": "slurp_native_role_planner_v1.txt",
    "reviewer": "slurp_native_role_reviewer_v1.txt",
    "solver": "slurp_native_role_solver_v2.txt",
}

PROTECTED_FLOOR = 8


def _protected_values(snapshot: KnowledgeSnapshot) -> tuple[str, ...]:
    return tuple(
        material.strip().casefold()
        for material in (value.content for value in snapshot.values)
        if len(material.strip()) >= PROTECTED_FLOOR
    )


def _composed_texts(root: Path, lock) -> dict[str, str]:
    texts: dict[str, str] = {}
    label_inventory = render_slurp_closed_label_inventory(lock, root)
    for label, filename in TEMPLATES.items():
        raw = (PROBE_DIR / filename).read_text(encoding="utf-8")
        if "{tool_schemas}" in raw:
            raw = raw.replace("{tool_schemas}", label_inventory)
        texts[label] = raw
    catalog_path = root / CATALOG_RELPATH
    if catalog_path.is_file():
        texts["perception fill_params.source_catalog"] = catalog_path.read_text(
            encoding="utf-8"
        )
    return texts


def main() -> int:
    root = data_root()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    )
    protected = _protected_values(snapshot)
    print(
        f"snapshot values: {len(snapshot.values)}; protected (len>={PROTECTED_FLOOR}) "
        f"values: {len(protected)}"
    )

    texts = _composed_texts(root, lock)
    total_collisions = 0
    for label, text in texts.items():
        folded = text.casefold()
        hits = [material for material in protected if material in folded]
        total_collisions += len(hits)
        status = "COLLISION" if hits else "clean"
        print(f"[{status}] {label}: {len(text)} chars, {len(hits)} colliding value(s)")
        for hit in hits[:3]:
            print(f"    e.g. {hit[:80]!r}")

    print("---")
    print(
        f"total collisions across {len(texts)} composed instruction text(s) "
        f"(equivalent to all 1,080 TRAIN Fold A rows -- see module docstring): "
        f"{total_collisions}"
    )
    if total_collisions:
        print(
            "APPLY the no-example task-contract projection before this store may fly "
            "(search docs/readiness/2026-09-16-* and rails/ for 'no-example')."
        )
        return 1
    print("NO no-example projection needed: containment is clean as-is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
