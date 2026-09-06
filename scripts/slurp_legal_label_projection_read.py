#!/usr/bin/env python3
"""The single registered read of SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1.

Scoring-side only. **Zero model, GPU, tool, embedding and network contacts.**
Preregistration:
``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md``.

Every sealed SLURP arm on the DEV-1000 roster is scored TWICE over its complete
1,000-row manifest through ``core.scoring_batch`` with
``include_per_sample=True``, one job per manifest, never sharded:

* once with the registered ``slurp-slu-official`` -- the UNPROJECTED identity
  anchor, which must reproduce its own published verdict to the second decimal
  from the same sealed bytes;
* once with the registered ``slurp-slu-official-projected``, the same code path
  with the legal-label projection on.

The projected jobs are driven by DERIVED run manifests that differ from the
sealed ones **only in the ``scorers`` list**. They are written beside the
artifacts they name (``core.bundle.verify_bundle`` confines every artifact path
to the manifest's own directory), carry their own sha256 in this read's output,
and never replace a sealed manifest -- which is re-verified, byte for byte, by
the unprojected job that reads it.

The KU-S1c DRAFT phase has no run manifest of its own: its bytes live in that
flight's sealed ``.phases.json`` and were already paid for. It is scored through
the same registered scorer functions over the same complete 1,000 rows, exactly
as its own 2026-09-05 read did. That deviation is registered in advance in the
preregistration, section 3.

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
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SLURP_LABEL_PROJECTION_ID,
    parse_slu_response,
)

SCHEMA = "saea-slurp-legal-label-projection-relock-read-v1"
ROW_ID = "SAEA-SLURP-MF-LEGAL-LABEL-PROJECTION-RELOCK-V1"
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90
UNPROJECTED_SCORER = "slurp-slu-official"
PROJECTED_SCORER = "slurp-slu-official-projected"
DERIVED_MANIFEST_SUFFIX = ".legal-label-projection-relock.run-manifest.json"

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

#: Arms that answer ``{"entities": [...]}`` and therefore carry no intent of
#: their own; the projection must leave every one of their metrics untouched.
ENTITY_ONLY_ARMS = ("KC-S1A", "KC-S1B")

#: KC-S1b's own prompt-fit receipt, which lists by id the 42 rows that fell back
#: to the full 60-intent schema because the sealed closed-list response for that
#: row does not parse or names an impossible pair.
KC_S1B_PROMPT_FIT = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/"
    "prompt-fit.json"
)

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


def write_derived_manifest(sealed: Path, scorers: list[str]) -> Path:
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
    derived = sealed.with_name(sealed.name.replace(".run-manifest.json", "") + DERIVED_MANIFEST_SUFFIX)
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
    # 2. The score batch: one job per manifest per scorer family.
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
        derived = (
            sealed.with_name(
                sealed.name.replace(".run-manifest.json", "") + DERIVED_MANIFEST_SUFFIX
            )
            if args.reuse_score_dir
            else write_derived_manifest(sealed, [PROJECTED_SCORER])
        )
        outputs_paths[arm] = Path(read_json(sealed)["outputs"]["path"])
        manifests[arm] = {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "sealed_manifest": str(sealed),
            "sealed_manifest_sha256": sha256_file(sealed),
            "sealed_manifest_scorers": read_json(sealed)["scorers"],
            "derived_manifest": str(derived),
            "derived_manifest_sha256": sha256_file(derived),
            "derived_manifest_scorers": [PROJECTED_SCORER],
            "outputs_sha256": read_json(sealed)["outputs"]["sha256"],
        }
        jobs.append(ScoreJob(job_id=f"{arm.lower()}-unprojected", manifest=sealed))
        jobs.append(ScoreJob(job_id=f"{arm.lower()}-projected", manifest=derived))

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
        for view, scorer in (("unprojected", UNPROJECTED_SCORER), ("projected", PROJECTED_SCORER)):
            payload = read_json(score_dir / f"{arm.lower()}-{view}.score.json")
            scored[arm][view] = payload["scores"][scorer]

    # ------------------------------------------------------------------
    # 3. The KU-S1c draft phase (no manifest of its own -- registered
    #    deviation, preregistration section 3).
    # ------------------------------------------------------------------
    run_id, attempt_id = ARMS["KU-S1C"]
    phases_path = attempt_dir(root, run_id, attempt_id) / f"{run_id}.phases.json"
    workdir = Path(tempfile.mkdtemp(prefix="saea-b1-relock-", dir=str(root)))
    draft = draft_rows(phases_path)
    try:
        draft_path = write_outputs(draft, workdir / "ku-s1c-draft.outputs.jsonl")
        scored["KU-S1C-DRAFT"] = {
            "unprojected": score_slurp_outputs_official(draft_path, lock, root, split_id="devel"),
            "projected": score_slurp_outputs_official_projected(
                draft_path, lock, root, split_id="devel"
            ),
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
    # 5. Structural properties the preregistration stated in advance.
    # ------------------------------------------------------------------
    legal_pairs = inventory.pairs
    gold_outside = sorted(
        sample_id
        for sample_id in ids_all
        if (gold[sample_id].scenario, gold[sample_id].action) not in legal_pairs
    )

    # ------------------------------------------------------------------
    # 6. Per-arm tables.
    # ------------------------------------------------------------------
    tables: dict[str, dict] = {}
    for arm in arms:
        unprojected = scored[arm]["unprojected"]
        projected = scored[arm]["projected"]
        left = by_sample(unprojected)
        right = by_sample(projected)
        entity_fields = ("slot_f1_exact_f1", "slu_f1_f1", "slu_f1_word_f1", "slu_f1_char_f1")
        entity_side_moved = sorted(
            sample_id
            for sample_id in ids_all
            if any(left[sample_id][field] != right[sample_id][field] for field in entity_fields)
        )
        projection = projected["aggregate"]["projection"]
        changed_ids = sorted(
            sample_id for sample_id in ids_all if right[sample_id].get("projected")
        )
        per_scenario_projected = collections.Counter(stratum_of(sid) for sid in changed_ids)
        landed_on_gold = sum(
            1
            for sample_id in changed_ids
            if right[sample_id]["scenario_action_exact"] == 1.0
        )
        tables[arm] = {
            "official_unprojected": official_block(unprojected),
            "official_projected": official_block(projected),
            "projection": {
                "projection_id": projection.get("projection_id"),
                "counts": projection.get("counts"),
                "map": projection.get("map"),
                "changed_rows": len(changed_ids),
                "changed_rows_pct": percent(len(changed_ids), len(ids_all)),
                "changed_rows_landing_on_gold_intent": landed_on_gold,
                "changed_rows_per_gold_scenario": dict(sorted(per_scenario_projected.items())),
            },
            "entity_side_rows_moved": entity_side_moved,
            "entity_side_invariant_holds": not entity_side_moved,
            "paired": {
                population: contrast_rows(left, right, ids, stratum_of)
                for population, ids in populations.items()
            },
            "weightings_intent": {
                population: {
                    "natural_unprojected_pct": round(
                        100.0 * mean(left[sid]["scenario_action_exact"] for sid in ids), 2
                    ),
                    "natural_projected_pct": round(
                        100.0 * mean(right[sid]["scenario_action_exact"] for sid in ids), 2
                    ),
                    "equal_stratum_unprojected_pct": round(
                        100.0
                        * mean(
                            mean(
                                left[sid]["scenario_action_exact"]
                                for sid in ids
                                if stratum_of(sid) == scenario
                            )
                            for scenario in sorted({stratum_of(sid) for sid in ids})
                        ),
                        2,
                    ),
                    "equal_stratum_projected_pct": round(
                        100.0
                        * mean(
                            mean(
                                right[sid]["scenario_action_exact"]
                                for sid in ids
                                if stratum_of(sid) == scenario
                            )
                            for scenario in sorted({stratum_of(sid) for sid in ids})
                        ),
                        2,
                    ),
                }
                for population, ids in populations.items()
            },
        }

    # ------------------------------------------------------------------
    # 7. Impossible-pair rate before and after, on the same sealed rows.
    # ------------------------------------------------------------------
    # An eligible row is changed by the projection if and only if its pair was
    # not one of the 60, and the projection always emits one of the 60, so
    # "changed" IS the impossible-pair count before and the rate after is zero
    # by construction. Both are re-derived from the emitted labels rather than
    # asserted, so a defect in the rule would show up here as a non-zero
    # residual instead of hiding behind its own bookkeeping.
    impossible: dict[str, dict] = {}
    for arm in arms:
        right = by_sample(scored[arm]["projected"])
        counts = scored[arm]["projected"]["aggregate"]["projection"]["counts"]
        residual = sum(
            1
            for sid in ids_all
            if right[sid].get("projected_to") is not None
            and tuple(str(right[sid]["projected_to"]).split("_", 1)) not in legal_pairs
        )
        impossible[arm] = {
            "eligible_rows": counts["eligible"],
            "ineligible_rows": counts["ineligible"],
            "impossible_pairs_before": counts["changed"],
            "impossible_pairs_before_pct": percent(counts["changed"], len(ids_all)),
            "impossible_pairs_after": 0,
            "residual_illegal_targets": residual,
        }

    # ------------------------------------------------------------------
    # 7b. What the residual actually IS, described. NOT part of the
    #     registered rule, NOT a metric, NOT a gate, and it changes no lock
    #     decision -- it exists because the registered rule is a legality
    #     repair and this says what the rows it repaired were actually doing
    #     wrong. Two descriptions, both reported whichever wins:
    #
    #     * EXCHANGE: the parsed pair becomes legal when its two halves swap;
    #     * ACTION-AS-SCENARIO: the parsed SCENARIO half is not a legal
    #       scenario but IS a legal ACTION name, so the row named the action
    #       in the scenario slot and a generic action beside it. The
    #       2026-09-05 closed-list verdict named this class by eye
    #       ("the model picking the action name as the scenario for
    #       recommendation_locations / recommendation_events"); this counts
    #       it, and prices what promoting it back would have recovered.
    #
    #     The promotion target is deterministic in the registered rule's own
    #     style: the scenario carrying that action with the larger TRAIN
    #     prior, ties alphabetically.
    # ------------------------------------------------------------------
    source_rows = {arm: rows_of(path) for arm, path in outputs_paths.items()}
    source_rows["KU-S1C-DRAFT"] = draft
    owners: dict[str, list[str]] = {}
    for scenario, actions in inventory.actions_by_scenario.items():
        for action in actions:
            owners.setdefault(action, []).append(scenario)
    swaps: dict[str, dict] = {}
    for arm in arms:
        right = by_sample(scored[arm]["projected"])
        changed = [sid for sid in ids_all if right[sid].get("projected")]
        parsed_by_id = {
            row["sample_id"]: parse_slu_response(row["text"]) for row in source_rows[arm]
        }
        reversed_legal = reversed_gold = 0
        action_as_scenario = promotion_gold = 0
        promotion_map: dict[str, list[int]] = {}
        for sample_id in changed:
            scenario, action, _entities, was_parsed = parsed_by_id[sample_id]
            if not was_parsed or scenario is None or action is None:
                continue
            record = gold[sample_id]
            if (action, scenario) in legal_pairs:
                reversed_legal += 1
                reversed_gold += (action, scenario) == (record.scenario, record.action)
            if scenario not in inventory.actions_by_scenario and scenario in owners:
                action_as_scenario += 1
                owner = min(
                    owners[scenario], key=lambda c: (-inventory.prior(c, scenario), c)
                )
                hit = (owner, scenario) == (record.scenario, record.action)
                promotion_gold += hit
                key = f"{scenario}/{action} -> {owner}_{scenario}"
                entry = promotion_map.setdefault(key, [0, 0])
                entry[0] += 1
                entry[1] += int(hit)
        swaps[arm] = {
            "changed_rows": len(changed),
            "landed_on_gold_under_the_registered_rule": sum(
                1 for sid in changed if right[sid]["scenario_action_exact"] == 1.0
            ),
            "exchange_is_legal": reversed_legal,
            "exchange_equals_gold": reversed_gold,
            "action_as_scenario_rows": action_as_scenario,
            "action_as_scenario_promotion_equals_gold": promotion_gold,
            "action_as_scenario_promotion_map": {
                key: {"rows": value[0], "gold": value[1]}
                for key, value in sorted(promotion_map.items())
            },
            "definition": (
                "among the rows the REGISTERED projection changed: 'exchange' counts those "
                "whose parsed pair becomes legal with its halves swapped; "
                "'action_as_scenario' counts those whose parsed scenario is not a legal "
                "scenario but IS a legal action name, and the promotion columns price what "
                "sending it back to its owning scenario would have recovered. Descriptive "
                "only -- no rule, no metric, no gate, no effect on the lock decision."
            ),
        }

    # ------------------------------------------------------------------
    # 8. The 42 KC-S1b fallback rows.
    # ------------------------------------------------------------------
    fallback = None
    prompt_fit_path = REPO / KC_S1B_PROMPT_FIT
    if prompt_fit_path.is_file():
        document = read_json(prompt_fit_path)
        fallback_ids = sorted(_collect_fallback_ids(document))
        right = by_sample(scored["CLOSED-LIST"]["projected"])
        left = by_sample(scored["CLOSED-LIST"]["unprojected"])
        legal_after = [sid for sid in fallback_ids if right[sid].get("projected")]
        gold_after = [sid for sid in legal_after if right[sid]["scenario_action_exact"] == 1.0]
        unparsed_still = [sid for sid in fallback_ids if not left[sid]["parsed"]]
        fallback = {
            "source": KC_S1B_PROMPT_FIT,
            "fallback_rows": len(fallback_ids),
            "rows_made_legal_by_the_projection": len(legal_after),
            "rows_landing_on_the_gold_intent": len(gold_after),
            "rows_still_unparsed": len(unparsed_still),
            "ids_made_legal": legal_after,
            "note": (
                "forward looking only: KC-S1b chose its per-intent TRAIN slot schema block "
                "from the SEALED closed-list response, so this says what a successor cell "
                "would have served, never what KC-S1b did serve. No KC-S1b number is "
                "restated because of it."
            ),
        }

    # ------------------------------------------------------------------
    # 9. The lock rule, applied exactly as preregistered.
    # ------------------------------------------------------------------
    lock_table = tables[LOCK_ARM]
    intent_old = lock_table["paired"]["old500"]["scenario_action_exact"]
    intent_new = lock_table["paired"]["new500"]["scenario_action_exact"]
    pooled = lock_table["paired"]["pooled_1000"]["scenario_action_exact"]
    worst_stratum = max(
        pooled["per_stratum"].items(), key=lambda item: item[1]["harms"], default=(None, {"harms": 0})
    )
    conditions = {
        "intent_delta_old500_non_negative": intent_old["delta_pp"] >= 0.0,
        "intent_delta_new500_non_negative": intent_new["delta_pp"] >= 0.0,
        "no_stratum_harmed_by_more_than_one_row": all(
            row["harms"] <= 1 for row in pooled["per_stratum"].values()
        ),
    }
    locked = all(conditions.values())

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
            "projection_id": SLURP_LABEL_PROJECTION_ID,
            "legal_intents": len(inventory.pairs),
            "legal_scenarios": len(inventory.scenarios),
            "actions_by_scenario": {
                scenario: list(actions)
                for scenario, actions in sorted(ontology.actions_by_scenario.items())
            },
            "train_prior_source": "data.slurp.load_slurp_intent_slot_schema(...).intents[*].n",
        },
        "scorers": {"unprojected": UNPROJECTED_SCORER, "projected": PROJECTED_SCORER},
        "statistics": {
            "resampler": "analysis.paired.paired_contrast",
            "n_replicates": N_REPLICATES,
            "seed": SEED,
            "ci_level": CI_LEVEL,
            "strata": "gold scenario",
            "delta_convention": "projected minus unprojected, on the same sealed rows",
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
        "preregistered_properties": {
            "devel_gold_intents_outside_the_train_pairs": len(gold_outside),
            "devel_gold_intent_rows_outside_the_train_pairs": gold_outside,
            "entity_side_invariant_holds_on_every_arm": all(
                table["entity_side_invariant_holds"] for table in tables.values()
            ),
            "entity_only_arms_untouched": {
                arm: tables[arm]["projection"]["changed_rows"] == 0 for arm in ENTITY_ONLY_ARMS
            },
        },
        "arms": tables,
        "impossible_pairs": impossible,
        "residual_swap_diagnostic": swaps,
        "kc_s1b_fallback_rows": fallback,
        "lock": {
            "arm": LOCK_ARM,
            "rule": (
                "re-lock as closed-list + projection iff the intent delta is >= 0 on BOTH "
                "OLD500 and NEW500 and no gold-scenario stratum is harmed on intent by more "
                "than 1 row"
            ),
            "conditions": conditions,
            "locked": locked,
            "intent_delta_pooled_pp": pooled["delta_pp"],
            "intent_delta_old500_pp": intent_old["delta_pp"],
            "intent_delta_new500_pp": intent_new["delta_pp"],
            "worst_stratum_intent_harms": {
                "stratum": worst_stratum[0],
                "harms": worst_stratum[1]["harms"],
            },
            "comparator_identity": {
                "run_id": ARMS[LOCK_ARM][0],
                "attempt_id": ARMS[LOCK_ARM][1],
                "run_manifest_sha256": manifests[LOCK_ARM]["sealed_manifest_sha256"],
                "outputs_sha256": manifests[LOCK_ARM]["outputs_sha256"],
                "scorer_id": PROJECTED_SCORER if locked else UNPROJECTED_SCORER,
                "projection_id": SLURP_LABEL_PROJECTION_ID if locked else None,
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
