"""Cell B8a: the model-free admission read of module M3 as a RUNTIME NODE.

Zero model, tokenizer, encoder, ASR, server and paid-API contacts. The only
scorer invocations are the registered model-free SLURP scorings, every one of
them over a COPY of a sealed ``outputs.jsonl`` written under this read's own
output root, or over the node's own replayed copy of such a file. No sealed
file is ever opened for writing, moved or renamed, and no run directory is
written.

WHAT THIS READS. Module M3 -- the SLURP USE projection v3 (the label rule
``R_action``, then the registered legal-label projection v2, then the filler
normalisation P2) -- has lived in the SCORER since item E4, where the
official, unprojected scorer credits none of it. Item E11 built the SAME rule
as a deterministic, zero-contact DELIVERY NODE
(``saea-deliver-normalise-v3`` in ``core.base.DELIVERY_NORMALISERS``), applied
once to the accepted answer immediately before delivery. Because the node is
pure and makes no contact, its ON arm over any sealed OFF arm is computable
from that arm's own bytes, so the admission is read offline
(``analysis.deliver_normaliser_replay``) rather than flown.

CONTRACT. The seven steps below are the recipe's own
``driver.contract`` in ``docs/readiness/2026-09-19-slurp-b8a-deliver-
normalise-v1/analysis-recipe-v1.json``, followed in order:

1. verify every sealed SHA-256 in the recipe by hashing the file before
   reading it;
2. copy each sealed ``outputs.jsonl`` to a caller-named working directory;
3. replay ``saea-deliver-normalise-v3`` over each copy via
   ``analysis.deliver_normaliser_replay.replay``, asserting ``model_calls: 0``
   and 1,080 rows in and out;
4. score OFF (the sealed scores, re-verified by hash) and ON (the replayed
   copy) with ``slurp-slu-official-train``, and both with
   ``slurp-slu-f1-normalized-v1-train``, over byte-identical COPIES of the
   sealed bundle -- never the sealed directory;
5. assert the STOP condition of the preregistration's section 8 before any
   contrast is computed;
6. emit the paired contrasts, the per-scenario tables and owner decision 17's
   diagnostic to the output root, in both weightings;
7. print aggregates only.

Step 4 is served by resolving the registered scorer through
``core.base.SCORERS`` and invoking it ONCE per arm-side over a byte-verified
copy -- which is exactly the invocation ``core.scoring_batch`` makes inside
its own job process (``core.scorers.score_bundle`` calls
``scorer_fn(bundle.outputs_path, lock, root)``), one complete score per
arm-side, never sharded. ``core.scoring_batch`` itself cannot be the runner
here: it scores a complete, bundle-verified run directory, and the node-ON
side of each arm is a replayed ``outputs.jsonl`` that has no run manifest and
no bundle. The precedent drivers below take the same path.

This driver is an adapted copy of two sealed precedent drivers, whose
estimator calls are reproduced byte for byte:

  analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/b5e_paired_read.py
    sha256 0f5a60a8eb15c2ae641718c817ea103d2b456a17dd94ba3a4c9ae63db737db59
  analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/b2_paired_read.py
    sha256 8f101c9ae5c07728ddcdd8af59a5cc375e5918dcc6fcbfc3dfb7773941393bba

The contrast layer, the per-scenario band, the scored-copy layer and the
per-type slot decomposition are the precedents'; only the arm list (three
OFF/ON pairs instead of five independent runs), the node stages (the replay,
the triple-equality assertion, the idempotence witness and the changed-row
decomposition) and the decision block are new. Every estimator invocation,
seed, draw count and interval level is the precedents':
``analysis.null_calibration_cli.rows_for`` reads the per-sample rows,
``analysis.null_calibration.pooled_f1`` pools the official count fields,
``analysis.paired.resampled_statistic`` bootstraps the pooled deltas and
``analysis.paired.paired_contrast`` the per-row means, saves/harms/ties and
the exact two-sided McNemar sign test. ``analysis.score_compare_cli`` is
deliberately not the runner: it hard-codes ci_level 0.90 and DEV population
names.

Authority, applied unchanged and never tuned:
  docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md
    (section 8: the metric list, the STOP condition, the resampling and the
     decision rule),
  docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/analysis-recipe-v1.json,
  docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/sealed-inputs-v1.json,
  owner decisions 7, 17, 23, 25 and directive 26 of
  docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, and
  owner decision 27 of 2026-09-19.

No utterance text, transcript, gold filler, prediction filler or model output
is ever printed or persisted by this driver: it reports counts, aggregate
numbers, entity-type names, scenario names, intent-branch names and content
hashes only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import bootstrap as bs
from .null_calibration import pooled_f1
from .null_calibration_cli import rows_for
from .paired import paired_contrast, resampled_statistic

RESULT_SCHEMA = "saea-b8a-delivery-node-read-v1"
RECIPE_ID = "SAEA-SLURP-B8A-DELIVER-NORMALISE-MODEL-FREE-READ-V1"

SEED = 20260915
DRAWS = 10_000
SCORER = "slurp-slu-official-train"
V3_SCORER = "slurp-slu-official-projected-v3-train"
SYM_SCORER = "slurp-slu-f1-normalized-v1-train"
NORMALISER_ID = "saea-deliver-normalise-v3"

PRECEDENT_DRIVERS = (
    {
        "path": "analysis/SAEA-SLURP-B5E-COMBINATION-PAIRED-ANALYSIS-V1/b5e_paired_read.py",
        "sha256": "0f5a60a8eb15c2ae641718c817ea103d2b456a17dd94ba3a4c9ae63db737db59",
        "role": (
            "cell B5e's driver; the contrast layer, the per-scenario band, the scored-copy "
            "layer and the per-type slot decomposition"
        ),
    },
    {
        "path": "analysis/SAEA-SLURP-B2-SAMPLES5-PAIRED-ANALYSIS-V1/b2_paired_read.py",
        "sha256": "8f101c9ae5c07728ddcdd8af59a5cc375e5918dcc6fcbfc3dfb7773941393bba",
        "role": "cell B2 v3's driver; the single-factor decision block and the STOP shape",
    },
)

# The TRAIN A own null measured by cell B0r on this exact roster and geometry.
# Registered in the B8a preregistration section 8; inputs here, never outputs.
H_SLU = 1.1218
H_INTENT = 1.0051

# The program bar. NOT a clause of this cell (preregistration section 8): the
# verdict states which base clears it as a fact, never as a claim.
BAR_SLU = 64.00
BAR_INTENT = 78.00

PER_ROW_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)
MICRO_METRICS = {
    "slu_f1_micro": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
    "span_f1_micro": (
        ("slot_f1_exact_tp",),
        ("slot_f1_exact_fp",),
        ("slot_f1_exact_fn",),
    ),
}
OFFICIAL_FIELD = {"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}

ARMS = ("anchor", "b1", "b5e")
GATING_ARMS = ("anchor", "b1")
ARM_LABELS = {
    "anchor": "the sealed dual-store anchor",
    "b1": "cell B1's recovery arm (module M1)",
    "b5e": "cell B5e's recovery arm (M1 + M4b)",
}
ARM_SHORT = {"anchor": "anchor", "b1": "B1", "b5e": "B5e"}
CONTRASTS = tuple(f"node_on_minus_off_{arm}" for arm in ARMS)
CONTRAST_OF_ARM = dict(zip(ARMS, CONTRASTS))
CONTRAST_NAMES = {
    "node_on_minus_off_anchor": "node ON minus OFF on the anchor base (GATING)",
    "node_on_minus_off_b1": "node ON minus OFF on the cell B1 base (GATING)",
    "node_on_minus_off_b5e": "node ON minus OFF on the cell B5e base (reported)",
}

ROSTER_REL = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
AUTHORITY_RELPATHS = (
    "docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1-preregistration.md",
    "docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/README.md",
    "docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/analysis-recipe-v1.json",
    "docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/sealed-inputs-v1.json",
    "docs/readiness/2026-09-19-slurp-b8a-deliver-normalise-v1/protocol-registered-v1.json",
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md",
    "docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md",
    "docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md",
    "docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md",
    "docs/results/2026-09-18-slurp-b1-twin-verdict.md",
    "docs/results/2026-09-18-slurp-b5e-combination-verdict.md",
)
IMPLEMENTATION_RELPATHS = (
    "src/speech_aware_evidence_acquisition/analysis/paired.py",
    "src/speech_aware_evidence_acquisition/analysis/bootstrap.py",
    "src/speech_aware_evidence_acquisition/analysis/null_calibration.py",
    "src/speech_aware_evidence_acquisition/analysis/null_calibration_cli.py",
    "src/speech_aware_evidence_acquisition/analysis/slurp_entity_attribution.py",
    "src/speech_aware_evidence_acquisition/analysis/deliver_normaliser_replay.py",
    "src/speech_aware_evidence_acquisition/rails/delivery_normalisers.py",
    "src/speech_aware_evidence_acquisition/rails/slurp_projection_v3.py",
    "src/speech_aware_evidence_acquisition/reproduction/slurp_scoring.py",
    "src/speech_aware_evidence_acquisition/reproduction/slurp_official_eval.py",
    "src/speech_aware_evidence_acquisition/core/scorers.py",
)


class B8aReadError(RuntimeError):
    """The read cannot proceed: a hash mismatch, a STOP failure, an overwrite."""


@dataclass(frozen=True)
class Context:
    """The three roots every path in this read resolves against."""

    repo_root: Path
    data_root: Path
    lock_path: Path
    output_dir: Path
    work_dir: Path
    recipe_path: Path


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def verified_json(path: Path, expected: str, label: str) -> dict:
    actual = digest(path)
    if actual != expected:
        raise B8aReadError(
            f"{label} hash mismatch: {path} is {actual}, expected {expected}"
        )
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_recipe(ctx: Context) -> dict:
    return json.loads(ctx.recipe_path.read_text(encoding="utf-8"))


def sealed_paths(ctx: Context, recipe: dict, arm: str) -> dict[str, Path]:
    spec = recipe["arms"][arm]
    return {
        "outputs": ctx.data_root / spec["outputs_relpath"],
        "scores": ctx.data_root / spec["scores_relpath"],
        "manifest": ctx.data_root / spec["run_manifest_relpath"],
    }


def verify_sealed_inputs(ctx: Context, recipe: dict) -> dict[str, dict]:
    """Contract step 1: hash every sealed input the recipe pins, before reading
    it. A mismatch stops the read."""

    verified: dict[str, dict] = {}
    for arm in ARMS:
        spec = recipe["arms"][arm]
        paths = sealed_paths(ctx, recipe, arm)
        scores = verified_json(paths["scores"], spec["scores_sha256"], f"{arm} scores")
        manifest = verified_json(
            paths["manifest"], spec["run_manifest_sha256"], f"{arm} run manifest"
        )
        outputs_sha = digest(paths["outputs"])
        if outputs_sha != spec["outputs_sha256"]:
            raise B8aReadError(
                f"{arm} outputs.jsonl hash mismatch: {outputs_sha}, expected "
                f"{spec['outputs_sha256']}"
            )
        if manifest.get("status") != "COMPLETED":
            raise B8aReadError(f"{arm} manifest is not COMPLETED")
        pin = manifest.get("scores") or {}
        if pin.get("sha256") != spec["scores_sha256"] or Path(
            pin.get("path", "")
        ) != paths["scores"]:
            raise B8aReadError(f"{arm} manifest does not pin the score bytes this read used")
        split = manifest.get("split") or {}
        if split.get("identity_hash") != spec["split_identity_hash"] or split.get(
            "role"
        ) != spec["split_role"]:
            raise B8aReadError(f"{arm} split identity or role does not match the recipe")
        projection = (scores[SCORER]["aggregate"].get("projection") or {})
        if projection.get("applied"):
            raise B8aReadError(f"{arm} sealed decision score carries a label projection")
        verified[arm] = {
            "spec": spec,
            "paths": paths,
            "outputs_sha256": outputs_sha,
            "scores": scores,
            "manifest": manifest,
            "split_ids": tuple(split.get("ids") or ()),
        }
        print(
            f"  verified {arm}: outputs {outputs_sha[:12]}, scores "
            f"{spec['scores_sha256'][:12]}, manifest COMPLETED",
            flush=True,
        )
    return verified


def roster_and_metadata(ctx: Context, recipe: dict):
    population = recipe["population"]
    roster_path = ctx.repo_root / population["roster"]["relpath"]
    roster = verified_json(roster_path, population["roster"]["sha256"], "roster")
    ids = sorted(item["id"] for item in roster["items"])
    if len(ids) != population["rows"] or len(set(ids)) != population["rows"]:
        raise B8aReadError(f"roster is not {population['rows']} unique ids")
    metadata_path = ctx.data_root / population["roster_metadata"]["relpath"]
    metadata = verified_json(
        metadata_path, population["roster_metadata"]["sha256"], "roster metadata"
    )["rows"]
    if set(metadata) != set(ids):
        raise B8aReadError("roster metadata does not cover the roster exactly")
    return roster, ids, metadata, roster_path, metadata_path


# --------------------------------------------------------------------------
# Contract steps 2 and 3: copy in, replay the node, never write a sealed file
# --------------------------------------------------------------------------


def off_copy_path(ctx: Context, recipe: dict, arm: str) -> Path:
    run_id = recipe["arms"][arm]["run_id"]
    return ctx.output_dir / "off" / run_id / Path(
        recipe["arms"][arm]["outputs_relpath"]
    ).name


def on_dir(ctx: Context, recipe: dict, arm: str) -> Path:
    return ctx.output_dir / "on" / recipe["arms"][arm]["run_id"]


def stage_replay(ctx: Context, cache: Path) -> None:
    """Steps 2 and 3, plus the node diagnostics the coordinator's brief adds:
    the triple-equality assertion, the idempotence witness, and the changed-row
    decomposition (label repairs, filler repairs, unparsed rows left verbatim,
    rendering-suppressed rows)."""

    from ..core.base import DELIVERY_NORMALISERS  # noqa: PLC0415
    from ..data.lock import load_lock  # noqa: PLC0415
    from ..rails import delivery_normalisers as _normalisers  # noqa: PLC0415, F401
    from ..rails.slurp_projection_v3 import (  # noqa: PLC0415
        normalize_filler_p2,
        project_slu_label_v3,
    )
    from ..reproduction.slurp_official_eval import (  # noqa: PLC0415
        load_legal_intent_inventory,
    )
    from ..reproduction.slurp_scoring import (  # noqa: PLC0415
        SlotEntity,
        parse_slu_response,
    )
    from .deliver_normaliser_replay import replay  # noqa: PLC0415

    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    _roster, ids, _metadata, _rp, _mp = roster_and_metadata(ctx, recipe)

    lock = load_lock(ctx.lock_path)
    inventory = load_legal_intent_inventory(lock, ctx.data_root)
    normaliser = DELIVERY_NORMALISERS.resolve(NORMALISER_ID)

    def scorer_side_triple(text: str):
        """The prediction triple the v3 SCORER hands the official evaluator for
        one row -- parse, then the v3 label rule, then P2 -- written in the
        scorer's own order and calling the scorer's own functions, exactly as
        ``tests/unit/test_deliver_normaliser_sealed_replay.py`` does."""

        scenario, action, entities, parsed = parse_slu_response(text)
        if parsed:
            outcome = project_slu_label_v3(scenario, action, inventory, parsed=parsed)
            scenario, action = outcome.scenario, outcome.action
        entities = tuple(
            SlotEntity(type=entity.type, filler=normalize_filler_p2(entity.filler))
            for entity in entities
        )
        return scenario, action, entities, parsed

    out: dict[str, dict] = {}
    for arm in ARMS:
        spec = recipe["arms"][arm]
        sealed = verified[arm]["paths"]["outputs"]
        copy = off_copy_path(ctx, recipe, arm)
        copy.parent.mkdir(parents=True, exist_ok=True)
        if not copy.exists():
            shutil.copyfile(sealed, copy)
        copy_sha = digest(copy)
        if copy_sha != verified[arm]["outputs_sha256"]:
            raise B8aReadError(f"{arm} OFF copy does not match the sealed bytes")

        target = on_dir(ctx, recipe, arm)
        provenance_path = target / "provenance.json"
        if provenance_path.exists():
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            print(f"  {arm}: reusing the existing replay", flush=True)
        else:
            started = time.time()
            provenance = replay(
                outputs_path=copy, normaliser_id=NORMALISER_ID, output_dir=target
            )
            print(f"  {arm}: replayed in {time.time() - started:.1f}s", flush=True)
        if digest(copy) != copy_sha:
            raise B8aReadError(f"{arm} OFF copy changed during the replay")
        if provenance["model_calls"] != 0:
            raise B8aReadError(f"{arm} replay reports a model call")
        if provenance["rows"] != recipe["population"]["rows"]:
            raise B8aReadError(f"{arm} replay did not return every row")
        if provenance["rows_already_normalised"] != 0:
            raise B8aReadError(f"{arm} sealed rows already carry a normalisation receipt")

        # Row accounting: 1,080 in, 1,080 out, the same ids, none invented.
        sealed_rows = []
        with copy.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    sealed_rows.append(json.loads(line))
        replayed = {}
        with (target / "outputs.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    replayed[row["sample_id"]] = row
        if len(sealed_rows) != len(replayed):
            raise B8aReadError(f"{arm} replay row count differs from the sealed input")
        if {row["sample_id"] for row in sealed_rows} != set(replayed) or set(
            replayed
        ) != set(ids):
            raise B8aReadError(f"{arm} replay does not cover the roster exactly")

        # Triple equality, the idempotence witness and the changed-row
        # decomposition, in one pass over the sealed rows.
        started = time.time()
        compared = mismatches = unparsed = 0
        changed = labels = fillers = suppressed = 0
        entities_filler_changed = 0
        non_fixed_points = 0
        branches: dict[str, int] = defaultdict(int)
        reasons: dict[str, int] = defaultdict(int)
        for row in sealed_rows:
            text = row["text"]
            outcome = normaliser(text, inventory=inventory)
            receipt = outcome.receipt
            if replayed[row["sample_id"]]["text"] != outcome.text:
                raise B8aReadError(
                    f"{arm} replay text differs from the node's own output on a row"
                )
            if receipt["applied"]:
                branches[str(receipt["label_branch"])] += 1
            else:
                reasons[str(receipt["reason"])] += 1
            changed += int(bool(outcome.changed))
            labels += int(receipt["labels_changed"] > 0)
            fillers += int(receipt["fillers_changed"] > 0)
            entities_filler_changed += int(receipt["fillers_changed"])
            suppressed += int(bool(receipt["rendering_suppressed"]))
            twice = normaliser(outcome.text, inventory=inventory)
            if twice.text != outcome.text:
                non_fixed_points += 1
            expected = scorer_side_triple(text)
            if not expected[3]:
                unparsed += 1
                if outcome.text != text or outcome.changed:
                    raise B8aReadError(
                        f"{arm} unparsed row was not delivered byte-identically"
                    )
                continue
            delivered = parse_slu_response(outcome.text)
            compared += 1
            if (
                delivered[3] is not True
                or delivered[0] != expected[0]
                or delivered[1] != expected[1]
                or tuple(delivered[2]) != expected[2]
            ):
                mismatches += 1
        print(
            f"  {arm}: triple equality {compared} parsed rows, {mismatches} mismatches, "
            f"{unparsed} unparsed; changed {changed}; idempotence non-fixed-points "
            f"{non_fixed_points} in {time.time() - started:.1f}s",
            flush=True,
        )
        if mismatches:
            raise B8aReadError(
                f"{arm}: the node's delivered triple differs from the v3 scorer's on "
                f"{mismatches} rows -- the read stops"
            )

        registered = spec["replay_counts"]
        counts = {
            "rows": provenance["rows"],
            "rows_changed": changed,
            "rows_label_changed": labels,
            "rows_filler_changed": fillers,
            "entities_filler_changed": entities_filler_changed,
            "rows_unparsed": unparsed,
            "rows_rendering_suppressed": suppressed,
        }
        counts_reproduction = {
            field: {
                "registered": value,
                "recomputed": counts[field],
                "reproduced": counts[field] == value,
            }
            for field, value in registered.items()
        }
        provenance_counts = {
            field: {
                "replay_provenance": provenance[field],
                "recomputed": counts[field],
                "agrees": provenance[field] == counts[field],
            }
            for field in (
                "rows",
                "rows_changed",
                "rows_label_changed",
                "rows_filler_changed",
                "entities_filler_changed",
                "rows_unparsed",
            )
        }
        registered_triple = spec["triple_equality"]
        out[arm] = {
            "run_id": spec["run_id"],
            "attempt_id": spec["attempt_id"],
            "role": spec["role"],
            "sealed_outputs_path": str(verified[arm]["paths"]["outputs"]),
            "sealed_outputs_sha256": verified[arm]["outputs_sha256"],
            "off_copy_path": str(copy),
            "off_copy_sha256": copy_sha,
            "on_outputs_path": str(target / "outputs.jsonl"),
            "on_outputs_sha256": digest(target / "outputs.jsonl"),
            "on_provenance_path": str(provenance_path),
            "on_provenance_sha256": digest(provenance_path),
            "replay_provenance": provenance,
            "changed_row_decomposition": counts,
            "changed_row_reproduction": counts_reproduction,
            "replay_provenance_agreement": provenance_counts,
            "label_branch_histogram": dict(sorted(branches.items())),
            "unparsed_reason_histogram": dict(sorted(reasons.items())),
            "triple_equality": {
                "definition": (
                    "on every parsed row, the prediction triple (scenario, action, "
                    "entities) parsed back out of the node's delivered text against the "
                    "triple the v3 SCORER builds from the same row; every unparsed row "
                    "must be delivered byte-identically"
                ),
                "parsed_rows_compared": compared,
                "mismatches": mismatches,
                "unparsed_rows_delivered_verbatim": unparsed,
                "registered_parsed_rows_compared": registered_triple[
                    "parsed_rows_compared"
                ],
                "registered_mismatches": registered_triple["mismatches"],
                "reproduces_the_registration": (
                    compared == registered_triple["parsed_rows_compared"]
                    and mismatches == registered_triple["mismatches"]
                ),
            },
            "idempotence": {
                "definition": (
                    "re-applying the node to its own output; I7n requires DETERMINISM, "
                    "not idempotence, and the read is unaffected because the scorer "
                    "applies P2 exactly once and so does the node"
                ),
                "rows": len(sealed_rows),
                "non_fixed_points": non_fixed_points,
                "fixed_points": len(sealed_rows) - non_fixed_points,
                "registered": spec["idempotence"],
            },
        }

    cache.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("replay cached ->", cache)


# --------------------------------------------------------------------------
# Contract step 4: one complete registered scoring per arm-side, over copies
# --------------------------------------------------------------------------


def _score_copy(scorer_id: str, outputs_copy: Path, result_path: Path, lock, root: Path):
    from ..core.base import SCORERS  # noqa: PLC0415

    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))[scorer_id]
        elapsed = 0.0
    else:
        scorer = SCORERS.resolve(scorer_id)
        started = time.time()
        result = scorer(outputs_copy, lock, root)
        elapsed = time.time() - started
        result_path.parent.mkdir(parents=True, exist_ok=True)
        with result_path.open("x", encoding="utf-8") as handle:
            json.dump({scorer_id: result}, handle, indent=2, sort_keys=True)
            handle.write("\n")
    aggregate = result["aggregate"]
    if aggregate.get("split_id") not in (None, "train"):
        raise B8aReadError(f"{scorer_id} did not resolve TRAIN gold for {outputs_copy}")
    if not aggregate["identity_check"]["passed"]:
        raise B8aReadError(f"{scorer_id} port/official identity check failed")
    return result, elapsed


def stage_score(ctx: Context, cache: Path) -> None:
    """OFF is the sealed score, re-verified by hash; ON is the replayed copy,
    scored once. Both sides are additionally read with the v3 scorer (whose
    NO-OP on the ON side is the node's own byte-level proof) and with the TRAIN
    symmetric sibling of owner decision 14."""

    from ..data.lock import load_lock  # noqa: PLC0415

    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    lock = load_lock(ctx.lock_path)

    out: dict[str, dict] = {}
    for arm in ARMS:
        spec = recipe["arms"][arm]
        off_copy = off_copy_path(ctx, recipe, arm)
        on_copy = on_dir(ctx, recipe, arm) / "outputs.jsonl"
        for side, copy in (("off", off_copy), ("on", on_copy)):
            if not copy.is_file():
                raise B8aReadError(f"{arm} {side} copy is missing: run the replay stage")
        entry: dict[str, dict] = {}

        # OFF official: the sealed score itself, re-verified by hash. No new
        # official invocation over the OFF side (the recipe's own step 4).
        entry["off"] = {
            SCORER: {
                "source": "the sealed scores.json, re-verified by hash",
                "scores_path": str(verified[arm]["paths"]["scores"]),
                "scores_sha256": spec["scores_sha256"],
                "aggregate": verified[arm]["scores"][SCORER]["aggregate"],
                "seconds": 0.0,
            }
        }
        for side, copy in (("off", off_copy), ("on", on_copy)):
            side_entry = entry.setdefault(side, {})
            scorers = (V3_SCORER, SYM_SCORER) if side == "off" else (
                SCORER,
                V3_SCORER,
                SYM_SCORER,
            )
            for scorer_id in scorers:
                result_path = copy.parent / f"{scorer_id}-scores.json"
                result, elapsed = _score_copy(
                    scorer_id, copy, result_path, lock, ctx.data_root
                )
                aggregate = result["aggregate"]
                side_entry[scorer_id] = {
                    "source": f"the {side.upper()} copy under this read's output root",
                    "outputs_path": str(copy),
                    "outputs_sha256": digest(copy),
                    "scores_path": str(result_path),
                    "scores_sha256": digest(result_path),
                    "aggregate": aggregate,
                    "seconds": elapsed,
                }
                print(
                    f"  {arm} {side} {scorer_id}: slu_f1 "
                    f"{100 * float(aggregate['official']['slu_f1']):.4f} in "
                    f"{elapsed:.1f}s",
                    flush=True,
                )
        out[arm] = entry

    cache.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("scores cached ->", cache)


# --------------------------------------------------------------------------
# Contract step 5: the STOP condition, asserted before any contrast is built
# --------------------------------------------------------------------------


def _close(got: float, want: float, tol: float = 0.005) -> bool:
    return abs(got - want) <= tol + 1e-9


def stop_condition(recipe: dict, scored: dict, replay_cache: dict, ids) -> dict:
    """Preregistration section 8's three clauses, to the hundredth of a point."""

    expected = recipe["arms"]
    checks: dict[str, dict] = {}
    for arm in ARMS:
        off = scored[arm]["off"][SCORER]["aggregate"]["official"]
        on = scored[arm]["on"][SCORER]["aggregate"]["official"]
        for field, key in (("slu_f1", "pooled_slu_f1"), ("intent_accuracy", "intent")):
            want_off = expected[arm]["official_aggregate"][key]
            got_off = 100 * float(off[field])
            checks[f"{arm}.off.{field}"] = {
                "registered": want_off,
                "recomputed": got_off,
                "reproduced": _close(got_off, want_off),
            }
            want_on = expected[arm]["projection_v3_aggregate"][key]
            got_on = 100 * float(on[field])
            checks[f"{arm}.on.{field}"] = {
                "registered": want_on,
                "recomputed": got_on,
                "reproduced": _close(got_on, want_on),
            }
        rows = replay_cache[arm]["replay_provenance"]["rows"]
        checks[f"{arm}.rows"] = {
            "registered": recipe["population"]["rows"],
            "recomputed": rows,
            "reproduced": rows == recipe["population"]["rows"] == len(ids),
        }
        # The registered v3 SCORER over the OFF copy re-derives the same
        # projected numbers a second way, and over the ON copy it must be a
        # NO-OP: the node already performed the rule.
        off_v3 = scored[arm]["off"][V3_SCORER]["aggregate"]["official"]
        on_v3 = scored[arm]["on"][V3_SCORER]["aggregate"]["official"]
        for field, key in (("slu_f1", "pooled_slu_f1"), ("intent_accuracy", "intent")):
            want = expected[arm]["projection_v3_aggregate"][key]
            got = 100 * float(off_v3[field])
            checks[f"{arm}.off_v3_scorer.{field}"] = {
                "registered": want,
                "recomputed": got,
                "reproduced": _close(got, want),
            }
            got_on_v3 = 100 * float(on_v3[field])
            checks[f"{arm}.on_v3_scorer_is_a_no_op.{field}"] = {
                "registered": 100 * float(on[field]),
                "recomputed": got_on_v3,
                "reproduced": abs(got_on_v3 - 100 * float(on[field])) < 1e-9,
            }
    failures = [name for name, row in checks.items() if not row["reproduced"]]
    return {
        "definition": recipe["decision_rule"]["stop_condition"],
        "tolerance": "|recomputed - registered| <= 0.005 pp (the hundredth of a point)",
        "checks": checks,
        "failures": failures,
        "passed": not failures,
    }


# --------------------------------------------------------------------------
# The contrast layer -- the precedents' estimator calls, unchanged
# --------------------------------------------------------------------------


def percentiles(replicates, level: float) -> list[float]:
    tail = (1.0 - level) / 2.0
    ordered = sorted(replicates)
    return [100 * bs._percentile(ordered, tail), 100 * bs._percentile(ordered, 1.0 - tail)]


def interval_block(result, resampling: str) -> dict:
    ci95 = percentiles(result.replicates, 0.95)
    ci90 = percentiles(result.replicates, 0.90)
    return {
        "resampling": resampling,
        "point_estimate_pp": 100 * result.point_estimate,
        "sigma_hat_pp": 100 * result.sigma_hat,
        "ci95_pp": ci95,
        "ci95_half_width_pp": (ci95[1] - ci95[0]) / 2.0,
        "ci90_pp": ci90,
        "ci90_half_width_pp": (ci90[1] - ci90[0]) / 2.0,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
    }


def population_block(ids, metadata, roster, scenarios, speakers, recipe) -> dict:
    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    population = recipe["population"]
    return {
        "rows": len(ids),
        "roster_id": roster.get("roster_id", population["roster"]["roster_id"]),
        "roster_path": population["roster"]["relpath"],
        "roster_sha256": population["roster"]["sha256"],
        "scenarios": len(scenarios),
        "speakers": len(speakers),
        "expected_speakers": population["speaker_clusters"],
        "headset_rows": sum(1 for sid in ids if metadata[sid]["headset"]),
        "far_field_rows": sum(1 for sid in ids if not metadata[sid]["headset"]),
        "split_identity_hash": recipe["arms"]["anchor"]["split_identity_hash"],
        "split_role": recipe["arms"]["anchor"]["split_role"],
        "rows_per_scenario": sorted(
            {sum(1 for s in ids if scenario_of(s) == c) for c in scenarios}
        ),
    }


def contrast_block(
    name: str,
    left_key: str,
    right_key: str,
    rows: dict,
    labels: dict,
    ids,
    cluster_of,
    scenario_of,
    scenarios,
    row_counts: dict,
    *,
    stratified: bool = True,
) -> dict:
    left, right = rows[left_key], rows[right_key]
    block: dict[str, object] = {
        "contrast": {
            "id": name,
            "left": labels[left_key],
            "right": labels[right_key],
            "sign": (
                f"delta = {labels[right_key]} minus {labels[left_key]}; "
                "negative means the right arm is worse"
            ),
        },
        "row_counts": {
            "left": row_counts[left_key],
            "right": row_counts[right_key],
            "both_parsed": sum(
                1 for sid in ids if left[sid]["parsed"] == 1.0 and right[sid]["parsed"] == 1.0
            ),
        },
    }

    pooled: dict[str, dict] = {}
    for micro, groups in MICRO_METRICS.items():
        started = time.time()

        def statistic(resampled, groups=groups, left=left, right=right):
            return pooled_f1(right, resampled, groups) - pooled_f1(left, resampled, groups)

        clustered = resampled_statistic(
            sample_ids=ids,
            statistic=statistic,
            seed=SEED,
            n_replicates=DRAWS,
            ci_level=0.95,
            cluster_of=cluster_of,
        )
        entry = {
            "estimand": "pooled-count-f1",
            "direction": f"right({right_key})-minus-left({left_key})",
            "fields": {"tp": list(groups[0]), "fp": list(groups[1]), "fn": list(groups[2])},
            "left_pct": 100 * pooled_f1(left, ids, groups),
            "right_pct": 100 * pooled_f1(right, ids, groups),
            "delta_pp": 100 * statistic(ids),
            "speaker_clustered": interval_block(
                clustered, "paired whole-speaker cluster bootstrap"
            ),
        }
        if stratified:
            strat = resampled_statistic(
                sample_ids=ids,
                statistic=statistic,
                seed=SEED,
                n_replicates=DRAWS,
                ci_level=0.95,
                strata_of=scenario_of,
            )
            entry["scenario_stratified"] = interval_block(
                strat, "paired scenario-stratified row bootstrap"
            )
        per_scenario = {}
        for scenario in scenarios:
            members = [sid for sid in ids if scenario_of(sid) == scenario]
            lv = pooled_f1(left, members, groups)
            rv = pooled_f1(right, members, groups)
            per_scenario[scenario] = {
                "n": len(members),
                "left_pct": 100 * lv,
                "right_pct": 100 * rv,
                "delta_pp": 100 * (rv - lv),
            }
        entry["per_scenario"] = per_scenario
        entry["equal_scenario_delta_pp"] = sum(
            item["delta_pp"] for item in per_scenario.values()
        ) / len(per_scenario)
        pooled[micro] = entry
        print(f"  [{name}] pooled {micro} in {time.time() - started:.1f}s", flush=True)
    block["pooled_micro"] = pooled

    started = time.time()
    clustered_rows = paired_contrast(
        left,
        right,
        metrics=PER_ROW_METRICS,
        sample_ids=ids,
        cluster_of=cluster_of,
        seed=SEED,
        n_replicates=DRAWS,
        ci_level=0.95,
    )
    stratified_rows = None
    if stratified:
        stratified_rows = paired_contrast(
            left,
            right,
            metrics=PER_ROW_METRICS,
            sample_ids=ids,
            strata_of=scenario_of,
            seed=SEED,
            n_replicates=DRAWS,
            ci_level=0.95,
        )
    per_row: dict[str, dict] = {}
    for metric in PER_ROW_METRICS:
        contrast = clustered_rows[metric]
        entry = {
            "estimand": "mean-per-row",
            "direction": f"right({right_key})-minus-left({left_key})",
            "n": contrast.n,
            "left_pct": 100 * contrast.left_mean,
            "right_pct": 100 * contrast.right_mean,
            "delta_pp": 100 * contrast.delta,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "sign_test": "exact two-sided McNemar binomial on saves vs harms",
            "sign_test_p": contrast.sign_test_p,
            "speaker_clustered": interval_block(
                contrast.bootstrap, "paired whole-speaker cluster bootstrap"
            ),
        }
        if stratified_rows is not None:
            strat = stratified_rows[metric]
            entry["scenario_stratified"] = interval_block(
                strat.bootstrap, "paired scenario-stratified row bootstrap"
            )
            per_scenario = {
                name_: {
                    "n": row.n,
                    "left_pct": 100 * row.left_mean,
                    "right_pct": 100 * row.right_mean,
                    "delta_pp": 100 * row.delta,
                    "saves": row.saves,
                    "harms": row.harms,
                    "ties": row.ties,
                }
                for name_, row in strat.per_stratum.items()
            }
        else:
            per_scenario = {}
            for scenario in scenarios:
                members = [sid for sid in ids if scenario_of(sid) == scenario]
                lvals = [left[sid][metric] for sid in members]
                rvals = [right[sid][metric] for sid in members]
                saves = sum(1 for lv, rv in zip(lvals, rvals) if rv > lv)
                harms = sum(1 for lv, rv in zip(lvals, rvals) if rv < lv)
                per_scenario[scenario] = {
                    "n": len(members),
                    "left_pct": 100 * sum(lvals) / len(members),
                    "right_pct": 100 * sum(rvals) / len(members),
                    "delta_pp": 100 * (sum(rvals) - sum(lvals)) / len(members),
                    "saves": saves,
                    "harms": harms,
                    "ties": len(members) - saves - harms,
                }
        entry["per_scenario"] = per_scenario
        entry["equal_scenario_delta_pp"] = sum(
            item["delta_pp"] for item in per_scenario.values()
        ) / len(per_scenario)
        per_row[metric] = entry
    block["per_row"] = per_row
    print(f"  [{name}] per-row metrics in {time.time() - started:.1f}s", flush=True)
    return block


def _side_documents(ctx: Context, recipe: dict, scored: dict, verified: dict, scorer_id: str):
    """Wrap each arm-side's score document for ``rows_for``."""

    documents: dict[str, dict] = {}
    for arm in ARMS:
        for side in ("off", "on"):
            entry = scored[arm][side][scorer_id]
            if side == "off" and scorer_id == SCORER:
                scores = verified[arm]["scores"]
            else:
                scores = json.loads(
                    Path(entry["scores_path"]).read_text(encoding="utf-8")
                )
            documents[f"{arm}:{side}"] = {
                "verified": True,
                "manifest": entry.get("scores_path", entry.get("scores_path", "")),
                "scores": scores,
            }
    return documents


def _arm_labels(recipe: dict) -> dict[str, str]:
    labels = {}
    for arm in ARMS:
        run_id = recipe["arms"][arm]["run_id"]
        labels[f"{arm}:off"] = f"{ARM_LABELS[arm]} OFF, the sealed bytes ({run_id})"
        labels[f"{arm}:on"] = (
            f"{ARM_LABELS[arm]} ON, the same rows after {NORMALISER_ID} ({run_id})"
        )
    return labels


def stage_contrasts(ctx: Context, scores_cache: Path, replay_cache: Path, cache: Path) -> None:
    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    scored = json.loads(scores_cache.read_text(encoding="utf-8"))
    replayed = json.loads(replay_cache.read_text(encoding="utf-8"))
    roster, ids, metadata, roster_path, metadata_path = roster_and_metadata(ctx, recipe)

    stop = stop_condition(recipe, scored, replayed, ids)
    if not stop["passed"]:
        raise B8aReadError(
            "STOP condition failed before any contrast was computed: "
            + ", ".join(stop["failures"])
        )
    print("  STOP: every registered OFF and ON aggregate reproduces", flush=True)

    fields = tuple(
        sorted(
            set(PER_ROW_METRICS)
            | {name for groups in MICRO_METRICS.values() for group in groups for name in group}
            | {"parsed"}
        )
    )
    documents = _side_documents(ctx, recipe, scored, verified, SCORER)
    rows = {key: rows_for(documents[key], SCORER, fields) for key in documents}
    for key in rows:
        if set(rows[key]) != set(ids):
            raise B8aReadError(f"{key} score rows do not equal the roster")
    for arm in ARMS:
        if set(verified[arm]["split_ids"]) != set(ids):
            raise B8aReadError(f"{arm} manifest split ids do not equal the roster")

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    scenarios = sorted({scenario_of(sid) for sid in ids})
    speakers = sorted({cluster_of(sid) for sid in ids})
    population = population_block(ids, metadata, roster, scenarios, speakers, recipe)

    consistency: dict[str, dict] = {}
    for key in rows:
        arm, side = key.split(":")
        aggregate = scored[arm][side][SCORER]["aggregate"]["official"]
        for micro, groups in MICRO_METRICS.items():
            recomputed = pooled_f1(rows[key], ids, groups)
            official = float(aggregate[OFFICIAL_FIELD[micro]])
            consistency[f"{key}.{micro}"] = {
                "official_field": f"{SCORER}.aggregate.official.{OFFICIAL_FIELD[micro]}",
                "recomputed_pooled_f1": recomputed,
                "official_aggregate": official,
                "abs_diff": abs(recomputed - official),
                "matches_1e-6": abs(recomputed - official) < 1e-6,
            }
    if not all(entry["matches_1e-6"] for entry in consistency.values()):
        raise B8aReadError("pooled_f1 does not reproduce an arm-side's official aggregate")

    row_counts = {
        key: {
            "scored_rows": len(rows[key]),
            "parsed_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] == 1.0),
            "malformed_retained_rows": sum(
                1 for sid in ids if rows[key][sid]["parsed"] != 1.0
            ),
        }
        for key in rows
    }

    labels = _arm_labels(recipe)
    comparisons: dict[str, dict] = {}
    for arm in ARMS:
        name = CONTRAST_OF_ARM[arm]
        comparisons[name] = contrast_block(
            name,
            f"{arm}:off",
            f"{arm}:on",
            rows,
            labels,
            ids,
            cluster_of,
            scenario_of,
            scenarios,
            row_counts,
        )

    payload = {
        "population": population,
        "consistency_check": consistency,
        "stop_condition": stop,
        "row_counts": row_counts,
        "comparisons": comparisons,
        "roster_path": str(roster_path),
        "metadata_path": str(metadata_path),
    }
    cache.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("contrasts cached ->", cache)


def stage_band(ctx: Context, scores_cache: Path, cache: Path) -> None:
    """Each scenario's own paired intent delta with its own CI95 from the same
    paired whole-speaker cluster bootstrap restricted to that scenario's rows,
    plus owner decision 17's net-harmed-rows diagnostic (flagged at five or
    more)."""

    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    scored = json.loads(scores_cache.read_text(encoding="utf-8"))
    _roster, ids, metadata, _rp, _mp = roster_and_metadata(ctx, recipe)

    fields = ("scenario_action_exact", "parsed")
    documents = _side_documents(ctx, recipe, scored, verified, SCORER)
    rows = {key: rows_for(documents[key], SCORER, fields) for key in documents}

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    scenarios = sorted({metadata[sid]["scenario"] for sid in ids})
    out: dict[str, dict] = {}
    for arm in ARMS:
        name = CONTRAST_OF_ARM[arm]
        per_scenario = {}
        for scenario in scenarios:
            members = sorted(sid for sid in ids if metadata[sid]["scenario"] == scenario)
            contrast = paired_contrast(
                rows[f"{arm}:off"],
                rows[f"{arm}:on"],
                metrics=("scenario_action_exact",),
                sample_ids=members,
                cluster_of=cluster_of,
                seed=SEED,
                n_replicates=DRAWS,
                ci_level=0.95,
            )["scenario_action_exact"]
            interval = interval_block(
                contrast.bootstrap,
                "paired whole-speaker cluster bootstrap within the scenario",
            )
            net_harmed = contrast.harms - contrast.saves
            per_scenario[scenario] = {
                "n": contrast.n,
                "clusters": len({cluster_of(sid) for sid in members}),
                "left_pct": 100 * contrast.left_mean,
                "right_pct": 100 * contrast.right_mean,
                "delta_pp": 100 * contrast.delta,
                "saves": contrast.saves,
                "harms": contrast.harms,
                "ties": contrast.ties,
                "net_harmed_rows": net_harmed,
                "decision_17_flag": net_harmed >= 5,
                "sign_test_p": contrast.sign_test_p,
                "ci95_pp": interval["ci95_pp"],
                "ci90_pp": interval["ci90_pp"],
                "ci95_upper_below_zero": interval["ci95_pp"][1] < 0.0,
                "interval": interval,
            }
        breached = sorted(k for k, v in per_scenario.items() if v["ci95_upper_below_zero"])
        flagged = sorted(k for k, v in per_scenario.items() if v["decision_17_flag"])
        out[name] = {
            "definition": (
                "a scenario loses intent beyond the null band when the CI95 upper bound of "
                "that scenario's own paired intent delta is below zero (preregistration "
                "section 8 clause 3, fixed before contact)"
            ),
            "decision_17_definition": (
                "owner decision 17 of 2026-09-17: report the net harmed rows per scenario "
                "(harms minus saves) and flag any scenario at five or more; a diagnostic, "
                "never a gate"
            ),
            "per_scenario": per_scenario,
            "scenarios_losing_beyond_the_band": breached,
            "band_breached": bool(breached),
            "decision_17_flagged_scenarios": flagged,
        }
        print(
            f"  [{name}] scenario band: {len(breached)} breaching, "
            f"{len(flagged)} decision-17 flagged",
            flush=True,
        )
    cache.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("band cached ->", cache)


def stage_symcontrasts(ctx: Context, scores_cache: Path, cache: Path) -> None:
    """Owner decision 14's TRAIN symmetric sibling, ON minus OFF, reported
    beside every official delta and never a gate."""

    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    scored = json.loads(scores_cache.read_text(encoding="utf-8"))
    _roster, ids, metadata, _rp, _mp = roster_and_metadata(ctx, recipe)

    fields = tuple(
        sorted(
            set(PER_ROW_METRICS)
            | {name for groups in MICRO_METRICS.values() for group in groups for name in group}
            | {"parsed"}
        )
    )
    documents = _side_documents(ctx, recipe, scored, verified, SYM_SCORER)
    rows = {key: rows_for(documents[key], SYM_SCORER, fields) for key in documents}

    def cluster_of(sid: str) -> str:
        return metadata[sid]["speaker"]

    def scenario_of(sid: str) -> str:
        return metadata[sid]["scenario"]

    scenarios = sorted({scenario_of(sid) for sid in ids})
    consistency: dict[str, dict] = {}
    for key in rows:
        arm, side = key.split(":")
        aggregate = scored[arm][side][SYM_SCORER]["aggregate"]["normalized"]["micro"]
        for micro, groups in MICRO_METRICS.items():
            recomputed = pooled_f1(rows[key], ids, groups)
            declared = float(aggregate[OFFICIAL_FIELD[micro]])
            consistency[f"{key}.{micro}"] = {
                "recomputed_pooled_f1": recomputed,
                "declared_aggregate": declared,
                "abs_diff": abs(recomputed - declared),
                "matches_1e-6": abs(recomputed - declared) < 1e-6,
            }
    failed = [name for name, block in consistency.items() if not block["matches_1e-6"]]
    if failed:
        raise B8aReadError(
            "the symmetric pooled rows disagree with the aggregate: " + ", ".join(failed)
        )

    row_counts = {
        key: {
            "scored_rows": len(rows[key]),
            "parsed_rows": sum(1 for sid in ids if rows[key][sid]["parsed"] == 1.0),
            "malformed_retained_rows": sum(
                1 for sid in ids if rows[key][sid]["parsed"] != 1.0
            ),
        }
        for key in rows
    }
    labels = _arm_labels(recipe)
    comparisons: dict[str, dict] = {}
    for arm in ARMS:
        name = CONTRAST_OF_ARM[arm]
        comparisons[name] = contrast_block(
            name,
            f"{arm}:off",
            f"{arm}:on",
            rows,
            labels,
            ids,
            cluster_of,
            scenario_of,
            scenarios,
            row_counts,
            stratified=False,
        )
    payload = {
        "scorer_id": SYM_SCORER,
        "view": "symmetric",
        "owner_decision": (
            "owner decision 14 of 2026-09-17 registered the TRAIN sibling; owner decision 7 "
            "requires it beside every official number; it is never a gate"
        ),
        "consistency_check": consistency,
        "row_counts": row_counts,
        "comparisons": comparisons,
    }
    cache.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("symmetric contrasts cached ->", cache)


# --------------------------------------------------------------------------
# FN / FP mass by slot type, before and after the node
# --------------------------------------------------------------------------


def _entity_rows(ctx: Context, outputs_path: Path, per_sample: Mapping[str, Mapping], ids, gold_by_id):
    """Per-row, per-type entity behaviour of one arm-side, from its own
    ``outputs.jsonl``.

    The matching is the official scorer's own: ``_match_block`` is the exact
    greedy same-type distance match the official SpanDistanceFMeasure performs,
    and ``_exact_counts`` the exact SpanFMeasure one. Nothing is scored anew --
    the reconstruction is verified against that side's own official count
    fields row by row before any table is built.
    """

    from ..reproduction.slurp_scoring import (  # noqa: PLC0415
        _char_distance,
        _word_distance,
        parse_slu_response,
    )
    from .slurp_entity_attribution import _match_block  # noqa: PLC0415

    predicted: dict[str, list] = {}
    parsed_flag: dict[str, bool] = {}
    with Path(outputs_path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            _scenario, _action, entities, ok = parse_slu_response(row["text"])
            predicted[row["sample_id"]] = list(entities)
            parsed_flag[row["sample_id"]] = bool(ok)
    if set(predicted) != set(ids):
        raise B8aReadError(f"{outputs_path} does not cover the roster exactly")

    per_row = {}
    for sid in ids:
        gold = gold_by_id[sid]
        pred = predicted[sid]
        wmatched, wunmatched, wleft, wcounts = _match_block(gold, pred, _word_distance)
        cmatched, cunmatched, cleft, ccounts = _match_block(gold, pred, _char_distance)
        o = per_sample[sid]
        for field, value in zip(
            ("slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn"), wcounts
        ):
            if abs(float(o[field]) - value) > 1e-6:
                raise B8aReadError(f"{outputs_path} {sid} {field} does not reconstruct")
        for field, value in zip(
            ("slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn"), ccounts
        ):
            if abs(float(o[field]) - value) > 1e-6:
                raise B8aReadError(f"{outputs_path} {sid} {field} does not reconstruct")
        per_row[sid] = {
            "gold": gold,
            "predicted": pred,
            "word": (wmatched, wunmatched, wleft),
            "char": (cmatched, cunmatched, cleft),
            "parsed": parsed_flag[sid],
            "intent_correct": bool(o["scenario_action_exact"]),
        }
    return per_row


def _type_tables(per_row, ids):
    """Aggregate one arm-side's per-row entity behaviour into per-type tables."""

    from ..reproduction.slurp_scoring import _exact_counts  # noqa: PLC0415

    empty = {
        "gold_mentions": 0, "predicted_mentions": 0,
        "exact": 0, "different_filler": 0, "omitted": 0, "spurious": 0,
        "rows_with_gold": 0, "rows_omit_entirely": 0, "rows_all_exact": 0,
        "rows_partial_or_different": 0, "rows_spurious_only": 0,
        "rows_omit_entirely_and_intent_correct": 0,
        "word_distance_sum": 0.0, "char_distance_sum": 0.0,
        "slu_tp": 0.0, "slu_fp": 0.0, "slu_fn": 0.0,
        "exact_tp": 0.0, "exact_fp": 0.0, "exact_fn": 0.0,
    }
    totals = defaultdict(lambda: dict(empty))
    for sid in ids:
        row = per_row[sid]
        wmatched, wunmatched, wleft = row["word"]
        cmatched, cunmatched, cleft = row["char"]
        types: dict[str, dict] = {}

        def bucket(name):
            return types.setdefault(
                name,
                {"gold_mentions": 0, "predicted_mentions": 0, "exact": 0,
                 "different_filler": 0, "omitted": 0, "spurious": 0,
                 "word_distance_sum": 0.0, "char_distance_sum": 0.0,
                 "slu_tp": 0.0, "slu_fp": 0.0, "slu_fn": 0.0,
                 "exact_tp": 0.0, "exact_fp": 0.0, "exact_fn": 0.0},
            )

        for typ, gold_filler, pred_filler, distance in wmatched:
            b = bucket(typ)
            b["exact" if gold_filler == pred_filler else "different_filler"] += 1
            b["word_distance_sum"] += float(distance)
            b["slu_tp"] += 1.0
            b["slu_fp"] += float(distance)
            b["slu_fn"] += float(distance)
        for typ, _gf, _pf, distance in cmatched:
            b = bucket(typ)
            b["char_distance_sum"] += float(distance)
            b["slu_tp"] += 1.0
            b["slu_fp"] += float(distance)
            b["slu_fn"] += float(distance)
        for typ, _f in wleft:
            b = bucket(typ)
            b["omitted"] += 1
            b["slu_fn"] += 1.0
        for typ, _f in cleft:
            bucket(typ)["slu_fn"] += 1.0
        for typ, _f in wunmatched:
            b = bucket(typ)
            b["spurious"] += 1
            b["slu_fp"] += 1.0
        for typ, _f in cunmatched:
            bucket(typ)["slu_fp"] += 1.0
        for entity in row["gold"]:
            bucket(entity.type)["gold_mentions"] += 1
        for entity in row["predicted"]:
            bucket(entity.type)["predicted_mentions"] += 1
        for typ in types:
            g = [e for e in row["gold"] if e.type == typ]
            p = [e for e in row["predicted"] if e.type == typ]
            tp, fp, fn = _exact_counts(g, p)
            b = types[typ]
            b["exact_tp"] += tp
            b["exact_fp"] += fp
            b["exact_fn"] += fn

        for typ, b in types.items():
            agg = totals[typ]
            for field in ("gold_mentions", "predicted_mentions", "exact", "different_filler",
                          "omitted", "spurious", "word_distance_sum", "char_distance_sum",
                          "slu_tp", "slu_fp", "slu_fn", "exact_tp", "exact_fp", "exact_fn"):
                agg[field] += b[field]
            if b["gold_mentions"]:
                agg["rows_with_gold"] += 1
                if b["predicted_mentions"] == 0:
                    agg["rows_omit_entirely"] += 1
                    if row["intent_correct"]:
                        agg["rows_omit_entirely_and_intent_correct"] += 1
                elif b["exact"] == b["gold_mentions"]:
                    agg["rows_all_exact"] += 1
                else:
                    agg["rows_partial_or_different"] += 1
            elif b["predicted_mentions"]:
                agg["rows_spurious_only"] += 1
    return {k: dict(v) for k, v in totals.items()}


def stage_slot(ctx: Context, scores_cache: Path, cache: Path) -> None:
    from ..data.lock import load_lock  # noqa: PLC0415
    from ..data.slurp import load_slurp_train_construction_rows  # noqa: PLC0415
    from ..reproduction.slurp_scoring import SlotEntity  # noqa: PLC0415

    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    scored = json.loads(scores_cache.read_text(encoding="utf-8"))
    _roster, ids, _metadata, _rp, _mp = roster_and_metadata(ctx, recipe)

    lock = load_lock(ctx.lock_path)
    refs = load_slurp_train_construction_rows(lock, ctx.data_root, ids)
    gold_by_id = {sid: [SlotEntity(t, f) for t, f in refs[sid]["entities"]] for sid in ids}
    del refs

    tables: dict[str, dict] = {}
    closure: dict[str, dict] = {}
    for arm in ARMS:
        for side in ("off", "on"):
            key = f"{arm}:{side}"
            if side == "off":
                outputs = off_copy_path(ctx, recipe, arm)
                scores = verified[arm]["scores"]
            else:
                outputs = on_dir(ctx, recipe, arm) / "outputs.jsonl"
                scores = json.loads(
                    Path(scored[arm][side][SCORER]["scores_path"]).read_text(
                        encoding="utf-8"
                    )
                )
            per_sample = {r["sample_id"]: r for r in scores[SCORER]["per_sample"]}
            started = time.time()
            per_row = _entity_rows(ctx, outputs, per_sample, ids, gold_by_id)
            tables[key] = _type_tables(per_row, ids)
            del per_row
            raw = scores[SCORER]["aggregate"]["official"]["raw"]
            summed = {
                "slu_tp": sum(v["slu_tp"] for v in tables[key].values()),
                "slu_fp": sum(v["slu_fp"] for v in tables[key].values()),
                "slu_fn": sum(v["slu_fn"] for v in tables[key].values()),
                "exact_tp": sum(v["exact_tp"] for v in tables[key].values()),
                "exact_fp": sum(v["exact_fp"] for v in tables[key].values()),
                "exact_fn": sum(v["exact_fn"] for v in tables[key].values()),
            }
            official = {
                "slu_tp": raw["slu_f1"]["tp"], "slu_fp": raw["slu_f1"]["fp"],
                "slu_fn": raw["slu_f1"]["fn"],
                "exact_tp": raw["entities"]["tp"], "exact_fp": raw["entities"]["fp"],
                "exact_fn": raw["entities"]["fn"],
            }
            closure[key] = {
                "summed_over_types": summed,
                "official_aggregate_raw": official,
                "max_abs_diff": max(abs(summed[k] - official[k]) for k in summed),
                "closes_1e-6": all(abs(summed[k] - official[k]) < 1e-6 for k in summed),
            }
            print(f"  slot diagnostics {key} in {time.time() - started:.1f}s", flush=True)
    if not all(entry["closes_1e-6"] for entry in closure.values()):
        raise B8aReadError("the per-type decomposition does not close on an official aggregate")

    all_types = sorted({t for key in tables for t in tables[key]})
    per_type: dict[str, dict] = {}
    for typ in all_types:
        entry: dict[str, object] = {}
        for arm in ARMS:
            off = tables[f"{arm}:off"].get(typ, {})
            on = tables[f"{arm}:on"].get(typ, {})
            entry[arm] = {
                "off": off,
                "on": on,
                "delta_on_minus_off": {
                    field: on.get(field, 0) - off.get(field, 0)
                    for field in sorted(set(off) | set(on))
                },
            }
        per_type[typ] = entry

    payload = {
        "purpose": (
            "FN and FP mass by slot type before and after the delivery node, on each of the "
            "three sealed bases. The node's filler half can only move the entity side of the "
            "official metric, and this table is where that movement is read by type."
        ),
        "method": (
            "the official scorer's own matching, reconstructed from each arm-side's own "
            "outputs.jsonl: analysis.slurp_entity_attribution._match_block (the official "
            "SpanDistanceFMeasure greedy same-type match) under the official word and "
            "character distances, and reproduction.slurp_scoring._exact_counts for the exact "
            "SpanFMeasure. Every row's reconstruction is checked against that row's own "
            "official slu_f1 word and char tp/fp/fn before any table is built, and the "
            "per-type decomposition is required to sum to that side's official aggregate. No "
            "new scorer is written and no filler text is printed or persisted."
        ),
        "closure_check": closure,
        "per_type": per_type,
    }
    cache.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("slot cached ->", cache)


# --------------------------------------------------------------------------
# The decision block -- the preregistration's rule, applied unchanged
# --------------------------------------------------------------------------


def decision_block(recipe: dict, comparisons: dict, band: dict, symmetric: dict, scored: dict) -> dict:
    def slu(name: str) -> dict:
        return comparisons[name]["pooled_micro"]["slu_f1_micro"]

    def intent(name: str) -> dict:
        return comparisons[name]["per_row"]["scenario_action_exact"]

    def sym_slu(name: str) -> dict:
        return symmetric["comparisons"][name]["pooled_micro"]["slu_f1_micro"]

    clauses: dict[str, dict] = {}
    for arm in ARMS:
        name = CONTRAST_OF_ARM[arm]
        s = slu(name)["speaker_clustered"]
        i = intent(name)["speaker_clustered"]
        breached = band[name]["scenarios_losing_beyond_the_band"]
        flagged = band[name]["decision_17_flagged_scenarios"]
        clause1 = s["ci95_pp"][0] > 0.0
        clause2 = i["ci95_pp"][0] > -H_INTENT
        clause3 = not breached
        harmful = (
            s["point_estimate_pp"] < -H_SLU
            or i["point_estimate_pp"] < -H_INTENT
            or s["ci95_pp"][1] < 0.0
            or i["ci95_pp"][1] < 0.0
        )
        on_official = 100 * float(scored[arm]["on"][SCORER]["aggregate"]["official"]["slu_f1"])
        on_intent = 100 * float(
            scored[arm]["on"][SCORER]["aggregate"]["official"]["intent_accuracy"]
        )
        sym_delta = sym_slu(name)["delta_pp"]
        official_delta = slu(name)["delta_pp"]
        clauses[arm] = {
            "contrast": name,
            "gates": arm in GATING_ARMS,
            "clause_1_pooled_slu_ci95_lower_above_zero": {
                "delta_pp": official_delta,
                "ci95_pp": s["ci95_pp"],
                "ci95_lower_pp": s["ci95_pp"][0],
                "threshold": 0.0,
                "passes": clause1,
            },
            "clause_2_intent_non_inferior": {
                "delta_pp": intent(name)["delta_pp"],
                "ci95_pp": i["ci95_pp"],
                "ci95_lower_pp": i["ci95_pp"][0],
                "threshold": -H_INTENT,
                "passes": clause2,
            },
            "clause_3_no_scenario_intent_ci95_upper_below_zero": {
                "scenarios_losing_beyond_the_band": breached,
                "passes": clause3,
            },
            "clause_4_decision_17_reported": {
                "decision_17_flagged_scenarios": flagged,
                "reported": True,
                "passes": True,
            },
            "harmful_clause": {
                "requirement": (
                    "owner decision 25's Method B: a MEASURED loss -- an official pooled SLU "
                    f"or intent POINT ESTIMATE below -h ({-H_SLU} / {-H_INTENT}), or a CI95 "
                    "upper bound below zero"
                ),
                "pooled_slu_point_estimate_pp": s["point_estimate_pp"],
                "pooled_slu_ci95_upper_pp": s["ci95_pp"][1],
                "intent_point_estimate_pp": i["point_estimate_pp"],
                "intent_ci95_upper_pp": i["ci95_pp"][1],
                "fires": harmful,
            },
            "all_admission_clauses_pass": clause1 and clause2 and clause3,
            "symmetric_reported": {
                "delta_pp": sym_delta,
                "ci95_pp": sym_slu(name)["speaker_clustered"]["ci95_pp"],
                "share_of_the_official_gain": (
                    sym_delta / official_delta if official_delta else None
                ),
                "gates": False,
                "owner_decision_7": (
                    "about 2.5 pp of the 64-point bar is representation alignment rather "
                    "than capability; the share of the official gain the symmetric scorer "
                    "scores at zero is exactly that alignment, now performed by the system "
                    "itself"
                ),
            },
            "official_with_the_node": {
                "pooled_slu_f1": on_official,
                "intent": on_intent,
                "bar_slu": BAR_SLU,
                "bar_intent": BAR_INTENT,
                "clears_the_bar_slu": on_official >= BAR_SLU,
                "clears_the_bar_intent": on_intent >= BAR_INTENT,
                "note": (
                    "stated as a fact of this base, never as a claim: this cell is a "
                    "one-factor module admission, not a bar attempt"
                ),
            },
        }

    admitted = all(clauses[arm]["all_admission_clauses_pass"] for arm in GATING_ARMS)
    harmful = any(clauses[arm]["harmful_clause"]["fires"] for arm in GATING_ARMS)
    non_inferiority_unproven = [
        arm
        for arm in GATING_ARMS
        if not clauses[arm]["clause_1_pooled_slu_ci95_lower_above_zero"]["passes"]
        and slu(CONTRAST_OF_ARM[arm])["speaker_clustered"]["ci95_pp"][0] <= -H_SLU
    ]
    if harmful:
        status = "HARMFUL"
    elif admitted:
        status = "ADMITTED"
    else:
        status = "NEUTRAL"

    return {
        "rule": (
            "preregistration section 8, applied unchanged: ADMITTED if and only if on the "
            "anchor base AND the cell B1 base (1) the CI95 lower bound of the paired official "
            "pooled SLU-F1 delta is above zero, (2) the paired intent delta's CI95 lower bound "
            f"exceeds -{H_INTENT}, (3) no scenario's paired intent CI95 upper bound lies below "
            "zero, and (4) owner decision 17's net-harmed-rows diagnostic is reported. The "
            "cell B5e base is read under the same clauses and does NOT gate. HARMFUL only by a "
            "measured loss (owner decision 25 Method B). NEUTRAL otherwise. The TRAIN "
            "symmetric number is reported beside and is not a gate."
        ),
        "margins_pp": {
            "h_SLU_ci95": H_SLU,
            "h_intent_ci95": H_INTENT,
            "source": (
                "the TRAIN A own null measured by cell B0r on this exact roster and geometry "
                "(docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md); inputs here, "
                "never outputs"
            ),
            "conservatism": (
                "the ON and OFF arms are the same sealed rows one deterministic transform "
                "apart, so the paired bootstrap carries no decoding noise at all -- only the "
                "row-to-row variation of the rule's own effect. Cell B0r's margins were "
                "calibrated on a request-identical replicate whose two passes DO differ by "
                "decoding noise, so they are conservative here. A narrow interval is a "
                "property of the pairing, not extra evidence."
            ),
        },
        "per_base": clauses,
        "gating_bases": list(GATING_ARMS),
        "admitted": admitted,
        "harmful": harmful,
        "non_inferiority_not_proven_on": non_inferiority_unproven,
        "status": status,
        "status_line": f"MODEL-FREE READ: {status}; smoke pending",
        "read_once": True,
        "claim_boundary": recipe["claim_boundary"],
    }


# --------------------------------------------------------------------------
# Rendering and assembly
# --------------------------------------------------------------------------


HEADLINE_ROWS = (
    ("Official pooled SLU micro F1", "pooled_micro", "slu_f1_micro", "pooled count F1"),
    ("Intent (joint scenario+action)", "per_row", "scenario_action_exact", "mean per row"),
    ("Scenario accuracy", "per_row", "scenario_exact", "mean per row"),
    ("Action accuracy", "per_row", "action_exact", "mean per row"),
    ("Official span F1 (pooled)", "pooled_micro", "span_f1_micro", "pooled count F1"),
    ("Exact slot F1 (per-row mean)", "per_row", "slot_f1_exact_f1", "mean per row"),
    ("Official SLU F1 (per-row mean)", "per_row", "slu_f1_f1", "mean per row"),
)


def _ci(block: dict, level: str) -> str:
    low, high = block[level]
    return f"[{low:+.2f}, {high:+.2f}]"


def headline_table(block: dict, *, stratified: bool = True) -> str:
    lines = []
    for label, kind, metric, estimand in HEADLINE_ROWS:
        entry = block[kind][metric]
        clustered = entry["speaker_clustered"]
        strat_cell = ""
        if stratified:
            strat = entry.get("scenario_stratified")
            strat_cell = (_ci(strat, "ci95_pp") if strat else "n/a") + " | "
        lines.append(
            f"| {label} | {estimand} | {entry['left_pct']:.2f} | {entry['right_pct']:.2f} | "
            f"{entry['delta_pp']:+.2f} | {_ci(clustered, 'ci95_pp')} | "
            f"{_ci(clustered, 'ci90_pp')} | {clustered['ci95_half_width_pp']:.4f} | "
            f"{strat_cell}{entry['equal_scenario_delta_pp']:+.2f} |"
        )
    return "\n".join(lines)


def saves_table(block: dict) -> str:
    lines = [
        "| per-row metric | saves | harms | ties | exact two-sided McNemar p |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for metric in PER_ROW_METRICS:
        entry = block["per_row"][metric]
        lines.append(
            f"| {metric} | {entry['saves']} | {entry['harms']} | {entry['ties']} | "
            f"{entry['sign_test_p']:.3e} |"
        )
    return "\n".join(lines)


def scenario_table(block: dict, band_block: dict) -> str:
    pooled = block["pooled_micro"]["slu_f1_micro"]["per_scenario"]
    intent = block["per_row"]["scenario_action_exact"]["per_scenario"]
    bands = band_block["per_scenario"]
    lines = [
        "| scenario | n | OFF SLU | ON SLU | delta | OFF intent | ON intent | delta | "
        "intent CI95 | net harmed | decision-17 flag | loses beyond the band |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for scenario in sorted(pooled):
        p = pooled[scenario]
        i = intent[scenario]
        b = bands[scenario]
        lines.append(
            f"| {scenario} | {p['n']} | {p['left_pct']:.2f} | {p['right_pct']:.2f} | "
            f"{p['delta_pp']:+.2f} | {i['left_pct']:.2f} | {i['right_pct']:.2f} | "
            f"{i['delta_pp']:+.2f} | {_ci(b, 'ci95_pp')} | {b['net_harmed_rows']:+d} | "
            f"{'FLAG' if b['decision_17_flag'] else 'no'} | "
            f"{'YES' if b['ci95_upper_below_zero'] else 'no'} |"
        )
    equal_slu = block["pooled_micro"]["slu_f1_micro"]["equal_scenario_delta_pp"]
    equal_intent = block["per_row"]["scenario_action_exact"]["equal_scenario_delta_pp"]
    lines.append(
        f"| **equal-scenario mean** | 18 | | | **{equal_slu:+.2f}** | | | "
        f"**{equal_intent:+.2f}** | | | | |"
    )
    return "\n".join(lines)


def rule_table(decision: dict) -> str:
    lines = [
        "| base | clause | value | threshold | passes |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for arm in ARMS:
        block = decision["per_base"][arm]
        tag = f"{ARM_SHORT[arm]}{'' if block['gates'] else ' (reported)'}"
        c1 = block["clause_1_pooled_slu_ci95_lower_above_zero"]
        c2 = block["clause_2_intent_non_inferior"]
        c3 = block["clause_3_no_scenario_intent_ci95_upper_below_zero"]
        c4 = block["clause_4_decision_17_reported"]
        h = block["harmful_clause"]
        lines.append(
            f"| {tag} | 1. official pooled SLU CI95 lower > 0 | {c1['ci95_lower_pp']:+.4f} | "
            f"> {c1['threshold']:+.4f} | {'YES' if c1['passes'] else 'NO'} |"
        )
        lines.append(
            f"| {tag} | 2. intent CI95 lower > -h_intent | {c2['ci95_lower_pp']:+.4f} | "
            f"> {c2['threshold']:+.4f} | {'YES' if c2['passes'] else 'NO'} |"
        )
        lines.append(
            f"| {tag} | 3. no scenario intent CI95 upper < 0 | "
            f"{len(c3['scenarios_losing_beyond_the_band'])} of 18 | 0 | "
            f"{'YES' if c3['passes'] else 'NO'} |"
        )
        lines.append(
            f"| {tag} | 4. decision-17 diagnostic reported | "
            f"{len(c4['decision_17_flagged_scenarios'])} flagged | reported | YES |"
        )
        lines.append(
            f"| {tag} | HARMFUL (owner decision 25 Method B) | SLU point "
            f"{h['pooled_slu_point_estimate_pp']:+.4f}, intent point "
            f"{h['intent_point_estimate_pp']:+.4f} | point < -h or CI95 upper < 0 | "
            f"{'FIRES' if h['fires'] else 'no'} |"
        )
    return "\n".join(lines)


def build_readme(payload: dict, contrasts_sha: str, script_name: str, script_sha: str) -> str:
    decision = payload["decision"]
    comparisons = payload["comparisons"]
    band = payload["scenario_band"]
    node = payload["node_diagnostics"]
    stop = payload["stop_condition"]

    head = (
        "| metric | estimand | OFF | ON | delta (pp) | speaker CI95 | speaker CI90 | "
        "CI95 half-width | scenario-stratified CI95 | equal-scenario delta |\n"
        "| --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- | ---: |"
    )
    sections = []
    for arm in ARMS:
        name = CONTRAST_OF_ARM[arm]
        block = comparisons[name]
        sections.append(
            f"### {CONTRAST_NAMES[name]}\n\n"
            f"{head}\n{headline_table(block)}\n\n"
            f"{saves_table(block)}\n"
        )
    contrast_sections = "\n".join(sections)

    scen = "\n\n".join(
        f"### {CONTRAST_NAMES[CONTRAST_OF_ARM[arm]]}\n\n"
        + scenario_table(comparisons[CONTRAST_OF_ARM[arm]], band[CONTRAST_OF_ARM[arm]])
        for arm in ARMS
    )

    node_rows = "\n".join(
        f"| {ARM_SHORT[arm]} | {node[arm]['changed_row_decomposition']['rows_changed']} | "
        f"{node[arm]['changed_row_decomposition']['rows_label_changed']} | "
        f"{node[arm]['changed_row_decomposition']['rows_filler_changed']} "
        f"({node[arm]['changed_row_decomposition']['entities_filler_changed']}) | "
        f"{node[arm]['changed_row_decomposition']['rows_unparsed']} | "
        f"{node[arm]['changed_row_decomposition']['rows_rendering_suppressed']} | "
        f"{node[arm]['triple_equality']['parsed_rows_compared']} | "
        f"{node[arm]['triple_equality']['mismatches']} | "
        f"{node[arm]['idempotence']['non_fixed_points']} |"
        for arm in ARMS
    )

    symmetric_rows = "\n".join(
        f"| {ARM_SHORT[arm]} | "
        f"{decision['per_base'][arm]['clause_1_pooled_slu_ci95_lower_above_zero']['delta_pp']:+.4f} | "
        f"{decision['per_base'][arm]['symmetric_reported']['delta_pp']:+.4f} | "
        + (
            f"{100 * decision['per_base'][arm]['symmetric_reported']['share_of_the_official_gain']:.1f} %"
            if decision["per_base"][arm]["symmetric_reported"]["share_of_the_official_gain"]
            is not None
            else "n/a"
        )
        + " |"
        for arm in ARMS
    )

    def input_rows() -> str:
        return "\n".join(
            f"| `{row['path']}` | `{row['sha256']}` | {row['role']} |"
            for row in payload["inputs"]
        )

    def output_rows() -> str:
        return "\n".join(f"| `{row['path']}` | `{row['sha256']}` |" for row in payload["outputs"])

    return f"""# {payload['title']}

Status: **{decision['status_line']}**

Created {payload['created_at_utc']}. Execution profile `{payload['execution_profile']}`.
Model, tokenizer, encoder, ASR and server contacts **0**. The only scorer invocations are the
registered model-free SLURP scorings, each over a COPY of a sealed `outputs.jsonl` written under
this directory, or over the node's own replayed copy of one. **The sealed bytes were copied, never
opened for writing.**

Driver: `{script_name}` (sha256 `{script_sha}`), an adapted copy of two sealed precedent drivers
whose estimator calls are unchanged:
{chr(10).join(f"- `{d['path']}` (sha256 `{d['sha256']}`) -- {d['role']}" for d in PRECEDENT_DRIVERS)}

Registered analysis root of the recipe: `{payload['recipe_registered_analysis_root']}`. This read
was written to `{payload['analysis_root']}` on the coordinator's instruction; the driver takes its
output root from the caller, so the two names describe the same registered read.

## STOP condition

Closed **before any contrast was computed**: passed = **{stop['passed']}**
({len(stop['checks'])} checks, {len(stop['failures'])} failures).

- the three sealed OFF arms reproduce their registered official aggregates to the hundredth;
- the three node-ON arms reproduce the registered projection v3 aggregates to the hundredth;
- the registered v3 SCORER over each OFF copy re-derives the same projected numbers a second way,
  and over each ON copy it is a **NO-OP** -- the node already performed the rule;
- 1,080 rows in and 1,080 out per arm, the same ids, none invented.

## The node, measured on sealed bytes

| base | rows changed | label repairs | filler-repaired rows (entities) | unparsed, left verbatim | rendering-suppressed | parsed rows compared | triple mismatches | idempotence non-fixed-points |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{node_rows}

## The rule

{rule_table(decision)}

**{decision['status_line']}**

## Contrasts

{contrast_sections}

## The TRAIN symmetric view beside the official delta (owner decisions 7 and 14; never a gate)

| base | official pooled SLU delta (pp) | symmetric pooled SLU delta (pp) | symmetric share of the official gain |
| --- | ---: | ---: | ---: |
{symmetric_rows}

## Per-scenario tables (natural mixture; equal-scenario mean in the last row)

{scen}

## Inputs

| path | sha256 | role |
| --- | --- | --- |
{input_rows()}

## Claim boundary

{payload['claim_boundary']}

## Files

| file | sha256 |
| --- | --- |
{output_rows()}
| `score-contrasts.json` | `{contrasts_sha}` |
| `{script_name}` | `{script_sha}` |
| `README.md` | this file; its own sha256 is printed on the line that created it |
"""


def stage_assemble(ctx: Context, cache_dir: Path, script_path: Path) -> None:
    recipe = load_recipe(ctx)
    verified = verify_sealed_inputs(ctx, recipe)
    contrasts = json.loads((cache_dir / "contrasts-raw.json").read_text(encoding="utf-8"))
    band = json.loads((cache_dir / "band-raw.json").read_text(encoding="utf-8"))
    node = json.loads((cache_dir / "replay-raw.json").read_text(encoding="utf-8"))
    scored = json.loads((cache_dir / "scores-raw.json").read_text(encoding="utf-8"))
    symmetric = json.loads((cache_dir / "sym-contrasts-raw.json").read_text(encoding="utf-8"))
    slot = json.loads((cache_dir / "slot-raw.json").read_text(encoding="utf-8"))

    decision = decision_block(recipe, contrasts["comparisons"], band, symmetric, scored)

    authority = [
        {"path": rel, "sha256": digest(ctx.repo_root / rel)} for rel in AUTHORITY_RELPATHS
    ]
    implementation = [
        {"path": rel, "sha256": digest(ctx.repo_root / rel)} for rel in IMPLEMENTATION_RELPATHS
    ]

    inputs = []
    for arm in ARMS:
        spec = recipe["arms"][arm]
        paths = verified[arm]["paths"]
        inputs.append({"path": str(paths["scores"]), "sha256": spec["scores_sha256"],
                       "role": f"{arm}: sealed official score (the OFF official number)"})
        inputs.append({"path": str(paths["manifest"]), "sha256": spec["run_manifest_sha256"],
                       "role": f"{arm}: sealed run manifest"})
        inputs.append({"path": str(paths["outputs"]), "sha256": spec["outputs_sha256"],
                       "role": f"{arm}: sealed outputs (copied, never opened for writing)"})
    inputs.append({"path": contrasts["roster_path"],
                   "sha256": recipe["population"]["roster"]["sha256"], "role": "roster"})
    inputs.append({"path": contrasts["metadata_path"],
                   "sha256": recipe["population"]["roster_metadata"]["sha256"],
                   "role": "roster metadata (speaker clusters and scenario strata)"})
    inputs.append({"path": str(ctx.recipe_path), "sha256": digest(ctx.recipe_path),
                   "role": "the analysis recipe; this driver's contract"})
    inputs.append({"path": str(ctx.lock_path), "sha256": digest(ctx.lock_path),
                   "role": "the umbrella dataset lock the scorers resolve gold through"})
    for row in authority:
        inputs.append({"path": str(ctx.repo_root / row["path"]), "sha256": row["sha256"],
                       "role": "authority document"})
    for row in implementation:
        inputs.append({"path": str(ctx.repo_root / row["path"]), "sha256": row["sha256"],
                       "role": "estimator / rule implementation"})

    per_scenario = {
        CONTRAST_OF_ARM[arm]: {
            "pooled_slu": contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["pooled_micro"][
                "slu_f1_micro"
            ]["per_scenario"],
            "pooled_span": contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["pooled_micro"][
                "span_f1_micro"
            ]["per_scenario"],
            "per_row": {
                metric: contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["per_row"][metric][
                    "per_scenario"
                ]
                for metric in PER_ROW_METRICS
            },
            "intent_band": band[CONTRAST_OF_ARM[arm]]["per_scenario"],
            "equal_scenario_delta_pp": {
                "pooled_slu": contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["pooled_micro"][
                    "slu_f1_micro"
                ]["equal_scenario_delta_pp"],
                "pooled_span": contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["pooled_micro"][
                    "span_f1_micro"
                ]["equal_scenario_delta_pp"],
                **{
                    metric: contrasts["comparisons"][CONTRAST_OF_ARM[arm]]["per_row"][metric][
                        "equal_scenario_delta_pp"
                    ]
                    for metric in PER_ROW_METRICS
                },
            },
            "scenarios_losing_beyond_the_band": band[CONTRAST_OF_ARM[arm]][
                "scenarios_losing_beyond_the_band"
            ],
            "decision_17_flagged_scenarios": band[CONTRAST_OF_ARM[arm]][
                "decision_17_flagged_scenarios"
            ],
        }
        for arm in ARMS
    }

    payload = {
        "schema": RESULT_SCHEMA,
        "experiment_id": "SAEA-SLURP-B8A-DELIVERY-NODE-READ-V1",
        "recipe_id": RECIPE_ID,
        "analysis_root": str(ctx.output_dir),
        "recipe_registered_analysis_root": recipe["output"]["analysis_root"],
        "title": (
            "SLURP TRAIN A: cell B8a, the delivery-time normaliser node "
            "(saea-deliver-normalise-v3, module M3 executed inside the agent), node ON minus "
            "OFF over the sealed anchor, cell B1 and cell B5e arms"
        ),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution_profile": recipe["execution_profile"],
        "adapted_from": list(PRECEDENT_DRIVERS),
        "authority": authority,
        "module": recipe["module"],
        "delta_convention": (
            "delta = ON minus OFF, in percentage points; negative means the node is worse. The "
            "ON arm of each base is that base's own sealed rows after the node, so the two "
            "arms are perfectly paired and no interval below contains decoding noise."
        ),
        "contacts": {
            "model_calls": 0,
            "tokenizer_calls": 0,
            "encoder_calls": 0,
            "asr_calls": 0,
            "server_requests": 0,
            "paid_api_calls": 0,
            "scorer_invocations": {
                "official_off": 0,
                "official_on": len(ARMS),
                "projected_v3_off": len(ARMS),
                "projected_v3_on": len(ARMS),
                "train_symmetric_off": len(ARMS),
                "train_symmetric_on": len(ARMS),
                "note": (
                    "the OFF official number is the sealed scores.json, re-verified by hash, "
                    "and invokes no scorer; every other scoring is one complete, never "
                    "sharded invocation of a registered model-free scorer over a copy under "
                    "this directory"
                ),
            },
        },
        "resampling": {
            "primary": "paired whole-speaker cluster bootstrap over the roster's speaker clusters",
            "sensitivity": (
                "paired scenario-stratified row bootstrap (each of 18 scenarios resampled to "
                "its own size), on the official contrasts"
            ),
            "n_replicates": DRAWS,
            "seed": SEED,
            "ci_levels": [0.95, 0.90],
            "ci_note": (
                "both intervals are percentiles of the SAME retained replicate sequence "
                "(analysis.bootstrap._percentile over BootstrapResult.replicates)"
            ),
            "per_row_seed_rule": (
                "paired_contrast advances the seed by the metric index in "
                + ", ".join(PER_ROW_METRICS)
            ),
            "micro_seed_rule": "resampled_statistic uses the base seed for every pooled metric",
            "scenario_band": (
                "the same paired whole-speaker cluster bootstrap restricted to each scenario's "
                f"own rows, {DRAWS:,} draws, seed {SEED}"
            ),
            "pairing_note": recipe["resampling"]["pairing_note"],
            "tables": recipe["resampling"]["tables"],
        },
        "estimators": {
            "row_reader": "analysis.null_calibration_cli.rows_for",
            "pooled_micro_f1": "analysis.null_calibration.pooled_f1",
            "bootstrap_pooled": "analysis.paired.resampled_statistic",
            "paired_per_row": "analysis.paired.paired_contrast",
            "percentiles": "analysis.bootstrap._percentile over the retained replicates",
            "replay": "analysis.deliver_normaliser_replay.replay",
            "slot_matching": (
                "analysis.slurp_entity_attribution._match_block and "
                "reproduction.slurp_scoring._exact_counts, the official scorer's own matching"
            ),
            "not_used": (
                "analysis.score_compare_cli as the runner: it hard-codes ci_level 0.90 and "
                "DEV population names"
            ),
        },
        "scoring_note": (
            "the recipe's step 4 names core.scoring_batch. That module scores a complete, "
            "bundle-verified run directory in its own job process; the node-ON side of each "
            "arm is a replayed outputs.jsonl with no run manifest and no bundle, so it cannot "
            "be its input. This driver therefore resolves each registered scorer through "
            "core.base.SCORERS and invokes it ONCE per arm-side over a byte-verified copy -- "
            "which is the exact invocation core.scorers.score_bundle makes inside a "
            "core.scoring_batch job (scorer_fn(bundle.outputs_path, lock, root)), one complete "
            "score per arm-side, never sharded. The precedent drivers take the same path."
        ),
        "population": contrasts["population"],
        "sources": {
            arm: {
                "run_id": recipe["arms"][arm]["run_id"],
                "attempt_id": recipe["arms"][arm]["attempt_id"],
                "role": recipe["arms"][arm]["role"],
                "manifest_status": verified[arm]["manifest"].get("status"),
                "study_commit": verified[arm]["manifest"].get("study_commit"),
                "config_hash": (verified[arm]["manifest"].get("config") or {}).get(
                    "config_hash"
                ),
                "protocol_hash": verified[arm]["manifest"].get("protocol_hash"),
                "execution_profile": (verified[arm]["manifest"].get("plan") or {}).get(
                    "execution_profile"
                ),
                "scorer_version": verified[arm]["scores"][SCORER]["aggregate"].get(
                    "scorer_version"
                ),
                "evaluator_commit": verified[arm]["scores"][SCORER]["aggregate"].get(
                    "evaluator_commit"
                ),
                "identity_check": verified[arm]["scores"][SCORER]["aggregate"].get(
                    "identity_check"
                ),
                "official_aggregate_off": {
                    field: verified[arm]["scores"][SCORER]["aggregate"]["official"][field]
                    for field in (
                        "slu_f1",
                        "span_f1",
                        "intent_accuracy",
                        "scenario_accuracy",
                        "action_accuracy",
                    )
                },
                "official_aggregate_on": {
                    field: scored[arm]["on"][SCORER]["aggregate"]["official"][field]
                    for field in (
                        "slu_f1",
                        "span_f1",
                        "intent_accuracy",
                        "scenario_accuracy",
                        "action_accuracy",
                    )
                },
            }
            for arm in ARMS
        },
        "consistency_check": contrasts["consistency_check"],
        "stop_condition": contrasts["stop_condition"],
        "row_counts": contrasts["row_counts"],
        "comparisons": contrasts["comparisons"],
        "scenario_band": band,
        "node_diagnostics": node,
        "symmetric": symmetric,
        "slot_diagnostics": slot,
        "scored_aggregates": {
            arm: {
                side: {
                    scorer_id: {
                        "official": entry["aggregate"]["official"],
                        "projection": entry["aggregate"].get("projection"),
                        "filler_normalization": entry["aggregate"].get("filler_normalization"),
                        "normalized_micro": (entry["aggregate"].get("normalized") or {}).get(
                            "micro"
                        ),
                        "scores_path": entry.get("scores_path"),
                        "scores_sha256": entry.get("scores_sha256"),
                        "seconds": entry.get("seconds"),
                    }
                    for scorer_id, entry in scored[arm][side].items()
                }
                for side in ("off", "on")
            }
            for arm in ARMS
        },
        "decision": decision,
        "implementation": implementation,
        "inputs": inputs,
        "claim_boundary": recipe["claim_boundary"],
        "model_calls": 0,
    }

    ctx.output_dir.mkdir(parents=True, exist_ok=True)
    side_files = {
        "per-scenario-tables.json": per_scenario,
        "node-diagnostics.json": node,
        "slot-diagnostics.json": slot,
        "symmetric-contrasts.json": symmetric,
        "replay-provenance.json": {
            arm: node[arm]["replay_provenance"] for arm in ARMS
        },
    }
    outputs = []
    for name, document in side_files.items():
        target = ctx.output_dir / name
        with target.open("x", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
        outputs.append({"path": name, "sha256": digest(target)})
    for root in (ctx.output_dir / "off", ctx.output_dir / "on"):
        for path in sorted(root.glob("**/*")):
            if path.is_file():
                outputs.append(
                    {"path": str(path.relative_to(ctx.output_dir)), "sha256": digest(path)}
                )
    payload["outputs"] = outputs

    target = ctx.output_dir / "score-contrasts.json"
    with target.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    contrasts_sha = digest(target)
    print("score-contrasts.json", contrasts_sha)
    copied = ctx.output_dir / script_path.name
    with copied.open("x", encoding="utf-8") as handle:
        handle.write(script_path.read_text(encoding="utf-8"))
    script_sha = digest(copied)
    print(copied.name, script_sha)
    readme = ctx.output_dir / "README.md"
    with readme.open("x", encoding="utf-8") as handle:
        handle.write(build_readme(payload, contrasts_sha, copied.name, script_sha))
    print("README.md", digest(readme))
    print("STATUS", decision["status_line"])


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


STAGES = ("replay", "score", "contrasts", "band", "symcontrasts", "slot", "assemble", "all")


def replay_and_read(
    *,
    repo_root: Path,
    data_root: Path,
    lock_path: Path,
    recipe_path: Path,
    output_dir: Path,
    cache_dir: Path,
    work_dir: Path | None = None,
    stage: str = "all",
    script_path: Path | None = None,
) -> None:
    """Run one stage, or the whole read, of cell B8a's model-free admission."""

    if stage not in STAGES:
        raise B8aReadError(f"unknown stage {stage!r}")
    ctx = Context(
        repo_root=Path(repo_root),
        data_root=Path(data_root),
        lock_path=Path(lock_path),
        output_dir=Path(output_dir),
        work_dir=Path(work_dir) if work_dir is not None else Path(output_dir),
        recipe_path=Path(recipe_path),
    )
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    script = Path(script_path) if script_path is not None else Path(__file__).resolve()

    order = STAGES[:-1] if stage == "all" else (stage,)
    for name in order:
        print(f"[{name}]", flush=True)
        if name == "replay":
            stage_replay(ctx, cache_dir / "replay-raw.json")
        elif name == "score":
            stage_score(ctx, cache_dir / "scores-raw.json")
        elif name == "contrasts":
            stage_contrasts(
                ctx,
                cache_dir / "scores-raw.json",
                cache_dir / "replay-raw.json",
                cache_dir / "contrasts-raw.json",
            )
        elif name == "band":
            stage_band(ctx, cache_dir / "scores-raw.json", cache_dir / "band-raw.json")
        elif name == "symcontrasts":
            stage_symcontrasts(
                ctx, cache_dir / "scores-raw.json", cache_dir / "sym-contrasts-raw.json"
            )
        elif name == "slot":
            stage_slot(ctx, cache_dir / "scores-raw.json", cache_dir / "slot-raw.json")
        else:
            stage_assemble(ctx, cache_dir, script)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cell B8a: the model-free admission read of the delivery-time normaliser node "
            "(module M3). Zero model, tokenizer, encoder, ASR and server contacts; the sealed "
            "bytes are copied, never opened for writing."
        )
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--stage", default="all", choices=STAGES)
    parser.add_argument("--script", default=None)
    args = parser.parse_args(argv)
    replay_and_read(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        lock_path=Path(args.lock_path),
        recipe_path=Path(args.recipe),
        output_dir=Path(args.output_dir),
        cache_dir=Path(args.cache_dir),
        work_dir=Path(args.work_dir) if args.work_dir else None,
        stage=args.stage,
        script_path=Path(args.script) if args.script else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "B8aReadError",
    "RESULT_SCHEMA",
    "main",
    "replay_and_read",
]
