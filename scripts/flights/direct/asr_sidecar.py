#!/usr/bin/env python3
"""Qwen3-ASR CPU sidecar (owner rulings 339 / 342 A): lock resolution, reaper-safe argv, session receipt.

The sidecar is a llama-server of the pinned build serving ONE open Qwen3-ASR GGUF plus its mmproj on CPU
(-ngl 0) on its own port. Asset identity is read from the umbrella datasets lock at use time; nothing is
copied out of it. The argv puts ``--port`` BEFORE ``--host`` so the core serving entry's unscoped reaper
pattern ``llama-server --host`` (and the E5 port-8080 detector) never match it.

    asr_sidecar.py start|stop|status <model-id> [--port N] [--lock P] [--binary P] [--session-root D]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MODEL_IDS = {"qwen3-asr-0.6b": "qwen3-asr-0.6b-gguf", "qwen3-asr-1.7b": "qwen3-asr-1.7b-gguf"}
DEFAULT_PORT = 8190
DEFAULT_BINARY = "/home/chao/llama.cpp-featcache/build/bin/llama-server"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
RECEIPT_SCHEMA = "saea-asr-sidecar-session-v1"
REAPER_PATTERN = re.compile(r"llama-server --host")
CORE_PORT_PATTERN = re.compile(r"llama-server --host 127\.0\.0\.1 --port 8080( |$)")
CORE_PORT = 8080
THREADS = 8


class SidecarError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def resolve_assets(model_id: str, lock_path: Path, data_root: Path) -> dict:
    """Model id -> lock entry -> {model, mmproj} paths with the lock's sha256 (fail-closed)."""
    if model_id not in MODEL_IDS:
        raise SidecarError(f"unknown model id {model_id!r}; expected one of {sorted(MODEL_IDS)}")
    doc = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    entry = None
    for value in doc.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("name") == MODEL_IDS[model_id]:
                    entry = item
    if entry is None:
        raise SidecarError(f"lock entry {MODEL_IDS[model_id]} not found in {lock_path}")
    if entry.get("status") != "COMPLETE":
        raise SidecarError(f"lock entry {entry['name']} is not COMPLETE")
    base = Path(data_root) / entry["local_subdir"]
    files = {}
    for spec in entry["source"]["files"]:
        role = "mmproj" if spec["filename"].startswith("mmproj-") else "model"
        files[role] = {"path": str(base / spec["filename"]), "sha256": spec["sha256"],
                       "size_bytes": spec["size_bytes"], "filename": spec["filename"]}
    if set(files) != {"model", "mmproj"}:
        raise SidecarError(f"lock entry {entry['name']} must name exactly one model and one mmproj file")
    return {"lock_name": entry["name"], "revision": entry["revision"], "files": files}


def verify_assets(assets: dict) -> None:
    for role, f in assets["files"].items():
        p = Path(f["path"])
        if not p.is_file() or p.stat().st_size != f["size_bytes"]:
            raise SidecarError(f"{role} file missing or size differs from the lock: {p}")
        if sha256_file(p) != f["sha256"]:
            raise SidecarError(f"{role} sha256 differs from the lock: {p}")


def build_argv(binary: str, assets: dict, port: int, threads: int = THREADS) -> list:
    """CPU-only, reaper-safe argv: ``--port`` precedes ``--host``; the binary is never followed by ``--host``."""
    if port == CORE_PORT:
        raise SidecarError("port 8080 belongs to the resident core; the sidecar never uses it")
    argv = [binary, "--port", str(port), "--host", "127.0.0.1",
            "-m", assets["files"]["model"]["path"], "--mmproj", assets["files"]["mmproj"]["path"],
            "-ngl", "0", "--no-mmproj-offload", "-t", str(threads), "-c", "4096", "-np", "1", "--no-webui"]
    joined = " ".join(argv)
    if REAPER_PATTERN.search(joined) or CORE_PORT_PATTERN.search(joined):
        raise SidecarError("sidecar argv matches the core reaper pattern")
    return argv


def server_env() -> dict:
    """CPU only: the GPU is hidden from the sidecar process (the core holds it)."""
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def build_commit(binary: str) -> str:
    src = Path(binary).resolve().parents[2]
    out = subprocess.run(["git", "-C", str(src), "rev-parse", "--short=9", "HEAD"], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def session_dir(session_root: Path, model_id: str) -> Path:
    return Path(session_root) / f"asr-sidecar-{model_id}"


def make_receipt(model_id: str, assets: dict, argv: list, port: int, pid: int, binary: str, commit: str) -> dict:
    return {"schema": RECEIPT_SCHEMA, "model_id": model_id, "lock_entry": assets["lock_name"],
            "lock_revision": assets["revision"],
            "model": {"path": assets["files"]["model"]["path"], "sha256": assets["files"]["model"]["sha256"]},
            "mmproj": {"path": assets["files"]["mmproj"]["path"], "sha256": assets["files"]["mmproj"]["sha256"]},
            "binary": binary, "build_commit": commit, "device": "cpu", "port": port, "pid": pid,
            "argv": argv, "started_at": datetime.now(timezone.utc).isoformat()}


def wait_ready(port: int, pid: int, timeout: float = 300.0) -> None:
    import urllib.request
    end = time.time() + timeout
    while time.time() < end:
        try:
            os.kill(pid, 0)
        except OSError:
            raise SidecarError("sidecar exited before it became ready")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise SidecarError("sidecar not ready before the timeout")


def cmd_start(a) -> int:
    root = Path(a.session_root)
    sdir = session_dir(root, a.model_id)
    if (sdir / "session.json").exists() and not (sdir / "session-stop.json").exists():
        raise SidecarError(f"a session for {a.model_id} is already recorded; stop it first")
    assets = resolve_assets(a.model_id, Path(a.lock), Path(os.environ["SPEECHRL_DATA_DIR"]))
    verify_assets(assets)
    argv = build_argv(a.binary, assets, a.port)
    sdir.mkdir(parents=True, exist_ok=True)
    log = (sdir / "server.log").open("ab")
    proc = subprocess.Popen(argv, stdout=log, stderr=log, stdin=subprocess.DEVNULL, env=server_env())
    receipt = make_receipt(a.model_id, assets, argv, a.port, proc.pid, a.binary, build_commit(a.binary))
    (sdir / "session.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stop = {"flag": False}

    def _term(*_):
        stop["flag"] = True
        proc.terminate()

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)
    try:
        wait_ready(a.port, proc.pid)
    except SidecarError as error:
        proc.terminate()
        print(f"asr_sidecar: {error}", file=sys.stderr)
        (sdir / "session-stop.json").write_text(json.dumps({"reason": str(error)}) + "\n")
        return 1
    print(f"asr_sidecar: ready {a.model_id} port {a.port} pid {proc.pid}", flush=True)
    rc = proc.wait()
    (sdir / "session-stop.json").write_text(json.dumps(
        {"stopped_at": datetime.now(timezone.utc).isoformat(), "exit_status": rc, "requested": stop["flag"]}) + "\n")
    return 0 if stop["flag"] else 1


def _read(a):
    p = session_dir(Path(a.session_root), a.model_id) / "session.json"
    if not p.is_file():
        raise SidecarError(f"no session recorded for {a.model_id}")
    return json.loads(p.read_text(encoding="utf-8"))


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    st = Path(f"/proc/{pid}/stat")
    return st.is_file() and st.read_text().rsplit(")", 1)[1].split()[0] != "Z"


def cmd_status(a) -> int:
    r = _read(a)
    stopped = (session_dir(Path(a.session_root), a.model_id) / "session-stop.json").exists()
    alive = _alive(r["pid"])
    print(json.dumps({"model_id": a.model_id, "port": r["port"], "pid": r["pid"], "alive": alive,
                      "stopped_recorded": stopped, "started_at": r["started_at"]}))
    return 0 if alive and not stopped else 3


def cmd_stop(a) -> int:
    r = _read(a)
    if _alive(r["pid"]):
        os.kill(r["pid"], signal.SIGTERM)
        for _ in range(60):
            if not _alive(r["pid"]):
                break
            time.sleep(0.5)
    sp = session_dir(Path(a.session_root), a.model_id) / "session-stop.json"
    if not sp.exists():
        sp.write_text(json.dumps({"stopped_at": datetime.now(timezone.utc).isoformat(), "requested": True}) + "\n")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("start", "stop", "status"))
    p.add_argument("model_id")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--lock", default=os.environ.get("SAEA_ASR_LOCK", DEFAULT_LOCK))
    p.add_argument("--binary", default=os.environ.get("SAEA_ASR_BINARY", DEFAULT_BINARY))
    p.add_argument("--session-root", default=os.path.join(os.environ.get("SPEECHRL_DATA_DIR", "."), "serving"))
    a = p.parse_args(argv)
    try:
        return {"start": cmd_start, "stop": cmd_stop, "status": cmd_status}[a.command](a)
    except SidecarError as error:
        print(f"asr_sidecar: REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
