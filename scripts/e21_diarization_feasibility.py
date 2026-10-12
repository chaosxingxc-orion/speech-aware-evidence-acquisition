#!/usr/bin/env python3
"""Which diarization ROUTE actually exists on this machine, recorded offline.

An environment inventory, not an exposure event: it hashes files, lists what is
installed, and invokes the pinned runtime binary only for ``--version`` and
``doctor --json``, neither of which loads a model or reads one byte of corpus
audio. The corpus pass itself is separately pre-registered as
`SAEA-E21-TOOL-DIARIZATION-V1` and has NOT been run.

Two routes were prepared when the tool was acquired (umbrella lock entry
``diar-sortformer-4spk-v2``, 2026-08-18), and this script reports which of them is
live rather than assuming either:

* **Route A -- NeMo reference path.** The fp32 ``.nemo`` checkpoint under an
  ISOLATED venv (``~/.venvs/diar``). The shared ``~/.venvs/speechrl`` is checked
  too, and must NOT have ``nemo`` -- installing it there is forbidden.
* **Route B -- NeMo-Speech.cpp deployment path.** The first-party ``q8_0`` GGUF
  through the CUDA build of ``nemo-speech``, whose binary SHA-256 the lock pins.

Every tool fact is read from the umbrella lock through ``data.lock`` at run time --
no hash, revision or path is copied into this file.

``--json-out`` writes the receipt. Exit code is 1 when NEITHER route is live.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    lock_entry,
    load_lock,
    umbrella_lock_path,
)

TOOL_LOCK_KEY = "diar-sortformer-4spk-v2"
SHARED_VENV = Path("/home/chao/.venvs/speechrl")
DIAR_VENV = Path("/home/chao/.venvs/diar")

DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _module_present(python: Path, module: str) -> bool | None:
    """Is ``module`` importable by ``python``? ``None`` when that interpreter is
    absent. Never installs anything."""

    if not python.is_file():
        return None
    probe = subprocess.run(
        [
            str(python),
            "-c",
            f"import importlib.util,sys; sys.exit(0 if importlib.util.find_spec({module!r}) else 3)",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return probe.returncode == 0


def _run(binary: Path, argv: list[str]) -> dict[str, object]:
    completed = subprocess.run(
        [str(binary), *argv],
        capture_output=True,
        text=True,
        cwd=str(binary.parent),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
    )
    return {
        "argv": argv,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr_tail": completed.stderr.strip().splitlines()[-3:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    entry = lock_entry(lock, TOOL_LOCK_KEY)
    source = entry.get("source", {})
    deployment = entry.get("deployment_runtime", {})
    model_dir = args.data_root / str(entry["local_subdir"])

    payloads = []
    for declared in source.get("files", []):
        path = model_dir / str(declared["filename"])
        present = path.is_file()
        payloads.append(
            {
                "filename": declared["filename"],
                "present": present,
                "declared_bytes": declared.get("size_bytes"),
                "actual_bytes": path.stat().st_size if present else None,
                "declared_sha256": declared.get("sha256"),
                "actual_sha256": sha256_file(path) if present else None,
            }
        )
    for payload in payloads:
        payload["byte_identity_holds"] = bool(
            payload["present"]
            and payload["actual_bytes"] == payload["declared_bytes"]
            and payload["actual_sha256"] == payload["declared_sha256"]
        )

    nemo_payload = next(
        (row for row in payloads if str(row["filename"]).endswith(".nemo")), None
    )
    gguf_payload = next(
        (row for row in payloads if str(row["filename"]).endswith(".gguf")), None
    )

    route_a = {
        "name": "NeMo reference path (.nemo)",
        "checkpoint_present": bool(nemo_payload and nemo_payload["byte_identity_holds"]),
        "shared_venv": str(SHARED_VENV),
        "nemo_in_shared_venv": _module_present(SHARED_VENV / "bin" / "python", "nemo"),
        "isolated_venv": str(DIAR_VENV),
        "isolated_venv_present": (DIAR_VENV / "bin" / "python").is_file(),
        "nemo_in_isolated_venv": _module_present(DIAR_VENV / "bin" / "python", "nemo"),
        "torch_in_isolated_venv": _module_present(DIAR_VENV / "bin" / "python", "torch"),
        "install_policy": (
            "nemo_toolkit must NEVER be installed into the shared speechrl venv; the "
            "isolated ~/.venvs/diar is the only sanctioned home for it and this script "
            "installs nothing"
        ),
    }
    route_a["live"] = bool(
        route_a["checkpoint_present"]
        and route_a["nemo_in_isolated_venv"]
        and route_a["torch_in_isolated_venv"]
    )

    binary_path = Path(str(deployment.get("checkout", ""))) / str(
        deployment.get("binary", "")
    )
    binary_present = binary_path.is_file()
    route_b = {
        "name": "NeMo-Speech.cpp deployment path (q8_0 GGUF)",
        "gguf_present": bool(gguf_payload and gguf_payload["byte_identity_holds"]),
        "runtime": deployment.get("runtime"),
        "checkout": deployment.get("checkout"),
        "pinned_commit": deployment.get("commit"),
        "binary_path": str(binary_path),
        "binary_present": binary_present,
        "declared_binary_sha256": deployment.get("binary_sha256"),
        "actual_binary_sha256": sha256_file(binary_path) if binary_present else None,
    }
    route_b["binary_identity_holds"] = (
        route_b["actual_binary_sha256"] == route_b["declared_binary_sha256"]
    )
    if binary_present:
        route_b["version"] = _run(binary_path, ["--version"])
        route_b["doctor"] = _run(binary_path, ["doctor", "--json"])
        route_b["diarize_usage"] = _run(binary_path, ["help", "diarize"])
    route_b["live"] = bool(
        route_b["gguf_present"] and binary_present and route_b["binary_identity_holds"]
    )

    report = {
        "schema": "saea-e21-diarization-feasibility-v1",
        "study": "speech-aware-evidence-acquisition",
        "tool_lock_key": TOOL_LOCK_KEY,
        "tool_revision": entry.get("revision"),
        "tool_license": entry.get("license"),
        "research_role": entry.get("research_role"),
        "claim_limit": entry.get("claim_limit"),
        "payloads": payloads,
        "route_a_nemo": route_a,
        "route_b_nemo_speech_cpp": route_b,
        "selected_route": (
            "route_b_nemo_speech_cpp"
            if route_b["live"]
            else ("route_a_nemo" if route_a["live"] else None)
        ),
        "ffmpeg_on_path": shutil.which("ffmpeg"),
        "zero_contact": (
            "environment inventory only: file hashes, interpreter module probes, and the "
            "pinned binary's --version / doctor / help subcommands, all with "
            "CUDA_VISIBLE_DEVICES empty. No model was loaded, no corpus audio was read, "
            "no frozen-core contact was made, and nothing was installed. The corpus "
            "diarization pass is pre-registered as SAEA-E21-TOOL-DIARIZATION-V1 and has "
            "not been run."
        ),
    }

    payload = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload)
    return 0 if report["selected_route"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
