"""Run the frozen 104-sample executable-ground qualification experiment."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.analysis.bootstrap import (  # noqa: E402
    paired_cluster_bootstrap,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS,
    RunResult,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.scoring_batch import (  # noqa: E402
    ScoreJob,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import (  # noqa: E402
    VerifiedSplit,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_expected_calls,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.probes import (  # noqa: E402
    a2t_executable_ground_qualification_flight as ground_flight,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_bundle import (  # noqa: E402
    canonical_payload_bytes,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (  # noqa: E402
    M0_DIRECT_PHASE,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_phase_bundle_material,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
    score_item,
)


RUN_ID = "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1"
RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-ground-qual-104"
BASELINE_FRAGMENT = "a2t-executable-ground-qualification"
EXPERIMENT_FRAGMENT = "a2t-executable-ground-qualification-104-v1"

COMPOSED_CONFIG_SHA256 = (
    "60b896eea441e94cc6570e5721303762b88da388d0ddc987a6a7b65cdeca8dda"
)
PROTOCOL_SHA256 = (
    "82680b0bc909a0c6f3f88f87ce4bd815feecdeff03a694e79e8456acc63dc33b"
)
SPLIT_IDENTITY_SHA256 = (
    "fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b"
)
RECEIPT_IDENTITY_SHA256 = (
    "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
)

SPLIT_COUNT = 104
SPLIT_AUDIO_SECONDS = 543.107
GGUF_DECLARED_CONTEXT_TOKENS = 65536
SERVER_CONTEXT_TOKENS = 65536
SERVER_SLOT_COUNT = 2
CONTEXT_TOKENS_PER_SLOT = 32768
CANONICAL_TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-GROUND-QUAL-104.json")
RECEIPT_SHA256 = (
    "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
)
ROSTER_RESULT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-qualification-104-v1-roster/"
    "roster-result.json"
)
ROSTER_RESULT_SHA256 = (
    "577184e7b189c2dba1471435e99a8a7ec873787b887af66824e6f68a7829c0c5"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)
LLAMA_CPP_BUILD_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
DECODER_GGUF_SHA256 = (
    "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
)

HANDBOOK_RELPATH = Path("knowledge/audio2tool/executable-ground-v1/handbook.txt")
HANDBOOK_SHA256 = (
    "58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8"
)
HANDBOOK_UTF8_BYTES = 54881
HANDBOOK_BUILD_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-build-v1/build-receipt.json"
)
HANDBOOK_BUILD_SHA256 = (
    "505645b3cdef553ac847a5b248936182160d7b38aaaac84a076b9137c8e40e34"
)
REGISTRY_SHA256 = (
    "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
)

PROMOTION_RECEIPT = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/"
    "A2T-GROUND-QUAL-104-promotion.json"
)
PROMOTION_SHA256 = (
    "b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f"
)
PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-468-v1/"
    "prompt-fit-result.json"
)
PROMPT_FIT_SHA256 = (
    "277f5147b8ce1ac9acca538e4b8a83a2c5b282c62f278afd56e27c9fd61a2fd5"
)

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "schema": "saea-a2t-ground-qualification-score-plan-v1",
    "entrypoint": "scripts/evaluate_parallel.sh",
    "operation": "finalize",
    "workers": 2,
    "official_scorer_modified": False,
    "processes_per_job": 1,
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "m0-registry-direct",
            "arm": ground_flight.REGISTRY_DIRECT,
            "input": "one complete 104-row manifest",
            "row_count": 104,
        },
        {
            "job_id": "g1-full-executable-ground",
            "arm": ground_flight.FULL_EXECUTABLE_GROUND,
            "input": "one complete 104-row manifest",
            "row_count": 104,
        },
    ],
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read governed JSON object {path}: {error}") from error
    if not isinstance(document, dict):
        raise RuntimeError(f"governed JSON document must be an object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _require_file_hash(path: Path, expected: str, label: str) -> None:
    try:
        measured = _sha256_file(path)
    except OSError as error:
        raise RuntimeError(f"cannot read governed {label}: {path}: {error}") from error
    if measured != expected:
        raise RuntimeError(
            f"{label} SHA-256 drift: expected {expected}, measured {measured}"
        )


def _execution_plan(attempt_id: str) -> ExecutionPlan:
    """Encode the exact preregistered run-level authority."""

    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_SHA256,
        planned_model_calls=230,
        planned_gpu_hours=0.7,
        planned_speech_audio_seconds=1300,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def _validate_roster(receipt: Mapping[str, object]) -> dict[str, object]:
    """Validate the complete runtime-legal receipt without reading annotations."""

    items = receipt.get("items")
    if (
        receipt.get("count") != SPLIT_COUNT
        or receipt.get("run_identity_hash") != SPLIT_IDENTITY_SHA256
        or receipt.get("split_identity_hash") != RECEIPT_IDENTITY_SHA256
        or not isinstance(items, list)
        or len(items) != SPLIT_COUNT
    ):
        raise RuntimeError("governed roster identity or count drift")
    try:
        seconds = float(receipt.get("audio_seconds_total", -1))
    except (TypeError, ValueError) as error:
        raise RuntimeError("governed roster audio duration is malformed") from error
    if abs(seconds - SPLIT_AUDIO_SECONDS) > 1e-9:
        raise RuntimeError("governed roster audio duration drift")

    sample_ids: list[str] = []
    packet_ids: list[str] = []
    tiers: dict[str, str] = {}
    query_blocks: list[str] = []
    for number, item in enumerate(items, start=1):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"governed roster item {number} is not an object")
        sample_id = item.get("sample_id")
        packet_id = item.get("packet_id")
        tier = item.get("tier")
        audio_sha256 = item.get("audio_sha256")
        media_relpath = item.get("media_relpath")
        query_block = item.get("query_block")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(packet_id, str)
            or not packet_id
            or not isinstance(tier, str)
            or not tier
            or not isinstance(audio_sha256, str)
            or len(audio_sha256) != 64
            or not isinstance(media_relpath, str)
            or not media_relpath.endswith(".wav")
        ):
            raise RuntimeError(f"governed roster item {number} is malformed")
        sample_ids.append(sample_id)
        packet_ids.append(packet_id)
        tiers[sample_id] = tier
        if query_block is not None:
            if not isinstance(query_block, str) or not query_block:
                raise RuntimeError(f"governed roster query block {number} is malformed")
            query_blocks.append(query_block)
    if len(set(sample_ids)) != SPLIT_COUNT:
        raise RuntimeError("governed roster requires 104 unique sample identities")
    if len(set(packet_ids)) != SPLIT_COUNT:
        raise RuntimeError("governed roster requires 104 unique packet identities")
    if query_blocks and len(set(query_blocks)) != SPLIT_COUNT:
        raise RuntimeError("governed roster requires 104 unique query blocks")
    tier_counts = dict(sorted(Counter(tiers.values()).items()))
    if set(tier_counts) == set(CANONICAL_TIERS):
        expected_tier_counts = {tier: 13 for tier in CANONICAL_TIERS}
    else:
        # Unit fixtures may use synthetic tier names, but the same frozen
        # eight-by-thirteen geometry still applies.
        expected_tier_counts = {tier: 13 for tier in sorted(tier_counts)}
    if len(tier_counts) != 8 or tier_counts != expected_tier_counts:
        raise RuntimeError("governed roster requires eight tiers with thirteen rows each")
    resend_ids = ground_flight.select_resend_ids(tiers)
    if len(resend_ids) != 16 or len(set(resend_ids)) != 16:
        raise RuntimeError("identity-only resend roster drift")
    return {
        "items": tuple(items),
        "sample_ids": tuple(sample_ids),
        "packet_ids": tuple(packet_ids),
        "sample_tiers": tiers,
        "tier_counts": tier_counts,
        "resend_ids": resend_ids,
    }


def _validate_server_geometry(values: Mapping[str, object]) -> dict[str, int]:
    arguments = values.get("server_args")
    if not isinstance(arguments, (list, tuple)):
        raise RuntimeError("server arguments must be a sequence")
    try:
        context = int(arguments[arguments.index("-c") + 1])
        slots = int(arguments[arguments.index("-np") + 1])
    except (ValueError, IndexError, TypeError) as error:
        raise RuntimeError("server arguments lack numeric -c/-np geometry") from error
    decoding = values.get("decoding_params")
    if (
        context != SERVER_CONTEXT_TOKENS
        or slots != SERVER_SLOT_COUNT
        or context // slots != CONTEXT_TOKENS_PER_SLOT
        or values.get("profile_slot_count") != SERVER_SLOT_COUNT
        or not isinstance(decoding, Mapping)
        or decoding.get("temperature") != 0
        or decoding.get("seed") != 20260803
        or decoding.get("max_tokens") != 1024
        or decoding.get("id_slot") != "per-sample"
    ):
        raise RuntimeError("serving must preserve exactly two 32768-token slots")
    return {
        "context_tokens": context,
        "slot_count": slots,
        "context_tokens_per_slot": context // slots,
    }


def _validate_official_score_plan(
    plan: Mapping[str, object],
) -> Mapping[str, object]:
    """Require two outer-parallel, whole-manifest official finalizers."""

    if (
        plan.get("schema") != "saea-a2t-ground-qualification-score-plan-v1"
        or plan.get("entrypoint") != "scripts/evaluate_parallel.sh"
        or plan.get("operation") != "finalize"
        or plan.get("workers") != 2
        or plan.get("official_scorer_modified") is not False
        or plan.get("processes_per_job") != 1
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
    ):
        raise RuntimeError("official scoring plan drift")
    jobs = plan.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 2:
        raise RuntimeError("official scoring requires exactly two complete manifests")
    expected = (
        ("m0-registry-direct", ground_flight.REGISTRY_DIRECT),
        ("g1-full-executable-ground", ground_flight.FULL_EXECUTABLE_GROUND),
    )
    for job, (job_id, arm) in zip(jobs, expected, strict=True):
        if (
            not isinstance(job, Mapping)
            or job.get("job_id") != job_id
            or job.get("arm") != arm
            or job.get("input") != "one complete 104-row manifest"
            or job.get("row_count") != SPLIT_COUNT
        ):
            raise RuntimeError(
                "every official score job must own one complete 104-row manifest"
            )
    return plan


def _official_a2t_surface(
    scores: Mapping[str, object], expected_ids: Sequence[str]
) -> dict[str, object]:
    scorer = scores.get("a2t-toolcall")
    if not isinstance(scorer, Mapping):
        raise RuntimeError("official score lacks the unchanged a2t-toolcall result")
    per_sample = scorer.get("per_sample")
    aggregate = scorer.get("aggregate")
    expected = tuple(expected_ids)
    if (
        len(expected) != SPLIT_COUNT
        or len(set(expected)) != SPLIT_COUNT
        or not isinstance(per_sample, list)
        or len(per_sample) != SPLIT_COUNT
        or not isinstance(aggregate, Mapping)
        or aggregate.get("samples") != SPLIT_COUNT
    ):
        raise RuntimeError("complete 104-row official score is required")
    by_id: dict[str, Mapping[str, object]] = {}
    for row in per_sample:
        sample_id = row.get("sample_id") if isinstance(row, Mapping) else None
        if not isinstance(sample_id, str) or not sample_id or sample_id in by_id:
            raise RuntimeError("complete 104-row official score has malformed identities")
        for field in ("exact_match", "tool_accuracy"):
            if row.get(field) not in {0, 0.0, 1, 1.0}:
                raise RuntimeError(f"official per-sample {field} must be binary")
        if not isinstance(row.get("parsed"), bool):
            raise RuntimeError("official per-sample parsed flag must be boolean")
        by_id[sample_id] = row
    if set(by_id) != set(expected):
        raise RuntimeError("complete 104-row official score identity drift")
    slot_f1 = aggregate.get("slot_f1")
    if (
        isinstance(slot_f1, bool)
        or not isinstance(slot_f1, (int, float))
        or not 0.0 <= float(slot_f1) <= 1.0
    ):
        raise RuntimeError("official slot micro-F1 is malformed")
    exact_count = sum(int(float(by_id[sample_id]["exact_match"])) for sample_id in expected)
    tool_count = sum(int(float(by_id[sample_id]["tool_accuracy"])) for sample_id in expected)
    parse_count = sum(bool(by_id[sample_id]["parsed"]) for sample_id in expected)
    if (
        abs(float(aggregate.get("exact_match", -1)) - exact_count / SPLIT_COUNT)
        > 1e-12
        or abs(float(aggregate.get("tool_accuracy", -1)) - tool_count / SPLIT_COUNT)
        > 1e-12
        or aggregate.get("parse_failures") != SPLIT_COUNT - parse_count
    ):
        raise RuntimeError("official aggregate and per-sample scores disagree")
    return {
        "by_id": by_id,
        "aggregate": dict(aggregate),
        "exact_count": exact_count,
        "tool_count": tool_count,
        "parse_count": parse_count,
        "slot_f1": float(slot_f1),
    }


def _grouped_exact_bootstrap(
    *,
    items: Sequence[Mapping[str, object]],
    m0_by_id: Mapping[str, Mapping[str, object]],
    g1_by_id: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Run the registered whole-query-block, sample-weighted paired bootstrap."""

    groups: dict[str, list[str]] = {}
    for item in items:
        sample_id = item.get("sample_id")
        group_id = item.get("query_block")
        if not isinstance(sample_id, str) or not isinstance(group_id, str) or not group_id:
            raise RuntimeError("bootstrap requires frozen sample and query_block identities")
        groups.setdefault(group_id, []).append(sample_id)
    if set(m0_by_id) != set(g1_by_id) or set(m0_by_id) != {
        sample_id for sample_ids in groups.values() for sample_id in sample_ids
    }:
        raise RuntimeError("bootstrap paired surface differs from the frozen roster")
    group_ids = tuple(sorted(groups))

    def statistic(sampled_groups: Sequence[str]) -> float:
        numerator = 0.0
        denominator = 0
        for group_id in sampled_groups:
            for sample_id in groups[group_id]:
                numerator += float(g1_by_id[sample_id]["exact_match"]) - float(
                    m0_by_id[sample_id]["exact_match"]
                )
                denominator += 1
        if denominator == 0:
            raise RuntimeError("bootstrap replicate contains zero paired rows")
        return numerator / denominator

    result = paired_cluster_bootstrap(
        sample_ids=group_ids,
        statistic=statistic,
        n_replicates=10_000,
        seed=20260902,
        ci_level=0.90,
    )
    return {
        **result.as_json(),
        "cluster_id": "query_block",
        "interval": "percentile",
        "quantile_method": "linear",
        "lower_quantile": 0.05,
        "upper_quantile": 0.95,
        "replicate_statistic": "sample-weighted mean paired exact delta",
    }


def _build_qualification_result(
    *,
    m0_scores: Mapping[str, object],
    g1_scores: Mapping[str, object],
    g1_texts: Mapping[str, str],
    resend_texts: Mapping[str, str],
    expected_by_id: Mapping[str, Sequence[object]],
    items: Sequence[Mapping[str, object]],
    resend_ids: Sequence[str],
) -> dict[str, object]:
    """Apply every frozen post-seal gate without changing official metrics."""

    sample_ids = tuple(str(item.get("sample_id")) for item in items)
    m0 = _official_a2t_surface(m0_scores, sample_ids)
    g1 = _official_a2t_surface(g1_scores, sample_ids)
    bootstrap = _grouped_exact_bootstrap(
        items=items,
        m0_by_id=m0["by_id"],  # type: ignore[arg-type]
        g1_by_id=g1["by_id"],  # type: ignore[arg-type]
    )
    selected = tuple(resend_ids)
    if (
        len(selected) != 16
        or len(set(selected)) != 16
        or set(g1_texts) != set(sample_ids)
        or set(resend_texts) != set(selected)
        or not set(selected).issubset(expected_by_id)
    ):
        raise RuntimeError("fixed sixteen-pair resend surface is incomplete")
    resend_parse = 0
    semantic_agreement = 0
    exact_outcome_agreement = 0
    resend_rows: list[dict[str, object]] = []
    for sample_id in selected:
        source_calls, source_parsed = parse_tool_calls_text(g1_texts[sample_id])
        repeated_calls, repeated_parsed = parse_tool_calls_text(resend_texts[sample_id])
        resend_parse += int(repeated_parsed)
        semantic_equal = bool(
            source_parsed
            and repeated_parsed
            and score_item(source_calls, repeated_calls).exact_match == 1.0
        )
        semantic_agreement += int(semantic_equal)
        expected = expected_by_id[sample_id]
        source_exact = bool(g1["by_id"][sample_id]["exact_match"])  # type: ignore[index]
        repeated_exact = score_item(expected, repeated_calls).exact_match == 1.0  # type: ignore[arg-type]
        exact_equal = source_exact == repeated_exact
        exact_outcome_agreement += int(exact_equal)
        resend_rows.append(
            {
                "sample_id": sample_id,
                "source_parsed": source_parsed,
                "resend_parsed": repeated_parsed,
                "semantic_call_agreement": semantic_equal,
                "source_exact": source_exact,
                "resend_exact": repeated_exact,
                "exact_outcome_agreement": exact_equal,
            }
        )
    exact_gain = int(g1["exact_count"]) - int(m0["exact_count"])
    tool_gain = int(g1["tool_count"]) - int(m0["tool_count"])
    counts = {
        "m0_exact": m0["exact_count"],
        "m0_tool": m0["tool_count"],
        "g1_exact": g1["exact_count"],
        "g1_tool": g1["tool_count"],
        "g1_parse": g1["parse_count"],
        "exact_gain_over_m0": exact_gain,
        "tool_gain_over_m0": tool_gain,
        "resend_parse": resend_parse,
        "resend_semantic_call_agreement": semantic_agreement,
        "resend_exact_outcome_agreement": exact_outcome_agreement,
    }
    gates = {
        "primary_parse_count_at_least_103": int(g1["parse_count"]) >= 103,
        "primary_exact_count_at_least_94": int(g1["exact_count"]) >= 94,
        "primary_tool_count_at_least_99": int(g1["tool_count"]) >= 99,
        "primary_slot_micro_f1_at_least_0_90": float(g1["slot_f1"]) >= 0.90,
        "exact_gain_over_m0_at_least_15": exact_gain >= 15,
        "tool_gain_over_m0_at_least_15": tool_gain >= 15,
        "paired_exact_grouped_ci90_lower_strictly_positive": (
            float(bootstrap["ci_low"]) > 0.0
        ),
        "resend_semantic_call_agreement_at_least_15": semantic_agreement >= 15,
        "resend_parse_count_at_least_16": resend_parse >= 16,
        "resend_exact_outcome_agreement_at_least_15": (
            exact_outcome_agreement >= 15
        ),
    }
    basic_passed = all(gates.values())
    target_passed = int(g1["exact_count"]) >= 99
    return {
        "schema": "saea-a2t-executable-ground-qualification-result-v1",
        "run_id": RUN_ID,
        "counts": counts,
        "rates": {
            "m0_exact": int(m0["exact_count"]) / SPLIT_COUNT,
            "m0_tool": int(m0["tool_count"]) / SPLIT_COUNT,
            "g1_exact": int(g1["exact_count"]) / SPLIT_COUNT,
            "g1_tool": int(g1["tool_count"]) / SPLIT_COUNT,
            "g1_parse": int(g1["parse_count"]) / SPLIT_COUNT,
            "g1_slot_micro_f1": g1["slot_f1"],
        },
        "gates": gates,
        "basic_ground_passed": basic_passed,
        "target_ground_passed": target_passed,
        "bootstrap": bootstrap,
        "per_tier": g1["aggregate"]["per_tier"],  # type: ignore[index]
        "resend_pairs": resend_rows,
        "decision": (
            "freeze the full executable handbook as the qualified task ground"
            if basic_passed
            else "keep candidate pruning, training-free control, scale, and test closed"
        ),
    }


def _assert_resend_equivalence(
    source_payloads: Mapping[str, Mapping[str, object]],
    resend_payloads: Mapping[str, Mapping[str, object]],
) -> dict[str, int]:
    """Allow only a fresh request identity; preserve content and source slot."""

    if not source_payloads or set(source_payloads) != set(resend_payloads):
        raise RuntimeError("resend and source request identities differ")
    slots: dict[str, int] = {}
    for sample_id in sorted(source_payloads):
        source = dict(source_payloads[sample_id])
        resend = dict(resend_payloads[sample_id])
        source_request_id = source.pop("request_id", None)
        resend_request_id = resend.pop("request_id", None)
        decoding = source.get("decoding_params")
        slot = decoding.get("id_slot") if isinstance(decoding, Mapping) else None
        if (
            not isinstance(source_request_id, str)
            or not isinstance(resend_request_id, str)
            or source_request_id == resend_request_id
            or slot not in {0, 1}
            or source != resend
        ):
            raise RuntimeError(
                f"resend source request equivalence drift for {sample_id!r}"
            )
        slots[sample_id] = int(slot)
    return slots


def _request_payloads_by_sample(
    documents: Sequence[Mapping[str, object]],
    *,
    selected_ids: Sequence[str] | None = None,
) -> dict[str, Mapping[str, object]]:
    """Recover hash-verified request payloads from one sealed trace."""

    wanted = set(selected_ids) if selected_ids is not None else None
    found: dict[str, Mapping[str, object]] = {}
    for number, document in enumerate(documents, start=1):
        if document.get("channel") != "MODEL_REQUEST":
            continue
        envelope = document.get("payload")
        if not isinstance(envelope, Mapping):
            raise RuntimeError(f"request trace row {number} lacks an envelope")
        payload = envelope.get("payload")
        digest = envelope.get("payload_sha256")
        if not isinstance(payload, Mapping) or not isinstance(digest, str):
            raise RuntimeError(f"request trace row {number} is malformed")
        measured = hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()
        if measured != digest:
            raise RuntimeError(f"request payload hash drift at trace row {number}")
        request_id = payload.get("request_id")
        sample_id = payload.get("sample_id")
        if (
            not isinstance(request_id, str)
            or document.get("record_id") != f"{request_id}/request"
            or not isinstance(sample_id, str)
            or not sample_id
        ):
            raise RuntimeError(f"request identity drift at trace row {number}")
        if wanted is not None and sample_id not in wanted:
            continue
        if sample_id in found:
            raise RuntimeError(f"duplicate request for sample {sample_id!r}")
        found[sample_id] = payload
    if wanted is not None and set(found) != wanted:
        raise RuntimeError("selected request payload surface is incomplete")
    if not found:
        raise RuntimeError("sealed trace carries no model requests")
    return {sample_id: found[sample_id] for sample_id in sorted(found)}


def _human_ledger_cells(phase: str, lock_sha256: str) -> dict[str, str]:
    return {
        "experiment_id": RUN_ID,
        "speech task/carrier": "Audio2Tool A2T-GROUND-QUAL-104 discovery",
        "changed axes": phase,
        "shared code revision": "receipt-pinned launcher",
        "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "dataset rev": lock_sha256,
        "MLflow run": "not uploaded",
        "effectiveness": "unread before finalization",
        "reasonableness": "complete verified 104-row official scorer job",
        "efficiency": "two outer workers, one complete manifest per process",
        "deviations": "none; no retries and no network-jitter testing",
        "decision": "pending preregistered post-seal qualification read",
    }


def _run_parallel_finalizers(
    *, mission_dir: Path, jobs: Sequence[Mapping[str, str]]
) -> dict[str, object]:
    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)
    frozen_jobs = tuple(jobs)
    if (
        len(frozen_jobs) != 2
        or [job.get("job_id") for job in frozen_jobs]
        != ["m0-registry-direct", "g1-full-executable-ground"]
        or any(set(job) != {"job_id", "manifest", "ledger_cells"} for job in frozen_jobs)
    ):
        raise RuntimeError("parallel finalization requires the two registered jobs")
    jobs_path = Path(mission_dir) / "parallel-official-finalize-jobs.jsonl"
    _write_jsonl(jobs_path, frozen_jobs)
    output_dir = Path(mission_dir) / "parallel-official-finalize"
    command = [
        "bash",
        str(REPO / "scripts/evaluate_parallel.sh"),
        "--finalize",
        "--jobs",
        str(jobs_path),
        "--output-dir",
        str(output_dir),
        "--workers",
        "2",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO,
        env={
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}:{os.environ.get('PATH', '')}",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        check=False,
        text=True,
        capture_output=True,
    )
    (Path(mission_dir) / "parallel-official-finalize.stdout.log").write_text(
        completed.stdout, encoding="utf-8", newline="\n"
    )
    (Path(mission_dir) / "parallel-official-finalize.stderr.log").write_text(
        completed.stderr, encoding="utf-8", newline="\n"
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"outer-parallel official finalization exited {completed.returncode}"
        )
    summary = _read_json(output_dir / "batch-summary.json")
    if summary.get("failed") != 0 or summary.get("succeeded") != 2:
        raise RuntimeError("both whole-manifest official finalizers must settle")
    return summary


def _assert_contact_surface_sealed(
    *,
    m0: Mapping[str, object],
    g1: Mapping[str, object],
    resend: Mapping[str, object],
) -> None:
    """Prove 104 + 104 + 16 response records sealed before scoring."""

    for label, result in (("M0", m0), ("G1", g1)):
        bundle = verify_bundle(Path(result["manifest"]))
        client = result.get("client")
        if (
            bundle.attempt_state != "OPENED"
            or len(bundle.outputs_rows) != SPLIT_COUNT
            or not isinstance(client, Mapping)
            or client.get("request_count") != SPLIT_COUNT
            or len(str(client.get("trace_manifest_hash", ""))) != 64
            or len(result.get("texts", {})) != SPLIT_COUNT  # type: ignore[arg-type]
        ):
            raise RuntimeError(f"{label} complete response surface is not sealed")
    resend_client = resend.get("client")
    resend_cost = resend_client.get("cost") if isinstance(resend_client, Mapping) else None
    if (
        resend.get("attempt_state") != "ABORTED"
        or not isinstance(resend_client, Mapping)
        or resend_client.get("request_count") != 16
        or len(str(resend_client.get("trace_manifest_hash", ""))) != 64
        or not isinstance(resend_cost, Mapping)
        or resend_cost.get("calls_used") != 16
        or len(resend.get("texts", {})) != 16  # type: ignore[arg-type]
    ):
        raise RuntimeError("sixteen-response resend trace is not sealed")


def _load_final_scores(manifest_path: Path) -> dict[str, object]:
    bundle = verify_bundle(Path(manifest_path))
    scores_meta = bundle.manifest.get("scores")
    if bundle.attempt_state != "FINALIZED" or not isinstance(scores_meta, Mapping):
        raise RuntimeError("official finalizer did not attach scores to a terminal bundle")
    path = scores_meta.get("path")
    digest = scores_meta.get("sha256")
    if not isinstance(path, str) or not isinstance(digest, str):
        raise RuntimeError("finalized bundle scores metadata is malformed")
    scores_path = Path(path)
    _require_file_hash(scores_path, digest, "official scores")
    return _read_json(scores_path)


def _postseal_qualification(
    *,
    root: Path,
    context: Mapping[str, object],
    mission_dir: Path,
    lock_sha256: str,
    m0: Mapping[str, object],
    g1: Mapping[str, object],
    resend: Mapping[str, object],
) -> dict[str, object]:
    """Finalize whole manifests, then and only then open scorer-side gold."""

    _assert_contact_surface_sealed(m0=m0, g1=g1, resend=resend)
    jobs: list[dict[str, str]] = []
    for job_id, phase, result in (
        ("m0-registry-direct", ground_flight.REGISTRY_DIRECT, m0),
        ("g1-full-executable-ground", ground_flight.FULL_EXECUTABLE_GROUND, g1),
    ):
        cells = Path(mission_dir) / f"{job_id}-ledger-cells.json"
        _write_json(cells, _human_ledger_cells(phase, lock_sha256))
        jobs.append(
            {
                "job_id": job_id,
                "manifest": str(result["manifest"]),
                "ledger_cells": str(cells),
            }
        )
    score_summary = _run_parallel_finalizers(
        mission_dir=mission_dir,
        jobs=jobs,
    )
    for result in (m0, g1):
        if verify_bundle(Path(result["manifest"])).attempt_state != "FINALIZED":
            raise RuntimeError("both official finalizers must settle before gold opens")
    m0_scores = _load_final_scores(Path(m0["manifest"]))
    g1_scores = _load_final_scores(Path(g1["manifest"]))

    # This is the first direct gold read in the launcher.  It is intentionally
    # below both successful FINALIZED-state checks.
    expected = load_expected_calls(context["lock"], root, repo_root=REPO)  # type: ignore[arg-type]
    qualification = _build_qualification_result(
        m0_scores=m0_scores,
        g1_scores=g1_scores,
        g1_texts=g1["texts"],  # type: ignore[arg-type]
        resend_texts=resend["texts"],  # type: ignore[arg-type]
        expected_by_id=expected,
        items=context["items"],  # type: ignore[arg-type]
        resend_ids=context["resend_ids"],  # type: ignore[arg-type]
    )
    qualification_path = Path(mission_dir) / "qualification-result.json"
    _write_json(qualification_path, qualification)
    return {
        "official_finalizers": score_summary,
        "qualification": qualification,
        "qualification_path": str(qualification_path),
        "qualification_sha256": _sha256_file(qualification_path),
    }


def _official_score_jobs(
    *,
    m0_manifest: Path,
    g1_manifest: Path,
    m0_ledger_cells: Path,
    g1_ledger_cells: Path,
) -> tuple[ScoreJob, ScoreJob]:
    """Materialize existing scorer primitives without running either job."""

    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)
    manifests = (Path(m0_manifest), Path(g1_manifest))
    if manifests[0] == manifests[1] or any(
        not path.name.endswith(".run-manifest.json") for path in manifests
    ):
        raise RuntimeError("official jobs require two distinct complete manifests")
    return (
        ScoreJob("m0-registry-direct", manifests[0], ledger_cells=m0_ledger_cells),
        ScoreJob(
            "g1-full-executable-ground",
            manifests[1],
            ledger_cells=g1_ledger_cells,
        ),
    )


def _validate_roster_result(result: Mapping[str, object]) -> None:
    contacts = result.get("contacts")
    engineering = result.get("engineering_scope")
    if (
        result.get("selected_count") != SPLIT_COUNT
        or result.get("selected_receipt_sha256") != RECEIPT_SHA256
        or result.get("selected_run_identity_hash") != SPLIT_IDENTITY_SHA256
        or result.get("selected_split_identity_hash") != RECEIPT_IDENTITY_SHA256
        or not isinstance(contacts, Mapping)
        or any(value not in {0, 0.0} for value in contacts.values())
        or not isinstance(engineering, Mapping)
        or engineering.get("complete_manifest_outer_parallel_scoring") is not True
        or engineering.get("dataset_sharding") is not False
        or engineering.get("network_jitter_testing") is not False
    ):
        raise RuntimeError("governed roster verdict drift")


def _validate_runtime_receipt(receipt: Mapping[str, object]) -> None:
    llama_cpp = receipt.get("llama_cpp")
    gguf_files = receipt.get("gguf_files")
    if (
        receipt.get("schema") != "saea-runtime-receipt-v3"
        or receipt.get("model_lock_key")
        != "qwen3-omni-30b-a3b-instruct-gguf-q4km"
        or not isinstance(llama_cpp, Mapping)
        or llama_cpp.get("build_commit") != LLAMA_CPP_BUILD_COMMIT
        or not isinstance(gguf_files, list)
        or len(gguf_files) != 1
        or not isinstance(gguf_files[0], Mapping)
        or gguf_files[0].get("sha256") != DECODER_GGUF_SHA256
    ):
        raise RuntimeError("runtime receipt identity drift")


def _validate_handbook_build(receipt: Mapping[str, object]) -> None:
    handbook = receipt.get("handbook")
    sources = receipt.get("source_hashes")
    report = handbook.get("report") if isinstance(handbook, Mapping) else None
    if (
        not isinstance(handbook, Mapping)
        or handbook.get("sha256") != HANDBOOK_SHA256
        or not isinstance(report, Mapping)
        or report.get("ascii_only") is not True
        or report.get("utf8_bytes") != HANDBOOK_UTF8_BYTES
        or not isinstance(sources, Mapping)
        or sources.get("registry") != REGISTRY_SHA256
    ):
        raise RuntimeError("handbook build receipt drift")


def _validate_prompt_fit(receipt: Mapping[str, object]) -> None:
    contacts = receipt.get("contacts")
    bounds = receipt.get("bounds")
    engineering = receipt.get("engineering_scope")
    source_hashes = receipt.get("source_hashes")
    if (
        not isinstance(contacts, Mapping)
        or any(
            value not in (0, 0.0)
            for key, value in contacts.items()
            if key != "outbound_targets"
        )
        or contacts.get("outbound_targets") != []
        or not isinstance(bounds, Mapping)
        or bounds.get("context_tokens") != 65536
        or bounds.get("slot_count") != 2
        or bounds.get("context_tokens_per_slot") != 32768
        or bounds.get("maximum_prompt_fits_one_slot") is not True
        or int(bounds.get("context_margin_tokens", -1)) <= 0
        or not isinstance(source_hashes, Mapping)
        or source_hashes.get("promotion_receipt") != PROMOTION_SHA256
        or not isinstance(engineering, Mapping)
        or engineering.get("complete_manifest_outer_parallel_scoring") is not True
        or engineering.get("official_scorer_single_process_per_manifest") is not True
        or engineering.get("dataset_sharding") is not False
        or engineering.get("network_jitter_testing") is not False
    ):
        raise RuntimeError("prompt-fit or engineering boundary drift")


def _validate_promotion(
    receipt: Mapping[str, object], roster: Mapping[str, object]
) -> None:
    packets = receipt.get("packets")
    if (
        receipt.get("count") != SPLIT_COUNT
        or receipt.get("split_identity_hash") != SPLIT_IDENTITY_SHA256
        or receipt.get("subset_receipt_sha256") != RECEIPT_SHA256
        or not isinstance(packets, list)
        or len(packets) != SPLIT_COUNT
    ):
        raise RuntimeError("speech packet promotion receipt drift")
    promoted_ids = {
        packet.get("packet_id")
        for packet in packets
        if isinstance(packet, Mapping)
        and isinstance(packet.get("packet_id"), str)
        and isinstance(packet.get("packet_sha256"), str)
        and len(str(packet.get("packet_sha256"))) == 64
    }
    if promoted_ids != set(roster["packet_ids"]):  # type: ignore[arg-type]
        raise RuntimeError("promoted packet identities do not equal the governed roster")


def _static_preflight(root: Path) -> dict[str, object]:
    """Run the zero-contact, read-only governance and artifact gate."""

    commit = require_clean_study_repo(REPO)
    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("composed config identity drift")
    measured_protocol = protocol_hash(
        composed.config_hash,
        str(composed.values.get("arm")),
        SPLIT_IDENTITY_SHA256,
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("governed protocol identity drift")
    plan = _execution_plan("attempt-20260902t000000z-groundqualpre")
    geometry = _validate_server_geometry(composed.values)
    score_plan = _validate_official_score_plan(OFFICIAL_SCORE_PLAN)
    if ground_flight.SPLIT_ID != "A2T-GROUND-QUAL-104":
        raise RuntimeError("flight split identity drift")

    roster_result_path = REPO / ROSTER_RESULT_RELPATH
    _require_file_hash(roster_result_path, ROSTER_RESULT_SHA256, "roster result")
    _validate_roster_result(_read_json(roster_result_path))

    receipt_path = REPO / RECEIPT_RELPATH
    _require_file_hash(receipt_path, RECEIPT_SHA256, "roster receipt")
    roster = _validate_roster(_read_json(receipt_path))

    runtime_path = REPO / RUNTIME_RECEIPT_RELPATH
    _require_file_hash(runtime_path, RUNTIME_RECEIPT_SHA256, "runtime receipt")
    _validate_runtime_receipt(_read_json(runtime_path))

    build_path = REPO / HANDBOOK_BUILD_RELPATH
    _require_file_hash(build_path, HANDBOOK_BUILD_SHA256, "handbook build receipt")
    _validate_handbook_build(_read_json(build_path))
    handbook_path = Path(root) / HANDBOOK_RELPATH
    _require_file_hash(handbook_path, HANDBOOK_SHA256, "executable handbook")
    handbook_bytes = handbook_path.read_bytes()
    if len(handbook_bytes) != HANDBOOK_UTF8_BYTES or not handbook_bytes.isascii():
        raise RuntimeError("executable handbook must remain exact ASCII English")

    prompt_fit_path = REPO / PROMPT_FIT_RELPATH
    _require_file_hash(prompt_fit_path, PROMPT_FIT_SHA256, "prompt-fit receipt")
    _validate_prompt_fit(_read_json(prompt_fit_path))

    configured_promotion = composed.values.get("speech_packet_promotion_receipt")
    configured_promotion_hash = composed.values.get(
        "speech_packet_promotion_receipt_sha256"
    )
    if (
        configured_promotion != str(PROMOTION_RECEIPT)
        or configured_promotion_hash != PROMOTION_SHA256
    ):
        raise RuntimeError("composed promotion receipt binding drift")
    _require_file_hash(PROMOTION_RECEIPT, PROMOTION_SHA256, "promotion receipt")
    promotion = _read_json(PROMOTION_RECEIPT)
    _validate_promotion(promotion, roster)
    promoted = {
        str(row["packet_id"]): row
        for row in promotion["packets"]  # type: ignore[index]
        if isinstance(row, Mapping)
    }
    packet_bindings: dict[str, dict[str, str]] = {}
    for item in roster["items"]:  # type: ignore[union-attr]
        packet_id = str(item["packet_id"])
        packet = load_speech_feature_packet(PROMOTION_RECEIPT.parent, packet_id)
        recorded = promoted.get(packet_id)
        if (
            recorded is None
            or packet.audio_sha256 != item["audio_sha256"]
            or packet.packet_sha256 != recorded.get("packet_sha256")
        ):
            raise RuntimeError(f"promoted speech packet drift for {item['sample_id']!r}")
        packet_bindings[str(item["sample_id"])] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    lock = load_lock(umbrella_lock_path(REPO))
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)

    return {
        "commit": commit,
        "composed": composed,
        "execution_plan": plan,
        "geometry": geometry,
        "official_score_plan": score_plan,
        "sample_ids": roster["sample_ids"],
        "resend_ids": roster["resend_ids"],
        "items": roster["items"],
        "lock": lock,
        "carrier_root": carrier_root,
        "packet_bindings": packet_bindings,
        "handbook": handbook_bytes.decode("ascii"),
        "handbook_path": handbook_path,
        "promotion_receipt": PROMOTION_RECEIPT,
    }


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = Path(run_dir) / f"{RUN_ID}.trace.jsonl"
    documents: list[Mapping[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if not line:
            continue
        document = json.loads(line)
        if not isinstance(document, Mapping):
            raise RuntimeError(f"trace row {number} is not an object")
        documents.append(document)
    if not documents:
        raise RuntimeError(f"sealed trace is empty: {path}")
    return tuple(documents)


def _verified_split(sample_ids: Sequence[str]) -> VerifiedSplit:
    ids = tuple(sorted(sample_ids))
    if len(ids) != SPLIT_COUNT or len(set(ids)) != SPLIT_COUNT:
        raise RuntimeError("verified split requires the complete 104 identities")
    return VerifiedSplit(
        name=ground_flight.SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_SHA256,
    )


def _decoding(context: Mapping[str, object]) -> dict[str, object]:
    values = context["composed"].values  # type: ignore[union-attr]
    decoding = dict(values["decoding_params"])
    decoding.pop("id_slot", None)
    return decoding


def _build_completed_manifest(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
    outputs_path: Path,
    trace_manifest_hash: str,
    cost: Mapping[str, object],
) -> Path:
    manifest = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=context["composed"],  # type: ignore[arg-type]
        plan=plan,
        verified_split=_verified_split(context["sample_ids"]),  # type: ignore[arg-type]
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        result=RunResult(
            run_id=RUN_ID,
            arm="speech-feature-query",
            outputs_path=outputs_path,
            trace_manifest_hash=trace_manifest_hash,
            cost=cost,
        ),
    )
    bundle = verify_bundle(manifest)
    if bundle.attempt_state != "OPENED" or len(bundle.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("direct arm did not seal a complete OPENED manifest")
    return manifest


def _run_direct_arm(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    mode: str,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(Path(run_dir) / "execution-plan.json", asdict(plan))
    adapter = ground_flight.GroundQualificationAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        mode=mode,
        handbook=str(context["handbook"]),
    )
    samples = adapter.load_split(ground_flight.SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    prefix = "ground-m0" if mode == ground_flight.REGISTRY_DIRECT else "ground-g1"
    key_id = (
        "audio2tool-direct-registry-v1"
        if mode == ground_flight.REGISTRY_DIRECT
        else "audio2tool-full-executable-ground-v1"
    )
    policy_id = (
        "saea-a2t-ground-qualification-m0-v1"
        if mode == ground_flight.REGISTRY_DIRECT
        else "saea-a2t-ground-qualification-g1-v1"
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir,
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=prefix,
        speech_feature_root=PROMOTION_RECEIPT.parent,
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
    )
    try:
        summary = ground_flight.run_direct_qualification_phase(
            adapter=adapter,
            core_client=client,
            split_id=ground_flight.SPLIT_ID,
            speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
            slot_count=2,
            decoding_params=_decoding(context),
            key_representation_id=key_id,
            matcher_policy_id=policy_id,
        )
    except Exception:
        client.close()
        raise
    client_summary = client.close()
    if client_summary.get("request_count") != SPLIT_COUNT:
        raise RuntimeError(f"{mode} did not make exactly 104 one-shot contacts")
    documents = _trace_documents(run_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase=M0_DIRECT_PHASE,
        umbrella_lock_sha256=str(client_summary["cost"]["umbrella_lock_sha256"]),  # type: ignore[index]
    )
    frozen_rows = tuple({**row, "phase": mode} for row in rows)
    outputs = Path(run_dir) / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, frozen_rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
        cost=cost,
    )
    texts = {
        result.sample_id: result.final_response_text for result in summary.results
    }
    return {
        "mode": mode,
        "attempt_id": attempt_id,
        "manifest": manifest,
        "outputs": outputs,
        "texts": texts,
        "payloads": _request_payloads_by_sample(documents),
        "client": client_summary,
    }


def _source_slots(payloads: Mapping[str, Mapping[str, object]]) -> dict[str, int]:
    slots: dict[str, int] = {}
    for sample_id, payload in payloads.items():
        decoding = payload.get("decoding_params")
        slot = decoding.get("id_slot") if isinstance(decoding, Mapping) else None
        if slot not in {0, 1}:
            raise RuntimeError(f"G1 source slot drift for {sample_id!r}")
        slots[sample_id] = int(slot)
    return slots


def _run_resends(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    g1: Mapping[str, object],
) -> dict[str, object]:
    selected = tuple(context["resend_ids"])  # type: ignore[arg-type]
    selected_set = set(selected)
    selected_items = tuple(
        item
        for item in context["items"]  # type: ignore[union-attr]
        if item["sample_id"] in selected_set
    )
    selected_bindings = {
        sample_id: context["packet_bindings"][sample_id]  # type: ignore[index]
        for sample_id in selected
    }
    source_payloads = {
        sample_id: g1["payloads"][sample_id]  # type: ignore[index]
        for sample_id in selected
    }
    source_slots = _source_slots(source_payloads)
    plan = _execution_plan(attempt_id)
    _write_json(Path(run_dir) / "execution-plan.json", asdict(plan))
    adapter = ground_flight.GroundQualificationAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=selected_items,
        mode=ground_flight.FULL_EXECUTABLE_GROUND,
        handbook=str(context["handbook"]),
    )
    samples = adapter.load_split(ground_flight.SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir,
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="ground-resend",
        speech_feature_root=PROMOTION_RECEIPT.parent,
        speech_packet_bindings=selected_bindings,
    )
    try:
        summary = ground_flight.run_direct_qualification_phase(
            adapter=adapter,
            core_client=client,
            split_id=ground_flight.SPLIT_ID,
            speech_packet_bindings=selected_bindings,
            slot_count=2,
            decoding_params=_decoding(context),
            key_representation_id="audio2tool-full-executable-ground-v1",
            matcher_policy_id="saea-a2t-ground-qualification-g1-v1",
            slot_by_sample=source_slots,
        )
    except Exception:
        client.close()
        raise
    client_summary = client.close()
    documents = _trace_documents(run_dir)
    resend_payloads = _request_payloads_by_sample(documents, selected_ids=selected)
    _assert_resend_equivalence(source_payloads, resend_payloads)
    if (
        client_summary.get("request_count") != 16
        or client_summary.get("cost", {}).get("calls_used") != 16  # type: ignore[union-attr]
    ):
        raise RuntimeError("resend path did not make exactly sixteen one-shot contacts")
    texts = {
        result.sample_id: result.final_response_text for result in summary.results
    }
    _write_json(
        Path(run_dir) / "resend-receipt.json",
        {
            "schema": "saea-a2t-ground-qualification-resend-receipt-v1",
            "attempt_id": attempt_id,
            "selected_ids": list(selected),
            "source_slots": source_slots,
            "client": client_summary,
            "source_request_equivalence": True,
        },
    )
    if not abort_attempt_if_opened(
        root,
        RUN_ID,
        attempt_id,
        reason="sixteen resend responses sealed; no standalone scorer job registered",
    ):
        raise RuntimeError("resend attempt did not reach terminal ABORTED state")
    return {
        "attempt_id": attempt_id,
        "attempt_state": "ABORTED",
        "texts": texts,
        "resend_ids": selected,
        "client": client_summary,
        "run_dir": run_dir,
    }


def _stop_service(session: object, runtime_receipt: object, receipt_path: Path) -> None:
    stop_session(
        session,  # type: ignore[arg-type]
        runtime_receipt=runtime_receipt,  # type: ignore[arg-type]
        runtime_root=RUNTIME_ROOT,
        force_after_timeout=True,
        receipt_path=receipt_path,
    )


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {
        "m0": f"attempt-{stamp.lower()}-groundm0",
        "g1": f"attempt-{stamp.lower()}-groundg1",
        "resend": f"attempt-{stamp.lower()}-groundresend",
    }
    values = context["composed"].values  # type: ignore[union-attr]
    runtime_receipt = load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH)
    model_root = Path(str(values["model_materialization_root"]))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(RUNTIME_RECEIPT_RELPATH.relative_to("docs")),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=model_root,
    )
    lock_sha256 = gate.assert_model_touch_allowed(
        _execution_plan(attempt_ids["resend"]), full_hash=True
    )
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("decoder base_url must be an explicit loopback port")
    service_dir = mission_dir / "service"
    service_dir.mkdir()
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    started = time.perf_counter()
    try:
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=parsed_url.port,
            session_id=f"{RUN_ID}-SESSION-{stamp}",
            extra_argv=tuple(values["server_args"]),
            extra_env=dict(values.get("server_env", {})),
            receipt_path=session_receipt,
            ready_timeout_seconds=600.0,
            server_log_path=service_dir / "server.log",
            role="inference",
            model_root=model_root,
        )
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
        )
        m0 = _run_direct_arm(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            mode=ground_flight.REGISTRY_DIRECT,
            attempt_id=attempt_ids["m0"],
            run_dir=mission_dir / "m0-registry-direct",
            session_receipt_path=session_receipt,
        )
        g1 = _run_direct_arm(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            mode=ground_flight.FULL_EXECUTABLE_GROUND,
            attempt_id=attempt_ids["g1"],
            run_dir=mission_dir / "g1-full-executable-ground",
            session_receipt_path=session_receipt,
        )
        resend = _run_resends(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["resend"],
            run_dir=mission_dir / "g1-resend-stability",
            g1=g1,
        )
        _stop_service(session, runtime_receipt, stop_receipt)
        session = None
        postseal = _postseal_qualification(
            root=root,
            context=context,
            mission_dir=mission_dir,
            lock_sha256=lock_sha256,
            m0=m0,
            g1=g1,
            resend=resend,
        )
        receipt = {
            "schema": "saea-a2t-executable-ground-qualification-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "contacts": {"m0": 104, "g1": 104, "resend": 16, "total": 224},
            "attempt_ids": attempt_ids,
            "session_receipt": str(session_receipt),
            "stop_receipt": str(stop_receipt),
            **postseal,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        for attempt_id in attempt_ids.values():
            abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {
                "schema": "saea-a2t-executable-ground-qualification-failure-v1",
                "run_id": RUN_ID,
                "attempt_ids": attempt_ids,
                "error": repr(error),
            },
        )
        raise
    finally:
        if session is not None:
            _stop_service(session, runtime_receipt, stop_receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="validate frozen inputs without any model, scorer, or network contact",
    )
    args = parser.parse_args(argv)
    root = data_root()
    if not args.preflight_only:
        receipt = _launch(root)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    context = _static_preflight(root)
    print(
        json.dumps(
            {
                "preflight": "passed",
                "run_id": RUN_ID,
                "study_commit": context["commit"],
                "samples": len(context["sample_ids"]),  # type: ignore[arg-type]
                "official_score_workers": 2,
                "official_score_manifests": 2,
                "contacts": {
                    "model": 0,
                    "scorer": 0,
                    "network": 0,
                    "tokenizer": 0,
                    "retriever": 0,
                    "gold": 0,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
