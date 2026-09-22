"""Reviewer-perspective statistical audit of the SEALED DEV-100 campaign.

Exposure row ``SAEA-SN-MF-DEV100-REVIEWER-AUDIT`` (registered before any
computation): zero frozen-core contacts, zero embedding-tool contacts, zero
tokenizer contacts, zero HTTP requests of any kind. Everything this module
reads is already landed: the four committed round reports, the committed
DEV-100 split receipt and knowledge-build receipt, the four sealed attempt
stores (per-sample score files and durable traces), the pinned TRAIN
knowledge snapshot, and devel gold read scoring-side for the SAME 100
samples whose gold was lawfully opened at each round seal.

Why this exists
---------------
The campaign's headline is a paired accuracy gain of the knowledge-
conditioned BLEND arm over the M0 direct-decode arm on DEV-100 (+15 at
rounds 0/1, +17 at round 2, +19 at round 3). Every one of those numbers is
a point estimate on 100 exposed samples, produced by a stack with a
*documented* nondeterminism channel (cross-attempt direct-decode byte
agreement 75-81/100). A reviewer will not accept a point estimate from that
setting; this module asks, and answers by computation, the six questions a
reviewer would actually ask:

1. **Uncertainty.** A per-sample paired cluster bootstrap on BLEND - M0
   (:mod:`.bootstrap`, N = 10,000, seed 20260807, 90% percentile CI) plus
   discordant-pair accounting -- exact-binomial McNemar, its mid-p variant,
   and the continuity-corrected chi-square.
2. **Variance-channel robustness.** A conservative floor that re-scores the
   samples in the documented byte-instability channel *against* the claim,
   so the headline is confronted with its own worst case rather than its
   best one.
3. **Baseline fairness.** What arm M0 does and does not contain, the
   DEV-100 majority-class floor computed from gold, the per-scenario and
   per-channel M0 profile, a same-session in-flight direct comparator, and
   a label-space conformance measurement that separates "the knowledge
   plane supplied a fact" from "the knowledge plane supplied the label
   vocabulary".
4. **Leakage and hygiene.** Landed receipts are CITED and their pinned
   fields are re-asserted; nothing is re-derived, because re-deriving a
   decontamination verdict would mean opening rosters this row does not
   open.
5. **Effect attribution.** Round-to-round deltas split into a mechanism
   channel and the documented direct-byte variance channel, using only the
   sealed movement lists and the sealed direct-agreement lists.
6. **Reviewer report.** The numbers above, assembled; the prose lives in
   ``docs/readiness/2026-08-24-dev100-reviewer-audit.md``.

Honesty about what this module can and cannot say
-------------------------------------------------
It is an ITERATION-TIER adversarial read over exposed data. It computes no
held-out result, authorises no flight, selects no knob, and reaches no
verdict. Every interval it publishes is an interval *on DEV-100*, whose
samples have been read four times; the ladder's answer to the question the
campaign poses is a one-shot DEV-500 confirmatory reading, which this row
does not authorise and this module cannot substitute for. Where a question
is not decidable from sealed bytes (notably the train-side E108 K0-M0
comparison, which would need a matched re-decode), the module records a
limitation string instead of a number and the report repeats it.

Two-source discipline
---------------------
Every per-sample paired outcome is built TWICE: once from the landed
per-sample score files in the attempt stores, and once, independently, by
reconstructing the paired difference vector from the committed round
report's own ``wrong_to_correct_sample_ids`` / ``correct_to_wrong_sample_ids``
movement lists and arm totals. :func:`paired_rounds` refuses to return
unless the two agree sample-for-sample, so a divergence between what the
committed report says and what the landed store holds is a hard failure,
not a silent preference for one of them.

Deliberate reuse
----------------
The sibling :mod:`.dev100_damage_channel_analysis` already owns identity-
checked readers for the durable trace and devel gold, and
:mod:`.bootstrap` already owns the registration-mandated resampling
primitive with the mandated seed. Both are imported rather than
re-implemented, so the two DEV-100 analyses read identical bytes through
identical code and cannot drift apart.

Offline proof
-------------
:func:`arm_offline_guard` replaces ``socket.socket.connect``,
``socket.socket.connect_ex`` and ``socket.create_connection`` with raisers
that count attempts, BEFORE any input is opened. The receipt publishes the
count. The sibling analysis proved its offline claim with a byte-identical
resident ``server.log``; that proof is unavailable while a concurrent
flight owns the log, and an armed guard that refuses every outbound
connection is a strictly stronger statement than an unchanged log anyway --
it cannot be satisfied by a contact that happens to log nothing.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import socket
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import bootstrap as bs
from . import dev100_damage_channel_analysis as dc

SCHEMA = "saea-dev100-reviewer-audit-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-DEV100-REVIEWER-AUDIT"

# The four sealed round reports, relative to the study repo root. Round 3 is
# included because it was committed (land commit 03a85964) before this audit
# reached synthesis; had it not been, it would have been excluded outright.
ROUND_REPORT_RELPATHS = {
    0: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round0/round0-report.json",
    1: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round1/round1-report.json",
    2: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round2/round2-report.json",
    3: "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round3/round3-report.json",
}

# Per-round arm keys inside each attempt store's ``round{N}-scores.json``.
BLEND_ARM_KEYS = {0: "BLEND", 1: "BLEND_ROUND1", 2: "BLEND_ROUND2", 3: "BLEND_ROUND3"}
M0_ARM_KEYS = {0: "M0", 1: "M0_SEALED_ROUND0", 2: "M0_SEALED_ROUND0", 3: "M0_SEALED_ROUND0"}

DEV100_RECEIPT_RELPATH = "docs/receipts/probe-samples/DEV-100.json"
KB_BUILD_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-full.json"
SPLIT_IDENTITY_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-23-dev100-campaign-preregistration.md"
DAMAGE_CHANNEL_RELPATH = "docs/readiness/2026-08-24-dev100-damage-channel-analysis.md"

# The primary (best) sealed round. Asserted against the data, never trusted.
EXPECTED_PRIMARY_ROUND = 3

# Cited constant, NOT recomputed here: the train-side EFFECT-C108 direct-decode
# reference a reviewer will hold the DEV-100 M0 number against.
E108_K0M0_CORRECT = 77
E108_N = 108
E108_SOURCE = (
    "docs/readiness/2026-08-21-speech-native-agent-loop-training-free-rl-plan.md "
    "(EFFECT-C108 replacement read, sha256 6f7017fb...f40a); restated in "
    "docs/readiness/2026-08-19-scheme-scoreboard.md"
)

# SLURP's full intent inventory size, from the landed KB build receipt's own
# ``coverage_report.counts.train_intents``; re-asserted at load, never assumed.
EXPECTED_TRAIN_INTENTS = 60


class AuditError(RuntimeError):
    """Raised when a landed input contradicts a committed record, or when a
    pinned identity does not match. Never raised for a legitimate data
    shape -- an audit that silently tolerates a contradiction is worthless."""


# ---------------------------------------------------------------------------
# Offline guard
# ---------------------------------------------------------------------------


class _ConnectAttempts:
    """Mutable counter the guard closes over (published in the receipt).

    Also carries the pre-arm originals of the three patched socket
    attributes, so the SAME object callers already read ``.count``/
    ``.targets`` off of can restore them via :meth:`disarm`. Neither
    attribute is read by any receipt writer today (only ``.count`` and
    ``.targets`` are), so adding them changes no published output."""

    def __init__(self) -> None:
        self.count = 0
        self.targets: list[str] = []
        self._original_connect = None
        self._original_connect_ex = None
        self._original_create_connection = None
        self._armed = False

    def disarm(self) -> None:
        """Restore ``socket.socket.connect``/``connect_ex`` and
        ``socket.create_connection`` to what they were immediately before
        this guard's own :func:`arm_offline_guard` call.

        Idempotent: a no-op if this guard was never armed, or has already
        been disarmed. Production ``main()`` callers never call this --
        their whole point is that the guard stays armed for the rest of
        that process (see the module docstring's "Offline proof" section);
        only tests and the ``disarmed_offline_guard`` context manager use
        it, to stop one test's guard from leaking into the next test's
        socket use."""

        if not self._armed:
            return
        socket.socket.connect = self._original_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._original_connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._original_create_connection  # type: ignore[assignment]
        self._armed = False


def arm_offline_guard() -> _ConnectAttempts:
    """Make every outbound socket connection raise, and count the attempts.

    Called before any input is opened. A model-free row's whole claim is
    that it contacts nothing; this turns that claim into something the
    process itself enforces rather than something the reader has to take on
    trust from a log file the process does not own.

    The guard stays armed until the returned object's ``disarm()`` is
    called (or never, for a production ``main()``) -- arming semantics are
    unchanged from before ``disarm()`` existed."""

    attempts = _ConnectAttempts()
    attempts._original_connect = socket.socket.connect
    attempts._original_connect_ex = socket.socket.connect_ex
    attempts._original_create_connection = socket.create_connection
    attempts._armed = True

    def _refuse(self, address, *args, **kwargs):  # noqa: ANN001 - socket API shape
        attempts.count += 1
        attempts.targets.append(repr(address))
        raise AuditError(
            f"offline guard: {EXPOSURE_ROW_ID} registered ZERO contacts, but a network "
            f"connection to {address!r} was attempted"
        )

    def _refuse_create(address, *args, **kwargs):  # noqa: ANN001 - socket API shape
        attempts.count += 1
        attempts.targets.append(repr(address))
        raise AuditError(
            f"offline guard: {EXPOSURE_ROW_ID} registered ZERO contacts, but "
            f"socket.create_connection({address!r}) was attempted"
        )

    socket.socket.connect = _refuse  # type: ignore[method-assign]
    socket.socket.connect_ex = _refuse  # type: ignore[method-assign]
    socket.create_connection = _refuse_create  # type: ignore[assignment]
    return attempts


@contextlib.contextmanager
def disarmed_offline_guard():
    """Context-manager form of :func:`arm_offline_guard`: arm for the body,
    then unconditionally :meth:`~_ConnectAttempts.disarm` on exit (normal
    return or exception).

    For tests, and any other short-lived offline-proof scope that must not
    leak its armed guard into whatever runs next in the same process.
    Production ``main()`` callers keep calling :func:`arm_offline_guard`
    directly and are unaffected -- this is an additive alternative entry
    point, not a replacement for the existing one."""

    attempts = arm_offline_guard()
    try:
        yield attempts
    finally:
        attempts.disarm()


# ---------------------------------------------------------------------------
# Landed inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundRecord:
    """One sealed round, from BOTH its committed report and its landed store."""

    index: int
    report: Mapping[str, object]
    run_dir: Path
    m0: Mapping[str, int]
    blend: Mapping[str, int]
    m0_fields: Mapping[str, tuple[int, int]]
    blend_fields: Mapping[str, tuple[int, int]]
    m0_source: str
    blend_arm_key: str

    @property
    def gain(self) -> int:
        return sum(self.blend.values()) - sum(self.m0.values())

    def difference(self, sample_id: str) -> int:
        return self.blend[sample_id] - self.m0[sample_id]


def load_dev100_ids(repo_root: Path) -> tuple[str, ...]:
    """The 100 sample ids, from the COMMITTED split receipt -- so the
    bootstrap's resampling universe is the registered split, not whatever
    happens to be in a run directory."""

    receipt = json.loads((Path(repo_root) / DEV100_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    ids = tuple(str(item["id"]) for item in receipt["items"])
    if len(ids) != int(receipt["n_items"]) or len(set(ids)) != len(ids):
        raise AuditError("DEV-100 receipt item list is not 100 distinct ids")
    return ids


def paired_rounds(*, repo_root: Path, sample_ids: Sequence[str]) -> dict[int, RoundRecord]:
    """Per-round paired outcome vectors, built twice and cross-checked.

    Source A is the landed ``round{N}-scores.json`` in the round's own
    attempt store. Source B is the committed round report: its arm totals
    plus its two movement lists determine the paired DIFFERENCE vector
    exactly (a sample outside both lists has ``blend == m0``), which is
    everything the gain and the bootstrap consume. Disagreement raises."""

    rounds: dict[int, RoundRecord] = {}
    for index, relpath in sorted(ROUND_REPORT_RELPATHS.items()):
        report = json.loads((Path(repo_root) / relpath).read_text(encoding="utf-8"))
        if int(report["round_index"]) != index:
            raise AuditError(f"round report {relpath} declares round_index {report['round_index']}")
        run_dir = Path(str(report["run_dir"]))
        scores = json.loads((run_dir / f"round{index}-scores.json").read_text(encoding="utf-8"))
        blend_key = BLEND_ARM_KEYS[index]
        m0_key = M0_ARM_KEYS[index]
        blend = {sid: int(bool(scores[blend_key][sid]["correct"])) for sid in sample_ids}
        m0 = {sid: int(bool(scores[m0_key][sid]["correct"])) for sid in sample_ids}
        blend_fields = {
            sid: (
                int(bool(scores[blend_key][sid]["scenario_exact"])),
                int(bool(scores[blend_key][sid]["action_exact"])),
            )
            for sid in sample_ids
        }
        m0_fields = {
            sid: (
                int(bool(scores[m0_key][sid]["scenario_exact"])),
                int(bool(scores[m0_key][sid]["action_exact"])),
            )
            for sid in sample_ids
        }

        # --- source B: the committed report alone -------------------------
        wrong_to_correct = set(report["wrong_to_correct_sample_ids"])
        correct_to_wrong = set(report["correct_to_wrong_sample_ids"])
        overlap = wrong_to_correct & correct_to_wrong
        if overlap:
            raise AuditError(f"round {index} movement lists overlap on {sorted(overlap)}")
        unknown = (wrong_to_correct | correct_to_wrong) - set(sample_ids)
        if unknown:
            raise AuditError(f"round {index} movement lists name non-DEV-100 ids {sorted(unknown)}")
        for sid in sample_ids:
            expected = 1 if sid in wrong_to_correct else (-1 if sid in correct_to_wrong else 0)
            if blend[sid] - m0[sid] != expected:
                raise AuditError(
                    f"round {index}: landed scores and the committed report disagree on {sid} "
                    f"(store says {blend[sid] - m0[sid]:+d}, report says {expected:+d})"
                )
        arms = report["arms"]
        report_blend_total = int(arms[blend_key if blend_key in arms else "BLEND"]["correct_count"])
        report_m0_total = int(arms["M0"]["correct_count"])
        if sum(blend.values()) != report_blend_total or sum(m0.values()) != report_m0_total:
            raise AuditError(f"round {index}: arm totals disagree with the landed per-sample scores")

        rounds[index] = RoundRecord(
            index=index,
            report=report,
            run_dir=run_dir,
            m0=m0,
            blend=blend,
            m0_fields=m0_fields,
            blend_fields=blend_fields,
            m0_source=str(scores[m0_key][sample_ids[0]].get("source", "")),
            blend_arm_key=blend_key,
        )
    # M0 is one arm flown once: every round must carry the identical vector.
    reference = rounds[0].m0
    for index, record in rounds.items():
        if record.m0 != reference:
            raise AuditError(f"round {index} carries a DIFFERENT M0 vector than round 0")
    return rounds


# ---------------------------------------------------------------------------
# Question 1 -- uncertainty
# ---------------------------------------------------------------------------


def _gain_statistic(m0: Mapping[str, int], blend: Mapping[str, int]):
    """Percentage-point gain of BLEND over M0 on a resampled id multiset."""

    def statistic(ids: Sequence[str]) -> float:
        total = 0
        for sid in ids:
            total += blend[sid] - m0[sid]
        return 100.0 * total / len(ids)

    return statistic


def bootstrap_gain(
    *,
    sample_ids: Sequence[str],
    m0: Mapping[str, int],
    blend: Mapping[str, int],
    n_replicates: int = bs.DEFAULT_N_REPLICATES,
    seed: int = bs.DEFAULT_SEED,
) -> dict[str, object]:
    """90% (and, for completeness, 95%) percentile CI on the paired gain.

    The 95% interval is reported alongside because a reviewer who is handed
    only the interval that happens to exclude zero will ask for the other
    one; publishing both removes the question."""

    statistic = _gain_statistic(m0, blend)
    result = bs.paired_cluster_bootstrap(
        sample_ids=sample_ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=0.90
    )
    ordered = sorted(result.replicates)
    ci95_low = bs._percentile(ordered, 0.025)
    ci95_high = bs._percentile(ordered, 0.975)
    at_or_below_zero = sum(1 for value in result.replicates if value <= 0.0)
    return {
        "point_estimate_pp": result.point_estimate,
        "sigma_hat_pp": result.sigma_hat,
        "ci90_low_pp": result.ci_low,
        "ci90_high_pp": result.ci_high,
        "ci90_excludes_zero": result.ci_low > 0.0,
        "ci95_low_pp": ci95_low,
        "ci95_high_pp": ci95_high,
        "ci95_excludes_zero": ci95_low > 0.0,
        "replicates_at_or_below_zero": at_or_below_zero,
        "replicate_share_at_or_below_zero": at_or_below_zero / result.n_replicates,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
        "resampling": "per-sample paired cluster bootstrap over the 100 DEV-100 ids; the SAME "
        "resampled multiset scores both arms, preserving the pairing",
    }


def mcnemar(n01: int, n10: int) -> dict[str, object]:
    """Discordant-pair accounting: exact binomial, mid-p, and chi-square.

    ``n01`` is wrong->correct (BLEND repairs a direct error), ``n10`` is
    correct->wrong (BLEND damages a direct success). Concordant pairs carry
    no information about the sign of the effect and are excluded by
    construction -- which is exactly why this test is reported ALONGSIDE the
    bootstrap and never instead of it: it conditions on the discordant set
    and so answers a narrower question than "how big is the gain"."""

    n = n01 + n10
    if n == 0:
        return {"n01": 0, "n10": 0, "discordant": 0, "note": "no discordant pairs"}
    smaller = min(n01, n10)
    tail = sum(math.comb(n, k) for k in range(smaller + 1)) * (0.5**n)
    exact_p = min(1.0, 2.0 * tail)
    point_mass = math.comb(n, smaller) * (0.5**n)
    mid_p = min(1.0, 2.0 * (tail - 0.5 * point_mass))
    chi2 = (abs(n01 - n10) - 1) ** 2 / n if n01 != n10 else 0.0
    chi2_p = math.erfc(math.sqrt(chi2 / 2.0)) if chi2 > 0 else 1.0
    return {
        "n01_wrong_to_correct": n01,
        "n10_correct_to_wrong": n10,
        "discordant_pairs": n,
        "odds_ratio_n01_over_n10": (n01 / n10) if n10 else None,
        "exact_binomial_two_sided_p": exact_p,
        "mid_p_two_sided": mid_p,
        "chi_square_continuity_corrected": chi2,
        "chi_square_two_sided_p": chi2_p,
    }


# ---------------------------------------------------------------------------
# Question 2 -- the variance channel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VarianceChannel:
    """The documented direct-decode byte-instability channel, per round and
    pooled, plus the samples whose scored outcome actually moved with it."""

    per_round_disagree: Mapping[int, tuple[str, ...]]
    unstable_union: tuple[str, ...]
    unstable_intersection: tuple[str, ...]
    flipped: tuple[str, ...]
    unstable_and_flipped: tuple[str, ...]


def variance_channel(rounds: Mapping[int, RoundRecord], sample_ids: Sequence[str]) -> VarianceChannel:
    """Byte-unstable samples (vs the M0 responses the pairing is built on)
    and samples whose BLEND correctness is not constant across the rounds.

    Byte instability is read from each round's own
    ``cross_attempt_direct_agreement.disagree_sample_ids``: the per-sample
    sha256 inequality between that round's flown direct decode and the
    attempt-1 M0 response the paired comparison uses as its baseline. It is
    the channel by which two arms can differ WITHOUT the mechanism doing
    anything at all."""

    per_round: dict[int, tuple[str, ...]] = {}
    for index, record in sorted(rounds.items()):
        block = record.report["cross_attempt_direct_agreement"]
        ids = tuple(str(value) for value in block["disagree_sample_ids"])
        unknown = set(ids) - set(sample_ids)
        if unknown:
            raise AuditError(f"round {index} disagreement list names non-DEV-100 ids {sorted(unknown)}")
        if len(ids) + int(block["agree_count"]) != len(sample_ids):
            raise AuditError(f"round {index} agreement count and disagreement list do not sum to 100")
        per_round[index] = ids
    union = tuple(sorted(set().union(*per_round.values())))
    intersection = tuple(sorted(set.intersection(*(set(v) for v in per_round.values()))))
    flipped = tuple(
        sid for sid in sample_ids if len({record.blend[sid] for record in rounds.values()}) > 1
    )
    return VarianceChannel(
        per_round_disagree=per_round,
        unstable_union=union,
        unstable_intersection=intersection,
        flipped=flipped,
        unstable_and_flipped=tuple(sorted(set(union) & set(flipped))),
    )


def conservative_floors(
    *,
    sample_ids: Sequence[str],
    rounds: Mapping[int, RoundRecord],
    primary: int,
    channel: VarianceChannel,
) -> dict[str, object]:
    """Three floors under the headline gain, from mild to punitive.

    ``observed_worst`` -- for every sample, take its WORST paired outcome
    across the four sealed rounds. No fiction: every value is something the
    stack actually produced. This is the floor a reviewer can be argued
    into, because it is a measurement.

    ``adversarial_flipped`` -- the floor the audit brief mandates: every
    sample that is BOTH byte-unstable (in some round's direct-disagreement
    list) AND demonstrably flipped its scored outcome across rounds is
    scored against the claim (BLEND wrong, M0 correct). This is a fiction
    on purpose: it asks what survives if every sample the variance channel
    provably touched had gone the other way.

    ``adversarial_all_unstable`` -- the same fiction applied to the whole
    byte-unstable union, flipped or not. It is reported for completeness
    and should be read as a bound on the bound: it charges the claim for
    samples whose outcome never moved, so a gain that survives it survives
    anything."""

    record = rounds[primary]
    base = {sid: record.difference(sid) for sid in sample_ids}

    observed_worst = {sid: min(rounds[i].difference(sid) for i in rounds) for sid in sample_ids}
    adversarial_flipped = dict(base)
    for sid in channel.unstable_and_flipped:
        adversarial_flipped[sid] = -1
    adversarial_all = dict(base)
    for sid in channel.unstable_union:
        adversarial_all[sid] = -1

    def summarise(name: str, differences: Mapping[str, int], charged: Sequence[str]) -> dict[str, object]:
        return {
            "floor_name": name,
            "gain_samples": sum(differences.values()),
            "gain_pp": 100.0 * sum(differences.values()) / len(sample_ids),
            "wrong_to_correct": sum(1 for value in differences.values() if value > 0),
            "correct_to_wrong": sum(1 for value in differences.values() if value < 0),
            "samples_charged": len(charged),
            "charged_sample_ids": list(charged),
        }

    floors = {
        "headline": summarise(f"round-{primary} as sealed", base, ()),
        "observed_worst": summarise(
            "per-sample worst paired outcome across all sealed rounds", observed_worst, ()
        ),
        "adversarial_flipped": summarise(
            "byte-unstable AND cross-round-flipped samples scored against the claim",
            adversarial_flipped,
            channel.unstable_and_flipped,
        ),
        "adversarial_all_unstable": summarise(
            "every byte-unstable sample scored against the claim",
            adversarial_all,
            channel.unstable_union,
        ),
    }

    # The mandated floor is the headline claim's real exposure, so it gets an
    # interval too -- a floor without one is just a different point estimate.
    zeros = {sid: 0 for sid in sample_ids}
    floors["adversarial_flipped_bootstrap"] = bootstrap_gain(
        sample_ids=sample_ids,
        m0=zeros,
        blend=adversarial_flipped,
    )
    floors["observed_worst_bootstrap"] = bootstrap_gain(
        sample_ids=sample_ids,
        m0=zeros,
        blend=observed_worst,
    )
    floors["discordant_pairs_in_the_variance_channel"] = {
        "primary_round": primary,
        "wrong_to_correct_byte_unstable": sorted(
            set(rounds[primary].report["wrong_to_correct_sample_ids"]) & set(channel.unstable_union)
        ),
        "correct_to_wrong_byte_unstable": sorted(
            set(rounds[primary].report["correct_to_wrong_sample_ids"]) & set(channel.unstable_union)
        ),
    }
    return floors


# ---------------------------------------------------------------------------
# Question 3 -- baseline fairness
# ---------------------------------------------------------------------------


def majority_class_baseline(gold_by_sample: Mapping[str, object], sample_ids: Sequence[str]) -> dict[str, object]:
    """The floor under any 60-way intent classifier on this split.

    DEV-100 is scenario-stratified (18 scenarios, 6/6/.../5), so the
    scenario marginal is deliberately near-uniform and the intent marginal
    is flatter still. Both are reported: a reviewer asks for the majority
    class, and the honest answer is that stratification has already made it
    close to chance."""

    intents = Counter()
    scenarios = Counter()
    for sid in sample_ids:
        record = gold_by_sample[sid]
        intents[f"{record.scenario}_{record.action}"] += 1
        scenarios[record.scenario] += 1
    top_intent, top_intent_count = intents.most_common(1)[0]
    top_scenario, top_scenario_count = scenarios.most_common(1)[0]
    # Diagnostic only, NOT a baseline: it needs an oracle scenario label.
    oracle_scenario_majority = 0
    by_scenario: dict[str, Counter] = {}
    for sid in sample_ids:
        record = gold_by_sample[sid]
        by_scenario.setdefault(record.scenario, Counter())[record.action] += 1
    for counter in by_scenario.values():
        oracle_scenario_majority += counter.most_common(1)[0][1]
    return {
        "majority_class_intent": top_intent,
        "majority_class_correct": top_intent_count,
        "majority_class_accuracy": top_intent_count / len(sample_ids),
        "distinct_gold_intents": len(intents),
        "distinct_gold_scenarios": len(scenarios),
        "majority_scenario": top_scenario,
        "majority_scenario_count": top_scenario_count,
        "uniform_chance_over_60_intents": 1.0 / EXPECTED_TRAIN_INTENTS,
        "scenario_oracle_majority_action_correct": oracle_scenario_majority,
        "scenario_oracle_note": "NOT a baseline -- it consumes a gold scenario label at "
        "inference time. Reported only to show how much of the 60-way problem is the "
        "action decision inside a known scenario",
        "intent_histogram": dict(sorted(intents.items())),
    }


def per_scenario_profile(
    *,
    gold_by_sample: Mapping[str, object],
    sample_ids: Sequence[str],
    rounds: Mapping[int, RoundRecord],
    primary: int,
) -> dict[str, object]:
    """Where the direct-decode baseline actually loses, and where the
    knowledge plane actually pays -- by scenario and by recording channel.

    The channel split (close-talk vs headset) is read from the sample id
    suffix the SLURP loader itself assigns, so it costs no extra input."""

    record = rounds[primary]
    rows: dict[str, dict[str, object]] = {}
    for sid in sample_ids:
        scenario = gold_by_sample[sid].scenario
        row = rows.setdefault(
            scenario, {"n": 0, "m0_correct": 0, "blend_correct": 0, "w2c": 0, "c2w": 0}
        )
        row["n"] += 1
        row["m0_correct"] += record.m0[sid]
        row["blend_correct"] += record.blend[sid]
        difference = record.difference(sid)
        if difference > 0:
            row["w2c"] += 1
        elif difference < 0:
            row["c2w"] += 1
    for row in rows.values():
        row["m0_accuracy"] = row["m0_correct"] / row["n"]
        row["blend_accuracy"] = row["blend_correct"] / row["n"]
        row["delta_samples"] = row["blend_correct"] - row["m0_correct"]

    channels: dict[str, dict[str, object]] = {}
    for sid in sample_ids:
        key = "headset" if sid.endswith("-headset") else "close-talk"
        row = channels.setdefault(key, {"n": 0, "m0_correct": 0, "blend_correct": 0})
        row["n"] += 1
        row["m0_correct"] += record.m0[sid]
        row["blend_correct"] += record.blend[sid]
    for row in channels.values():
        row["m0_accuracy"] = row["m0_correct"] / row["n"]
        row["blend_accuracy"] = row["blend_correct"] / row["n"]

    m0_accuracies = sorted((row["m0_accuracy"], name) for name, row in rows.items())
    return {
        "primary_round": primary,
        "by_scenario": dict(sorted(rows.items())),
        "by_recording_channel": dict(sorted(channels.items())),
        "worst_three_scenarios_for_m0": [name for _, name in m0_accuracies[:3]],
        "best_three_scenarios_for_m0": [name for _, name in m0_accuracies[-3:]],
        "scenarios_where_blend_loses": sorted(
            name for name, row in rows.items() if row["delta_samples"] < 0
        ),
        "scenarios_where_blend_is_flat": sorted(
            name for name, row in rows.items() if row["delta_samples"] == 0
        ),
    }


def field_profile(
    *, rounds: Mapping[int, RoundRecord], sample_ids: Sequence[str], primary: int
) -> dict[str, object]:
    """Scenario-field and action-field accuracy, per arm.

    ``scenario_action_exact`` is a conjunction, and a conjunction hides
    which conjunct moved. If the direct arm already names the right
    scenario most of the time, then the knowledge plane's job on this split
    is mostly the ACTION decision inside a scenario the frozen core already
    identified -- a much narrower claim than "knowledge raises SLU"."""

    record = rounds[primary]
    out: dict[str, object] = {}
    for name, fields in (("m0", record.m0_fields), ("blend", record.blend_fields)):
        values = [fields[sid] for sid in sample_ids]
        out[name] = {
            "scenario_exact": sum(value[0] for value in values),
            "action_exact": sum(value[1] for value in values),
            "both": sum(1 for value in values if value[0] and value[1]),
            "scenario_right_action_wrong": sum(1 for value in values if value[0] and not value[1]),
            "scenario_wrong_action_right": sum(1 for value in values if not value[0] and value[1]),
        }
    out["primary_round"] = primary
    out["reading"] = (
        "the gain the campaign reports is a gain on the conjunction; this table says how much "
        "of it is a scenario gain and how much is an action gain"
    )
    return out


def prior_only_baseline(
    *,
    rounds: Mapping[int, RoundRecord],
    sample_ids: Sequence[str],
    gold_by_sample: Mapping[str, object],
    train_intent_counts: Mapping[str, int],
    scenarios: frozenset[str],
) -> dict[str, object]:
    """The baseline a reviewer will demand before crediting retrieval.

    Rule: take the flown direct answer's OWN predicted scenario, then emit
    the action that is most frequent for that scenario in TRAIN. It uses no
    retrieval, no second contact, no embedding, no gold -- only the TRAIN
    label prior, which is exposed by construction, and a response the arm
    already produced. If this rule reaches what the full knowledge plane
    reaches, then the plane's measured contribution on this split is a
    prior, not evidence.

    Its cost is ZERO additional contacts: it re-uses the direct responses
    already in the sealed traces."""

    majority_action: dict[str, str] = {}
    per_scenario_counts: dict[str, Counter] = {}
    for target, count in train_intent_counts.items():
        scenario = next((name for name in scenarios if target.startswith(name + "_")), None)
        if scenario is None:
            raise AuditError(f"TRAIN intent {target!r} does not start with a known scenario name")
        action = target[len(scenario) + 1 :]
        per_scenario_counts.setdefault(scenario, Counter())[action] += count
    for scenario, counter in per_scenario_counts.items():
        majority_action[scenario] = counter.most_common(1)[0][0]

    out: dict[str, object] = {}
    for index, record in sorted(rounds.items()):
        direct_texts, _evidence, _supply = dc._load_trace(record.run_dir)
        correct = 0
        unusable_scenario = 0
        agreements_with_blend = 0
        for sid in sample_ids:
            scored = dc.score_response(gold_by_sample[sid], direct_texts[sid])
            predicted_scenario = str(scored["predicted_scenario"])
            if predicted_scenario not in majority_action:
                unusable_scenario += 1
                hit = 0
            else:
                hit = int(
                    predicted_scenario == gold_by_sample[sid].scenario
                    and majority_action[predicted_scenario] == gold_by_sample[sid].action
                )
            correct += hit
            agreements_with_blend += int(hit == record.blend[sid])
        out[f"round{index}"] = {
            "prior_only_correct": correct,
            "prior_only_accuracy": correct / len(sample_ids),
            "blend_correct": sum(record.blend.values()),
            "blend_minus_prior_only_samples": sum(record.blend.values()) - correct,
            "direct_scenario_not_a_slurp_scenario": unusable_scenario,
            "per_sample_agreement_with_blend": agreements_with_blend,
        }
    out["rule"] = (
        "predicted scenario from the arm's own direct answer + argmax_action p_TRAIN(action | "
        "scenario) from the pinned knowledge snapshot's own value counts"
    )
    out["contacts_required"] = 0
    out["majority_action_by_scenario"] = dict(sorted(majority_action.items()))
    return out


def inflight_direct_baseline(
    *,
    rounds: Mapping[int, RoundRecord],
    sample_ids: Sequence[str],
    gold_by_sample: Mapping[str, object],
    label_targets: frozenset[str],
) -> dict[str, object]:
    """Score each round's OWN direct-decode responses -- the comparator that
    removes the cross-attempt confound from the paired contrast.

    The registered M0 arm was flown ONCE, in round-0 attempt 1, on the
    zero-copy build; every later BLEND arm re-decodes the same prompts on
    the base build under 8-slot concurrency. Those two response sets differ
    on 19-25 of 100 samples, so "BLEND minus M0" mixes the mechanism with a
    serving-stack difference. Each round's own direct contact is the
    within-session baseline that difference cannot reach, and the trace
    holds it verbatim.

    The same pass measures LABEL-SPACE CONFORMANCE: whether the direct
    answer even names a (scenario, action) pair that exists in the TRAIN
    intent inventory. A direct answer that invents a label cannot be right,
    and a knowledge plane that merely supplies the legal vocabulary would
    show up here rather than as retrieval success."""

    out: dict[str, object] = {}
    for index, record in sorted(rounds.items()):
        direct_texts, _evidence, _supply = dc._load_trace(record.run_dir)
        missing = set(sample_ids) - set(direct_texts)
        if missing:
            raise AuditError(f"round {index} trace lacks direct responses for {sorted(missing)}")
        correct = 0
        parsed = 0
        out_of_inventory = 0
        field_swap_recoverable = 0
        agrees_with_m0_score = 0
        for sid in sample_ids:
            scored = dc.score_response(gold_by_sample[sid], direct_texts[sid])
            correct += int(bool(scored["correct"]))
            parsed += int(bool(scored["parsed"]))
            predicted = f"{scored['predicted_scenario']}_{scored['predicted_action']}"
            swapped = f"{scored['predicted_action']}_{scored['predicted_scenario']}"
            if predicted not in label_targets:
                out_of_inventory += 1
            gold = f"{gold_by_sample[sid].scenario}_{gold_by_sample[sid].action}"
            if not scored["correct"] and swapped == gold:
                field_swap_recoverable += 1
            agrees_with_m0_score += int(bool(scored["correct"]) == bool(record.m0[sid]))
        out[f"round{index}"] = {
            "inflight_direct_correct": correct,
            "inflight_direct_accuracy": correct / len(sample_ids),
            "parsed": parsed,
            "gain_of_blend_over_inflight_direct_samples": sum(record.blend.values()) - correct,
            "registered_m0_correct": sum(record.m0.values()),
            "scored_outcome_agrees_with_m0_samples": agrees_with_m0_score,
            "direct_answers_outside_train_intent_inventory": out_of_inventory,
            "wrong_answers_recoverable_by_field_swap": field_swap_recoverable,
        }
    return out


# ---------------------------------------------------------------------------
# Question 4 -- leakage and hygiene (cited, not re-derived)
# ---------------------------------------------------------------------------


def hygiene_checklist(*, repo_root: Path, rounds: Mapping[int, RoundRecord]) -> dict[str, object]:
    """Re-assert the pinned fields of the landed hygiene receipts.

    Deliberately a CITATION check, not a derivation: re-deriving
    train/devel/test disjointness would mean this row opening the very
    rosters the decontamination receipt exists to keep closed. What an
    audit can legitimately do is confirm the receipts exist, say what they
    are claimed to say, and are the ones the campaign actually names."""

    kb_receipt = json.loads((Path(repo_root) / KB_BUILD_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    dev100 = json.loads((Path(repo_root) / DEV100_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    split_identity = json.loads(
        (Path(repo_root) / SPLIT_IDENTITY_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    decontamination = kb_receipt["decontamination"]
    if decontamination["verdict"] != "clean":
        raise AuditError("knowledge-build receipt does not carry a clean decontamination verdict")
    counts = kb_receipt["coverage_report"]["counts"]
    if int(counts["train_intents"]) != EXPECTED_TRAIN_INTENTS:
        raise AuditError("KB receipt train_intents is not the expected 60")

    return {
        "decontamination": {
            "receipt": KB_BUILD_RECEIPT_RELPATH,
            "verdict": decontamination["verdict"],
            "checked_sample_count": decontamination["checked_sample_count"],
            "forbidden_roster_receipts": decontamination["forbidden_roster_receipts"],
            "snapshot_sha256": kb_receipt["snapshot_sha256"],
            "reads": "the knowledge snapshot is built from TRAIN utterances only "
            f"({counts['train_utterances']} of them) and was checked against the frozen "
            "devel/test identity roster plus every DEV/FINAL probe roster",
        },
        "split_identity": {
            "receipt": SPLIT_IDENTITY_RECEIPT_RELPATH,
            "note": split_identity["note"],
            "devel_count": split_identity["splits"]["devel"]["count"],
            "devel_identity_hash": split_identity["splits"]["devel"]["identity_hash"],
        },
        "final60_and_probe60_exclusion": {
            "receipt": DEV100_RECEIPT_RELPATH,
            "split_identity_hash": dev100["split_identity_hash"],
            "exclusions": {
                key: {
                    "excluded_utterance_count": block["excluded_utterance_count"],
                    "receipt": block["receipt"],
                }
                for key, block in dev100["exclusions"].items()
            },
            "nesting": dev100["nesting"],
        },
        "gold_opening_discipline": {
            "rule": "gold opens SCORING-SIDE ONLY, after all of a round's arms have sealed; "
            "devel gold moves between rounds, never into runtime",
            "source": PREREGISTRATION_RELPATH + " sections 3 and 6",
            "per_round_evidence": {
                str(index): {
                    "authority": record.report["authority"],
                    "split_role_in_runtime": "dev (QueryState.use_partition_role)",
                }
                for index, record in sorted(rounds.items())
            },
        },
        "confirmatory_tier_contamination": {
            "finding": "DEV-100 is an EXACT SUBSET of DEV-500 (the split receipt's own nesting "
            "block). A DEV-500 confirmatory reading therefore re-reads the 100 samples four "
            "rounds of knob and code selection were made against: 20% of the confirmatory "
            "denominator is already exposed",
            "receipt": DEV100_RECEIPT_RELPATH,
            "parent_tier": dev100["nesting"]["parent_tier"],
            "is_exact_subset_of_parent": dev100["nesting"]["is_exact_subset_of_parent"],
            "unexposed_remainder": 400,
            "remedy_a": "pre-register the DEV-500 read to publish the 400-sample unexposed "
            "remainder as the primary number and the full 500 as secondary",
            "remedy_b": "accept the 20% exposure explicitly and price it in the claim",
            "status": "OPEN -- neither remedy is registered as of this audit",
        },
        "dev_tier_framing": {
            "rule": "DEV-100 is the agent-space OPTIMIZATION tier. Its numbers are iteration "
            "numbers on data that has now been read four times; they are not a held-out claim "
            "and no promotion follows from them",
            "source": PREREGISTRATION_RELPATH + " sections 1 and 3 (owner ladder ruling 2.2)",
            "confirmatory_answer": "a one-shot DEV-500 reading, blocked until the campaign "
            "converges positive; FINAL60 and test stay unread",
        },
        "what_a_reviewer_may_conclude": [
            "The knowledge snapshot contains no devel, test, FINAL60 or DEV-tier utterance "
            "(cited receipt, clean verdict over 50,628 checked samples).",
            "The 100 scored utterances exclude FINAL60 and the historic probe-60 at UTTERANCE "
            "granularity, so the reserved tiers are untouched by this campaign.",
            "Gold never entered runtime; every arm's decisions were sealed before scoring.",
        ],
        "what_a_reviewer_may_not_conclude": [
            "That any DEV-100 number generalises. Four rounds of knob and code selection were "
            "made against these 100 samples; the split is exposed by construction.",
            "That the gain is a held-out effect size. Only a one-shot confirmatory tier can "
            "produce that, and none has been read.",
            "That decontamination has been re-verified here. It is CITED from a landed receipt; "
            "this row opened no roster.",
            "That a DEV-500 reading would be a clean held-out confirmation as currently framed: "
            "DEV-100 nests inside it, so 100 of its 500 samples are already exposed.",
        ],
    }


# ---------------------------------------------------------------------------
# Question 5 -- effect attribution
# ---------------------------------------------------------------------------


def attribution(
    *, rounds: Mapping[int, RoundRecord], channel: VarianceChannel, sample_ids: Sequence[str]
) -> dict[str, object]:
    """Split the round-to-round movement into mechanism and variance.

    A delta is attributable to the variance channel when the samples that
    produced it are ones whose direct decode changed bytes between the two
    rounds; it is attributable to the mechanism when the round's registered
    variable predicted it and the direct input was byte-unchanged."""

    indices = sorted(rounds)
    w2c_sets = {i: set(rounds[i].report["wrong_to_correct_sample_ids"]) for i in indices}
    c2w_sets = {i: set(rounds[i].report["correct_to_wrong_sample_ids"]) for i in indices}
    steps = []
    for previous, current in zip(indices, indices[1:]):
        gained = (w2c_sets[current] - w2c_sets[previous]) | (c2w_sets[previous] - c2w_sets[current])
        lost = (w2c_sets[previous] - w2c_sets[current]) | (c2w_sets[current] - c2w_sets[previous])
        moved = sorted(gained | lost)
        unstable = set(channel.per_round_disagree[current]) | set(channel.per_round_disagree[previous])
        steps.append(
            {
                "from_round": previous,
                "to_round": current,
                "delta_samples": rounds[current].gain - rounds[previous].gain,
                "newly_correct_sample_ids": sorted(gained),
                "newly_wrong_sample_ids": sorted(lost),
                "moved_samples_in_the_byte_variance_channel": sorted(set(moved) & unstable),
                "moved_samples_outside_the_variance_channel": sorted(set(moved) - unstable),
            }
        )
    stable_w2c = set.intersection(*w2c_sets.values())
    stable_c2w = set.intersection(*c2w_sets.values())
    return {
        "per_step": steps,
        "repairs_present_in_every_sealed_round": sorted(stable_w2c),
        "repairs_present_in_every_sealed_round_count": len(stable_w2c),
        "damage_present_in_every_sealed_round": sorted(stable_c2w),
        "damage_present_in_every_sealed_round_count": len(stable_c2w),
        "stable_core_gain_samples": len(stable_w2c) - len(stable_c2w),
        "stable_core_and_variance_channel_overlap": sorted(
            (stable_w2c | stable_c2w) & set(channel.unstable_union)
        ),
        "inert_knob_finding": {
            "source": DAMAGE_CHANNEL_RELPATH,
            "claim": "the rank weights, top_k and alpha are provably inert on this split "
            "(0 changed trajectories on exact replay), and tau never bound; rounds 1 and 2 "
            "therefore carried no live mechanism variable",
            "consequence": "the round-1 delta of 0 is a mechanism NULL, and the round-2 delta "
            "of +2 cannot be an alpha effect -- it is the variance channel",
        },
        "reading": "attribution is per-step and per-sample; no round's delta is asserted as "
        "mechanism unless its samples sit outside the byte-variance channel",
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _train_label_statistics(*, data_root: Path) -> tuple[frozenset[str], Mapping[str, int]]:
    """The TRAIN intent inventory and its utterance counts, from the pinned
    knowledge snapshot (identity-checked against the same content hash the
    sibling analysis pins).

    The counts are the snapshot's OWN per-value ``task_target`` tally, i.e.
    exactly the TRAIN label prior the campaign's ``prior_source = "train"``
    knob draws on -- so the prior-only baseline below is built from the
    same bytes the system under audit uses, not from a re-derivation."""

    from ..rails import kb_policy as kb
    from ..rails.knowledge import KnowledgeSnapshot

    snapshot_path = Path(data_root) / dc.SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    measured = snapshot.content_hash()
    if measured != dc.SNAPSHOT_SHA256:
        raise AuditError(f"knowledge snapshot hashes to {measured}, not the pinned identity")
    targets = frozenset(kb._label_identities(snapshot).values())
    if len(targets) != EXPECTED_TRAIN_INTENTS:
        raise AuditError(f"snapshot carries {len(targets)} label identities, expected 60")
    counts = Counter(
        str(value.task_target) for value in snapshot.values if value.task_target is not None
    )
    if set(counts) != set(targets):
        raise AuditError("snapshot value targets and label identities disagree")
    return targets, dict(counts)


def audit(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Every reviewer question, answered over sealed bytes."""

    guard = arm_offline_guard()
    sample_ids = load_dev100_ids(Path(repo_root))
    rounds = paired_rounds(repo_root=Path(repo_root), sample_ids=sample_ids)

    primary = max(rounds, key=lambda index: rounds[index].gain)
    if primary != EXPECTED_PRIMARY_ROUND:
        raise AuditError(
            f"best sealed round is {primary}, not the expected {EXPECTED_PRIMARY_ROUND}; "
            "the audit's framing must be revisited before its numbers are published"
        )

    gold_by_sample = dc._load_gold(
        data_root=Path(data_root), repo_root=Path(repo_root), sample_ids=set(sample_ids)
    )
    label_targets, train_intent_counts = _train_label_statistics(data_root=Path(data_root))
    gold_scenarios = frozenset(gold_by_sample[sid].scenario for sid in sample_ids)

    uncertainty = {}
    for index, record in sorted(rounds.items()):
        uncertainty[f"round{index}"] = {
            "m0_correct": sum(record.m0.values()),
            "blend_correct": sum(record.blend.values()),
            "gain_samples": record.gain,
            "bootstrap": bootstrap_gain(sample_ids=sample_ids, m0=record.m0, blend=record.blend),
            "mcnemar": mcnemar(
                len(record.report["wrong_to_correct_sample_ids"]),
                len(record.report["correct_to_wrong_sample_ids"]),
            ),
        }

    channel = variance_channel(rounds, sample_ids)
    floors = conservative_floors(
        sample_ids=sample_ids, rounds=rounds, primary=primary, channel=channel
    )

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW_ID,
        "tier": "iteration-tier adversarial read over exposed dev data; design input, not a verdict",
        "offline_guard": {
            "armed": True,
            "connect_attempts": guard.count,
            "attempted_targets": guard.targets,
            "note": "socket.socket.connect / connect_ex / socket.create_connection were replaced "
            "by raisers before any input was opened",
        },
        "sealed_rounds_audited": sorted(rounds),
        "primary_round": primary,
        "split": {
            "receipt": DEV100_RECEIPT_RELPATH,
            "n": len(sample_ids),
            "role": "dev",
        },
        "m0_arm_identity": {
            "source": rounds[0].m0_source,
            "caveat": "flown ONCE (round-0 attempt 1, zero-copy build); every later round reuses "
            "those responses, so the paired contrast spans a build and a concurrency change",
        },
        "q1_uncertainty": uncertainty,
        "q2_variance_channel": {
            "per_round_byte_disagreement_counts": {
                str(index): len(ids) for index, ids in sorted(channel.per_round_disagree.items())
            },
            "unstable_union_count": len(channel.unstable_union),
            "unstable_union_sample_ids": list(channel.unstable_union),
            "unstable_in_every_round_count": len(channel.unstable_intersection),
            "cross_round_flipped_sample_ids": list(channel.flipped),
            "unstable_and_flipped_sample_ids": list(channel.unstable_and_flipped),
            "floors": floors,
        },
        "q3_baseline_fairness": {
            "what_m0_contains": [
                "the full task contract in the system message (output schema, field names, the "
                "instruction to answer from the speech query alone)",
                "the original speech packet on the single contact -- no transcript-only query",
                "JSON-shaped constrained decoding, so parse failures are 0/100 in every round",
                "one frozen-core contact per sample, temperature-0 sampling settings",
            ],
            "what_m0_does_not_contain": [
                "the SLURP label inventory: the contract never enumerates the 60 legal "
                "(scenario, action) pairs, so the arm is free to invent a label",
                "any retrieved evidence, any in-context example, any prior over intents",
                "a second contact, so it cannot revise",
            ],
            "majority_class": majority_class_baseline(gold_by_sample, sample_ids),
            "per_scenario": per_scenario_profile(
                gold_by_sample=gold_by_sample,
                sample_ids=sample_ids,
                rounds=rounds,
                primary=primary,
            ),
            "field_profile": field_profile(rounds=rounds, sample_ids=sample_ids, primary=primary),
            "prior_only_baseline": prior_only_baseline(
                rounds=rounds,
                sample_ids=sample_ids,
                gold_by_sample=gold_by_sample,
                train_intent_counts=train_intent_counts,
                scenarios=gold_scenarios,
            ),
            "inflight_direct_comparator": inflight_direct_baseline(
                rounds=rounds,
                sample_ids=sample_ids,
                gold_by_sample=gold_by_sample,
                label_targets=label_targets,
            ),
            "e108_consistency": {
                "e108_k0m0_correct": E108_K0M0_CORRECT,
                "e108_n": E108_N,
                "e108_accuracy": E108_K0M0_CORRECT / E108_N,
                "dev100_m0_accuracy": sum(rounds[0].m0.values()) / len(sample_ids),
                "gap_pp": 100.0 * (E108_K0M0_CORRECT / E108_N - sum(rounds[0].m0.values()) / len(sample_ids)),
                "source": E108_SOURCE,
                "limitation": "NOT decomposable from sealed DEV-100 bytes. The two numbers differ "
                "in split side (train vs devel), selection rule (a discovery-split eligibility "
                "filter vs a scenario-stratified draw), serving stack (zero-copy np16 M-line vs "
                "the np8 campaign service) and prompt lineage. Attributing the gap needs a "
                "matched same-protocol train-side direct-decode control, which is roughly 100 "
                "contacts and is NOT authorised by this row",
                "what_the_sealed_data_does_show": "the per-scenario and per-channel M0 profile "
                "below, i.e. WHERE on DEV-100 the direct baseline loses",
            },
        },
        "q4_hygiene": hygiene_checklist(repo_root=Path(repo_root), rounds=rounds),
        "q5_attribution": attribution(rounds=rounds, channel=channel, sample_ids=sample_ids),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    result = audit(repo_root=args.repo_root, data_root=args.data_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
