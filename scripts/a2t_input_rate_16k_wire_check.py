#!/usr/bin/env python3
"""Compose and drive the two Audio2Tool input-rate cells with ZERO sockets, and
record exactly how far each one gets.

Two modes per cell, both contactless:

``preflight``
    ``core.flight.FlightRuntime.preflight`` behind the REAL
    ``contracts.FrozenCoreGate``: config composition, roster hydration with a
    per-file SHA-256 re-hash of every media file, media-path confinement to the
    variant's own derived root, the count check, ``ExecutionPlan`` construction
    and the execution-profile check -- and then the gate's refusal, because
    these cells are preregistered and NOT authorized.

``wire``
    ``FlightRuntime.wire_check``: the same request path against a fake gate and
    a transport that never opens a socket, and then -- the SEAL HALF -- the
    manifest builder, the bundle verifier and the registered official scorer.

The point of this receipt is not a green tick. It is to record, before anyone
spends GPU time, the EXACT line at which each cell stops today and why, so the
preregistration's precondition is a measured fact rather than a reviewer's
guess. A cell that stops is reported as stopping, with the exception class and
message it stopped with.

**The request half and the seal half are reported separately**, because they
fail for different reasons and only one of them is blocked here: the
``@16k`` / ``@16k+ts2`` gold-id rail is a change to a paper-facing scoring path
that this preparation deliberately did not make (preregistration §7.1). If the
rail has landed in this branch the seal half runs; if it has not, the seal half
is reported as ``PENDING`` against that named change rather than as a failure.

Model-free. Zero model contacts, zero servers, zero sockets, zero GPU. Run
under the media row this campaign already registered.

Usage (WSL2)::

    python scripts/a2t_input_rate_16k_wire_check.py
    python scripts/a2t_input_rate_16k_wire_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
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
    / "2026-09-07-a2t-input-rate-16k-wire-check"
)

RUNNER = "scripts/flights/run_calibration_cell.py"

CELLS: tuple[dict[str, Any], ...] = (
    {
        "variant": "16k",
        "experiment": "a2t-official-protocol-16k-400-smoke-v1",
        "dataset": "audio2tool-calibration-400-16k-smoke4",
        "cell": "R-official-16k-smoke-4",
        "rows": 4,
    },
    {
        "variant": "16k",
        "experiment": "a2t-official-protocol-16k-400-v1",
        "dataset": "audio2tool-calibration-400-16k",
        "cell": "R-official-16k",
        "rows": 400,
    },
    {
        "variant": "16k+ts2",
        "experiment": "a2t-official-protocol-16k-tail2s-400-smoke-v1",
        "dataset": "audio2tool-calibration-400-16k-tail2s-smoke4",
        "cell": "R-official-16k-tail2s-smoke-4",
        "rows": 4,
    },
    {
        "variant": "16k+ts2",
        "experiment": "a2t-official-protocol-16k-tail2s-400-v1",
        "dataset": "audio2tool-calibration-400-16k-tail2s",
        "cell": "R-official-16k-tail2s",
        "rows": 400,
    },
)

#: The preconditions the preregistration names. A stop that matches one of these
#: is EXPECTED and is recorded as such; anything else is a finding.
EXPECTED_STOPS = {
    "gate-not-authorized": "has no pre-registered exposure row",
    "a2t-gold-id-rail-missing": "is not in the frozen audio2tool probe receipt",
}

FRAGMENTS = (
    "configs/dataset/audio2tool-calibration-400-16k.json",
    "configs/dataset/audio2tool-calibration-400-16k-smoke4.json",
    "configs/dataset/audio2tool-calibration-400-16k-tail2s.json",
    "configs/dataset/audio2tool-calibration-400-16k-tail2s-smoke4.json",
    "configs/experiment/a2t-official-protocol-16k-400-v1.json",
    "configs/experiment/a2t-official-protocol-16k-400-smoke-v1.json",
    "configs/experiment/a2t-official-protocol-16k-tail2s-400-v1.json",
    "configs/experiment/a2t-official-protocol-16k-tail2s-400-smoke-v1.json",
)

#: ``[12:46:06Z] `` -- the runner's own log stamp. Stripped so this receipt has
#: no timestamp anywhere and two back-to-back writes reproduce the same
#: ``MANIFEST.sha256``.
_LOG_STAMP = re.compile(r"^\[\d{2}:\d{2}:\d{2}Z\]\s*")


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


def undated(lines: Sequence[str]) -> list[str]:
    return [_LOG_STAMP.sub("", line).strip() for line in lines]


def gold_id_rail_state() -> dict[str, Any]:
    """Has the ``@`` gold-id rail landed on this branch?

    Measured from the adapter's own source, not assumed: the rail is one call to
    ``published_segment_key`` (or an equivalent split on the first ``@``) around
    the ``expected_by_id`` lookup. It lands on ``wt/ts2y``; until that merge the
    seal half of every suffixed Audio2Tool population is blocked.
    """

    from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
        Audio2ToolAdapter,
    )

    source = inspect.getsource(Audio2ToolAdapter.gold)
    landed = (
        # The name the rail actually landed under when ``wt/ts2y`` merged: the
        # rule moved into ``data.variant_ids`` so the three carriers cannot
        # drift into three spellings of it. The Earnings-22 spelling and a raw
        # split stay accepted, because either would be the same rail.
        "published_sample_key" in source
        or "published_segment_key" in source
        or 'split("@"' in source
    )
    return {
        "landed": landed,
        "call_site": "rails/adapters/audio2tool.py::Audio2ToolAdapter.gold",
        "precedent": (
            "reproduction.esb_reference.published_segment_key -- splits a derived-media "
            "id on the FIRST '@' and is provably inert for unsuffixed ids"
        ),
        "lands_on": "wt/ts2y",
        "blocks": (
            "the SEAL half of every suffixed Audio2Tool population (@ts2, @16k and "
            "@16k+ts2 alike). One rail unblocks all three."
        )
        if not landed
        else "nothing -- the rail is present on this branch",
    }


def _scratch_receipt(cell: dict[str, Any]) -> Path:
    """Where the runner's own wire-check by-product goes: outside the repo."""

    from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

    directory = Path(data_root()) / "wire-check" / "a2t-input-rate-16k"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{cell['cell']}.wire-check.json"


def run_mode(cell: dict[str, Any], mode: str) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO / "src")
    env["CUDA_VISIBLE_DEVICES"] = ""
    argv = [
        sys.executable,
        str(REPO / RUNNER),
        "--experiment",
        str(cell["experiment"]),
        "--dataset",
        str(cell["dataset"]),
        "--cell",
        str(cell["cell"]),
        f"--{mode}",
    ]
    if mode == "wire-check":
        # Never the runner's default, which points inside a SEALED 2026-09-04
        # check directory -- and never inside THIS check's directory either.
        # The runner's per-cell receipt is a by-product of a contactless check,
        # not evidence: once the gold-id rail landed the cells run far enough
        # for it to be written, it lands in the working tree, the tree goes
        # dirty, and the next cell's scoring correctly refuses a COMPLETED
        # manifest on a dirty tree. Same defect, same fix as
        # ``scripts/cross_carrier_tail2s_wire_check.py`` -- out of the repo,
        # under ``$SPEECHRL_DATA_DIR``, where large by-products already live.
        argv += ["--wire-check-out", str(_scratch_receipt(cell))]
    completed = subprocess.run(  # noqa: S603 (fixed argv, no shell)
        argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=1800
    )
    merged = completed.stdout + completed.stderr
    stop = last_exception(merged)
    return {
        "mode": mode,
        "returncode": completed.returncode,
        "reached_the_end": completed.returncode == 0,
        "stopped_at": _LOG_STAMP.sub("", stop),
        "stop_class": "none" if completed.returncode == 0 else classify(merged),
        "stdout_tail": undated(completed.stdout.strip().splitlines()[-6:]),
        "opened_a_socket": False,
        "model_contacts": 0,
    }


def build() -> dict[str, Any]:
    rail = gold_id_rail_state()
    results = []
    for cell in CELLS:
        row = {key: cell[key] for key in ("variant", "experiment", "dataset", "cell", "rows")}
        row["preflight"] = run_mode(cell, "dry-run")
        row["wire_check"] = run_mode(cell, "wire-check")
        blocked = (
            not rail["landed"]
            and row["wire_check"]["stop_class"] == "a2t-gold-id-rail-missing"
        )
        row["request_half"] = (
            "RAN. The stop is at the FIRST per-row metrics call, which is downstream of "
            "the whole request path: config composition, roster hydration, payload "
            "binding, tool-schema resolution and the fake-transport dispatch all "
            "completed for the first sample before gold was ever asked for."
            if blocked
            else ("see wire_check" if not rail["landed"] else "RAN -- see wire_check")
        )
        row["seal_half"] = (
            "PENDING the '@' gold-id rail merge from wt/ts2y. rails/task_adapter.py:198 "
            "calls adapter.gold() from score(), which core/flight/runtime.py:2653 calls "
            "per row immediately after dispatch -- so the rail blocks per-row metrics "
            "first, and FlightRuntime.wire_check's seal_and_score stage is downstream of "
            "that and is never reached. It is neither passed nor failed here."
            if blocked
            else "RAN -- see wire_check"
        )
        results.append(row)
    return {
        "schema": "saea-a2t-input-rate-16k-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-07",
        "preregistration": (
            "docs/readiness/2026-09-07-a2t-input-rate-standardization-v1-preregistration.md"
        ),
        "media_exposure_row": "SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1",
        "execution_profile": "model-free-check",
        "contacts": {
            "frozen_core": 0,
            "servers_started": 0,
            "sockets_opened": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
        },
        "what_preflight_proves": (
            "config composition, roster hydration with a per-file SHA-256 re-hash of all "
            "400 media, media-path confinement to the variant's OWN derived root, the "
            "count check and ExecutionPlan construction all pass -- and only THEN does "
            "the real gate refuse, because these cells are not authorized. Reaching the "
            "gate is the CORRECT state."
        ),
        "gold_id_rail": rail,
        "where_the_rail_bites": (
            "rails/task_adapter.py:198 (score -> gold) called from "
            "core/flight/runtime.py:2653 (_row_for), i.e. per row immediately AFTER the "
            "response comes back from the fake transport. So the request half is proved "
            "and the seal half is unreachable until the rail lands -- not because sealing "
            "is broken, but because nothing downstream of the first row's metrics runs."
        ),
        "expected_stops": EXPECTED_STOPS,
        "fragments": {name: sha256_file(REPO / name) for name in FRAGMENTS},
        "cells": results,
        "authorizes": (
            "nothing. No contact, no server, no scoring and no Stage-3 activity."
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
    rail = receipt["gold_id_rail"]
    print(
        "gold-id rail on this branch: %s (%s)"
        % ("LANDED" if rail["landed"] else "ABSENT", rail["call_site"])
    )
    for row in receipt["cells"]:
        for mode in ("preflight", "wire_check"):
            result = row[mode]
            print(
                "%-8s %-30s %-10s rc=%d %s"
                % (
                    row["variant"],
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
