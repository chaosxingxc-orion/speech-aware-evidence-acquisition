#!/usr/bin/env python3
"""P3.2: the Thinking-core speech-packet pass of the Audio2Tool paired 400 (the receipt-bound A2T-G1 / SLURP-Thinking driver pattern, applied to the paired-400 roster).

LIVE exposure row ``SAEA-CARRIER-THINK-A2T-PACKETS-GPU-V1`` (package ``docs/readiness/2026-10-18-carrier-packets-thinking-v1``; experiment
``configs/experiment/carrier-think-a2t-packets-gpu-v1.json``). The Instruct packets of these 400 rows are decoder-ready outputs of the Instruct audio encoder and are not valid
input to the Thinking decoder (748 of 860 mmproj tensors differ), so the Thinking carrier cells need their OWN packets, in the existing Thinking packet root, under their own
promotion receipt ``A2T-PAIRED-400-THINKING-promotion.json`` (created once, never rewritten).

Two stages of ONE run id (the plan budget is run-cumulative):

``smoke``  the first four roster rows are encoded into the legacy cache ONLY (no packet, no receipt) and the rows per minute are measured: a projected full pass above the cap
           stops the window (the ``--smoke-rate`` gate);
``full``   the remaining cold rows are encoded (rows already warm in the legacy cache are NOT contacted again), the encoder server stops normally, and all 400 are promoted into the
           Thinking packet root (additive; harness item E40 for a shared packet) and the receipt is written create-only.

Modes::

    carrier_think_packets.py a2t --stage smoke --dry-run        # zero contacts: verify every input, print the plan, the pins and the ledger state
    carrier_think_packets.py a2t --stage full  --dry-run
    carrier_think_packets.py a2t --stage smoke --run            # via carrier_think_packets_gpu.sh a2t (a serving-swap window; the card must be empty)
    carrier_think_packets.py a2t --stage full  --run
    carrier_think_packets.py a2t --check-ledger                 # exit 0 only if the exposure row is countersigned
    carrier_think_packets.py a2t --smoke-rate                   # exit 0 only if the measured smoke rate projects a full pass inside the cap
    carrier_think_packets.py a2t --verify-receipt               # model-free: the written receipt hashes, covers the roster and every packet validates

``--dry-run`` opens no media file beyond the roster receipt, starts no process and contacts nothing; it never refuses over a resident serving session (the pre-window check runs
it while the card is occupied). The Earnings window stage is ``carrier_think_windows_stage.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402

REPO = fam.REPO_ROOT
SPEC = fam.packets_spec("a2t")
RUN_ID = SPEC["run_id"]
EXPERIMENT = SPEC["experiment"]
MODEL_FRAGMENT = "q4km-thinking-feature-preprocess-gpu-np1-carrier-a2t-v1"
DATASET_FRAGMENT = "audio2tool-paired-400"
BASELINE_FRAGMENT = "speech-native-preprocess"
LEGACY_CACHE = Path(SPEC["legacy_cache_dir"])
PACKET_ROOT = Path(fam.THINK_PACKET_ROOT)
PROMOTION_RECEIPT = Path(fam.A2T_PROMOTION_RECEIPT)
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-thinking-preprocess-gpu.json"
ROSTER_RECEIPT = SPEC["roster_receipt"]
ROSTER_SHA256 = SPEC["roster_receipt_sha256"]
ROWS = int(SPEC["rows"])
SMOKE_ROWS = int(SPEC["smoke_roster_rows"])
PLAN_GPU_HOURS = float(SPEC["plan_gpu_hours"])
EXPECTED_N_EMBD = 2048
#: The roster's flight split identity (data.splits.split_identity_hash over audio2tool/<tier>:<id6>), the value the paired cells and the exposure row carry.
SPLIT_IDENTITY_HASH = "965f145f581753874353216a25109a4746627095027cefbab0ed91c88090990a"
SIDECAR_PORT = 8081
INFERENCE_PORT = 8080
INSTRUCTION = "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}
REQUEST_PREFIX = "carrierthinka2tprep"
STAGES = ("smoke", "full")
#: The smoke-rate gate: the projected seconds of the full pass at the measured rows per minute must stay below this cap (the registered ceiling is 0.5 GPU-h = 1,800 s;
#: the encode share of it is the cap; the rest is server load and promotion).
FULL_PASS_ENCODE_CAP_SECONDS = 1200.0
SCHEMA = "saea-a2t-speech-packet-promotion-receipt-v1"
ENCODER_RECEIPT_SCHEMA = "saea-carrier-think-a2t-encoder-receipt-v1"
DRAFT_TOKEN = re.compile(r"\bDRAFT\b")
COUNTERSIGNED_TOKEN = re.compile(r"REGISTERED BEFORE CONTACT")


def log(message: str) -> None:
    print("%s %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def data_root() -> Path:
    value = os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        raise SystemExit("no data root: set SAEA_DATA_ROOT or SPEECHRL_DATA_DIR")
    return Path(value)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


# ---- roster and samples -----------------------------------------------------------------------------------------------------------
def load_roster(repo: Path = REPO) -> dict:
    path = Path(repo) / ROSTER_RECEIPT
    measured = sha256_file(path)
    if measured != ROSTER_SHA256:
        raise SystemExit("roster receipt hashes to %s, not the registered %s" % (measured, ROSTER_SHA256))
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt["count"] != ROWS or len(receipt["items"]) != ROWS:
        raise SystemExit("roster receipt count drifted")
    return receipt


def packet_id(item: Mapping[str, Any]) -> str:
    value = str(item["sample_id"]).replace(":", "/")
    if value.startswith("/") or "\\" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise SystemExit("unsafe packet id %r" % value)
    return value


def stage_items(roster: Mapping[str, Any], stage: str) -> list[dict]:
    items = list(roster["items"])
    return items[:SMOKE_ROWS] if stage == "smoke" else items


def verify_media(items: Sequence[Mapping[str, Any]], root: Path, workers: int = 8) -> None:
    """Re-hash every roster file against its receipt (label-free: bytes only)."""

    from concurrent.futures import ThreadPoolExecutor

    def one(item: Mapping[str, Any]) -> None:
        rel = str(item["media_relpath"])
        if rel.startswith("/") or "\\" in rel:
            raise SystemExit("receipt media path must be relative POSIX: %s" % rel)
        path = (root / rel).resolve()
        path.relative_to(root.resolve())
        if not path.is_file():
            raise SystemExit("receipt media file is missing: %s" % rel)
        if sha256_file(path) != item["audio_sha256"]:
            raise SystemExit("audio bytes drift for %s" % item["sample_id"])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, items))


def legacy_cache_state(items: Sequence[Mapping[str, Any]], root: Path) -> tuple[set[str], list[str]]:
    """(sample ids already warm in the legacy cache, foreign cache files that are not roster rows)."""

    from speech_aware_evidence_acquisition.core.model.speech_features import legacy_audio_feature_cache_key

    expected = {}
    for item in items:
        key = legacy_audio_feature_cache_key((root / str(item["media_relpath"])).read_bytes())
        expected[key] = str(item["sample_id"])
    warm, foreign = set(), []
    if LEGACY_CACHE.is_dir():
        for path in sorted(LEGACY_CACHE.glob("*.feat")):
            key = path.name.split("_o", 1)[0]
            if key in expected:
                warm.add(expected[key])
            else:
                foreign.append(path.name)
    return warm, foreign


# ---- identity, pins, ledger -------------------------------------------------------------------------------------------------------
def compose_values(repo: Path = REPO):
    from speech_aware_evidence_acquisition.core.config import compose

    return compose(Path(repo), MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT)


def verify_identity(composed, repo: Path = REPO) -> None:
    values = composed.values
    if values["experiment_id"] != RUN_ID:
        raise SystemExit("experiment fragment names run id %r, not %s" % (values["experiment_id"], RUN_ID))
    if values.get("a2t_calibration_subset_receipt_sha256") != ROSTER_SHA256:
        raise SystemExit("the dataset fragment pins a different roster receipt")
    if values["speech_feature_root"] != str(PACKET_ROOT) or values["server_env"].get("LLAMA_MTMD_FEAT_CACHE_DIR") != str(LEGACY_CACHE):
        raise SystemExit("the encoder fragment names a different packet root or legacy cache")
    if values["runtime_receipt"] != RUNTIME_RECEIPT_RELPATH:
        raise SystemExit("the encoder fragment names runtime receipt %r" % values["runtime_receipt"])
    receipt = json.loads((Path(repo) / "docs" / RUNTIME_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    if receipt.get("role") != "preprocess" or receipt.get("model_lock_key") != values["model_lock_key"]:
        raise SystemExit("the runtime receipt is not the Thinking preprocess receipt")


def ledger_state(ledger_path: Path, *, expected_calls: int, expected_seconds: int) -> dict:
    from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables

    rows = [r for r in _parse_ledger_tables(Path(ledger_path).read_text(encoding="utf-8")) if r.get("run/experiment id") == RUN_ID]
    problems: list[str] = []
    state: dict[str, Any] = {"row": RUN_ID, "present": len(rows) == 1, "countersigned": False, "problems": problems}
    if len(rows) != 1:
        problems.append("%d exposure rows for %s, need exactly one" % (len(rows), RUN_ID))
        return state
    row = rows[0]
    try:
        numbers = (int(row["calls"]), int(row["speech audio seconds"]), float(row["gpu hours"]))
    except (KeyError, ValueError):
        numbers = None
    if numbers != (expected_calls, expected_seconds, PLAN_GPU_HOURS):
        problems.append("budgets (calls, speech audio seconds, gpu hours) %r, registered %r" % (numbers, (expected_calls, expected_seconds, PLAN_GPU_HOURS)))
    if str(row.get("consumed", "")).strip().lower() != "no":
        problems.append("row is consumed; a sealed preparation is never re-run")
    text = " ".join(str(v) for v in row.values())
    state["draft"] = bool(DRAFT_TOKEN.search(text))
    state["countersigned"] = (not state["draft"]) and bool(COUNTERSIGNED_TOKEN.search(text)) and not problems
    return state


def verify_pins(lock_path: Path, repo: Path = REPO) -> tuple[dict, dict]:
    sys.path.insert(0, str(HERE.parent / "direct"))
    import direct_fb_pins as pins_mod  # noqa: PLC0415

    pins = pins_mod.resolve_pins(lock_path=Path(lock_path), main_receipt=pins_mod.LOCAL_MAIN_RECEIPT, mmproj_receipt=pins_mod.LOCAL_MMPROJ_RECEIPT)
    receipt = json.loads((Path(repo) / "docs" / RUNTIME_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    if receipt.get("gguf_files") != [pins["main"], pins["mmproj"]]:
        raise SystemExit("runtime receipt gguf_files differ from the lock-verified Thinking pins; refusing to prepare packets under a receipt that does not bind the pinned files")
    return pins, receipt


def port_listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def resident_sessions(root: Path) -> list[str]:
    serving = Path(root) / "serving"
    out = []
    if serving.is_dir():
        for d in sorted(serving.iterdir()):
            if (d / "session.json").is_file() and not (d / "session-stop.json").is_file():
                out.append(d.name)
    return out


# ---- plan --------------------------------------------------------------------------------------------------------------------------
def build_plan(stage: str, repo: Path = REPO) -> dict:
    roster = load_roster(repo)
    items = stage_items(roster, stage)
    audio = sum(float(i["audio_seconds"]) for i in items)
    root = data_root()
    plan: dict[str, Any] = {"run_id": RUN_ID, "stage": stage, "rows": len(items), "audio_seconds": round(audio, 6), "roster_receipt": ROSTER_RECEIPT, "roster_sha256": ROSTER_SHA256,
                            "packet_root": str(PACKET_ROOT), "legacy_cache_dir": str(LEGACY_CACHE), "promotion_receipt": str(PROMOTION_RECEIPT),
                            "promotes": stage == "full", "model_fragment": MODEL_FRAGMENT}
    plan["packet_root_exists"] = PACKET_ROOT.is_dir()
    plan["promotion_receipt_exists"] = PROMOTION_RECEIPT.exists()
    plan["resident_sessions"] = resident_sessions(root)
    plan["sidecar_port_listening"] = port_listening(SIDECAR_PORT)
    plan["inference_port_listening"] = port_listening(INFERENCE_PORT)
    return plan


def dry_run(args, repo: Path = REPO) -> int:
    composed = compose_values(repo)
    verify_identity(composed, repo)
    plan = build_plan(args.stage, repo)
    roster = load_roster(repo)
    root = data_root()
    verify_media(stage_items(roster, args.stage), root, args.workers)
    warm, foreign = legacy_cache_state(stage_items(roster, args.stage), root) if LEGACY_CACHE.is_dir() else (set(), [])
    ledger = ledger_state(repo / "docs" / "exposure-ledger.md", expected_calls=ROWS, expected_seconds=int(-(-sum(float(i["audio_seconds"]) for i in roster["items"]) // 1)))
    problems = list(ledger["problems"])
    if foreign:
        problems.append("the legacy cache %s holds %d entries that are not roster rows (e.g. %s)" % (LEGACY_CACHE, len(foreign), foreign[0]))
    if plan["promotion_receipt_exists"] and args.stage == "full":
        problems.append("the promotion receipt already exists; a sealed promotion is never re-run")
    report = {"plan": plan, "config_hash": composed.config_hash, "ledger": ledger, "warm_rows": len(warm), "cold_rows": len(stage_items(roster, args.stage)) - len(warm),
              "problems": problems, "contacts": 0}
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


def check_ledger(args, repo: Path = REPO) -> int:
    roster = load_roster(repo)
    state = ledger_state(repo / "docs" / "exposure-ledger.md", expected_calls=ROWS, expected_seconds=int(-(-sum(float(i["audio_seconds"]) for i in roster["items"]) // 1)))
    print(json.dumps(state, sort_keys=True))
    return 0 if state["countersigned"] else 1


def smoke_rate(args) -> int:
    path = data_root() / "runs" / RUN_ID / "attempt-carrier-think-a2t-packets-smoke-v1" / "encoder-receipt.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    per_minute = float(document["rows_per_minute"])
    projected = ROWS * 60.0 / per_minute
    log("smoke rate %.2f rows per minute; projected full encode %.0f s against the %.0f s cap" % (per_minute, projected, FULL_PASS_ENCODE_CAP_SECONDS))
    return 0 if projected <= FULL_PASS_ENCODE_CAP_SECONDS else 1


# ---- run ---------------------------------------------------------------------------------------------------------------------------
def write_create_only(path: Path, document: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return sha256_file(path)


def run(args, repo: Path = REPO) -> int:
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import TRANSPORTS
    from speech_aware_evidence_acquisition.core.config import d1_media_supplement_relpath, d1_media_supplement_sha256
    from speech_aware_evidence_acquisition.core.model.speech_features import PACKET_MANIFEST_NAME, materialize_legacy_cached_speech_feature_packets
    from speech_aware_evidence_acquisition.core.session import start_session, stop_session
    from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY
    from speech_aware_evidence_acquisition.data.lock import asset_dir, load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolSample
    from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient, build_payload_binding
    from speech_aware_evidence_acquisition.rails.obs import AudioRef

    stage = args.stage
    composed = compose_values(repo)
    verify_identity(composed, repo)
    values = composed.values
    root = data_root()
    lock_path = Path(args.lock_path) if args.lock_path else umbrella_lock_path()
    pins, runtime_receipt = verify_pins(lock_path, repo)
    roster = load_roster(repo)
    all_items = list(roster["items"])
    items = stage_items(roster, stage)
    audio_total = sum(float(i["audio_seconds"]) for i in all_items)
    ledger = ledger_state(repo / "docs" / "exposure-ledger.md", expected_calls=ROWS, expected_seconds=int(-(-audio_total // 1)))
    problems = list(ledger["problems"])
    if not ledger["countersigned"] and not ledger["problems"]:
        problems.append("exposure row %s is not root-countersigned" % RUN_ID)
    resident = resident_sessions(root)
    if resident:
        problems.append("a serving session is still resident (%s): the card holds one core, run inside the serving-swap window" % ", ".join(resident))
    if port_listening(SIDECAR_PORT) or port_listening(INFERENCE_PORT):
        problems.append("something listens on the sidecar or the inference port")
    if stage == "full":
        if PROMOTION_RECEIPT.exists():
            problems.append("the promotion receipt already exists")
        smoke_receipt = root / "runs" / RUN_ID / "attempt-carrier-think-a2t-packets-smoke-v1" / "encoder-receipt.json"
        if not smoke_receipt.is_file():
            problems.append("the smoke stage has not run (no %s)" % smoke_receipt)
    if problems:
        raise SystemExit("REFUSED: " + "; ".join(problems))
    verify_media(items, root, args.workers)
    warm, foreign = legacy_cache_state(all_items, root) if LEGACY_CACHE.is_dir() else (set(), [])
    if foreign:
        raise SystemExit("REFUSED: the legacy cache holds %d entries that are not roster rows (e.g. %s)" % (len(foreign), foreign[0]))
    cold = [i for i in items if str(i["sample_id"]) not in warm]
    log("stage %s: %d rows, %d cold (only cold rows are contacted), config %s" % (stage, len(items), len(cold), composed.config_hash[:16]))

    lockdoc = load_lock(lock_path)
    samples = []
    for i in items:
        samples.append(Audio2ToolSample(sample_id=str(i["sample_id"]), audio_ref=AudioRef(path=str(i["media_relpath"]), sha256=str(i["audio_sha256"])).validate(),
                                        audio_seconds=float(i["audio_seconds"]), media_relpath=str(i["media_relpath"])))
    binding = build_payload_binding(carrier_lock_key=AUDIO2TOOL_LOCK_KEY, samples=samples, data_root=root, carrier_root=asset_dir(lockdoc, AUDIO2TOOL_LOCK_KEY, root))
    media_facts = {sid: (binding.media_relpaths[sid], binding.sample_facts[sid][0]) for sid in sorted(binding.allowed_sample_ids)}
    attempt_id = "attempt-carrier-think-a2t-packets-%s-v1" % stage
    run_dir = root / "runs" / RUN_ID / attempt_id
    gate = FrozenCoreGate.for_study_repo(repo, root, Path("/home/chao"), runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH, expected_model_lock_key=str(values["model_lock_key"]),
                                         d1_media_supplement_relpath=d1_media_supplement_relpath(values), d1_media_supplement_sha256=d1_media_supplement_sha256(values))
    gate.verify_media_identity(AUDIO2TOOL_LOCK_KEY, media_facts)
    log("D1 media identity PASS for %d samples" % len(media_facts))
    cold_audio = sum(float(i["audio_seconds"]) for i in cold)
    plan = ExecutionPlan(run_id=RUN_ID, execution_profile=str(values["execution_profile"]), carrier_lock_key=AUDIO2TOOL_LOCK_KEY, split_role="discovery",
                         split_identity_hash=SPLIT_IDENTITY_HASH,
                         planned_model_calls=len(cold), planned_gpu_hours=PLAN_GPU_HOURS, planned_speech_audio_seconds=int(-(-cold_audio // 1)) or 1, protocol_hash=composed.config_hash,
                         attempt_id=attempt_id).validate()
    log("frozen-core gate PASS (lock %s)" % gate.assert_model_touch_allowed(plan)[:12])
    run_dir.mkdir(parents=True, exist_ok=False)
    LEGACY_CACHE.mkdir(parents=True, exist_ok=True)            # the patched server writes cache entries only into a directory that already exists
    PACKET_ROOT.parent.mkdir(parents=True, exist_ok=True)
    contacts, failures, started = 0, [], time.time()
    session_json: dict[str, Any] = {"session_id": None}
    if cold:
        log("spawning the GPU Thinking encoder server on %d at -np 1" % SIDECAR_PORT)
        session = start_session(runtime_root=Path("/home/chao"), data_root=root, runtime_receipt=runtime_receipt, host="127.0.0.1", port=SIDECAR_PORT,
                                session_id="%s-%s" % (RUN_ID, attempt_id), extra_argv=list(values["server_args"]), extra_env=dict(values["server_env"]),
                                receipt_path=run_dir / "session-preprocess.receipt.json", server_log_path=run_dir / "session-preprocess.server.log", role="preprocess",
                                ready_timeout_seconds=1800.0)
        started = time.time()
        try:
            transport = TRANSPORTS.resolve(str(values["transport"]))(values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao"))
            client = FrozenCoreClient(plan=plan, gate=gate, transport=transport, run_dir=run_dir, binding=binding, request_id_prefix=REQUEST_PREFIX)
            by_id = {s.sample_id: s for s in samples}
            for index, item in enumerate(cold, start=1):
                sample = by_id[str(item["sample_id"])]
                messages = ({"role": "system", "content": INSTRUCTION},
                            {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]})
                try:
                    client.complete(messages, decoding_params=DECODING_PARAMS)
                    contacts += 1
                except Exception as error:  # noqa: BLE001 -- reported, never masked
                    failures.append("%s: %r" % (sample.sample_id, error))
                    log("contact FAILED %s" % failures[-1])
                if index % 25 == 0 or index == len(cold):
                    log("encode %d/%d (%d ok, %d failed, %.1fs)" % (index, len(cold), contacts, len(failures), time.time() - started))
            client.close()
        finally:
            stop = stop_session(session, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao"), receipt_path=run_dir / "session-preprocess.stop-receipt.json",
                                force_after_timeout=True)
            log("encoder server stopped: %s forced=%s" % (stop.get("termination_signal"), stop.get("forced")))
        session_json = {"session_id": session.session_id, "stop": stop, "session_receipt_sha256": canonical_sha256(session.as_json()), "stop_receipt_sha256": canonical_sha256(stop)}
        if failures:
            raise SystemExit("%d encode contacts failed; refusing to promote a partial cache: %r" % (len(failures), failures[:5]))
    encode_seconds = max(time.time() - started, 1e-9)
    warm_after, _ = legacy_cache_state(items, root)
    missing = [str(i["sample_id"]) for i in items if str(i["sample_id"]) not in warm_after]
    if missing:
        raise SystemExit("the legacy cache holds no entry for %d of %d rows (e.g. %s): the contacts are counted and the features are lost; this attempt is FAILED" % (len(missing), len(items), missing[0]))
    decoder = [g for g in runtime_receipt["gguf_files"] if "mmproj" not in Path(str(g["path"])).name.lower()][0]
    mmproj = [g for g in runtime_receipt["gguf_files"] if "mmproj" in Path(str(g["path"])).name.lower()][0]
    receipt_common = {"schema": ENCODER_RECEIPT_SCHEMA, "run_id": RUN_ID, "attempt_id": attempt_id, "stage": stage, "rows": len(items), "cold_rows": len(cold), "contacts": contacts,
                      "encode_seconds": round(encode_seconds, 3), "rows_per_minute": (60.0 * contacts / encode_seconds) if contacts else None,
                      "config_hash": composed.config_hash, "runtime_receipt_sha256": canonical_sha256(runtime_receipt), "decoder_gguf_sha256": decoder["sha256"], "mmproj_sha256": mmproj["sha256"],
                      "legacy_cache_dir": str(LEGACY_CACHE), "session": session_json, "boundary": "label-free: gold and task text never opened; the one-token completions are never read"}
    if stage == "smoke":
        write_create_only(run_dir / "encoder-receipt.json", dict(receipt_common, mode="encode-only"))
        log("SMOKE PASS: %d contacts, %s rows per minute, no packet written" % (contacts, ("%.2f" % receipt_common["rows_per_minute"]) if contacts else "n/a"))
        return 0
    bindings = tuple({"packet_id": packet_id(i), "audio_path": str(root / str(i["media_relpath"]))} for i in all_items)
    shared: list = []
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=PACKET_ROOT, bindings=bindings, legacy_cache_dir=LEGACY_CACHE, encoder_receipt_sha256=canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder["sha256"]), mmproj_sha256=str(mmproj["sha256"]), expected_n_embd=EXPECTED_N_EMBD, causal_attention=True, workers=args.promote_workers,
        on_shared=shared.append)
    if len(packets) != ROWS:
        raise SystemExit("promotion produced %d packets for %d rows" % (len(packets), ROWS))
    audio_by_packet = {packet_id(i): i["audio_sha256"] for i in all_items}
    for packet in packets:
        if packet.audio_sha256 != audio_by_packet[packet.packet_id]:
            raise SystemExit("promoted packet %s carries a different audio sha256" % packet.packet_id)
    n_tokens = {p.packet_id: sum(c.n_tokens for c in p.chunks) for p in packets}
    receipt = {
        "schema": SCHEMA, "study": "speech-aware-evidence-acquisition", "carrier": AUDIO2TOOL_LOCK_KEY, "run_id": RUN_ID, "attempt_id": attempt_id,
        "subset_receipt": ROSTER_RECEIPT, "subset_receipt_sha256": ROSTER_SHA256, "config_hash": composed.config_hash,
        "preprocess_session_id": session_json.get("session_id"), "preprocess_session_receipt_sha256": session_json.get("session_receipt_sha256"),
        "preprocess_stop_receipt_sha256": session_json.get("stop_receipt_sha256"), "runtime_receipt": RUNTIME_RECEIPT_RELPATH, "runtime_receipt_sha256": canonical_sha256(runtime_receipt),
        "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"], "legacy_cache_dir": str(LEGACY_CACHE), "feature_root": str(PACKET_ROOT),
        "encode_contacts": contacts, "count": len(packets), "shared_packet_count": len(shared), "shared_packets": [r.as_json() for r in sorted(shared, key=lambda e: e.packet_id)],
        "packets": [{"packet_id": p.packet_id, "packet_sha256": p.packet_sha256, "audio_sha256": p.audio_sha256, "decoder_gguf_sha256": p.decoder_gguf_sha256,
                     "mmproj_sha256": p.mmproj_sha256, "n_tokens": n_tokens[p.packet_id]} for p in packets],
        "speech_feature_tokens": {"max": max(n_tokens.values()), "min": min(n_tokens.values()), "total": sum(n_tokens.values())},
        "packet_id_convention": "sample_id with ':' replaced by '/'",
    }
    promotion_sha = write_create_only(PROMOTION_RECEIPT, receipt)
    log("promotion receipt %s (sha256 %s, %d packets, %d shared)" % (PROMOTION_RECEIPT, promotion_sha[:16], len(packets), len(shared)))
    write_create_only(run_dir / "encoder-receipt.json", dict(receipt_common, mode="encode-and-promote", promotion_receipt=str(PROMOTION_RECEIPT), promotion_receipt_sha256=promotion_sha))
    log("A2T PASS: %d packets promoted; next: python -B scripts/flights/carriers/carrier_think_derive_cells.py --require-receipts (pins the receipt)" % len(packets))
    return 0


def verify_receipt(args, repo: Path = REPO) -> int:
    """Model-free: the written receipt hashes, covers exactly the roster, and every packet validates under the Thinking decoder."""

    from speech_aware_evidence_acquisition.core.model.speech_features import load_speech_feature_packet_ids

    if not PROMOTION_RECEIPT.is_file():
        raise SystemExit("no promotion receipt at %s" % PROMOTION_RECEIPT)
    sha = sha256_file(PROMOTION_RECEIPT)
    document = json.loads(PROMOTION_RECEIPT.read_text(encoding="utf-8"))
    roster = load_roster(repo)
    ids = [packet_id(i) for i in roster["items"]]
    got = {p["packet_id"]: p for p in document["packets"]}
    if set(got) != set(ids) or document["count"] != ROWS:
        raise SystemExit("the receipt does not cover exactly the roster")
    _pins, receipt = verify_pins(Path(args.lock_path), repo) if args.lock_path else (None, json.loads((repo / "docs" / RUNTIME_RECEIPT_RELPATH).read_text(encoding="utf-8")))
    decoder = [g for g in receipt["gguf_files"] if "mmproj" not in Path(str(g["path"])).name.lower()][0]["sha256"]
    packets = load_speech_feature_packet_ids(PACKET_ROOT, ids, workers=8, expected_decoder_gguf_sha256=decoder)
    for p in packets:
        if got[p.packet_id]["packet_sha256"] != p.packet_sha256:
            raise SystemExit("packet %s disagrees with the receipt" % p.packet_id)
    print(json.dumps({"receipt": str(PROMOTION_RECEIPT), "sha256": sha, "packets": len(packets), "verified": True}, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = p.add_subparsers(dest="carrier", required=True)
    a = sub.add_parser("a2t")
    a.add_argument("--stage", choices=STAGES, default="full")
    mode = a.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check-ledger", action="store_true")
    mode.add_argument("--smoke-rate", action="store_true")
    mode.add_argument("--verify-receipt", action="store_true")
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--promote-workers", type=int, default=8)
    a.add_argument("--lock-path", default=None)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check_ledger:
        return check_ledger(args)
    if args.smoke_rate:
        return smoke_rate(args)
    if args.verify_receipt:
        return verify_receipt(args)
    if args.dry_run:
        return dry_run(args)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
