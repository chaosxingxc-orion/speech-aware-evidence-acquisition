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


def _load_flight_module(name: str):
    """Import a flight script by path -- the shared venv ships an unrelated
    top-level ``scripts`` package that shadows this repository's namespace
    directory, so ``import scripts.flights...`` is not reliable here (same
    reasoning, same fix, as ``scripts/checks/derived_media_confinement_check.
    py``'s own loader of the same name)."""

    import importlib.util  # noqa: PLC0415

    path = REPO / "scripts" / "flights" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_saea_flight_{name}", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load flight module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stages_for_cell(cell: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The two shared contactless stages for one cell's own real roster rows --
    ``rails.core_client.payload_binding_stage`` and
    ``rails.core_client.media_identity_stage`` -- run BETWEEN the request half
    (``preflight``) and the seal half (``wire_check``'s own
    ``seal_and_score``). **A cell is wire-ready only if it BINDS and is
    IDENTITY-CLOSED.**

    Loads ONLY the rows the binding stage itself will check (every row for a
    "-smoke4" cell, else the first and last of the calibration roster's own
    declared order) -- never the whole 400-row population -- through
    ``run_calibration_cell``'s own roster loader (real media, re-hashed
    against the roster's own record), and drives the binding through the REAL
    carrier root (``data.lock.asset_dir``, never the flight script's own
    ``carrier_root_resolver`` swap) plus this fragment's own declared derived
    media root (``a2t_calibration_derived_subdir``). See
    docs/readiness/2026-09-07-derived-media-confinement-v1.md section 5.

    THE MEDIA-IDENTITY STAGE closes the third blind spot of
    docs/readiness/2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md: this
    check's binding stage read the CARRIER-PREFIXED supplement key while the
    real gate reads the PLAIN one, so all four cells reported BOUND while the
    identity gate saw no supplement at all. The identity stage constructs the
    REAL ``contracts.FrozenCoreGate`` exactly as ``FlightRuntime.preflight``
    constructs it, over the COMPOSED config (all four fragments, so it reads
    what the flight reads), and asserts every roster id is inside D1's
    identity closure plus the loaded rows' bytes. Zero sockets, zero servers,
    zero model contacts.
    """

    from speech_aware_evidence_acquisition.core.base import (  # noqa: PLC0415
        declared_derived_media_roots,
    )
    from speech_aware_evidence_acquisition.core.config import compose  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data.lock import (  # noqa: PLC0415
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: PLC0415
        PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT,
        media_identity_stage,
        payload_binding_stage,
    )

    dataset = str(cell["dataset"])
    values = json.loads(
        (REPO / "configs" / "dataset" / f"{dataset}.json").read_text(encoding="utf-8")
    )
    carrier_lock_key = str(values["carrier_lock_key"])
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    carrier_root = asset_dir(lock, carrier_lock_key, root)
    derived_media_roots = declared_derived_media_roots(values, root)

    roster_path = REPO / str(values["a2t_calibration_subset_receipt"])
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    module = _load_flight_module("run_calibration_cell")
    # The full-400 and "-smoke4" A2T dataset fragments SHARE one 400-row
    # roster receipt; the smoke restriction to 4 ids lives in the EXPERIMENT
    # fragment's own "populations" entry, read exactly as run_calibration_
    # cell.py's CLI itself reads it -- never assume the receipt's own item
    # count is this cell's population size.
    experiment_doc = json.loads(
        (REPO / "configs" / "experiment" / f"{cell['experiment']}.json").read_text(
            encoding="utf-8"
        )
    )
    all_ids = module.population_ids(experiment_doc, dataset) or [
        str(item["sample_id"]) for item in receipt["items"]
    ]
    wanted = (
        all_ids
        if len(all_ids) <= PAYLOAD_BINDING_STAGE_CHEAP_ROW_LIMIT
        else [all_ids[0], all_ids[-1]]
    )
    samples = module.roster_samples(
        roster_path,
        str(values["a2t_calibration_subset_receipt_sha256"]),
        root,
        limit_sample_ids=wanted,
        media_prefix=str(values.get("a2t_calibration_derived_subdir", "")) or None,
    )

    result = payload_binding_stage(
        dataset_fragment=dataset,
        carrier_lock_key=carrier_lock_key,
        samples=samples,
        data_root=root,
        carrier_root=carrier_root,
        derived_media_roots=derived_media_roots,
    )
    binding = dict(result.as_receipt())
    # The stage's own ``rows_total`` counts only the rows THIS CALL loaded
    # (never the whole 400-row population, to keep the stage cheap);
    # ``fragment_row_count`` is the fragment's own full roster size.
    binding["fragment_row_count"] = len(all_ids)
    binding["checked_every_row"] = len(all_ids) <= len(result.rows_checked)

    # The gate reads the COMPOSED config, not the dataset fragment alone --
    # ``runtime_receipt_relpath`` and ``model_lock_key`` live in the model
    # fragment. Compose exactly as ``run_calibration_cell.build_runtime``
    # does, off this cell's own declared model/baseline fragments.
    cell_doc = next(
        item
        for item in experiment_doc["cells"]
        if str(item["cell_id"]) == str(cell["cell"])
    )
    composed = compose(
        REPO,
        str(cell_doc["model_fragment"]),
        dataset,
        str(cell_doc["baseline_fragment"]),
        str(cell["experiment"]),
    )
    identity = media_identity_stage(
        dataset_fragment=dataset,
        carrier_lock_key=carrier_lock_key,
        values=composed.values,
        repo_root=REPO,
        data_root=root,
        runtime_root=module.RUNTIME_ROOT,
        roster_sample_ids=all_ids,
        samples=samples,
    )
    return {
        "payload_binding_stage": binding,
        "media_identity_stage": dict(identity.as_receipt()),
    }


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
        # The two mandatory contactless stages: BETWEEN the request half
        # (preflight, above) and the seal half (wire_check's own
        # seal_and_score, below). Zero sockets, zero servers, zero model
        # contacts -- see stages_for_cell's own docstring.
        row.update(stages_for_cell(cell))
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
        "wire_ready_rule": (
            "a cell is wire-ready only if it BINDS and is IDENTITY-CLOSED. The "
            "payload_binding_stage proves media-path confinement; the "
            "media_identity_stage constructs the REAL contracts.FrozenCoreGate "
            "exactly as core.flight.FlightRuntime.preflight constructs it and "
            "proves every roster id is inside D1's media identity closure plus "
            "the loaded rows' bytes. The two read DIFFERENT config keys, which "
            "is why a green binding stage alone was not evidence "
            "(docs/readiness/2026-09-09-a2t-derived-media-d1-declaration-fix-v1.md)"
        ),
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
        stage = row["payload_binding_stage"]
        print(
            "%-8s %-30s %-10s %s  rows_checked=%d/%d"
            % (
                row["variant"],
                row["cell"],
                "binding_stage",
                "BOUND" if stage["bound"] else "NOT BOUND",
                len(stage["rows_checked"]),
                stage["fragment_row_count"],
            )
        )
        identity = row["media_identity_stage"]
        print(
            "%-8s %-30s %-10s %s  roster=%d closure=%d verified=%d%s"
            % (
                row["variant"],
                row["cell"],
                "identity",
                "IDENTITY-CLOSED" if identity["identity_closed"] else "NOT CLOSED",
                identity["roster_ids_checked"],
                identity["closure_ids"],
                len(identity["rows_verified"]),
                "" if identity["identity_closed"] else "  %s" % identity["refusal"],
            )
        )
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
    not_bound = [row["cell"] for row in receipt["cells"] if not row["payload_binding_stage"]["bound"]]
    not_closed = [
        row["cell"]
        for row in receipt["cells"]
        if not row["media_identity_stage"]["identity_closed"]
    ]
    if unexpected:
        print("UNEXPECTED STOPS: %r" % (unexpected,))
    if not_bound:
        print("PAYLOAD-BINDING STAGE FAILED (cell not wire-ready): %r" % (not_bound,))
    if not_closed:
        print("MEDIA-IDENTITY STAGE FAILED (cell not wire-ready): %r" % (not_closed,))
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
    return 1 if (unexpected or not_bound or not_closed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
