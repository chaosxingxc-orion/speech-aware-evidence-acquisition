"""The ONE registered one-shot LOCK READ of the SEALED DEV-1000 BASELINE-LOCK campaign.

Exposure row ``SAEA-SN-MF-DEV1000-LOCK-READ`` (registered before any
computation, ledger commit ``11ce2cef``): zero frozen-core contacts, zero
embedding-tool contacts, zero tokenizer contacts, zero HTTP or socket
requests. Everything this module reads is already landed and sealed -- the
two committed per-arm mechanical reports, the two sealed attempt stores
(per-sample outputs, per-sample mechanical records, the BLEND arm's own
landed query vectors, and -- for the 14 override trajectories only -- the
BLEND attempt's own durable trace, consulted purely to recover the direct
decode's TEXT for a hash the per-sample record already carries), the pinned
TRAIN knowledge snapshot with its content-facet vector NPZ (value vectors
stay SEALED), the committed split receipts, and SLURP devel gold read
strictly scoring-side.

One-shot semantics
------------------
The preregistration
(``docs/readiness/2026-08-24-dev1000-baseline-lock-preregistration.md``
section 2) and the candidate selection
(``docs/readiness/2026-08-25-lock-candidate-selection.md`` sections 3 and 4)
froze the statistic, the population, and the lock condition BEFORE the arms
flew. This module computes them EXACTLY as frozen, exactly once. No
threshold may be changed, no parameter re-tried, no partial re-read
performed, no arm re-flown, whatever the outcome. A second execution against
these same pinned bytes is a reproducibility check and can never become a
second read -- which is precisely why every input is pinned by sha256 and a
mismatch is a fail-closed :class:`ReadError`, never a warning.

The primary statistic and the LOCK CONDITION
--------------------------------------------
Paired per-sample ``BLEND(v2) - M0`` over the **500 UNEXPOSED samples only**
(DEV-1000 minus the nested, prior-exposed DEV-500 -- the ``DEV-1000-NEW500``
receipt, partitioned on the receipt's ``id`` field, never its carrier-prefixed
``key`` field, which is the A4 lesson), a paired cluster bootstrap at
N=10,000 / seed 20260807 with 90% and 95% percentile CIs, and McNemar exact
on the discordant pairs. **Lock condition (preregistered): the 90% CI LOWER
BOUND is at least +10 pp** -- not merely "excludes zero". The outcome is
recorded as exactly one of:

``LOCKED``
    the 90% CI lower bound is at least +10 pp;
``CONFIRMED-BUT-SHRUNKEN``
    the 90% CI excludes zero but its lower bound falls below +10 pp -- this
    does NOT lock and returns the program to iteration;
``NOT-CONFIRMED``
    the 90% CI includes zero.

The 500 previously-exposed samples are scored and reported separately and
are NEVER pooled into the lock claim (the DEV-500 nesting precedent).

Registered secondaries (reported, no claim attaches)
----------------------------------------------------
The exposed-500 pair on its own and the pooled 1,000 descriptively; the
delta-override subgroup (the 14 fires, 3 of them inside the unexposed half)
with their individual outcomes and the mechanism's realized contribution to
the lock statistic, bounded at plus-or-minus 3 samples; the dead-direct
dispatch subgroup against the retain-primary subgroup; wrong-to-correct and
correct-to-wrong tables per population; per-scenario accuracy and the top
confusions; the retrieval-reachability ceiling recomputed scoring-side over
the unexposed 500 (preregistration section 3); and the SCALE-STABILITY
comparison of this tier's unexposed-500 margin against the sealed DEV-500
unexposed-400 margin.

The fit-not-validated disclosure, carried at every citation
-----------------------------------------------------------
The v2 candidate is the v1 frozen cell PLUS the ``delta >= 0.14``
retain-override. The candidate-selection note section 3 records, and this
read repeats, that the bar was FIT on exposed data (DEV-100 r4/r5 and DEV-500
NEW400) and frozen on 2026-08-25 before this read. The unexposed-500 read
therefore validates the bar AND confirms the cell in a single touch --
legitimate only because the bar was frozen before the read and the fit is
declared.

The oracle substitution, disclosed wherever the ceiling is cited
----------------------------------------------------------------
Unchanged from the DEV-500 read and inherited verbatim through the imported
:func:`.dev500_confirmatory_read.reachability_ceiling`: the literature-standard
oracle/GT-prompt retrieval ceiling requires gold-conditioned supply at RUNTIME,
which this repository's immutable charter forbids, so that arm was never flown.
The registered substitute bounds what RETRIEVAL could have reached and is
silent on what the frozen core would have answered.

Deliberate reuse
----------------
:mod:`.dev500_confirmatory_read` owns the paired-comparison shape, the arm
scorer, the descriptive profiles, the subgroup profile and the reachability
ceiling; through it, :mod:`.dev100_reviewer_audit` owns the bootstrap wrapper,
the McNemar accounting and the offline guard, and :mod:`.bootstrap` owns the
resampling primitive with the mandated seed. All are IMPORTED, never
re-implemented, so this read and the sealed DEV-500 read read identical bytes
through identical code and cannot drift apart. What is new here and only here
is the DEV-1000 population/pin table, the LOCK CONDITION evaluation, the
three-way dispatch decomposition the v2 override introduces, and the
scale-stability comparison.

Scope (preregistration section 5, binding)
------------------------------------------
Dev-tier. A LOCK records the cell as the baseline version for large-scale
experiments; it does NOT authorize test contact, a superiority claim, a
generalization claim, or any Stage-3 activity. FINAL60 and test remain
untouched. This artifact reports the registered outputs only -- the
coordinator interprets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev500_confirmatory_read as d5

ReadError = d5.ReadError

SCHEMA = "saea-dev1000-lock-read-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-DEV1000-LOCK-READ"
RUN_ID = "SAEA-DEV1000-BASELINE-LOCK"

PREREGISTRATION_RELPATH = "docs/readiness/2026-08-24-dev1000-baseline-lock-preregistration.md"
CANDIDATE_SELECTION_RELPATH = "docs/readiness/2026-08-25-lock-candidate-selection.md"
CAMPAIGN_FRAGMENT_RELPATH = "configs/experiment/slurp-dev1000-baseline-lock-v1.json"
CHECK_DIR_RELPATH = "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-baseline-lock"

# Verbatim from preregistration section 2 -- quoted, never paraphrased.
STATISTIC_CITATION = (
    "Statistic: paired per-sample BLEND - M0 over the unexposed 500; paired cluster bootstrap "
    "(N=10,000, seed 20260807) 90% and 95% CIs; McNemar exact. Lock condition (preregistered): "
    "the 90% CI lower bound >= +10 pp -- i.e. not merely \"excludes zero\" but retains the bulk "
    "of the DEV-500 margin (+19.75 pp, CI [+16.5, +23.0]) at double scale. A CI that excludes "
    "zero but falls below +10 is recorded as CONFIRMED-BUT-SHRUNKEN and does NOT lock; it returns "
    "to iteration."
)
LOCK_CONDITION = (
    "the 90% CI lower bound on the paired per-sample BLEND(v2) - M0 gain over the 500 unexposed "
    "samples is at least +10 pp"
)
LOCK_THRESHOLD_PP = 10.0

BOOTSTRAP_N = d5.BOOTSTRAP_N
BOOTSTRAP_SEED = d5.BOOTSTRAP_SEED

# The registered variance prior, carried as registered.
VARIANCE_PRIOR = "DEV-100 round-5 replication: plus-minus 2 per 100 at 8-slot decode"

# The prior tier this one exists to test for scale stability. Values are the
# sealed DEV-500 confirmatory read's own committed primary block.
DEV500_REFERENCE = {
    "source": "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory-read/read-verdict.json",
    "population": "DEV-500-NEW400 (400 unexposed)",
    "n": 400,
    "M0_correct": 210,
    "M0_accuracy": 0.525,
    "BLEND_correct": 289,
    "BLEND_accuracy": 0.7225,
    "delta_samples": 79,
    "delta_pp": 19.75,
    "ci90_low_pp": 16.5,
    "ci90_high_pp": 23.0,
    "ci95_low_pp": 15.75,
    "ci95_high_pp": 23.75,
    "sigma_hat_pp": 2.0562578496810655,
    "wrong_to_correct_count": 81,
    "correct_to_wrong_count": 2,
    "cell": "v1 frozen cell (configs/policy/kb-policy-v1-dev100.json)",
}

# The v2 lock candidate, hash-pinned at the flight row.
LOCK_CANDIDATE = {
    "relpath": "configs/policy/kb-policy-v2-lock-candidate.json",
    "sha256": "0c34ebe7be636b8e432bffe504b0175d1a122000a74051b183e09615de69033e",
    "supersedes_relpath": "configs/policy/kb-policy-v1-dev100.json",
    "supersedes_sha256": "0d36273eb2a5f4411ba9ca378ad820392e97c8759222087cf562e7f19442e2b0",
    "delta_bar": 0.14,
    "fit_not_validated_disclosure": (
        "the delta >= 0.14 retain-override bar was FIT on exposed data (DEV-100 r4/r5 and DEV-500 "
        "NEW400) and frozen 2026-08-25 BEFORE this read; the unexposed-500 read therefore validates "
        "the bar AND confirms the cell in a single touch, which is legitimate only because the bar "
        "was frozen before the read and the fit is declared -- candidate selection note section 3"
    ),
}

ARM_PINS = (
    d5.ArmPin(
        arm_id="M0",
        arm_index=1,
        attempt_id="attempt-20260825T053342Z-dev1000m0",
        report_basename="arm1-m0-mechanical-report.json",
        report_sha256="c751ca585bfacd71b2a62093afaf744ceee5cf7ad63980b5145ae43a825f24f1",
        outputs_basename="arm1-m0-outputs.jsonl",
        outputs_sha256="ea7045d3cfd3d1652f568911a0c47c16d66b879e824d314a6cb5061d7f07decc",
        mechanical_basename="arm1-m0-mechanical.json",
        mechanical_sha256="814532760a712888d943c4a781f358cff426001ac0394ee29814cf4ee0335d16",
        expected_samples=1000,
        population="DEV-1000",
    ),
    d5.ArmPin(
        arm_id="BLEND",
        arm_index=2,
        attempt_id="attempt-20260825T054707Z-dev1000blend",
        report_basename="arm2-blend-mechanical-report.json",
        report_sha256="c3ed01699a43087e719b917c751d1ce96d6b0992107d58437fc048fd12ba5930",
        outputs_basename="arm2-blend-outputs.jsonl",
        outputs_sha256="542a029adca8fb8daf3618e8a049aecdba1b04aba30eafedb67099fb6e08cf14",
        mechanical_basename="arm2-blend-mechanical.json",
        mechanical_sha256="e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e",
        expected_samples=1000,
        population="DEV-1000",
    ),
)

# Split receipts: (relpath, run_identity_hash, receipt_integrity_hash, n_items,
# receipt_file_sha256). The DEV-1000 run identity is the CORRECTED value
# 8580d199...3c84; preregistration section 2 quotes DEV-100's e9a7b7fe...d853
# by copy error, an erratum recorded in the campaign landing and restated here.
RECEIPT_PINS = {
    "DEV-1000": (
        "docs/receipts/probe-samples/DEV-1000.json",
        "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84",
        "9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b",
        1000,
        "653c7556edf88e56af2e18a25239426b2efc3b080af0173fd65c87fe8e4f528b",
    ),
    "DEV-500": (
        "docs/receipts/probe-samples/DEV-500.json",
        "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4",
        "c0f1c7531fb8972885abf1d840cc101bbfa38ae04e3929cc46e0f5b9ef35452b",
        500,
        "adc3e4ddd20518d279dc6c3aa42821629ca67b05eaba7802e1918f0349c2f315",
    ),
    "DEV-1000-NEW500": (
        "docs/receipts/probe-samples/DEV-1000-NEW500.json",
        "48a96f6fcb9cc391dd776aededa9c27ec4e89195b06a656ae68e814948416ecd",
        "1d6d4ba61028c36f22f03de87d48afebeda1b53bd3b32b1a001e117068ddc66d",
        500,
        "1feefb8c327c0234160e96906bd5344cfef25ac665ddbb4db957fab067a234a3",
    ),
}

PREREGISTRATION_ERRATUM = (
    "preregistration section 2 quotes `e9a7b7fe...d853` as the DEV-1000 load-split identity; that "
    "value is DEV-100's run identity, carried over by a copy error when the preregistration was "
    "drafted. The correct DEV-1000 load-split identity is `8580d199...3c84`, which is what this "
    "read pins and asserts, and what the campaign row's split-identity cell carries. The "
    "receipt-integrity value the preregistration quotes, `9fb44e33...243b`, is correct. The erratum "
    "moves NO sample: the population is the same 1,000 ids under either reading."
)


# ---------------------------------------------------------------------------
# Populations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Populations:
    """The three id sets, each verified against its committed receipt."""

    dev1000: tuple[str, ...]
    dev500: tuple[str, ...]
    new500: tuple[str, ...]
    receipt_hashes: Mapping[str, str]


def load_populations(repo_root: Path) -> Populations:
    """DEV-1000, the nested prior-exposed DEV-500, and the unexposed NEW500.

    NEW500 is re-derived here as the deterministic set difference and then
    compared to its own committed receipt, so the lock population is PROVED
    to be exactly what the campaign registered rather than trusted to be.

    The partition is taken on the receipt's ``id`` field. Comparing on the
    carrier-prefixed ``key`` field yields a SILENTLY EMPTY intersection -- the
    A4 lesson, applied here as an explicit non-empty assertion."""

    from ..data.splits import split_identity_hash

    ids: dict[str, tuple[str, ...]] = {}
    receipt_hashes: dict[str, str] = {}
    for name, (relpath, run_identity, integrity, n_items, file_sha) in RECEIPT_PINS.items():
        path = Path(repo_root) / relpath
        measured = d5._require_hash(path, file_sha, f"{name} committed receipt")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(str(item["id"]) for item in receipt["items"])
        if len(items) != n_items or len(set(items)) != n_items:
            raise ReadError(f"{name} receipt is not {n_items} distinct ids")
        if int(receipt["n_items"]) != n_items:
            raise ReadError(f"{name} receipt declares n_items {receipt['n_items']}, not {n_items}")
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
        receipt_hashes[name] = measured

    dev1000, dev500, new500 = ids["DEV-1000"], ids["DEV-500"], ids["DEV-1000-NEW500"]
    if not set(dev500) <= set(dev1000):
        raise ReadError("DEV-500 is not nested inside DEV-1000")
    if not set(dev500) & set(dev1000):
        raise ReadError(
            "the DEV-500 / DEV-1000 intersection is EMPTY -- the A4 failure mode (partitioning on "
            "the carrier-prefixed key rather than the id) has recurred and the read STOPS"
        )
    derived = tuple(sorted(set(dev1000) - set(dev500)))
    if derived != new500:
        raise ReadError(
            "the deterministic set difference DEV-1000 minus DEV-500 does not equal the committed "
            "NEW500 receipt -- the lock population is not what was registered"
        )
    if set(new500) & set(dev500):
        raise ReadError("NEW500 and DEV-500 are not disjoint")
    if set(new500) | set(dev500) != set(dev1000):
        raise ReadError("NEW500 and DEV-500 do not union to DEV-1000")
    return Populations(
        dev1000=dev1000, dev500=dev500, new500=new500, receipt_hashes=receipt_hashes
    )


# ---------------------------------------------------------------------------
# Sealed arm outputs
# ---------------------------------------------------------------------------


def load_arm(*, pin: d5.ArmPin, repo_root: Path, data_root: Path) -> d5.ArmOutputs:
    """Load one sealed arm, hash-verifying its committed report AND its
    attempt-store bytes before a single response text is parsed.

    Same discipline as :func:`.dev500_confirmatory_read.load_arm`, re-stated
    for this campaign's own run id and check directory, and extended with the
    v2 retain-override cross-checks the DEV-500 tier had no arm for."""

    report_path = Path(repo_root) / CHECK_DIR_RELPATH / pin.report_basename
    d5._require_hash(report_path, pin.report_sha256, f"{pin.arm_id} committed mechanical report")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if str(report["arm_id"]) != pin.arm_id or str(report["attempt_id"]) != pin.attempt_id:
        raise ReadError(f"{pin.arm_id}: committed report names a different arm/attempt")
    if str(report["run_id"]) != RUN_ID:
        raise ReadError(f"{pin.arm_id}: committed report names run id {report['run_id']!r}")
    if not bool(report.get("mechanical_only")):
        raise ReadError(f"{pin.arm_id}: committed report is not a mechanical-only landing")

    run_dir = Path(data_root) / "runs" / RUN_ID / pin.attempt_id
    if Path(str(report["run_dir"])) != run_dir:
        raise ReadError(f"{pin.arm_id}: committed report's run_dir is not the pinned attempt dir")
    outputs_path = run_dir / pin.outputs_basename
    d5._require_hash(outputs_path, pin.outputs_sha256, f"{pin.arm_id} sealed outputs")
    d5._require_hash(
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

    mechanical = report["mechanical"]
    retained = sum(1 for value in contacts.values() if value == 1)
    dispatched = sum(1 for value in contacts.values() if value == 2)
    if retained != int(mechanical["one_contact_trajectories_retained_primary"]):
        raise ReadError(f"{pin.arm_id}: retain-primary count disagrees with the committed report")
    if dispatched != int(mechanical["two_contact_trajectories_dispatched"]):
        raise ReadError(f"{pin.arm_id}: dispatched count disagrees with the committed report")
    if retained + dispatched != pin.expected_samples:
        raise ReadError(f"{pin.arm_id}: contact counts are not all 1 or 2")

    return d5.ArmOutputs(
        pin=pin,
        responses=responses,
        contacts=contacts,
        winner_labels=winners,
        report=report,
        run_dir=run_dir,
    )


def load_per_sample_mechanical(*, arm: d5.ArmOutputs) -> Mapping[str, Mapping[str, object]]:
    """The sealed per-sample mechanical record, already hash-verified at load.

    Cross-checked against the committed report's own ``retain_override``
    block AND against the per-sample contact counts, so the three-way
    dispatch decomposition this read publishes is proved twice."""

    path = arm.run_dir / arm.pin.mechanical_basename
    records = json.loads(path.read_text(encoding="utf-8"))
    if set(records) != set(arm.responses):
        raise ReadError(f"{arm.pin.arm_id}: per-sample mechanical records do not cover the outputs")

    block = arm.report["mechanical"]["retain_override"]
    fires = sorted(sid for sid, rec in records.items() if bool(rec["override_fires"]))
    override_dispatched = sum(
        1 for sid in fires if int(records[sid]["contacts"]) == 2
    )
    recovered = sum(1 for rec in records.values() if bool(rec["direct_label_recovered"]))
    dead_direct_dispatched = sum(
        1
        for sid, rec in records.items()
        if int(rec["contacts"]) == 2 and not bool(rec["override_fires"])
    )
    if len(fires) != int(block["fired"]):
        raise ReadError(f"{arm.pin.arm_id}: override fire count disagrees with the committed report")
    if override_dispatched != int(block["override_dispatched"]):
        raise ReadError(f"{arm.pin.arm_id}: override-dispatch count disagrees with the report")
    if dead_direct_dispatched != int(block["dead_direct_dispatched"]):
        raise ReadError(f"{arm.pin.arm_id}: dead-direct dispatch count disagrees with the report")
    if recovered != int(arm.report["mechanical"]["direct_label_recovered_samples"]):
        raise ReadError(f"{arm.pin.arm_id}: recovered-label count disagrees with the report")
    for sid, rec in records.items():
        if int(rec["contacts"]) != arm.contacts[sid]:
            raise ReadError(f"{arm.pin.arm_id}/{sid}: mechanical contacts disagree with the outputs")
        digest = hashlib.sha256(arm.responses[sid].encode("utf-8")).hexdigest()
        if digest != str(rec["response_sha256"]):
            raise ReadError(
                f"{arm.pin.arm_id}/{sid}: the sealed response text does not hash to the sealed "
                f"response_sha256 -- the two attempt-store artifacts contradict each other"
            )
    return records


def _direct_texts(*, run_dir: Path, wanted: Mapping[str, str]) -> dict[str, str]:
    """Recover the direct decode's TEXT for a bounded set of samples.

    ``wanted`` maps sample id -> the ``direct_response_sha256`` the sealed
    per-sample record already carries. The BLEND attempt's own durable trace
    is streamed once and every recovered text is re-hashed and matched to the
    hash that asked for it, so this lookup cannot substitute one response for
    another. Nothing else is taken from the trace."""

    trace_path = run_dir / f"{RUN_ID}.trace.jsonl"
    by_sha: dict[str, str] = {}
    targets = set(wanted.values())
    with trace_path.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record["channel"] != "MODEL_RESPONSE":
                continue
            payload = record["payload"]
            digest = str(payload["response_text_sha256"])
            if digest in targets and digest not in by_sha:
                by_sha[digest] = str(payload["text"])
    texts: dict[str, str] = {}
    for sample_id, digest in wanted.items():
        text = by_sha.get(digest)
        if text is None:
            raise ReadError(f"{sample_id}: no logged direct-decode text for {digest}")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != digest:
            raise ReadError(f"{sample_id}: recovered direct-decode text does not re-hash to {digest}")
        texts[sample_id] = text
    return texts


# ---------------------------------------------------------------------------
# The v2 override subgroup (new at this tier)
# ---------------------------------------------------------------------------


def override_analysis(
    *,
    blend: d5.ArmOutputs,
    m0_arm: d5.ArmOutputs,
    records: Mapping[str, Mapping[str, object]],
    gold_by_sample: Mapping[str, object],
    m0_correct: Mapping[str, int],
    blend_correct: Mapping[str, int],
    new500: Sequence[str],
    dev500: Sequence[str],
) -> dict[str, object]:
    """Every override fire, individually, plus the mechanism's REALIZED
    contribution to the lock statistic.

    The counterfactual is exact rather than estimated: the override is
    BRANCH-ONLY, so had it not fired the trajectory would have RETAINED and
    the final answer would have been that trajectory's own direct decode --
    whose text the sealed record pins by hash. Scoring that text with the
    repository's own scorer gives the v1 outcome for the same sample, and the
    difference is what the mechanism actually bought on this population.

    The contribution is bounded at plus-or-minus 3 samples on the lock
    statistic BY CONSTRUCTION: only 3 of the 14 fires fall inside the
    unexposed 500."""

    from ..reproduction.slurp_scoring import parse_slu_response, score_slu

    fires = sorted(sid for sid, rec in records.items() if bool(rec["override_fires"]))
    wanted = {sid: str(records[sid]["direct_response_sha256"]) for sid in fires}
    direct_texts = _direct_texts(run_dir=blend.run_dir, wanted=wanted)

    new500_set = set(new500)
    rows: list[dict[str, object]] = []
    for sid in fires:
        record = records[sid]
        gold = gold_by_sample[sid]
        scenario, action, entities, parsed = parse_slu_response(direct_texts[sid])
        result = score_slu(
            gold_scenario=gold.scenario,
            gold_action=gold.action,
            gold_entities=gold.entities,
            predicted_scenario=scenario,
            predicted_action=action,
            predicted_entities=tuple(entities),
        )
        retain_correct = 1 if result.scenario_action_exact == 1.0 else 0
        m0_digest = hashlib.sha256(m0_arm.responses[sid].encode("utf-8")).hexdigest()
        rows.append(
            {
                "sample_id": sid,
                "population": "UNEXPOSED (lock statistic)" if sid in new500_set else "prior-exposed",
                "delta": float(record["delta"]),
                "cos_direct": float(record["cos_direct"]),
                "cos_top1": float(record["cos_top1"]),
                "direct_target": record["direct_target"],
                "fused_top1_target": record["fused_top1_target"],
                "winner_label": blend.winner_labels[sid],
                "gold_intent": f"{gold.scenario}_{gold.action}",
                "M0_correct": m0_correct[sid],
                "BLEND_v2_correct": blend_correct[sid],
                "v1_counterfactual_retain_correct": retain_correct,
                "override_attributable_delta": blend_correct[sid] - retain_correct,
                "outcome": (
                    "RECOVERED"
                    if blend_correct[sid] - retain_correct > 0
                    else ("DAMAGED" if blend_correct[sid] - retain_correct < 0 else "NO CHANGE")
                ),
                "direct_decode_byte_identical_to_M0_response": m0_digest == wanted[sid],
                "counterfactual_direct_text_parsed": bool(parsed),
            }
        )

    def _tally(subset: Sequence[Mapping[str, object]]) -> dict[str, object]:
        gained = sum(1 for row in subset if int(row["override_attributable_delta"]) > 0)
        lost = sum(1 for row in subset if int(row["override_attributable_delta"]) < 0)
        return {
            "fires": len(subset),
            "recovered": gained,
            "damaged": lost,
            "no_change": len(subset) - gained - lost,
            "net_override_attributable_samples": gained - lost,
        }

    unexposed_rows = [row for row in rows if row["population"].startswith("UNEXPOSED")]
    exposed_rows = [row for row in rows if not row["population"].startswith("UNEXPOSED")]

    return {
        "what_this_is": (
            "the v2 variable's own subgroup: the delta >= 0.14 retain-override fires, individually, "
            "with an EXACT counterfactual (had the override not fired the trajectory would have "
            "retained and answered with its own direct decode, whose text the sealed record pins by "
            "hash)"
        ),
        "fit_not_validated_disclosure": LOCK_CANDIDATE["fit_not_validated_disclosure"],
        "bar": LOCK_CANDIDATE["delta_bar"],
        "fires_total": len(rows),
        "fires_in_unexposed_500": len(unexposed_rows),
        "fires_in_exposed_500": len(exposed_rows),
        "per_fire": rows,
        "realized_contribution_to_the_lock_statistic": {
            **_tally(unexposed_rows),
            "population": "DEV-1000-NEW500 (500 unexposed)",
            "bound": (
                "bounded at plus-or-minus 3 samples BY CONSTRUCTION -- only 3 of the 14 fires fall "
                "inside the unexposed 500, so the mechanism can move the lock statistic by at most "
                "3 of 500 = 0.60 pp in either direction"
            ),
            "max_possible_pp_either_direction": 100.0 * len(unexposed_rows) / len(new500),
            "realized_pp": 100.0
            * sum(int(row["override_attributable_delta"]) for row in unexposed_rows)
            / len(new500),
        },
        "on_the_prior_exposed_500_no_claim": {
            **_tally(exposed_rows),
            "population": "DEV-500 nested prior-exposed (500)",
        },
        "over_all_1000_descriptive": _tally(rows),
        "loss_side": {
            "zero_loss_property_held": all(
                int(row["override_attributable_delta"]) >= 0 for row in rows
            ),
            "note": (
                "the candidate-selection note records the override's loss side as zero BY "
                "CONSTRUCTION and held so in flight on both sealed DEV-100 bases; this field reports "
                "whether it held here, whatever it shows"
            ),
        },
    }


def dispatch_decomposition(
    *,
    sample_ids: Sequence[str],
    records: Mapping[str, Mapping[str, object]],
    blend_correct: Mapping[str, int],
    m0_correct: Mapping[str, int],
) -> dict[str, object]:
    """Three-way, because v2 has three structurally different trajectories.

    ``retain_primary`` (one contact, the blend kept the direct label),
    ``dead_direct_dispatch`` (the v1 predicate: the direct answer named no
    TRAIN intent), and ``override_dispatch`` (the v2 variable). A two-contact
    arm's headline is an average over these; publishing the average alone
    hides which trajectory class carries the effect."""

    groups: dict[str, dict[str, object]] = {}
    for sid in sample_ids:
        record = records[sid]
        if int(record["contacts"]) == 1:
            key = "retain_primary"
        elif bool(record["override_fires"]):
            key = "override_dispatch"
        else:
            key = "dead_direct_dispatch"
        row = groups.setdefault(
            key, {"n": 0, "BLEND_correct": 0, "M0_correct": 0, "w2c": 0, "c2w": 0}
        )
        row["n"] = int(row["n"]) + 1
        row["BLEND_correct"] = int(row["BLEND_correct"]) + blend_correct[sid]
        row["M0_correct"] = int(row["M0_correct"]) + m0_correct[sid]
        difference = blend_correct[sid] - m0_correct[sid]
        if difference > 0:
            row["w2c"] = int(row["w2c"]) + 1
        elif difference < 0:
            row["c2w"] = int(row["c2w"]) + 1
    for row in groups.values():
        n = int(row["n"])
        row["BLEND_accuracy"] = int(row["BLEND_correct"]) / n
        row["M0_accuracy"] = int(row["M0_correct"]) / n
        row["delta_samples"] = int(row["BLEND_correct"]) - int(row["M0_correct"])
        row["delta_pp"] = 100.0 * int(row["delta_samples"]) / n
        row["share_of_population"] = n / len(sample_ids)
    return dict(sorted(groups.items()))


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


def read(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the one registered lock read. Called exactly once."""

    attempts = ra.arm_offline_guard()
    service_log_before = d5._service_log_measurement()

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    populations = load_populations(repo_root)
    arms = {
        pin.arm_id: load_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in ARM_PINS
    }

    expected = set(populations.dev1000)
    for arm in arms.values():
        if set(arm.responses) != expected:
            raise ReadError(f"{arm.pin.arm_id}: sealed outputs do not cover exactly DEV-1000")

    # The campaign's own committed proof of the partition must agree with the
    # receipt this read re-derived, or the two records contradict each other.
    lock_population = arms["BLEND"].report["lock_statistic_population"]
    if str(lock_population["receipt_sha256"]) != populations.receipt_hashes["DEV-1000-NEW500"]:
        raise ReadError("the BLEND report's NEW500 receipt hash is not the receipt this read loaded")
    if int(lock_population["count"]) != len(populations.new500):
        raise ReadError("the BLEND report's NEW500 count is not 500")

    blend_records = load_per_sample_mechanical(arm=arms["BLEND"])
    m0_records = load_per_sample_mechanical(arm=arms["M0"])

    # GOLD OPENS HERE, ONCE, SCORING-SIDE, FOR ALL 1,000.
    gold_by_sample = dc._load_gold(
        data_root=data_root, repo_root=repo_root, sample_ids=set(populations.dev1000)
    )
    scored = {
        arm_id: d5.score_arm(arm=arm, gold_by_sample=gold_by_sample)
        for arm_id, arm in arms.items()
    }
    m0 = scored["M0"].correct
    blend = scored["BLEND"].correct
    new500 = populations.new500
    dev500 = populations.dev500
    dev1000 = populations.dev1000

    # ---------------- PRIMARY (the frozen statistic + LOCK CONDITION) ------
    primary = d5.paired_comparison(
        label=(
            "PRIMARY (preregistered): paired per-sample BLEND(v2) - M0 over the 500 UNEXPOSED samples"
        ),
        population="DEV-1000-NEW500 (500 unexposed)",
        sample_ids=new500,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    bootstrap = primary["bootstrap"]
    ci90_low = float(bootstrap["ci90_low_pp"])
    excludes_zero = bool(bootstrap["ci90_excludes_zero"])
    if ci90_low >= LOCK_THRESHOLD_PP:
        outcome = "LOCKED"
    elif excludes_zero:
        outcome = "CONFIRMED-BUT-SHRUNKEN"
    else:
        outcome = "NOT-CONFIRMED"
    primary["lock_condition"] = LOCK_CONDITION
    primary["lock_threshold_pp"] = LOCK_THRESHOLD_PP
    primary["lock_condition_met"] = outcome == "LOCKED"
    primary["lock_outcome"] = outcome
    primary["lock_outcome_definitions"] = {
        "LOCKED": "the 90% CI lower bound is at least +10 pp",
        "CONFIRMED-BUT-SHRUNKEN": (
            "the 90% CI excludes zero but its lower bound falls below +10 pp -- does NOT lock; "
            "returns to iteration"
        ),
        "NOT-CONFIRMED": "the 90% CI includes zero",
    }
    primary["ci90_lower_bound_margin_vs_threshold_pp"] = ci90_low - LOCK_THRESHOLD_PP
    primary["statistic_citation"] = STATISTIC_CITATION
    primary["variance_prior_carried"] = VARIANCE_PRIOR
    primary["fit_not_validated_disclosure"] = LOCK_CANDIDATE["fit_not_validated_disclosure"]

    # ---------------- SECONDARIES (reported, no claim) --------------------
    secondaries: dict[str, object] = {}
    secondaries["exposed_500_blend_vs_m0"] = d5.paired_comparison(
        label=(
            "SECONDARY: BLEND(v2) - M0 on the nested PRIOR-EXPOSED DEV-500 "
            "(never pooled into the lock claim)"
        ),
        population="DEV-500 (500 prior-exposed)",
        sample_ids=dev500,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["pooled_1000_blend_vs_m0_descriptive"] = d5.paired_comparison(
        label=(
            "SECONDARY (DESCRIPTIVE ONLY, explicitly NOT the lock claim): BLEND(v2) - M0 pooled "
            "over all 1,000"
        ),
        population="DEV-1000 (500 unexposed + 500 prior-exposed, pooled)",
        sample_ids=dev1000,
        baseline_name="M0",
        baseline=m0,
        treatment_name="BLEND",
        treatment=blend,
    )
    secondaries["override_subgroup"] = override_analysis(
        blend=arms["BLEND"],
        m0_arm=arms["M0"],
        records=blend_records,
        gold_by_sample=gold_by_sample,
        m0_correct=m0,
        blend_correct=blend,
        new500=new500,
        dev500=dev500,
    )
    secondaries["dispatch_decomposition_unexposed500"] = dispatch_decomposition(
        sample_ids=new500, records=blend_records, blend_correct=blend, m0_correct=m0
    )
    secondaries["dispatch_decomposition_exposed500"] = dispatch_decomposition(
        sample_ids=dev500, records=blend_records, blend_correct=blend, m0_correct=m0
    )
    secondaries["dispatch_decomposition_pooled1000"] = dispatch_decomposition(
        sample_ids=dev1000, records=blend_records, blend_correct=blend, m0_correct=m0
    )

    # ---------------- Scale stability (the question this tier exists for) --
    delta_pp = float(primary["delta_pp"])
    secondaries["scale_stability_vs_dev500"] = {
        "what_this_is": (
            "the comparison the lock tier exists to make: this tier's UNEXPOSED-500 margin against "
            "the sealed DEV-500 tier's UNEXPOSED-400 margin, at double the held-out scale"
        ),
        "dev500_unexposed400": DEV500_REFERENCE,
        "dev1000_unexposed500": {
            "population": "DEV-1000-NEW500 (500 unexposed)",
            "n": len(new500),
            "M0_correct": primary["M0_correct"],
            "M0_accuracy": primary["M0_accuracy"],
            "BLEND_correct": primary["BLEND_correct"],
            "BLEND_accuracy": primary["BLEND_accuracy"],
            "delta_samples": primary["delta_samples"],
            "delta_pp": delta_pp,
            "ci90_low_pp": ci90_low,
            "ci90_high_pp": bootstrap["ci90_high_pp"],
            "ci95_low_pp": bootstrap["ci95_low_pp"],
            "ci95_high_pp": bootstrap["ci95_high_pp"],
            "sigma_hat_pp": bootstrap["sigma_hat_pp"],
            "wrong_to_correct_count": primary["wrong_to_correct_count"],
            "correct_to_wrong_count": primary["correct_to_wrong_count"],
            "cell": "v2 lock candidate (v1 frozen cell + the delta >= 0.14 retain-override)",
        },
        "margin_change_pp": delta_pp - float(DEV500_REFERENCE["delta_pp"]),
        "dev1000_point_inside_dev500_ci90": (
            float(DEV500_REFERENCE["ci90_low_pp"]) <= delta_pp <= float(DEV500_REFERENCE["ci90_high_pp"])
        ),
        "dev500_point_inside_dev1000_ci90": (
            ci90_low <= float(DEV500_REFERENCE["delta_pp"]) <= float(bootstrap["ci90_high_pp"])
        ),
        "ci90_intervals_overlap": not (
            ci90_low > float(DEV500_REFERENCE["ci90_high_pp"])
            or float(bootstrap["ci90_high_pp"]) < float(DEV500_REFERENCE["ci90_low_pp"])
        ),
        "not_an_independent_replication": (
            "the two populations are DISJOINT (NEW500 was unexposed at both tiers, NEW400 is inside "
            "this tier's prior-exposed half) but the ARMS DIFFER: DEV-500 flew the v1 cell and "
            "DEV-1000 flew v2 = v1 plus the retain-override. The override's realized contribution to "
            "the unexposed-500 statistic is reported separately and is bounded at 3 samples, so the "
            "comparison is between two cells that differ by a mechanism of bounded size, not between "
            "two runs of the same cell"
        ),
    }

    # ---------------- Descriptive profiles --------------------------------
    arm_accuracies = {
        "NEW500 (500 unexposed)": {
            name: {
                "correct": sum(table[sid] for sid in new500),
                "accuracy": sum(table[sid] for sid in new500) / len(new500),
            }
            for name, table in (("M0", m0), ("BLEND", blend))
        },
        "DEV-500 (500 prior-exposed)": {
            name: {
                "correct": sum(table[sid] for sid in dev500),
                "accuracy": sum(table[sid] for sid in dev500) / len(dev500),
            }
            for name, table in (("M0", m0), ("BLEND", blend))
        },
        "DEV-1000 (pooled, descriptive)": {
            name: {
                "correct": sum(table[sid] for sid in dev1000),
                "accuracy": sum(table[sid] for sid in dev1000) / len(dev1000),
            }
            for name, table in (("M0", m0), ("BLEND", blend))
        },
    }

    profiles = {
        "per_scenario_unexposed500": d5.scenario_profile(
            sample_ids=new500, gold_by_sample=gold_by_sample, arms={"M0": m0, "BLEND": blend}
        ),
        "per_scenario_exposed500": d5.scenario_profile(
            sample_ids=dev500, gold_by_sample=gold_by_sample, arms={"M0": m0, "BLEND": blend}
        ),
        "confusion_unexposed500": {
            name: d5.confusion_profile(
                sample_ids=new500, gold_by_sample=gold_by_sample, scored=scored[name]
            )
            for name in ("M0", "BLEND")
        },
        "confusion_exposed500": {
            name: d5.confusion_profile(
                sample_ids=dev500, gold_by_sample=gold_by_sample, scored=scored[name]
            )
            for name in ("M0", "BLEND")
        },
        "subgroups_unexposed500_two_way": {
            "BLEND_vs_M0": d5.subgroup_profile(
                sample_ids=new500,
                arm=arms["BLEND"],
                scored=scored["BLEND"],
                reference=m0,
                reference_name="M0",
            )
        },
        "subgroups_exposed500_two_way": {
            "BLEND_vs_M0": d5.subgroup_profile(
                sample_ids=dev500,
                arm=arms["BLEND"],
                scored=scored["BLEND"],
                reference=m0,
                reference_name="M0",
            )
        },
        "field_decomposition_unexposed500": {
            name: {
                "scenario_exact": sum(scored[name].scenario_exact[sid] for sid in new500),
                "action_exact": sum(scored[name].action_exact[sid] for sid in new500),
                "scenario_action_exact": sum(scored[name].correct[sid] for sid in new500),
                "unparsed": sum(1 for sid in new500 if not scored[name].parsed[sid]),
                "slot_f1_exact_mean": sum(scored[name].slot_f1[sid] for sid in new500)
                / len(new500),
            }
            for name in ("M0", "BLEND")
        },
        "field_decomposition_exposed500": {
            name: {
                "scenario_exact": sum(scored[name].scenario_exact[sid] for sid in dev500),
                "action_exact": sum(scored[name].action_exact[sid] for sid in dev500),
                "scenario_action_exact": sum(scored[name].correct[sid] for sid in dev500),
                "unparsed": sum(1 for sid in dev500 if not scored[name].parsed[sid]),
                "slot_f1_exact_mean": sum(scored[name].slot_f1[sid] for sid in dev500)
                / len(dev500),
            }
            for name in ("M0", "BLEND")
        },
    }

    ceiling = d5.reachability_ceiling(
        repo_root=repo_root,
        data_root=data_root,
        sample_ids=new500,
        gold_by_sample=gold_by_sample,
        blend_run_dir=arms["BLEND"].run_dir,
    )
    # The imported helper hard-codes its original caller's population label;
    # the arithmetic is population-agnostic, so only the label is corrected.
    ceiling["population_label_as_returned_by_the_imported_helper"] = ceiling["population"]
    ceiling["population"] = "DEV-1000-NEW500 (500 unexposed)"

    service_log_after = d5._service_log_measurement()
    zero_contact = {
        "registered_contacts": {"frozen_core": 0, "pinned_tool_embedding": 0, "tokenizer": 0},
        "offline_guard": {
            "armed_before_any_input_was_opened": True,
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
        },
        "resident_service_log": {
            "path": str(d5.SERVICE_LOG_PATH),
            "before": service_log_before,
            "after": service_log_after,
            "byte_length_identical": service_log_before.get("bytes")
            == service_log_after.get("bytes"),
            "sha256_identical": service_log_before.get("sha256")
            == service_log_after.get("sha256"),
            "note": (
                "the resident decoder is UP and idle; this read never started, stopped, probed, "
                "reconfigured or contacted it, and the log is measured before and after"
            ),
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
            "candidate_selection": CANDIDATE_SELECTION_RELPATH,
            "campaign_fragment": CAMPAIGN_FRAGMENT_RELPATH,
            "campaign_landings": ["11309317", "fbc651bb", "9928d7ce"],
            "statistic_citation": STATISTIC_CITATION,
            "preregistration_erratum": PREREGISTRATION_ERRATUM,
        },
        "one_shot": {
            "rule": (
                "computed exactly once as preregistered; no threshold change, no re-computation "
                "with different parameters, no partial re-read, no re-fly, whatever the outcome"
            ),
            "gold_opened": "ONCE, here, scoring-side, for all 1,000 DEV-1000 samples",
            "variance_prior_carried": VARIANCE_PRIOR,
        },
        "lock_candidate": LOCK_CANDIDATE,
        "populations": {
            "dev1000_n": len(dev1000),
            "unexposed_new500_n": len(new500),
            "exposed_dev500_n": len(dev500),
            "new500_derivation": (
                "deterministic set difference DEV-1000 minus DEV-500, re-derived on the receipts' "
                "`id` field (never the carrier-prefixed `key` field -- the A4 lesson, asserted "
                "non-empty here) and matched to its own committed receipt"
            ),
            "receipt_file_sha256": dict(populations.receipt_hashes),
            "dev1000_load_split_identity": RECEIPT_PINS["DEV-1000"][1],
            "dev1000_receipt_integrity": RECEIPT_PINS["DEV-1000"][2],
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
            "call the sealed round launchers make post-seal, reached here through the DEV-500 "
            "read's own imported score_arm"
        ),
        "arm_accuracies": arm_accuracies,
        "primary": primary,
        "secondaries": secondaries,
        "reachability_ceiling": ceiling,
        "profiles": profiles,
        "mechanical_cross_checks": {
            "blend_dispatch_decomposition_exact": {
                "retain_primary": int(arms["BLEND"].report["mechanical"][
                    "one_contact_trajectories_retained_primary"
                ]),
                "dead_direct_dispatched": int(
                    arms["BLEND"].report["mechanical"]["retain_override"]["dead_direct_dispatched"]
                ),
                "override_dispatched": int(
                    arms["BLEND"].report["mechanical"]["retain_override"]["override_dispatched"]
                ),
                "total_dispatched": int(
                    arms["BLEND"].report["mechanical"]["two_contact_trajectories_dispatched"]
                ),
                "direct_labels_recovered": int(
                    arms["BLEND"].report["mechanical"]["direct_label_recovered_samples"]
                ),
                "re_verified_against_per_sample_records": True,
            },
            "branch_only_property": {
                "holds": bool(
                    arms["BLEND"].report["mechanical"]["retain_override"]["branch_only_holds"]
                ),
                "supply_mismatches": list(
                    arms["BLEND"].report["mechanical"]["retain_override"][
                        "branch_only_supply_mismatches"
                    ]
                ),
                "source": "the launcher's own pure-function replay, asserted at landing",
            },
            "m0_arm_is_single_contact": {
                "retain_primary": int(
                    arms["M0"].report["mechanical"]["one_contact_trajectories_retained_primary"]
                ),
                "dispatched": int(
                    arms["M0"].report["mechanical"]["two_contact_trajectories_dispatched"]
                ),
                "override_fires": int(
                    arms["M0"].report["mechanical"]["retain_override"]["fired"]
                ),
            },
            "response_text_rehash_matched_sealed_hash_on_every_sample": True,
            "m0_per_sample_records_loaded": len(m0_records),
            "blend_per_sample_records_loaded": len(blend_records),
        },
        "campaign_spend": campaign_spend,
        "zero_contact_proof": zero_contact,
        "scope": {
            "binding": (
                "dev-tier. A LOCK records the cell as the baseline version for large-scale "
                "experiments; it does NOT authorize test contact, a superiority claim, a "
                "generalization claim, or any Stage-3 activity. FINAL60 and test remain untouched"
            ),
            "interpretation": (
                "this artifact reports the registered outputs only; the coordinator interprets"
            ),
        },
    }


def _campaign_spend(arms: Mapping[str, d5.ArmOutputs]) -> dict[str, object]:
    """Campaign totals, re-summed from the two committed reports."""

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
        "frozen_core_contacts": 3400,
        "pinned_tool_embedding_contacts": 1200,
        "metered_audio_seconds": 9000,
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
        f"PRIMARY  M0 {primary['M0_correct']}/500  BLEND(v2) {primary['BLEND_correct']}/500  "
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
    print(f"  LOCK CONDITION (90% CI lower bound >= +10 pp): {primary['lock_outcome']}")
    return 0


__all__ = [
    "ARM_PINS",
    "DEV500_REFERENCE",
    "EXPOSURE_ROW_ID",
    "LOCK_CANDIDATE",
    "LOCK_CONDITION",
    "LOCK_THRESHOLD_PP",
    "PREREGISTRATION_ERRATUM",
    "Populations",
    "ReadError",
    "SCHEMA",
    "STATISTIC_CITATION",
    "dispatch_decomposition",
    "load_arm",
    "load_per_sample_mechanical",
    "load_populations",
    "main",
    "override_analysis",
    "read",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
