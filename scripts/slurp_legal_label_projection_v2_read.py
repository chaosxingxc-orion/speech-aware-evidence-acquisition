#!/usr/bin/env python3
"""The single registered read of SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1.

Scoring-side only. **Zero model, GPU, tool, embedding and network contacts.**
Preregistration:
``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md``.

Every sealed SLURP arm on the DEV-1000 roster is scored THREE times over its
complete 1,000-row manifest through ``core.scoring_batch`` with
``include_per_sample=True``, one job per manifest, never sharded:

* ``slurp-slu-official`` -- UNPROJECTED, the identity anchor that must
  reproduce its own published verdict to the second decimal from the same
  sealed bytes;
* ``slurp-slu-official-projected`` -- ``slurp-legal-label-projection-v1``, the
  LOCKED comparator, which must likewise reproduce v1's own published verdict;
* ``slurp-slu-official-projected-v2`` -- the successor rule under test.

Both projected jobs need a manifest that declares their scorer, and
``core.bundle.verify_bundle`` confines every artifact path a manifest names to
the manifest's own directory. So two DERIVED run manifests are written beside
each sealed one, differing from it **only in the ``scorers`` list**; their
sha256 goes into this read's output, and neither replaces a sealed manifest --
which is re-verified, byte for byte, by the unprojected job in the same batch.

The KU-S1c DRAFT phase has no run manifest of its own: its bytes live in that
flight's sealed ``.phases.json`` and were already paid for. It is scored
through the same registered scorer functions over the same complete 1,000
rows, exactly as its own 2026-09-05 read and v1's read did. That deviation is
registered in advance in the preregistration, section 3.

Gold opens once, scoring-side, through the registered official scorer on
``split_id="devel"`` with ``allow_heldout=False``. No SLURP devel sentence text
is read anywhere; the held-out ``test`` split is never named, loaded or scored.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.paired import paired_contrast
from speech_aware_evidence_acquisition.core.scoring_batch import ScoreJob, run_score_batch
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.slurp import load_slurp_ontology, load_slurp_split
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    load_legal_intent_inventory,
    score_slurp_outputs_official,
    score_slurp_outputs_official_projected,
    score_slurp_outputs_official_projected_v2,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SLURP_LABEL_PROJECTION_ID,
    SLURP_LABEL_PROJECTION_V2_ID,
    parse_slu_response,
)

SCHEMA = "saea-slurp-legal-label-projection-v2-read-v1"
ROW_ID = "SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-V2-V1"
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90

#: ``view -> (registered scorer id, direct scorer function, derived-manifest
#: suffix)``. ``unprojected`` reads the SEALED manifest and so needs no derived
#: one.
VIEWS: dict[str, tuple[str, object, str | None]] = {
    "unprojected": ("slurp-slu-official", score_slurp_outputs_official, None),
    "v1": (
        "slurp-slu-official-projected",
        score_slurp_outputs_official_projected,
        ".legal-label-projection-v2-read.v1.run-manifest.json",
    ),
    "v2": (
        "slurp-slu-official-projected-v2",
        score_slurp_outputs_official_projected_v2,
        ".legal-label-projection-v2-read.v2.run-manifest.json",
    ),
}

#: ``name -> (left view, right view)``; every delta is ``right - left`` on the
#: SAME sealed rows.
CONTRASTS: dict[str, tuple[str, str]] = {
    "v2_minus_v1": ("v1", "v2"),
    "v2_minus_unprojected": ("unprojected", "v2"),
    "v1_minus_unprojected": ("unprojected", "v1"),
}

#: The two contrasts the preregistered lock rule is evaluated in (section 6).
LOCK_CONTRASTS = ("v2_minus_v1", "v2_minus_unprojected")

PAIRED_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)

#: ``arm name -> (run id, attempt id)``. Every one of these was sealed by a
#: separately registered flight; this read adds no row and no contact.
ARMS: dict[str, tuple[str, str]] = {
    "CLOSED-LIST": (
        "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
        "attempt-20260905T060424Z-2c5596",
    ),
    "KU-S1C": (
        "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1",
        "attempt-20260906T042946Z-44720f",
    ),
    "KC-S1A": (
        "SAEA-SLURP-KC-S1A-SLOTS-DEV1000-V1",
        "attempt-20260906T023017Z-38c20a",
    ),
    "KC-S1B": (
        "SAEA-SLURP-KC-S1B-SLOTS-SCHEMA-DEV1000-V1",
        "attempt-20260906T025102Z-af6b04",
    ),
}

#: The arm whose numbers the lock rule is evaluated on.
LOCK_ARM = "CLOSED-LIST"

#: Arms that answer ``{"entities": [...]}`` on most rows and therefore carry no
#: intent of their own; every ENTITY-side metric of theirs must be identical in
#: all three views (their as-sealed label columns are not: v1's read found they
#: volunteer a pair on 194 and 456 rows respectively).
ENTITY_ONLY_ARMS = ("KC-S1A", "KC-S1B")

#: KC-S1b's own prompt-fit receipt, which lists by id the 42 rows that fell back
#: to the full 60-intent schema because the sealed closed-list response for that
#: row does not parse or names an impossible pair.
KC_S1B_PROMPT_FIT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/"
    "prompt-fit.json"
)

#: Every number the two PUBLISHED verdicts state, hard-coded so this read
#: FAILS CLOSED if the same sealed bytes ever stop reproducing them:
#: ``docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md``
#: and section 1 of
#: ``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-verdict.md``.
#: The v2 column has no anchor by construction -- it has never been published.
PUBLISHED: dict[str, dict[str, dict[str, float]]] = {
    "CLOSED-LIST": {
        "unprojected": {
            "scenario": 81.00, "action": 73.90, "intent": 71.40,
            "entities_strict": 21.91, "word_f1": 33.69, "char_f1": 38.20, "slu_f1": 35.80,
        },
        "v1": {
            "scenario": 81.00, "action": 73.30, "intent": 71.60,
            "entities_strict": 21.91, "word_f1": 33.69, "char_f1": 38.20, "slu_f1": 35.80,
        },
    },
    "KU-S1C": {
        "unprojected": {
            "scenario": 81.50, "action": 75.20, "intent": 72.90,
            "entities_strict": 23.26, "word_f1": 33.99, "char_f1": 38.07, "slu_f1": 35.92,
        },
        "v1": {
            "scenario": 81.50, "action": 74.70, "intent": 73.10,
            "entities_strict": 23.26, "word_f1": 33.99, "char_f1": 38.07, "slu_f1": 35.92,
        },
    },
    "KU-S1C-DRAFT": {
        "unprojected": {
            "scenario": 81.40, "action": 74.90, "intent": 72.60,
            "entities_strict": 22.50, "word_f1": 33.62, "char_f1": 37.62, "slu_f1": 35.51,
        },
        "v1": {
            "scenario": 81.40, "action": 74.30, "intent": 72.70,
            "entities_strict": 22.50, "word_f1": 33.62, "char_f1": 37.62, "slu_f1": 35.51,
        },
    },
    "KC-S1A": {
        "unprojected": {
            "scenario": 16.10, "action": 15.70, "intent": 15.20,
            "entities_strict": 21.82, "word_f1": 33.62, "char_f1": 38.17, "slu_f1": 35.75,
        },
        "v1": {
            "scenario": 16.10, "action": 15.50, "intent": 15.30,
            "entities_strict": 21.82, "word_f1": 33.62, "char_f1": 38.17, "slu_f1": 35.75,
        },
    },
    "KC-S1B": {
        "unprojected": {
            "scenario": 36.00, "action": 33.30, "intent": 32.10,
            "entities_strict": 31.37, "word_f1": 41.58, "char_f1": 47.51, "slu_f1": 44.35,
        },
        "v1": {
            "scenario": 36.00, "action": 32.80, "intent": 32.30,
            "entities_strict": 31.37, "word_f1": 41.58, "char_f1": 47.51, "slu_f1": 44.35,
        },
    },
}

REPO = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def receipt_ids(relpath: str) -> set[str]:
    return {item["id"] for item in read_json(REPO / relpath)["items"]}


def percent(count: int, total: int) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def attempt_dir(root: Path, run_id: str, attempt_id: str) -> Path:
    return Path(root) / "runs" / run_id / attempt_id


def sealed_manifest_path(root: Path, run_id: str, attempt_id: str) -> Path:
    return attempt_dir(root, run_id, attempt_id) / f"{run_id}.run-manifest.json"


def derived_manifest_path(sealed: Path, suffix: str) -> Path:
    return sealed.with_name(sealed.name.replace(".run-manifest.json", "") + suffix)


def write_derived_manifest(sealed: Path, suffix: str, scorers: list[str]) -> Path:
    """A manifest identical to ``sealed`` except for its ``scorers`` list.

    Written INTO the sealed attempt directory on purpose: ``verify_bundle``
    confines every artifact path a manifest names to the manifest's own parent
    directory, so a derived manifest that lives anywhere else could not name the
    sealed outputs at all. The sealed manifest itself is never touched, and the
    unprojected job re-verifies it from its own bytes in the same batch.
    """

    document = read_json(sealed)
    if document.get("scorers") == scorers:
        raise SystemExit(f"derived manifest for {sealed} would be a no-op copy")
    document["scorers"] = list(scorers)
    derived = derived_manifest_path(sealed, suffix)
    derived.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return derived


def rows_of(path: Path) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def draft_rows(phases_path: Path) -> list[dict]:
    """The KU-S1c draft phase's own sealed responses, in the outputs shape the
    registered scorer reads. No contact and no new exposure: those bytes were
    already paid for by the KU-S1c flight."""

    document = read_json(phases_path)
    draft: dict[str, str] | None = None
    for summary in document["phases"]:
        if str(summary["controller_policy_id"]).endswith(":draft"):
            draft = {
                result["sample_id"]: result["final_response_text"]
                for result in summary["results"]
            }
    if draft is None or len(draft) != 1000:
        raise SystemExit("the KU-S1c phases file carries no complete draft phase")
    return [{"sample_id": sid, "text": text} for sid, text in sorted(draft.items())]


def write_outputs(rows: list[dict], path: Path) -> Path:
    path.write_text(
        "\n".join(
            json.dumps({"sample_id": row["sample_id"], "text": row["text"]}, ensure_ascii=False)
            for row in rows
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def official_block(result: dict) -> dict:
    """The seven official numbers plus the answer accounting, in percent, from
    one registered-scorer result."""

    official = result["aggregate"]["official"]
    raw = official["raw"]
    per_sample = result["per_sample"]
    return {
        "scenario": round(100.0 * official["scenario_accuracy"], 2),
        "action": round(100.0 * official["action_accuracy"], 2),
        "intent": round(100.0 * official["intent_accuracy"], 2),
        "entities_strict": round(100.0 * float(raw["entities"]["f_measure"]), 2),
        "word_f1": round(100.0 * float(raw["entities_distance_word"]["f_measure"]), 2),
        "char_f1": round(100.0 * float(raw["entities_distance_char"]["f_measure"]), 2),
        "slu_f1": round(100.0 * official["slu_f1"], 2),
        "samples": len(per_sample),
        "unparsed": sum(1 for row in per_sample if not row["parsed"]),
        "identity_check_passed": bool(result["aggregate"]["identity_check"]["passed"]),
        "identity_check_slu_f1_abs_diff": result["aggregate"]["identity_check"][
            "slu_f1_abs_diff"
        ],
    }


def by_sample(result: dict) -> dict[str, dict]:
    return {row["sample_id"]: row for row in result["per_sample"]}


def mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def contrast_rows(left: dict, right: dict, ids, stratum_of) -> dict:
    contrasts = paired_contrast(
        left,
        right,
        metrics=PAIRED_METRICS,
        sample_ids=sorted(ids),
        strata_of=stratum_of,
        seed=SEED,
        n_replicates=N_REPLICATES,
        ci_level=CI_LEVEL,
    )
    out: dict[str, dict] = {}
    for metric, contrast in contrasts.items():
        document = contrast.as_dict()
        bootstrap = document.get("bootstrap") or {}
        out[metric] = {
            "n": document["n"],
            "left_pct": round(100.0 * document["left_mean"], 2),
            "right_pct": round(100.0 * document["right_mean"], 2),
            "delta_pp": round(100.0 * document["delta"], 2),
            "saves": document["saves"],
            "harms": document["harms"],
            "ties": document["ties"],
            "sign_test_p": document["sign_test_p"],
            "ci90_pp": [
                round(100.0 * bootstrap.get("ci_low", 0.0), 2),
                round(100.0 * bootstrap.get("ci_high", 0.0), 2),
            ],
            "per_stratum": {
                name: {
                    "n": row["n"],
                    "left_pct": round(100.0 * row["left_mean"], 2),
                    "right_pct": round(100.0 * row["right_mean"], 2),
                    "delta_pp": round(100.0 * row["delta"], 2),
                    "saves": row["saves"],
                    "harms": row["harms"],
                }
                for name, row in document["per_stratum"].items()
            },
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="where read.json lands")
    parser.add_argument(
        "--score-dir",
        type=Path,
        default=None,
        help="empty directory for the score batch (default: under SPEECHRL_DATA_DIR)",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--reuse-score-dir",
        action="store_true",
        help=(
            "re-read an existing score batch instead of running it again "
            "(the batch is deterministic; this only avoids re-spawning the official "
            "evaluator for an analysis-side change)"
        ),
    )
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = Path(data_root())
    started = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # 1. The legal inventory itself, and the gold side of the roster.
    # ------------------------------------------------------------------
    ontology = load_slurp_ontology(lock, root)
    inventory = load_legal_intent_inventory(lock, root)
    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}

    # ------------------------------------------------------------------
    # 2. The score batch: one job per manifest per view.
    # ------------------------------------------------------------------
    score_dir = args.score_dir or (root / "runs" / ROW_ID / "score-batch")
    score_dir = Path(score_dir)
    if score_dir.exists() and any(score_dir.iterdir()) and not args.reuse_score_dir:
        raise SystemExit(f"score directory is not empty: {score_dir}")

    manifests: dict[str, dict] = {}
    jobs: list[ScoreJob] = []
    outputs_paths: dict[str, Path] = {}
    for arm, (run_id, attempt_id) in ARMS.items():
        sealed = sealed_manifest_path(root, run_id, attempt_id)
        if not sealed.is_file():
            raise SystemExit(f"sealed manifest missing for {arm}: {sealed}")
        outputs_paths[arm] = Path(read_json(sealed)["outputs"]["path"])
        entry = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "sealed_manifest": str(sealed),
            "sealed_manifest_sha256": sha256_file(sealed),
            "sealed_manifest_scorers": read_json(sealed)["scorers"],
            "outputs_sha256": read_json(sealed)["outputs"]["sha256"],
            "derived": {},
        }
        for view, (scorer, _function, suffix) in VIEWS.items():
            if suffix is None:
                jobs.append(ScoreJob(job_id=f"{arm.lower()}-{view}", manifest=sealed))
                continue
            derived = (
                derived_manifest_path(sealed, suffix)
                if args.reuse_score_dir
                else write_derived_manifest(sealed, suffix, [scorer])
            )
            entry["derived"][view] = {
                "manifest": str(derived),
                "manifest_sha256": sha256_file(derived),
                "scorers": [scorer],
            }
            jobs.append(ScoreJob(job_id=f"{arm.lower()}-{view}", manifest=derived))
        manifests[arm] = entry

    if args.reuse_score_dir:
        batch = read_json(score_dir / "batch-summary.json")
    else:
        batch = run_score_batch(
            jobs,
            output_dir=score_dir,
            max_workers=args.workers,
            include_per_sample=True,
        )
    if batch["failed"]:
        raise SystemExit(f"score batch failed: {json.dumps(batch['jobs'], indent=2)[:4000]}")

    scored: dict[str, dict[str, dict]] = {}
    for arm in ARMS:
        scored[arm] = {}
        for view, (scorer, _function, _suffix) in VIEWS.items():
            payload = read_json(score_dir / f"{arm.lower()}-{view}.score.json")
            scored[arm][view] = payload["scores"][scorer]

    # ------------------------------------------------------------------
    # 3. The KU-S1c draft phase (no manifest of its own -- registered
    #    deviation, preregistration section 3).
    # ------------------------------------------------------------------
    run_id, attempt_id = ARMS["KU-S1C"]
    phases_path = attempt_dir(root, run_id, attempt_id) / f"{run_id}.phases.json"
    workdir = Path(tempfile.mkdtemp(prefix="saea-b1b-v2-", dir=str(root)))
    draft = draft_rows(phases_path)
    try:
        draft_path = write_outputs(draft, workdir / "ku-s1c-draft.outputs.jsonl")
        scored["KU-S1C-DRAFT"] = {
            view: function(draft_path, lock, root, split_id="devel")
            for view, (_scorer, function, _suffix) in VIEWS.items()
        }
        manifests["KU-S1C-DRAFT"] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "sealed_manifest": None,
            "phases_file": str(phases_path),
            "phases_file_sha256": sha256_file(phases_path),
            "outputs_projection_sha256": sha256_file(draft_path),
            "note": (
                "the draft phase's own sealed responses, read from the flight's phases file "
                "and scored through the same registered scorer functions over the same "
                "complete 1,000 rows; no manifest exists for a phase, so core.scoring_batch "
                "cannot reach it (registered in advance)"
            ),
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    arms = list(scored)

    # ------------------------------------------------------------------
    # 4. Populations and strata.
    # ------------------------------------------------------------------
    ids_all = sorted(by_sample(scored[LOCK_ARM]["unprojected"]))
    if len(ids_all) != 1000:
        raise SystemExit(f"{LOCK_ARM} carries {len(ids_all)} rows, expected 1000")
    for arm, views in scored.items():
        for view, result in views.items():
            if sorted(by_sample(result)) != ids_all:
                raise SystemExit(
                    f"{arm} ({view}) does not cover the same 1,000 sample ids as {LOCK_ARM}"
                )
    if any(sample_id not in gold for sample_id in ids_all):
        raise SystemExit("a scored sample id is not part of the SLURP devel split")
    old500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-500.json") & set(ids_all))
    new500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-1000-NEW500.json") & set(ids_all))
    if len(old500) != 500 or len(new500) != 500 or set(old500) & set(new500):
        raise SystemExit("the OLD500 / NEW500 partition of DEV-1000 does not reconstruct")
    populations = {"pooled_1000": ids_all, "old500": old500, "new500": new500}

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    # ------------------------------------------------------------------
    # 5. The published identity anchors, checked before any new number is
    #    trusted. FAILS CLOSED: if the same sealed bytes stop reproducing a
    #    published verdict, nothing downstream of that is worth reading.
    # ------------------------------------------------------------------
    anchors: dict[str, dict] = {}
    anchor_failures: list[str] = []
    for arm, expected_views in PUBLISHED.items():
        anchors[arm] = {}
        for view, expected in expected_views.items():
            observed = official_block(scored[arm][view])
            mismatches = {
                metric: {"published": value, "observed": observed[metric]}
                for metric, value in expected.items()
                if abs(observed[metric] - value) > 1e-9
            }
            anchors[arm][view] = {
                "published": expected,
                "observed": {metric: observed[metric] for metric in expected},
                "matches": not mismatches,
                "mismatches": mismatches,
            }
            if mismatches:
                anchor_failures.append(f"{arm}/{view}: {mismatches}")
    if anchor_failures:
        raise SystemExit(
            "published identity anchors did not reproduce from the sealed bytes:\n"
            + "\n".join(anchor_failures)
        )

    # ------------------------------------------------------------------
    # 6. Structural properties the preregistration stated in advance.
    # ------------------------------------------------------------------
    legal_pairs = inventory.pairs
    gold_outside = sorted(
        sample_id
        for sample_id in ids_all
        if (gold[sample_id].scenario, gold[sample_id].action) not in legal_pairs
    )

    # ------------------------------------------------------------------
    # 7. Per-arm tables.
    # ------------------------------------------------------------------
    entity_fields = ("slot_f1_exact_f1", "slu_f1_f1", "slu_f1_word_f1", "slu_f1_char_f1")
    tables: dict[str, dict] = {}
    for arm in arms:
        views = {view: by_sample(scored[arm][view]) for view in VIEWS}
        base = views["unprojected"]
        entity_side_moved = sorted(
            sample_id
            for sample_id in ids_all
            if any(
                views[view][sample_id][field] != base[sample_id][field]
                for view in ("v1", "v2")
                for field in entity_fields
            )
        )
        projection_blocks: dict[str, dict] = {}
        for view in ("v1", "v2"):
            projection = scored[arm][view]["aggregate"]["projection"]
            right = views[view]
            changed_ids = sorted(
                sample_id for sample_id in ids_all if right[sample_id].get("projected")
            )
            per_scenario = collections.Counter(stratum_of(sid) for sid in changed_ids)
            branch_gold = collections.Counter()
            branch_rows = collections.Counter()
            for sample_id in changed_ids:
                branch = str(right[sample_id].get("projected_branch"))
                branch_rows[branch] += 1
                if right[sample_id]["scenario_action_exact"] == 1.0:
                    branch_gold[branch] += 1
            projection_blocks[view] = {
                "projection_id": projection.get("projection_id"),
                "projection_version": projection.get("projection_version"),
                "counts": projection.get("counts"),
                "branch_counts": projection.get("branch_counts"),
                "map": projection.get("map"),
                "map_by_branch": projection.get("map_by_branch"),
                "changed_rows": len(changed_ids),
                "changed_rows_pct": percent(len(changed_ids), len(ids_all)),
                "changed_rows_landing_on_gold_intent": sum(branch_gold.values()),
                "changed_rows_per_branch": dict(sorted(branch_rows.items())),
                "changed_rows_landing_on_gold_per_branch": dict(sorted(branch_gold.items())),
                "changed_rows_per_gold_scenario": dict(sorted(per_scenario.items())),
            }
        tables[arm] = {
            "official": {view: official_block(scored[arm][view]) for view in VIEWS},
            "projection": projection_blocks,
            "entity_side_rows_moved": entity_side_moved,
            "entity_side_invariant_holds": not entity_side_moved,
            "paired": {
                name: {
                    population: contrast_rows(views[left], views[right], ids, stratum_of)
                    for population, ids in populations.items()
                }
                for name, (left, right) in CONTRASTS.items()
            },
            "weightings_intent": {
                view: {
                    population: {
                        "natural_pct": round(
                            100.0
                            * mean(views[view][sid]["scenario_action_exact"] for sid in ids),
                            2,
                        ),
                        "equal_stratum_pct": round(
                            100.0
                            * mean(
                                mean(
                                    views[view][sid]["scenario_action_exact"]
                                    for sid in ids
                                    if stratum_of(sid) == scenario
                                )
                                for scenario in sorted({stratum_of(sid) for sid in ids})
                            ),
                            2,
                        ),
                    }
                    for population, ids in populations.items()
                }
                for view in VIEWS
            },
        }

    # ------------------------------------------------------------------
    # 8. Impossible-pair rate before and after, on the same sealed rows.
    # ------------------------------------------------------------------
    # An eligible row is changed by a projection if and only if its pair was
    # not one of the 60, and both rules always emit one of the 60, so "changed"
    # IS the impossible-pair count before and the rate after is zero by
    # construction. Both are re-derived from the emitted labels rather than
    # asserted, so a defect in either rule shows up here as a non-zero residual
    # instead of hiding behind its own bookkeeping.
    impossible: dict[str, dict] = {}
    for arm in arms:
        impossible[arm] = {}
        for view in ("v1", "v2"):
            right = by_sample(scored[arm][view])
            counts = scored[arm][view]["aggregate"]["projection"]["counts"]
            residual = sum(
                1
                for sid in ids_all
                if right[sid].get("projected_to") is not None
                and tuple(str(right[sid]["projected_to"]).split("_", 1)) not in legal_pairs
            )
            impossible[arm][view] = {
                "eligible_rows": counts["eligible"],
                "ineligible_rows": counts["ineligible"],
                "impossible_pairs_before": counts["changed"],
                "impossible_pairs_before_pct": percent(counts["changed"], len(ids_all)),
                "impossible_pairs_after": 0,
                "residual_illegal_targets": residual,
            }

    # ------------------------------------------------------------------
    # 9. What is LEFT after v2, described. NOT part of the registered rule,
    #    NOT a metric, NOT a gate, and it changes no lock decision. v1's read
    #    named the action-as-scenario class this way and v2 is the answer to
    #    it; this asks the same question of v2's own residual so the next rule,
    #    if there is one, has something to be registered against.
    # ------------------------------------------------------------------
    source_rows = {arm: rows_of(path) for arm, path in outputs_paths.items()}
    source_rows["KU-S1C-DRAFT"] = draft
    residual: dict[str, dict] = {}
    for arm in arms:
        right = by_sample(scored[arm]["v2"])
        changed = [sid for sid in ids_all if right[sid].get("projected")]
        parsed_by_id = {
            row["sample_id"]: parse_slu_response(row["text"]) for row in source_rows[arm]
        }
        still_wrong = [sid for sid in changed if right[sid]["scenario_action_exact"] != 1.0]
        exchange_legal = exchange_gold = 0
        promoted_but_wrong_action = 0
        for sample_id in still_wrong:
            scenario, action, _entities, was_parsed = parsed_by_id[sample_id]
            if not was_parsed or scenario is None or action is None:
                continue
            record = gold[sample_id]
            if (action, scenario) in legal_pairs:
                exchange_legal += 1
                exchange_gold += (action, scenario) == (record.scenario, record.action)
            if right[sample_id].get("projected_branch") == "promote":
                promoted_but_wrong_action += 1
        residual[arm] = {
            "changed_rows": len(changed),
            "landed_on_gold": len(changed) - len(still_wrong),
            "still_wrong_after_v2": len(still_wrong),
            "still_wrong_whose_halves_exchange_to_a_legal_pair": exchange_legal,
            "still_wrong_whose_exchange_equals_gold": exchange_gold,
            "still_wrong_that_the_promote_branch_touched": promoted_but_wrong_action,
            "definition": (
                "among the rows the v2 projection CHANGED: how many still miss the gold "
                "intent, and what those rows look like. Descriptive only -- no rule, no "
                "metric, no gate, no effect on the lock decision."
            ),
        }

    # ------------------------------------------------------------------
    # 10. The 42 KC-S1b fallback rows, under both rules.
    # ------------------------------------------------------------------
    fallback = None
    prompt_fit_path = REPO / KC_S1B_PROMPT_FIT
    if prompt_fit_path.is_file():
        document = read_json(prompt_fit_path)
        fallback_ids = sorted(_collect_fallback_ids(document))
        left = by_sample(scored["CLOSED-LIST"]["unprojected"])
        fallback = {
            "source": KC_S1B_PROMPT_FIT,
            "fallback_rows": len(fallback_ids),
            "rows_still_unparsed": len([sid for sid in fallback_ids if not left[sid]["parsed"]]),
            "note": (
                "forward looking only: KC-S1b chose its per-intent TRAIN slot schema block "
                "from the SEALED closed-list response, so this says what a successor cell "
                "would have served, never what KC-S1b did serve. No KC-S1b number is "
                "restated because of it."
            ),
        }
        for view in ("v1", "v2"):
            right = by_sample(scored["CLOSED-LIST"][view])
            legal_after = [sid for sid in fallback_ids if right[sid].get("projected")]
            gold_after = [
                sid for sid in legal_after if right[sid]["scenario_action_exact"] == 1.0
            ]
            fallback[view] = {
                "rows_made_legal_by_the_projection": len(legal_after),
                "rows_landing_on_the_gold_intent": len(gold_after),
            }

    # ------------------------------------------------------------------
    # 11. The lock rule, applied exactly as preregistered (section 6): BOTH
    #     contrasts, on the CLOSED-LIST arm.
    # ------------------------------------------------------------------
    lock_table = tables[LOCK_ARM]
    per_contrast: dict[str, dict] = {}
    for name in LOCK_CONTRASTS:
        paired = lock_table["paired"][name]
        pooled = paired["pooled_1000"]["scenario_action_exact"]
        intent_old = paired["old500"]["scenario_action_exact"]
        intent_new = paired["new500"]["scenario_action_exact"]
        worst = max(
            pooled["per_stratum"].items(),
            key=lambda item: item[1]["harms"],
            default=(None, {"harms": 0}),
        )
        conditions = {
            "intent_delta_old500_non_negative": intent_old["delta_pp"] >= 0.0,
            "intent_delta_new500_non_negative": intent_new["delta_pp"] >= 0.0,
            "no_stratum_harmed_by_more_than_one_row": all(
                row["harms"] <= 1 for row in pooled["per_stratum"].values()
            ),
        }
        per_contrast[name] = {
            "conditions": conditions,
            "passed": all(conditions.values()),
            "intent_delta_pooled_pp": pooled["delta_pp"],
            "intent_delta_old500_pp": intent_old["delta_pp"],
            "intent_delta_new500_pp": intent_new["delta_pp"],
            "worst_stratum_intent_harms": {"stratum": worst[0], "harms": worst[1]["harms"]},
        }
    locked = all(entry["passed"] for entry in per_contrast.values())

    document = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "row_id": ROW_ID,
        "generated_at": started.isoformat(),
        "boundary": (
            "zero model, GPU, tool, embedding and network contacts. Every number is computed "
            "from outputs JSONL files that prior, separately-registered runs already sealed; "
            "gold enters only through the registered official scorer, on split_id='devel' "
            "with allow_heldout=False. No SLURP devel sentence text is read. The held-out "
            "test split is never named, loaded or scored."
        ),
        "projection": {
            "v1": {"projection_id": SLURP_LABEL_PROJECTION_ID},
            "v2": {"projection_id": SLURP_LABEL_PROJECTION_V2_ID},
            "legal_intents": len(inventory.pairs),
            "legal_scenarios": len(inventory.scenarios),
            "actions_by_scenario": {
                scenario: list(actions)
                for scenario, actions in sorted(ontology.actions_by_scenario.items())
            },
            "multi_owner_actions": {
                action: list(inventory.owners_of(action))
                for action in sorted(
                    {a for actions in ontology.actions_by_scenario.values() for a in actions}
                )
                if len(inventory.owners_of(action)) > 1
            },
            "train_prior_source": "data.slurp.load_slurp_intent_slot_schema(...).intents[*].n",
        },
        "scorers": {view: scorer for view, (scorer, _f, _s) in VIEWS.items()},
        "statistics": {
            "resampler": "analysis.paired.paired_contrast",
            "n_replicates": N_REPLICATES,
            "seed": SEED,
            "ci_level": CI_LEVEL,
            "strata": "gold scenario",
            "delta_convention": "right view minus left view, on the same sealed rows",
            "contrasts": {name: {"left": left, "right": right} for name, (left, right) in CONTRASTS.items()},
        },
        "populations": {name: len(ids) for name, ids in populations.items()},
        "manifests": manifests,
        "score_batch": {
            "output_dir": str(score_dir),
            "job_count": batch["job_count"],
            "succeeded": batch["succeeded"],
            "failed": batch["failed"],
            "elapsed_seconds": batch["elapsed_seconds"],
            "include_per_sample": True,
            "jobs": [
                {
                    "job_id": job["job_id"],
                    "manifest": job["manifest"],
                    "status": job["status"],
                    "elapsed_seconds": job["elapsed_seconds"],
                    "result_sha256": job["result_sha256"],
                }
                for job in batch["jobs"]
            ],
        },
        "published_identity_anchors": anchors,
        "preregistered_properties": {
            "devel_gold_intents_outside_the_train_pairs": len(gold_outside),
            "devel_gold_intent_rows_outside_the_train_pairs": gold_outside,
            "entity_side_invariant_holds_on_every_arm": all(
                table["entity_side_invariant_holds"] for table in tables.values()
            ),
            "entity_only_arms_label_rows_moved": {
                arm: tables[arm]["projection"]["v2"]["changed_rows"] for arm in ENTITY_ONLY_ARMS
            },
        },
        "arms": tables,
        "impossible_pairs": impossible,
        "residual_after_v2": residual,
        "kc_s1b_fallback_rows": fallback,
        "lock": {
            "arm": LOCK_ARM,
            "rule": (
                "re-lock as closed-list + projection v2 iff, in BOTH the v2-minus-v1 and "
                "the v2-minus-unprojected contrast, the intent delta is >= 0 on BOTH OLD500 "
                "and NEW500 and no gold-scenario stratum is harmed on intent by more than "
                "1 row"
            ),
            "contrasts": per_contrast,
            "locked": locked,
            "comparator_identity": {
                "run_id": ARMS[LOCK_ARM][0],
                "attempt_id": ARMS[LOCK_ARM][1],
                "run_manifest_sha256": manifests[LOCK_ARM]["sealed_manifest_sha256"],
                "outputs_sha256": manifests[LOCK_ARM]["outputs_sha256"],
                "scorer_id": VIEWS["v2" if locked else "v1"][0],
                "projection_id": (
                    SLURP_LABEL_PROJECTION_V2_ID if locked else SLURP_LABEL_PROJECTION_ID
                ),
                "intent_pct": lock_table["official"]["v2" if locked else "v1"]["intent"],
                "slu_f1_pct": lock_table["official"]["v2" if locked else "v1"]["slu_f1"],
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(document["lock"], indent=2, sort_keys=True))
    return 0


def _collect_fallback_ids(document: object) -> set[str]:
    """The KC-S1b prompt-fit receipt's own fallback-row id list, found without
    hard-coding a path through a receipt this read does not own."""

    found: set[str] = set()

    def walk(node: object, key_path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, key_path + (str(key),))
        elif isinstance(node, list):
            if any("fallback" in part.lower() for part in key_path) and all(
                isinstance(item, str) for item in node
            ):
                found.update(item for item in node if item.startswith("slurp:devel:"))
            else:
                for item in node:
                    walk(item, key_path)
        elif isinstance(node, str) and node.startswith("slurp:devel:"):
            if any("fallback" in part.lower() for part in key_path):
                found.add(node)

    walk(document, ())
    return found


if __name__ == "__main__":
    raise SystemExit(main())
