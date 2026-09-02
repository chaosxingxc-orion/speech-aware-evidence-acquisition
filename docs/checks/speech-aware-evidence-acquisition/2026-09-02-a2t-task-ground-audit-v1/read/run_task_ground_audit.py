"""Run the preregistered task-ground landed-surface audit once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[5]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    a2t_task_ground_audit as audit,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)

RUN_ID = "SAEA-A2T-MF-TASK-GROUND-AUDIT-V1"
SOURCE_HASHES = {
    "a0": "8b0e96ca6eac50b75eb07d6f1d05b245c43cc845e877b8f1dd185e4665c7ccff",
    "s2": "2377f09ac1138c2648e18fd6ac040465f5d4d11967f4f6479b39ec53bbffa8bf",
    "s2b": "ad49af4c73e281b5094aecb917bf59b4b13cf3c7472b54e45947f895a2a86363",
    "s2c": "904b63c1465371f6dcc5c6093cc39153001a32974d06fc83fab357c7a7f75fdc",
    "cpv2": "59b7e91fc2ce47e3f54652e20091228b2c78f970eac85771fe028313e9f13fc1",
    "headroom": "a3fc915b945a23e4d265c403235b51e4febd714d03fb4823b6613de067b7b8ac",
    "kb_size": "75f52a23ee86ff00abc2d33bb865fd3a0864dcb77fe7035eece13fbb2e77e081",
    "lexical": "624d85f9803291d3f2f8698687bc9c1d0dd43bb49f1bbc8b8948b14b983703fc",
    "registry": "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4",
}
SOURCE_PATHS = {
    "a0": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/verdict.json",
    "s2": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2-read/verdict.json",
    "s2b": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2b-read/verdict.json",
    "s2c": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-read/verdict.json",
    "cpv2": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-contract-preserving-cascade-104-v2/mechanism-result.json",
    "headroom": REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-postcontact-headroom-v1/headroom-result.json",
    "kb_size": REPO / "docs/receipts/knowledge/a2t-kb-size-full.json",
    "lexical": REPO / "docs/receipts/knowledge/a2t-kb-lexical-ceiling.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(key: str) -> Mapping[str, object]:
    path = SOURCE_PATHS[key]
    actual = _sha256(path)
    if actual != SOURCE_HASHES[key]:
        raise RuntimeError(f"{key} SHA-256 drift: {actual} != {SOURCE_HASHES[key]}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{key} source is not a JSON object")
    return value


def run_read(root: Path) -> dict[str, object]:
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    sources = {key: _read_object(key) for key in SOURCE_PATHS}
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    registry_sha = _sha256(registry_path)
    if registry_sha != SOURCE_HASHES["registry"]:
        raise RuntimeError(
            f"registry SHA-256 drift: {registry_sha} != {SOURCE_HASHES['registry']}"
        )
    registry = load_tool_registry(lock, root)

    a0_overall = sources["a0"]["overall"]
    cpv2_scores = sources["cpv2"]["official_scores"]
    cpv2_effects = sources["cpv2"]["mechanism_effects"]
    matched = cpv2_scores["matched_always_use"]
    headroom = sources["headroom"]["audit"]
    s1p = sources["s2"]["per_arm"]["S1p"]["overall"]
    b1 = sources["s2b"]["per_arm"]["B1"]["overall"]
    c3 = sources["s2c"]["per_arm"]["C3"]["overall"]
    kb_coverage = sources["kb_size"]["coverage_report"]
    lexical = sources["lexical"]["ceiling"]

    matched_metrics = audit.GroundMetrics(
        n_samples=104,
        exact_count=int(matched["exact_count"]),
        tool_correct_count=int(matched["tool_correct_count"]),
        parse_failures=int(matched["parse_failures"]),
        slot_micro_f1=float(matched["slot_micro_f1"]),
    )
    matched_qualification = audit.qualify_ground(matched_metrics)
    top5_coverage = (
        int(cpv2_scores["m0_direct"]["tool_correct_count"])
        + int(cpv2_effects["top5_gold_tool_correct_minus_m0_tool_correct"])
    ) / 104
    diagnosis = audit.diagnose_landed_surface(
        full_registry_tool_accuracy=float(a0_overall["tool_accuracy"]),
        full_registry_exact_match=float(a0_overall["exact_match"]),
        top5_gold_tool_coverage=top5_coverage,
        matched_exact_match=float(matched["exact_match"]),
        postcontact_oracle_exact_match=int(headroom["oracle_exact_count"]) / 104,
        highlighted_correct_row_conversion=float(s1p["em_conversion_rate"]),
        highlighted_correct_row_retention=float(s1p["tool_selection_retention"]),
        highlighted_default_substitutions=int(s1p["induced_substitution_count"]),
    )
    if len(registry) != 152 or not all(diagnosis.values()):
        raise RuntimeError("task-ground landed-surface invariants did not reproduce")

    return {
        "schema": "saea-a2t-task-ground-audit-result-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "claim_status": "sealed aggregate diagnosis and prospective ground contract",
        "source_hashes": SOURCE_HASHES,
        "ground_contract": {
            "minimum_exact_match": audit.MIN_EXACT_MATCH,
            "target_exact_match": audit.TARGET_EXACT_MATCH,
            "minimum_tool_accuracy": audit.MIN_TOOL_ACCURACY,
            "minimum_slot_micro_f1": audit.MIN_SLOT_MICRO_F1,
            "minimum_parse_rate": audit.MIN_PARSE_RATE,
        },
        "knowledge_inventory": {
            "registry_tools": len(registry),
            "construction_tools": kb_coverage["counts"]["selected_tools"],
            "argument_pattern_families": kb_coverage["counts"][
                "selected_argument_pattern_families"
            ],
            "argument_keys": kb_coverage["counts"]["selected_argument_keys"],
            "tool_coverage": kb_coverage["tool_coverage"],
            "argument_pattern_family_coverage": kb_coverage[
                "argument_pattern_family_coverage"
            ],
            "lexical_gold_tool_recall": {
                "at_5": lexical["recall_at_k"]["5"],
                "at_16": lexical["recall_at_k"]["16"],
                "at_32": lexical["recall_at_k"]["32"],
                "at_128": lexical["recall_at_k"]["128"],
            },
        },
        "landed_surfaces": {
            "full_registry_a0": {
                "n_samples": a0_overall["n_samples"],
                "tool_accuracy": a0_overall["tool_accuracy"],
                "exact_match": a0_overall["exact_match"],
            },
            "top5_matched_cpv2": {
                "metrics": matched_metrics.as_json(),
                "qualification": matched_qualification.as_json(),
                "gold_tool_coverage": top5_coverage,
            },
            "perfect_m0_matched_arbitration": {
                "exact_count": headroom["oracle_exact_count"],
                "exact_match": int(headroom["oracle_exact_count"]) / 104,
            },
            "highlighted_correct_registry_row": {
                "n_samples": s1p["n_samples"],
                "exact_conversion": s1p["em_conversion_rate"],
                "tool_retention": s1p["tool_selection_retention"],
                "literal_default_substitutions": s1p[
                    "induced_substitution_count"
                ],
            },
            "values_stripped_correct_row": {
                "exact_conversion": b1["em_conversion_rate"],
                "literal_default_substitutions": b1[
                    "induced_substitution_count"
                ],
            },
            "full_registry_plus_values_stripped_correct_row": {
                "exact_conversion": c3["em_conversion_rate"],
                "tool_retention": c3["tool_selection_retention"],
                "literal_default_substitutions": c3[
                    "induced_substitution_count"
                ],
            },
        },
        "diagnosis": diagnosis,
        "decision": (
            "expand task-wide executable knowledge before candidate pruning or "
            "training-free controller optimization"
        ),
        "contacts": {
            "frozen_core": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "http_or_socket": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
        "engineering_scope": {
            "complete_manifest_outer_parallel_scoring": True,
            "network_jitter_testing": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_read(data_root())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
