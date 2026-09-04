"""Part D step 2 (2026-09-03 recovery plan): re-issue the September Audio2Tool
verdicts under ``a2t-scorer-v2`` (:mod:`reproduction.toolcall_scoring_v2`),
zero model/tool/network/audio/GPU contact.

Model-free, read-only offline re-scoring of already-sealed ``outputs.jsonl``
files. This module never opens a model session, embedding service, tokenizer,
or network connection; it re-scores bytes that prior, separately-registered
runs already wrote, using the UNCHANGED v1 scorer
(:mod:`reproduction.toolcall_scoring`) side by side with the registered v2
scorer (:mod:`reproduction.toolcall_scoring_v2`, adopted from the slice-S1
zero-contact study, :mod:`analysis.a2t_scorer_v2_study`).

This is a SEPARATE, wider sweep than slice S1: S1 covered three sources (A0,
semantic-AgentLoop-104, select-fill-AgentLoop-104); this module adds every
other September Audio2Tool run with per-row final-answer outputs (the TFRL
cascades, the self-transcript/self-consistency training-free probes, and the
G-ladder mechanism runs), re-using the exact same v1/v2 scoring primitives.

Gold resolution
----------------
:func:`_resolve_gold` tries the STANDARD frozen-receipt gold map first
(``data.audio2tool.load_expected_calls``, built from the union of every
``docs/receipts/probe-samples/*.json`` receipt whose carrier is
``audio2tool`` -- the A0-400, semantic-104, and select-fill-104
populations). For a sample_id outside that map (every G-ladder/TFRL-cascade
run draws from ``A2T-CPV2-104`` or ``A2T-G1-104``, neither of which lives
under ``probe-samples/``), it falls back to a DIRECT on-disk tier-manifest
lookup: the same ``reproduction.toolcall_gold.expected_tool_calls_for_entry``
call over the same manifest entry ``data.audio2tool._resolve_items`` would
have hydrated, reached without needing that receipt's own selection metadata
-- provably byte-identical gold either way, since the receipt only chooses
WHICH (tier, id) pairs are wanted, never how a wanted pair's gold is parsed.
This is read-only re-scoring of ALREADY-EXPOSED sealed rows, not a new
exposure, so the receipt's pre-registration/authorization role does not
apply here.

Per-arm safety net
-------------------
:func:`rescore_arm` recomputes v1 aggregate numbers and, wherever a sealed
target is known, compares them (rounded to 4 decimals) against the sealed
summary before trusting the v2 numbers at all. A mismatch -- or any read/
gold/parse failure -- SKIPS the whole arm (never reports untrustworthy v2
numbers); :func:`run` records every skip under ``residuals``.

No function here performs import-time I/O; :func:`run`/:func:`main` are the
only places that touch the umbrella lock, the controlled data root, or the
committed sealed-summary docs, and :func:`run` refuses to overwrite an
existing ``summary.json`` (one-shot read discipline, matching
``analysis.a2t_scorer_v2_study``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, _tier_manifest, load_expected_calls, load_tool_registry
from ..data.lock import REPO_ROOT, asset_dir, data_root, load_lock, umbrella_lock_path
from ..e0.artifacts import write_json_artifact
from ..reproduction.toolcall_gold import GoldParseError, expected_tool_calls_for_entry
from ..reproduction.toolcall_scoring import (
    A2T_SCORER_VERSION,
    AggregateScore,
    ItemScore,
    aggregate,
    parse_tool_calls_text,
    score_item,
)
from ..reproduction.toolcall_scoring_v2 import (
    A2T_SCORER_V2_VERSION,
    AggregateScoreV2,
    ItemScoreV2,
    RegistryDefaults,
    RegistryDriftError,
    aggregate_v2,
    build_registry_defaults,
    score_item_v2,
)
from .paired import PairedContrast, paired_contrast

RESULT_SCHEMA = "saea-a2t-v2-rescore-v1"
_ROUND_DECIMALS = 4
_BOOTSTRAP_SEED = 20260903
_BOOTSTRAP_REPLICATES = 10_000
_CI_LEVEL = 0.90
_PAIRED_METRICS: tuple[str, ...] = (
    "v1_exact",
    "v1_tool",
    "v2_exact",
    "v2_tool_ordered",
    "v2_tool_multiset",
)


class RescoreError(RuntimeError):
    """The rescore run itself cannot proceed (refuse-overwrite, lock/root failure)."""


def _round4(value: float) -> float:
    return round(float(value), _ROUND_DECIMALS)


def _tier_of(sample_id: str) -> str:
    return sample_id.rsplit(":", 1)[0]


# ---------------------------------------------------------------------------
# Sealed v1 identity targets -- transcribed from the committed verdict docs
# and sealed summary JSON files named in the mission brief. Documentation
# only (never fabricated): every value below is the exact figure printed in
# the cited doc, used purely to VALIDATE this module's own independent
# re-read before its v2 numbers are trusted.
# ---------------------------------------------------------------------------

_A0_PER_TIER: dict[str, dict[str, float]] = {
    "tier1_direct": {"tool_accuracy": 0.5800, "exact_match": 0.1200},
    "tier2_parametric": {"tool_accuracy": 0.7200, "exact_match": 0.3800},
    "tier3_multi_intent": {"tool_accuracy": 0.6200, "exact_match": 0.0400},
    "tier4_implicit": {"tool_accuracy": 0.3000, "exact_match": 0.2400},
    "tier5_needle": {"tool_accuracy": 0.5400, "exact_match": 0.3000},
    "tier6_correction": {"tool_accuracy": 0.6400, "exact_match": 0.4000},
    "tier7_multiturn": {"tool_accuracy": 0.6000, "exact_match": 0.4400},
    "tier8_intent_blending": {"tool_accuracy": 0.3400, "exact_match": 0.0200},
}

# The paper's own per-tier row (arXiv:2604.22821 Table 3, tool_acc/EM),
# reproduced here verbatim from docs/checks/.../2026-09-03-a2t-scorer-v2-
# zero-contact-study/README.md for the readiness note's side-by-side table.
# Never a target this module checks against -- reference only.
PAPER_TIER_ROW: dict[str, dict[str, float]] = {
    "tier1_direct": {"tool_accuracy": 0.924, "exact_match": 0.924},
    "tier2_parametric": {"tool_accuracy": 0.846, "exact_match": 0.156},
    "tier3_multi_intent": {"tool_accuracy": 0.747, "exact_match": 0.286},
    "tier4_implicit": {"tool_accuracy": 0.334, "exact_match": 0.113},
    "tier5_needle": {"tool_accuracy": 0.906, "exact_match": 0.360},
    "tier6_correction": {"tool_accuracy": 0.815, "exact_match": 0.248},
    "tier7_multiturn": {"tool_accuracy": 0.546, "exact_match": 0.163},
    "tier8_intent_blending": {"tool_accuracy": 0.417, "exact_match": 0.124},
}


# ---------------------------------------------------------------------------
# ArmSpec / locate_arms.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmSpec:
    source: str
    arm: str
    run_id: str
    outputs_path: Path
    text_field: str
    roster_receipt: str
    target_overall: Mapping[str, float] | None = None
    target_per_tier: Mapping[str, Mapping[str, float]] | None = None


# (source, arm, run_id, relative outputs path under <data root>/runs/,
#  text field, roster_receipt note, sealed v1 tool_accuracy, sealed v1 exact_match)
_ARMS_TABLE: tuple[tuple[str, str, str, str, str, str, float, float], ...] = (
    (
        "a0", "zero_supply", "SAEA-BASE-a2t-a0-400",
        "SAEA-BASE-a2t-a0-400/attempt-20260818T055500Z-res315/outputs.jsonl",
        "response_text", "r1-audio2tool-sample.json (parent 400)",
        217 / 400, 97 / 400,
    ),
    (
        "semantic104", "direct_m0", "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/mission-20260903t190000z-semantic104-v1/"
        "zero-contact-recovery-v2/direct_m0/SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
        "text", "semantic-agentloop-104-postseal-scoring.json", 0.5096, 0.2404,
    ),
    (
        "semantic104", "transcript_top16_use", "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/mission-20260903t190000z-semantic104-v1/"
        "zero-contact-recovery-v2/transcript_top16_use/SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
        "text", "semantic-agentloop-104-postseal-scoring.json", 0.5962, 0.2596,
    ),
    (
        "semantic104", "model_query_top16_use", "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/mission-20260903t190000z-semantic104-v1/"
        "zero-contact-recovery-v2/model_query_top16_use/SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
        "text", "semantic-agentloop-104-postseal-scoring.json", 0.5769, 0.2308,
    ),
    (
        "semantic104", "rrf_fused_top16_use", "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/mission-20260903t190000z-semantic104-v1/"
        "zero-contact-recovery-v2/rrf_fused_top16_use/SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
        "text", "semantic-agentloop-104-postseal-scoring.json", 0.5769, 0.2404,
    ),
    (
        "semantic104", "same_stratum_shuffled_fused_use", "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1/mission-20260903t190000z-semantic104-v1/"
        "zero-contact-recovery-v2/same_stratum_shuffled_fused_use/"
        "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
        "text", "semantic-agentloop-104-postseal-scoring.json", 0.0865, 0.0385,
    ),
    (
        "selectfill104", "DIRECT_M0", "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5/"
        "mission-20260903t204700z-selectfill104-recovery-v5/recovered-direct-m0/"
        "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2.outputs.jsonl",
        "text", "select-fill-agentloop-104-postseal-scoring.json", 0.4038, 0.1731,
    ),
    (
        "selectfill104", "JOINT_ONE_CALL", "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5/"
        "mission-20260903t204700z-selectfill104-recovery-v5/zero-contact-seal-recovery-v1/"
        "joint_one_call/SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
        "text", "select-fill-agentloop-104-postseal-scoring.json", 0.6250, 0.2404,
    ),
    (
        "selectfill104", "JOINT_DRAFT_REVISE", "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5/"
        "mission-20260903t204700z-selectfill104-recovery-v5/zero-contact-seal-recovery-v1/"
        "joint_draft_revise/SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
        "text", "select-fill-agentloop-104-postseal-scoring.json", 0.6346, 0.2500,
    ),
    (
        "selectfill104", "SELECT_THEN_FILL", "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5/"
        "mission-20260903t204700z-selectfill104-recovery-v5/zero-contact-seal-recovery-v1/"
        "select_then_fill/SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
        "text", "select-fill-agentloop-104-postseal-scoring.json", 0.5962, 0.2500,
    ),
    (
        "cpv2", "M0", "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T223557Z/"
        "m0-direct/SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2.outputs.jsonl",
        "text", "A2T-CPV2-104.json (fresh 104, tier-manifest fallback)", 61 / 104, 32 / 104,
    ),
    (
        "cpv2", "matched", "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T225026Z/"
        "matched-composite/SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2.outputs.jsonl",
        "text", "A2T-CPV2-104.json (fresh 104, tier-manifest fallback)", 73 / 104, 40 / 104,
    ),
    (
        "cpv2", "shuffled", "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T230624Z/"
        "shuffled-recovery/complete-bundle/"
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2.outputs.jsonl",
        "text", "A2T-CPV2-104.json (fresh 104, tier-manifest fallback)", 51 / 104, 28 / 104,
    ),
    (
        "cpv2", "resend", "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T232133Z/"
        "resend-composite/SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2.outputs.jsonl",
        "text", "A2T-CPV2-104.json (fresh 104, tier-manifest fallback)", 72 / 104, 39 / 104,
    ),
    (
        "cpv2", "cross_fitted_policy", "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/policy-recovery-20260901T233025Z/"
        "policy-composite/SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2.outputs.jsonl",
        "text", "A2T-CPV2-104.json (fresh 104, tier-manifest fallback)", 59 / 104, 30 / 104,
    ),
    (
        "g1_m0_shared", "M0", "SAEA-A2T-G1",
        "SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl",
        "final_response_text", "A2T-G1-104 (shared M0 anchor, tier-manifest fallback)",
        62 / 104, 29 / 104,
    ),
    (
        "self_transcript_cascade", "USE_MATCHED", "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1",
        "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/flight-20260901T211135Z/"
        "matched-composite/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 0.0, 0.0,
    ),
    (
        "self_transcript_cascade", "USE_SHUFFLED_EVIDENCE", "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1",
        "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/flight-20260901T211135Z/"
        "shuffled-evidence-composite/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 0.0, 0.0,
    ),
    (
        "self_transcript_cascade", "MATCHED_RESEND_COMPOSITE", "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1",
        "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/flight-20260901T211135Z/"
        "resend-composite/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 0.0, 0.0,
    ),
    (
        "self_transcript_cascade", "CROSSFIT_POLICY", "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1",
        "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/flight-20260901T211135Z/"
        "policy-composite/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 62 / 104, 29 / 104,
    ),
    (
        "self_consistency", "REOBSERVE_DIRECT", "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1",
        "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T172514Z/"
        "reobserve-direct/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 55 / 104, 23 / 104,
    ),
    (
        "self_consistency", "SUPPLY_UNION_STRIPPED", "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1",
        "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T174317Z/"
        "supply-union-stripped/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1.outputs.jsonl",
        "text", "A2T-G1-104 (tier-manifest fallback)", 60 / 104, 23 / 104,
    ),
    (
        "g3", "m0", "SAEA-A2T-G3-PLAIN-ENGLISH-V1",
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T174427Z/m0/"
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1.outputs.jsonl",
        "text", "A2T-G3-PILOT-40.json (tier-manifest fallback)", 21 / 40, 8 / 40,
    ),
    (
        "g3", "matched", "SAEA-A2T-G3-PLAIN-ENGLISH-V1",
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T182038Z/matched/"
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1.outputs.jsonl",
        "text", "A2T-G3-PILOT-40.json (tier-manifest fallback)", 27 / 40, 8 / 40,
    ),
    (
        "g3", "shuffled", "SAEA-A2T-G3-PLAIN-ENGLISH-V1",
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T182038Z/shuffled/"
        "SAEA-A2T-G3-PLAIN-ENGLISH-V1.outputs.jsonl",
        "text", "A2T-G3-PILOT-40.json (tier-manifest fallback)", 24 / 40, 7 / 40,
    ),
    (
        "g5", "g5", "SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1",
        "SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1/flight-20260902T210832Z/g5/"
        "SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1.outputs.jsonl",
        "text", "A2T-G5-FIXED16-IDENTITY.json subset of A2T-G1-104 (tier-manifest fallback)",
        4 / 16, 3 / 16,
    ),
    (
        "g6", "g6_seal", "SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1",
        "SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1/flight-seal-20260902T222625Z/g6-seal/"
        "SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1.outputs.jsonl",
        "text", "A2T-G6-FAMILY-SWEEP-FIXED16.json subset of A2T-G1-104 (tier-manifest fallback)",
        0.0, 0.0,
    ),
    (
        "g7", "g7", "SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2",
        "SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2/flight-20260903T000610Z/g7/"
        "SAEA-A2T-G7-MULTIMODAL-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V2.outputs.jsonl",
        "text", "A2T-G7-EXAMPLE-FIXED16.json subset of A2T-G1-104 (tier-manifest fallback)",
        7 / 16, 3 / 16,
    ),
    (
        "g8c", "STOP_M0", "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1",
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1/flight-20260903T034314Z/g8c/"
        "branches/stop_m0/SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1.STOP_M0.outputs.jsonl",
        "text", "A2T-G8C-ACTION-SUPPORT-FIXED12.json subset of A2T-G1-104 (tier-manifest fallback)",
        10 / 12, 4 / 12,
    ),
    (
        "g8c", "EXHAUSTIVE_G7", "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1",
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1/flight-20260903T034314Z/g8c/"
        "branches/exhaustive_g7/"
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1.EXHAUSTIVE_G7.outputs.jsonl",
        "text", "A2T-G8C-ACTION-SUPPORT-FIXED12.json subset of A2T-G1-104 (tier-manifest fallback)",
        7 / 12, 1 / 12,
    ),
    (
        "g8c", "SUPPORT_ONLY_RESOLVE", "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1",
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1/flight-20260903T034314Z/g8c/"
        "branches/support_only_resolve/"
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1.SUPPORT_ONLY_RESOLVE.outputs.jsonl",
        "text", "A2T-G8C-ACTION-SUPPORT-FIXED12.json subset of A2T-G1-104 (tier-manifest fallback)",
        0.0, 0.0,
    ),
    (
        "g8c", "DECOMPOSED_SELECT_BIND_RESOLVE", "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1",
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1/flight-20260903T034314Z/g8c/"
        "branches/decomposed_select_bind_resolve/"
        "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1.DECOMPOSED_SELECT_BIND_RESOLVE.outputs.jsonl",
        "text", "A2T-G8C-ACTION-SUPPORT-FIXED12.json subset of A2T-G1-104 (tier-manifest fallback)",
        9 / 12, 1 / 12,
    ),
    (
        "native_structured", "REGISTRY_NO_SCHEMA", "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1",
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1/flight-20260903T013000Z/"
        "historical-subsets/REGISTRY_NO_SCHEMA/"
        "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1.historical-fixed8.outputs.jsonl",
        "text",
        "A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json subset of A2T-G1-104 (tier-manifest fallback)",
        0.0, 0.0,
    ),
    (
        "native_structured", "REGISTRY_STRICT_ACTION", "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1",
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1/flight-20260903T013000Z/"
        "registry_strict_action/SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1.outputs.jsonl",
        "text",
        "A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json subset of A2T-G1-104 (tier-manifest fallback)",
        4 / 8, 2 / 8,
    ),
    (
        "native_structured", "HANDBOOK_NO_SCHEMA", "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1",
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1/flight-20260903T013000Z/"
        "historical-subsets/HANDBOOK_NO_SCHEMA/"
        "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1.historical-fixed8.outputs.jsonl",
        "text",
        "A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json subset of A2T-G1-104 (tier-manifest fallback)",
        5 / 8, 1 / 8,
    ),
    (
        "native_structured", "HANDBOOK_STRICT_ACTION", "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1",
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1/flight-20260903T013000Z/"
        "handbook_strict_action_recovery_v2/"
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2.outputs.jsonl",
        "text",
        "A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json subset of A2T-G1-104 (tier-manifest fallback)",
        3 / 8, 1 / 8,
    ),
)

# Per-source, per-tier v1 identity targets -- only A0 has a committed
# per-tier sealed table; every other source is checked overall-only (the
# September flights' own sealed summaries carry overall numbers only).
_PER_TIER_TARGETS: dict[tuple[str, str], Mapping[str, Mapping[str, float]]] = {
    ("a0", "zero_supply"): _A0_PER_TIER,
}

# (baseline_source, baseline_arm, treatment_source, treatment_arm) -- every
# paired contrast this module computes. A pairing whose baseline lives in a
# DIFFERENT source (the shared "g1_m0_shared"/"M0" anchor) reuses that one
# scored file rather than re-scoring it once per consumer.
PAIRINGS: tuple[tuple[str, str, str, str], ...] = (
    ("semantic104", "direct_m0", "semantic104", "transcript_top16_use"),
    ("semantic104", "direct_m0", "semantic104", "model_query_top16_use"),
    ("semantic104", "direct_m0", "semantic104", "rrf_fused_top16_use"),
    ("semantic104", "direct_m0", "semantic104", "same_stratum_shuffled_fused_use"),
    ("selectfill104", "DIRECT_M0", "selectfill104", "JOINT_ONE_CALL"),
    ("selectfill104", "DIRECT_M0", "selectfill104", "JOINT_DRAFT_REVISE"),
    ("selectfill104", "DIRECT_M0", "selectfill104", "SELECT_THEN_FILL"),
    ("cpv2", "M0", "cpv2", "matched"),
    ("cpv2", "M0", "cpv2", "shuffled"),
    ("cpv2", "M0", "cpv2", "resend"),
    ("cpv2", "M0", "cpv2", "cross_fitted_policy"),
    ("g1_m0_shared", "M0", "self_transcript_cascade", "USE_MATCHED"),
    ("g1_m0_shared", "M0", "self_transcript_cascade", "USE_SHUFFLED_EVIDENCE"),
    ("g1_m0_shared", "M0", "self_transcript_cascade", "MATCHED_RESEND_COMPOSITE"),
    ("g1_m0_shared", "M0", "self_transcript_cascade", "CROSSFIT_POLICY"),
    ("g1_m0_shared", "M0", "self_consistency", "REOBSERVE_DIRECT"),
    ("g1_m0_shared", "M0", "self_consistency", "SUPPLY_UNION_STRIPPED"),
    ("g3", "m0", "g3", "matched"),
    ("g3", "m0", "g3", "shuffled"),
    ("g1_m0_shared", "M0", "g5", "g5"),
    ("g1_m0_shared", "M0", "g6", "g6_seal"),
    ("g1_m0_shared", "M0", "g7", "g7"),
    ("g8c", "STOP_M0", "g8c", "EXHAUSTIVE_G7"),
    ("g8c", "STOP_M0", "g8c", "SUPPORT_ONLY_RESOLVE"),
    ("g8c", "STOP_M0", "g8c", "DECOMPOSED_SELECT_BIND_RESOLVE"),
    ("native_structured", "REGISTRY_NO_SCHEMA", "native_structured", "REGISTRY_STRICT_ACTION"),
    ("native_structured", "HANDBOOK_NO_SCHEMA", "native_structured", "HANDBOOK_STRICT_ACTION"),
)

# Runs named in the mission brief's read-first sweep that carry NO owned
# verdict doc to append to and were not scored here -- listed so the
# readiness note's residuals are complete without silently dropping them.
UNSCORED_RUNS: tuple[str, ...] = (
    "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1: has a findable "
    "outputs.jsonl per arm (m0-registry-direct, g1-full-executable-ground) "
    "but no verdict doc is listed in this task's ownership scope and its "
    "sealed aggregate could not be matched with certainty in the time "
    "budget available; not attempted.",
    "SAEA-A2T-CONSTRUCTION-SEMANTIC-GROUND-DIAGNOSTIC-104-V1: result-summary.json "
    "reports g1/g2 counts (19, 4) whose n and role are not self-evident from "
    "that file alone (not simply /104 against the A2T-G1-104 baseline), and no "
    "verdict doc is listed in this task's ownership scope; not attempted.",
)


def locate_arms(data_root: Path, *, repo_root: Path | None = None) -> list[ArmSpec]:
    """Every arm this module knows how to re-score, with its sealed v1
    overall identity target and (for A0 only) per-tier targets.

    ``repo_root`` is accepted for signature symmetry with the rest of this
    study's modules; only ``data_root`` feeds this function's own path
    construction (every path below is ``<data_root>/runs/...``).
    """

    del repo_root  # not needed for path construction; kept for symmetry
    root = Path(data_root)
    runs_dir = root / "runs"
    specs: list[ArmSpec] = []
    for source, arm, run_id, rel_path, text_field, roster_receipt, tool_acc, exact_match in _ARMS_TABLE:
        specs.append(
            ArmSpec(
                source=source,
                arm=arm,
                run_id=run_id,
                outputs_path=runs_dir / rel_path,
                text_field=text_field,
                roster_receipt=roster_receipt,
                target_overall={"tool_accuracy": tool_acc, "exact_match": exact_match},
                target_per_tier=_PER_TIER_TARGETS.get((source, arm)),
            )
        )
    return specs


# ---------------------------------------------------------------------------
# Gold resolution: standard frozen-receipt map, falling back to a direct
# on-disk tier-manifest lookup for a sample_id outside that map.
# ---------------------------------------------------------------------------


def _resolve_gold(
    sample_id: str,
    standard_gold: Mapping[str, Sequence[object]],
    manifest_cache: dict[str, Mapping[int, Mapping[str, object]]],
    public_dir: Path,
) -> tuple[object, ...] | None:
    gold = standard_gold.get(sample_id)
    if gold is not None:
        return tuple(gold)
    tier, sep, id_text = sample_id.rpartition(":")
    if not sep or not tier or not id_text:
        return None
    try:
        item_id = int(id_text)
    except ValueError:
        return None
    manifest = manifest_cache.get(tier)
    if manifest is None:
        try:
            manifest = _tier_manifest(public_dir, tier)
        except Exception:  # noqa: BLE001 -- fail-closed to "no gold", never crash the arm
            return None
        manifest_cache[tier] = manifest
    entry = manifest.get(item_id)
    if entry is None:
        return None
    try:
        return expected_tool_calls_for_entry(entry)
    except GoldParseError:
        return None


# ---------------------------------------------------------------------------
# ArmResult / rescore_arm.
# ---------------------------------------------------------------------------


def _v1_view(score: AggregateScore) -> dict[str, object]:
    return {
        "n": score.n_items,
        "tool_accuracy": score.tool_accuracy,
        "exact_match": score.exact_match,
        "slot_precision": score.slot_precision,
        "slot_recall": score.slot_recall,
        "slot_f1": score.slot_f1,
    }


def _v2_view(score: AggregateScoreV2) -> dict[str, object]:
    return {
        "n": score.n_items,
        "tool_accuracy_ordered": score.tool_accuracy_ordered,
        "tool_accuracy_multiset": score.tool_accuracy_multiset,
        "exact_match": score.exact_match,
        "slot_precision": score.slot_precision,
        "slot_recall": score.slot_recall,
        "slot_f1": score.slot_f1,
        "slot_f1_raw": score.slot_f1_raw,
    }


def _identity_check(
    v1_overall: Mapping[str, object],
    v1_per_tier: Mapping[str, Mapping[str, object]],
    target_overall: Mapping[str, float] | None,
    target_per_tier: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, object]:
    mismatches: list[dict[str, object]] = []
    for key, expected_value in (target_overall or {}).items():
        actual_value = v1_overall.get(key)
        if actual_value is None or _round4(actual_value) != _round4(expected_value):
            mismatches.append(
                {"scope": "overall", "field": key, "expected": expected_value, "actual": actual_value}
            )
    for tier, targets in (target_per_tier or {}).items():
        actual_tier = v1_per_tier.get(tier)
        if actual_tier is None:
            mismatches.append({"scope": tier, "field": "presence", "expected": "present", "actual": "missing"})
            continue
        for key, expected_value in targets.items():
            actual_value = actual_tier.get(key)
            if actual_value is None or _round4(actual_value) != _round4(expected_value):
                mismatches.append(
                    {"scope": tier, "field": key, "expected": expected_value, "actual": actual_value}
                )
    return {
        "checked": bool(target_overall or target_per_tier),
        "match": not mismatches,
        "mismatches": mismatches,
    }


@dataclass(frozen=True)
class ArmResult:
    source: str
    arm: str
    run_id: str
    outputs_path: str
    text_field: str
    skipped: bool
    skip_reason: str | None
    n_rows: int
    identity: Mapping[str, object] | None
    v1_overall: Mapping[str, object] | None
    v2_overall: Mapping[str, object] | None
    v1_per_tier: Mapping[str, Mapping[str, object]] | None
    v2_per_tier: Mapping[str, Mapping[str, object]] | None
    per_sample: Mapping[str, Mapping[str, float]]
    per_row: tuple[Mapping[str, object], ...]


def _skip(spec: ArmSpec, reason: str) -> ArmResult:
    return ArmResult(
        source=spec.source,
        arm=spec.arm,
        run_id=spec.run_id,
        outputs_path=str(spec.outputs_path),
        text_field=spec.text_field,
        skipped=True,
        skip_reason=reason,
        n_rows=0,
        identity=None,
        v1_overall=None,
        v2_overall=None,
        v1_per_tier=None,
        v2_per_tier=None,
        per_sample={},
        per_row=(),
    )


def rescore_arm(
    spec: ArmSpec,
    lock: Mapping[str, object],
    root: Path,
    *,
    standard_gold: Mapping[str, Sequence[object]],
    registry_defaults: RegistryDefaults,
    manifest_cache: dict[str, Mapping[int, Mapping[str, object]]],
    public_dir: Path,
) -> ArmResult:
    """One arm's v1 identity check plus v1/v2 aggregate, per-tier, and
    per-row scores. Returns a SKIPPED result (never raises) for any read,
    gold, parse, or v1-identity failure -- the caller decides what to do
    with a skip; this function's job is only to never report untrustworthy
    v2 numbers past a failed check."""

    del lock  # gold/registry are already resolved by the caller; kept for signature symmetry
    try:
        text = Path(spec.outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return _skip(spec, f"cannot read outputs {spec.outputs_path}: {error}")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        return _skip(spec, f"outputs file {spec.outputs_path} is empty")

    v1_items: list[ItemScore] = []
    v2_items: list[ItemScoreV2] = []
    v1_by_tier: dict[str, list[ItemScore]] = {}
    v2_by_tier: dict[str, list[ItemScoreV2]] = {}
    per_sample: dict[str, dict[str, float]] = {}
    per_row: list[dict[str, object]] = []
    seen: set[str] = set()

    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            return _skip(spec, f"{spec.outputs_path} line {number} malformed: {error}")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            return _skip(spec, f"{spec.outputs_path} line {number} lacks a sample_id")
        if sample_id in seen:
            return _skip(spec, f"{spec.outputs_path} has a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        text_value = row.get(spec.text_field)
        if not isinstance(text_value, str):
            return _skip(
                spec, f"{spec.outputs_path} line {number} ({sample_id}) lacks {spec.text_field!r}"
            )
        expected = _resolve_gold(sample_id, standard_gold, manifest_cache, public_dir)
        if expected is None:
            return _skip(spec, f"no gold resolvable for {sample_id!r} in {spec.outputs_path}")

        predicted, parsed = parse_tool_calls_text(text_value)
        v1_item = score_item(expected, predicted)
        try:
            v2_item = score_item_v2(expected, predicted, registry_defaults=registry_defaults)
        except RegistryDriftError as error:
            return _skip(spec, f"registry drift at {sample_id!r}: {error}")

        tier = _tier_of(sample_id)
        v1_items.append(v1_item)
        v2_items.append(v2_item)
        v1_by_tier.setdefault(tier, []).append(v1_item)
        v2_by_tier.setdefault(tier, []).append(v2_item)
        per_sample[sample_id] = {
            "v1_exact": v1_item.exact_match,
            "v1_tool": v1_item.tool_accuracy,
            "v2_exact": v2_item.exact_match,
            "v2_tool_ordered": v2_item.tool_accuracy_ordered,
            "v2_tool_multiset": v2_item.tool_accuracy_multiset,
        }
        per_row.append(
            {
                "run": spec.run_id,
                "source": spec.source,
                "arm": spec.arm,
                "sample_id": sample_id,
                "tier": tier,
                "v1_exact": v1_item.exact_match,
                "v1_tool": v1_item.tool_accuracy,
                "v2_exact": v2_item.exact_match,
                "v2_tool_ordered": v2_item.tool_accuracy_ordered,
                "v2_tool_multiset": v2_item.tool_accuracy_multiset,
                "parsed": parsed,
            }
        )

    if not v1_items:
        return _skip(spec, f"{spec.outputs_path} produced zero scoreable rows")

    v1_overall = _v1_view(aggregate(v1_items))
    v2_overall = _v2_view(aggregate_v2(v2_items))
    v1_per_tier = {tier: _v1_view(aggregate(items)) for tier, items in sorted(v1_by_tier.items())}
    v2_per_tier = {tier: _v2_view(aggregate_v2(items)) for tier, items in sorted(v2_by_tier.items())}

    identity = _identity_check(v1_overall, v1_per_tier, spec.target_overall, spec.target_per_tier)
    if identity["checked"] and not identity["match"]:
        return _skip(spec, f"v1 identity mismatch against sealed target: {identity['mismatches']}")

    return ArmResult(
        source=spec.source,
        arm=spec.arm,
        run_id=spec.run_id,
        outputs_path=str(spec.outputs_path),
        text_field=spec.text_field,
        skipped=False,
        skip_reason=None,
        n_rows=len(v1_items),
        identity=identity,
        v1_overall=v1_overall,
        v2_overall=v2_overall,
        v1_per_tier=v1_per_tier,
        v2_per_tier=v2_per_tier,
        per_sample=per_sample,
        per_row=tuple(per_row),
    )


# ---------------------------------------------------------------------------
# paired_contrasts.
# ---------------------------------------------------------------------------


def paired_contrasts(
    results: Sequence[ArmResult],
    *,
    seed: int = _BOOTSTRAP_SEED,
    n_replicates: int = _BOOTSTRAP_REPLICATES,
    ci_level: float = _CI_LEVEL,
) -> dict[str, dict[str, object]]:
    """Every :data:`PAIRINGS` entry whose baseline and treatment arms both
    scored cleanly, as a paired v1-and-v2 contrast (``analysis.paired.
    paired_contrast``, seed 20260903, 10,000 replicates, CI90, strata = tier
    parsed from sample_id). A pairing whose baseline or treatment is missing
    or skipped is recorded skipped with its reason, never silently dropped.
    """

    by_key = {(result.source, result.arm): result for result in results}
    out: dict[str, dict[str, object]] = {}
    for baseline_source, baseline_arm, treat_source, treat_arm in PAIRINGS:
        key = f"{treat_source}/{treat_arm}_vs_{baseline_source}/{baseline_arm}"
        baseline = by_key.get((baseline_source, baseline_arm))
        treatment = by_key.get((treat_source, treat_arm))
        if baseline is None or treatment is None:
            out[key] = {"skipped": True, "reason": "baseline or treatment arm was never scored"}
            continue
        if baseline.skipped or treatment.skipped:
            out[key] = {
                "skipped": True,
                "reason": (
                    f"baseline skipped ({baseline.skip_reason})"
                    if baseline.skipped
                    else f"treatment skipped ({treatment.skip_reason})"
                ),
            }
            continue
        treat_ids = tuple(sorted(treatment.per_sample))
        missing = [sid for sid in treat_ids if sid not in baseline.per_sample]
        if missing:
            out[key] = {
                "skipped": True,
                "reason": f"{len(missing)} treatment sample id(s) absent from baseline per-sample map",
            }
            continue
        contrasts = paired_contrast(
            baseline.per_sample,
            treatment.per_sample,
            metrics=_PAIRED_METRICS,
            sample_ids=treat_ids,
            strata_of=_tier_of,
            seed=seed,
            n_replicates=n_replicates,
            ci_level=ci_level,
        )
        out[key] = {"skipped": False, "contrasts": contrasts}
    return out


def _contrast_row(name: str, contrast: PairedContrast) -> str:
    ci_low = f"{contrast.bootstrap.ci_low:.4f}" if contrast.bootstrap is not None else ""
    ci_high = f"{contrast.bootstrap.ci_high:.4f}" if contrast.bootstrap is not None else ""
    return (
        f"| {name} | {contrast.n} | {contrast.left_mean:.4f} | {contrast.right_mean:.4f} | "
        f"{contrast.delta:+.4f} | {contrast.saves} | {contrast.harms} | {contrast.ties} | "
        f"[{ci_low}, {ci_high}] |"
    )


# ---------------------------------------------------------------------------
# run() / README rendering / CLI.
# ---------------------------------------------------------------------------


def _render_readme(results: Sequence[ArmResult], contrasts: Mapping[str, Mapping[str, object]]) -> str:
    lines: list[str] = []
    lines.append("# a2t-scorer-v2 re-score of the September Audio2Tool runs (2026-09-03)")
    lines.append("")
    lines.append(
        "Model-free, read-only offline re-scoring of already-sealed `outputs.jsonl` files "
        "under the registered `a2t-scorer-v2` (`reproduction.toolcall_scoring_v2`), reported "
        "side by side with the unchanged v1 scorer. Zero model/tool/network/audio/GPU contact."
    )
    lines.append("")
    lines.append(f"Scorer versions: `{A2T_SCORER_VERSION}` (v1, unchanged) / `{A2T_SCORER_V2_VERSION}` (v2).")
    lines.append("")
    lines.append(
        "## Per-arm table (v1 identity check, then v1 and v2 aggregate; exact / tool ordered / "
        "tool multiset / slot F1 / parse)"
    )
    lines.append("")
    lines.append(
        "| source/arm | run | n | identity | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | "
        "v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for result in results:
        key = f"{result.source}/{result.arm}"
        if result.skipped:
            lines.append(f"| {key} | {result.run_id} | -- | SKIPPED | -- | -- | -- | -- | -- | -- | -- | -- |")
            continue
        identity_text = "match" if result.identity and result.identity["match"] else "unchecked"
        v1o = result.v1_overall or {}
        v2o = result.v2_overall or {}
        parse_rate = (
            sum(1 for row in result.per_row if row["parsed"]) / len(result.per_row)
            if result.per_row
            else 0.0
        )
        lines.append(
            f"| {key} | {result.run_id} | {result.n_rows} | {identity_text} | "
            f"{v1o.get('exact_match', 0.0):.4f} | {v1o.get('tool_accuracy', 0.0):.4f} | "
            f"{v2o.get('exact_match', 0.0):.4f} | {v2o.get('tool_accuracy_ordered', 0.0):.4f} | "
            f"{v2o.get('tool_accuracy_multiset', 0.0):.4f} | {v2o.get('slot_f1', 0.0):.4f} | "
            f"{v1o.get('slot_f1', 0.0):.4f} | {parse_rate:.4f} |"
        )
    lines.append("")

    lines.append("## Paired contrasts vs. each run's direct baseline (v1 and v2, CI90, 10,000 replicates)")
    lines.append("")
    for pairing_key in sorted(contrasts):
        payload = contrasts[pairing_key]
        lines.append(f"### {pairing_key}")
        lines.append("")
        if payload["skipped"]:
            lines.append(f"SKIPPED -- {payload['reason']}")
            lines.append("")
            continue
        lines.append("| metric | n | left_mean | right_mean | delta | saves | harms | ties | CI90 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for metric_name, contrast in payload["contrasts"].items():
            lines.append(_contrast_row(metric_name, contrast))
        lines.append("")

    residuals = [f"{r.source}/{r.arm}: {r.skip_reason}" for r in results if r.skipped]
    lines.append("## Residuals (skipped arms)")
    lines.append("")
    if residuals:
        for note in residuals:
            lines.append(f"- {note}")
    else:
        lines.append("- none")
    lines.append("")
    for note in UNSCORED_RUNS:
        lines.append(f"- (not attempted) {note}")
    lines.append("")
    return "\n".join(lines)


def run(
    *,
    repo_root: Path | None = None,
    output_dir: Path | None = None,
    data_root_override: Path | None = None,
) -> dict[str, object]:
    """Locate every known arm, re-score it under v1 and v2, compute the
    registered paired contrasts, and write ``summary.json`` / ``per_arm.jsonl``
    / ``README.md`` under ``output_dir``. Refuses to overwrite an existing
    ``summary.json`` (one-shot read discipline)."""

    repo = Path(REPO_ROOT if repo_root is None else repo_root)
    root = Path(data_root_override) if data_root_override is not None else data_root()
    out_dir = (
        Path(output_dir)
        if output_dir is not None
        else repo
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-scorer-v2-rescore"
    )

    summary_path = out_dir / "summary.json"
    if summary_path.exists():
        raise RescoreError(
            f"{summary_path} already exists -- this rescore refuses to run twice against the "
            "same output dir (one-shot read discipline); choose a fresh output_dir if a "
            "genuinely new read is intended"
        )

    lock = load_lock(umbrella_lock_path(repo))
    standard_gold = load_expected_calls(lock, root, repo_root=repo)
    registry_defaults = build_registry_defaults(load_tool_registry(lock, root))
    public_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / "public"
    manifest_cache: dict[str, Mapping[int, Mapping[str, object]]] = {}

    specs = locate_arms(root, repo_root=repo)
    results = [
        rescore_arm(
            spec,
            lock,
            root,
            standard_gold=standard_gold,
            registry_defaults=registry_defaults,
            manifest_cache=manifest_cache,
            public_dir=public_dir,
        )
        for spec in specs
    ]
    contrasts = paired_contrasts(results)

    out_dir.mkdir(parents=True, exist_ok=True)
    per_arm_path = out_dir / "per_arm.jsonl"
    with per_arm_path.open("w", encoding="utf-8", newline="\n") as handle:
        for result in results:
            for row in result.per_row:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary_payload: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "scorer_v1_version": A2T_SCORER_VERSION,
        "scorer_v2_version": A2T_SCORER_V2_VERSION,
        "arms": {
            f"{result.source}/{result.arm}": {
                "run_id": result.run_id,
                "outputs_path": result.outputs_path,
                "text_field": result.text_field,
                "skipped": result.skipped,
                "skip_reason": result.skip_reason,
                "n_rows": result.n_rows,
                "identity": result.identity,
                "v1_overall": result.v1_overall,
                "v2_overall": result.v2_overall,
                "v1_per_tier": result.v1_per_tier,
                "v2_per_tier": result.v2_per_tier,
            }
            for result in results
        },
        "paired_contrasts": {
            key: (
                {"skipped": True, "reason": payload["reason"]}
                if payload["skipped"]
                else {
                    "skipped": False,
                    "contrasts": {
                        metric_name: contrast.as_dict() for metric_name, contrast in payload["contrasts"].items()
                    },
                }
            )
            for key, payload in contrasts.items()
        },
        "residuals": [f"{r.source}/{r.arm}: {r.skip_reason}" for r in results if r.skipped],
        "unscored_runs": list(UNSCORED_RUNS),
        "per_arm_count": sum(len(r.per_row) for r in results),
    }
    summary_sha = write_json_artifact(summary_path, summary_payload)

    readme_path = out_dir / "README.md"
    readme_path.write_text(_render_readme(results, contrasts), encoding="utf-8", newline="\n")

    return {
        "summary_path": summary_path,
        "summary_sha256": summary_sha,
        "per_arm_path": per_arm_path,
        "readme_path": readme_path,
        "results": results,
        "contrasts": contrasts,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="a2t-v2-rescore",
        description=(
            "Re-score every located September Audio2Tool run's sealed outputs.jsonl under "
            "a2t-scorer-v2, side by side with the unchanged v1 scorer; write summary.json, "
            "per_arm.jsonl and README.md. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=None, help="TEST-ONLY override")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--data-root", type=Path, default=None, help="TEST-ONLY override")
    args = parser.parse_args(argv)

    try:
        result = run(
            repo_root=args.repo_root,
            output_dir=args.output_dir,
            data_root_override=args.data_root,
        )
    except RescoreError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    print(f"wrote {result['summary_path']} sha256={result['summary_sha256']}")
    print(f"wrote {result['per_arm_path']}")
    print(f"wrote {result['readme_path']}")
    residuals = [r for r in result["results"] if r.skipped]
    if residuals:
        print("residuals:")
        for entry in residuals:
            print(f"  {entry.source}/{entry.arm}: {entry.skip_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
