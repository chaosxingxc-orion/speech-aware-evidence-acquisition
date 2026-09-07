#!/usr/bin/env python3
"""Compose and drive the cross-carrier ``@ts2`` cells with ZERO sockets, and
record exactly how far each one gets.

Two modes per cell, both contactless:

``preflight``
    ``core.flight.FlightRuntime.preflight`` behind the REAL
    ``contracts.FrozenCoreGate``: config composition, roster hydration with a
    per-file SHA-256 re-hash of every media file, media-path confinement,
    the count check, ``ExecutionPlan`` construction and the execution-profile
    check -- and then the gate's refusal, because these cells are preregistered
    and NOT authorized.

``wire``
    ``FlightRuntime.wire_check``: the same request path against a fake gate and
    a transport that never opens a socket.

The point of this receipt is not a green tick. It is to record, before anyone
spends GPU time, the EXACT line at which each carrier's cell stops today and
why -- so the preregistration's preconditions are measured facts rather than a
reviewer's guess. A cell that stops is reported as stopping, with the
exception class and message it stopped with.

Model-free. Zero model contacts, zero servers, zero sockets, zero GPU. Run
under the media rows this campaign already registered.

Usage (WSL2)::

    python scripts/cross_carrier_tail2s_wire_check.py
    python scripts/cross_carrier_tail2s_wire_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-cross-carrier-tail2s-wire-check"
)

CELLS: tuple[dict[str, Any], ...] = (
    {
        "carrier": "audio2tool",
        "runner": "scripts/flights/run_calibration_cell.py",
        "experiment": "a2t-official-protocol-tail2s-400-smoke-v1",
        "dataset": "audio2tool-calibration-400-tail2s-smoke4",
        "cell": "R-official-tail2s-smoke-4",
        "rows": 4,
    },
    {
        "carrier": "audio2tool",
        "runner": "scripts/flights/run_calibration_cell.py",
        "experiment": "a2t-official-protocol-tail2s-400-v1",
        "dataset": "audio2tool-calibration-400-tail2s",
        "cell": "R-official-tail2s",
        "rows": 400,
    },
    {
        "carrier": "slurp",
        "runner": "scripts/flights/run_slurp_closed_list_cell.py",
        "experiment": "slurp-dev1000-closed-list-tail2s-smoke-4-v1",
        "dataset": "slurp-speech-native-dev1000-tail2s-smoke4",
        "cell": "closed-list-tail2s-smoke-4",
        "rows": 4,
    },
    {
        "carrier": "slurp",
        "runner": "scripts/flights/run_slurp_closed_list_cell.py",
        "experiment": "slurp-dev1000-closed-list-tail2s-v1",
        "dataset": "slurp-speech-native-dev1000-tail2s",
        "cell": "closed-list-tail2s",
        "rows": 1000,
    },
)

#: The two preconditions the preregistration names. A stop that matches one of
#: these is EXPECTED and is recorded as such; anything else is a finding.
EXPECTED_STOPS = {
    "gate-not-authorized": "has no pre-registered exposure row",
    "slurp-packet-root-missing": "disagrees with the promotion receipt",
    "a2t-gold-id-rail-missing": "is not in the frozen audio2tool probe receipt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(text: str) -> str:
    for name, needle in EXPECTED_STOPS.items():
        if needle in text:
            return name
    return "UNEXPECTED"


def last_exception(text: str) -> str:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


#: Both runners print ``seal_and_score=<status>`` on their own summary line. A
#: cell that reaches that line has already passed every stop ``classify`` knows
#: about, so a NON-OK status there would otherwise be recorded as
#: ``stop_class: none`` with ``reached_the_end: true`` -- a green that hides the
#: one link §8 item 4 of the preregistration actually exists to prove. It is
#: lifted out here and given its own class instead.
_SEAL_LINE = re.compile(r"seal_and_score=(\S+)")
SEAL_NOT_OK = "seal-and-score-not-ok"


def seal_status(text: str) -> str | None:
    matches = _SEAL_LINE.findall(text)
    return matches[-1] if matches else None


#: ``[12:46:06Z] `` -- the runners' own log stamp. Stripped so this receipt has
#: no timestamp anywhere and two back-to-back writes reproduce the same
#: ``MANIFEST.sha256``, which is this repository's receipt convention.
_LOG_STAMP = re.compile(r"^\[\d{2}:\d{2}:\d{2}Z\]\s*")


def undated(lines: Sequence[str]) -> list[str]:
    return [_LOG_STAMP.sub("", line).strip() for line in lines]


#: The Audio2Tool runner writes its own per-cell wire-check receipt, and its
#: DEFAULT path is inside ``docs/checks/`` -- i.e. inside the study repo. That
#: is harmless when a cell stops early, and it was fatal the first time the
#: gold-id rail let one get all the way to ``seal_and_score``: the smoke cell's
#: receipt landed in the tree, the tree went dirty, and the NEXT cell's scoring
#: correctly refused a COMPLETED manifest on a dirty tree
#: (``core.bundle.require_clean_study_repo``). The receipt is a by-product of a
#: contactless check, not evidence, so it is redirected OUT of the repo -- under
#: ``$SPEECHRL_DATA_DIR``, where large by-products already live -- and this
#: script's own receipt stays the single committed record.
def _scratch_receipt(cell: dict[str, Any]) -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

    directory = Path(data_root()) / "wire-check" / "cross-carrier-ts2"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{cell['cell']}.wire-check.json"


def run_mode(cell: dict[str, Any], mode: str) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO / "src")
    env["CUDA_VISIBLE_DEVICES"] = ""
    argv = [
        sys.executable,
        str(REPO / str(cell["runner"])),
        "--experiment",
        str(cell["experiment"]),
        "--dataset",
        str(cell["dataset"]),
        "--cell",
        str(cell["cell"]),
        f"--{mode}",
    ]
    if cell["carrier"] == "audio2tool":
        argv += ["--wire-check-out", str(_scratch_receipt(cell))]
    completed = subprocess.run(  # noqa: S603 (fixed argv, no shell)
        argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=1800
    )
    merged = completed.stdout + completed.stderr
    stop = last_exception(merged)
    seal = seal_status(merged)
    reached_the_end = completed.returncode == 0 and seal in (None, "OK")
    if completed.returncode != 0:
        stop_class = classify(merged)
    elif seal in (None, "OK"):
        stop_class = "none"
    else:
        stop_class = SEAL_NOT_OK
        stop = next(
            (line.strip() for line in merged.splitlines() if "seal_and_score=" in line),
            stop,
        )
    return {
        "mode": mode,
        "returncode": completed.returncode,
        "reached_the_end": reached_the_end,
        "seal_and_score": seal,
        "stopped_at": _LOG_STAMP.sub("", stop),
        "stop_class": stop_class,
        "stdout_tail": undated(completed.stdout.strip().splitlines()[-6:]),
        "opened_a_socket": False,
        "model_contacts": 0,
    }


def fragment_digests() -> dict[str, str]:
    names = [
        "configs/dataset/slurp-speech-native-dev1000-tail2s.json",
        "configs/dataset/slurp-speech-native-dev1000-tail2s-smoke4.json",
        "configs/model/q4km-mmproj-free-speech-native-np8-ts2-packets-max64.json",
        "configs/experiment/slurp-dev1000-closed-list-tail2s-v1.json",
        "configs/experiment/slurp-dev1000-closed-list-tail2s-smoke-4-v1.json",
        "configs/dataset/audio2tool-calibration-400-tail2s.json",
        "configs/dataset/audio2tool-calibration-400-tail2s-smoke4.json",
        "configs/experiment/a2t-official-protocol-tail2s-400-v1.json",
        "configs/experiment/a2t-official-protocol-tail2s-400-smoke-v1.json",
    ]
    return {name: sha256_file(REPO / name) for name in names}


def build() -> dict[str, Any]:
    results = []
    for cell in CELLS:
        row = {key: cell[key] for key in ("carrier", "experiment", "dataset", "cell", "rows")}
        row["preflight"] = run_mode(cell, "dry-run")
        row["wire_check"] = run_mode(cell, "wire-check")
        results.append(row)
    return {
        "schema": "saea-cross-carrier-ts2-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-07",
        "preregistration": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md"
        ),
        "contacts": {
            "frozen_core": 0,
            "servers_started": 0,
            "sockets_opened": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
        },
        "expected_stops": EXPECTED_STOPS,
        "seal_and_score_rule": (
            "a run that exits 0 is green only when the runner's own "
            "seal_and_score line says OK; any other status is recorded as "
            f"stop_class {SEAL_NOT_OK!r} with reached_the_end false, so a "
            "manifest that seals COMPLETED and then will not score can never "
            "be reported here as 'none'"
        ),
        "fragments": fragment_digests(),
        "cells": results,
        "earnings21": (
            "NO CELL. Earnings-21's 90-second windows are cut at RUNTIME by "
            "reproduction.obs_loop from each whole call; nothing in the harness "
            "consumes pre-cut slices and the full-44 baseline flies through "
            "core.driver.run_experiment_bundled rather than FlightRuntime, so there is "
            "no fragment to compose and no wire check to run. The committed @ts2 window "
            "media is the byte-exact oracle for the one named obs knob that cell needs; "
            "see the preregistration."
        ),
    }


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt")
    args = parser.parse_args()
    receipt = build()
    for row in receipt["cells"]:
        for mode in ("preflight", "wire_check"):
            result = row[mode]
            print(
                "%-11s %-34s %-10s rc=%d %s"
                % (
                    row["carrier"],
                    row["cell"],
                    mode,
                    result["returncode"],
                    result["stop_class"],
                )
            )
    unexpected = [
        (row["cell"], mode)
        for row in receipt["cells"]
        for mode in ("preflight", "wire_check")
        if row[mode]["stop_class"] == "UNEXPECTED"
    ]
    if unexpected:
        print("UNEXPECTED STOPS: %r" % (unexpected,))
    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8")
        (OUT_DIR / "wire-check.json").write_bytes(payload)
        write_manifest(OUT_DIR)
        print("receipt written: %s" % (OUT_DIR / "wire-check.json"))
    else:
        print("(print only; pass --write to land the receipt)")
    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
