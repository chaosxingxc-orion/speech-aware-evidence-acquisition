#!/usr/bin/env python3
"""Prove that the composed config of cell COMP-1b differs from cell COMP-1's own
composed config by EXACTLY the citation-contract's four leaf paths (policy,
phase_material.solver.instruction_template, phase_material.solver.response_format_id,
native_episode.deliver_normaliser.normaliser) plus per-flight bookkeeping, and by
nothing else. Config only: no contact.

    python scripts/analysis/slurp_comp1b_diff_proof.py
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

BOOKKEEPING_PREFIXES = (
    "native_contact_fit.",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "what_this_is",
)
CITATION_FACTOR_PATHS = (
    "policy",
    "phase_material.solver.instruction_template",
    "phase_material.solver.response_format_id",
    "native_episode.deliver_normaliser.normaliser",
)


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def rd(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def composed_of(experiment: str):
    document = rd(f"configs/experiment/{experiment}.json")
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def classify(parent_values, mine, experiment_keys, allowed):
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))

    def matches(key: str, path: str) -> bool:
        return key == path or (path.endswith(".") and key.startswith(path))

    factor = [k for k in changed if any(matches(k, p) for p in allowed)]
    bookkeeping = [k for k in changed if k not in factor and k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k not in factor and k not in bookkeeping and k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in factor and k not in bookkeeping and k not in experiment_block]
    return {"factor_paths": factor, "bookkeeping": bookkeeping, "experiment_fragment_own_block": experiment_block, "anything_else": other, "old_values": {k: a.get(k) for k in factor}, "new_values": {k: b.get(k) for k in factor}}


def main() -> int:
    comp1_doc, comp1_cell, comp1 = composed_of("slurp-native-stage3-comp1-fold-a-v1")
    b_doc, b_cell, b = composed_of("slurp-native-stage3-comp1b-fold-a-v1")
    comp1_smoke_doc, comp1_smoke_cell, comp1_smoke = composed_of("slurp-native-stage3-comp1-fold-a-smoke-4-v1")
    bs_doc, bs_cell, bs = composed_of("slurp-native-stage3-comp1b-fold-a-smoke-4-v1")

    diff_arm = classify(comp1.values, b.values, set(comp1_doc) | set(b_doc), CITATION_FACTOR_PATHS)
    diff_smoke = classify(comp1_smoke.values, bs.values, set(comp1_smoke_doc) | set(bs_doc), CITATION_FACTOR_PATHS)

    report = {"arm": diff_arm, "smoke": diff_smoke}
    ok = True
    for name, diff in report.items():
        if diff["anything_else"]:
            ok = False
        if sorted(diff["factor_paths"]) != sorted(CITATION_FACTOR_PATHS):
            ok = False

    # Confirm the agreement term and centroid key are UNCHANGED between COMP-1
    # and COMP-1b (they must not appear in either diff at all).
    boundary = "knowledge_stores.intent-boundaries.phase_supply.perception."
    for name, diff in report.items():
        if any(k.startswith(boundary) for k in diff["factor_paths"] + diff["bookkeeping"] + diff["experiment_fragment_own_block"] + diff["anything_else"]):
            ok = False
            report[name]["UNEXPECTED_BOUNDARY_CHANGE"] = True

    report["ok"] = ok
    report["comp1_config_hash"] = comp1.config_hash
    report["comp1b_config_hash"] = b.config_hash
    report["comp1_smoke_config_hash"] = comp1_smoke.config_hash
    report["comp1b_smoke_config_hash"] = bs.config_hash
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
