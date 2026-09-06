#!/usr/bin/env python3
"""MF-7b: rebuild MF-7's DEV-1000 rows against the RE-LOCKED SLURP comparator.

Exposure row ``SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2``. **Zero model, GPU, tool,
embedding, network and audio contacts** -- this reads sealed bytes a prior,
separately registered flight already paid for.

MF-7 measured corrective power against the UNPROJECTED closed-list direct
baseline (intent 71.40 pooled / 73.20 NEW500 / 69.60 OLD500). The 2026-09-06
re-lock made the SLURP comparator that same sealed arm PLUS
``slurp-legal-label-projection-v2``, scored through the registered
``slurp-slu-official-projected-v2`` (73.10 / 75.20 / 71.00). Every MF-7b net
figure is stated against the new mask, so the per-row
``baseline_intent_correct`` flag has to be recomputed under the projection.

The recomputation is the registered scorer's own, not a re-implementation:
``reproduction.slurp_official_eval.score_slurp_outputs_official_projected_v2``
scores the sealed outputs JSONL and returns its per-sample
``scenario_action_exact``. The three published intent levels are hard-coded
below and asserted before anything is written -- if the sealed bytes stop
reproducing them the script raises rather than emitting a mask.

Output: ``$SPEECHRL_DATA_DIR/vectors/slurp-mf7b/dev-rows-projected-v2.jsonl``
(MF-7's ``dev-rows.jsonl`` with one field replaced) plus
``comparator-mask.receipt.json``. No SLURP devel sentence text is read, written
or logged; the held-out ``test`` split is never named.
"""

from __future__ import annotations

import argparse
import hashlib
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
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    score_slurp_outputs_official_projected_v2,
)

SCHEMA = "saea-mf7b-comparator-mask-v1"
ROW_ID = "SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2"
BASELINE_RUN = "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1"
BASELINE_ATTEMPT = "attempt-20260905T060424Z-2c5596"
SCORER_ID = "slurp-slu-official-projected-v2"
PROJECTION_ID = "slurp-legal-label-projection-v2"

#: The published levels of the re-locked comparator
#: (``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md``),
#: asserted before a mask is written. Percent, two decimals.
PUBLISHED_INTENT = {"ALL1000": 73.10, "NEW500": 75.20, "OLD500": 71.00}

#: The UNPROJECTED levels MF-7 used, asserted on the inherited flag in the same
#: pass so the change of mask is proven rather than assumed.
PUBLISHED_INTENT_UNPROJECTED = {"ALL1000": 71.40, "NEW500": 73.20, "OLD500": 69.60}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def levels(rows: list[dict], field: str) -> dict[str, float]:
    """Intent accuracy in percent, per population, from a per-row flag."""

    out: dict[str, float] = {}
    for population in ("ALL1000", "NEW500", "OLD500"):
        subset = [
            row
            for row in rows
            if population == "ALL1000" or row["population"] == population
        ]
        out[population] = round(
            100.0 * sum(float(row[field]) for row in subset) / len(subset), 10
        )
    return out


def assert_levels(actual: dict[str, float], expected: dict[str, float], what: str) -> None:
    for population, published in expected.items():
        if abs(actual[population] - published) > 5e-3:
            raise SystemExit(
                f"identity anchor FAILED for {what} on {population}: "
                f"reproduced {actual[population]:.4f}, published {published:.2f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the mask and its receipt")
    args = parser.parse_args()

    root = Path(data_root())
    lock = load_lock(umbrella_lock_path())
    source = root / "vectors/slurp-mf7/dev-rows.jsonl"
    out_dir = root / "vectors/slurp-mf7b"
    dev_rows = read_jsonl(source)
    if len(dev_rows) != 1000:
        raise SystemExit(f"expected 1,000 MF-7 dev rows, got {len(dev_rows)}")

    inherited = levels(dev_rows, "baseline_intent_correct")
    assert_levels(inherited, PUBLISHED_INTENT_UNPROJECTED, "the inherited unprojected mask")

    attempt = root / "runs" / BASELINE_RUN / BASELINE_ATTEMPT
    sealed_manifest = attempt / f"{BASELINE_RUN}.run-manifest.json"
    manifest = json.loads(sealed_manifest.read_text(encoding="utf-8"))
    outputs_path = Path(manifest["outputs"]["path"])
    if sha256_file(outputs_path) != manifest["outputs"]["sha256"]:
        raise SystemExit(f"sealed outputs {outputs_path} do not match the manifest sha256")

    scored = score_slurp_outputs_official_projected_v2(outputs_path, lock, root)
    per_sample = {row["sample_id"]: row for row in scored["per_sample"]}
    missing = [row["sample_id"] for row in dev_rows if row["sample_id"] not in per_sample]
    if missing:
        raise SystemExit(f"{len(missing)} DEV rows have no scored row; first {missing[0]!r}")

    projected_rows = []
    flipped_to_right = 0
    flipped_to_wrong = 0
    for row in dev_rows:
        new = dict(row)
        was = bool(float(row["baseline_intent_correct"]))
        now = bool(float(per_sample[row["sample_id"]]["scenario_action_exact"]))
        new["baseline_intent_correct"] = 1.0 if now else 0.0
        new["baseline_intent_correct_unprojected"] = 1.0 if was else 0.0
        new["baseline_projected"] = bool(per_sample[row["sample_id"]].get("projected", False))
        new["baseline_projected_branch"] = per_sample[row["sample_id"]].get("projected_branch")
        projected_rows.append(new)
        flipped_to_right += int(now and not was)
        flipped_to_wrong += int(was and not now)

    reproduced = levels(projected_rows, "baseline_intent_correct")
    assert_levels(reproduced, PUBLISHED_INTENT, "the re-locked projected-v2 mask")

    aggregate = scored["aggregate"]
    counts = {
        population: {
            "n": len([r for r in projected_rows if population == "ALL1000"
                      or r["population"] == population]),
            "right": len([r for r in projected_rows
                          if (population == "ALL1000" or r["population"] == population)
                          and r["baseline_intent_correct"] == 1.0]),
            "wrong": len([r for r in projected_rows
                          if (population == "ALL1000" or r["population"] == population)
                          and r["baseline_intent_correct"] == 0.0]),
        }
        for population in ("ALL1000", "NEW500", "OLD500")
    }

    print(json.dumps({"inherited": inherited, "projected_v2": reproduced,
                      "flipped_to_right": flipped_to_right,
                      "flipped_to_wrong": flipped_to_wrong,
                      "rows": counts}, indent=1))
    if not args.write:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    mask_path = out_dir / "dev-rows-projected-v2.jsonl"
    mask_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in projected_rows),
        encoding="utf-8",
    )
    write_json_artifact(out_dir / "comparator-mask.receipt.json", {
        "schema": SCHEMA,
        "exposure_ledger_row": ROW_ID,
        "comparator": {
            "run_id": BASELINE_RUN,
            "attempt_id": BASELINE_ATTEMPT,
            "sealed_manifest_sha256": sha256_file(sealed_manifest),
            "outputs_sha256": manifest["outputs"]["sha256"],
            "scorer_id": SCORER_ID,
            "projection_id": PROJECTION_ID,
        },
        "identity_anchors": {
            "published_projected_v2": PUBLISHED_INTENT,
            "reproduced_projected_v2": reproduced,
            "published_unprojected": PUBLISHED_INTENT_UNPROJECTED,
            "reproduced_unprojected": inherited,
            "passed": True,
        },
        "official": {
            "evaluator_commit": aggregate["evaluator_commit"],
            "identity_check": aggregate["identity_check"],
            "slu_f1": aggregate["official"]["slu_f1"],
            "projection": aggregate["projection"]["counts"],
            "projection_branches": aggregate["projection"]["branch_counts"],
        },
        "mask": {
            "file": mask_path.name,
            "source": str(source),
            "source_sha256": sha256_file(source),
            "sha256": sha256_file(mask_path),
            "bytes": mask_path.stat().st_size,
            "rows": len(projected_rows),
            "flipped_to_right": flipped_to_right,
            "flipped_to_wrong": flipped_to_wrong,
            "counts": counts,
        },
        "accounting": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": 0,
            "gpu_hours": 0.0,
            "speech_audio_seconds": 0.0,
        },
        "boundary": {
            "held_out_test_split_named": False,
            "devel_sentence_text_read": False,
            "note": "gold labels are opened scoring-side only, through the registered official "
            "scorer on split_id='devel' with allow_heldout=False",
        },
    })
    print(f"wrote {mask_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
