"""The ONE registered one-shot read of the SEALED DEV-500 confirmatory campaign.

Exposure row ``SAEA-SN-MF-DEV500-CONFIRMATORY-READ`` (registered before any
computation, ledger commit ``405000ee``): zero frozen-core contacts, zero
embedding-tool contacts, zero tokenizer contacts, zero HTTP or socket
requests. Everything this module reads is already landed and sealed -- the
four committed per-arm mechanical reports, the four sealed attempt stores'
per-sample outputs, the BLEND arm's own landed query vectors, the pinned
TRAIN knowledge snapshot with its content-facet vector NPZ (value vectors
stay SEALED), the three committed split receipts, and SLURP devel gold read
strictly scoring-side.

One-shot semantics
------------------
The preregistration
(``docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md``
section 1) and its machine-readable twin
(``configs/experiment/slurp-dev500-confirmatory-campaign-v1.json``,
``dev500_confirmatory_statistic``) froze the statistic BEFORE the arms flew.
This module computes it EXACTLY as frozen, exactly once. No threshold may be
changed, no parameter re-tried, no partial re-read performed, no arm
re-flown, whatever the outcome. A second execution of this module against
these same pinned bytes is a reproducibility check and can never become a
second read -- which is precisely why every input is pinned by sha256 and a
mismatch is a fail-closed :class:`ReadError`, never a warning.

The primary statistic
---------------------
Paired per-sample ``BLEND - M0`` over the **400 UNEXPOSED samples only**
(DEV-500 minus the nested, prior-exposed DEV-100), a paired cluster
bootstrap at N=10,000 / seed 20260807 with 90% and 95% percentile CIs, and
McNemar exact on the discordant pairs. **Claim condition (preregistered):
the 90% CI excludes zero.** The exposed 100 are scored and reported
separately and NEVER pooled into the claim.

Registered secondaries (reported, no claim attaches)
----------------------------------------------------
The exposed-100 pair on its own and the pooled 500 descriptively; ABL-RANDRET
vs BLEND on the NEW400 (same fusion path, randomized retrieval signal);
ABL-RANDICL vs BLEND and vs M0 on the NEW400 (retrieval vs generic in-context
conditioning); the retrieval-reachability ceiling; wrong-to-correct and
correct-to-wrong tables per comparison; per-scenario accuracy and confusion;
and the retain-primary vs dispatched subgroup accuracies.

The oracle substitution, disclosed wherever the ceiling is cited
----------------------------------------------------------------
The literature-standard oracle/GT-prompt retrieval ceiling requires
gold-conditioned supply at RUNTIME, which this repository's immutable
charter forbids, so that arm was never flown. The registered substitute is
the ANALYTIC retrieval-reachability ceiling: where the gold-bearing content
facet sits in the full cosine ordering of the query against all landed
content facets, and hence ``recall@k`` for the frozen ``top_k`` and beyond.
It bounds what RETRIEVAL could have reached. It says nothing about what the
frozen core would have answered given that supply, and no such reading may
be taken from it.

Deliberate reuse
----------------
:mod:`.bootstrap` owns the registration-mandated resampling primitive with
the mandated seed; :mod:`.dev100_reviewer_audit` owns the gain-statistic
wrapper, the McNemar accounting and the offline guard;
:mod:`.dev100_damage_channel_analysis` owns the identity-checked devel-gold
reader and the ``kb_policy``-pinned reachability arithmetic. All are
IMPORTED, never re-implemented, so this read and the two sealed DEV-100
analyses read identical bytes through identical code and cannot drift apart.

Scoring path
------------
:func:`score_arm` calls ``reproduction.slurp_scoring.parse_slu_response``
followed by ``score_slu`` and takes ``scenario_action_exact`` as the
correctness predicate -- byte-for-byte the same computation
``rails.adapters.slurp.SlurpAdapter.score`` performs, which is the call the
sealed DEV-100 round launchers made post-seal. The read therefore cannot
score differently from the campaign it is reading.

Scope (preregistration section 5, binding)
------------------------------------------
Dev-tier confirmatory. NO test claim, NO generalization claim, NO
controller/RL claim. FINAL60 and test remain untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from ..reproduction.slurp_scoring import parse_slu_response, score_slu

SCHEMA = "saea-dev500-confirmatory-read-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-DEV500-CONFIRMATORY-READ"
RUN_ID = "SAEA-DEV500-CONFIRMATORY"

PREREGISTRATION_RELPATH = "docs/readiness/2026-08-24-dev500-confirmatory-preregistration.md"
CAMPAIGN_FRAGMENT_RELPATH = "configs/experiment/slurp-dev500-confirmatory-campaign-v1.json"
CHECK_DIR_RELPATH = "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory"

# Verbatim from preregistration section 1 -- quoted, never paraphrased.
STATISTIC_CITATION = (
    "Statistic: paired per-sample BLEND - M0 over the 400; paired cluster bootstrap "
    "(N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact test on the discordant pairs. "
    "Claim condition (preregistered): the 90% CI excludes zero."
)
CLAIM_CONDITION = "the 90% CI on the paired per-sample BLEND - M0 gain over the 400 unexposed samples excludes zero"

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260807

# The registered variance prior, carried as registered (preregistration s1).
VARIANCE_PRIOR = "DEV-100 round-5 replication: plus-minus 2 per 100 at 8-slot decode"

# The resident service this read must NOT touch. Byte length and hash are
# measured before and after; equality is the zero-contact proof.
SERVICE_LOG_PATH = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP8-BASE-DEV100-20260824T120910Z/server.log"
)

SNAPSHOT_RELPATH = dc.SNAPSHOT_RELPATH
SNAPSHOT_SHA256 = dc.SNAPSHOT_SHA256
EMBEDDING_RECEIPT_RELPATH = dc.EMBEDDING_RECEIPT_RELPATH

# The frozen cell's own top_k, for which the ceiling's headline recall is quoted.
FROZEN_TOP_K = 5
RECALL_AT_K_GRID = (1, 2, 3, 5, 8, 10, 16, 32, 64, 128)


class ReadError(RuntimeError):
    """A pinned input does not match, or a landed artifact contradicts a
    committed record. Never raised for a legitimate data shape: a one-shot
    read that silently tolerates a contradiction is worse than no read."""


# ---------------------------------------------------------------------------
# Pinned sources
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmPin:
    """One sealed arm: its committed report and its attempt-store bytes."""

    arm_id: str
    arm_index: int
    attempt_id: str
    report_basename: str
    report_sha256: str
    outputs_basename: str
    outputs_sha256: str
    mechanical_basename: str
    mechanical_sha256: str
    expected_samples: int
    population: str


ARM_PINS = (
    ArmPin(
        arm_id="M0",
        arm_index=1,
        attempt_id="attempt-20260824T203716Z-dev500m0",
        report_basename="arm1-m0-mechanical-report.json",
        report_sha256="22bd0d1a26b5f7f27200893dea67c4537e2eaad3350bfedd8e19527a22b15979",
        outputs_basename="arm1-m0-outputs.jsonl",
        outputs_sha256="d09fbf479a5bb48b9ff69d1499e01ed5f233bbce20b4c6196ba5bbbed787629d",
        mechanical_basename="arm1-m0-mechanical.json",
        mechanical_sha256="76e5dfc94b4d6de03d9fa57ebb1f9db07e47b9dc7126f42ae0baf55212d57704",
        expected_samples=500,
        population="DEV-500",
    ),
    ArmPin(
        arm_id="BLEND",
        arm_index=2,
        attempt_id="attempt-20260824T205527Z-dev500blend",
        report_basename="arm2-blend-mechanical-report.json",
        report_sha256="d7a6b159b94a95e5524e02ba94076b93286fa5056cf73f397743587959cbffff",
        outputs_basename="arm2-blend-outputs.jsonl",
        outputs_sha256="3ae9fef0c75cbceb7d008115522df8854d0a0db473cd553c1c44f4b7200efe0b",
        mechanical_basename="arm2-blend-mechanical.json",
        mechanical_sha256="164210fbaf954d36459e62c14b61c927e31c5be38273aee155b96a9ae29bb52b",
        expected_samples=500,
        population="DEV-500",
    ),
    ArmPin(
        arm_id="ABL-RANDRET",
        arm_index=3,
        attempt_id="attempt-20260824T212928Z-dev500randret",
        report_basename="arm3-randret-mechanical-report.json",
        report_sha256="8a860273d00c0a932d1dd57ad71bcc09913b28a29412bdf5deb996f4763a040d",
        outputs_basename="arm3-randret-outputs.jsonl",
        outputs_sha256="aa0bab8fb606da5da0ff7a8db305b0e8a3cae77e48ea96b33dbe7b3d05015890",
        mechanical_basename="arm3-randret-mechanical.json",
        mechanical_sha256="1fc2cfd7acb0a0cc36b42c78cbc36d45f61952a6671d339666dcd19842fe91ef",
        expected_samples=400,
        population="DEV-500-NEW400",
    ),
    ArmPin(
        arm_id="ABL-RANDICL",
        arm_index=4,
        attempt_id="attempt-20260824T213948Z-dev500randicl",
        report_basename="arm4-randicl-mechanical-report.json",
        report_sha256="be3d210d9d7244e6cb799c1826b928cd877a7a359d0691a193c074b20d51a155",
        outputs_basename="arm4-randicl-outputs.jsonl",
        outputs_sha256="ffbfc92d15d58db694c528864a2120487ff22c2c621ed61917064fb2d2956248",
        mechanical_basename="arm4-randicl-mechanical.json",
        mechanical_sha256="d8417013c22c9ea99f7186c103c815c9ed6e8d177b4d1cd71188a79ff138f14f",
        expected_samples=400,
        population="DEV-500-NEW400",
    ),
)

# Split receipts: (relpath, run_identity_hash, receipt_integrity_hash, n_items).
RECEIPT_PINS = {
    "DEV-500": (
        "docs/receipts/probe-samples/DEV-500.json",
        "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4",
        "c0f1c7531fb8972885abf1d840cc101bbfa38ae04e3929cc46e0f5b9ef35452b",
        500,
    ),
    "DEV-100": (
        "docs/receipts/probe-samples/DEV-100.json",
        "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853",
        "d676d38b4d27b3a136ba2523b96ae3c71ba2b8b436f7712f4f0c976c3ea833e1",
        100,
    ),
    "DEV-500-NEW400": (
        "docs/receipts/probe-samples/DEV-500-NEW400.json",
        "e1cf6fc512a16ec2f1d439655f40b1602ff5e295ec2736cecaf136402a4d036c",
        "36c778dafb418d8f0fb80ad53fb11f2608f3ebcd4ad9f5fa3d964ff16b54898b",
        400,
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> str:
    measured = _sha256_file(path)
    if measured != expected:
        raise ReadError(
            f"{label}: {path} hashes to {measured}, not the registered {expected} -- "
            "the one-shot read STOPS rather than read bytes the ledger row does not pin"
        )
    return measured


# ---------------------------------------------------------------------------
# Populations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Populations:
    """The three id sets, each verified against its committed receipt."""

    dev500: tuple[str, ...]
    dev100: tuple[str, ...]
    new400: tuple[str, ...]
    receipt_hashes: Mapping[str, str]


def load_populations(repo_root: Path) -> Populations:
    """DEV-500, the nested exposed DEV-100, and the unexposed NEW400.

    NEW400 is re-derived here as the deterministic set difference and then
    compared to its own committed receipt, so the claim population is proven
    to be exactly what the campaign fragment registered rather than trusted
    to be."""

    from ..data.splits import split_identity_hash

    ids: dict[str, tuple[str, ...]] = {}
    receipt_hashes: dict[str, str] = {}
    for name, (relpath, run_identity, integrity, n_items) in RECEIPT_PINS.items():
        path = Path(repo_root) / relpath
        receipt = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(str(item["id"]) for item in receipt["items"])
        if len(items) != n_items or len(set(items)) != n_items:
            raise ReadError(f"{name} receipt is not {n_items} distinct ids")
        if str(receipt["run_identity_hash"]) != run_identity:
            raise ReadError(f"{name} receipt run identity hash is not the registered {run_identity}")
        if str(receipt["split_identity_hash"]) != integrity:
            raise ReadError(f"{name} receipt integrity hash is not the registered {integrity}")
        rederived = split_identity_hash(f"slurp/{sample_id}" for sample_id in items)
        if rederived != run_identity:
            raise ReadError(
                f"{name}: re-derived identity hash {rederived} != receipt {run_identity}"
            )
        ids[name] = tuple(sorted(items))
        receipt_hashes[name] = _sha256_file(path)

    dev500, dev100, new400 = ids["DEV-500"], ids["DEV-100"], ids["DEV-500-NEW400"]
    if not set(dev100) <= set(dev500):
        raise ReadError("DEV-100 is not nested inside DEV-500")
    derived = tuple(sorted(set(dev500) - set(dev100)))
    if derived != new400:
        raise ReadError(
            "the deterministic set difference DEV-500 minus DEV-100 does not equal the "
            "committed NEW400 receipt -- the claim population is not what was registered"
        )
    return Populations(
        dev500=dev500, dev100=dev100, new400=new400, receipt_hashes=receipt_hashes
    )


# ---------------------------------------------------------------------------
# Sealed arm outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmOutputs:
    """One sealed arm's per-sample responses and mechanical facts."""

    pin: ArmPin
    responses: Mapping[str, str]
    contacts: Mapping[str, int]
    winner_labels: Mapping[str, str | None]
    report: Mapping[str, object]
    run_dir: Path


def load_arm(*, pin: ArmPin, repo_root: Path, data_root: Path) -> ArmOutputs:
    """Load one arm, hash-verifying its committed report AND its sealed
    attempt-store bytes before a single response text is parsed."""

    report_path = Path(repo_root) / CHECK_DIR_RELPATH / pin.report_basename
    _require_hash(report_path, pin.report_sha256, f"{pin.arm_id} committed mechanical report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if str(report["arm_id"]) != pin.arm_id or str(report["attempt_id"]) != pin.attempt_id:
        raise ReadError(f"{pin.arm_id}: committed report names a different arm/attempt")
    if not bool(report.get("mechanical_only")):
        raise ReadError(f"{pin.arm_id}: committed report is not a mechanical-only landing")

    run_dir = Path(data_root) / "runs" / RUN_ID / pin.attempt_id
    if Path(str(report["run_dir"])) != run_dir:
        raise ReadError(f"{pin.arm_id}: committed report's run_dir is not the pinned attempt dir")
    outputs_path = run_dir / pin.outputs_basename
    _require_hash(outputs_path, pin.outputs_sha256, f"{pin.arm_id} sealed outputs")
    _require_hash(
        run_dir / pin.mechanical_basename,
        pin.mechanical_sha256,
        f"{pin.arm_id} sealed per-sample mechanical records",
    )

    responses: dict[str, str] = {}
    contacts: dict[str, int] = {}
    winners: dict[str, str | None] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if str(record["arm"]) != pin.arm_id:
                raise ReadError(f"{pin.arm_id}: outputs carry a foreign arm id {record['arm']!r}")
            sample_id = str(record["sample_id"])
            if sample_id in responses:
                raise ReadError(f"{pin.arm_id}: duplicate sample {sample_id} in the sealed outputs")
            responses[sample_id] = str(record["final_response_text"])
            contacts[sample_id] = int(record["contacts"])
            winner = record.get("winner_label")
            winners[sample_id] = None if winner is None else str(winner)
    if len(responses) != pin.expected_samples:
        raise ReadError(
            f"{pin.arm_id}: sealed outputs carry {len(responses)} samples, not {pin.expected_samples}"
        )

    # The mechanical report's own retain/dispatch counts must equal what the
    # per-sample contact counts say -- two independent sources, cross-checked.
    mechanical = report["mechanical"]
    retained = sum(1 for value in contacts.values() if value == 1)
    dispatched = sum(1 for value in contacts.values() if value == 2)
    if retained != int(mechanical["one_contact_trajectories_retained_primary"]):
        raise ReadError(f"{pin.arm_id}: retain-primary count disagrees with the committed report")
    if dispatched != int(mechanical["two_contact_trajectories_dispatched"]):
        raise ReadError(f"{pin.arm_id}: dispatched count disagrees with the committed report")
    if retained + dispatched != pin.expected_samples:
        raise ReadError(f"{pin.arm_id}: contact counts are not all 1 or 2")

    return ArmOutputs(
        pin=pin,
        responses=responses,
        contacts=contacts,
        winner_labels=winners,
        report=report,
        run_dir=run_dir,
    )


# ---------------------------------------------------------------------------
# Scoring (gold opens here, once, scoring-side)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scored:
    """Per-sample scored outcome for one arm."""

    correct: Mapping[str, int]
    scenario_exact: Mapping[str, int]
    action_exact: Mapping[str, int]
    slot_f1: Mapping[str, float]
    parsed: Mapping[str, bool]
    predicted_scenario: Mapping[str, str | None]
    predicted_action: Mapping[str, str | None]


def score_arm(*, arm: ArmOutputs, gold_by_sample: Mapping[str, object]) -> Scored:
    """The repository's own registered scorer, sample by sample.

    Identical arithmetic to ``rails.adapters.slurp.SlurpAdapter.score``
    (parse, then ``score_slu``, then ``scenario_action_exact``) -- the call
    the sealed round launchers make post-seal, so this read cannot score
    differently from the campaign it reads."""

    correct: dict[str, int] = {}
    scenario_exact: dict[str, int] = {}
    action_exact: dict[str, int] = {}
    slot_f1: dict[str, float] = {}
    parsed_by_sample: dict[str, bool] = {}
    predicted_scenario: dict[str, str | None] = {}
    predicted_action: dict[str, str | None] = {}
    for sample_id, text in arm.responses.items():
        gold = gold_by_sample[sample_id]
        scenario, action, entities, parsed = parse_slu_response(text)
        result = score_slu(
            gold_scenario=gold.scenario,
            gold_action=gold.action,
            gold_entities=gold.entities,
            predicted_scenario=scenario,
            predicted_action=action,
            predicted_entities=tuple(entities),
        )
        correct[sample_id] = 1 if result.scenario_action_exact == 1.0 else 0
        scenario_exact[sample_id] = 1 if result.scenario_exact == 1.0 else 0
        action_exact[sample_id] = 1 if result.action_exact == 1.0 else 0
        # ``slot_f1_exact`` is the (precision, recall, F1) triple; the F1
        # measure is its third member -- the same value the round launchers
        # recorded as ``slot_f1_exact_f1`` from ``as_metrics_dict``.
        slot_f1[sample_id] = float(result.slot_f1_exact[2])
        parsed_by_sample[sample_id] = bool(parsed)
        predicted_scenario[sample_id] = scenario
        predicted_action[sample_id] = action
    return Scored(
        correct=correct,
        scenario_exact=scenario_exact,
        action_exact=action_exact,
        slot_f1=slot_f1,
        parsed=parsed_by_sample,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
    )


# ---------------------------------------------------------------------------
# Paired comparison (the registered shape, used by primary AND secondaries)
# ---------------------------------------------------------------------------


def paired_comparison(
    *,
    label: str,
    population: str,
    sample_ids: Sequence[str],
    baseline_name: str,
    baseline: Mapping[str, int],
    treatment_name: str,
    treatment: Mapping[str, int],
    with_bootstrap: bool = True,
) -> dict[str, object]:
    """One paired contrast in the registered shape.

    ``treatment - baseline`` per sample, arm accuracies, the two movement
    lists (wrong->correct and correct->wrong, reported whatever they show),
    McNemar exact on the discordant pairs, and -- when asked -- the paired
    cluster bootstrap at the mandated N and seed. The bootstrap and McNemar
    implementations are :mod:`.dev100_reviewer_audit`'s own, imported."""

    ids = tuple(sample_ids)
    wrong_to_correct = tuple(
        sid for sid in ids if treatment[sid] - baseline[sid] > 0
    )
    correct_to_wrong = tuple(
        sid for sid in ids if treatment[sid] - baseline[sid] < 0
    )
    baseline_correct = sum(baseline[sid] for sid in ids)
    treatment_correct = sum(treatment[sid] for sid in ids)
    block: dict[str, object] = {
        "label": label,
        "population": population,
        "n": len(ids),
        "baseline_arm": baseline_name,
        "treatment_arm": treatment_name,
        f"{baseline_name}_correct": baseline_correct,
        f"{treatment_name}_correct": treatment_correct,
        f"{baseline_name}_accuracy": baseline_correct / len(ids),
        f"{treatment_name}_accuracy": treatment_correct / len(ids),
        "delta_samples": treatment_correct - baseline_correct,
        "delta_pp": 100.0 * (treatment_correct - baseline_correct) / len(ids),
        "wrong_to_correct_count": len(wrong_to_correct),
        "correct_to_wrong_count": len(correct_to_wrong),
        "wrong_to_correct_sample_ids": list(wrong_to_correct),
        "correct_to_wrong_sample_ids": list(correct_to_wrong),
        "concordant_pairs": len(ids) - len(wrong_to_correct) - len(correct_to_wrong),
        "mcnemar": ra.mcnemar(len(wrong_to_correct), len(correct_to_wrong)),
    }
    if with_bootstrap:
        block["bootstrap"] = ra.bootstrap_gain(
            sample_ids=ids,
            m0=baseline,
            blend=treatment,
            n_replicates=BOOTSTRAP_N,
            seed=BOOTSTRAP_SEED,
        )
    return block


# ---------------------------------------------------------------------------
# Descriptive profiles
# ---------------------------------------------------------------------------


def scenario_profile(
    *,
    sample_ids: Sequence[str],
    gold_by_sample: Mapping[str, object],
    arms: Mapping[str, Mapping[str, int]],
) -> dict[str, object]:
    """Per-scenario n and per-arm accuracy over one population."""

    rows: dict[str, dict[str, object]] = {}
    for sid in sample_ids:
        scenario = gold_by_sample[sid].scenario
        row = rows.setdefault(scenario, {"n": 0, **{f"{name}_correct": 0 for name in arms}})
        row["n"] = int(row["n"]) + 1
        for name, correct in arms.items():
            row[f"{name}_correct"] = int(row[f"{name}_correct"]) + correct[sid]
    for row in rows.values():
        for name in arms:
            row[f"{name}_accuracy"] = int(row[f"{name}_correct"]) / int(row["n"])
    return dict(sorted(rows.items()))


def confusion_profile(
    *,
    sample_ids: Sequence[str],
    gold_by_sample: Mapping[str, object],
    scored: Scored,
    top_n: int = 25,
) -> dict[str, object]:
    """Where one arm's errors land: gold intent -> predicted intent."""

    pairs: Counter[tuple[str, str]] = Counter()
    unparsed = 0
    for sid in sample_ids:
        gold = gold_by_sample[sid]
        gold_target = f"{gold.scenario}_{gold.action}"
        if not scored.parsed[sid]:
            unparsed += 1
            predicted_target = "<unparsed>"
        else:
            predicted_target = f"{scored.predicted_scenario[sid]}_{scored.predicted_action[sid]}"
        if predicted_target != gold_target:
            pairs[(gold_target, predicted_target)] += 1
    ordered = pairs.most_common(top_n)
    return {
        "unparsed_responses": unparsed,
        "distinct_error_pairs": len(pairs),
        "total_errors": sum(pairs.values()),
        "top_confusions": [
            {"gold_intent": gold, "predicted_intent": predicted, "count": count}
            for (gold, predicted), count in ordered
        ],
        # scenario_action_exact is a conjunction, so an error is decomposed:
        # the scenario itself is wrong, or the scenario is right and only the
        # action is wrong. The two are disjoint and sum to total_errors.
        "errors_with_wrong_scenario": sum(
            1 for sid in sample_ids if scored.scenario_exact[sid] == 0
        ),
        "errors_with_right_scenario_wrong_action": sum(
            1
            for sid in sample_ids
            if scored.scenario_exact[sid] == 1 and scored.action_exact[sid] == 0
        ),
    }


def subgroup_profile(
    *,
    sample_ids: Sequence[str],
    arm: ArmOutputs,
    scored: Scored,
    reference: Mapping[str, int],
    reference_name: str,
) -> dict[str, object]:
    """Retain-primary vs dispatched, each with its own accuracy and its own
    paired delta against the reference arm -- because a two-contact arm's
    headline is an average over two structurally different trajectories."""

    groups: dict[str, dict[str, object]] = {}
    for sid in sample_ids:
        key = "retain_primary" if arm.contacts[sid] == 1 else "dispatched"
        row = groups.setdefault(
            key,
            {"n": 0, "arm_correct": 0, f"{reference_name}_correct": 0, "w2c": 0, "c2w": 0},
        )
        row["n"] = int(row["n"]) + 1
        row["arm_correct"] = int(row["arm_correct"]) + scored.correct[sid]
        row[f"{reference_name}_correct"] = (
            int(row[f"{reference_name}_correct"]) + reference[sid]
        )
        difference = scored.correct[sid] - reference[sid]
        if difference > 0:
            row["w2c"] = int(row["w2c"]) + 1
        elif difference < 0:
            row["c2w"] = int(row["c2w"]) + 1
    for row in groups.values():
        n = int(row["n"])
        row["arm_accuracy"] = int(row["arm_correct"]) / n
        row[f"{reference_name}_accuracy"] = int(row[f"{reference_name}_correct"]) / n
        row["delta_samples"] = int(row["arm_correct"]) - int(row[f"{reference_name}_correct"])
    return dict(sorted(groups.items()))


# ---------------------------------------------------------------------------
# The retrieval-reachability ceiling (registered oracle substitute)
# ---------------------------------------------------------------------------


def reachability_ceiling(
    *,
    repo_root: Path,
    data_root: Path,
    sample_ids: Sequence[str],
    gold_by_sample: Mapping[str, object],
    blend_run_dir: Path,
) -> dict[str, object]:
    """Gold-facet recall@k over the population, computed scoring-side.

    Where does a gold-bearing content facet sit in the FULL cosine ordering
    of a sample's own flown query vector against every landed content facet?
    That position decides, mechanically, whether ANY re-weighting or wider
    ``top_k`` could ever have put the right fact in front of the core. The
    vectorised cosine is pinned to ``kb_policy._cosine`` on a bounded probe
    set per sample (the same discipline
    :func:`.dev100_damage_channel_analysis._assert_cosine_agreement` applies
    to the recalled facets), so the diagnostic is bound to the registered
    policy, not to numpy.

    CHARTER DISCLOSURE, restated wherever this number is cited: this is the
    substitute for the forbidden gold-conditioned oracle arm. It bounds what
    RETRIEVAL could reach. It is silent on what the frozen core would have
    answered.
    """

    import numpy as np

    from ..rails import kb_policy as kb
    from ..rails.knowledge import KnowledgeSnapshot

    snapshot_path = Path(data_root) / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    snapshot_sha256 = snapshot.content_hash()
    if snapshot_sha256 != SNAPSHOT_SHA256:
        raise ReadError(
            f"knowledge snapshot hashes to {snapshot_sha256}, not the pinned {SNAPSHOT_SHA256}"
        )

    receipt = json.loads(
        (Path(repo_root) / EMBEDDING_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    facet_block = receipt["vectors"]["content_facets"]
    npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = _require_hash(npz_path, facet_block["sha256"], "content-facet vector NPZ")
    # VALUE VECTORS STAY SEALED: receipt["vectors"]["values"] is never opened.
    npz = np.load(npz_path)
    facet_ids = tuple(str(value) for value in npz["ids"])
    matrix = np.asarray(npz["vectors"], dtype=np.float64)
    if matrix.shape[0] != len(facet_ids):
        raise ReadError(f"unexpected facet vector shape {matrix.shape}")

    content_facet_target: dict[str, str] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        for facet_id in value.associated_facet_ids:
            content_facet_target.setdefault(facet_id, value.task_target)

    query_vectors = dc._load_query_vectors(blend_run_dir)
    missing = set(sample_ids) - set(query_vectors)
    if missing:
        raise ReadError(
            f"{len(missing)} population samples have no landed BLEND query vector; the "
            "ceiling cannot be computed over a population it does not cover"
        )

    targets = np.array(
        [content_facet_target.get(facet_id, "") for facet_id in facet_ids], dtype=object
    )
    facet_norms = np.linalg.norm(matrix, axis=1)

    positions: dict[str, int | None] = {}
    best_cosines: dict[str, float | None] = {}
    cosine_probes = 0
    for sample_id in sample_ids:
        query = np.asarray(query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        gold = gold_by_sample[sample_id]
        gold_target = f"{gold.scenario}_{gold.action}"
        order = np.argsort(-cosines, kind="stable")
        position: int | None = None
        for rank_position, index in enumerate(order, start=1):
            if targets[int(index)] == gold_target:
                position = rank_position
                break
        positions[sample_id] = position
        best_cosines[sample_id] = (
            float(cosines[int(order[position - 1])]) if position is not None else None
        )
        # Pin the vectorised cosine to the policy's own scalar implementation
        # on this sample's top-8 facets plus, when present, the gold-bearing one.
        probe_indices = [int(index) for index in order[:8]]
        if position is not None:
            probe_indices.append(int(order[position - 1]))
        for index in probe_indices:
            policy_value = kb._cosine(
                tuple(query.tolist()), tuple(matrix[index].tolist())
            )
            if abs(policy_value - float(cosines[index])) > 1e-9:
                raise ReadError(
                    f"{sample_id}/{facet_ids[index]}: vectorised cosine "
                    f"{float(cosines[index])} disagrees with kb_policy._cosine {policy_value}"
                )
            cosine_probes += 1

    reachable = [value for value in positions.values() if value is not None]
    absent = len(positions) - len(reachable)
    recall_at_k = {
        f"recall_at_{k}": {
            "count": sum(1 for value in reachable if value <= k),
            "rate": sum(1 for value in reachable if value <= k) / len(positions),
        }
        for k in RECALL_AT_K_GRID
    }
    ordered_positions = sorted(reachable)

    def percentile(fraction: float) -> int | None:
        if not ordered_positions:
            return None
        index = min(
            len(ordered_positions) - 1, int(fraction * (len(ordered_positions) - 1))
        )
        return ordered_positions[index]

    return {
        "what_this_is": (
            "the registered CHARTER SUBSTITUTE for the forbidden gold-conditioned oracle arm: "
            "gold-facet recall@k over the population, computed scoring-side from the flown "
            "query vectors and the landed content-facet vectors"
        ),
        "charter_disclosure": (
            "the literature standard (RASU's GT-prompt line) requires gold-conditioned supply at "
            "runtime, which this repository's immutable charter forbids, so the oracle arm was "
            "never flown; this ceiling bounds what RETRIEVAL could have reached and is SILENT on "
            "what the frozen core would have answered given that supply"
        ),
        "population": "DEV-500-NEW400",
        "n": len(positions),
        "frozen_top_k_per_dimension": FROZEN_TOP_K,
        "headline_recall_at_frozen_top_k": recall_at_k[f"recall_at_{FROZEN_TOP_K}"],
        "recall_at_k": recall_at_k,
        "gold_bearing_facet_absent_from_kb": absent,
        "gold_bearing_facet_present": len(reachable),
        "gold_facet_position_median": percentile(0.5),
        "gold_facet_position_p10": percentile(0.10),
        "gold_facet_position_p90": percentile(0.90),
        "gold_facet_position_max": ordered_positions[-1] if ordered_positions else None,
        "snapshot_sha256": snapshot_sha256,
        "content_facet_npz_sha256": measured_npz,
        "content_facet_count": len(facet_ids),
        "value_vectors": "SEALED (never loaded)",
        "cosine_agreement_probes_vs_kb_policy": cosine_probes,
        "query_vector_source": str(blend_run_dir / "query-vectors.jsonl"),
    }


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


def read(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the one registered read. Called exactly once."""

    attempts = ra.arm_offline_guard()

    service_log_before = _service_log_measurement()

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    populations = load_populations(repo_root)
    arms = {pin.arm_id: load_arm(pin=pin, repo_root=repo_root, data_root=data_root) for pin in ARM_PINS}

    # Population coverage: each arm's sealed outputs must cover exactly the
    # population its registration named.
    expected_ids = {
        "DEV-500": set(populations.dev500),
        "DEV-500-NEW400": set(populations.new400),
    }
    for arm in arms.values():
        if set(arm.responses) != expected_ids[arm.pin.population]:
            raise ReadError(
                f"{arm.pin.arm_id}: sealed outputs do not cover exactly {arm.pin.population}"
            )

    # GOLD OPENS HERE, ONCE, SCORING-SIDE, FOR ALL 500.
    gold_by_sample = dc._load_gold(
        data_root=data_root, repo_root=repo_root, sample_ids=set(populations.dev500)
    )
    scored = {arm_id: score_arm(arm=arm, gold_by_sample=gold_by_sample) for arm_id, arm in arms.items()}

    m0 = scored["M0"].correct
    blend = scored["BLEND"].correct
    randret = scored["ABL-RANDRET"].correct
    randicl = scored["ABL-RANDICL"].correct
    new400 = populations.new400
    dev100 = populations.dev100
    dev500 = populations.dev500

    # ---------------- PRIMARY (the frozen statistic) ----------------------
    primary = paired_comparison(
        label="PRIMARY (preregistered): paired per-sample BLEND - M0 over the 400 UNEXPOSED samples",
        population="DEV-500-NEW400 (400 unexposed)",
        sample_ids=new400,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    bootstrap = primary["bootstrap"]
    claim_met = bool(bootstrap["ci90_excludes_zero"])
    primary["claim_condition"] = CLAIM_CONDITION
    primary["claim_condition_met"] = claim_met
    primary["claim_condition_outcome"] = "MET" if claim_met else "NOT MET"
    primary["statistic_citation"] = STATISTIC_CITATION
    primary["variance_prior_carried"] = VARIANCE_PRIOR

    # ---------------- SECONDARIES (reported, no claim) --------------------
    secondaries: dict[str, object] = {}
    secondaries["exposed_100_blend_vs_m0"] = paired_comparison(
        label="SECONDARY: BLEND - M0 on the nested PRIOR-EXPOSED DEV-100 (never pooled into the claim)",
        population="DEV-100 (100 prior-exposed)",
        sample_ids=dev100,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["pooled_500_blend_vs_m0_descriptive"] = paired_comparison(
        label="SECONDARY (DESCRIPTIVE ONLY, explicitly NOT the claim): BLEND - M0 pooled over all 500",
        population="DEV-500 (400 unexposed + 100 prior-exposed, pooled)",
        sample_ids=dev500,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["new400_blend_vs_randret"] = paired_comparison(
        label=(
            "SECONDARY: the RETRIEVAL-SIGNAL effect -- BLEND - ABL-RANDRET on the NEW400 "
            "(same fusion path, same admission, same rendering; only the retrieval signal is randomized)"
        ),
        population="DEV-500-NEW400 (400 unexposed)",
        sample_ids=new400,
        baseline_name="ABL-RANDRET",
        baseline=randret,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["new400_blend_vs_randicl"] = paired_comparison(
        label=(
            "SECONDARY: retrieval vs generic in-context conditioning -- BLEND - ABL-RANDICL on the NEW400"
        ),
        population="DEV-500-NEW400 (400 unexposed)",
        sample_ids=new400,
        baseline_name="ABL-RANDICL",
        baseline=randicl,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["new400_randicl_vs_m0"] = paired_comparison(
        label=(
            "SECONDARY: what generic in-context conditioning alone buys -- ABL-RANDICL - M0 on the NEW400"
        ),
        population="DEV-500-NEW400 (400 unexposed)",
        sample_ids=new400,
        baseline_name="M0",
        baseline=m0,
        treatment_name="ABL-RANDICL",
        treatment=randicl,
    )
    secondaries["new400_randret_vs_m0"] = paired_comparison(
        label=(
            "SECONDARY (context for the two above): ABL-RANDRET - M0 on the NEW400"
        ),
        population="DEV-500-NEW400 (400 unexposed)",
        sample_ids=new400,
        baseline_name="M0",
        baseline=m0,
        treatment_name="ABL-RANDRET",
        treatment=randret,
    )

    # ---------------- Descriptive profiles --------------------------------
    arm_accuracies = {
        "NEW400 (400 unexposed)": {
            name: {
                "correct": sum(table[sid] for sid in new400),
                "accuracy": sum(table[sid] for sid in new400) / len(new400),
            }
            for name, table in (
                ("M0", m0), ("BLEND", blend), ("ABL-RANDRET", randret), ("ABL-RANDICL", randicl)
            )
        },
        "DEV-100 (100 prior-exposed)": {
            name: {
                "correct": sum(table[sid] for sid in dev100),
                "accuracy": sum(table[sid] for sid in dev100) / len(dev100),
            }
            for name, table in (("M0", m0), ("BLEND", blend))
        },
        "DEV-500 (pooled, descriptive)": {
            name: {
                "correct": sum(table[sid] for sid in dev500),
                "accuracy": sum(table[sid] for sid in dev500) / len(dev500),
            }
            for name, table in (("M0", m0), ("BLEND", blend))
        },
    }

    profiles = {
        "per_scenario_new400": scenario_profile(
            sample_ids=new400,
            gold_by_sample=gold_by_sample,
            arms={"M0": m0, "BLEND": blend, "ABL-RANDRET": randret, "ABL-RANDICL": randicl},
        ),
        "per_scenario_exposed100": scenario_profile(
            sample_ids=dev100,
            gold_by_sample=gold_by_sample,
            arms={"M0": m0, "BLEND": blend},
        ),
        "confusion_new400": {
            name: confusion_profile(
                sample_ids=new400, gold_by_sample=gold_by_sample, scored=scored[name]
            )
            for name in ("M0", "BLEND", "ABL-RANDRET", "ABL-RANDICL")
        },
        "subgroups_new400": {
            "BLEND_vs_M0": subgroup_profile(
                sample_ids=new400,
                arm=arms["BLEND"],
                scored=scored["BLEND"],
                reference=m0,
                reference_name="M0",
            ),
            "ABL-RANDRET_vs_M0": subgroup_profile(
                sample_ids=new400,
                arm=arms["ABL-RANDRET"],
                scored=scored["ABL-RANDRET"],
                reference=m0,
                reference_name="M0",
            ),
        },
        "subgroups_exposed100": {
            "BLEND_vs_M0": subgroup_profile(
                sample_ids=dev100,
                arm=arms["BLEND"],
                scored=scored["BLEND"],
                reference=m0,
                reference_name="M0",
            ),
        },
        "field_decomposition_new400": {
            name: {
                "scenario_exact": sum(scored[name].scenario_exact[sid] for sid in new400),
                "action_exact": sum(scored[name].action_exact[sid] for sid in new400),
                "scenario_action_exact": sum(scored[name].correct[sid] for sid in new400),
                "unparsed": sum(1 for sid in new400 if not scored[name].parsed[sid]),
                "slot_f1_exact_mean": sum(scored[name].slot_f1[sid] for sid in new400) / len(new400),
            }
            for name in ("M0", "BLEND", "ABL-RANDRET", "ABL-RANDICL")
        },
    }

    ceiling = reachability_ceiling(
        repo_root=repo_root,
        data_root=data_root,
        sample_ids=new400,
        gold_by_sample=gold_by_sample,
        blend_run_dir=arms["BLEND"].run_dir,
    )

    service_log_after = _service_log_measurement()
    zero_contact = {
        "registered_contacts": {"frozen_core": 0, "pinned_tool_embedding": 0, "tokenizer": 0},
        "offline_guard": {
            "armed_before_any_input_was_opened": True,
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
        },
        "resident_service_log": {
            "path": str(SERVICE_LOG_PATH),
            "before": service_log_before,
            "after": service_log_after,
            "byte_length_identical": service_log_before.get("bytes")
            == service_log_after.get("bytes"),
            "sha256_identical": service_log_before.get("sha256")
            == service_log_after.get("sha256"),
        },
    }

    campaign_spend = _campaign_spend(arms)

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "exposure_row_id": EXPOSURE_ROW_ID,
        "authority": {
            "preregistration": PREREGISTRATION_RELPATH,
            "campaign_fragment": CAMPAIGN_FRAGMENT_RELPATH,
            "statistic_citation": STATISTIC_CITATION,
        },
        "one_shot": {
            "rule": (
                "computed exactly once as preregistered; no threshold change, no re-computation "
                "with different parameters, no partial re-read, no re-fly, whatever the outcome"
            ),
            "gold_opened": "ONCE, here, scoring-side, for all 500 DEV-500 samples",
            "variance_prior_carried": VARIANCE_PRIOR,
        },
        "populations": {
            "dev500_n": len(dev500),
            "new400_n": len(new400),
            "exposed100_n": len(dev100),
            "new400_derivation": "deterministic set difference DEV-500 minus DEV-100, re-derived and matched to its own committed receipt",
            "receipt_file_sha256": dict(populations.receipt_hashes),
        },
        "sources": [
            {
                "arm": pin.arm_id,
                "attempt_id": pin.attempt_id,
                "committed_report": f"{CHECK_DIR_RELPATH}/{pin.report_basename}",
                "committed_report_sha256": pin.report_sha256,
                "sealed_outputs": pin.outputs_basename,
                "sealed_outputs_sha256": pin.outputs_sha256,
                "sealed_mechanical": pin.mechanical_basename,
                "sealed_mechanical_sha256": pin.mechanical_sha256,
                "population": pin.population,
                "n": pin.expected_samples,
            }
            for pin in ARM_PINS
        ],
        "scoring_path": (
            "reproduction.slurp_scoring.parse_slu_response + score_slu, correctness = "
            "scenario_action_exact -- identical to rails.adapters.slurp.SlurpAdapter.score, the "
            "call the sealed DEV-100 round launchers made post-seal"
        ),
        "arm_accuracies": arm_accuracies,
        "primary": primary,
        "secondaries": secondaries,
        "reachability_ceiling": ceiling,
        "profiles": profiles,
        "campaign_spend": campaign_spend,
        "zero_contact_proof": zero_contact,
        "scope": {
            "binding": (
                "dev-tier confirmatory: NO test claim, NO generalization claim, NO controller/RL "
                "claim; FINAL60 and test remain untouched"
            ),
            "interpretation": (
                "this artifact reports the registered outputs only; the coordinator interprets"
            ),
        },
    }


def _service_log_measurement() -> dict[str, object]:
    if not SERVICE_LOG_PATH.exists():
        return {"present": False}
    return {
        "present": True,
        "bytes": SERVICE_LOG_PATH.stat().st_size,
        "sha256": _sha256_file(SERVICE_LOG_PATH),
    }


def _campaign_spend(arms: Mapping[str, ArmOutputs]) -> dict[str, object]:
    """Campaign totals, re-summed from the four committed reports."""

    calls = 0
    audio = 0.0
    tool = 0
    gpu = 0.0
    per_arm: dict[str, object] = {}
    for arm_id, arm in arms.items():
        cost = arm.report["core_client"]["cost"]
        this = arm.report["spend_vs_ceilings"]["this_attempt"]
        embedding = arm.report.get("embedding_accounting", {}) or {}
        arm_calls = int(cost["calls_used"])
        arm_audio = float(cost["audio_seconds_used"])
        arm_tool = int(embedding.get("tool_contacts", 0) or 0)
        arm_gpu = float(this.get("gpu_active_hours_contact_basis", 0.0) or 0.0)
        calls += arm_calls
        audio += arm_audio
        tool += arm_tool
        gpu += arm_gpu
        per_arm[arm_id] = {
            "frozen_core_contacts": arm_calls,
            "tool_contacts": arm_tool,
            "metered_audio_seconds": arm_audio,
            "gpu_active_hours": arm_gpu,
        }
    ceilings = {
        "frozen_core_contacts": 3200,
        "pinned_tool_embedding_contacts": 1000,
        "metered_audio_seconds": 8000,
        "gpu_hours": 3.0,
    }
    totals = {
        "frozen_core_contacts": calls,
        "pinned_tool_embedding_contacts": tool,
        "metered_audio_seconds": audio,
        "gpu_active_hours": gpu,
    }
    return {
        "per_arm": per_arm,
        "campaign_totals": totals,
        "campaign_ceilings": ceilings,
        "inside_every_ceiling": (
            calls <= ceilings["frozen_core_contacts"]
            and tool <= ceilings["pinned_tool_embedding_contacts"]
            and audio <= ceilings["metered_audio_seconds"]
            and gpu <= ceilings["gpu_hours"]
        ),
        "this_read": {"calls": 0, "tool_contacts": 0, "audio_seconds": 0, "gpu_hours": 0.0},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    verdict = read(repo_root=args.repo_root, data_root=args.data_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(verdict, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    primary = verdict["primary"]
    bootstrap = primary["bootstrap"]
    print(f"wrote {args.out}")
    print(
        f"PRIMARY  M0 {primary['M0_correct']}/400  BLEND {primary['BLEND_correct']}/400  "
        f"delta {primary['delta_samples']:+d} ({primary['delta_pp']:+.2f} pp)"
    )
    print(
        f"  90% CI [{bootstrap['ci90_low_pp']:.4f}, {bootstrap['ci90_high_pp']:.4f}] pp   "
        f"95% CI [{bootstrap['ci95_low_pp']:.4f}, {bootstrap['ci95_high_pp']:.4f}] pp"
    )
    print(
        f"  McNemar exact p = {primary['mcnemar'].get('exact_binomial_two_sided_p')}   "
        f"W->C {primary['wrong_to_correct_count']}  C->W {primary['correct_to_wrong_count']}"
    )
    print(f"  CLAIM CONDITION: {primary['claim_condition_outcome']}")
    return 0


__all__ = [
    "ARM_PINS",
    "CLAIM_CONDITION",
    "EXPOSURE_ROW_ID",
    "SCHEMA",
    "STATISTIC_CITATION",
    "ArmOutputs",
    "ArmPin",
    "Populations",
    "ReadError",
    "Scored",
    "load_arm",
    "load_populations",
    "main",
    "paired_comparison",
    "read",
    "reachability_ceiling",
    "score_arm",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
