#!/usr/bin/env python3
"""Derive the CONVERSION PROBE's 70-row roster, and prove it reproduces the
committed replication receipt.

WHY THIS EXISTS. The agreement arm's declared expectation is a product of a
MEASURED delivery gain and an UNMEASURED persuasion factor. The probe that
measures the persuasion factor flies exactly the rows the gain lands on: the
INTENT-UNCOVERED rows of TRAIN Fold A whose gold intent's boundary entry is
NEWLY DELIVERED under ``w_agree`` 1.0 at recall width 60. The committed receipt
``docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/production-replication-v1.json``
(sha256 7cd1f6d3...) records that COUNT -- 70 of 130, 0 lost -- but carries NO
row ids: its own text discipline emits "an id, a count, a rate or a hash" and it
chose counts. The roster therefore cannot be READ OFF the receipt; it has to be
RECONSTRUCTED, and this script reconstructs it from the receipt's own recipe and
then proves the reconstruction by reproducing every count the receipt committed.

WHAT MAKES THAT A PROOF AND NOT A RE-GUESS. Nothing here re-implements the
recipe. ``scripts/analysis/slurp_intent_agreement_production_replication.py`` is
imported BYTE-UNCHANGED and its own functions -- ``load_bank``,
``load_train_gold``, ``arm_channels``, ``load_sealed``, ``exemplar_selections``,
``agreement_table``, ``boundary_decisions``, ``tally`` -- are called with the
receipt's own parameters (recall width 60, w_agree 0.0 vs 1.0, 4 workers). The
resulting ``delivery`` block is compared to the receipt's committed
``arms['train-fold-a-plan']['by_recall_width']['60']['delivery']`` for EXACT
equality, as are both boundary-channel pin blocks and every pinned digest. Only
then is the id set taken, from exactly the predicate the receipt's own ``tally``
counts with::

    plan_class == "INTENT-UNCOVERED"  and  gold in treat.fused  and  gold not in base.fused

THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's ``plan_class``
and the row's gold intent are read on the scoring side only, in this script,
before any flight exists. That is legitimate for a CONDITIONAL estimate on a
TRAIN roster and it is illegitimate for anything else: NO POOLED OR
ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THE RESULTING CELL, because its
population was chosen by the mechanism's own effect. Gold reaches no query, no
key, no weight, no selector and no runtime.

TEXT DISCIPLINE. Sample ids, counts, rates and hashes only. No utterance text,
transcript, gold label, intent name, knowledge body or model output is printed
or persisted -- a sample id is an id.

ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API
contacts: arithmetic over receipt-pinned vector files and frozen snapshots, each
verified against its configured sha256 by this repository's own loaders.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_intent_agreement_conversion_roster.py \
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \
        --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \
        --output docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from argparse import Namespace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

#: The committed receipt this derivation is proven against, and its sha256 as
#: the brief named it. The path is not the receipt's own analysis id
#: (``analysis/SAEA-.../replication-v1.json``, which is where the read wrote its
#: working copy under SPEECHRL_DATA_DIR); it is the committed copy, and the
#: digest is what binds the two.
RECEIPT = Path(
    "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/"
    "production-replication-v1.json"
)
RECEIPT_SHA256 = "7cd1f6d338731ea7b6eef34408e5d37453c852670900319445968ddc2a1dc624"

#: The replication recipe, imported byte-unchanged rather than re-implemented.
RECIPE_PATH = Path(
    "scripts/analysis/slurp_intent_agreement_production_replication.py"
)

ARM_LABEL = "train-fold-a-plan"
RECALL_WIDTH = 60
WORKERS = 4
PLAN_CLASS = "INTENT-UNCOVERED"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
CARRIER_LOCK_KEY = "slurp"

#: The registered per-row headroom of the class the gain lands on, from the
#: agreement package's own ``expected_effect_derivation``. Reported so the
#: re-declared expectation is arithmetic on this receipt, not a second source.
HEADROOM_SLU_PP_PER_ROW = 5.41 / 130.0
HEADROOM_INTENT_PP_PER_ROW = 12.04 / 130.0
ARM_ROWS = 1080
ARM_ADMISSION_BAR_PP = 2.5


class DeriveError(RuntimeError):
    """Refuse a derivation that cannot be proven against committed bytes."""


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def import_recipe(repo: Path):
    """Import the committed replication script as a module, unchanged."""

    path = repo / RECIPE_PATH
    sha = digest_file(path)
    spec = importlib.util.spec_from_file_location("_saea_repl_recipe", path)
    if spec is None or spec.loader is None:
        raise DeriveError("cannot import the replication recipe module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sha


def load_receipt(repo: Path) -> tuple[dict, str]:
    path = repo / RECEIPT
    sha = digest_file(path)
    if sha != RECEIPT_SHA256:
        raise DeriveError(
            f"the committed receipt hashes to {sha}, not the registered "
            f"{RECEIPT_SHA256}; the derivation refuses to proceed"
        )
    return json.loads(path.read_text(encoding="utf-8")), sha


def compare(label: str, expected: object, observed: object, diffs: list[str]) -> bool:
    if expected == observed:
        return True
    diffs.append(label)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    if not 1 <= args.workers <= 4:
        print(json.dumps({"error": "workers must be 1..4"}), file=sys.stderr)
        return 1

    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    lock_path = Path(args.lock_path).resolve()

    receipt, receipt_sha = load_receipt(repo)
    if receipt["recipe"] != "slurp-intent-agreement-production-replication-v1":
        raise DeriveError("the committed receipt is not the replication recipe's own")
    if int(receipt["recall_width"]) != RECALL_WIDTH:
        raise DeriveError("the committed receipt did not read at recall width 60")
    if int(receipt["wiring_probe_max_rows"]) != 0:
        raise DeriveError("the committed receipt is a truncated wiring probe")
    committed = receipt["arms"][ARM_LABEL]
    committed_block = committed["by_recall_width"][str(RECALL_WIDTH)]

    recipe, recipe_sha = import_recipe(repo)
    from speech_aware_evidence_acquisition.data.lock import load_lock

    lock = load_lock(lock_path)
    bank = recipe.load_bank(data_root)
    train_gold = recipe.load_train_gold(lock, data_root)
    arm = next(a for a in recipe.ARMS if a["label"] == ARM_LABEL)

    channels = recipe.arm_channels(repo, data_root, lock_path, arm)
    population = recipe.load_population(data_root, arm, bank, train_gold)
    sealed = recipe.load_sealed(data_root, arm["run_id"], channels["attempt_id"])
    selections, _vote_pins = recipe.exemplar_selections(
        data_root, arm, channels, args.workers
    )
    table, _vote_measured = recipe.agreement_table(arm, channels, selections)
    base = recipe.boundary_decisions(data_root, arm, channels, None, 0.0, RECALL_WIDTH)
    treat = recipe.boundary_decisions(data_root, arm, channels, table, 1.0, RECALL_WIDTH)
    delivery = recipe.tally(population, sealed, base, treat)

    # ---- the proof: every committed cell, reproduced exactly -------------
    diffs: list[str] = []
    compare("delivery", committed_block["delivery"], delivery, diffs)
    compare("boundary_channel", committed_block["boundary_channel"], base["pins"], diffs)
    compare(
        "treatment_boundary_channel",
        committed_block["treatment_boundary_channel"],
        treat["pins"],
        diffs,
    )
    compare(
        "bad_case_bank_sha256", receipt["bad_case_bank_sha256"], bank["sha256"], diffs
    )
    compare(
        "agreement_builder_sha256",
        receipt["agreement_builder_sha256"],
        recipe.BUILDER_SHA,
        diffs,
    )
    compare(
        "sealed_phase_artefact_sha256",
        committed["sealed_phase_artefact"]["sha256"],
        sealed["sha256"],
        diffs,
    )
    compare(
        "split_identity_hash",
        committed["split_identity_hash"],
        channels["split_identity_hash"],
        diffs,
    )
    compare("population_sha256", committed["population"]["sha256"], population["source_sha256"], diffs)
    compare("roster_rows", committed["roster_rows"], len(channels["packets"]), diffs)
    if diffs:
        raise DeriveError(
            "the reconstruction does not reproduce the committed receipt: "
            + ", ".join(diffs)
        )

    # ---- the row set, by the receipt's own predicate ---------------------
    newly_delivered: list[str] = []
    newly_lost: list[str] = []
    uncovered_rows = 0
    for sample_id, verdict in sorted(population["rows"].items()):
        if verdict.get("plan_class") != PLAN_CLASS:
            continue
        gold = verdict.get("gold_intent")
        if gold is None:
            continue
        if sample_id not in base["rows"] or sample_id not in treat["rows"]:
            continue
        if sealed["rows"].get(sample_id) is None:
            continue
        uncovered_rows += 1
        gold_id = f"{recipe.BOUNDARY_DIM}:{gold}"
        before = gold_id in base["rows"][sample_id]["fused"]
        after = gold_id in treat["rows"][sample_id]["fused"]
        if after and not before:
            newly_delivered.append(sample_id)
        if before and not after:
            newly_lost.append(sample_id)

    committed_split = committed_block["delivery"]["plan_class_split"][PLAN_CLASS]
    if len(newly_delivered) != committed_split["newly_delivered"]:
        raise DeriveError(
            f"derived {len(newly_delivered)} newly-delivered rows, the receipt "
            f"committed {committed_split['newly_delivered']}"
        )
    if len(newly_lost) != committed_split["newly_lost"]:
        raise DeriveError("the newly-lost count does not match the receipt")
    if uncovered_rows != committed_split["rows"]:
        raise DeriveError("the class row count does not match the receipt")

    ids = sorted(newly_delivered)
    id_list_sha256 = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    probe_split_identity = split_identity_hash(prefixed(CARRIER_LOCK_KEY, ids))

    # ---- the roster's own audio arithmetic, from the committed manifest ---
    manifest = json.loads(
        (repo / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {str(item["sample_id"]): item for item in manifest["items"]}
    missing = [sample_id for sample_id in ids if sample_id not in by_id]
    if missing:
        raise DeriveError(f"{len(missing)} derived ids are not in the roster manifest")
    audio_seconds = sum(float(by_id[sample_id]["audio_seconds"]) for sample_id in ids)

    m = len(ids)
    report = {
        "schema": "saea-agreement-conversion-roster-v1",
        "derivation_id": "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-ROSTER-V1",
        "contact_class": "model-free",
        "contacts": {
            "model": 0, "server": 0, "encoder": 0, "embedder": 0,
            "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
        },
        "workers": args.workers,
        "recall_width": RECALL_WIDTH,
        "why": (
            "The committed replication receipt records the COUNT of newly delivered "
            "INTENT-UNCOVERED rows (70 of 130, 0 lost) and carries NO row ids, so the "
            "probe's roster cannot be read off it. It is RECONSTRUCTED here by importing "
            "that receipt's own recipe byte-unchanged and calling its own functions with "
            "its own parameters, and the reconstruction is PROVEN by reproducing every "
            "cell the receipt committed for this arm at this width -- the whole delivery "
            "block, both boundary-channel pin blocks, the bank digest, the builder "
            "digest, the sealed phase-artefact digest, the split identity and the roster "
            "row count -- before a single id is taken."
        ),
        "proof": {
            "receipt_relpath": str(RECEIPT).replace("\\", "/"),
            "receipt_sha256": receipt_sha,
            "receipt_read_id": receipt["read_id"],
            "recipe_relpath": str(RECIPE_PATH).replace("\\", "/"),
            "recipe_sha256": recipe_sha,
            "recipe_imported_unchanged": True,
            "compared_exactly": [
                "by_recall_width.60.delivery (all six classes, both definitions, "
                "plan_class_split, sealed_boundary_agreement, skipped, "
                "fusion_vs_rank_disagreements)",
                "by_recall_width.60.boundary_channel (every pin and histogram)",
                "by_recall_width.60.treatment_boundary_channel (every pin and histogram)",
                "bad_case_bank_sha256",
                "agreement_builder_sha256",
                "sealed_phase_artefact.sha256",
                "split_identity_hash",
                "population.sha256",
                "roster_rows",
            ],
            "differences": [],
            "committed_plan_class_split": committed_split,
            "reconstructed_plan_class_split": {
                "rows": uncovered_rows,
                "newly_delivered": len(newly_delivered),
                "newly_lost": len(newly_lost),
            },
        },
        "gold_use": (
            "THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class "
            "and each row's gold intent are read on the scoring side only, in this "
            "derivation, before the cell exists. That is legitimate for a CONDITIONAL "
            "estimate on a TRAIN roster and for nothing else: NO POOLED OR ROSTER-LEVEL "
            "CLAIM MAY EVER BE MADE FROM THE CELL THIS ROSTER DEFINES, because its "
            "population was chosen by the mechanism's own effect. Gold reaches no query, "
            "no key, no weight, no selector and no runtime."
        ),
        "population": {
            "source": population["source"],
            "sha256": population["source_sha256"],
            "plan_class": PLAN_CLASS,
            "class_rows": uncovered_rows,
            "predicate": (
                "plan_class == 'INTENT-UNCOVERED' and the row's own gold intent's "
                "intent-boundary value id is in the w_agree 1.0 fused selection and NOT "
                "in the w_agree 0.0 fused selection, both at recall width 60 with "
                "fuse_coverage m 8 / c 1 / top_l 8 -- the receipt's own tally predicate."
            ),
        },
        "roster": {
            "dataset_fragment": DATASET_FRAGMENT,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "count": m,
            "ids": ids,
            "id_list_sha256": id_list_sha256,
            "id_list_convention": (
                "sha256 over the LF-joined sorted sample ids, UTF-8, no trailing newline"
            ),
            "split_identity_hash": probe_split_identity,
            "split_identity_convention": (
                "data.splits.split_identity_hash over the LF-joined sorted "
                "carrier-prefixed ids f'slurp/{sample_id}'"
            ),
            "audio_seconds_total": round(audio_seconds, 7),
            "newly_lost_ids": sorted(newly_lost),
        },
        "the_quantity_this_roster_measures": {
            "name": "P(correct | newly delivered)",
            "what_it_is": (
                "the agreement arm's PERSUASION factor, the one term of its declared "
                "expectation that is not measured. Every one of these rows is intent "
                "WRONG in the sealed comparator (INTENT-UNCOVERED collapses to "
                "INTENT-WRONG in the bank's own convention), so the forward count is "
                "the whole estimate and the reverse count on this population is zero by "
                "construction."
            ),
            "arm_declared_conversion": 0.467895,
            "arm_declared_persuasion_factor": 0.5,
            "arm_p_correct_given_covered": 0.935789,
            "arm_ceiling_slu_pp": round(m * HEADROOM_SLU_PP_PER_ROW, 4),
            "arm_ceiling_intent_pp": round(m * HEADROOM_INTENT_PP_PER_ROW, 4),
            "headroom_slu_pp_per_row": round(HEADROOM_SLU_PP_PER_ROW, 6),
            "headroom_intent_pp_per_row": round(HEADROOM_INTENT_PP_PER_ROW, 6),
            "re_declared_expectation_rule": (
                "re-declared expected_effect_pp of the 1,080-row AGREE arm = "
                "(rows of this roster that move from a wrong intent to the gold intent) "
                f"x {HEADROOM_SLU_PP_PER_ROW:.6f} pp SLU-F1, and "
                f"x {HEADROOM_INTENT_PP_PER_ROW:.6f} pp intent accuracy."
            ),
            "rows_needed_to_clear_the_arm_bar": math.ceil(
                ARM_ADMISSION_BAR_PP / HEADROOM_SLU_PP_PER_ROW
            ),
            "conversion_needed_to_clear_the_arm_bar": round(
                ARM_ADMISSION_BAR_PP / (m * HEADROOM_SLU_PP_PER_ROW), 6
            ),
            "arm_admission_bar_pp": ARM_ADMISSION_BAR_PP,
            "arm_rows": ARM_ROWS,
            "the_only_directly_observable_prior": (
                "86 of the 191 intent-wrong Fold A rows already RECEIVE the gold "
                "intent's boundary entry in the sealed comparator and are intent-wrong "
                "anyway (the agreement package's own measured_inputs), so the only "
                "directly observable conversion evidence on this population is zero. "
                "That is a reason to measure the factor, not a prediction of it."
            ),
        },
        "boundary": (
            "ZERO model, server, encoder, embedder, scorer, network, GPU and paid-API "
            "contacts: no server was started, stopped or probed, no waveform decoded and "
            "no embedding computed. Every number is arithmetic over receipt-pinned vector "
            "files and frozen snapshots, each verified against its configured sha256 by "
            "this repository's own loaders through its own rails.phase_supply / "
            "rails.knowledge_provider / rails.kb_policy seams. A DERIVATION, never a "
            "gate: it registers no cell by itself, admits no mechanism, releases no "
            "store, authorises no flight and states no effectiveness, superiority or "
            "generalisation claim. Every roster is a discovery or dev roster and every "
            "number is a development number (owner decisions 28 and 86). No utterance "
            "text, transcript, gold label, intent name, knowledge body or delivered "
            "answer is printed or persisted: every cell is an id, a count, a rate or a "
            "hash."
        ),
    }

    out = repo / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "derived_rows": m,
                "committed_newly_delivered": committed_split["newly_delivered"],
                "newly_lost": len(newly_lost),
                "class_rows": uncovered_rows,
                "id_list_sha256": id_list_sha256,
                "split_identity_hash": probe_split_identity,
                "audio_seconds_total": round(audio_seconds, 7),
                "differences": diffs,
                # A re-run that writes OUTSIDE the repository is the way this
                # derivation is proven byte-reproducible without dirtying the
                # tree, so an out-of-repo path is reported as itself rather
                # than crashing after the file is already written.
                "output": (
                    str(out.relative_to(repo)).replace("\\", "/")
                    if out.is_relative_to(repo)
                    else str(out)
                ),
                "output_sha256": digest_file(out),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
