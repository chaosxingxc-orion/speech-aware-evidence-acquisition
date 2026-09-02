"""Fail-closed launcher scaffold for executable-ground qualification.

Only ``--preflight-only`` is executable in this revision.  Preflight hashes
and validates every governed, runtime-visible input without opening a model,
tokenizer, retriever, scorer, network connection, expected call, or gold.
The model-facing path remains deliberately sealed until its bundle assembly
and exposure-ledger integration receive a separate review.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.scoring_batch import (  # noqa: E402
    ScoreJob,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes import (  # noqa: E402
    a2t_executable_ground_qualification_flight as ground_flight,
)


RUN_ID = "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-ground-qual-104"
BASELINE_FRAGMENT = "a2t-executable-ground-qualification"
EXPERIMENT_FRAGMENT = "a2t-executable-ground-qualification-104-v1"

COMPOSED_CONFIG_SHA256 = (
    "2ec773a13e65698d0d8f750b46ae377213ebb1cd98660cd813fd077dcb56b1dd"
)
PROTOCOL_SHA256 = (
    "c0c611454c3db4b1f185811eb8f7d40e96d92123790a75c6927cc5954f73a4aa"
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
    _validate_promotion(_read_json(PROMOTION_RECEIPT), roster)

    return {
        "commit": commit,
        "composed": composed,
        "execution_plan": plan,
        "geometry": geometry,
        "official_score_plan": score_plan,
        "sample_ids": roster["sample_ids"],
        "resend_ids": roster["resend_ids"],
        "handbook_path": handbook_path,
        "promotion_receipt": PROMOTION_RECEIPT,
    }


def _launch(root: Path) -> Mapping[str, object]:
    del root
    raise RuntimeError(
        "full execution is a contact-closed scaffold; only --preflight-only is "
        "implemented, and no model, scorer, network, tokenizer, retriever, or gold "
        "contact is authorized by this launcher revision"
    )


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
        _launch(root)
        return 2  # pragma: no cover - _launch is intentionally fail-closed.
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
