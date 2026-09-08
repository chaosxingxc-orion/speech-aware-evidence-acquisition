#!/usr/bin/env python3
"""Receipt-bound SAEA-SN-DEV1000-TS2-PREPROCESS-V1 encode + packet promotion.

Committed successor of the scratchpad iterations (v1-v3) that found and fixed
the confinement gap this row needed (``build_payload_binding``'s
``derived_media_roots`` argument, wired into both preflight's D1 media-identity
check and the encode client's own payload binding below) and the missing
per-dataset-campaign legacy feature-cache directory (auto-created here, with a
stated reason, instead of requiring an operator to ``mkdir`` it out of band).
Every path this script WRITES to is outside the git tree: the CPU sidecar's
legacy feature cache and packet root under ``/home/chao/feat-cache/...``, and
run receipts under ``$SPEECHRL_DATA_DIR/runs/...``. It only ever READS this
repository (to import the package and its committed config fragments /
runtime receipt / exposure ledger) and never mutates it -- no ``git add``, no
``git commit``, no stash, no worktree prune, ever, from this script.

Two named modes, run in order:

  --gate    4-row dry run (a MEMBERSHIP subset of the full 1,000-row split,
            not a separate dataset fragment -- see GATE_SAMPLE_IDS below).
            Encodes the 4 rows through the CPU-only sidecar, promotes their
            packets into the REAL @ts2 packet root (packet-level promotion is
            idempotent, so the later --full pass re-verifying these same 4 is
            a no-op), and checks the token-count falsifier against the REAL
            sealed DEV-1000 promotion receipt plus the
            analysis.e22_short_clip_encoding formula. Writes its own small
            gate receipt (DEV-1000-TAIL2S-GATE4-promotion.json), never the
            final one.
  --full    The 1,000-row pass (dataset fragment
            slurp-speech-native-dev1000-tail2s). SKIPS an encode contact for
            any row whose legacy-cache entry is already warm -- only the
            packet promotion touches them again, at zero contacts -- so a
            re-run after a partial prior attempt only pays for the rows that
            are still cold. Writes the FINAL promotion receipt
            (DEV-1000-TAIL2S-promotion.json).

RECOVERY NOTE (2026-09-08): the first --full attempt on this row
(attempt-full-v3-20260908T030246Z) completed 995 of 996 contacts and was
refused 2.8046875 audio-s short of the then-registered 4,905-second ceiling
on its very last row (slurp:devel:017167:audio-1498573910@ts2, 3.6638125
audio-s) -- a real, durable, but wasted duplicate encode earlier in the same
task (see docs/exposure-ledger.md's recovery narrative on this row) had
already consumed the headroom a clean run would have had. The ledger's
registered speech-audio-seconds cell was raised 4905 -> 4908 in the SAME
recovery re-registration that this script's own PLAN_SPEECH_SECONDS_CEILING
below must match (the adapter's cumulative budget check compares against the
ATTEMPT's own declared plan value, not the ledger cell directly -- the ledger
cell only bounds the maximum an attempt may legally declare). A successor
--full --run invocation of this same script skips the 999 rows already warm
in the legacy cache and encodes only the one row the shortfall left short,
then promotes all 1,000 packets.

Modes::

    python scripts/slurp_dev1000_ts2_preprocess.py --gate --preflight-only
    python scripts/slurp_dev1000_ts2_preprocess.py --gate --run
    python scripts/slurp_dev1000_ts2_preprocess.py --full --preflight-only
    python scripts/slurp_dev1000_ts2_preprocess.py --full --run
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

REPO = Path(__file__).resolve().parent.parent
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.analysis.e22_short_clip_encoding import (  # noqa: E402
    llamacpp_audio_tokens)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS, declared_derived_media_roots)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose, d1_media_supplement_relpath, d1_media_supplement_sha256)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    legacy_audio_feature_cache_key, load_speech_feature_packet,
    materialize_legacy_cached_speech_feature_packets)
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
RUN_ID = "SAEA-SN-DEV1000-TS2-PREPROCESS-V1"
MODEL_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar-slurp-ts2"
BASELINE_FRAGMENT = "speech-native-preprocess"
EXPERIMENT_FRAGMENT = "slurp-dev1000-ts2-preprocess"
DATASET_FULL = "slurp-speech-native-dev1000-tail2s"
# The row's OWN registered split_identity_hash (9f78d0ff...) is the FULL
# fragment's, and the row's text is explicit that "the 4 rows are inside the
# 1,000" -- same split, same identity, a MEMBERSHIP subset, not a separate
# split. configs/dataset/slurp-speech-native-dev1000-tail2s-smoke4.json is a
# DIFFERENT, independently-identified split (its own split_identity_hash
# c80d2295...) built for the LATER CELL's own smoke registration
# (SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1 / closed-list-tail2s-smoke-4);
# composing it here trips gate_exposure's split-identity-hash check against
# THIS row (confirmed 2026-09-07: GateClosed, "row 9f78d0ff... vs plan
# c80d2295..."). So the gate selects 4 ids OUT OF the full fragment instead --
# the SAME 4 ids the smoke4 fragment names, for later-cell consistency, but
# sourced (and identity-bound) from DATASET_FULL.
GATE_SAMPLE_IDS = frozenset({
    "slurp:devel:000011:audio-1497266596@ts2",
    "slurp:devel:000053:audio-1498758443@ts2",
    "slurp:devel:000058:audio-1488637952@ts2",
    "slurp:devel:000068:audio-1488550098@ts2",
})
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
SIDECAR_PORT = 8081
INFERENCE_PORT = 8080  # never touched -- the GPU flight owns it
EXPECTED_N_EMBD = 2048
TAIL_SAMPLES = 32000  # 2.0 s * 16 kHz, the additive @ts2 rule
SEALED_FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
PREPROCESS_INSTRUCTION = (
    "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
)
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}
# Registered ceiling this row carries in docs/exposure-ledger.md: 1,004 calls /
# 4,908 speech-audio-seconds (raised from the row's original 4,905 by the
# 2026-09-08 recovery re-registration -- see the module docstring) / a nominal
# positive GPU-hours placeholder. Both --gate and --full attempts declare the
# FULL registered ceiling (legal: the row-level check is `registered >=
# planned`, equality included) rather than a tight per-attempt estimate, so
# neither attempt's own arithmetic can trip the per-request cumulative-budget
# check (core.model.adapter: sibling-attempts' actual + this attempt's own
# running total + this request must stay <= this attempt's OWN declared plan
# value) -- and so that a successor attempt after a partial prior one is
# never refused merely for being a later attempt on the same run_id.
#
# The GPU-hours cell is a required-positive contract formality, not a
# physical measurement: contracts.plan.ExecutionPlan.validate() unconditionally
# refuses planned_gpu_hours <= 0 ("must be a finite positive number"), and
# there is no role="preprocess" or -ngl-0 exemption anywhere in contracts/.
# Both named precedents this row follows registered a nominal positive
# placeholder instead (SAEA-SN-DEV1000-PREPROCESS: 1.0 for 520 calls;
# SAEA-SLURP-EVO-FOLD-PACKETS-V2: 2.0 for 2,200 calls); the true realized GPU
# usage of a "-ngl 0 --no-mmproj-offload" CPU sidecar is 0 either way.
PLAN_CALLS_CEILING = 1004
PLAN_SPEECH_SECONDS_CEILING = 4908
PLAN_GPU_HOURS_CEILING = 0.1  # matches the registered ledger cell


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


def roster_samples(
    values: Mapping[str, object], root: Path, workers: int,
    select_ids: frozenset[str] | None = None,
) -> tuple[SlurpSample, ...]:
    """Label-free samples from the frozen @ts2 runtime view, each file re-hashed.

    ``select_ids``, when given, is a MEMBERSHIP filter over the SAME split
    (the gate's 4-row dry run): the strict ``count == len(items)`` identity
    check is skipped in that case (deliberately selecting fewer than the
    registered count), replaced by asserting every requested id is actually a
    member of this split -- fail-closed against a typo'd or foreign id.
    """

    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a speech-native runtime view")
    if select_ids is None:
        if int(values.get("count", len(items))) != len(items):
            raise SystemExit("runtime view count disagrees with its own items")
    else:
        items = [item for item in items if str(item["sample_id"]) in select_ids]
        found = {str(item["sample_id"]) for item in items}
        missing = select_ids - found
        if missing:
            raise SystemExit("selected id(s) not members of this split: %r" % sorted(missing))
    if values.get("split_role") != "dev":
        raise SystemExit("this row is DEV-1000 only; dataset fragment split_role is not 'dev'")

    def build(item: Mapping[str, object]) -> SlurpSample:
        sample_id = str(item["sample_id"])
        if not sample_id.startswith("slurp:devel:"):
            raise SystemExit("DEV-1000 rows are 'slurp:devel:...'; %r is not" % sample_id)
        if not sample_id.endswith("@ts2"):
            raise SystemExit("every row of this view must carry the @ts2 suffix: %r" % sample_id)
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


def packet_id_for(sample_id: str) -> str:
    return sample_id.replace(":", "/")


def is_warm(legacy_cache: Path, media_bytes: bytes) -> bool:
    key = legacy_audio_feature_cache_key(media_bytes)
    return any(legacy_cache.glob("%s_o*.feat" % key))


def ensure_legacy_cache_dir(legacy_cache: Path) -> None:
    """Auto-create the per-dataset-campaign legacy feature-cache directory.

    ``docs/featcache-directories.md`` names the convention (one directory per
    NEW dataset campaign, never reusing another dataset's or encoder's cache)
    but nothing in ``core/session`` or any preprocessing script created it
    automatically -- an earlier attempt on this same row found the directory
    missing only at PROMOTION time (``core.model.speech_features``'s
    ``_legacy_cached_chunks`` refuses a cache directory that is not already a
    directory), after the CPU sidecar had already been driven through a full
    encode pass with nowhere to persist its cached embeddings: a real,
    durable, but entirely wasted contact. Creating the directory here, before
    the sidecar is ever spawned, means a missing directory is fixed with zero
    contacts instead of one wasted encode pass.
    """

    if legacy_cache.is_dir():
        return
    log("creating legacy feature-cache directory %s: missing before this dataset "
        "campaign's first use (docs/featcache-directories.md's per-dataset-campaign "
        "convention); the CPU sidecar cannot persist a cache it cannot find, and "
        "promotion refuses to read a cache directory that does not exist" % legacy_cache)
    legacy_cache.mkdir(parents=True, exist_ok=True)


def run_gate_check(packet_root: Path, samples: Sequence[SlurpSample]) -> dict[str, object]:
    """The token-count falsifier: the promoted @ts2 packet's token count must
    equal the sealed packet's own (real, measured) token count plus exactly
    what analysis.e22_short_clip_encoding predicts a 32,000-sample tail adds.
    Two independent things are checked per row, not one: that the formula
    reproduces the REAL sealed packet's token count on the untailed sample
    count, and that it reproduces the REAL freshly-promoted @ts2 packet's
    token count on the tailed one. Raises on any disagreement.
    """

    rows = []
    for sample in samples:
        ts2_packet_id = packet_id_for(sample.sample_id)
        sealed_packet_id = ts2_packet_id.rsplit("@ts2", 1)[0]
        n_ts2 = int(round(sample.audio_seconds * 16000))
        n_sealed = n_ts2 - TAIL_SAMPLES
        if n_sealed <= 0:
            raise SystemExit("row %s: sealed sample count is non-positive" % sample.sample_id)

        sealed_packet = load_speech_feature_packet(SEALED_FEATURE_ROOT, sealed_packet_id)
        ts2_packet = load_speech_feature_packet(packet_root, ts2_packet_id)
        measured_sealed = sum(chunk.n_tokens for chunk in sealed_packet.chunks)
        measured_ts2 = sum(chunk.n_tokens for chunk in ts2_packet.chunks)
        formula_sealed = llamacpp_audio_tokens(n_sealed)
        formula_ts2 = llamacpp_audio_tokens(n_ts2)

        if formula_sealed != measured_sealed:
            raise SystemExit(
                "row %s: formula predicts %d sealed tokens but the REAL sealed packet "
                "carries %d" % (sample.sample_id, formula_sealed, measured_sealed))
        if formula_ts2 != measured_ts2:
            raise SystemExit(
                "row %s: formula predicts %d @ts2 tokens but the REAL promoted packet "
                "carries %d -- gate FAILS" % (sample.sample_id, formula_ts2, measured_ts2))
        tail_blocks_tokens = measured_ts2 - measured_sealed
        if tail_blocks_tokens != (formula_ts2 - formula_sealed):
            raise SystemExit("row %s: tail-block token delta disagrees with the formula" % sample.sample_id)
        rows.append({
            "sample_id": sample.sample_id, "sealed_packet_id": sealed_packet_id,
            "n_sealed_samples": n_sealed, "n_ts2_samples": n_ts2,
            "sealed_tokens": measured_sealed, "ts2_tokens": measured_ts2,
            "tail_added_tokens": tail_blocks_tokens,
        })
    return {"gate": "PASS", "rows": rows}


def _compose_for(dataset: str) -> tuple[object, Path]:
    root = data_root()
    composed = compose(REPO, MODEL_FRAGMENT, dataset, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    if str(composed.values["experiment_id"]) != RUN_ID:
        raise SystemExit("experiment fragment names a different run id")
    return composed, root


def _preflight(
    dataset: str, workers: int, select_ids: frozenset[str] | None = None,
) -> tuple[object, Path, tuple[SlurpSample, ...], object]:
    composed, root = _compose_for(dataset)
    values = composed.values
    if "-ngl" not in values["server_args"] or values["server_args"][values["server_args"].index("-ngl") + 1] != "0":
        raise SystemExit("refusing: sidecar server_args do not carry '-ngl 0'")
    if "--no-mmproj-offload" not in values["server_args"]:
        raise SystemExit("refusing: sidecar server_args do not carry --no-mmproj-offload")
    lock = load_lock(umbrella_lock_path())
    samples = roster_samples(values, root, workers, select_ids=select_ids)
    audio_seconds = sum(float(sample.audio_seconds) for sample in samples)
    log("dataset %s: %d samples, %.6f audio-s, config %s"
        % (dataset, len(samples), audio_seconds, composed.config_hash[:16]))

    binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY, samples=samples, data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
        derived_media_roots=declared_derived_media_roots(values, root))
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
    return composed, root, samples, gate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gate", action="store_true", help="4-row dry run (a membership subset)")
    mode.add_argument("--full", action="store_true", help="the 1,000-row pass")
    step = parser.add_mutually_exclusive_group(required=True)
    step.add_argument("--preflight-only", action="store_true")
    step.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=4, help="encode concurrency; the sidecar serves -np 4")
    parser.add_argument("--promote-workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--attempt-id", default=None)
    args = parser.parse_args(argv)

    dataset = DATASET_FULL
    select_ids = GATE_SAMPLE_IDS if args.gate else None
    composed, root, samples, gate = _preflight(dataset, args.promote_workers, select_ids=select_ids)
    values = composed.values
    packet_root = Path(str(values["feature_root"]))
    legacy_cache = Path(str(values["legacy_cache_dir"]))
    final_promotion_receipt = Path(str(values["promotion_receipt"]))
    out_receipt = (
        packet_root / "DEV-1000-TAIL2S-GATE4-promotion.json" if args.gate else final_promotion_receipt
    )

    warm_media = {}
    for sample in samples:
        media_bytes = (root / sample.media_relpath).read_bytes()
        warm_media[sample.sample_id] = is_warm(legacy_cache, media_bytes) if legacy_cache.is_dir() else False
    warm_count = sum(1 for value in warm_media.values() if value)
    log("artifact preflight: %d/%d legacy cache entries already warm; feature_root exists=%s"
        % (warm_count, len(samples), packet_root.is_dir()))
    if args.gate and out_receipt.exists():
        raise SystemExit("gate receipt already exists: %s" % out_receipt)
    if args.full and final_promotion_receipt.exists():
        raise SystemExit("FINAL promotion receipt already exists: %s" % final_promotion_receipt)

    if args.preflight_only:
        log("PREFLIGHT-ONLY PASS: inputs verified, zero contacts, no session, no gate open")
        return 0

    ensure_legacy_cache_dir(legacy_cache)

    for port, label in ((SIDECAR_PORT, "sidecar"),):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                raise SystemExit("something already listens on the %s port %d" % (label, port))
        except OSError:
            pass
    log("preflight: %d free (the GPU inference port %d is not touched)" % (SIDECAR_PORT, INFERENCE_PORT))

    attempt_id = args.attempt_id or (
        "attempt-tail2s-gate" if args.gate else "attempt-tail2s-full"
    )
    plan = ExecutionPlan(
        run_id=RUN_ID, execution_profile=str(values["execution_profile"]),
        carrier_lock_key=SLURP_LOCK_KEY, split_role="dev",
        split_identity_hash=str(values["split_identity_hash"]),
        planned_model_calls=PLAN_CALLS_CEILING, planned_gpu_hours=PLAN_GPU_HOURS_CEILING,
        planned_speech_audio_seconds=PLAN_SPEECH_SECONDS_CEILING, protocol_hash=composed.config_hash,
        attempt_id=attempt_id).validate()
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)

    encode_targets = samples if args.gate else tuple(s for s in samples if not warm_media[s.sample_id])
    skipped = len(samples) - len(encode_targets)
    log("encode plan: %d of %d rows need a contact (%d already warm, skipped)"
        % (len(encode_targets), len(samples), skipped))

    contacts, failures, started = 0, [], time.time()
    core_receipt = None
    if encode_targets:
        log("spawning the CPU-only preprocessing sidecar on %d" % SIDECAR_PORT)
        server_env = dict(values["server_env"])
        server_env["CUDA_VISIBLE_DEVICES"] = ""
        session = start_session(
            runtime_root=RUNTIME_ROOT, data_root=root, runtime_receipt=runtime_receipt,
            host="127.0.0.1", port=SIDECAR_PORT, session_id="%s-%s-cpu-sidecar" % (RUN_ID, attempt_id),
            extra_argv=list(values["server_args"]), extra_env=server_env,
            receipt_path=run_dir / "session-preprocess.receipt.json",
            server_log_path=run_dir / "session-preprocess.server.log",
            role="preprocess", ready_timeout_seconds=1800.0)
        log("sidecar up: pid=%s port=%s" % (session.pid, session.port))
        try:
            transport = TRANSPORTS.resolve(str(values["transport"]))(
                values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT)
            client = FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir,
                                      binding=build_payload_binding(
                                          carrier_lock_key=SLURP_LOCK_KEY, samples=samples, data_root=root,
                                          carrier_root=asset_dir(load_lock(umbrella_lock_path()), SLURP_LOCK_KEY, root),
                                          derived_media_roots=declared_derived_media_roots(values, root)),
                                      request_id_prefix="slurpts2prep")

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
                for index, problem in enumerate(pool.map(encode, encode_targets), start=1):
                    if problem is None:
                        contacts += 1
                    else:
                        failures.append(problem)
                        log("contact FAILED %s" % problem)
                    if index % 100 == 0 or index == len(encode_targets):
                        log("encode %d/%d (%d ok, %d failed, %.1fs)"
                            % (index, len(encode_targets), contacts, len(failures), time.time() - started))
            core_receipt = client.close()
        finally:
            stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=RUNTIME_ROOT,
                                receipt_path=run_dir / "session-preprocess.stop-receipt.json",
                                force_after_timeout=True)
            log("sidecar stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
    else:
        stop = {"termination_signal": None, "forced": False, "note": "no sidecar spawned: nothing was cold"}
        log("no cold rows: sidecar never spawned")
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
        bindings=tuple({"packet_id": packet_id_for(sample.sample_id),
                        "audio_path": str(root / sample.media_relpath)} for sample in samples),
        legacy_cache_dir=legacy_cache, encoder_receipt_sha256=canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder[0]["sha256"]), mmproj_sha256=str(mmproj[0]["sha256"]),
        expected_n_embd=EXPECTED_N_EMBD, causal_attention=True, workers=args.promote_workers)
    promote_seconds = time.time() - promote_started
    if len(packets) != len(samples):
        raise SystemExit("promotion produced %d packets for %d samples" % (len(packets), len(samples)))
    audio_by_packet = {packet_id_for(sample.sample_id): sample.audio_ref.sha256 for sample in samples}
    for packet in packets:
        if packet.audio_sha256 != audio_by_packet[packet.packet_id]:
            raise SystemExit("promoted packet %s carries a different audio sha256" % packet.packet_id)
    tokens = {packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks) for packet in packets}

    gate_result = None
    if args.gate:
        gate_result = run_gate_check(packet_root, samples)
        log("GATE TOKEN-COUNT FALSIFIER: %s" % gate_result["gate"])

    receipt = {
        "schema": "saea-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "count": len(packets),
        "dataset_runtime_view_sha256": str(values["runtime_view_sha256"]),
        "feature_root": str(packet_root),
        "legacy_cache_dir": str(legacy_cache),
        "preprocess_session_id": (session.session_id if encode_targets else "no-session-all-warm"),
        "preprocess_session_receipt_sha256": (canonical_sha256(session.as_json()) if encode_targets else None),
        "preprocess_stop_receipt_sha256": canonical_sha256(stop),
        "runtime_receipt_sha256": canonical_sha256(runtime_receipt),
        "packets": [
            {"packet_id": packet.packet_id, "packet_sha256": packet.packet_sha256,
             "audio_sha256": packet.audio_sha256,
             "decoder_gguf_sha256": str(decoder[0]["sha256"]), "mmproj_sha256": str(mmproj[0]["sha256"])}
            for packet in sorted(packets, key=lambda entry: entry.packet_id)
        ],
    }
    with out_receipt.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    log("promotion receipt %s (sha256 %s)" % (out_receipt, sha256_file(out_receipt)[:16]))

    report = {
        "schema": "saea-slurp-dev1000-ts2-preprocess-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": RUN_ID, "attempt_id": attempt_id, "mode": "gate" if args.gate else "full",
        "config_fragments": {"model": MODEL_FRAGMENT, "dataset": dataset,
                             "baseline": BASELINE_FRAGMENT, "experiment": EXPERIMENT_FRAGMENT},
        "config_hash": composed.config_hash,
        "split_identity_hash": str(values["split_identity_hash"]),
        "rows": len(samples), "audio_seconds": round(sum(float(s.audio_seconds) for s in samples), 6),
        "declared_plan": {"calls": PLAN_CALLS_CEILING, "speech_audio_seconds": PLAN_SPEECH_SECONDS_CEILING,
                          "gpu_hours": PLAN_GPU_HOURS_CEILING,
                          "basis": "the row's full registered ceiling, declared by both attempts for headroom"},
        "legacy_cache_warm_before": warm_count,
        "encode_targets": len(encode_targets), "encode_skipped_already_warm": skipped,
        "contacts": contacts, "failures": failures,
        "encode_seconds": round(encode_seconds, 3),
        "encode_rows_per_second": round(len(encode_targets) / max(encode_seconds, 1e-9), 4) if encode_targets else 0.0,
        "encode_workers": args.workers,
        "promote_seconds": round(promote_seconds, 3),
        "promote_packets_per_second": round(len(packets) / max(promote_seconds, 1e-9), 4),
        "promote_workers": args.promote_workers,
        "promotion_receipt": str(out_receipt),
        "promotion_receipt_sha256": sha256_file(out_receipt),
        "packet_tokens": {"min": min(tokens.values()), "max": max(tokens.values()),
                          "total": sum(tokens.values())},
        "core_client": ({"trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
                        "cost": core_receipt.get("cost")} if core_receipt is not None else None),
        "session_stop": stop,
        "gate_check": gate_result,
        "gpu_offload": "-ngl 0 --no-mmproj-offload, CUDA_VISIBLE_DEVICES='': this pass leaves the GPU free",
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
