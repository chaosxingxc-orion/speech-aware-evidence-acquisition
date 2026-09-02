"""Run the preregistered tokenizer-only executable-ground prompt-fit check."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.core.driver.speech_native import (  # noqa: E402
    _LoopbackPromptAuditClient,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.rails.a2t_executable_ground_prompt_fit import (  # noqa: E402
    COMPLETION_TOKEN_ALLOWANCE,
    CONTEXT_TOKENS,
    CONTEXT_TOKENS_PER_SLOT,
    OBSERVATION_CHARACTER_LIMIT,
    OBSERVATION_TOKEN_ALLOWANCE,
    OBSERVATION_WORD_LIMIT,
    PROMPT_ORDER,
    SLOT_COUNT,
    SPEECH_FEATURE_TOKEN_RESERVE,
    build_ground_envelopes,
    compute_prompt_fit_bounds,
    measure_text_prompt_tokens,
    validate_registered_contact_counts,
)

EXPERIMENT_ID = "SAEA-A2T-MF-EXECUTABLE-GROUND-PROMPT-FIT-V1"
CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-v1"
)
OUTPUT = CHECK_DIR / "prompt-fit-result.json"
HANDBOOK_RELPATH = Path("knowledge/audio2tool/executable-ground-v1/handbook.txt")
HANDBOOK_SHA256 = "58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8"
BUILD_RECEIPT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-build-v1/build-receipt.json"
)
BUILD_RECEIPT_SHA256 = (
    "505645b3cdef553ac847a5b248936182160d7b38aaaac84a076b9137c8e40e34"
)
MODEL_FRAGMENT_RELPATH = Path(
    "configs/model/q4km-mmproj-free-speech-native-np2-a2t-max1024.json"
)
MODEL_FRAGMENT_SHA256 = (
    "82a23ed8bf71ff3cb290cea7d1f8e4cb35b281965a085bf8ab6d59406d650532"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)
CPV2_PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-contract-preserving-cascade-104-v2/prompt-fit-cpv2.json"
)
CPV2_PROMPT_FIT_SHA256 = (
    "9b6b8464926af01b33bdd6f1f5360eb6623702033e217491b26141b3f947d5df"
)
CHAT_TEMPLATE_SHA256 = (
    "45777d2e798aae1d1ce6844e69edcb23fc0c710009554711c78efab9044da2c8"
)
DECODER_GGUF_SHA256 = "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
LLAMA_CPP_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
RUNTIME_ROOT = Path("/home/chao")
HOST = "127.0.0.1"
PORT = 8090


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_file_hash(path: Path, expected: str, label: str) -> str:
    measured = _sha256_file(path)
    if measured != expected:
        raise RuntimeError(f"{label} SHA-256 drift: {measured}")
    return measured


def _verify_runtime_bytes(
    runtime_receipt: Mapping[str, object], root: Path
) -> dict[str, object]:
    verified: list[dict[str, object]] = []
    llama = runtime_receipt.get("llama_cpp")
    if not isinstance(llama, Mapping) or llama.get("build_commit") != LLAMA_CPP_COMMIT:
        raise RuntimeError("runtime receipt llama.cpp identity drift")
    binary_path = llama.get("binary_path")
    binary_sha = llama.get("binary_sha256")
    if not isinstance(binary_path, str) or not isinstance(binary_sha, str):
        raise RuntimeError("runtime receipt binary entry is malformed")
    binary = RUNTIME_ROOT / binary_path
    _require_file_hash(binary, binary_sha, "runtime binary")
    verified.append({"path": binary_path, "sha256": binary_sha})

    libraries = runtime_receipt.get("runtime_libraries")
    if not isinstance(libraries, list) or not libraries:
        raise RuntimeError("runtime receipt library inventory is malformed")
    for entry in libraries:
        if not isinstance(entry, Mapping):
            raise RuntimeError("runtime library entry is malformed")
        relative = entry.get("path")
        expected = entry.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeError("runtime library path or SHA-256 is malformed")
        _require_file_hash(RUNTIME_ROOT / relative, expected, "runtime library")
        verified.append({"path": relative, "sha256": expected})

    gguf_files = runtime_receipt.get("gguf_files")
    if not isinstance(gguf_files, list) or len(gguf_files) != 1:
        raise RuntimeError("inference runtime must pin exactly one decoder GGUF")
    gguf = gguf_files[0]
    if not isinstance(gguf, Mapping):
        raise RuntimeError("runtime GGUF entry is malformed")
    relative = gguf.get("path")
    expected = gguf.get("sha256")
    if not isinstance(relative, str) or expected != DECODER_GGUF_SHA256:
        raise RuntimeError("runtime decoder GGUF identity drift")
    _require_file_hash(root / relative, DECODER_GGUF_SHA256, "decoder GGUF")
    return {
        "llama_cpp_build_commit": LLAMA_CPP_COMMIT,
        "decoder_gguf_sha256": DECODER_GGUF_SHA256,
        "runtime_binary_and_library_file_count": len(verified),
        "runtime_binary_and_library_hashes_verified": True,
        "decoder_gguf_hash_verified": True,
    }


def _load_fragment() -> dict[str, object]:
    _require_file_hash(
        REPO / MODEL_FRAGMENT_RELPATH,
        MODEL_FRAGMENT_SHA256,
        "model fragment",
    )
    fragment = json.loads((REPO / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    server_args = [str(value) for value in fragment.get("server_args", [])]
    context = int(server_args[server_args.index("-c") + 1])
    slots = int(server_args[server_args.index("-np") + 1])
    decoding = fragment.get("decoding_params")
    if not isinstance(decoding, Mapping):
        raise RuntimeError("model fragment decoding parameters are malformed")
    if (
        context != CONTEXT_TOKENS
        or slots != SLOT_COUNT
        or context // slots != CONTEXT_TOKENS_PER_SLOT
        or decoding.get("max_tokens") != COMPLETION_TOKEN_ALLOWANCE
        or fragment.get("prompt_order") != PROMPT_ORDER
    ):
        raise RuntimeError("model fragment serving or prompt geometry drift")
    if fragment.get("runtime_receipt") != "receipts/runtime-q4km-mmproj-free.json":
        raise RuntimeError("model fragment runtime-receipt path drift")
    return fragment


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("PYTHONDONTWRITEBYTECODE=1 is required")
    if OUTPUT.exists():
        raise RuntimeError("registered prompt-fit output already exists")
    study_commit = require_clean_study_repo(REPO)
    root = data_root()
    handbook_path = root / HANDBOOK_RELPATH
    _require_file_hash(handbook_path, HANDBOOK_SHA256, "executable handbook")
    handbook = handbook_path.read_text(encoding="utf-8")
    _require_file_hash(
        REPO / BUILD_RECEIPT_RELPATH,
        BUILD_RECEIPT_SHA256,
        "executable-ground build receipt",
    )
    _require_file_hash(
        REPO / CPV2_PROMPT_FIT_RELPATH,
        CPV2_PROMPT_FIT_SHA256,
        "CPV2 prompt-fit receipt",
    )
    cpv2 = json.loads((REPO / CPV2_PROMPT_FIT_RELPATH).read_text(encoding="utf-8"))
    if cpv2.get("speech_feature_tokens_measured_worst") != SPEECH_FEATURE_TOKEN_RESERVE:
        raise RuntimeError("CPV2 measured speech-feature reserve drift")
    fragment = _load_fragment()
    _require_file_hash(
        REPO / RUNTIME_RECEIPT_RELPATH,
        RUNTIME_RECEIPT_SHA256,
        "runtime receipt",
    )
    runtime_receipt = load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH)
    runtime_verification = _verify_runtime_bytes(runtime_receipt, root)

    run_dir = root / "runs" / EXPERIMENT_ID / "attempt-v1"
    run_dir.mkdir(parents=True, exist_ok=False)
    session_path = run_dir / "session-receipt.json"
    stop_path = run_dir / "stop-receipt.json"
    server_log_path = run_dir / "llama-server.log"
    session = None
    stop_receipt: Mapping[str, object] | None = None
    request_counts = {
        "GET /props": 0,
        "POST /apply-template": 0,
        "POST /tokenize": 0,
    }
    measurements: dict[str, int] = {}
    message_hashes: dict[str, str] = {}
    media_marker = ""
    try:
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=runtime_receipt,
            host=HOST,
            port=PORT,
            session_id="saea-a2t-executable-ground-prompt-fit-v1",
            extra_argv=tuple(str(value) for value in fragment["server_args"]),
            extra_env={
                str(key): str(value)
                for key, value in dict(fragment.get("server_env", {})).items()
            },
            startup_timeout_seconds=60.0,
            ready_timeout_seconds=240.0,
            receipt_path=session_path,
            server_log_path=server_log_path,
            role="inference",
        )
        client = _LoopbackPromptAuditClient(host=HOST, port=PORT, timeout_seconds=120.0)
        props = client.get_json("/props")
        request_counts["GET /props"] += 1
        media_marker_value = props.get("media_marker")
        chat_template = props.get("chat_template")
        if not isinstance(media_marker_value, str) or not media_marker_value:
            raise RuntimeError("live tokenizer lacks a media marker")
        if not isinstance(chat_template, str):
            raise RuntimeError("live tokenizer lacks a chat template")
        if (
            hashlib.sha256(chat_template.encode("utf-8")).hexdigest()
            != CHAT_TEMPLATE_SHA256
        ):
            raise RuntimeError("live chat-template identity drift")
        live_context = (props.get("default_generation_settings") or {}).get("n_ctx")
        if live_context != CONTEXT_TOKENS_PER_SLOT:
            raise RuntimeError("live context-per-slot geometry drift")
        media_marker = media_marker_value
        for envelope in build_ground_envelopes(handbook):
            message_hashes[envelope.envelope_id] = _canonical_sha256(envelope.messages)
            measurements[envelope.envelope_id] = measure_text_prompt_tokens(
                client,
                envelope.messages,
                media_marker=media_marker,
                request_counts=request_counts,
            )
        validate_registered_contact_counts(request_counts)
    finally:
        if session is not None:
            stop_receipt = stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
                timeout_seconds=30.0,
                force_after_timeout=False,
                receipt_path=stop_path,
            )

    if stop_receipt is None:
        raise RuntimeError(
            "receipt-bound tokenizer service did not produce a stop receipt"
        )
    bounds = compute_prompt_fit_bounds(measurements)
    session_sha = _sha256_file(session_path)
    stop_sha = _sha256_file(stop_path)
    server_log_sha = _sha256_file(server_log_path)
    report = {
        "schema": "saea-a2t-executable-ground-prompt-fit-result-v1",
        "experiment_id": EXPERIMENT_ID,
        "study": "speech-aware-evidence-acquisition",
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            "handbook": HANDBOOK_SHA256,
            "executable_ground_build_receipt": BUILD_RECEIPT_SHA256,
            "model_fragment": MODEL_FRAGMENT_SHA256,
            "runtime_receipt": RUNTIME_RECEIPT_SHA256,
            "cpv2_prompt_fit_receipt": CPV2_PROMPT_FIT_SHA256,
        },
        "handbook": {
            "relative_path": HANDBOOK_RELPATH.as_posix(),
            "characters": len(handbook),
            "utf8_bytes": len(handbook.encode("utf-8")),
            "ascii_only": handbook.isascii(),
            "complete_system_message": True,
            "selected_or_reordered_after_measurement": False,
        },
        "message_sha256": message_hashes,
        "observation_bound": {
            "maximum_words": OBSERVATION_WORD_LIMIT,
            "maximum_ascii_characters": OBSERVATION_CHARACTER_LIMIT,
            "separate_token_allowance": OBSERVATION_TOKEN_ALLOWANCE,
            "silent_truncation_allowed": False,
        },
        "speech_feature_bound": {
            "reserved_tokens": SPEECH_FEATURE_TOKEN_RESERVE,
            "source_sample_id": cpv2.get(
                "speech_feature_tokens_measured_worst_sample_id"
            ),
            "fresh_roster_inheritance_rule": (
                "every promoted packet must measure at most 455 tokens; a larger "
                "packet stops qualification and requires a new prompt-fit receipt"
            ),
        },
        "bounds": bounds,
        "runtime_verification": runtime_verification,
        "tokenizer": {
            "host": HOST,
            "port": PORT,
            "chat_template_sha256": CHAT_TEMPLATE_SHA256,
            "media_marker": media_marker,
            "request_counts": request_counts,
            "allowed_endpoints": ["/props", "/apply-template", "/tokenize"],
            "completion_endpoint_calls": 0,
            "decoder_evaluations": 0,
            "generated_tokens": 0,
            "audio_decoded": False,
            "session_receipt_sha256": session_sha,
            "stop_receipt_sha256": stop_sha,
            "server_log_sha256": server_log_sha,
            "service_started_by_check": True,
            "service_stopped_by_check": True,
        },
        "contacts": {
            "frozen_core_decode": 0,
            "local_tokenizer_http": sum(request_counts.values()),
            "retriever": 0,
            "embedding_tool": 0,
            "external_network": 0,
            "audio_seconds": 0,
            "gpu_decode_hours": 0.0,
        },
        "gold_read": False,
        "test_read": False,
        "decision": (
            "permit only fresh approximately-104 roster freezing and separately "
            "preregistered preprocessing and ground qualification"
        ),
        "engineering_scope": {
            "complete_manifest_outer_parallel_scoring": True,
            "official_scorer_single_process_per_manifest": True,
            "dataset_sharding": False,
            "network_jitter_testing": False,
        },
    }
    OUTPUT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(bounds, indent=2, sort_keys=True))
    print(f"receipt: {OUTPUT}")
    print(f"receipt_sha256: {_sha256_file(OUTPUT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
