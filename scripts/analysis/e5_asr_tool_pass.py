#!/usr/bin/env python3
"""E5-0: one pinned Whisper large-v3 transcript pass over a SLURP TRAIN roster (an INSTRUMENT).

Owner decision 201 (option A, 2026-09-29) and the owner supplement of the same day: E5-0 and the
offline read E5-1 are INSTRUMENTS / ORACLES. They bound what a perfect ASR tool call could yield for
slot-value verification; nothing here is, or becomes, a system-default delivery step. The runtime form
(E5-2) is the frozen core OFFERED a pinned ASR tool and DECIDING itself whether to call it; no code for
it exists yet. Design: ``docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md``
(and its 2026-09-29 addendum); registration: ``docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/``.

This driver reuses the existing producer unchanged: ``core.preparation_speech_observations.
run_speech_observation_preparation`` (shared custody, generation lease, attempt store, per-row
``speech-tool`` artifacts, the ``saea-prepared-speech-observation-catalog-v1`` catalog) with the
``LocalWhisperBackend``. It adds only: a model-free source export for the roster, the registration
files, the refusal gate, a byte-identical publication of the sealed catalog under
``$DATA/prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/<roster>/`` and a hashes-and-counts receipt.

Subcommands (every one but ``run`` is model-free):

    sources  --roster R [--write]   the roster's source inventory (packet + original-audio metadata;
                                    no audio decode). Without --write it only computes the would-be
                                    file sha256 in a temporary directory.
    register --roster R --device D  write (or --check) the protocol and plan envelope of R x D under
                                    docs/readiness/2026-09-29-slurp-asr-tool-pass-v1/<R>-<D>/.
    check    --roster R [--cpu]     evaluate every refusal; exit 0 admissible, 3 refused. No contact.
    run      --roster R [--cpu]     check, export sources if absent, run the producer, publish, receipt.

Refusals (``run`` and ``check``): the roster's exposure-ledger row (Fold A:
``SAEA-SLURP-ASR-TOOL-PASS-V1``; Fold B: ``SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1``, both beside the
umbrella row ``SAEA-SLURP-ASR-TOOL-PASS-V1``) must exist once, read consumed = no and carry a root
countersignature; no generation flight may be alive (``$DATA/locks/flight.lock`` or a
``core.flight.cli campaign|worker`` / ``batch_driver.sh`` / ``core.flight.lease_cli`` process); in GPU
mode no llama-server may hold the serving port (the serving session is down), otherwise the caller
must pass ``--cpu``; the umbrella lock must carry ``whisper-large-v3-openai-pt`` with the runtime
inventory's checkpoint sha256; the checkout must be clean; the registration files must re-derive
byte-identically; no attempt of the run may already exist unless its catalog is sealed (then the call
is the idempotent warm path and makes no contact).

Text discipline: no utterance text, transcript, gold label or model output is printed or persisted by
this driver; the transcripts live only inside the producer's per-row artifacts under the data root.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
REG_DIR = "docs/readiness/2026-09-29-slurp-asr-tool-pass-v1"
PUBLISH_ROOT = "prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1"
RECEIPT_SCHEMA = "saea-slurp-asr-tool-pass-receipt-v1"
UMBRELLA_ROW = "SAEA-SLURP-ASR-TOOL-PASS-V1"
LOCK_ENTRY = "whisper-large-v3-openai-pt"
CARRIER = "slurp"
PROFILE = "bounded-discovery-probe"
SPLIT_ROLE = "discovery"
PROMOTION = {
    "path": "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/EVO-FOLDS-V2-promotion.json",
    "sha256": "4f048f47830a22d41d0bc81ccb453efd41bf8c6726a462bd1dc11eab36f30247",
}
CHECKPOINT_RECEIPT = {
    "relpath": "docs/readiness/2026-09-12-slurp-whisper-recovery-v1/runtime-inventory.json",
    "sha256": "79c79469975a8c014f6fc1b94bb3ab439f9e0cdc877c11378ec33d37170dc697",
}
CHECKPOINT_SHA256 = "e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb"

# The DEV-1000 recovery decode, byte for byte in its decode fields
# (docs/readiness/2026-09-12-slurp-whisper-recovery-v1/preparation-protocol.json, "decoding").
GPU_DECODING = {
    "batch_size": 8, "beam_size": 5, "cpu_workers": 8, "device": "cuda", "fp16": True, "language": "en",
    "logprob_threshold": -1.0, "no_speech_threshold": 0.6, "sample_len": 224,
    "schema": "saea-local-whisper-decode-v1", "task": "transcribe", "temperature": 0, "without_timestamps": True,
}
# The CPU fallback: the same decode fields on CPU fp32, batch 1, one worker x 4 inference threads (the
# 2026-09-14 Fold A CPU envelope, docs/readiness/2026-09-14-slurp-native-candidate-refresh-tools-train-fold-a-v1/
# whisper-cpu-protocol-v1.json, except sample_len kept at the DEV-1000 value 224).
CPU_DECODING = {
    "batch_size": 1, "beam_size": 5, "cpu_thread_limits": {"inference_threads": 4, "interop_threads": 1},
    "cpu_workers": 1, "device": "cpu", "fp16": False, "language": "en", "logprob_threshold": -1.0,
    "no_speech_threshold": 0.6, "sample_len": 224, "schema": "saea-local-whisper-decode-v1",
    "task": "transcribe", "temperature": 0, "without_timestamps": True,
}
DECODING = {"gpu": GPU_DECODING, "cpu": CPU_DECODING}
# Elapsed-preparation allowance per plan (the producer refuses a contact past it). The ledger rows
# register 5.0 so the CPU fallback (about 4.4 h measured) is covered; the GPU pass needs about 0.15.
PLANNED_HOURS = {"gpu": 0.5, "cpu": 5.0}

ROSTERS = {
    "fold-a": {
        "dataset": "configs/dataset/slurp-speech-native-evo-fold-a-1080.json",
        "split_identity_hash": "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6",
        "row_id": "SAEA-SLURP-ASR-TOOL-PASS-V1",
        "sources_relpath": "prepared/SAEA-SLURP-TRAIN-A-LIVE-SPEECH-SOURCES-PREPARE-V1/sources.json",
        "catalog_id": "slurp-train-fold-a-whisper-large-v3-full-utterance-v1",
        "rows": 1080,
        "planned_audio_seconds": 3085,
    },
    "fold-b": {
        "dataset": "configs/dataset/slurp-speech-native-evo-fold-b-1080.json",
        "split_identity_hash": "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a",
        "row_id": "SAEA-SLURP-ASR-TOOL-PASS-FOLD-B-V1",
        "sources_relpath": "prepared/SAEA-SLURP-TRAIN-B-ASR-TOOL-PASS-SOURCES-V1/sources.json",
        "catalog_id": "slurp-train-fold-b-whisper-large-v3-full-utterance-v1",
        "rows": 1080,
        "planned_audio_seconds": 3155,
    },
}
DEVICES = ("gpu", "cpu")

GENERATION_FLIGHT = re.compile(
    r"core\.flight\.cli (campaign|worker)( |$)|batch_driver\.sh|core\.flight\.lease_cli")
SERVING_PORT_SERVER = re.compile(r"llama-server --host 127\.0\.0\.1 --port 8080( |$)")


class ToolPassError(RuntimeError):
    """A refused or inconsistent E5-0 step."""


# ---------------------------------------------------------------------------- small helpers


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical_json(document) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def attempt_id(roster: str, device: str) -> str:
    return f"attempt-slurp-asr-tool-pass-{roster}-{device}-v1"


def reg_paths(roster: str, device: str) -> dict:
    base = f"{REG_DIR}/{roster}-{device}"
    return {"protocol": f"{base}/preparation-protocol.json", "plan": f"{base}/preparation-plan.json"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------- sources (model-free)


def source_bindings(dataset: dict, promotion: dict) -> dict:
    """sample_id -> the five-field source binding the producer's source inventory carries.

    The packet sha256 comes from the registered promotion receipt (the same one every EVO-FOLDS-V2 arm
    binds); the original-audio relpath, sha256 and duration come from the dataset fragment. The
    promotion's own audio sha256 must agree with the fragment's.
    """
    packets = {}
    for entry in promotion.get("packets") or ():
        packets[entry["packet_id"]] = entry
    out = {}
    for item in dataset["items"]:
        packet = packets.get(item["packet_id"])
        if packet is None:
            raise ToolPassError(f"promotion receipt lacks packet {item['packet_id']}")
        if packet.get("audio_sha256") != item["audio_sha256"]:
            raise ToolPassError(f"promotion and dataset disagree on the audio of {item['packet_id']}")
        out[item["sample_id"]] = {
            "packet_id": item["packet_id"],
            "packet_sha256": packet["packet_sha256"],
            "source_audio_relpath": item["media_relpath"],
            "source_audio_sha256": item["audio_sha256"],
            "source_audio_duration_seconds": float(item["audio_seconds"]),
        }
    if len(out) != len(dataset["items"]):
        raise ToolPassError("dataset fragment repeats a sample id")
    return out


def export_sources(path: Path, bindings: dict, split: str) -> dict:
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import (
        export_speech_observation_sources)

    return export_speech_observation_sources(
        path, source_bindings=bindings, carrier_lock_key=CARRIER, split_identity_hash=split)


def roster_sources(roster: str, *, data_root: Path, repo: Path | None = None, write: bool = False,
                   promotion_path: str | None = None, promotion_sha256: str | None = None) -> dict:
    repo = REPO_ROOT if repo is None else repo
    spec = ROSTERS[roster]
    dataset = json.loads((repo / spec["dataset"]).read_text(encoding="utf-8"))
    if dataset.get("split_identity_hash") != spec["split_identity_hash"] or dataset.get("count") != spec["rows"]:
        raise ToolPassError(f"{roster}: dataset fragment identity differs from the registered roster")
    ppath = Path(promotion_path or PROMOTION["path"])
    psha = promotion_sha256 or PROMOTION["sha256"]
    raw = ppath.read_bytes()
    if sha256_bytes(raw) != psha:
        raise ToolPassError("promotion receipt bytes differ from the pinned sha256")
    bindings = source_bindings(dataset, json.loads(raw))
    seconds = sum(b["source_audio_duration_seconds"] for b in bindings.values())
    with tempfile.TemporaryDirectory(prefix="e5-sources-") as scratch:
        probe = Path(scratch) / "sources.json"
        export_sources(probe, bindings, spec["split_identity_hash"])
        expected = sha256_file(probe)
    target = data_root / spec["sources_relpath"]
    written = False
    if target.exists():
        if sha256_file(target) != expected:
            raise ToolPassError(f"{roster}: the landed source inventory differs from its re-derivation")
    elif write:
        export_sources(target, bindings, spec["split_identity_hash"])
        if sha256_file(target) != expected:
            raise ToolPassError(f"{roster}: the written source inventory differs from its re-derivation")
        written = True
    return {"roster": roster, "relpath": spec["sources_relpath"], "sha256": expected, "rows": len(bindings),
            "audio_seconds": seconds, "exists": target.exists(), "written": written}


# ---------------------------------------------------------------------------- registration files


def build_registration(roster: str, device: str, sources_sha256: str) -> dict:
    """The protocol bytes and the plan envelope bytes of one roster x device (deterministic)."""
    spec = ROSTERS[roster]
    attempt = attempt_id(roster, device)
    prefix = f"prepared/{spec['row_id']}/{attempt}"
    protocol = {
        "artifacts_relpath": f"{prefix}/observations",
        "catalog_id": spec["catalog_id"] + ("" if device == "gpu" else "-cpu"),
        "checkpoint_receipt": dict(CHECKPOINT_RECEIPT),
        "decoding": dict(DECODING[device]),
        "monitor_interval_seconds": 10,
        "output_relpath": f"{prefix}/catalog.json",
        "schema": "saea-speech-observation-preparation-protocol-v1",
        "sources": {"relpath": spec["sources_relpath"], "sha256": sources_sha256},
    }
    protocol_bytes = canonical_json(protocol)
    plan = {
        "attempt_id": attempt,
        "carrier_lock_key": CARRIER,
        "execution_profile": PROFILE,
        "planned_gpu_hours": PLANNED_HOURS[device],
        "planned_model_calls": spec["rows"],
        "planned_speech_audio_seconds": spec["planned_audio_seconds"],
        "protocol_hash": sha256_bytes(protocol_bytes),
        "run_id": spec["row_id"],
        "schema": "saea-execution-plan-v1",
        "split_identity_hash": spec["split_identity_hash"],
        "split_role": SPLIT_ROLE,
        "study": "speech-aware-evidence-acquisition",
    }
    plan_bytes = canonical_json({"execution_plan": plan})
    return {"protocol": protocol, "protocol_bytes": protocol_bytes, "plan": plan, "plan_bytes": plan_bytes}


def write_registration(roster: str, device: str, sources_sha256: str, repo: Path | None = None,
                       check: bool = False) -> dict:
    repo = REPO_ROOT if repo is None else repo
    built = build_registration(roster, device, sources_sha256)
    paths = reg_paths(roster, device)
    out = {}
    for key in ("protocol", "plan"):
        path = repo / paths[key]
        raw = built[f"{key}_bytes"]
        if check:
            if not path.exists() or path.read_bytes() != raw:
                raise ToolPassError(f"{paths[key]} does not re-derive byte-identically")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        out[key] = {"relpath": paths[key], "sha256": sha256_bytes(raw)}
    return out


# ---------------------------------------------------------------------------- refusal predicates


def ledger_row_state(ledger_text: str, row_id: str) -> dict:
    """Presence, uniqueness, consumed flag and root countersignature of one exposure-ledger row."""
    from speech_aware_evidence_acquisition.contracts import _EXPOSURE_RUN_COLUMN, _parse_ledger_tables

    rows = [r for r in _parse_ledger_tables(ledger_text) if r.get(_EXPOSURE_RUN_COLUMN) == row_id]
    state = {"row_id": row_id, "present": bool(rows), "unique": len(rows) == 1, "consumed": None,
             "countersigned": False}
    if len(rows) == 1:
        notes = rows[0].get("notes", "")
        state["consumed"] = rows[0].get("consumed", "").strip().lower()
        lowered = notes.lower()
        state["countersigned"] = "root countersigned" in lowered and "countersignature pending" not in lowered
    return state


def flight_alive(data_root: Path, process_lines: list[str]) -> list[str]:
    reasons = []
    if (Path(data_root) / "locks" / "flight.lock").exists():
        reasons.append("flight.lock present")
    reasons += [f"generation flight process: {line[:160]}" for line in process_lines
                if GENERATION_FLIGHT.search(line)]
    return reasons


def serving_up(process_lines: list[str]) -> list[str]:
    return [line[:160] for line in process_lines if SERVING_PORT_SERVER.search(line)]


def list_processes() -> list[str]:
    """``pid argv`` of every process, read from /proc (no pgrep self-match)."""
    lines = []
    me = os.getpid()
    for entry in Path("/proc").iterdir() if Path("/proc").is_dir() else ():
        if not entry.name.isdigit() or int(entry.name) == me:
            continue
        try:
            argv = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
        except OSError:
            continue
        if argv:
            lines.append(f"{entry.name} {argv}")
    return lines


def lock_entry_state(lock: dict) -> list[str]:
    entries = [m for m in lock.get("models") or () if m.get("name") == LOCK_ENTRY]
    if len(entries) != 1:
        return [f"umbrella lock carries {len(entries)} '{LOCK_ENTRY}' entries (need exactly 1)"]
    files = (entries[0].get("source") or {}).get("files") or ()
    if [f.get("sha256") for f in files] != [CHECKPOINT_SHA256] or entries[0].get("status") != "COMPLETE":
        return [f"umbrella lock '{LOCK_ENTRY}' does not pin checkpoint sha256 {CHECKPOINT_SHA256} as COMPLETE"]
    return []


def git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, env=env)


def evaluate(roster: str, *, device: str, data_root: Path, lock_path: Path, repo: Path | None = None,
             processes: list[str] | None = None, require_clean: bool = True) -> dict:
    """Every refusal of ``run``; ``admissible`` is True only with an empty ``refusals`` list."""
    repo = REPO_ROOT if repo is None else repo
    spec = ROSTERS[roster]
    refusals = []
    ledger_text = (repo / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    rows = {rid: ledger_row_state(ledger_text, rid) for rid in dict.fromkeys((UMBRELLA_ROW, spec["row_id"]))}
    for rid, st in rows.items():
        if not st["present"]:
            refusals.append(f"exposure-ledger row {rid} is absent")
        elif not st["unique"]:
            refusals.append(f"exposure-ledger row {rid} is registered more than once")
        elif not st["countersigned"]:
            refusals.append(f"exposure-ledger row {rid} carries no root countersignature")
    own = rows[spec["row_id"]]
    procs = list_processes() if processes is None else processes
    refusals += flight_alive(data_root, procs)
    if device == "gpu":
        up = serving_up(procs)
        if up:
            refusals.append("the serving session is up (a llama-server holds port 8080); stop it first or pass --cpu: "
                            + "; ".join(up))
    try:
        lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
        refusals += lock_entry_state(lock)
    except (OSError, ValueError) as error:
        refusals.append(f"umbrella lock unreadable: {error}")
    if require_clean:
        try:
            if git(repo, "status", "--porcelain").strip():
                refusals.append("the checkout is not clean")
        except (OSError, subprocess.CalledProcessError) as error:
            refusals.append(f"git status failed: {error}")
    reg = reg_paths(roster, device)
    for key, rel in reg.items():
        if not (repo / rel).exists():
            refusals.append(f"registration file {rel} is absent")
    sealed = None
    if not any(r.startswith("registration file") for r in refusals):
        protocol = json.loads((repo / reg["protocol"]).read_bytes())
        plan = json.loads((repo / reg["plan"]).read_bytes())["execution_plan"]
        built = build_registration(roster, device, protocol["sources"]["sha256"])
        if (repo / reg["protocol"]).read_bytes() != built["protocol_bytes"] or \
                (repo / reg["plan"]).read_bytes() != built["plan_bytes"]:
            refusals.append("registration files do not re-derive byte-identically")
        catalog = data_root / protocol["output_relpath"]
        attempts = sorted((data_root / "attempts" / plan["run_id"]).glob("*.json")) \
            if (data_root / "attempts" / plan["run_id"]).is_dir() else []
        if catalog.exists():
            sealed = str(catalog)
        elif attempts:
            refusals.append(f"an attempt of {plan['run_id']} already exists without a sealed catalog "
                            f"({', '.join(a.stem for a in attempts)}); a recovery needs its own registration")
        other = "cpu" if device == "gpu" else "gpu"
        other_catalog = data_root / build_registration(roster, other, protocol["sources"]["sha256"])[
            "protocol"]["output_relpath"]
        if other_catalog.exists():
            refusals.append(f"the {other} pass of {roster} already sealed a catalog; one pass per roster")
    if own["present"] and own["unique"] and own["consumed"] != "no" and sealed is None:
        refusals.append(f"exposure-ledger row {spec['row_id']} is not 'consumed = no'")
    return {"roster": roster, "device": device, "rows": rows, "refusals": refusals,
            "admissible": not refusals, "sealed_catalog": sealed}


# ---------------------------------------------------------------------------- run + publish


def publish(data_root: Path, roster: str, catalog_relpath: str) -> dict:
    source = data_root / catalog_relpath
    raw = source.read_bytes()
    target = data_root / PUBLISH_ROOT / roster / "catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise ToolPassError(f"{target} already holds a different catalog")
    else:
        with target.open("xb") as handle:
            handle.write(raw)
    return {"relpath": f"{PUBLISH_ROOT}/{roster}/catalog.json", "sha256": sha256_bytes(raw),
            "producer_relpath": catalog_relpath}


def environment_identity(device: str) -> dict:
    packages = {}
    for name in ("torch", "numpy", "tiktoken", "soundfile", "triton"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    gpu = None
    smi = shutil.which("nvidia-smi")
    if device == "gpu" and smi:
        try:
            gpu = subprocess.check_output([smi, "--query-gpu=name,driver_version", "--format=csv,noheader"],
                                          text=True, timeout=30).strip()
        except (OSError, subprocess.SubprocessError):
            gpu = None
    return {"python": platform.python_version(), "executable": sys.executable, "platform": platform.platform(),
            "packages": packages, "gpu": gpu, "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}


def build_receipt(*, roster: str, device: str, protocol: dict, protocol_sha256: str, plan_pin: dict,
                  producer: dict, published: dict, sources: dict, study_head: str, ledger_sha256: str,
                  lock_sha256: str, started_at: str, wall_seconds: float, env: dict) -> dict:
    from speech_aware_evidence_acquisition.core.preparation import digest

    spec = ROSTERS[roster]
    inventory = json.loads((REPO_ROOT / CHECKPOINT_RECEIPT["relpath"]).read_text(encoding="utf-8"))
    return {
        "schema": RECEIPT_SCHEMA,
        "roster": roster,
        "run_id": spec["row_id"],
        "attempt_id": attempt_id(roster, device),
        "exposure_ledger_rows": sorted({UMBRELLA_ROW, spec["row_id"]}),
        "split_identity_hash": spec["split_identity_hash"],
        "source_inventory": {"relpath": sources["relpath"], "sha256": sources["sha256"]},
        "utterance_count": producer.get("logical_speech_tool_contacts"),
        "speech_audio_seconds": producer.get("actual_speech_audio_seconds"),
        "device_mode": device,
        "model": {"lock_entry": LOCK_ENTRY, "checkpoint_path": inventory["checkpoint"]["path"],
                  "checkpoint_bytes": inventory["checkpoint"]["bytes"],
                  "checkpoint_sha256": inventory["checkpoint"]["sha256"]},
        "runtime_inventory": dict(CHECKPOINT_RECEIPT),
        "whisper_source_path": inventory["whisper_source_path"],
        "whisper_packages": inventory["packages"],
        "decoding": protocol["decoding"],
        "decoding_config_sha256": digest(protocol["decoding"]),
        "protocol": {"relpath": reg_paths(roster, device)["protocol"], "sha256": protocol_sha256},
        "execution_plan": plan_pin,
        "producer_receipt": producer,
        "catalog": published,
        "study_head": study_head,
        "exposure_ledger_sha256_at_run": ledger_sha256,
        "umbrella_lock_sha256_at_run": lock_sha256,
        "environment": env,
        "started_at": started_at,
        "wall_seconds": round(wall_seconds, 3),
        "core_contacts": 0,
        "text_discipline": "hashes and counts only; no utterance text, transcript, gold label or model output",
    }


def run(roster: str, *, device: str, data_root: Path, lock_path: Path, session_id: str | None = None,
        runner=None, processes: list[str] | None = None) -> dict:
    verdict = evaluate(roster, device=device, data_root=data_root, lock_path=lock_path, processes=processes)
    if not verdict["admissible"]:
        raise ToolPassError("REFUSED: " + " | ".join(verdict["refusals"]))
    receipt_path = data_root / PUBLISH_ROOT / roster / "receipt.json"
    if verdict["sealed_catalog"] is not None:
        # Idempotent warm path: the pass already sealed; never contact again. The producer's own warm
        # reload would re-pin the (since grown) exposure ledger, so it is not called here.
        protocol = json.loads((REPO_ROOT / reg_paths(roster, device)["protocol"]).read_bytes())
        published = publish(data_root, roster, protocol["output_relpath"])
        if not receipt_path.exists():
            raise ToolPassError(f"the {roster} catalog is sealed but {receipt_path} is absent; coordinator to inspect")
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if prior.get("catalog") != published:
            raise ToolPassError(f"{receipt_path} records a different catalog")
        return {**prior, "cache": "warm", "new_contacts": 0}
    started, t0 = now(), time.monotonic()
    reg = reg_paths(roster, device)
    protocol_raw = (REPO_ROOT / reg["protocol"]).read_bytes()
    plan_raw = (REPO_ROOT / reg["plan"]).read_bytes()
    protocol, plan = json.loads(protocol_raw), json.loads(plan_raw)["execution_plan"]
    sources = roster_sources(roster, data_root=data_root, write=True)
    if sources["sha256"] != protocol["sources"]["sha256"]:
        raise ToolPassError("the source inventory differs from the registered protocol pin")
    head = git(REPO_ROOT, "rev-parse", "HEAD").strip()
    ledger_raw = (REPO_ROOT / "docs/exposure-ledger.md").read_bytes()
    lock_raw = Path(lock_path).read_bytes()
    config = {
        "plan": plan,
        "execution_plan": {"relpath": reg["plan"], "sha256": sha256_bytes(plan_raw)},
        "ledger_row": {"relpath": "docs/exposure-ledger.md", "sha256": sha256_bytes(ledger_raw),
                       "row_id": plan["run_id"]},
        "protocol": {"path": str(REPO_ROOT / reg["protocol"]), "sha256": sha256_bytes(protocol_raw)},
        "umbrella_lock": {"path": str(lock_path), "sha256": sha256_bytes(lock_raw)},
        "session_id": session_id or f"e5-asr-tool-pass-{roster}-{device}",
        "study_head": head,
    }
    os.environ.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
    if runner is None:
        from speech_aware_evidence_acquisition.core.preparation_speech_observations import (
            run_speech_observation_preparation as runner)
    producer = runner(config, source_root=REPO_ROOT, data_root=data_root)
    catalog_relpath = producer.get("catalog_relpath") or protocol["output_relpath"]
    published = publish(data_root, roster, catalog_relpath)
    if producer.get("catalog_sha256") not in (None, published["sha256"]):
        raise ToolPassError("the published catalog differs from the producer's sealed catalog")
    receipt = build_receipt(
        roster=roster, device=device, protocol=protocol, protocol_sha256=sha256_bytes(protocol_raw),
        plan_pin=config["execution_plan"], producer=dict(producer), published=published, sources=sources,
        study_head=head, ledger_sha256=config["ledger_row"]["sha256"], lock_sha256=config["umbrella_lock"]["sha256"],
        started_at=started, wall_seconds=time.monotonic() - t0, env=environment_identity(device))
    with receipt_path.open("xb") as handle:
        handle.write(canonical_json(receipt))
    return receipt


# ---------------------------------------------------------------------------- CLI


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("sources", "register", "check", "run"):
        p = sub.add_parser(name)
        p.add_argument("--roster", choices=sorted(ROSTERS), required=True)
        p.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
        if name == "sources":
            p.add_argument("--write", action="store_true")
        if name == "register":
            p.add_argument("--device", choices=DEVICES, required=True)
            p.add_argument("--check", action="store_true")
        if name in ("check", "run"):
            p.add_argument("--cpu", action="store_true", help="CPU fallback (allowed while serving is up)")
            p.add_argument("--lock", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    try:
        if args.command == "sources":
            print(json.dumps(roster_sources(args.roster, data_root=data_root, write=args.write), sort_keys=True))
        elif args.command == "register":
            sources = roster_sources(args.roster, data_root=data_root)
            print(json.dumps(write_registration(args.roster, args.device, sources["sha256"], check=args.check),
                             sort_keys=True))
        elif args.command == "check":
            verdict = evaluate(args.roster, device="cpu" if args.cpu else "gpu", data_root=data_root,
                               lock_path=Path(args.lock))
            print(json.dumps(verdict, sort_keys=True))
            return 0 if verdict["admissible"] else 3
        else:
            receipt = run(args.roster, device="cpu" if args.cpu else "gpu", data_root=data_root,
                          lock_path=Path(args.lock))
            print(json.dumps({k: receipt[k] for k in ("roster", "run_id", "utterance_count", "device_mode",
                                                     "wall_seconds", "catalog")}, sort_keys=True))
    except ToolPassError as error:
        print(str(error), file=sys.stderr)
        return 3 if str(error).startswith("REFUSED") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
