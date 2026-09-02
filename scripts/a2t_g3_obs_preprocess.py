#!/usr/bin/env python3
"""Preflight or execute the five-contact G3 complete-dialogue packet pass.

Preflight verifies all 40 original packets, all runtime media bytes, the 35/5
binding partition, and the absence of every target artifact. Run mode contacts
only the five complete-dialogue WAVs through the existing CPU feature-cache
sidecar and emits one merged 40-row receipt plus binding map. Generated text is
never assigned, inspected, scored, or used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.analysis.a2t_g3_obs_preprocess import (  # noqa: E402
    G3ObsPreprocessPlan,
    build_execution_plan,
    build_merged_outputs,
    build_preprocess_plan,
)
from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    model_materialization_root,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    PACKET_MANIFEST_NAME,
    legacy_audio_feature_cache_key,
    load_speech_feature_packets,
    materialize_legacy_cached_speech_feature_packets,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

RUN_ID = "SAEA-SN-A2T-G3-OBS-PREPROCESS"
MODEL_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar-a2t-g3-dialogue"
DATASET_FRAGMENT = "audio2tool-g3-pilot-40"
BASELINE_FRAGMENT = "speech-native-preprocess"
EXPERIMENT_FRAGMENT = "a2t-g3-obs-preprocess"
SIDECAR_PORT = 8081
EXPECTED_N_EMBD = 2048
PACKET_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
LEGACY_CACHE_DIR = Path(
    "/home/chao/feat-cache/audio2tool-g3-dialogue-q4km-04ccc72a"
)
PROMOTION_RECEIPT = PACKET_ROOT / "A2T-G3-OBS-40-promotion.json"
BINDING_MAP = PACKET_ROOT / "A2T-G3-OBS-40-bindings.json"
SOURCE_PROMOTIONS = {
    "A2T-CPV2-104-promotion.json": (
        "a9ae338fbc9ba4734553b97a417403923aa6e085d3bd4446848a2abff3b65c87"
    ),
    "A2T-G1-104-promotion.json": (
        "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
    ),
    "A2T-GROUND-QUAL-104-promotion.json": (
        "b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f"
    ),
}
PREPROCESS_INSTRUCTION = (
    "Observe the complete speech signal for deterministic feature preprocessing. "
    "Respond with OK."
)
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}


@dataclass(frozen=True)
class Preflight:
    plan: G3ObsPreprocessPlan
    roster: Mapping[str, object]
    media_manifest: Mapping[str, object]
    values: Mapping[str, object]
    protocol_hash: str
    samples: tuple[Audio2ToolSample, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _load_json(path: Path, expected_sha256: str, label: str) -> Mapping[str, object]:
    if _sha256(path) != expected_sha256:
        raise SystemExit(f"{label} SHA-256 mismatch")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise SystemExit(f"{label} must be a JSON object")
    return document


def _reachable(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def _composed():
    return compose(
        REPO_ROOT,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )


def preflight() -> Preflight:
    """Perform every read-only input, packet, media, and absence check."""

    composed = _composed()
    values = composed.values
    root = data_root()
    roster_path = REPO_ROOT / str(values["a2t_g3_roster"])
    media_path = root / str(values["a2t_g3_runtime_media_manifest"])
    roster = _load_json(
        roster_path, str(values["a2t_g3_roster_sha256"]), "G3 roster"
    )
    media = _load_json(
        media_path,
        str(values["a2t_g3_runtime_media_manifest_sha256"]),
        "G3 runtime-media manifest",
    )
    promotions: dict[str, Mapping[str, object]] = {}
    for name, digest in SOURCE_PROMOTIONS.items():
        path = PACKET_ROOT / name
        promotion = dict(_load_json(path, digest, f"source promotion {name}"))
        promotion["receipt_sha256"] = digest
        promotions[name] = promotion
    plan = build_preprocess_plan(roster, media, promotions)
    if plan.derived_audio_seconds != 197.654375:
        raise SystemExit("derived audio accounting drifted")

    media_by_id = {item["sample_id"]: item for item in media["items"]}
    for sample_id, item in media_by_id.items():
        path = root / str(item["media_relpath"])
        if _sha256(path) != item["audio_sha256"]:
            raise SystemExit(f"runtime media SHA-256 drift for {sample_id}")
    original_bindings = tuple(
        {"packet_id": item.packet_id, "sha256": item.packet_sha256}
        for item in plan.original_verified
    )
    verified_originals = load_speech_feature_packets(
        PACKET_ROOT,
        original_bindings,
        workers=8,
        expected_n_embd=EXPECTED_N_EMBD,
    )
    expected_originals = {item.packet_id: item for item in plan.original_verified}
    for packet in verified_originals:
        expected = expected_originals[packet.packet_id]
        if (
            packet.packet_sha256 != expected.packet_sha256
            or packet.audio_sha256 != expected.audio_sha256
        ):
            raise SystemExit(f"source packet bytes drift for {packet.packet_id}")

    if PROMOTION_RECEIPT.exists() or BINDING_MAP.exists():
        raise SystemExit("G3 merged promotion output already exists")
    samples: list[Audio2ToolSample] = []
    for item in plan.derived:
        packet_manifest = PACKET_ROOT / item.packet_id / PACKET_MANIFEST_NAME
        if packet_manifest.exists():
            raise SystemExit(f"derived packet already exists: {item.packet_id}")
        audio_path = root / item.media_relpath
        cache_key = legacy_audio_feature_cache_key(audio_path.read_bytes())
        if any(LEGACY_CACHE_DIR.glob(f"{cache_key}_o*.feat")):
            raise SystemExit(f"derived feature-cache entry already exists: {item.sample_id}")
        samples.append(
            Audio2ToolSample(
                sample_id=item.contact_sample_id,
                audio_ref=AudioRef(path=item.media_relpath, sha256=item.audio_sha256).validate(),
                audio_seconds=item.audio_seconds,
                media_relpath=item.media_relpath,
            )
        )
    if _reachable(SIDECAR_PORT):
        raise SystemExit(f"sidecar port {SIDECAR_PORT} is already in use")
    return Preflight(
        plan=plan,
        roster=roster,
        media_manifest=media,
        values=values,
        protocol_hash=composed.config_hash,
        samples=tuple(samples),
    )


def _summary(ready: Preflight) -> dict[str, object]:
    return {
        "derived_audio_seconds_exact": ready.plan.derived_audio_seconds,
        "execution_plan_audio_seconds": ready.plan.execution_plan_audio_seconds,
        "original_packets_reused": len(ready.plan.reused),
        "original_packets_verified": len(ready.plan.original_verified),
        "planned_contacts": ready.plan.planned_contacts,
        "protocol_hash": ready.protocol_hash,
        "split_identity_hash": ready.plan.run_identity_hash,
        "target_derived_packets": [item.packet_id for item in ready.plan.derived],
    }


def run(ready: Preflight) -> None:
    """Execute one five-contact attempt, then promote and merge exactly once."""

    root = data_root()
    values = ready.values
    attempt_id = "attempt-%s-a2tg3obs" % datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=False)
    LEGACY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PACKET_ROOT.mkdir(parents=True, exist_ok=True)
    plan: ExecutionPlan = build_execution_plan(
        ready.plan,
        run_id=RUN_ID,
        protocol_hash=ready.protocol_hash,
        attempt_id=attempt_id,
    )
    model_root_value = model_materialization_root(values)
    gate = FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        root,
        Path(model_root_value) if model_root_value is not None else root,
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=Path(model_root_value) if model_root_value is not None else None,
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    runtime_receipt_path = REPO_ROOT / "docs" / runtime_receipt_relpath(values)
    runtime_receipt = load_runtime_receipt(runtime_receipt_path)
    session = start_session(
        runtime_root=Path(model_root_value) if model_root_value is not None else root,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=SIDECAR_PORT,
        session_id=f"{RUN_ID}-{attempt_id}-cpu-sidecar",
        extra_argv=list(values["server_args"]),
        extra_env=dict(values["server_env"]),
        receipt_path=run_dir / "session-preprocess.receipt.json",
        server_log_path=run_dir / "session-preprocess.server.log",
        role="preprocess",
        ready_timeout_seconds=1800.0,
    )
    stop_receipt_path = run_dir / "session-preprocess.stop-receipt.json"
    client = None
    contacts = 0
    try:
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(model_root_value) if model_root_value is not None else root,
        )
        binding = build_payload_binding(
            carrier_lock_key="audio2tool",
            samples=ready.samples,
            data_root=root,
            carrier_root=root,
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=gate,
            transport=transport,
            run_dir=run_dir,
            binding=binding,
            request_id_prefix="a2tg3obs",
        )
        for sample in ready.samples:
            messages = (
                {"role": "system", "content": PREPROCESS_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "media_relpath": sample.media_relpath}
                    ],
                },
            )
            client.complete(messages, decoding_params=DECODING_PARAMS)
            contacts += 1
        client.close()
    finally:
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path(model_root_value) if model_root_value is not None else root,
            receipt_path=stop_receipt_path,
            force_after_timeout=True,
        )
    if contacts != 5:
        raise SystemExit(f"only {contacts} of five contacts completed; no promotion written")

    gguf_files = runtime_receipt["gguf_files"]
    decoder = [entry for entry in gguf_files if "mmproj" not in Path(entry["path"]).name.lower()]
    mmproj = [entry for entry in gguf_files if "mmproj" in Path(entry["path"]).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit("runtime receipt must bind one decoder and one mmproj")
    derived_packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=PACKET_ROOT,
        bindings=tuple(
            {
                "packet_id": item.packet_id,
                "audio_path": str(root / item.media_relpath),
            }
            for item in ready.plan.derived
        ),
        legacy_cache_dir=LEGACY_CACHE_DIR,
        encoder_receipt_sha256=_canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder[0]["sha256"]),
        mmproj_sha256=str(mmproj[0]["sha256"]),
        expected_n_embd=EXPECTED_N_EMBD,
        causal_attention=True,
        workers=5,
    )
    packet_rows = [
        {
            "audio_sha256": packet.audio_sha256,
            "decoder_gguf_sha256": packet.decoder_gguf_sha256,
            "mmproj_sha256": packet.mmproj_sha256,
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
        }
        for packet in derived_packets
    ]
    receipt, bindings = build_merged_outputs(
        ready.plan, packet_rows, feature_root=str(PACKET_ROOT)
    )
    receipt["binding_map_path"] = str(BINDING_MAP)
    receipt["runtime_receipt_sha256"] = _canonical_sha256(runtime_receipt)
    with BINDING_MAP.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(bindings, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    with PROMOTION_RECEIPT.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    ready = preflight()
    if args.preflight_only:
        print(json.dumps(_summary(ready), indent=2, sort_keys=True))
        return 0
    run(ready)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
