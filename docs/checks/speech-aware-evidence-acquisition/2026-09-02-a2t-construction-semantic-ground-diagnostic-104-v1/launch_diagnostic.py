"""Run the 104-sample G2 construction-semantic ground diagnostic."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    abort_attempt_if_opened,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
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
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_phase_bundle_material,
)


RUN_ID = "SAEA-A2T-CONSTRUCTION-SEMANTIC-GROUND-DIAGNOSTIC-104-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np1-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-ground-qual-104"
BASELINE_FRAGMENT = "a2t-construction-semantic-ground-diagnostic"
EXPERIMENT_FRAGMENT = "a2t-construction-semantic-ground-diagnostic-104-v1"
COMPOSED_CONFIG_SHA256 = (
    "53d298c0c150cf29dd2a3050997b42f82f00c319b997ecee54260cf953386c4a"
)
PROTOCOL_SHA256 = (
    "9784e0ca0f80cb7798d25412ecdf3cd6f8a69a68708f2848ee0cc446ce92dc7b"
)
RUN_IDENTITY_SHA256 = (
    "fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b"
)
SPLIT_IDENTITY_SHA256 = (
    "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
)
SPLIT_COUNT = 104
SPLIT_AUDIO_SECONDS = 543.107
RUNTIME_ROOT = Path("/home/chao")

RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-GROUND-QUAL-104.json")
RECEIPT_SHA256 = (
    "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)
HANDBOOK_RELPATH = Path(
    "knowledge/audio2tool/construction-semantic-ground-v2/handbook.txt"
)
HANDBOOK_SHA256 = (
    "04c9c78d03b002faf6c828a5b35f1786aadc7f5da3fee2bf675374e7ea2ea697"
)
HANDBOOK_BYTES = 97548
BUILD_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-construction-semantic-ground-build-v2/build-receipt.json"
)
BUILD_SHA256 = (
    "ad7a96c11fbd633e0d1643d385e44726f5a456c522619720e8dcc3f54da56b0d"
)
PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-construction-semantic-ground-prompt-fit-v2-np1/"
    "prompt-fit-result.json"
)
PROMPT_FIT_SHA256 = (
    "942d26c839f4d57dbed787087829dc920f51f1693096b60df157c47ad5750c25"
)
PROMOTION_RECEIPT = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/"
    "A2T-GROUND-QUAL-104-promotion.json"
)
PROMOTION_SHA256 = (
    "b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f"
)
HISTORICAL_G1_SCORES = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/"
    "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1/"
    "flight-20260902T145019Z/g1-full-executable-ground/"
    "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1.scores.json"
)
HISTORICAL_G1_SCORE_SHA256 = (
    "ef172f42cab575d2fe746066a9b95595930f568e4058b6c3f071c4a194a86706"
)


def _load_qualification_launcher() -> object:
    path = (
        REPO
        / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-02-a2t-executable-ground-qualification-104-v1/launcher/"
        "launch_ground_qualification.py"
    )
    spec = importlib.util.spec_from_file_location("saea_g1_qualification_launcher", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import the frozen qualification launcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN_ID = RUN_ID
    module.MODEL_FRAGMENT = MODEL_FRAGMENT
    module.DATASET_FRAGMENT = DATASET_FRAGMENT
    module.BASELINE_FRAGMENT = BASELINE_FRAGMENT
    module.EXPERIMENT_FRAGMENT = EXPERIMENT_FRAGMENT
    module.COMPOSED_CONFIG_SHA256 = COMPOSED_CONFIG_SHA256
    module.PROTOCOL_SHA256 = PROTOCOL_SHA256
    module.SPLIT_IDENTITY_SHA256 = RUN_IDENTITY_SHA256
    module.RECEIPT_IDENTITY_SHA256 = SPLIT_IDENTITY_SHA256
    module.SERVER_SLOT_COUNT = 1
    module.CONTEXT_TOKENS_PER_SLOT = 65536
    module.HANDBOOK_RELPATH = HANDBOOK_RELPATH
    module.HANDBOOK_SHA256 = HANDBOOK_SHA256
    module.HANDBOOK_UTF8_BYTES = HANDBOOK_BYTES
    module.PROMOTION_RECEIPT = PROMOTION_RECEIPT
    module.PROMOTION_SHA256 = PROMOTION_SHA256
    return module


Q = _load_qualification_launcher()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    measured = _sha256_file(path)
    if measured != expected:
        raise RuntimeError(f"{label} SHA-256 drift: {measured}")


def _read_json(path: Path) -> dict[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _execution_plan(attempt_id: str) -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=RUN_IDENTITY_SHA256,
        planned_model_calls=108,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=570,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def _validate_prompt_fit(document: Mapping[str, object]) -> None:
    bounds = document.get("bounds")
    source_hashes = document.get("source_hashes")
    engineering = document.get("engineering_scope")
    if (
        not isinstance(bounds, Mapping)
        or bounds.get("context_tokens_per_slot") != 65536
        or bounds.get("slot_count") != 1
        or bounds.get("required_context_per_slot") != 52149
        or bounds.get("context_margin_tokens") != 13387
        or bounds.get("maximum_prompt_fits_one_slot") is not True
        or not isinstance(source_hashes, Mapping)
        or source_hashes.get("handbook") != HANDBOOK_SHA256
        or not isinstance(engineering, Mapping)
        or engineering.get("official_scorer_single_process_per_manifest") is not True
        or engineering.get("dataset_sharding") is not False
        or engineering.get("network_jitter_testing") is not False
    ):
        raise RuntimeError("G2 prompt-fit receipt drift")


def _static_preflight(root: Path) -> dict[str, object]:
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
    if (
        protocol_hash(composed.config_hash, str(composed.values.get("arm")), RUN_IDENTITY_SHA256)
        != PROTOCOL_SHA256
    ):
        raise RuntimeError("protocol identity drift")
    geometry = Q._validate_server_geometry(composed.values)

    _require_hash(REPO / RECEIPT_RELPATH, RECEIPT_SHA256, "roster receipt")
    roster = Q._validate_roster(_read_json(REPO / RECEIPT_RELPATH))
    _require_hash(
        REPO / RUNTIME_RECEIPT_RELPATH,
        RUNTIME_RECEIPT_SHA256,
        "runtime receipt",
    )
    Q._validate_runtime_receipt(_read_json(REPO / RUNTIME_RECEIPT_RELPATH))

    _require_hash(REPO / BUILD_RELPATH, BUILD_SHA256, "G2 build receipt")
    build = _read_json(REPO / BUILD_RELPATH)
    handbook_meta = build.get("handbook")
    report = handbook_meta.get("report") if isinstance(handbook_meta, Mapping) else None
    if (
        not isinstance(handbook_meta, Mapping)
        or handbook_meta.get("sha256") != HANDBOOK_SHA256
        or not isinstance(report, Mapping)
        or report.get("utf8_bytes") != HANDBOOK_BYTES
        or report.get("ascii_only") is not True
        or report.get("source_sample_count") != 22951
        or report.get("argument_values_rendered") != 0
        or report.get("invocation_texts_rendered") != 0
    ):
        raise RuntimeError("G2 build receipt content drift")
    handbook_path = Path(root) / HANDBOOK_RELPATH
    _require_hash(handbook_path, HANDBOOK_SHA256, "G2 handbook")
    handbook_bytes = handbook_path.read_bytes()
    if len(handbook_bytes) != HANDBOOK_BYTES or not handbook_bytes.isascii():
        raise RuntimeError("G2 handbook byte surface drift")

    _require_hash(REPO / PROMPT_FIT_RELPATH, PROMPT_FIT_SHA256, "G2 prompt fit")
    _validate_prompt_fit(_read_json(REPO / PROMPT_FIT_RELPATH))
    _require_hash(PROMOTION_RECEIPT, PROMOTION_SHA256, "packet promotion receipt")
    promotion = _read_json(PROMOTION_RECEIPT)
    Q._validate_promotion(promotion, roster)
    promoted = {
        str(row["packet_id"]): row
        for row in promotion["packets"]
        if isinstance(row, Mapping)
    }
    packet_bindings: dict[str, dict[str, str]] = {}
    for item in roster["items"]:
        packet_id = str(item["packet_id"])
        packet = load_speech_feature_packet(PROMOTION_RECEIPT.parent, packet_id)
        recorded = promoted.get(packet_id)
        if (
            recorded is None
            or packet.audio_sha256 != item["audio_sha256"]
            or packet.packet_sha256 != recorded.get("packet_sha256")
        ):
            raise RuntimeError(f"packet drift for {item['sample_id']!r}")
        packet_bindings[str(item["sample_id"])] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    lock = load_lock(umbrella_lock_path(REPO))
    return {
        "commit": commit,
        "composed": composed,
        "geometry": geometry,
        "sample_ids": roster["sample_ids"],
        "items": roster["items"],
        "lock": lock,
        "carrier_root": asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
        "packet_bindings": packet_bindings,
        "handbook": handbook_bytes.decode("ascii"),
    }


def _run_g2(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    adapter = ground_flight.GroundQualificationAdapter(
        context["lock"],
        root,
        repo_root=REPO,
        receipt_items=context["items"],
        mode=ground_flight.FULL_EXECUTABLE_GROUND,
        handbook=str(context["handbook"]),
    )
    samples = adapter.load_split(ground_flight.SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="ground-g2",
        speech_feature_root=PROMOTION_RECEIPT.parent,
        speech_packet_bindings=context["packet_bindings"],
    )
    try:
        summary = ground_flight.run_direct_qualification_phase(
            adapter=adapter,
            core_client=client,
            split_id=ground_flight.SPLIT_ID,
            speech_packet_bindings=context["packet_bindings"],
            slot_count=1,
            decoding_params=Q._decoding(context),
            key_representation_id="audio2tool-construction-semantic-ground-v2",
            matcher_policy_id="saea-a2t-ground-diagnostic-g2-v1",
        )
    except Exception:
        client.close()
        raise
    client_summary = client.close()
    if client_summary.get("request_count") != SPLIT_COUNT:
        raise RuntimeError("G2 did not make exactly 104 one-shot contacts")
    documents = Q._trace_documents(run_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase=Q.M0_DIRECT_PHASE,
        umbrella_lock_sha256=str(client_summary["cost"]["umbrella_lock_sha256"]),
    )
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    Q._write_jsonl(
        outputs,
        tuple({**row, "phase": "G2_CONSTRUCTION_SEMANTIC_GROUND"} for row in rows),
    )
    manifest = Q._build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
        cost=cost,
    )
    return {
        "manifest": manifest,
        "client": client_summary,
        "texts": {
            result.sample_id: result.final_response_text for result in summary.results
        },
    }


def _finalize_and_analyze(
    *, mission_dir: Path, context: Mapping[str, object], result: Mapping[str, object]
) -> dict[str, object]:
    bundle = verify_bundle(Path(result["manifest"]))
    if bundle.attempt_state != "OPENED" or len(bundle.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("G2 manifest did not seal before scoring")
    cells = mission_dir / "g2-ledger-cells.json"
    _write_json(
        cells,
        {
            "experiment_id": RUN_ID,
            "speech task/carrier": "Audio2Tool A2T-GROUND-QUAL-104 discovery",
            "changed axes": "construction-semantic ground representation",
            "shared code revision": "receipt-pinned launcher",
            "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
            "dataset rev": RECEIPT_SHA256,
            "MLflow run": "not uploaded",
            "effectiveness": "unread before finalization",
            "reasonableness": "complete verified 104-row official scorer job",
            "efficiency": "one complete manifest, one official scorer process",
            "deviations": "none; no retries and no network-jitter testing",
            "decision": "apply the preregistered G2 absolute gates",
        },
    )
    jobs_path = mission_dir / "official-finalize-jobs.jsonl"
    Q._write_jsonl(
        jobs_path,
        (
            {
                "job_id": "g2-construction-semantic-ground",
                "manifest": str(result["manifest"]),
                "ledger_cells": str(cells),
            },
        ),
    )
    output_dir = mission_dir / "official-finalize"
    completed = subprocess.run(
        [
            "bash",
            str(REPO / "scripts/evaluate_parallel.sh"),
            "--finalize",
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(output_dir),
            "--workers",
            "1",
        ],
        cwd=REPO,
        env={
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}:{os.environ.get('PATH', '')}",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        text=True,
        capture_output=True,
        check=False,
    )
    (mission_dir / "official-finalize.stdout.log").write_text(
        completed.stdout, encoding="utf-8", newline="\n"
    )
    (mission_dir / "official-finalize.stderr.log").write_text(
        completed.stderr, encoding="utf-8", newline="\n"
    )
    if completed.returncode != 0:
        raise RuntimeError(f"official finalizer exited {completed.returncode}")
    summary = _read_json(output_dir / "batch-summary.json")
    if summary.get("succeeded") != 1 or summary.get("failed") != 0:
        raise RuntimeError("official G2 finalizer did not settle")

    scores = Q._load_final_scores(Path(result["manifest"]))
    _require_hash(HISTORICAL_G1_SCORES, HISTORICAL_G1_SCORE_SHA256, "historical G1 scores")
    g1_scores = _read_json(HISTORICAL_G1_SCORES)
    sample_ids = tuple(str(item["sample_id"]) for item in context["items"])
    g1 = Q._official_a2t_surface(g1_scores, sample_ids)
    g2 = Q._official_a2t_surface(scores, sample_ids)
    bootstrap = Q._grouped_exact_bootstrap(
        items=context["items"],
        m0_by_id=g1["by_id"],
        g1_by_id=g2["by_id"],
    )
    exact_gain = int(g2["exact_count"]) - int(g1["exact_count"])
    tool_gain = int(g2["tool_count"]) - int(g1["tool_count"])
    gates = {
        "parse_count_at_least_103": int(g2["parse_count"]) >= 103,
        "exact_count_at_least_94": int(g2["exact_count"]) >= 94,
        "tool_count_at_least_99": int(g2["tool_count"]) >= 99,
        "slot_micro_f1_at_least_0_90": float(g2["slot_f1"]) >= 0.90,
        "paired_exact_grouped_ci90_lower_strictly_positive": float(bootstrap["ci_low"]) > 0,
    }
    diagnostic = {
        "schema": "saea-a2t-construction-semantic-ground-diagnostic-result-v1",
        "run_id": RUN_ID,
        "counts": {
            "historical_g1_exact": g1["exact_count"],
            "historical_g1_tool": g1["tool_count"],
            "g2_parse": g2["parse_count"],
            "g2_exact": g2["exact_count"],
            "g2_tool": g2["tool_count"],
            "exact_gain_over_g1": exact_gain,
            "tool_gain_over_g1": tool_gain,
        },
        "rates": {
            "historical_g1_exact": int(g1["exact_count"]) / SPLIT_COUNT,
            "historical_g1_tool": int(g1["tool_count"]) / SPLIT_COUNT,
            "g2_parse": int(g2["parse_count"]) / SPLIT_COUNT,
            "g2_exact": int(g2["exact_count"]) / SPLIT_COUNT,
            "g2_tool": int(g2["tool_count"]) / SPLIT_COUNT,
            "g2_slot_micro_f1": g2["slot_f1"],
        },
        "gates": gates,
        "basic_ground_passed": all(gates.values()),
        "target_ground_passed": int(g2["exact_count"]) >= 99,
        "bootstrap": bootstrap,
        "per_tier": g2["aggregate"]["per_tier"],
        "scope": "same-cohort development diagnostic; independent confirmation remains required",
        "decision": (
            "freeze G2 provisionally and prepare fresh-cohort confirmation"
            if all(gates.values())
            else "do not scale; expand observation or knowledge from the measured failure channels"
        ),
        "official_score_sha256": _sha256_file(
            Path(verify_bundle(Path(result["manifest"])).manifest["scores"]["path"])
        ),
    }
    diagnostic_path = mission_dir / "diagnostic-result.json"
    _write_json(diagnostic_path, diagnostic)
    return {
        "official_finalizer": summary,
        "diagnostic": diagnostic,
        "diagnostic_path": str(diagnostic_path),
        "diagnostic_sha256": _sha256_file(diagnostic_path),
    }


def _stop_service(session: object, runtime_receipt: object, receipt_path: Path) -> None:
    stop_session(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
        force_after_timeout=True,
        receipt_path=receipt_path,
    )


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    mission_dir.mkdir(parents=True, exist_ok=False)
    attempt_id = f"attempt-{stamp.lower()}-groundg2"
    values = context["composed"].values
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
    gate.assert_model_touch_allowed(_execution_plan(attempt_id), full_hash=True)
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("decoder must use an explicit loopback port")
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
        result = _run_g2(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=attempt_id,
            run_dir=mission_dir / "g2-construction-semantic-ground",
            session_receipt_path=session_receipt,
        )
        _stop_service(session, runtime_receipt, stop_receipt)
        session = None
        postseal = _finalize_and_analyze(
            mission_dir=mission_dir,
            context=context,
            result=result,
        )
        receipt = {
            "schema": "saea-a2t-construction-semantic-ground-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "attempt_id": attempt_id,
            "elapsed_seconds": time.perf_counter() - started,
            "contacts": {"model": 104, "scorer_manifests": 1, "network_jitter": 0},
            **postseal,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {"run_id": RUN_ID, "attempt_id": attempt_id, "error": repr(error)},
        )
        raise
    finally:
        if session is not None:
            _stop_service(session, runtime_receipt, stop_receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        print(
            json.dumps(
                {
                    "preflight": "passed",
                    "run_id": RUN_ID,
                    "samples": len(context["sample_ids"]),
                    "slot_count": context["geometry"]["slot_count"],
                    "model_contacts": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(_launch(root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
