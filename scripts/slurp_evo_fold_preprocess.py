#!/usr/bin/env python3
"""Receipt-bound EVO-S1 fold speech-feature preprocessing and packet promotion.

Exposure row ``SAEA-SLURP-EVO-FOLD-PACKETS-V2`` (contracts
``configs/experiment/slurp-evo-fold-{a,b}-preprocess.json``), preregistration
section 13 item 3. SLURP sibling of ``scripts/a2t_g1_preprocess.py``, following
``SAEA-SN-DEV1000-PREPROCESS`` (2026-08-24), which is the precedent the row names.

Two phases in one invocation, per fold:

1. ENCODE -- a CPU-only llama-server sidecar on port 8081 (``-ngl 0
   --no-mmproj-offload``, ``receipts/runtime-q4km-preprocess.json``: decoder AND
   bf16 mmproj) is spawned under its own session receipt, driven with one contact
   per fold row at ``max_tokens: 1``, and stopped with its own stop receipt. The
   prompt is a fixed minimal instruction: the legacy feature-cache key is the
   FNV-1a hash of the media bytes ALONE, so the prompt cannot affect the cached
   features. No response is read semantically and no gold is ever opened.
2. PROMOTE -- ``core.model.speech_features.
   materialize_legacy_cached_speech_feature_packets`` promotes the warm entries
   into audited packets under the resident ``04ccc72a`` packet root and writes the
   fold's own promotion receipt. Zero contacts, and only after a verified normal
   stop.

Label-free by construction: samples are built from the fold's frozen
``saea-speech-native-runtime-view-v1`` dataset fragment, which carries media
identity and nothing else, and every media file is re-hashed against the view's own
record before it can become a sample. `-ngl 0` means this pass leaves the GPU free.

Modes::

    python scripts/slurp_evo_fold_preprocess.py --fold a --preflight-only
    python scripts/slurp_evo_fold_preprocess.py --fold a --run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.base import TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose, d1_media_supplement_relpath, d1_media_supplement_sha256)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    legacy_audio_feature_cache_key, materialize_legacy_cached_speech_feature_packets)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt, start_session, stop_session)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir, data_root, load_lock, umbrella_lock_path)
from speech_aware_evidence_acquisition.data.slurp import SLURP_LOCK_KEY  # noqa: E402
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient, build_payload_binding)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpSample  # noqa: E402
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

RUNTIME_ROOT = Path("/home/chao")
RUN_ID = "SAEA-SLURP-EVO-FOLD-PACKETS-V2"
MODEL_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar"
BASELINE_FRAGMENT = "speech-native-preprocess"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
SIDECAR_PORT = 8081
INFERENCE_PORT = 8080
EXPECTED_N_EMBD = 2048
PREPROCESS_INSTRUCTION = (
    "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
)
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}
# A plan's budget is metered run-CUMULATIVELY across every attempt of a run id
# (``core.model.adapter`` re-reads the attempt store's prior actuals on every
# request), so a SUCCESSOR session must declare prior durable spend PLUS its own
# worst case -- not its own fold's arithmetic alone. These defaults are the FIRST
# session of each fold; ``--plan-calls`` / ``--plan-speech-seconds`` are how a
# successor states the cumulative figure, and the registered ceilings
# (2,200 calls / 6,300 speech seconds / 2.0 GPU-h) bound both.
PLAN_BY_FOLD = {"a": (1090, 3085, 1.0), "b": (1090, 3155, 1.0)}


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def roster_samples(values: Mapping[str, object], root: Path, workers: int) -> tuple[SlurpSample, ...]:
    """Label-free samples from the frozen runtime view, each file re-hashed."""

    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    if int(values.get("count", len(items))) != len(items):
        raise SystemExit("runtime view count disagrees with its own items")

    def build(item: Mapping[str, object]) -> SlurpSample:
        sample_id = str(item["sample_id"])
        if not sample_id.startswith("slurp:train:"):
            raise SystemExit("the EVO-S1 folds are TRAIN rosters; %r is not" % sample_id)
        measured = sha256_file(root / str(item["media_relpath"]))
        if measured != str(item["audio_sha256"]):
            raise SystemExit("media %s hashes to %s" % (item["media_relpath"], measured))
        return SlurpSample(
            sample_id=sample_id,
            audio_ref=AudioRef(path=str(item["media_relpath"]), sha256=measured).validate(),
            audio_seconds=float(item["audio_seconds"]), utterance_id=sample_id.split(":")[2],
            media_relpath=str(item["media_relpath"]), scenario="", action="", intent="", entities=())

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        samples = list(pool.map(build, items))
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


def _write_union_receipt(args) -> int:
    """One promotion receipt over both folds, from the two the sessions wrote.

    Zero contacts, no server, no encoder: a deterministic merge of two committed
    documents whose parents are recorded by sha256, so a reader can rebuild it or
    refuse it. It exists because a candidate portfolio has ONE artifact and TWO
    fold fragment variants copied from ONE base, and a base can name one receipt.
    """

    root = data_root()
    parents, packets, seen = [], [], set()
    for fold in sorted(PLAN_BY_FOLD):
        values = compose(REPO, MODEL_FRAGMENT, f"slurp-speech-native-evo-fold-{fold}-1080",
                         BASELINE_FRAGMENT, f"slurp-evo-fold-{fold}-preprocess").values
        path = Path(str(values["promotion_receipt"]))
        document = json.loads(path.read_text(encoding="utf-8"))
        parents.append({"fold": str(values["fold"]), "path": str(path),
                        "sha256": sha256_file(path), "count": int(document["count"])})
        for entry in document["packets"]:
            packet_id = str(entry["packet_id"])
            if packet_id in seen:
                raise SystemExit("the two folds share packet %s; they are disjoint by draw" % packet_id)
            seen.add(packet_id)
            packets.append(dict(entry))
        for key in ("feature_root", "legacy_cache_dir", "runtime_receipt_sha256"):
            if document[key] != json.loads(Path(str(parents[0]["path"])).read_text(encoding="utf-8"))[key]:
                raise SystemExit("the two promotion receipts disagree on %s" % key)
    first = json.loads(Path(str(parents[0]["path"])).read_text(encoding="utf-8"))
    receipt = {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "count": len(packets),
        "feature_root": first["feature_root"],
        "legacy_cache_dir": first["legacy_cache_dir"],
        "runtime_receipt_sha256": first["runtime_receipt_sha256"],
        "preprocess_session_id": "union of %s" % ", ".join(p["fold"] for p in parents),
        "preprocess_session_receipt_sha256": first["preprocess_session_receipt_sha256"],
        "preprocess_stop_receipt_sha256": first["preprocess_stop_receipt_sha256"],
        "dataset_runtime_view_sha256": first["dataset_runtime_view_sha256"],
        "union_of": parents,
        "union_note": (
            "MODEL-FREE MERGE, zero contacts. The two per-fold receipts are unchanged and are "
            "the authority; this document exists only because a candidate portfolio has one "
            "artifact and two fold fragment variants copied from ONE base fragment, and a base "
            "fragment names one promotion receipt. Every packet entry is copied verbatim from "
            "the fold receipt that promoted it, and the two folds are proved disjoint by draw."
        ),
        "packets": sorted(packets, key=lambda entry: str(entry["packet_id"])),
    }
    out = Path(first["feature_root"]) / "EVO-FOLDS-V2-promotion.json"
    if out.exists():
        raise SystemExit("union promotion receipt already exists: %s" % out)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    summary = {"path": str(out), "sha256": sha256_file(out), "count": len(packets),
               "parents": parents, "data_root": str(root)}
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", default=None, choices=sorted(PLAN_BY_FOLD))
    parser.add_argument("--workers", type=int, default=4, help="encode concurrency; the sidecar serves -np 4")
    parser.add_argument("--promote-workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--plan-calls", type=int, default=None,
                        help="cumulative call ceiling this attempt declares (prior spend + its own)")
    parser.add_argument("--plan-speech-seconds", type=int, default=None,
                        help="cumulative speech-second ceiling this attempt declares")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument(
        "--union-receipt", action="store_true",
        help=(
            "MODEL-FREE: merge the two per-fold promotion receipts into one covering all "
            "2,160 rows. rails.evolution.write_candidate_fragments copies ONE base fragment "
            "into a fold-a and a fold-b variant, so the base can name only one promotion "
            "receipt and it has to cover both folds; the per-fold receipts stay exactly as "
            "the two sessions wrote them and this one records their sha256s as its parents"
        ),
    )
    args = parser.parse_args(argv)

    if args.union_receipt:
        return _write_union_receipt(args)

    if args.fold is None:
        raise SystemExit("--fold is required for --preflight-only and --run")
    dataset = f"slurp-speech-native-evo-fold-{args.fold}-1080"
    experiment = f"slurp-evo-fold-{args.fold}-preprocess"
    lock, root = load_lock(umbrella_lock_path()), data_root()
    composed = compose(REPO, MODEL_FRAGMENT, dataset, BASELINE_FRAGMENT, experiment)
    values = composed.values
    if str(values["experiment_id"]) != RUN_ID:
        raise SystemExit("experiment fragment names a different run id")
    packet_root = Path(str(values["feature_root"]))
    legacy_cache = Path(str(values["legacy_cache_dir"]))
    promotion_receipt = Path(str(values["promotion_receipt"]))
    samples = roster_samples(values, root, args.promote_workers)
    audio_seconds = sum(float(sample.audio_seconds) for sample in samples)
    log("fold %s: %d samples, %.6f audio-s, config %s"
        % (args.fold, len(samples), audio_seconds, composed.config_hash[:16]))

    warm = sum(
        1 for sample in samples
        if any(legacy_cache.glob("%s_o*.feat"
                                 % legacy_audio_feature_cache_key((root / sample.media_relpath).read_bytes())))
    )
    log("artifact preflight: %d/%d legacy cache entries warm; promotion receipt exists=%s"
        % (warm, len(samples), promotion_receipt.exists()))
    if promotion_receipt.exists():
        raise SystemExit("promotion receipt already exists: %s" % promotion_receipt)

    binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY, samples=samples, data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root))
    media_facts = {
        sample_id: (binding.media_relpaths[sample_id], binding.sample_facts[sample_id][0])
        for sample_id in sorted(binding.allowed_sample_ids)
    }
    gate = FrozenCoreGate.for_study_repo(
        REPO, root, RUNTIME_ROOT, runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values))
    gate.verify_media_identity(SLURP_LOCK_KEY, media_facts)
    log("D1 media identity PASS for %d samples" % len(media_facts))

    if args.preflight_only:
        log("PREFLIGHT-ONLY PASS: inputs verified, zero contacts, no session, no gate open")
        return 0

    for port, label in ((SIDECAR_PORT, "sidecar"), ):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                raise SystemExit("something already listens on the %s port %d" % (label, port))
        except OSError:
            pass
    log("preflight: %d free (the GPU inference port %d is not touched)" % (SIDECAR_PORT, INFERENCE_PORT))

    calls, speech, gpu_hours = PLAN_BY_FOLD[args.fold]
    calls = args.plan_calls if args.plan_calls is not None else calls
    speech = args.plan_speech_seconds if args.plan_speech_seconds is not None else speech
    attempt_id = args.attempt_id or ("attempt-packets-fold-%s" % args.fold)
    plan = ExecutionPlan(
        run_id=RUN_ID, execution_profile=str(values["execution_profile"]),
        carrier_lock_key=SLURP_LOCK_KEY, split_role="discovery",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=calls, planned_gpu_hours=gpu_hours,
        planned_speech_audio_seconds=speech, protocol_hash=composed.config_hash,
        attempt_id=attempt_id).validate()
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log("spawning the CPU-only preprocessing sidecar on %d" % SIDECAR_PORT)
    session = start_session(
        runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
        host="127.0.0.1", port=SIDECAR_PORT, session_id="%s-%s-cpu-sidecar" % (RUN_ID, attempt_id),
        extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
        receipt_path=run_dir / "session-preprocess.receipt.json",
        server_log_path=run_dir / "session-preprocess.server.log",
        role="preprocess", ready_timeout_seconds=1800.0)
    log("sidecar up: pid=%s port=%s" % (session.pid, session.port))

    contacts, failures, started = 0, [], time.time()
    try:
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT)
        client = FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir,
                                  binding=binding, request_id_prefix="slurpevoprep")

        def encode(sample: SlurpSample) -> str | None:
            messages = (
                {"role": "system", "content": PREPROCESS_INSTRUCTION},
                {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
            )
            try:
                client.complete(messages, decoding_params=DECODING_PARAMS)
                return None
            except Exception as error:  # noqa: BLE001 -- reported, never masked
                return "%s: %r" % (sample.sample_id, error)

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            for index, problem in enumerate(pool.map(encode, samples), start=1):
                if problem is None:
                    contacts += 1
                else:
                    failures.append(problem)
                    log("contact FAILED %s" % problem)
                if index % 100 == 0 or index == len(samples):
                    log("encode %d/%d (%d ok, %d failed, %.1fs)"
                        % (index, len(samples), contacts, len(failures), time.time() - started))
        core_receipt = client.close()
    finally:
        stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                            receipt_path=run_dir / "session-preprocess.stop-receipt.json",
                            force_after_timeout=True)
        log("sidecar stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
    encode_seconds = time.time() - started
    if failures:
        raise SystemExit("%d encode contacts failed; refusing to promote a partial cache: %r"
                         % (len(failures), failures[:5]))

    gguf = runtime_receipt["gguf_files"]
    decoder = [e for e in gguf if "mmproj" not in Path(str(e["path"])).name.lower()]
    mmproj = [e for e in gguf if "mmproj" in Path(str(e["path"])).name.lower()]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit("preprocess receipt must bind exactly one decoder and one mmproj")
    promote_started = time.time()
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=packet_root,
        bindings=tuple({"packet_id": sample.sample_id.replace(":", "/"),
                        "audio_path": str(root / sample.media_relpath)} for sample in samples),
        legacy_cache_dir=legacy_cache, encoder_receipt_sha256=canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder[0]["sha256"]), mmproj_sha256=str(mmproj[0]["sha256"]),
        expected_n_embd=EXPECTED_N_EMBD, causal_attention=True, workers=args.promote_workers)
    promote_seconds = time.time() - promote_started
    if len(packets) != len(samples):
        raise SystemExit("promotion produced %d packets for %d samples" % (len(packets), len(samples)))
    audio_by_packet = {sample.sample_id.replace(":", "/"): sample.audio_ref.sha256 for sample in samples}
    for packet in packets:
        if packet.audio_sha256 != audio_by_packet[packet.packet_id]:
            raise SystemExit("promoted packet %s carries a different audio sha256" % packet.packet_id)
    tokens = {packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks) for packet in packets}

    receipt = {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "count": len(packets),
        "dataset_runtime_view_sha256": str(values["runtime_view_sha256"]),
        "feature_root": str(packet_root),
        "legacy_cache_dir": str(legacy_cache),
        "preprocess_session_id": session.session_id,
        "preprocess_session_receipt_sha256": canonical_sha256(session.as_json()),
        "preprocess_stop_receipt_sha256": canonical_sha256(stop),
        "runtime_receipt_sha256": canonical_sha256(runtime_receipt),
        "packets": [
            {"packet_id": packet.packet_id, "packet_sha256": packet.packet_sha256,
             "audio_sha256": packet.audio_sha256,
             "decoder_gguf_sha256": str(decoder[0]["sha256"]), "mmproj_sha256": str(mmproj[0]["sha256"])}
            for packet in sorted(packets, key=lambda entry: entry.packet_id)
        ],
    }
    with promotion_receipt.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    log("promotion receipt %s (sha256 %s)" % (promotion_receipt, sha256_file(promotion_receipt)[:16]))

    report = {
        "schema": "saea-slurp-evo-fold-preprocess-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": RUN_ID, "attempt_id": attempt_id, "fold": str(values["fold"]),
        "config_fragments": {"model": MODEL_FRAGMENT, "dataset": dataset,
                             "baseline": BASELINE_FRAGMENT, "experiment": experiment},
        "config_hash": composed.config_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "rows": len(samples), "audio_seconds": round(audio_seconds, 6),
        "declared_plan": {"calls": calls, "speech_audio_seconds": speech,
                          "gpu_hours": gpu_hours,
                          "basis": "run-cumulative: prior durable spend on this run id plus this attempt's own worst case"},
        "legacy_cache_warm_before": warm,
        "contacts": contacts, "failures": failures,
        "encode_seconds": round(encode_seconds, 3),
        "encode_rows_per_second": round(len(samples) / max(encode_seconds, 1e-9), 4),
        "encode_workers": args.workers,
        "promote_seconds": round(promote_seconds, 3),
        "promote_packets_per_second": round(len(packets) / max(promote_seconds, 1e-9), 4),
        "promote_workers": args.promote_workers,
        "promotion_receipt": str(promotion_receipt),
        "promotion_receipt_sha256": sha256_file(promotion_receipt),
        "packet_tokens": {"min": min(tokens.values()), "max": max(tokens.values()),
                          "total": sum(tokens.values())},
        "core_client": {"trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
                        "cost": core_receipt.get("cost")},
        "session": {"session_id": session.session_id, "pid": session.pid, "stop": stop},
        "gpu_offload": "-ngl 0 --no-mmproj-offload: this pass leaves the GPU free",
    }
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        log("wrote %s" % args.output)
    else:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
