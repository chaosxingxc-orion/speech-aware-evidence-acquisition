"""SCOREBOARD v5 -- the machine check that every number on the two-axis
scoreboard was read out of the receipt that produced it.

Row ``SAEA-SN-MF-SCOREBOARD-V5`` (model-free-check), registered in
``docs/exposure-ledger.md`` BEFORE this module ran.

WHY THIS EXISTS. ``docs/readiness/2026-08-19-scheme-scoreboard.md`` is the
study's living scoreboard. Version 4 was a prose consistency ledger: one
accuracy-shaped number per mechanism, no delivery rate, no per-row provenance,
and -- because a scoreboard is exactly the document in which a number drifts --
several figures restated from other documents' prose rather than re-read from
the JSON a computation wrote. Version 5 replaces it with one row per landed
cell, two axes that are never merged, delivery beside every where-delivered
figure, and a provenance key on every row. This module is what makes that last
promise a check rather than a habit: every quantity the scoreboard carries is
declared here against the receipt field it came from, and :func:`run` refuses to
return unless all of them match.

WHAT IT DOES NOT DO. It computes no new experimental quantity, opens no sealed
run directory, no attempt store and no split roster, and reads no gold label.
Every input is a file already committed to this repository. It therefore proves
FAITHFULNESS -- that the scoreboard says what the receipts say -- and nothing
about whether the receipts are right, which is each landed row's own business.

THE FOUR CHECKS, in the order :func:`run` performs them:

1. :func:`arm_offline_guard` (imported from :mod:`.dev100_reviewer_audit`, not
   reimplemented) is armed BEFORE the first input is opened, and its attempt
   counter is published. A model-free row's whole claim is that it contacts
   nothing; the process enforces it rather than asserting it.
2. :func:`verify_artifacts` re-hashes every cited receipt AND every cited
   document with SHA-256 against the digest the scoreboard's register quotes. A
   digest mismatch stops the run: a number verified against the wrong bytes is
   not verified.
3. :func:`verify_claims` walks each declared JSON path and compares -- exactly
   for ints, bools and strings, to :data:`FLOAT_TOLERANCE` for floats -- and
   :func:`verify_substring_claims` does the same for figures a receipt publishes
   only inside a clause-detail string.
4. :func:`verify_document_claims` asserts, verbatim, the sentences that carry
   the handful of quantities whose own computation artifact lives OUTSIDE Git
   (under ``SPEECHRL_DATA_DIR``) and therefore cannot be re-read here. Those
   rows are marked provenance tier **D** on the scoreboard and are listed in its
   "could not verify" section, so a document-pinned figure is never mistaken for
   a receipt-pinned one.

TWO PROVENANCE TIERS, KEPT APART ON PURPOSE. Tier **R** is a receipt: path,
SHA-256, and the JSON field the number lives in. Tier **D** is a landed
document: path, SHA-256, and the exact sentence asserted here. Tier D exists
only for the speech-native EFFECT-C108 line, the external-controller
rejections, the E-C projection, the K-WIDEN K2 stopping ruling and the
43-gate split of the gate audit -- five places where the underlying artifact is
either outside Git or is itself the document. Everything else is tier R.

FAIL-CLOSED. Every mismatch raises :class:`ScoreboardVerificationError`. A
verification module that returns "3 of 400 failed" invites the reader to decide
which three did not matter, which is precisely the judgement it exists to
remove.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .dev100_reviewer_audit import arm_offline_guard
from .stage2a_synthesis_verification import (
    Claim,
    Receipt,
    _matches,
    _walk,
    crlf_defect,
    sha256_of,
)

SCHEMA = "saea-scoreboard-v5-verification-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-SCOREBOARD-V5"
SCOREBOARD_RELPATH = "docs/readiness/2026-08-19-scheme-scoreboard.md"
FLOAT_TOLERANCE = 5e-5

_CHECKS = "docs/checks/speech-aware-evidence-acquisition"
_READY = "docs/readiness"


class ScoreboardVerificationError(RuntimeError):
    """Raised when a digest or a carried number does not match. Never raised for
    a legitimate data shape -- a scoreboard check that tolerates a mismatch is
    worth nothing."""


# ---------------------------------------------------------------------------
# The register: every artifact the scoreboard cites, pinned by digest
# ---------------------------------------------------------------------------

#: Tier R -- receipts. The key is the scoreboard's citation key.
RECEIPTS: tuple[Receipt, ...] = (
    Receipt(
        "R-PSLU",
        f"{_CHECKS}/2026-08-18-pslu-read/verdict.json",
        "7bedd461e4443932bda01444af84cac65f700c45d79e7d1cc012fd22ce1a287f",
        "P-SLU elicitation-bank supply ladder on SLURP-60",
    ),
    Receipt(
        "R-PSLU2",
        f"{_CHECKS}/2026-08-18-pslu-s2-read/verdict.json",
        "a29e5ac1151711f8b56a41609187b65d018753369ac680cf402a2ad2fedc2fe8",
        "P-SLU stage 2: KNOWLEDGE-BEYOND-FORMAT + SELF-SCOPING-WORKS",
    ),
    Receipt(
        "R-PPHON",
        f"{_CHECKS}/2026-08-18-pphon-decomp/verdict.json",
        "0654ba1fbf242c789e6fdc6211f6de501a1a36e747fa79d8e0e466358c1f32ec",
        "P-PHON failure-class decomposition on both carriers",
    ),
    Receipt(
        "R-A2T-A0",
        f"{_CHECKS}/2026-08-18-pa2t-a0-read/verdict.json",
        "8b0e96ca6eac50b75eb07d6f1d05b245c43cc845e877b8f1dd185e4665c7ccff",
        "Audio2Tool A0 baseline anchor on the parent 400-item split",
    ),
    Receipt(
        "R-A2T-S2",
        f"{_CHECKS}/2026-08-18-a2t-s2-read/verdict.json",
        "2377f09ac1138c2648e18fd6ac040465f5d4d11967f4f6479b39ec53bbffa8bf",
        "Audio2Tool stage 2: the value-copy trap",
    ),
    Receipt(
        "R-A2T-S2B",
        f"{_CHECKS}/2026-08-18-a2t-s2b-read/verdict.json",
        "ad49af4c73e281b5094aecb917bf59b4b13cf3c7472b54e45947f895a2a86363",
        "Audio2Tool stage 2b: CONFIRMED-CUT / INCONCLUSIVE-B",
    ),
    Receipt(
        "R-A2T-S2C",
        f"{_CHECKS}/2026-08-18-a2t-s2c-read/verdict.json",
        "904b63c1465371f6dcc5c6093cc39153001a32974d06fc83fab357c7a7f75fdc",
        "Audio2Tool stage 2c: ROBUST / CHANNEL-REOPENED",
    ),
    Receipt(
        "R-A2T-LOSS",
        f"{_CHECKS}/2026-08-18-a2t-loss-decomp/verdict.json",
        "04bb9dc841bb0ce95efdd9223cee72e8cf901929d114d3cb19c9c3294b3ccb07",
        "Audio2Tool B2 loss decomposition",
    ),
    Receipt(
        "R-A2T-ABST",
        f"{_CHECKS}/2026-08-19-a2t-abst-read/verdict.json",
        "23eaafa9a0d6fe958722d7c0d752a866a70b7bb3f91171ae68e23ae7cc50ec49",
        "Audio2Tool abstention asymmetry probe",
    ),
    Receipt(
        "R-A2T-POP",
        f"{_CHECKS}/2026-08-19-a2t-pop-read/verdict.json",
        "27457acaab8f193a4783cf166fdd8320dc0bd7204b038e35603074c5fbb9b73d",
        "Audio2Tool blind-replacement regression probe",
    ),
    Receipt(
        "R-PFEW",
        f"{_CHECKS}/2026-08-19-pfew-read/verdict.json",
        "339ad933a68e97115601d8e2751e77e37b0e1643693068b6f8d1eb427878057b",
        "P-FEW routing few-shot gain and bias",
    ),
    Receipt(
        "R-PTRAP",
        f"{_CHECKS}/2026-08-19-ptrap-read/verdict.json",
        "41241cc197194fdde5a2a4061144c42d6a744f9fa41b1a15546689f5778635ca",
        "P-TRAP self-percept resonance",
    ),
    Receipt(
        "R-PKEY2",
        f"{_CHECKS}/2026-08-19-pkey2-read/verdict.json",
        "429d3159fb10c1b6f0cda8567abc1a7065e2bcef0db3901d31ebe0500cdaedff",
        "P-KEY-2 audio-versus-text supply interaction",
    ),
    Receipt(
        "R-PEMB1",
        f"{_CHECKS}/2026-08-19-pemb1-read/verdict.json",
        "a2957d5637bb15f2502ee064df7f7e1e5477c31b5fc780c875cafac14ccc1992",
        "P-EMB-1 generation-core pooled-state routing (SLURP scenario)",
    ),
    Receipt(
        "R-PEMB2",
        f"{_CHECKS}/2026-08-19-pemb2-read/verdict.json",
        "3ed669178ab1ff685be136892fcaa4039c691b0a395caaf575582c127c51f76f",
        "P-EMB-2 generation-core pooled-state routing (A2T tool)",
    ),
    Receipt(
        "R-PEMB3L",
        f"{_CHECKS}/2026-08-20-pemb3l-read/verdict.json",
        "b4644d0a7c5e6db4b1415c95eea288d82872d00ec21ed5b9a5bdd0c5edde1171",
        "P-EMB-3L local construction sweep",
    ),
    Receipt(
        "R-PEMB3M",
        f"{_CHECKS}/2026-08-20-pemb3m-read/verdict.json",
        "17c3a9398003a94724e9c8a6d162407ad0abc1896c7fff5e718f97a3ee1409ce",
        "P-EMB-3M dedicated omni-embedding model plus the cascade arm",
    ),
    Receipt(
        "R-PEMB4R",
        f"{_CHECKS}/2026-08-21-pemb4r-read/verdict.json",
        "f1220d7b3518a80ccbd98e0c74afd249c9ee7cb1cbae39d2a2d5a0eda2a81691",
        "P-EMB-4R register-aligned utterance-to-utterance kNN",
    ),
    Receipt(
        "R-PCORRF",
        f"{_CHECKS}/2026-08-20-pcorrf-read/verdict.json",
        "e7ee3fda16c7dbce02559826da49b0259bb1ad27b7f0775cbfb61d8b85fc5e0c",
        "P-CORR-F percept-keyed corrective supply",
    ),
    Receipt(
        "R-E108",
        f"{_CHECKS}/2026-08-23-e108-zcopy-read/read-verdict.json",
        "e0154a4e26a839abb7a44584714442415724dd93f95996e1111b15c84a82504c",
        "E108 M11 adaptive evidence-gap read (train-only discovery split)",
    ),
    Receipt(
        "R-R0",
        f"{_CHECKS}/2026-08-24-dev100-round0/round0-report.json",
        "26f05488bb7031d1ae85710faffd2b414644729af1adc476a1002a55612fb0b6",
        "DEV-100 round 0",
    ),
    Receipt(
        "R-R1",
        f"{_CHECKS}/2026-08-24-dev100-round1/round1-report.json",
        "559559d239103f2905d8e86e643741990ceb1023070095d1d797d8e66de4cd8d",
        "DEV-100 round 1",
    ),
    Receipt(
        "R-R2",
        f"{_CHECKS}/2026-08-24-dev100-round2/round2-report.json",
        "c69cf3fef49a3bafb86818383953c9c0e37880518750073c6ba857f47e7b00f6",
        "DEV-100 round 2",
    ),
    Receipt(
        "R-R3",
        f"{_CHECKS}/2026-08-24-dev100-round3/round3-report.json",
        "ac5a884febb43ede69b6401deb6e1e67e1e543c8e8082e50ad552b8358c47965",
        "DEV-100 round 3",
    ),
    Receipt(
        "R-R4",
        f"{_CHECKS}/2026-08-24-dev100-round4/round4-report.json",
        "42fa837582f5f9e129348d4ecc8324c56db62a754728048126c319666a997f1e",
        "DEV-100 round 4 (the frozen cell)",
    ),
    Receipt(
        "R-R5",
        f"{_CHECKS}/2026-08-24-dev100-round5/round5-report.json",
        "482d33bde5fe4ff7a522f8ca5e2b4fd7f02f3a87a6113f682c6218f3256e4d71",
        "DEV-100 round 5 (the exact replication)",
    ),
    Receipt(
        "R-KWIDEN",
        f"{_CHECKS}/2026-08-24-dev100-kwiden-k1/kwiden-k1-report.json",
        "66a340da402f97f6495f87a6a0e3abfa312b3b7771652bd3087407eafee98f9f",
        "K-WIDEN K1 (retrieval width 5 to 8) plus its offline width-5 replay",
    ),
    Receipt(
        "R-A4",
        f"{_CHECKS}/2026-08-25-dev100-retain-override/retain-override-report.json",
        "0615275e395e983c54a694a9641c06de7d1c9a9b5aa87801d33edd002d9ef92f",
        "DEV-100 A4 retain-override dispatch variant",
    ),
    Receipt(
        "R-DEV500",
        f"{_CHECKS}/2026-08-24-dev500-confirmatory-read/read-verdict.json",
        "b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3",
        "the DEV-500 confirmatory one-shot read (four sealed arms)",
    ),
    Receipt(
        "R-LOCK",
        f"{_CHECKS}/2026-08-25-dev1000-lock-read/read-verdict.json",
        "2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581",
        "the one-shot DEV-1000 baseline-lock read (d9fef537)",
    ),
    Receipt(
        "R-G1",
        f"{_CHECKS}/2026-08-25-a2t-g1/g1-read-attempt4.json",
        "cb5e56584a6d572f7b41b39542201ddb1b361755042eac66c3a70c55fd086f89",
        "the Audio2Tool G1 attempt-4 paired read",
    ),
    Receipt(
        "R-SWEEP",
        f"{_CHECKS}/2026-08-25-a2t-admission-scale-sweep/sweep-report.json",
        "88f606fe89eb42e675bdd4832a31b028638613eba71d712d3d4ee6cf7aa74d66",
        "the admission-scale defect audit and its fix verification (repair 1341c2db)",
    ),
    Receipt(
        "R-GOLD",
        f"{_CHECKS}/2026-08-25-a2t-gold-absence/diagnosis-report.json",
        "64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14",
        "the Audio2Tool gold-absence diagnosis",
    ),
    Receipt(
        "R-ORACLE",
        f"{_CHECKS}/2026-08-25-a2t-oracle-query-bound/oracle-query-bound-report.json",
        "b564362b64bb41df4d9055518bcd0cd88753e2796b3583ed0b95f626a2ece723",
        "the Audio2Tool oracle-query upper bound (post-correction, 274ce62a)",
    ),
    Receipt(
        "R-XC",
        f"{_CHECKS}/2026-08-25-cross-carrier-decomposition/decomposition-report.json",
        "9a1903b35f3eff42dc7bf4caee5ba95235af855e9e0fc087ba8d9d7c0d8be5a1",
        "the cross-carrier ceiling decomposition",
    ),
    Receipt(
        "R-MVE",
        f"{_CHECKS}/2026-08-25-matching-vs-extraction/read-report.json",
        "378757b5bc3292395cbdc82a19c936912edaf61725cede012bfad6b77ffd6523",
        "the matching-versus-extraction read (population two-axis table; its CONDITIONED verdict is superseded)",
    ),
    Receipt(
        "R-ECD",
        f"{_CHECKS}/2026-08-25-extraction-conditioned-on-dispatch/read-report.json",
        "7662fbc381e6994f3c71422154a0facfc86c0e99b656cf91670577036a337525",
        "the extraction-conditioned-on-dispatch read (the supersession, 6c6ec719)",
    ),
    Receipt(
        "R-DEGEN",
        f"{_CHECKS}/2026-08-25-query-key-degeneracy/degeneracy-report.json",
        "a1a40999dfddae7642cdc3eaa6763a8fcffe1874e5488210e41618c219a6aeae",
        "the cross-carrier query-key degeneracy measurement",
    ),
    Receipt(
        "R-FIELD",
        f"{_CHECKS}/2026-08-25-field-level-supply-accounting/accounting-report.json",
        "ca973be873318deb6029f183045ac4074653dd1b5943c9113fb78d40766de4c6",
        "the field-level supply accounting (the delivery rates)",
    ),
    Receipt(
        "R-K1GATE",
        f"{_CHECKS}/2026-08-25-k1-hybrid-ranking-gate/gate-report.json",
        "252d53f30baed2ee36a725b0df9c5a5807438713c755845c8b8376b76ff5556f",
        "the K1 hybrid lexical-plus-dense ranking gate",
    ),
    Receipt(
        "R-FUSION",
        f"{_CHECKS}/2026-08-25-fusion-form-gate/gate-report.json",
        "568a78eeebd1519fcd7bee9d0c240469ffd6cb2b640fd4d4931ea22007a69647",
        "the fusion-form offline gate (four candidate scoring forms)",
    ),
    Receipt(
        "R-GATEAUDIT",
        f"{_CHECKS}/2026-08-25-gate-audit/gate-audit-report.json",
        "c850ace8e025071658201c3bc57f39741b8282f230fc0614f9dae9957516f8f3",
        "the can-it-fail gate audit",
    ),
    Receipt(
        "R-INTENT",
        f"{_CHECKS}/2026-08-25-slurp-intent-coverage/intent-coverage-report.json",
        "de1e9778795fc6b0d02445a53c45dedf060f483978e542e0f354003545d52750",
        "the SLURP intent-coverage check",
    ),
    Receipt(
        "R-PRIOR",
        f"{_CHECKS}/2026-08-25-prior-score-semantics-repair/repair-report.json",
        "041de6c0868ca4324545d2a423c098d5d96218ca9443fff2ca527aa053895c05",
        "the prior-score semantics repair",
    ),
    Receipt(
        "R-FACET",
        f"{_CHECKS}/2026-08-25-content-facet-target-audit/audit-report.json",
        "ff4311fab3b61719dc5d59b6e30a2eeada899b3d34ba7f7e20b5ac891886dcd5",
        "the content_facet_target correctness audit",
    ),
    Receipt(
        "R-AUDIT",
        f"{_CHECKS}/2026-08-24-dev100-reviewer-audit/reviewer-audit.json",
        "e039b5818fa23ef5568f4c6e505ea6d66e0fbb8493121f0c606994695f3bcc89",
        "the DEV-100 reviewer-perspective statistical audit",
    ),
    Receipt(
        "R-ALPHA",
        f"{_CHECKS}/2026-08-25-alpha-trade-sizing/alpha-trade-sizing-report.json",
        "4df34154a86fc7bb2f683b6f2a692819c0e4283228ccdc0bf1c796081812e2ab",
        "the alpha-trade decision sizing for open owner decision D1 (bcea7c95)",
    ),
    Receipt(
        "R-SYNTH",
        f"{_CHECKS}/2026-08-25-stage2a-synthesis/verification-report.json",
        "561a6c020d1c58a77097e88f30e2e7d597730fa570dbeb2e15200e321d45d9a0",
        "the Stage-2A matured synthesis verification receipt",
    ),
)

#: Tier D -- landed documents whose own computation artifact is outside Git, or
#: which ARE the artifact. Never confused with tier R on the scoreboard.
DOCUMENTS: tuple[Receipt, ...] = (
    Receipt(
        "D-SN",
        f"{_READY}/2026-08-21-speech-native-agent-loop-training-free-rl-plan.md",
        "e7803bf07300cdcf4976b5e9404d067bcf505166d79c7819c2dc85b574fb45ba",
        "the speech-native agent-loop plan: the EFFECT-C108 read and the M5-M9 controller rejections",
    ),
    Receipt(
        "D-E108",
        f"{_READY}/2026-08-23-e108-verdict.md",
        "1d36c557a9e780569bd8e7cbb0737c45f2ffd303daad924c795ed40286666788",
        "the E108 verdict: the information-support gate outcome",
    ),
    Receipt(
        "D-EC",
        f"{_READY}/2026-08-25-ec-and-retain-override-projections.md",
        "6d50d2ea164567e01c0cb6c5f999e10270453577b617f20d960a7a0fdb580462",
        "the E-C and retain-override model-free projections",
    ),
    Receipt(
        "D-KWIDEN",
        f"{_READY}/2026-08-24-kwiden-and-next-experiments-queue.md",
        "e4ae3f48a128bdf67811d1a67cb436b988ed83de4bf47bc1860f98c07de2285e",
        "the next-experiment queue: the K2 stopping ruling and the E-A pre-analysis outcome",
    ),
    # 2026-08-26 repin (CI-first-green repair, cause 3). The previous pin,
    # da59b6e1..., was taken from this file's CRLF WORKING-TREE bytes on the
    # Windows checkout (345 CRLF line endings, 32790 bytes). The Git blob is
    # LF (32445 bytes) and hashes to 6ab241b1..., so the old pin could never be
    # reproduced by any clean checkout -- CI hashed the blob bytes and refused.
    # Umbrella CLAUDE.md is the authority: "Git blob bytes are the evidence hash
    # authority ... not CRLF working-tree bytes". The working-tree file was
    # renormalized to LF (a no-op against the blob) and the pin now names the
    # blob digest; `_crlf_defect` below makes the defect class fail-closed.
    Receipt(
        "D-GATES",
        f"{_READY}/2026-08-25-gate-audit-can-it-fail.md",
        "6ab241b18a924122a5c3a64712bfde7fcc23a6bc2075f7ac0c281ca83d822efa",
        "the gate audit document: the 43-gate split (the receipt publishes the mutation tally instead)",
    ),
)

ARTIFACTS_BY_KEY: Mapping[str, Receipt] = {
    r.key: r for r in (*RECEIPTS, *DOCUMENTS)
}


def _c(claim_id: str, receipt: str, path: str, expected: Any) -> Claim:
    return Claim(claim_id, receipt, path, expected)


@dataclass(frozen=True)
class SubstringClaim:
    """A figure a receipt publishes only inside a clause-detail string."""

    claim_id: str
    receipt: str
    path: str
    substring: str


@dataclass(frozen=True)
class DocumentClaim:
    """A sentence a landed document must carry verbatim (provenance tier D)."""

    claim_id: str
    document: str
    substring: str


# ---------------------------------------------------------------------------
# Every number the scoreboard carries, bound to the field it came from
# ---------------------------------------------------------------------------

CLAIMS: tuple[Claim, ...] = (
    # -- Filling tier: the elicitation-bank supply ladder (SLURP-60) ---------
    _c("pslu.a0_slu_f1", "R-PSLU", "aggregates/A0/slu_f1/f1", 0.1740786454061426),
    _c("pslu.a1_slu_f1", "R-PSLU", "aggregates/A1/slu_f1/f1", 0.63401186634837),
    _c("pslu.a2_slu_f1", "R-PSLU", "aggregates/A2/slu_f1/f1", 0.46863681617556163),
    _c("pslu.a3_slu_f1", "R-PSLU", "aggregates/A3/slu_f1/f1", 0.5961280580450439),
    _c("pslu.a0_slot_f1", "R-PSLU", "aggregates/A0/slot_f1_exact/f1", 0.043478260869565216),
    _c("pslu.a1_slot_f1", "R-PSLU", "aggregates/A1/slot_f1_exact/f1", 0.5245901639344263),
    _c("pslu.a3_slot_f1", "R-PSLU", "aggregates/A3/slot_f1_exact/f1", 0.5),
    _c("pslu.a1_induced", "R-PSLU", "aggregates/A1/induced_substitution_count", 1),
    _c("pslu2.overall_qa", "R-PSLU2", "qa/overall", "KNOWLEDGE-BEYOND-FORMAT"),
    _c("pslu2.f1_slu_f1", "R-PSLU2", "qa/f1_slu_f1", 0.13561683312189396),
    _c("pslu2.gap", "R-PSLU2", "qa/gap_a3_minus_f1", 0.460483166878106),
    _c("pslu2.overall_qb", "R-PSLU2", "qb/overall", "SELF-SCOPING-WORKS"),
    _c("pslu2.non_fallback", "R-PSLU2", "qb/non_fallback_count", 60),
    _c("pslu2.calls", "R-PSLU2", "qb/n_calls", 60),
    _c("pslu2.gain_vs_a0", "R-PSLU2", "qb/gain_vs_a0", 0.4352242545024063),
    # -- P-PHON failure-class decomposition ---------------------------------
    _c("pphon.baseline_failures", "R-PPHON", "slurp/a1r/table/total_baseline_failures", 85),
    _c("pphon.converted", "R-PPHON", "slurp/a1r/table/total_converted", 41),
    _c("pphon.rate", "R-PPHON", "slurp/a1r/table/conversion_rate_overall", 0.4823529411764706),
    _c("pphon.missing_n", "R-PPHON", "slurp/a1r/table/classes/MISSING/baseline_failures", 71),
    _c("pphon.missing_converted", "R-PPHON", "slurp/a1r/table/classes/MISSING/converted", 35),
    _c("pphon.a2t_baseline_failures", "R-PPHON", "a2t/baseline_total_failures", 56),
    # -- Audio2Tool A0 anchor (both axes on one carrier) --------------------
    _c("a0.n", "R-A2T-A0", "overall/n_samples", 400),
    _c("a0.tool_accuracy", "R-A2T-A0", "overall/tool_accuracy", 0.5425),
    _c("a0.exact_match", "R-A2T-A0", "overall/exact_match", 0.2425),
    _c("a0.empty_rate", "R-A2T-A0", "overall/empty_tool_call_rate", 0.1025),
    _c("a0.gap", "R-A2T-A0", "overall/gap", 0.3),
    # -- Audio2Tool stages 2 / 2b / 2c and the loss decomposition -----------
    _c("s2.copy_trap", "R-A2T-S2", "branch_verdict/copy_trap", True),
    _c("s2b.qa_overall", "R-A2T-S2B", "qa_verdict/overall", "CONFIRMED-CUT"),
    _c("s2b.qb_overall", "R-A2T-S2B", "qb_verdict/overall", "INCONCLUSIVE-B"),
    _c("s2c.form_overall", "R-A2T-S2C", "form_robustness_verdict/overall", "ROBUST"),
    _c("s2c.augment_overall", "R-A2T-S2C", "deploy_augment_verdict/overall", "CHANNEL-REOPENED"),
    _c("loss.dragged", "R-A2T-LOSS", "b2_verdict/dragged_count", 3),
    _c("loss.drift_confirmed", "R-A2T-LOSS", "b2_verdict/drift_confirmed", True),
    _c("loss.b2_empty", "R-A2T-LOSS", "b2_verdict/b2_shape/EMPTY", 6),
    _c("loss.b2_parsefail", "R-A2T-LOSS", "b2_verdict/b2_shape/PARSE-FAIL", 6),
    # -- Audio2Tool abstention and blind-replacement regression -------------
    _c("abst.overall", "R-A2T-ABST", "verdict/overall", "ASYMMETRY-REFUTED"),
    _c("pop.overall", "R-A2T-POP", "verdict/overall", "REGRESSION-COSTLY"),
    _c("pop.delta_reg", "R-A2T-POP", "verdict/delta_reg", 36),
    _c("pop.ci_low", "R-A2T-POP", "verdict/bootstrap/ci_low", 28.0),
    _c("pop.ci_high", "R-A2T-POP", "verdict/bootstrap/ci_high", 44.0),
    # -- Routing tier: few-shot, resonance, key ------------------------------
    _c("pfew.overall", "R-PFEW", "verdict/overall", "INCONCLUSIVE-FEW"),
    _c("pfew.fs_none", "R-PFEW", "accuracy/fs_none", 0.8166666666666667),
    _c("pfew.fs_bal", "R-PFEW", "accuracy/fs_bal", 0.8166666666666667),
    _c("pfew.fs_skew", "R-PFEW", "accuracy/fs_skew", 0.75),
    _c("pfew.capture_count", "R-PFEW", "capture/capture_count", 2),
    _c("pfew.capture_denominator", "R-PFEW", "capture/n_denominator", 59),
    _c("ptrap.overall", "R-PTRAP", "verdict/overall", "ACOUSTIC-MEDIATED"),
    _c("ptrap.v1_capture", "R-PTRAP", "capture/v1_capture_count", 29),
    _c("ptrap.v2_capture", "R-PTRAP", "capture/v2_capture_count", 0),
    _c("ptrap.usable", "R-PTRAP", "n_usable", 32),
    _c("pkey2.overall", "R-PKEY2", "overall", "INCONCLUSIVE-KEY"),
    _c("pkey2.interaction", "R-PKEY2", "interaction/interaction", 0.046321913491409905),
    _c("pkey2.delta_aud", "R-PKEY2", "interaction/delta_aud", 0.4397452889197778),
    _c("pkey2.delta_txt", "R-PKEY2", "interaction/delta_txt", 0.3934233754283679),
    _c("pkey2.t0_wer", "R-PKEY2", "t0_wer/macro_wer", 0.5359343434343434),
    # -- Embedding routing: the four refutations and the cascade ------------
    _c("pemb1.verdict", "R-PEMB1", "verdict", "EMB-WEAK"),
    _c("pemb1.accuracy", "R-PEMB1", "accuracy", 0.05),
    _c("pemb1.n_correct", "R-PEMB1", "n_correct", 3),
    _c("pemb1.n_samples", "R-PEMB1", "n_samples", 60),
    _c("pemb2.verdict", "R-PEMB2", "verdict", "EMB-CLOSED"),
    _c("pemb2.top1_183", "R-PEMB2", "top1_accuracy_183", 0.01092896174863388),
    _c("pemb2.top5_183", "R-PEMB2", "top5_accuracy_183", 0.0273224043715847),
    _c("pemb2.recoveries", "R-PEMB2", "recoveries_183", 2),
    _c("pemb2.n_samples", "R-PEMB2", "n_samples", 400),
    _c("pemb3l.verdict", "R-PEMB3L", "verdict", "LOCAL-EXHAUSTED"),
    _c("pemb3l.l1", "R-PEMB3L", "arms/l1-last-bare/accuracy", 0.05),
    _c("pemb3l.l3", "R-PEMB3L", "l3_accuracy", 0.05),
    _c("pemb3m.overall", "R-PEMB3M", "verdict/overall", "EMB-WEAK + CASCADE-ROUTES"),
    _c("pemb3m.m1_accuracy", "R-PEMB3M", "arms/m1-lco-primary/accuracy", 0.05),
    _c("pemb3m.m1_correct", "R-PEMB3M", "arms/m1-lco-primary/n_correct", 3),
    _c("pemb3m.m2_accuracy", "R-PEMB3M", "arms/m2-glap-control/accuracy", 0.13333333333333333),
    _c("pemb3m.m2_correct", "R-PEMB3M", "arms/m2-glap-control/n_correct", 8),
    _c("pemb3m.m4_accuracy", "R-PEMB3M", "arms/m4-cascade/accuracy", 0.75),
    _c("pemb3m.m4_correct", "R-PEMB3M", "arms/m4-cascade/n_correct", 45),
    _c("pemb3m.control_anomaly", "R-PEMB3M", "verdict/control_anomaly", False),
    _c("pemb4r.overall", "R-PEMB4R", "verdict/overall", "REGISTER-RESCUE(a-glap) + KNN-BEATS-LABEL-MATCH"),
    _c("pemb4r.glap_k5", "R-PEMB4R", "arms/a-glap/vote_accuracy_k5", 0.31666666666666665),
    _c("pemb4r.glap_recall5", "R-PEMB4R", "arms/a-glap/recall_at_5", 0.5666666666666667),
    _c("pemb4r.lco3_k5", "R-PEMB4R", "arms/a-lco3/vote_accuracy_k5", 0.15),
    _c("pemb4r.lco7_k5", "R-PEMB4R", "arms/a-lco7/vote_accuracy_k5", 0.11666666666666667),
    _c("pemb4r.tqw_k5", "R-PEMB4R", "arms/t-qw/vote_accuracy_k5", 0.8666666666666667),
    _c("pemb4r.tqw_recall5", "R-PEMB4R", "arms/t-qw/recall_at_5", 0.9333333333333333),
    _c("pemb4r.audio_content_absent", "R-PEMB4R", "verdict/audio_content_absent", False),
    _c("pemb4r.chance", "R-PEMB4R", "chance_accuracy", 0.0556),
    _c("pemb4r.c_decode", "R-PEMB4R", "verdict/c_decode_status", "CANCELED-BY-OWNER-2026-08-21"),
    # -- P-CORR-F percept-keyed corrective supply ---------------------------
    _c("pcorrf.delta1", "R-PCORRF", "q1/delta1", 0.05082725613893746),
    _c("pcorrf.ci_low", "R-PCORRF", "q1/bootstrap/ci_low", 0.009823717551403526),
    _c("pcorrf.ci_high", "R-PCORRF", "q1/bootstrap/ci_high", 0.0967846789699773),
    _c("pcorrf.w1_slu_f1", "R-PCORRF", "guardrails/W1/slu_f1", 0.6588247118494402),
    _c("pcorrf.w2_slu_f1", "R-PCORRF", "guardrails/W2/slu_f1", 0.6079974557105028),
    _c("pcorrf.w3_slu_f1", "R-PCORRF", "guardrails/W3/slu_f1", 0.43360054595631714),
    _c("pcorrf.w4_slu_f1", "R-PCORRF", "guardrails/W4/slu_f1", 0.6366395673862216),
    _c("pcorrf.w1_slot_f1", "R-PCORRF", "guardrails/W1/slot_f1_exact", 0.6031746031746033),
    _c("pcorrf.w2_slot_f1", "R-PCORRF", "guardrails/W2/slot_f1_exact", 0.5208333333333333),
    _c("pcorrf.w1_recovery", "R-PCORRF", "dual_measurement/W1/recovery_total", 53),
    _c("pcorrf.w1_contamination", "R-PCORRF", "dual_measurement/W1/contamination_total", 12),
    _c("pcorrf.w2_recovery", "R-PCORRF", "dual_measurement/W2/recovery_total", 46),
    _c("pcorrf.w2_contamination", "R-PCORRF", "dual_measurement/W2/contamination_total", 0),
    _c("pcorrf.q2_delta2", "R-PCORRF", "q2/delta2", -0.16252751208872673),
    _c("pcorrf.dose_insufficient", "R-PCORRF", "q2/dose_insufficient/verdict", "met"),
    _c("pcorrf.parse_w1", "R-PCORRF", "guardrails/W1/parse_rate", 1.0),
    _c("pcorrf.copy_w1", "R-PCORRF", "guardrails/W1/copy_rate", 0.0),
    # -- E108 (the last external-controller generation) ---------------------
    _c("e108.correct", "R-E108", "aggregates/0/correct", 92),
    _c("e108.accuracy", "R-E108", "aggregates/0/accuracy", 0.8518518518518519),
    _c(
        "e108.action_variable",
        "R-E108",
        "aggregates/0/agent_loop_metrics/action_variable_query_count",
        14,
    ),
    _c(
        "e108.boundary_queries",
        "R-E108",
        "aggregates/0/agent_loop_metrics/adaptive_boundary_query_count",
        7,
    ),
    _c(
        "e108.boundary_helpful",
        "R-E108",
        "aggregates/0/agent_loop_metrics/information_flow/"
        "boundary_supply_transition/helpful_transition_count",
        4,
    ),
    _c(
        "e108.boundary_harmful",
        "R-E108",
        "aggregates/0/agent_loop_metrics/information_flow/"
        "boundary_supply_transition/harmful_transition_count",
        0,
    ),
    _c(
        "e108.final_minus_primary",
        "R-E108",
        "aggregates/0/agent_loop_metrics/final_minus_primary_correct",
        0,
    ),
    # -- The DEV-100 ladder --------------------------------------------------
    _c("r0.m0", "R-R0", "arms/M0/correct_count", 48),
    _c("r0.blend", "R-R0", "arms/BLEND/correct_count", 63),
    _c("r0.dispatched", "R-R0", "blend_decisions/evidence_contact_dispatched_samples", 100),
    _c("r0.alpha", "R-R0", "round0_knobs/alpha", 0.6),
    _c("r0.tau", "R-R0", "round0_knobs/tau", 0.5),
    _c("r1.blend", "R-R1", "arms/BLEND_ROUND1/correct_count", 63),
    _c("r1.dispatched", "R-R1", "blend_decisions/evidence_contact_dispatched_samples", 100),
    _c("r2.blend", "R-R2", "arms/BLEND_ROUND2/correct_count", 65),
    _c("r2.dispatched", "R-R2", "blend_decisions/evidence_contact_dispatched_samples", 100),
    _c("r2.alpha", "R-R2", "round2_knobs/alpha", 0.55),
    _c("r3.blend", "R-R3", "arms/BLEND_ROUND3/correct_count", 67),
    _c("r3.dispatched", "R-R3", "blend_decisions/evidence_contact_dispatched_samples", 48),
    _c("r3.retain", "R-R3", "arms/BLEND_ROUND3/retain_primary_samples", 52),
    _c("r4.blend", "R-R4", "arms/BLEND_ROUND4/correct_count", 72),
    _c("r4.dispatched", "R-R4", "blend_decisions/evidence_contact_dispatched_samples", 37),
    _c("r4.retain", "R-R4", "arms/BLEND_ROUND4/retain_primary_samples", 63),
    _c("r5.blend", "R-R5", "arms/BLEND_ROUND5/correct_count", 72),
    _c("r5.dispatched", "R-R5", "blend_decisions/evidence_contact_dispatched_samples", 33),
    _c("r5.delta_vs_r4", "R-R5", "replication_reconciliation/delta_vs_round4", 0),
    # -- K-WIDEN K1 (a refusal that flew) -----------------------------------
    _c("kwiden.correct", "R-KWIDEN", "kwiden_reconciliation/flown_correct_total", 71),
    _c("kwiden.expected", "R-KWIDEN", "kwiden_reconciliation/expected_correct_total", 72),
    _c("kwiden.delta_vs_r4", "R-KWIDEN", "kwiden_reconciliation/delta_vs_round4", -1),
    _c("kwiden.width_flips", "R-KWIDEN", "kwiden_reconciliation/width_attributable_flip_count", 0),
    _c("kwiden.dispatched", "R-KWIDEN", "blend_decisions/evidence_contact_dispatched_samples", 36),
    _c("kwiden.top_k", "R-KWIDEN", "kwiden_k1_knobs/top_k_per_dimension", 8),
    _c("kwiden.c2w", "R-KWIDEN", "stopping_rule_status/k1_c2w_vs_m0", 0),
    _c("kwiden.width_signal", "R-KWIDEN", "stopping_rule_status/width_widened_signal", False),
    # -- DEV-100 A4 retain-override (the override that later falsified) -----
    _c("a4.correct", "R-A4", "a4_reconciliation/flown_correct_total", 74),
    _c("a4.delta_vs_r4", "R-A4", "a4_reconciliation/delta_vs_round4", 2),
    _c("a4.override_dispatched", "R-A4", "blend_decisions/override_dispatched", 3),
    _c("a4.dispatched", "R-A4", "blend_decisions/evidence_contact_dispatched_samples", 41),
    _c("a4.override_flips", "R-A4", "a4_reconciliation/override_attributable_flip_count", 3),
    _c("a4.delta_bar", "R-A4", "delta_signal/bar", 0.14),
    _c("a4.branch_only", "R-A4", "branch_only_replay/verdict", "PASS"),
    # -- DEV-500 confirmatory ------------------------------------------------
    _c("dev500.n", "R-DEV500", "primary/n", 400),
    _c("dev500.m0", "R-DEV500", "primary/M0_correct", 210),
    _c("dev500.blend", "R-DEV500", "primary/BLEND_correct", 289),
    _c("dev500.delta_pp", "R-DEV500", "primary/delta_pp", 19.75),
    _c("dev500.ci_low", "R-DEV500", "primary/bootstrap/ci90_low_pp", 16.5),
    _c("dev500.ci_high", "R-DEV500", "primary/bootstrap/ci90_high_pp", 23.0),
    _c("dev500.w2c", "R-DEV500", "primary/mcnemar/n01_wrong_to_correct", 81),
    _c("dev500.c2w", "R-DEV500", "primary/mcnemar/n10_correct_to_wrong", 2),
    _c("dev500.mcnemar_p", "R-DEV500", "primary/mcnemar/exact_binomial_two_sided_p", 7.210946989931019e-22),
    _c("dev500.claim_met", "R-DEV500", "primary/claim_condition_met", True),
    _c("dev500.randret_delta", "R-DEV500", "secondaries/new400_blend_vs_randret/bootstrap/point_estimate_pp", 15.75),
    _c("dev500.randret_ci_low", "R-DEV500", "secondaries/new400_blend_vs_randret/bootstrap/ci90_low_pp", 12.5),
    _c("dev500.randret_ci_high", "R-DEV500", "secondaries/new400_blend_vs_randret/bootstrap/ci90_high_pp", 19.0),
    _c("dev500.randret_correct", "R-DEV500", "secondaries/new400_blend_vs_randret/ABL-RANDRET_correct", 226),
    _c("dev500.randicl_delta", "R-DEV500", "secondaries/new400_randicl_vs_m0/delta_pp", -5.5),
    _c("dev500.randret_vs_m0", "R-DEV500", "secondaries/new400_randret_vs_m0/delta_pp", 4.0),
    # -- The DEV-1000 baseline LOCK -----------------------------------------
    _c("lock.n", "R-LOCK", "populations/unexposed_new500_n", 500),
    _c("lock.m0", "R-LOCK", "primary/M0_correct", 278),
    _c("lock.blend", "R-LOCK", "primary/BLEND_correct", 379),
    _c("lock.delta_samples", "R-LOCK", "primary/delta_samples", 101),
    _c("lock.delta_pp", "R-LOCK", "primary/delta_pp", 20.2),
    _c("lock.ci_low", "R-LOCK", "primary/bootstrap/ci90_low_pp", 17.2),
    _c("lock.ci_high", "R-LOCK", "primary/bootstrap/ci90_high_pp", 23.4),
    _c("lock.w2c", "R-LOCK", "primary/mcnemar/n01_wrong_to_correct", 106),
    _c("lock.c2w", "R-LOCK", "primary/mcnemar/n10_correct_to_wrong", 5),
    _c("lock.condition_met", "R-LOCK", "primary/lock_condition_met", True),
    _c(
        "lock.override_zero_loss_held",
        "R-LOCK",
        "secondaries/override_subgroup/loss_side/zero_loss_property_held",
        False,
    ),
    _c("xc.locked_v1_blend", "R-XC", "decomposition/slurp_unexposed500/locked_v1_blend_correct", 382),
    _c(
        "xc.locked_v1_delta_pp",
        "R-XC",
        "decomposition/slurp_unexposed500/locked_v1_population_delta_pp",
        20.8,
    ),
    # -- The population two-axis table (both carriers, both SLURP halves) ---
    _c("mve.unexposed_m0_matching", "R-MVE", "two_axis_scoreboard/0/matching_count", 278),
    _c("mve.unexposed_m0_macro", "R-MVE", "two_axis_scoreboard/0/extraction_slot_f1_exact_mean", 0.17097619047619048),
    _c("mve.unexposed_m0_official", "R-MVE", "two_axis_scoreboard/0/extraction_slu_f1_micro_f1", 0.3766737646345322),
    _c("mve.unexposed_blend_matching", "R-MVE", "two_axis_scoreboard/1/matching_count", 379),
    _c("mve.unexposed_blend_macro", "R-MVE", "two_axis_scoreboard/1/extraction_slot_f1_exact_mean", 0.20641428571428572),
    _c("mve.unexposed_blend_official", "R-MVE", "two_axis_scoreboard/1/extraction_slu_f1_micro_f1", 0.4308127909577429),
    _c("mve.exposed_m0_matching", "R-MVE", "two_axis_scoreboard/2/matching_count", 258),
    _c("mve.exposed_m0_macro", "R-MVE", "two_axis_scoreboard/2/extraction_slot_f1_exact_mean", 0.12224761904761905),
    _c("mve.exposed_m0_official", "R-MVE", "two_axis_scoreboard/2/extraction_slu_f1_micro_f1", 0.36112984366406903),
    _c("mve.exposed_blend_matching", "R-MVE", "two_axis_scoreboard/3/matching_count", 378),
    _c("mve.exposed_blend_macro", "R-MVE", "two_axis_scoreboard/3/extraction_slot_f1_exact_mean", 0.15097142857142856),
    _c("mve.exposed_blend_official", "R-MVE", "two_axis_scoreboard/3/extraction_slu_f1_micro_f1", 0.4022671336550252),
    _c("mve.a2t_m0_matching", "R-MVE", "two_axis_scoreboard/4/matching_count", 62),
    _c("mve.a2t_m0_em", "R-MVE", "two_axis_scoreboard/4/extraction_exact_match_count", 29),
    _c("mve.a2t_m0_micro", "R-MVE", "two_axis_scoreboard/4/extraction_slot_micro_f1", 0.4378698224852071),
    _c("mve.a2t_blend_matching", "R-MVE", "two_axis_scoreboard/5/matching_count", 63),
    _c("mve.a2t_blend_em", "R-MVE", "two_axis_scoreboard/5/extraction_exact_match_count", 29),
    _c("mve.a2t_blend_micro", "R-MVE", "two_axis_scoreboard/5/extraction_slot_micro_f1", 0.41208791208791207),
    _c("mve.fidelity_pass", "R-MVE", "fidelity_gate/pass", True),
    _c(
        "mve.a_share",
        "R-MVE",
        "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/a_share_of_absolute_total",
        0.7178177909164203,
    ),
    _c(
        "mve.b_points",
        "R-MVE",
        "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/ab_split/b_points",
        1.0000000000000002,
    ),
    _c(
        "mve.both_matched_n",
        "R-MVE",
        "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/cells/both_matched/n",
        273,
    ),
    # -- The supersession: extraction conditioned on dispatch ---------------
    _c("ecd.superseded_cell_dispatched_unexposed", "R-ECD", "slurp/unexposed500/cross_tabulation/cells/both_matched/dispatched_n", 3),
    _c("ecd.superseded_cell_dispatched_exposed", "R-ECD", "slurp/exposed500/cross_tabulation/cells/both_matched/dispatched_n", 2),
    _c("ecd.superseded_cell_dispatched_a2t", "R-ECD", "a2t/cross_tabulation/cells/both_matched/dispatched_n", 0),
    _c("ecd.dispatched_n", "R-ECD", "slurp/unexposed500/strata/dispatched/n", 163),
    _c("ecd.dispatched_m0_matching", "R-ECD", "slurp/unexposed500/strata/dispatched/matching/M0_correct", 7),
    _c("ecd.dispatched_blend_matching", "R-ECD", "slurp/unexposed500/strata/dispatched/matching/BLEND_correct", 100),
    _c("ecd.dispatched_matching_delta", "R-ECD", "slurp/unexposed500/strata/dispatched/matching/delta_pp", 57.05521472392638),
    _c("ecd.dispatched_matching_ci_low", "R-ECD", "slurp/unexposed500/strata/dispatched/matching/bootstrap/ci90_low_pp", 50.306748466257666),
    _c("ecd.dispatched_matching_ci_high", "R-ECD", "slurp/unexposed500/strata/dispatched/matching/bootstrap/ci90_high_pp", 63.80368098159509),
    _c("ecd.dispatched_macro_delta", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", 9.439088518843121),
    _c("ecd.dispatched_macro_ci_low", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_low_pp", 4.355828220858895),
    _c("ecd.dispatched_macro_ci_high", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_high_pp", 14.519427402862988),
    _c("ecd.dispatched_official_delta", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slu_f1_micro_delta/point_estimate", 13.757043323670127),
    _c("ecd.dispatched_official_ci_low", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slu_f1_micro_delta/ci90_low", 8.884029844371804),
    _c("ecd.dispatched_official_ci_high", "R-ECD", "slurp/unexposed500/strata/dispatched/bootstrap_slu_f1_micro_delta/ci90_high", 18.669490340410512),
    _c("ecd.retained_n", "R-ECD", "slurp/unexposed500/strata/retained/n", 337),
    _c("ecd.retained_matching_delta", "R-ECD", "slurp/unexposed500/strata/retained/matching/delta_pp", 2.373887240356083),
    _c("ecd.free_cell_n", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/n", 59),
    _c("ecd.free_cell_macro", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/point_estimate_pp", 6.779661016949152),
    _c("ecd.free_cell_macro_ci_low", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_low_pp", 1.694915254237288),
    _c("ecd.free_cell_macro_ci_high", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slot_f1_exact_mean_delta/ci90_high_pp", 11.864406779661017),
    _c("ecd.free_cell_official", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/point_estimate", 15.231239819565115),
    _c("ecd.free_cell_official_ci_low", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/ci90_low", 8.21272658914912),
    _c("ecd.free_cell_official_ci_high", "R-ECD", "slurp/unexposed500/eight_cell_extraction/neither_matched|dispatched/bootstrap_slu_f1_micro_delta/ci90_high", 22.977784937447844),
    _c("ecd.three_way_matching", "R-ECD", "slurp/unexposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/matching_attributable", 2.543809523809525),
    _c("ecd.three_way_supply", "R-ECD", "slurp/unexposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched", 0.9333333333333332),
    _c("ecd.three_way_residue", "R-ECD", "slurp/unexposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/decode_variance_unsupplied_retained", 0.06666666666666586),
    _c("ecd.three_way_supply_exposed", "R-ECD", "slurp/exposed500/three_way_decomposition_slot_f1_exact_mean/terms_points/supply_attributable_dispatched", -0.0533333333333334),
    _c("ecd.a2t_dispatched_n", "R-ECD", "a2t/strata/dispatched/n", 15),
    _c("ecd.a2t_dispatched_delta", "R-ECD", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/point_estimate", 12.121212121212123),
    _c("ecd.a2t_dispatched_ci_low", "R-ECD", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_low", 0.0),
    _c("ecd.a2t_dispatched_ci_high", "R-ECD", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_high", 23.076923076923077),
    _c("ecd.a2t_dispatched_excludes_zero", "R-ECD", "a2t/strata/dispatched/bootstrap_slot_micro_f1_delta/ci90_excludes_zero", False),
    _c("ecd.a2t_retained_n", "R-ECD", "a2t/strata/retained/n", 89),
    _c("ecd.a2t_retained_delta", "R-ECD", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/point_estimate", -3.0249966324783104),
    _c("ecd.a2t_retained_ci_low", "R-ECD", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/ci90_low", -6.194049268636866),
    _c("ecd.a2t_retained_ci_high", "R-ECD", "a2t/strata/retained/bootstrap_slot_micro_f1_delta/ci90_high", -0.594122935347456),
    # -- Delivery: the rates that must stand beside every conditional --------
    _c("field.slurp_delivered", "R-FIELD", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/contacts_that_received_supply", 163),
    _c("field.slurp_rate", "R-FIELD", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/delivery_rate", 0.326),
    _c("field.slurp_population", "R-FIELD", "channel_cost/slurp/DEV-1000-NEW500 (UNEXPOSED)/two_rate/delivery/population_size", 500),
    _c("field.a2t_delivered", "R-FIELD", "channel_cost/audio2tool/two_rate/delivery/contacts_that_received_supply", 15),
    _c("field.a2t_rate", "R-FIELD", "channel_cost/audio2tool/two_rate/delivery/delivery_rate", 0.144231),
    _c("field.a2t_population", "R-FIELD", "channel_cost/audio2tool/two_rate/delivery/population_size", 104),
    # -- Audio2Tool G1 -------------------------------------------------------
    _c("g1.n", "R-G1", "population/count", 104),
    _c("g1.m0_tool", "R-G1", "paired_tool_accuracy/m0_count", 62),
    _c("g1.blend_tool", "R-G1", "paired_tool_accuracy/blend_count", 63),
    _c("g1.tool_delta_pp", "R-G1", "paired_tool_accuracy/delta_pp", 0.9615384615384616),
    _c("g1.m0_em", "R-G1", "paired_exact_match/m0_count", 29),
    _c("g1.blend_em", "R-G1", "paired_exact_match/blend_count", 29),
    _c("g1.em_delta_pp", "R-G1", "paired_exact_match/delta_pp", 0.0),
    _c("g1.dispatched", "R-G1", "mechanism/dispatched", 15),
    _c("g1.retained", "R-G1", "mechanism/retained_primary", 89),
    _c("g1.retain_equals_direct", "R-G1", "mechanism/retain_equals_direct_label_recovered", True),
    _c("g1.branch_only_vacuous", "R-G1", "mechanism/branch_only_replay_is_vacuous", False),
    _c("g1.m0_empty_rate", "R-G1", "headline/m0_empty_call_rate", 0.1346153846153846),
    _c("g1.blend_empty_rate", "R-G1", "headline/blend_empty_call_rate", 0.028846153846153848),
    # -- The ranker admission-scale defect and its repair --------------------
    _c("sweep.a2t_dispatch_prefix", "R-SWEEP", "audio2tool/alpha_gate/by_variant/V0-FROZEN/would_dispatch", 0),
    _c("sweep.a2t_dispatch_postfix", "R-SWEEP", "audio2tool/alpha_gate/by_variant/A6-DIMSUP-FLOOR1/would_dispatch", 15),
    _c("sweep.a2t_zero_content", "R-SWEEP", "audio2tool/scale_audit/eviction/trajectories_with_zero_content_facets_in_top_m", 104),
    _c("sweep.m_needed", "R-SWEEP", "audio2tool/scale_audit/eviction/m_needed_to_admit_every_admissible_content_facet", 15),
    _c("sweep.flown_supply_reproduced", "R-SWEEP", "audio2tool/baseline_fidelity_gate/flown_supply_reproduced", 104),
    _c("sweep.flown_dispatch_reproduced", "R-SWEEP", "audio2tool/baseline_fidelity_gate/flown_dispatch_decision_reproduced", 104),
    _c("sweep.gold_bearing_admitted", "R-SWEEP", "audio2tool/variant_table/A6-DIMSUP-FLOOR1/gold_bearing_supply_admitted", 68),
    # -- The Audio2Tool ceiling: four refusals by measurement ----------------
    _c("gold.build_defects", "R-GOLD", "q1_build_versus_ranking/case_a_build_coverage_defect/n", 0),
    _c("gold.ranking_defects", "R-GOLD", "q1_build_versus_ranking/case_b_ranking_recall_defect/n", 11),
    _c("gold.dominating", "R-GOLD", "q1_build_versus_ranking/dominating_sub_cause", "RANKING"),
    _c("gold.recall_at_5", "R-GOLD", "q2_reachability_curve/curve_case_b_ranking_defect/recall_at_5/count", 0),
    _c("gold.recall_at_512", "R-GOLD", "q2_reachability_curve/curve_case_b_ranking_defect/recall_at_512/rate", 1.0),
    _c("gold.reached_under_locked_top_l", "R-GOLD", "q2_reachability_curve/binding_stage/reached_at_some_depth_under_the_locked_top_l_3", 0),
    _c("gold.reached_under_any_top_l", "R-GOLD", "q2_reachability_curve/binding_stage/reached_at_some_depth_under_any_top_l", 2),
    _c("gold.blocked_by_tau", "R-GOLD", "q2_reachability_curve/binding_stage/blocked_by_the_tau_percept_gate", 9),
    _c("gold.form_repaired", "R-GOLD", "q5_form_repair_channel/form_repaired_n", 11),
    _c("gold.form_repaired_still_wrong", "R-GOLD", "q5_form_repair_channel/form_repaired_but_still_wrong_n", 9),
    _c("oracle.o3_supplied", "R-ORACLE", "oracle_bound/summary/O3_gold_supplied_of_the_gold_absent", 11),
    _c("oracle.o3_twin_free", "R-ORACLE", "oracle_bound/summary/O3_TWIN_FREE_gold_supplied_of_the_gold_absent", 11),
    _c("oracle.o3_rate_delivered", "R-ORACLE", "oracle_bound/summary/O3_RATE_pooled_delivered", 1596),
    _c("oracle.o3_rate_tried", "R-ORACLE", "oracle_bound/summary/O3_RATE_pooled_tried", 1871),
    _c("oracle.n1_clears_tau", "R-ORACLE", "lower_constructions/summary/N1_gold_facet_clears_tau_of_all_dispatched", 15),
    _c("oracle.n1_supplies_gold", "R-ORACLE", "lower_constructions/summary/N1_gold_supplied_of_all_dispatched", 0),
    _c("oracle.leak_units", "R-ORACLE", "utterance_leak_check/eval_UNITS_present_in_the_kb", 0),
    _c("oracle.leak_texts", "R-ORACLE", "utterance_leak_check/eval_UTTERANCE_TEXTS_matching_a_kb_content_facet", 6),
    _c("oracle.leak_among_dispatched", "R-ORACLE", "utterance_leak_check/text_matches_among_the_dispatched_15", 0),
    # -- Cross-carrier arithmetic --------------------------------------------
    _c("xc.reach_a2t", "R-XC", "decomposition/cross_carrier/reachable_share/a2t", 0.14423076923076922),
    _c("xc.reach_slurp", "R-XC", "decomposition/cross_carrier/reachable_share/slurp_unexposed500", 0.32),
    _c("xc.conv_a2t", "R-XC", "decomposition/cross_carrier/within_reach_conversion_pp/a2t", 13.333333333333334),
    _c("xc.conv_slurp", "R-XC", "decomposition/cross_carrier/within_reach_conversion_pp/slurp_unexposed500", 59.375),
    _c("xc.product_a2t", "R-XC", "decomposition/cross_carrier/reach_times_conversion_pp/a2t", 1.923076923076923),
    _c("xc.product_slurp", "R-XC", "decomposition/cross_carrier/reach_times_conversion_pp/slurp_unexposed500", 19.0),
    _c("xc.drift_a2t", "R-XC", "decomposition/cross_carrier/retain_drift_pp/a2t", -0.9615384615384616),
    _c("xc.drift_slurp", "R-XC", "decomposition/cross_carrier/retain_drift_pp/slurp_unexposed500", 1.6),
    _c("xc.closes_a2t", "R-XC", "decomposition/audio2tool/closes_exactly", True),
    _c("xc.closes_slurp", "R-XC", "decomposition/slurp_unexposed500/closes_exactly_as_flown", True),
    # -- Query-key degeneracy -------------------------------------------------
    _c("degen.a2t_control_reproduced", "R-DEGEN", "a2t_control/control_reproduced", True),
    _c("degen.a2t_dead_keys_per_traj", "R-DEGEN", "a2t_control/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.3333333333333333),
    _c("degen.a2t_live_keys_per_traj", "R-DEGEN", "a2t_control/degeneracy/label_recovered/distinct_query_vectors_per_trajectory", 0.9438202247191011),
    _c("degen.slurp_unexposed_dead_keys", "R-DEGEN", "slurp/halves/UNEXPOSED-NEW500/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.85),
    _c("degen.slurp_exposed_dead_keys", "R-DEGEN", "slurp/halves/EXPOSED-DEV500/degeneracy/dead_direct/distinct_query_vectors_per_trajectory", 0.7349397590361446),
    # -- The model-free audits and repairs of 2026-08-25 ---------------------
    _c("k1gate.dense_recall1", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/DENSE-ONLY/recall_at_1/rate", 0.636),
    _c("k1gate.dense_recall5", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/DENSE-ONLY/recall_at_5/rate", 0.744),
    _c("k1gate.rrf_recall1", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/RRF-60/recall_at_1/rate", 0.59),
    _c("k1gate.rrf_recall5", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/RRF-60/recall_at_5/rate", 0.762),
    _c("k1gate.rrf_recall1_count", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/RRF-60/recall_at_1/count", 295),
    _c("k1gate.dense_recall1_count", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/DENSE-ONLY/recall_at_1/count", 318),
    _c("k1gate.falsifier", "R-K1GATE", "falsifier/verdict", "RAISED"),
    _c("fusion.c1_verdict", "R-FUSION", "verdict_by_form/C1/verdict", "REFUSED -- NO MEASURABLE GAIN (an exact identity on every measured quantity on every population; expressly NOT the same verdict as HARMFUL)"),
    _c("fusion.c1_changed", "R-FUSION", "verdict_by_form/C1/unexposed_500_decisions_changed", 0),
    _c("fusion.c2_changed", "R-FUSION", "verdict_by_form/C2/unexposed_500_decisions_changed", 0),
    _c("fusion.c2b_changed", "R-FUSION", "verdict_by_form/C2B-0.25/unexposed_500_decisions_changed", 0),
    _c("fusion.c3_verdict", "R-FUSION", "verdict_by_form/C3/verdict", "REFUSED on EVERY population"),
    _c("fusion.c3_changed", "R-FUSION", "verdict_by_form/C3/unexposed_500_decisions_changed", 199),
    _c("fusion.c0_identity", "R-FUSION", "verdict_by_form/C0/identical_to_control_on_every_population", True),
    _c("gates.mutations_total", "R-GATEAUDIT", "mutations_total_recorded", 140),
    _c("gates.mutations_live", "R-GATEAUDIT", "mutations_live", 112),
    _c("gates.fires", "R-GATEAUDIT", "mutation_tally_live/FIRES", 69),
    _c("gates.did_not_fire", "R-GATEAUDIT", "mutation_tally_live/DID-NOT-FIRE", 23),
    _c("gates.ok_control", "R-GATEAUDIT", "mutation_tally_live/OK-CONTROL", 20),
    _c("gates.outbound", "R-GATEAUDIT", "offline_guard/outbound_connection_attempts_total", 0),
    _c("intent.modeled", "R-INTENT", "q2_snapshot_models/label_intent_facets", 60),
    _c("intent.task_vocabulary", "R-INTENT", "q4_coverage_denominator/task_intent_vocabulary_train_union_devel", 60),
    _c("intent.landed_coverage", "R-INTENT", "q4_coverage_denominator/landed_intent_coverage", 1.0),
    _c("intent.recomputed_coverage", "R-INTENT", "q4_coverage_denominator/recomputed_intent_coverage", 1.0),
    _c("intent.unmodeled_dev1000", "R-INTENT", "q5_consequence/dev1000_samples_carrying_an_unmodeled_intent", 0),
    _c("intent.unmodeled_unexposed500", "R-INTENT", "q5_consequence/unexposed_500_unmodeled_samples", 0),
    _c("intent.docstring_intent_field", "R-INTENT", "docstring_claim_under_test/measured_train_intents_intent_field", 91),
    _c("intent.docstring_scenario_action", "R-INTENT", "docstring_claim_under_test/measured_train_intents_scenario_action", 60),
    _c("prior.violation_supremum", "R-PRIOR", "range_contract_on_the_pinned_snapshot/violation_supremum", 4.1),
    _c("prior.recorded_violations", "R-PRIOR", "range_contract_on_the_pinned_snapshot/recorded_violations", 193),
    _c("prior.values_moved", "R-PRIOR", "a2t_prior_before_after/values_moved", 12237),
    _c("prior.values_unchanged", "R-PRIOR", "a2t_prior_before_after/values_unchanged", 364),
    _c("prior.supply_changed", "R-PRIOR", "corrected_prior_supply_replay/supply_changed_trajectories", 0),
    _c("prior.fidelity_supply", "R-PRIOR", "landed_fidelity_gate/supply_reproduced", 104),
    _c("prior.fidelity_dispatch", "R-PRIOR", "landed_fidelity_gate/dispatch_decision_reproduced", 104),
    _c("prior.pins_unchanged", "R-PRIOR", "pinned_artifacts/all_unchanged", True),
    _c("synth.claims", "R-SYNTH", "claims_verified", 332),
    _c("synth.receipts", "R-SYNTH", "receipts_verified", 12),
    _c("synth.outbound", "R-SYNTH", "offline_guard/outbound_connection_attempts", 0),
    # -- Intervals and secondaries the scoreboard prints beside the points ---
    _c("g1.tool_ci_low", "R-G1", "paired_tool_accuracy/bootstrap/ci90_low_pp", -2.8846153846153846),
    _c("g1.tool_ci_high", "R-G1", "paired_tool_accuracy/bootstrap/ci90_high_pp", 4.8076923076923075),
    _c("g1.tool_excludes_zero", "R-G1", "paired_tool_accuracy/bootstrap/ci90_excludes_zero", False),
    _c("g1.tool_share_at_or_below_zero", "R-G1", "paired_tool_accuracy/bootstrap/replicate_share_at_or_below_zero", 0.4156),
    _c("g1.tool_w2c", "R-G1", "paired_tool_accuracy/mcnemar/n01_wrong_to_correct", 3),
    _c("g1.tool_c2w", "R-G1", "paired_tool_accuracy/mcnemar/n10_correct_to_wrong", 2),
    _c("g1.tool_midp", "R-G1", "paired_tool_accuracy/mcnemar/mid_p_two_sided", 0.6875),
    _c("g1.em_ci_low", "R-G1", "paired_exact_match/bootstrap/ci90_low_pp", -1.9230769230769231),
    _c("g1.em_ci_high", "R-G1", "paired_exact_match/bootstrap/ci90_high_pp", 1.9230769230769231),
    _c("g1.em_excludes_zero", "R-G1", "paired_exact_match/bootstrap/ci90_excludes_zero", False),
    _c(
        "mve.unexposed_agg_delta_points",
        "R-MVE",
        "slurp/unexposed500/joint_decomposition_slot_f1_exact_mean/aggregate_delta_points",
        3.543809523809524,
    ),
    _c(
        "mve.exposed_agg_delta_points",
        "R-MVE",
        "slurp/exposed500/joint_decomposition_slot_f1_exact_mean/aggregate_delta_points",
        2.872380952380951,
    ),
    _c(
        "mve.a2t_agg_delta_points",
        "R-MVE",
        "audio2tool/joint_decomposition_slot_f1_mean/aggregate_delta_points",
        -0.28846153846153744,
    ),
    _c("lock.mcnemar_p", "R-LOCK", "primary/mcnemar/exact_binomial_two_sided_p", 1.035239298994319e-25),
    _c("lock.ci95_low", "R-LOCK", "primary/bootstrap/ci95_low_pp", 16.6),
    _c("lock.ci95_high", "R-LOCK", "primary/bootstrap/ci95_high_pp", 24.0),
    _c("lock.sigma", "R-LOCK", "primary/bootstrap/sigma_hat_pp", 1.898559506151967),
    _c(
        "lock.scale_overlap",
        "R-LOCK",
        "secondaries/scale_stability_vs_dev500/ci90_intervals_overlap",
        True,
    ),
    _c(
        "lock.scale_point_inside",
        "R-LOCK",
        "secondaries/scale_stability_vs_dev500/dev1000_point_inside_dev500_ci90",
        True,
    ),
    _c("lock.override_fires_total", "R-LOCK", "secondaries/override_subgroup/fires_total", 14),
    _c("lock.override_fires_exposed", "R-LOCK", "secondaries/override_subgroup/fires_in_exposed_500", 11),
    _c("lock.override_fires_unexposed", "R-LOCK", "secondaries/override_subgroup/fires_in_unexposed_500", 3),
    _c(
        "lock.override_recovered_exposed",
        "R-LOCK",
        "secondaries/override_subgroup/on_the_prior_exposed_500_no_claim/recovered",
        11,
    ),
    _c(
        "lock.override_damaged_exposed",
        "R-LOCK",
        "secondaries/override_subgroup/on_the_prior_exposed_500_no_claim/damaged",
        0,
    ),
    _c("lock.override_damaged_total", "R-LOCK", "secondaries/override_subgroup/over_all_1000_descriptive/damaged", 3),
    # -- The DEV-100 reviewer audit -----------------------------------------
    _c("audit.r0_point", "R-AUDIT", "q1_uncertainty/round0/bootstrap/point_estimate_pp", 15.0),
    _c("audit.r0_ci_low", "R-AUDIT", "q1_uncertainty/round0/bootstrap/ci90_low_pp", 5.0),
    _c("audit.r0_ci_high", "R-AUDIT", "q1_uncertainty/round0/bootstrap/ci90_high_pp", 24.0),
    _c("audit.r3_point", "R-AUDIT", "q1_uncertainty/round3/bootstrap/point_estimate_pp", 19.0),
    _c("audit.r3_ci_low", "R-AUDIT", "q1_uncertainty/round3/bootstrap/ci90_low_pp", 11.0),
    _c("audit.r3_ci_high", "R-AUDIT", "q1_uncertainty/round3/bootstrap/ci90_high_pp", 27.0),
    _c("audit.r3_mcnemar_p", "R-AUDIT", "q1_uncertainty/round3/mcnemar/exact_binomial_two_sided_p", 0.0005461126565933228),
    _c("audit.r3_w2c", "R-AUDIT", "q1_uncertainty/round3/mcnemar/n01_wrong_to_correct", 24),
    _c("audit.r3_c2w", "R-AUDIT", "q1_uncertainty/round3/mcnemar/n10_correct_to_wrong", 5),
    _c("audit.floor_flipped_gain", "R-AUDIT", "q2_variance_channel/floors/adversarial_flipped/gain_samples", 15),
    _c("audit.floor_flipped_ci_low", "R-AUDIT", "q2_variance_channel/floors/adversarial_flipped_bootstrap/ci90_low_pp", 6.0),
    _c("audit.floor_flipped_ci_high", "R-AUDIT", "q2_variance_channel/floors/adversarial_flipped_bootstrap/ci90_high_pp", 24.0),
    _c("audit.floor_worst_gain", "R-AUDIT", "q2_variance_channel/floors/observed_worst/gain_samples", 12),
    _c("audit.floor_worst_ci_low", "R-AUDIT", "q2_variance_channel/floors/observed_worst_bootstrap/ci90_low_pp", 2.0),
    _c("audit.floor_all_unstable_gain", "R-AUDIT", "q2_variance_channel/floors/adversarial_all_unstable/gain_samples", -24),
    _c("audit.majority_class", "R-AUDIT", "q3_baseline_fairness/majority_class/majority_class_accuracy", 0.06),
    _c("audit.uniform_chance", "R-AUDIT", "q3_baseline_fairness/majority_class/uniform_chance_over_60_intents", 0.016666666666666666),
    _c("lock.exposed_m0", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/M0_correct", 258),
    _c("lock.exposed_blend", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/BLEND_correct", 378),
    _c("lock.exposed_delta_pp", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/delta_pp", 24.0),
    _c("lock.exposed_ci_low", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/bootstrap/ci90_low_pp", 20.8),
    _c("lock.exposed_ci_high", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/bootstrap/ci90_high_pp", 27.2),
    _c("lock.exposed_w2c", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/wrong_to_correct_count", 123),
    _c("lock.exposed_c2w", "R-LOCK", "secondaries/exposed_500_blend_vs_m0/correct_to_wrong_count", 3),
    _c("kwiden.supply_changed_total", "R-KWIDEN", "kwiden_reconciliation/supply_width_attribution/supply_changed_by_width_total", 32),
    _c("kwiden.supply_changed_dispatched", "R-KWIDEN", "kwiden_reconciliation/supply_width_attribution/supply_changed_by_width_dispatched", 15),
    _c("r4.alpha", "R-R4", "round4_knobs/alpha", 0.45),
    _c("r4.tau", "R-R4", "round4_knobs/tau", 0.65),
    _c("r4.top_k", "R-R4", "round4_knobs/top_k_per_dimension", 5),
    _c("r4.fusion_m", "R-R4", "round4_knobs/fusion/m", 5),
    _c("r4.fusion_c", "R-R4", "round4_knobs/fusion/c", 2),
    _c("r4.fusion_l", "R-R4", "round4_knobs/fusion/l", 3),
    _c("gold.k3_flown_dispatch", "R-GOLD", "k3_dispatch_projection/projection_upper_bound_on_repair/flown_dispatch_count", 15),
    _c("gold.k3_projected_dispatch", "R-GOLD", "k3_dispatch_projection/projection_upper_bound_on_repair/projected_dispatch_count", 3),
    _c("gold.k3_rate_change_pp", "R-GOLD", "k3_dispatch_projection/projection_upper_bound_on_repair/projected_dispatch_rate_change_pp", -11.538461538461538),
    _c("gold.blocked_by_top_l_only", "R-GOLD", "q2_reachability_curve/binding_stage/blocked_by_the_top_l_target_budget_only", 2),
    _c("fusion.slurp_exposed_dispatched", "R-FUSION", "populations/SLURP-EXPOSED-500/flown_dispatched", 177),
    _c("fusion.slurp_exposed_n", "R-FUSION", "populations/SLURP-EXPOSED-500/n", 500),
    _c("e108.factor_supply_queries", "R-E108", "aggregates/0/agent_loop_metrics/information_flow/factor_supply_query_count", 108),
    _c("prior.selected_values", "R-PRIOR", "a2t_prior_before_after/selected_values", 12601),
    _c("audit.floor_worst_ci_high", "R-AUDIT", "q2_variance_channel/floors/observed_worst_bootstrap/ci90_high_pp", 22.0),
    _c("k1gate.rrf_recall5_count", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/RRF-60/recall_at_5/count", 381),
    _c("k1gate.dense_recall5_count", "R-K1GATE", "populations/DEV-1000-NEW500/by_query_normalization/Q-RAW/recall_table/DENSE-ONLY/recall_at_5/count", 372),
    # -- The alpha-trade decision sizing (open owner decision D1) ------------
    _c("alpha.control_alpha", "R-ALPHA", "registered_constants/control_alpha", 0.45),
    _c("alpha.slurp_control_dispatched", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.45/reach/dispatched", 160),
    _c("alpha.slurp_050_dispatched", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/reach/dispatched", 184),
    _c("alpha.slurp_050_rate", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/reach/dispatch_rate", 0.368),
    _c("alpha.slurp_050_newly", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/newly_dispatching_vs_control/n", 24),
    _c("alpha.slurp_050_at_risk", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/risk/currently_correct_put_at_risk", 20),
    _c("alpha.slurp_050_risk_gold_omitted", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/risk/of_those_at_risk_the_supply_omits_gold", 20),
    _c("alpha.slurp_050_risk_gold_carried", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/risk/of_those_at_risk_the_supply_carries_gold", 0),
    _c("alpha.slurp_050_gold_bearing", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/supply_quality_of_the_newly_dispatched/would_receive_a_gold_bearing_supply", 3),
    _c("alpha.slurp_050_central_pp", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/projection/delta_pp_central", -3.4109090909090924),
    _c("alpha.slurp_050_pessimistic_pp", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/projection/delta_pp_pessimistic", -3.582608695652175),
    _c("alpha.slurp_050_optimistic_pp", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/projection/delta_pp_optimistic", -0.010909090909092357),
    _c("alpha.slurp_050_margin", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/margin_arithmetic/guaranteed_margin_1_minus_2alpha", 0.0),
    _c("alpha.slurp_050_tie", "R-ALPHA", "populations/SLURP-UNEXPOSED-500/by_alpha/0.50/margin_arithmetic/worst_case_is_an_exact_tie", True),
    _c("alpha.a2t_050_newly", "R-ALPHA", "populations/A2T-G1-104/by_alpha/0.50/newly_dispatching_vs_control/n", 2),
    _c("alpha.a2t_050_at_risk", "R-ALPHA", "populations/A2T-G1-104/by_alpha/0.50/risk/currently_correct_put_at_risk", 0),
    _c("alpha.a2t_control_dispatched", "R-ALPHA", "populations/A2T-G1-104/by_alpha/0.45/reach/dispatched", 15),
)


SUBSTRING_CLAIMS: tuple[SubstringClaim, ...] = (
    SubstringClaim(
        "s2.copy_trap_detail",
        "R-A2T-S2",
        "branch_verdict/copy_trap_clauses/0/detail",
        "induced=34, em_flips=16",
    ),
    SubstringClaim(
        "s2b.b1_conversion",
        "R-A2T-S2B",
        "qa_verdict/confirmed_cut_clauses/1/detail",
        "B1 conversion=0.0667 (8/120)",
    ),
    SubstringClaim(
        "s2b.b1_induced",
        "R-A2T-S2B",
        "qa_verdict/confirmed_cut_clauses/0/detail",
        "B1 induced=2",
    ),
    SubstringClaim(
        "s2c.c3_induced",
        "R-A2T-S2C",
        "deploy_augment_verdict/channel_reopened_clause/detail",
        "C3 induced=22",
    ),
    SubstringClaim(
        "s2c.c1_conversion",
        "R-A2T-S2C",
        "form_robustness_verdict/robust_clauses/0/detail",
        "C1 conversion=0.0833 (10/120)",
    ),
    SubstringClaim(
        "loss.drag_rate",
        "R-A2T-LOSS",
        "b2_verdict/drift_confirmed_clause/detail",
        "dragged=3/21 (rate=0.1429)",
    ),
    SubstringClaim(
        "abst.refuted_detail",
        "R-A2T-ABST",
        "verdict/refuted_clause/detail",
        "abstention(TP-S)=11/11",
    ),
    SubstringClaim(
        "abst.confirmed_detail",
        "R-A2T-ABST",
        "verdict/confirmed_clause/detail",
        "abstention(TW-A)=2/11, confabulation(TP-S)=0/11",
    ),
    SubstringClaim(
        "pkey2.ci",
        "R-PKEY2",
        "ci_verdict/key_only/detail",
        "CI=[-0.0033, +0.0970]",
    ),
    SubstringClaim(
        "pemb4r.lco_scoped",
        "R-PEMB4R",
        "verdict/per_audio_arm_detail/a-lco3",
        "POOLING-OVERRIDE-PRESENT",
    ),
    SubstringClaim(
        "pfew.ci",
        "R-PFEW",
        "verdict/fs_helps/detail",
        "CI=[-0.0667, +0.0667]",
    ),
    SubstringClaim(
        "kwiden.sealed_line",
        "R-A4",
        "kwiden_k1_citation/sealed_results",
        "71/100",
    ),
    SubstringClaim(
        "r0.movement",
        "R-R1",
        "round0_citation/sealed_results",
        "M0 48/100; BLEND(tau .5) 63/100; W->C 26; C->W 11",
    ),
    SubstringClaim(
        "r1.tau_inert",
        "R-R2",
        "round1_citation/sealed_results",
        "tau proven INERT on [0.5, 0.65]",
    ),
)


DOCUMENT_CLAIMS: tuple[DocumentClaim, ...] = (
    # The EFFECT-C108 read wrote its output OUTSIDE Git; the plan document is
    # the landed record and carries the read's own SHA-256.
    DocumentClaim(
        "sn.read_digest",
        "D-SN",
        "wrote SHA-256 `6f7017fbe584c0cadccac0c48d091b0d2ec52b4fdbb83441c13abaddf923f40a`",
    ),
    DocumentClaim("sn.k0m0", "D-SN", "Direct K0-M0 scores 77/108."),
    DocumentClaim("sn.k1m1", "D-SN", "embedded speech-only K1-M1 primary scores 90/108"),
    DocumentClaim("sn.final", "D-SN", "the final grounded refinement scores 89/108"),
    DocumentClaim(
        "sn.controls",
        "D-SN",
        "Key-text shuffle collapses to 0/108, while speech swap reaches 75/108.",
    ),
    # The speech-swap THRESHOLD outcome, which the v4 scoreboard got backwards.
    DocumentClaim(
        "sn.swap_threshold",
        "D-SN",
        "Matched M6 exceeds speech-swap by 14/108, below the frozen 24 threshold, "
        "and exceeds key-text-shuffle by 89/108, above the frozen 18 threshold.",
    ),
    DocumentClaim("sn.oracle", "D-SN", "reaches 94/108, four above primary"),
    DocumentClaim(
        "sn.controllers",
        "D-SN",
        "rejects the current AgentLoop controller",
    ),
    DocumentClaim("e108.gate", "D-E108", "support_gate_passed = false"),
    DocumentClaim("e108.conjuncts", "D-E108", "6 of 8 conjuncts fail"),
    # E-C: refused by projection as an off-switch.
    DocumentClaim(
        "ec.contacts",
        "D-EC",
        "an E-C arm's\n**evidence-contact count is ZERO**",
    ),
    DocumentClaim("ec.dispatch_collapse", "D-EC", "| 37 → **0** | 33 → **0** | 130 → **0** |"),
    DocumentClaim("ec.not_as_briefed", "D-EC", "E-C should not be flown as briefed."),
    DocumentClaim(
        "ec.band",
        "D-EC",
        "| projected change vs sealed | **−18 … −5** | −15 … −4 | −71 … −37 |",
    ),
    # K-WIDEN K2 and E-A.
    DocumentClaim(
        "kwiden.k2",
        "D-KWIDEN",
        "**K2 at 16/32 is NOT\nrecommended as a width-only move**",
    ),
    DocumentClaim(
        "kwiden.stop",
        "D-KWIDEN",
        "Stopping rule: CONVERGED-OR-FALSIFIED for width at this tier",
    ),
    DocumentClaim("ea.degenerate", "D-KWIDEN", "The briefed trigger is degenerate."),
    DocumentClaim(
        "ea.not_dev100",
        "D-KWIDEN",
        "E-A cannot be evaluated on DEV-100",
    ),
    # The gate audit's GATE-level split lives in the document; the receipt
    # publishes the MUTATION-level tally instead. Both are carried, apart.
    DocumentClaim(
        "gates.split",
        "D-GATES",
        "Of the 43 gates in scope, 23 FIRE, 10 CANNOT FAIL, 9 are NARROWER THAN THEIR CLAIM, and 1 is\nUNTESTED.",
    ),
)


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def verify_artifacts(repo_root: Path) -> dict[str, Any]:
    """Re-hash every cited receipt and document against its pinned digest."""

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for artifact in (*RECEIPTS, *DOCUMENTS):
        path = repo_root / artifact.relpath
        if not path.is_file():
            failures.append(f"{artifact.key}: MISSING at {artifact.relpath}")
            continue
        crlf = crlf_defect(path)
        if crlf is not None:
            failures.append(f"{artifact.key}: {crlf}")
            continue
        measured = sha256_of(path)
        ok = measured == artifact.sha256
        if not ok:
            failures.append(
                f"{artifact.key}: digest {measured} != pinned {artifact.sha256}"
            )
        rows.append(
            {
                "key": artifact.key,
                "relpath": artifact.relpath,
                "sha256": measured,
                "matches_pin": ok,
                "tier": "R" if artifact in RECEIPTS else "D",
                "produced_by": artifact.produced_by,
            }
        )
    if failures:
        raise ScoreboardVerificationError(
            "artifact digest verification failed:\n  " + "\n  ".join(failures)
        )
    return {"artifacts": rows, "receipts_verified": len(RECEIPTS), "documents_verified": len(DOCUMENTS)}


def load_receipts(repo_root: Path) -> dict[str, Any]:
    return {
        r.key: json.loads((repo_root / r.relpath).read_text(encoding="utf-8"))
        for r in RECEIPTS
    }


def load_documents(repo_root: Path) -> dict[str, str]:
    return {
        d.key: (repo_root / d.relpath).read_text(encoding="utf-8") for d in DOCUMENTS
    }


def verify_claims(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Walk each declared JSON path and compare against the carried value."""

    failures: list[str] = []
    for claim in CLAIMS:
        try:
            measured = _walk(documents[claim.receipt], claim.path, receipt_key=claim.receipt)
        except Exception as exc:  # noqa: BLE001 - reported, never swallowed
            failures.append(f"{claim.claim_id}: {exc}")
            continue
        if not _matches(measured, claim.expected):
            failures.append(
                f"{claim.claim_id} ({claim.receipt} - {claim.path}): "
                f"receipt has {measured!r}, scoreboard carries {claim.expected!r}"
            )
    if failures:
        raise ScoreboardVerificationError(
            f"{len(failures)} of {len(CLAIMS)} carried numbers do not match their "
            "receipt:\n  " + "\n  ".join(failures)
        )
    return {"claims_verified": len(CLAIMS)}


def verify_substring_claims(documents: Mapping[str, Any]) -> dict[str, Any]:
    """Check figures a receipt publishes only inside a clause-detail string."""

    failures: list[str] = []
    for claim in SUBSTRING_CLAIMS:
        try:
            measured = _walk(documents[claim.receipt], claim.path, receipt_key=claim.receipt)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{claim.claim_id}: {exc}")
            continue
        if not isinstance(measured, str) or claim.substring not in measured:
            failures.append(
                f"{claim.claim_id} ({claim.receipt} - {claim.path}): "
                f"{claim.substring!r} not present in {measured!r}"
            )
    if failures:
        raise ScoreboardVerificationError(
            "receipt substring verification failed:\n  " + "\n  ".join(failures)
        )
    return {"substring_claims_verified": len(SUBSTRING_CLAIMS)}


def verify_document_claims(texts: Mapping[str, str]) -> dict[str, Any]:
    """Assert, verbatim, the sentences that carry the tier-D quantities."""

    failures: list[str] = []
    for claim in DOCUMENT_CLAIMS:
        text = texts[claim.document]
        if claim.substring not in text:
            failures.append(f"{claim.claim_id} ({claim.document}): {claim.substring!r} absent")
    if failures:
        raise ScoreboardVerificationError(
            "document (tier D) verification failed:\n  " + "\n  ".join(failures)
        )
    return {"document_claims_verified": len(DOCUMENT_CLAIMS)}


def run(*, repo_root: Path, out_path: Path | None = None) -> dict[str, Any]:
    """Arm the guard, verify every digest, then every carried number."""

    attempts = arm_offline_guard()

    artifacts_block = verify_artifacts(repo_root)
    receipts = load_receipts(repo_root)
    texts = load_documents(repo_root)
    claims_block = verify_claims(receipts)
    substring_block = verify_substring_claims(receipts)
    document_block = verify_document_claims(texts)

    scoreboard = repo_root / SCOREBOARD_RELPATH
    scoreboard_block: dict[str, Any] = {
        "relpath": SCOREBOARD_RELPATH,
        "present": scoreboard.is_file(),
    }
    if scoreboard.is_file():
        scoreboard_block["sha256"] = sha256_of(scoreboard)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "what_this_proves": (
            "FAITHFULNESS ONLY: every number scoreboard v5 carries is the number its own "
            "source artifact holds, at the JSON path (tier R) or in the verbatim sentence "
            "(tier D) named here. It proves nothing about whether those artifacts are "
            "right -- that is each landed row's own business -- and it computes no new "
            "experimental quantity."
        ),
        "offline_guard": {
            "armed_before_first_input": True,
            "outbound_connection_attempts": attempts.count,
            "targets": list(attempts.targets),
            "resident_llama_server": (
                "pid 38623 port 8090 treated as COLD: not started, stopped, probed, "
                "reconfigured or contacted"
            ),
        },
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "new_dependencies": 0,
            "gold_labels_opened": 0,
        },
        "float_tolerance": FLOAT_TOLERANCE,
        "scoreboard_document": scoreboard_block,
        **artifacts_block,
        **claims_block,
        **substring_block,
        **document_block,
        "reading_rules_enforced": [
            "POPULATION and WHERE-DELIVERED figures never share a column.",
            "MATCHING and EXTRACTION are separate columns; an unmeasured axis is EMPTY.",
            "Every SLURP unexposed-500 figure is a SECONDARY READING on the locked "
            "baseline's own population and revises nothing about the LOCK (d9fef537).",
            "Small-n cells are MECHANISM READINGS, never effect sizes.",
            "The test split (FINAL60) is untouched and is named by no row.",
        ],
        "hard_stop": (
            "DOCUMENTATION TIER. This module changes no knob, writes nothing under "
            "configs/, rails/ or core/, opens no sealed run directory, authorizes no "
            "flight and reaches no new empirical verdict."
        ),
    }

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n" explicitly: this module runs on both Windows and WSL and
        # the receipt is hashed by its bytes, so the bytes must not depend on
        # which side wrote it.
        out_path.write_text(
            json.dumps(report, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="scoreboard v5 verification")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = run(
        repo_root=Path(args.repo_root),
        out_path=Path(args.out) if args.out else None,
    )
    print(
        json.dumps(
            {
                "receipts_verified": report["receipts_verified"],
                "documents_verified": report["documents_verified"],
                "claims_verified": report["claims_verified"],
                "substring_claims_verified": report["substring_claims_verified"],
                "document_claims_verified": report["document_claims_verified"],
                "outbound_connection_attempts": report["offline_guard"][
                    "outbound_connection_attempts"
                ],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
