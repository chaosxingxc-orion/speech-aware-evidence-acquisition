"""CROSS-CARRIER CEILING DECOMPOSITION -- why one locked cell moves two carriers
by different amounts, decomposed arithmetically at ZERO CONTACTS.

Row ``SAEA-SN-MF-CROSS-CARRIER-CEILING-DECOMPOSITION`` (model-free-check),
registered in ``docs/exposure-ledger.md`` BEFORE any number here was computed.

THE QUESTION, STATED FIRST. The locked v1 policy cell delivers **+20.20 pp** on
SLURP DEV-1000's unexposed 500 and **+0.96 pp** of tool accuracy on the 104-item
Audio2Tool subset. A reviewer will ask whether the method is WEAKER on
Audio2Tool or whether its REACH is smaller there. This module answers that by
decomposition, never by assertion:

``population delta = reachable share x within-reach conversion + retain drift``

WHAT IT COMPUTES.

1. :func:`alpha_veto` -- CEILING A. ``kb_policy._blend_scores`` gives the direct
   label ``alpha * f(d) + (1 - alpha)`` and every rival ``alpha * f(r)``, while
   ``kb_policy._fused_label_scores`` floors every raw label score at ``0.0``
   (``best = 0.0`` before the ``max``) and then normalizes the vector to sum to
   1. So ``f`` lies in ``[0, 1]`` and ``sum f <= 1`` BY CONSTRUCTION, whatever
   the ranker returns. The worst case for the direct label is therefore
   ``f(d) = 0, f(r) = 1``, which gives the margin ``(1 - alpha) - alpha =
   1 - 2*alpha``. At the frozen ``alpha = 0.45`` that is ``+0.10 > 1e-9``, the
   tie tolerance ``_argmax_labels`` uses -- so a recovered direct label is the
   UNIQUE argmax for EVERY possible supply, and ``retain ==
   direct-label-recovered`` is a STRUCTURAL property of the policy form rather
   than an empirical observation. This function verifies the ``f`` range on the
   landed trajectories rather than assuming it, and reports the observed worst
   margin against the structural floor.
2. :func:`gold_coverage` -- CEILING B. Of the trajectories that DID dispatch,
   how many received a supply carrying the GOLD tool's own value, and at what
   fused target rank. RECOMPUTED here from the sealed attempt-4 supply records,
   not quoted from the admission-scale sweep's pre-flight projection.
3. :func:`conditional_conversion` -- among dispatched trajectories whose supply
   carried the gold value, what share ended correct under BLEND, against the
   SLURP anchors imported from :mod:`k1_hybrid_ranking_gate`.
4. :func:`decompose` -- the closing arithmetic on both carriers.

THE FIDELITY GATE IS NECESSARY, NOT DECORATIVE, and it was fixed in the
registration before any number was seen: no gold-coverage number may be read
unless the offline supply replay reproduces the flight's OWN landed per-sample
supply on 104 of 104 A2T trajectories. :func:`run` refuses otherwise.

REUSE, NEVER REIMPLEMENTATION. Recall, ranking, admission, fusion and the blend
head all go through ``analysis.dev100_damage_channel_analysis.replay_supply`` /
``replay_blend``, which call ``rails.kb_policy``'s registered ranker, registered
fuser, ``_fused_label_scores``, ``_blend_scores`` and ``_argmax_labels``
directly. The A2T snapshot bundle and the A2T primary-tool label normalizer come
from ``analysis.a2t_admission_scale_sweep``. Answers are scored by the frozen
``a2t-scorer-v1`` through ``rails.adapters.audio2tool.Audio2ToolAdapter.score``.
The SLURP conversion anchors come from ``analysis.k1_hybrid_ranking_gate``. The
SLURP decomposition is READ from the landed DEV-1000 lock-read verdict; no SLURP
run directory is re-scored and no SLURP seal is touched.

GOLD IS SCORING-SIDE ONLY. It is read from sealed records after the seal, never
on a runtime path; no gold value enters a prompt, a query vector or a policy
input. The A2T-G1-104 subset is EXPOSED and its seal was already broken by the
landed G1 read.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``,
``rails/`` or ``core/``. It opens no model session, no embedding sidecar and no
tokenizer: :func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE
the first input is opened and writes the recorded outbound-attempt count into
the receipt. The resident np2 A2T service on port 8090 is never contacted,
probed, reconfigured or stopped.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.cross_carrier_ceiling_decomposition \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import contrast_fewshot_preanalysis as cf
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as audit
from . import k1_hybrid_ranking_gate as k1
from ..rails import kb_policy as kb

EXPOSURE_ROW_ID = "SAEA-SN-MF-CROSS-CARRIER-CEILING-DECOMPOSITION"
SCHEMA = "saea-cross-carrier-ceiling-decomposition-v1"

FROZEN_ALPHA = sweep.FROZEN_ALPHA
FROZEN_WEIGHTS = sweep.FROZEN_WEIGHTS
FROZEN_FUSE = sweep.FROZEN_FUSE
FROZEN_TOP_K = sweep.FROZEN_TOP_K

# --- the sealed A2T G1 attempt-4 BLEND arm (the first flight after the repair)
A2T_RUN_ID = "SAEA-A2T-G1"
A2T_ATTEMPT4_ID = "attempt-20260825T144405Z-a2tg1blend"
A2T_M0_ATTEMPT_ID = "attempt-20260825T100735Z-a2tg1m0"
A2T_CHECK_DIR_RELPATH = sweep.A2T_CHECK_DIR_RELPATH
A2T_ATTEMPT4_REPORT_BASENAME = "arm2-blend-mechanical-report-attempt4.json"
A2T_READ_BASENAME = "g1-read-attempt4.json"

#: Measured on the sealed run directory and asserted before anything is read.
A2T_ATTEMPT4_BLEND_OUTPUTS_SHA256 = (
    "24a7864263226f4918076571aee359d40ee76838f9cea1da2bbae38f6b6bdd18"
)
A2T_M0_OUTPUTS_SHA256 = (
    "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"
)
#: Byte-identical to the attempt-3 Pass-A the admission sweep pinned: attempt 4
#: REPLAYED Pass A rather than re-flying it, and this equality proves it.
A2T_PASS_A_SHA256 = sweep.A2T_PASS_A_SHA256

# --- the landed SLURP DEV-1000 lock read (the comparison carrier, read only)
SLURP_READ_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/"
    "read-verdict.json"
)
SLURP_READ_README_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/"
    "README.md"
)

#: The EXACT v1 counterfactual for the 3 delta-override fires inside the
#: unexposed 500, transcribed from the landed lock-read README section 5.3
#: table ("v1 retain (counterfactual)" column: 1, 1, 1). The override is
#: branch-only, so had it not fired each trajectory would have RETAINED and
#: answered with ITS OWN contact-0 direct decode, whose text the sealed record
#: pins by hash -- which is NOT the same decode as the M0 arm's. Pricing the
#: three at the M0 arm's score instead gives +20.60 pp; the 0.20 pp difference
#: is exactly the one sample (``slurp:devel:002303``) where the two decodes of
#: the same prompt disagree. The lock verdict's +20.80 pp uses this column.
SLURP_OVERRIDE_V1_RETAIN_CORRECT_UNEXPOSED = 3


class DecompositionError(RuntimeError):
    """A pinned identity, a fidelity gate or a closing identity failed."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> str:
    measured = _sha256_file(path)
    if measured != expected:
        raise DecompositionError(
            f"{label}: {path} hashes to {measured}, not the pinned {expected}"
        )
    return measured


# ---------------------------------------------------------------------------
# CEILING A -- the alpha veto
# ---------------------------------------------------------------------------


def alpha_veto_theorem(alpha: float) -> dict[str, object]:
    """The structural statement, with its own arithmetic, and no data at all.

    Read straight off ``kb_policy._blend_scores`` and ``_fused_label_scores``;
    the empirical confirmation lives in :func:`alpha_veto_evidence`."""

    guaranteed_margin = (1.0 - alpha) - alpha
    return {
        "blend_head": (
            "_blend_scores(label) = alpha * fused(label) + (1 - alpha) * "
            "[label == direct_label]"
        ),
        "fused_range_argument": (
            "_fused_label_scores starts each label's raw score at best = 0.0 and "
            "only ever takes max(best, strength), so raw >= 0 for every label "
            "WHATEVER the ranker returns -- a negative or unbounded candidate "
            "score cannot make a raw label score negative. It then divides by "
            "total = sum(raw) when total > 0 and returns all-zeros otherwise. "
            "Therefore fused(label) in [0, 1] and sum(fused) in {0, 1}, by "
            "construction and not by measurement."
        ),
        "worst_case_for_the_direct_label": (
            "fused(direct) = 0 and some rival at fused(rival) = 1, which "
            "sum(fused) <= 1 allows only when the rival takes the whole mass"
        ),
        "alpha": alpha,
        "direct_label_floor": 1.0 - alpha,
        "rival_ceiling": alpha,
        "guaranteed_margin_1_minus_2alpha": guaranteed_margin,
        "argmax_tie_tolerance": 1e-9,
        "veto_holds": guaranteed_margin > 1e-9,
        "condition": (
            "alpha < 0.5 makes a RECOVERED direct label the strict, unique "
            "argmax of the blend for EVERY possible supply; alpha = 0.5 makes "
            "the worst case an exact tie, which _argmax_labels resolves as a "
            "multi-label best set and the controller therefore DISPATCHES; "
            "alpha > 0.5 lets a supply outvote the direct label."
        ),
        "consequence": (
            "under the locked cell 'retain == direct-label-recovered' is a "
            "PROPERTY OF THE POLICY FORM, not an empirical finding: evidence "
            "can only ever reach trajectories from which no direct label was "
            "recovered. The reachable set is the label-free set, exactly."
        ),
        "carve_out": (
            "the equivalence needs the trajectory to REACH the blend at all: "
            "kb_policy._advance_after_direct returns early when recall is empty "
            "or the fuser selects nothing, and such a trajectory retains without "
            "a blend being formed. Both counts are reported per carrier."
        ),
    }


def alpha_veto_evidence(
    *,
    label_targets: Mapping[str, str],
    blends: Mapping[str, dc.BlendReplay],
    direct_labels: Mapping[str, str | None],
    alpha: float,
) -> dict[str, object]:
    """Confirm the theorem's premise on the landed trajectories.

    Verifies the ``fused`` range empirically -- the theorem does not need this,
    but a reviewer is entitled to see that the code's guarantee and the flown
    numbers agree."""

    fused_min = 1.0
    fused_max = 0.0
    sum_min = 1.0
    sum_max = 0.0
    worst_observed_margin: float | None = None
    worst_sample: str | None = None
    retained = 0
    for sample_id, blend in blends.items():
        scores = blend.fused_label_scores
        total = sum(scores.values())
        sum_min = min(sum_min, total)
        sum_max = max(sum_max, total)
        if scores:
            fused_min = min(fused_min, min(scores.values()))
            fused_max = max(fused_max, max(scores.values()))
        direct = direct_labels[sample_id]
        if direct is None:
            continue
        retained += 1
        blended = blend.blended
        direct_score = blended[direct]
        rivals = [score for label, score in blended.items() if label != direct]
        margin = direct_score - max(rivals) if rivals else direct_score
        if worst_observed_margin is None or margin < worst_observed_margin:
            worst_observed_margin = margin
            worst_sample = sample_id
    return {
        "trajectories_examined": len(blends),
        "trajectories_with_a_recovered_direct_label": retained,
        "fused_label_score_min": fused_min,
        "fused_label_score_max": fused_max,
        "fused_label_score_sum_min": sum_min,
        "fused_label_score_sum_max": sum_max,
        "fused_range_inside_0_1": fused_min >= 0.0 and fused_max <= 1.0 + 1e-12,
        "fused_sum_never_exceeds_1": sum_max <= 1.0 + 1e-12,
        "worst_observed_direct_minus_best_rival": worst_observed_margin,
        "worst_observed_at": worst_sample,
        "structural_floor_1_minus_2alpha": (1.0 - alpha) - alpha,
        "observed_margin_at_or_above_structural_floor": (
            worst_observed_margin is None
            or worst_observed_margin >= ((1.0 - alpha) - alpha) - 1e-9
        ),
        "label_vocabulary_size": len(label_targets),
    }


# ---------------------------------------------------------------------------
# The sealed A2T attempt-4 material
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2TAttempt4:
    bundle: cf.SnapshotBundle
    inputs: dc.LandedInputs
    sample_ids: tuple[str, ...]
    direct_texts: Mapping[str, str]
    blend_final_texts: Mapping[str, str]
    m0_final_texts: Mapping[str, str]
    gold_primary: Mapping[str, str]
    blend_correct: Mapping[str, bool]
    m0_correct: Mapping[str, bool]
    direct_correct: Mapping[str, bool]
    flown_dispatched: Mapping[str, bool]
    flown_supply: Mapping[str, tuple[str, ...]]
    flown_direct_label_recovered: Mapping[str, bool]
    artifact_hashes: Mapping[str, str]


def _read_jsonl(path: Path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_a2t_attempt4(*, data_root: Path, repo_root: Path) -> A2TAttempt4:
    """The sealed attempt-4 BLEND arm and its M0 comparator, identity-checked."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    check_dir = repo_root / A2T_CHECK_DIR_RELPATH

    report = json.loads(
        (check_dir / A2T_ATTEMPT4_REPORT_BASENAME).read_text(encoding="utf-8")
    )
    if report["attempt_id"] != A2T_ATTEMPT4_ID or report["arm_id"] != "BLEND":
        raise DecompositionError("the pinned A2T report is not the attempt-4 BLEND arm")
    if (
        report["frozen_cell"]["policy_config_sha256"]
        != sweep.FROZEN_POLICY_CONFIG_SHA256
    ):
        raise DecompositionError("the attempt-4 report did not fly the locked v1 cell")

    receipt_path = repo_root / sweep.A2T_SUBSET_RECEIPT_RELPATH
    _require_hash(
        receipt_path, sweep.A2T_SUBSET_RECEIPT_SHA256, "the A2T-G1-104 receipt"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt["split_name"] != sweep.A2T_SPLIT_ID
        or receipt["count"] != sweep.A2T_SPLIT_COUNT
    ):
        raise DecompositionError("the A2T subset receipt identity drifted")
    sample_ids = tuple(sorted(str(item["sample_id"]) for item in receipt["items"]))

    bundle = sweep.load_a2t_bundle(data_root=data_root, repo_root=repo_root)
    run_dir = data_root / "runs" / A2T_RUN_ID / A2T_ATTEMPT4_ID
    m0_dir = data_root / "runs" / A2T_RUN_ID / A2T_M0_ATTEMPT_ID

    _require_hash(
        run_dir / "pass-a-direct-outputs.jsonl",
        A2T_PASS_A_SHA256,
        "the sealed attempt-4 Pass-A direct outputs (byte-identical to attempt 3)",
    )
    _require_hash(
        run_dir / "arm2-blend-outputs.jsonl",
        A2T_ATTEMPT4_BLEND_OUTPUTS_SHA256,
        "the sealed attempt-4 BLEND answers",
    )
    _require_hash(
        m0_dir / "arm1-m0-outputs.jsonl",
        A2T_M0_OUTPUTS_SHA256,
        "the sealed M0 answers",
    )

    direct_texts: dict[str, str] = {}
    for row in _read_jsonl(run_dir / "pass-a-direct-outputs.jsonl"):
        text = str(row["direct_response_text"])
        if _sha256_text(text) != str(row["direct_response_sha256"]):
            raise DecompositionError(
                f"{row['sample_id']}: Pass-A text does not hash to its own record"
            )
        direct_texts[str(row["sample_id"])] = text
    if tuple(sorted(direct_texts)) != sample_ids:
        raise DecompositionError("the landed Pass-A texts do not cover the subset")

    query_vectors: dict[str, tuple[float, ...]] = {}
    text_digests: dict[str, str] = {}
    for record in _read_jsonl(run_dir / "query-vectors.jsonl"):
        contact_id = str(record["contact_id"])
        if not contact_id.startswith("query:"):
            continue
        sample_id = contact_id.split("query:", 1)[1]
        query_vectors[sample_id] = tuple(float(v) for v in record["values"])
        text_digests[sample_id] = str(record["text_sha256"])
    missing = set(sample_ids) - set(query_vectors)
    if missing:
        raise DecompositionError(f"{len(missing)} samples have no landed query vector")
    for sample_id in sample_ids:
        if _sha256_text(direct_texts[sample_id]) != text_digests[sample_id]:
            raise DecompositionError(
                f"{sample_id}: the Pass-A text does not re-hash to the digest its own "
                "landed query-vector record carries"
            )

    mechanical = json.loads(
        (run_dir / "arm2-blend-mechanical.json").read_text(encoding="utf-8")
    )
    flown_dispatched = {
        sample_id: not bool(mechanical[sample_id]["retained_primary"])
        for sample_id in sample_ids
    }
    flown_supply = {
        sample_id: tuple(
            sorted(mechanical[sample_id].get("fusion_selected_value_ids") or ())
        )
        for sample_id in sample_ids
    }
    flown_recovered = {
        sample_id: bool(mechanical[sample_id]["direct_label_recovered"])
        for sample_id in sample_ids
    }

    blend_final: dict[str, str] = {}
    for row in _read_jsonl(run_dir / "arm2-blend-outputs.jsonl"):
        blend_final[str(row["sample_id"])] = str(row["final_response_text"])
    m0_final: dict[str, str] = {}
    for row in _read_jsonl(m0_dir / "arm1-m0-outputs.jsonl"):
        m0_final[str(row["sample_id"])] = str(row["final_response_text"])
    if tuple(sorted(blend_final)) != sample_ids or tuple(sorted(m0_final)) != sample_ids:
        raise DecompositionError("an answer file does not cover the subset exactly")

    from ..data.audio2tool import load_expected_calls
    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.adapters.audio2tool import Audio2ToolAdapter

    lock = load_lock(umbrella_lock_path(repo_root))
    adapter = Audio2ToolAdapter(lock, data_root, repo_root=repo_root)
    gold_calls = load_expected_calls(lock, data_root, repo_root=repo_root)

    gold_primary: dict[str, str] = {}
    blend_correct: dict[str, bool] = {}
    m0_correct: dict[str, bool] = {}
    direct_correct: dict[str, bool] = {}
    for sample_id in sample_ids:
        calls = gold_calls.get(sample_id)
        if not calls:
            raise DecompositionError(f"{sample_id}: no gold tool calls")
        gold_primary[sample_id] = str(calls[0].name)
        scoring_sample = sweep._a2t_scoring_sample(sample_id)
        blend_correct[sample_id] = (
            float(adapter.score(scoring_sample, blend_final[sample_id])["tool_accuracy"])
            == 1.0
        )
        m0_correct[sample_id] = (
            float(adapter.score(scoring_sample, m0_final[sample_id])["tool_accuracy"])
            == 1.0
        )
        direct_correct[sample_id] = (
            float(
                adapter.score(scoring_sample, direct_texts[sample_id])["tool_accuracy"]
            )
            == 1.0
        )

    facet_vectors = cf._facet_vector_lookup(bundle)
    inputs = dc.LandedInputs(
        snapshot=bundle.snapshot,
        snapshot_sha256=bundle.snapshot_sha256,
        facet_vector_ids=bundle.facet_ids,
        facet_vector_matrix=bundle.matrix,
        facet_vectors=facet_vectors,
        facet_npz_sha256=bundle.npz_sha256,
        query_vectors=query_vectors,
        direct_texts=direct_texts,
        evidence_texts={},
        logged_supply=flown_supply,
        logged_winner_labels={},
        gold_by_sample=gold_primary,
        round_scores={},
        round_reports={},
        label_targets=bundle.label_targets,
        label_texts=bundle.label_texts,
        values_by_id=bundle.values_by_id,
        content_facet_target=bundle.content_facet_target,
    )

    return A2TAttempt4(
        bundle=bundle,
        inputs=inputs,
        sample_ids=sample_ids,
        direct_texts=direct_texts,
        blend_final_texts=blend_final,
        m0_final_texts=m0_final,
        gold_primary=gold_primary,
        blend_correct=blend_correct,
        m0_correct=m0_correct,
        direct_correct=direct_correct,
        flown_dispatched=flown_dispatched,
        flown_supply=flown_supply,
        flown_direct_label_recovered=flown_recovered,
        artifact_hashes={
            A2T_ATTEMPT4_REPORT_BASENAME: _sha256_file(
                check_dir / A2T_ATTEMPT4_REPORT_BASENAME
            ),
            A2T_READ_BASENAME: _sha256_file(check_dir / A2T_READ_BASENAME),
            "pass-a-direct-outputs.jsonl": A2T_PASS_A_SHA256,
            "arm2-blend-outputs.jsonl": A2T_ATTEMPT4_BLEND_OUTPUTS_SHA256,
            "arm2-blend-mechanical.json": _sha256_file(
                run_dir / "arm2-blend-mechanical.json"
            ),
            "query-vectors.jsonl": _sha256_file(run_dir / "query-vectors.jsonl"),
            "arm1-m0-outputs.jsonl": A2T_M0_OUTPUTS_SHA256,
            "snapshot": bundle.snapshot_sha256,
            "content-facet-npz": bundle.npz_sha256,
            "kb_policy.py": _sha256_file(
                repo_root
                / "src/speech_aware_evidence_acquisition/rails/kb_policy.py"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Replay + fidelity gate
# ---------------------------------------------------------------------------


def replay_population(
    carrier: A2TAttempt4,
) -> tuple[
    dict[str, dc.SupplyReplay], dict[str, dc.BlendReplay], dict[str, str | None]
]:
    """Recall -> rank -> fuse -> blend for all 104, at the locked knobs."""

    supplies: dict[str, dc.SupplyReplay] = {}
    blends: dict[str, dc.BlendReplay] = {}
    direct_labels: dict[str, str | None] = {}
    for sample_id in carrier.sample_ids:
        supply = dc.replay_supply(
            carrier.inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
        )
        label = sweep.a2t_label_normalizer(
            carrier.direct_texts[sample_id], carrier.inputs.label_targets
        )
        blend = dc.replay_blend(
            carrier.inputs, supply, direct_label=label, alpha=FROZEN_ALPHA
        )
        supplies[sample_id] = supply
        blends[sample_id] = blend
        direct_labels[sample_id] = label
    return supplies, blends, direct_labels


def fidelity_gate(
    carrier: A2TAttempt4,
    supplies: Mapping[str, dc.SupplyReplay],
    blends: Mapping[str, dc.BlendReplay],
    direct_labels: Mapping[str, str | None],
) -> dict[str, object]:
    """The pre-registered necessary condition, computed before any gold number."""

    supply_matches = 0
    supply_mismatches: list[str] = []
    dispatch_matches = 0
    dispatch_mismatches: list[str] = []
    label_matches = 0
    label_mismatches: list[str] = []
    empty_recall = 0
    empty_supply = 0
    for sample_id in carrier.sample_ids:
        replayed = tuple(sorted(supplies[sample_id].selected_value_ids))
        flown = tuple(sorted(carrier.flown_supply[sample_id]))
        # The flight only records a supply for trajectories it dispatched; a
        # retained trajectory carries null. Compare on the dispatched set, and
        # assert the retained set is exactly the null set.
        if carrier.flown_dispatched[sample_id]:
            if replayed == flown:
                supply_matches += 1
            else:
                supply_mismatches.append(sample_id)
        elif flown == ():
            supply_matches += 1
        else:
            supply_mismatches.append(sample_id)
        replay_dispatched = bool(supplies[sample_id].selected_value_ids) and not blends[
            sample_id
        ].retain_primary
        if replay_dispatched == carrier.flown_dispatched[sample_id]:
            dispatch_matches += 1
        else:
            dispatch_mismatches.append(sample_id)
        if (direct_labels[sample_id] is not None) == carrier.flown_direct_label_recovered[
            sample_id
        ]:
            label_matches += 1
        else:
            label_mismatches.append(sample_id)
        if not supplies[sample_id].recall_scores:
            empty_recall += 1
        if not supplies[sample_id].selected_value_ids:
            empty_supply += 1
    return {
        "population": len(carrier.sample_ids),
        "supply_reproduced": supply_matches,
        "supply_mismatch_ids": supply_mismatches,
        "dispatch_decision_reproduced": dispatch_matches,
        "dispatch_mismatch_ids": dispatch_mismatches,
        "direct_label_recovery_reproduced": label_matches,
        "direct_label_mismatch_ids": label_mismatches,
        "trajectories_with_empty_recall": empty_recall,
        "trajectories_with_empty_supply": empty_supply,
        "semantics": (
            "the flight records fusion_selected_value_ids only for a trajectory it "
            "dispatched; a retained trajectory carries null. The dispatched set is "
            "compared value-id for value-id and the retained set is asserted null."
        ),
        "gate_passed": (
            supply_matches == len(carrier.sample_ids)
            and dispatch_matches == len(carrier.sample_ids)
            and label_matches == len(carrier.sample_ids)
        ),
    }


# ---------------------------------------------------------------------------
# CEILING B -- gold coverage inside the admitted window
# ---------------------------------------------------------------------------


def gold_coverage(
    carrier: A2TAttempt4,
    supplies: Mapping[str, dc.SupplyReplay],
    blends: Mapping[str, dc.BlendReplay],
) -> dict[str, object]:
    """Of the trajectories that DISPATCHED, how many got gold, and at what rank."""

    per_sample: dict[str, dict[str, object]] = {}
    for sample_id in carrier.sample_ids:
        supply = supplies[sample_id]
        blend = blends[sample_id]
        gold = carrier.gold_primary[sample_id]
        admitted = tuple(sorted(supply.admitted_facet_ids))
        gold_facet_admitted = any(
            carrier.bundle.content_facet_target.get(facet_id) == gold
            for facet_id in admitted
        )
        supplied_targets = tuple(
            sorted(
                {
                    str(carrier.bundle.values_by_id[value_id].task_target)
                    for value_id in supply.selected_value_ids
                    if carrier.bundle.values_by_id[value_id].task_target is not None
                }
            )
        )
        fused_ranked = cf._fused_ranked_targets(
            blend.fused_label_scores, carrier.inputs.label_targets
        )
        gold_rank = next(
            (
                position
                for position, (target, _score) in enumerate(fused_ranked, start=1)
                if target == gold
            ),
            None,
        )
        per_sample[sample_id] = {
            "dispatched": bool(carrier.flown_dispatched[sample_id]),
            "gold_primary_tool": gold,
            "gold_facet_inside_admitted_window": gold_facet_admitted,
            "gold_supplied": gold in supplied_targets,
            "gold_fused_target_rank": gold_rank,
            "supplied_targets": supplied_targets,
            "supplied_value_count": len(supply.selected_value_ids),
            "m0_correct": bool(carrier.m0_correct[sample_id]),
            "direct_correct": bool(carrier.direct_correct[sample_id]),
            "blend_correct": bool(carrier.blend_correct[sample_id]),
        }

    dispatched = [
        sample_id
        for sample_id in carrier.sample_ids
        if carrier.flown_dispatched[sample_id]
    ]
    retained = [
        sample_id
        for sample_id in carrier.sample_ids
        if not carrier.flown_dispatched[sample_id]
    ]
    rank_hist: dict[str, int] = {}
    for sample_id in dispatched:
        rank = per_sample[sample_id]["gold_fused_target_rank"]
        key = str(rank) if rank else "absent"
        rank_hist[key] = rank_hist.get(key, 0) + 1
    return {
        "dispatched_n": len(dispatched),
        "retained_n": len(retained),
        "dispatched_ids": dispatched,
        "dispatched_with_gold_facet_inside_admitted_window": sum(
            1 for s in dispatched if per_sample[s]["gold_facet_inside_admitted_window"]
        ),
        "dispatched_with_gold_bearing_supply": sum(
            1 for s in dispatched if per_sample[s]["gold_supplied"]
        ),
        "dispatched_gold_at_fused_rank_1": sum(
            1 for s in dispatched if per_sample[s]["gold_fused_target_rank"] == 1
        ),
        "dispatched_gold_at_fused_rank_2_or_3": sum(
            1
            for s in dispatched
            if per_sample[s]["gold_fused_target_rank"] in (2, 3)
        ),
        "dispatched_gold_absent_from_supply": sum(
            1 for s in dispatched if not per_sample[s]["gold_supplied"]
        ),
        "dispatched_gold_fused_rank_histogram": rank_hist,
        "dispatched_direct_answer_wrong": sum(
            1 for s in dispatched if not per_sample[s]["direct_correct"]
        ),
        "dispatched_direct_answer_correct": sum(
            1 for s in dispatched if per_sample[s]["direct_correct"]
        ),
        "retained_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE": sum(
            1 for s in retained if per_sample[s]["gold_supplied"]
        ),
        "population_with_gold_bearing_supply_IF_ALPHA_DID_NOT_GATE": sum(
            1 for s in carrier.sample_ids if per_sample[s]["gold_supplied"]
        ),
        "per_sample": per_sample,
    }


def conditional_conversion(
    carrier: A2TAttempt4, coverage: Mapping[str, object]
) -> dict[str, object]:
    """Among dispatched-with-gold trajectories, what share ended correct."""

    per_sample = coverage["per_sample"]  # type: ignore[index]
    dispatched = list(coverage["dispatched_ids"])  # type: ignore[arg-type]
    with_gold = [s for s in dispatched if per_sample[s]["gold_supplied"]]
    without_gold = [s for s in dispatched if not per_sample[s]["gold_supplied"]]
    rank1 = [s for s in with_gold if per_sample[s]["gold_fused_target_rank"] == 1]
    rank23 = [s for s in with_gold if per_sample[s]["gold_fused_target_rank"] in (2, 3)]

    def block(ids: Sequence[str], label: str) -> dict[str, object]:
        blend_correct = sum(1 for s in ids if per_sample[s]["blend_correct"])
        m0_correct = sum(1 for s in ids if per_sample[s]["m0_correct"])
        direct_correct = sum(1 for s in ids if per_sample[s]["direct_correct"])
        return {
            "label": label,
            "n": len(ids),
            "sample_ids": list(ids),
            "blend_correct": blend_correct,
            "blend_rate": (blend_correct / len(ids)) if ids else None,
            "m0_arm_correct": m0_correct,
            "own_contact0_direct_correct": direct_correct,
            "blend_minus_m0_samples": blend_correct - m0_correct,
            "blend_minus_own_direct_samples": blend_correct - direct_correct,
        }

    return {
        "a2t_dispatched_all": block(dispatched, "every dispatched trajectory"),
        "a2t_dispatched_with_gold_bearing_supply": block(
            with_gold, "dispatched AND supply carried the gold tool's own value"
        ),
        "a2t_dispatched_gold_at_fused_rank_1": block(rank1, "gold at fused rank 1"),
        "a2t_dispatched_gold_at_fused_rank_2_or_3": block(
            rank23, "gold at fused rank 2-3"
        ),
        "a2t_dispatched_without_gold_bearing_supply": block(
            without_gold, "dispatched AND gold absent from supply"
        ),
        "slurp_anchors": {
            "gold_at_fused_top_1": {
                "rate": k1.ANCHOR_TOP1,
                "measured": "108 / 110",
            },
            "gold_at_fused_rank_2_or_3": {
                "rate": k1.ANCHOR_RANK23,
                "measured": "16 / 23",
            },
            "gold_absent_from_supply": {
                "rate": k1.ANCHOR_ABSENT,
                "measured": "0 / 67",
            },
            "source": (
                "analysis.k1_hybrid_ranking_gate.ANCHOR_TOP1 / ANCHOR_RANK23 / "
                "ANCHOR_ABSENT, pooled over the three sealed SLURP populations; "
                "published in docs/readiness/"
                "2026-08-25-ec-and-retain-override-projections.md section 3 (table "
                "rows '108 / 110', '16 / 23', '0 / 67') and recomputed identically "
                "in docs/readiness/2026-08-25-supply-budget-projection.md section 6"
            ),
        },
        "reading_rule": (
            "MECHANISM READING, NEVER AN EFFECT SIZE. The A2T cells hold at most a "
            "handful of samples and the SLURP anchors were measured on a different "
            "task with a different label space and a different answer shape. The "
            "two are reported side by side with their sample sizes attached; no "
            "interval is computed across them."
        ),
    }


# ---------------------------------------------------------------------------
# The closing arithmetic
# ---------------------------------------------------------------------------


def _pp(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator


def decompose_a2t(
    carrier: A2TAttempt4, coverage: Mapping[str, object]
) -> dict[str, object]:
    """reachable share x within-reach conversion + retain drift, on A2T."""

    per_sample = coverage["per_sample"]  # type: ignore[index]
    n = len(carrier.sample_ids)
    dispatched = list(coverage["dispatched_ids"])  # type: ignore[arg-type]
    retained = [s for s in carrier.sample_ids if s not in set(dispatched)]

    def subgroup(ids: Sequence[str]) -> dict[str, object]:
        blend_correct = sum(1 for s in ids if per_sample[s]["blend_correct"])
        m0_correct = sum(1 for s in ids if per_sample[s]["m0_correct"])
        w2c = sum(
            1
            for s in ids
            if per_sample[s]["blend_correct"] and not per_sample[s]["m0_correct"]
        )
        c2w = sum(
            1
            for s in ids
            if per_sample[s]["m0_correct"] and not per_sample[s]["blend_correct"]
        )
        return {
            "n": len(ids),
            "share_of_population": len(ids) / n,
            "m0_correct": m0_correct,
            "blend_correct": blend_correct,
            "delta_samples": blend_correct - m0_correct,
            "within_subgroup_delta_pp": (
                _pp(blend_correct - m0_correct, len(ids)) if ids else 0.0
            ),
            "population_contribution_pp": _pp(blend_correct - m0_correct, n),
            "w2c": w2c,
            "c2w": c2w,
        }

    reach = subgroup(dispatched)
    drift = subgroup(retained)
    total_m0 = sum(1 for s in carrier.sample_ids if per_sample[s]["m0_correct"])
    total_blend = sum(1 for s in carrier.sample_ids if per_sample[s]["blend_correct"])
    observed_pp = _pp(total_blend - total_m0, n)
    reconstructed_pp = (
        float(reach["population_contribution_pp"])
        + float(drift["population_contribution_pp"])
    )
    return {
        "carrier": "audio2tool / A2T-G1-104 (EXPOSED)",
        "metric": "tool accuracy (a2t-scorer-v1 tool-name multiset equality)",
        "n": n,
        "m0_correct": total_m0,
        "blend_correct": total_blend,
        "observed_population_delta_pp": observed_pp,
        "reachable_subgroup_dead_direct_dispatch": reach,
        "unreachable_subgroup_retain_primary": drift,
        "reconstructed_population_delta_pp": reconstructed_pp,
        "closes_exactly": abs(reconstructed_pp - observed_pp) < 1e-9,
        "identity": (
            "the two subgroups partition the population, so the reconstruction is "
            "an exact identity and closure is a CHECK on the read, not a result. "
            "The content is in the two FACTORS: the reachable share and the "
            "within-reach conversion."
        ),
    }


def decompose_slurp(*, repo_root: Path) -> dict[str, object]:
    """The same decomposition, READ from the landed DEV-1000 lock verdict."""

    path = Path(repo_root) / SLURP_READ_RELPATH
    verdict = json.loads(path.read_text(encoding="utf-8"))
    if verdict.get("exposure_row_id") != "SAEA-SN-MF-DEV1000-LOCK-READ":
        raise DecompositionError("the pinned SLURP read verdict identity drifted")
    n = int(verdict["populations"]["unexposed_new500_n"])
    dec = verdict["secondaries"]["dispatch_decomposition_unexposed500"]
    primary = verdict["primary"]
    mech = verdict["mechanical_cross_checks"]["blend_dispatch_decomposition_exact"]

    dead = dec["dead_direct_dispatch"]
    override = dec["override_dispatch"]
    retain = dec["retain_primary"]

    def block(entry: Mapping[str, object], label: str) -> dict[str, object]:
        count = int(entry["n"])
        delta = int(entry["delta_samples"])
        return {
            "label": label,
            "n": count,
            "share_of_population": count / n,
            "m0_correct": int(entry["M0_correct"]),
            "blend_correct": int(entry["BLEND_correct"]),
            "delta_samples": delta,
            "within_subgroup_delta_pp": _pp(delta, count),
            "population_contribution_pp": _pp(delta, n),
            "w2c": int(entry["w2c"]),
            "c2w": int(entry["c2w"]),
        }

    reach = block(dead, "dead-direct dispatch (the reachable set under v1)")
    override_block = block(
        override, "delta retain-override dispatch (v2 ONLY -- removed from the lock)"
    )
    drift = block(retain, "retain-primary (the alpha-vetoed set)")
    observed_pp = float(primary["delta_pp"])
    reconstructed_pp = (
        float(reach["population_contribution_pp"])
        + float(override_block["population_contribution_pp"])
        + float(drift["population_contribution_pp"])
    )
    # The LOCKED cell is v1: the 3 override trajectories would have retained and
    # answered with their OWN contact-0 direct decode. The landed lock-read
    # README section 5.3 records that counterfactual exactly.
    v1_blend_correct = (
        int(reach["blend_correct"])
        + int(drift["blend_correct"])
        + SLURP_OVERRIDE_V1_RETAIN_CORRECT_UNEXPOSED
    )
    v1_pp = _pp(v1_blend_correct - int(primary["M0_correct"]), n)
    v1_pp_if_priced_at_the_m0_arm = (
        float(reach["population_contribution_pp"])
        + float(drift["population_contribution_pp"])
    )
    return {
        "carrier": "slurp / DEV-1000 unexposed NEW500",
        "metric": "scenario_action exact intent accuracy",
        "n": n,
        "source": SLURP_READ_RELPATH,
        "source_sha256": _sha256_file(path),
        "m0_correct": int(primary["M0_correct"]),
        "blend_correct": int(primary["BLEND_correct"]),
        "observed_population_delta_pp_as_flown_v2": observed_pp,
        "reachable_subgroup_dead_direct_dispatch": reach,
        "override_subgroup_v2_only": override_block,
        "unreachable_subgroup_retain_primary": drift,
        "reconstructed_population_delta_pp_as_flown_v2": reconstructed_pp,
        "closes_exactly_as_flown": abs(reconstructed_pp - observed_pp) < 1e-9,
        "locked_v1_blend_correct": v1_blend_correct,
        "locked_v1_population_delta_pp": v1_pp,
        "locked_v1_override_retain_counterfactual_correct": (
            SLURP_OVERRIDE_V1_RETAIN_CORRECT_UNEXPOSED
        ),
        "locked_v1_counterfactual_source": (
            SLURP_READ_README_RELPATH + " section 5.3, 'v1 retain (counterfactual)' "
            "column of the 14-fire table, restricted to the 3 UNEXPOSED rows "
            "(slurp:devel:002303, 002955, 014737): 1, 1, 1"
        ),
        "locked_v1_population_delta_pp_if_priced_at_the_m0_arm": (
            v1_pp_if_priced_at_the_m0_arm
        ),
        "locked_v1_note": (
            "the LOCKED cell is v1, which carries no override; the 3 override "
            "trajectories would have RETAINED and answered with their own "
            "contact-0 direct decode. Priced at that landed counterfactual the "
            "unexposed-500 margin is the +20.80 pp the lock verdict section 3 "
            "records (382/500). Priced instead at the M0 ARM's decode of the "
            "same prompts it reads +20.60 pp; the 0.20 pp gap is exactly the "
            "one sample (slurp:devel:002303) where the two decodes disagree, "
            "and it is arm-level decode variance, not an arithmetic difference."
        ),
        "direct_labels_recovered_unexposed500": int(retain["n"]) + int(override["n"]),
        "pooled1000_cross_check": {
            "direct_labels_recovered": int(mech["direct_labels_recovered"]),
            "dead_direct_dispatched": int(mech["dead_direct_dispatched"]),
            "retain_primary": int(mech["retain_primary"]),
            "override_dispatched": int(mech["override_dispatched"]),
        },
    }


def cross_carrier_table(
    a2t: Mapping[str, object], slurp: Mapping[str, object]
) -> dict[str, object]:
    a2t_reach = a2t["reachable_subgroup_dead_direct_dispatch"]  # type: ignore[index]
    slurp_reach = slurp["reachable_subgroup_dead_direct_dispatch"]  # type: ignore[index]
    a2t_share = float(a2t_reach["share_of_population"])  # type: ignore[index]
    slurp_share = float(slurp_reach["share_of_population"])  # type: ignore[index]
    a2t_conv = float(a2t_reach["within_subgroup_delta_pp"])  # type: ignore[index]
    slurp_conv = float(slurp_reach["within_subgroup_delta_pp"])  # type: ignore[index]
    return {
        "reachable_share": {"a2t": a2t_share, "slurp_unexposed500": slurp_share},
        "reachable_share_ratio_slurp_over_a2t": slurp_share / a2t_share,
        "within_reach_conversion_pp": {"a2t": a2t_conv, "slurp_unexposed500": slurp_conv},
        "within_reach_conversion_ratio_slurp_over_a2t": (
            slurp_conv / a2t_conv if a2t_conv else None
        ),
        "reach_times_conversion_pp": {
            "a2t": a2t_share * a2t_conv,
            "slurp_unexposed500": slurp_share * slurp_conv,
        },
        "retain_drift_pp": {
            "a2t": float(
                a2t["unreachable_subgroup_retain_primary"]["population_contribution_pp"]  # type: ignore[index]
            ),
            "slurp_unexposed500": float(
                slurp["unreachable_subgroup_retain_primary"][  # type: ignore[index]
                    "population_contribution_pp"
                ]
            ),
        },
        "reading": (
            "the two carriers differ on BOTH factors and they multiply. Neither "
            "factor alone explains the magnitude gap."
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    package_file = Path(kb.__file__).resolve()
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise DecompositionError(
            f"imported rails.kb_policy from {package_file}, not this checkout"
        )

    carrier = load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    supplies, blends, direct_labels = replay_population(carrier)
    gate = fidelity_gate(carrier, supplies, blends, direct_labels)
    if not gate["gate_passed"]:
        raise DecompositionError(
            "the pre-registered fidelity gate FAILED; no gold number is read: "
            + json.dumps(gate)
        )

    theorem = alpha_veto_theorem(FROZEN_ALPHA)
    evidence = alpha_veto_evidence(
        label_targets=carrier.inputs.label_targets,
        blends=blends,
        direct_labels=direct_labels,
        alpha=FROZEN_ALPHA,
    )
    coverage = gold_coverage(carrier, supplies, blends)
    conversion = conditional_conversion(carrier, coverage)
    a2t_dec = decompose_a2t(carrier, coverage)
    slurp_dec = decompose_slurp(repo_root=repo_root)
    table = cross_carrier_table(a2t_dec, slurp_dec)

    report: dict[str, object] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "outbound_connection_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
            "gold_opened": (
                "SCORING-SIDE ONLY, over the EXPOSED A2T-G1-104 whose seal the "
                "landed G1 read already broke; never on a runtime path"
            ),
        },
        "frozen_cell": {
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_FUSE.tau,
            "m": FROZEN_FUSE.m,
            "c": FROZEN_FUSE.c,
            "top_l": FROZEN_FUSE.top_l,
            "top_k": FROZEN_TOP_K,
            "weights": {
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
            "policy_config_sha256_at_flight": sweep.FROZEN_POLICY_CONFIG_SHA256,
        },
        "artifact_hashes": dict(carrier.artifact_hashes),
        "fidelity_gate": gate,
        "ceiling_a_alpha_veto": {"theorem": theorem, "evidence": evidence},
        "ceiling_b_gold_coverage": coverage,
        "conditional_conversion": conversion,
        "decomposition": {
            "audio2tool": a2t_dec,
            "slurp_unexposed500": slurp_dec,
            "cross_carrier": table,
        },
        "hard_stop": (
            "CONSOLIDATION READ ONLY. No knob is changed, no flight is authorized, "
            "no G2 is opened, no test contact is taken, and no generality or "
            "superiority claim follows from this artifact."
        ),
    }
    report["wall_seconds"] = round(time.perf_counter() - started, 3)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = run(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        out_path=Path(args.out),
    )
    print(json.dumps(report["fidelity_gate"], indent=1))
    print(json.dumps(report["decomposition"]["cross_carrier"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
