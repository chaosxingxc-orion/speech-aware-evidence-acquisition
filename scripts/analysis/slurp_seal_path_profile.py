#!/usr/bin/env python3
"""Profile the seal path of one already-sealed flight bundle, offline, against a scratch
target that this script creates and deletes -- never against the sealed directory.

WHY. During the ROLL-2 flight the run directory grew at about 1.5 MB/s into two large files
while the drvfs mount's own sequential write rate is about 164 MB/s (ext4: about 1,590 MB/s).
The coordinator refused to move the run root to ext4 on an unverified attribution. This
script settles it with numbers: it re-runs the seal writer's stages over the sealed bytes of
one bundle, to a scratch directory on the mount and then to one on ext4, and splits the wall
time among JSON serialisation, JSON parsing, hashing, per-record open/close, fsync and raw
read/write with ``cProfile``.

WHAT IS PROFILED. ``core.flight.runtime.FlightRuntime.seal`` needs a live, composed flight
(its config, plan, client, lock, serving session and a clean study tree), so it cannot be
invoked outside a flight. Every stage it performs on the run directory CAN be, and is, with
the repository's own functions wherever they take a path:

* the ``<run_id>.outputs.jsonl`` writer's exact expression (``json.dumps(row,
  ensure_ascii=False, sort_keys=True)`` per row, one buffered stream);
* the ``<run_id>.phases.json`` writer's exact expression (``json.dumps(..., indent=2,
  sort_keys=True, default=str)`` + ``Path.write_text``), timed as serialise + write;
* ``core.tracing.TraceSink.close`` -> ``e0.artifacts.write_json_artifact`` for the trace
  manifest (the real function);
* ``core.bundle.manifest.build_manifest``'s hashing of every artifact (``sha256_file``, the
  real function) and the manifest write (``write_json_artifact`` over the sealed GENERATION
  manifest with only its artifact paths rewritten to the scratch directory);
* ``core.bundle.verify.verify_bundle`` (the real function) over that scratch manifest;
* ``core.flight.scoring.seal_scoring_inputs`` (the real function; three fsynced files);
* ``core.driver.speech_native.read_attempt_trace_facts`` (the flight-receipt builder's pass
  over the trace; the real function);
* ``core.flight.receipts.write_flight_receipts`` (the real function; fsync + atomic replace)
  over the sealed ledger rebuilt as a ``FlightReceipts``.

Beside the seal proper, the IN-FLIGHT trace growth is replayed, because that is what the
run directory does at 1.5 MB/s: ``TraceSink.emit`` opens ``<run_id>.trace.jsonl`` in append
mode, writes one line and closes it, once per record. The sealed lines are re-appended with
that per-record pattern and again with one open per file; both reproduce the sealed bytes.

Every reproduced file is hashed and compared with the sealed artifact's sha256 (from the
sealed run manifest, or from the sealed directory listing hashed before the profile), so
the profile is over the SAME bytes the flight wrote. The sealed directory is hashed before
and after and the two listings must be identical.

ZERO CONTACTS: no model, server, encoder, tokenizer, scorer, GPU or network. Official
scoring (``core.scorers.score_bundle``, a scorer contact) is deliberately NOT part of this
profile; the deferred-scoring seal that every recent flight uses ends at
``seal_scoring_inputs`` and the scorer runs later in the score worker. Single-threaded.
Nothing is printed or persisted from the sealed content except sizes, counts, timings,
function names and hashes.

Run (WSL, speechrl venv; one target at a time so the two never contend)::

    P=scripts/analysis/slurp_seal_path_profile.py
    python -B $P --target-label mount --mode wall \
        --scratch-dir $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEAL-PATH-PROFILE-V1/scratch-mount
    python -B $P --target-label ext4 --mode wall \
        --scratch-dir /home/chao/saea-worktrees/.decomp-scratch/seal-profile-ext4
    (the same two with --mode cprofile)
    python -B $P --render <the four JSON files> --markdown docs/results/...md

Timings are measurements and differ between runs; every hash, count, size and
byte-identity flag is deterministic. The JSON artefacts carry one ``generated_at`` stamp.
"""

from __future__ import annotations

import argparse
import cProfile
import gc
import hashlib
import io
import json
import os
import platform
import pstats
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

RECIPE_ID = "slurp-seal-path-profile-v1"
SCHEMA = "saea-slurp-seal-path-profile-v1"
OUT_DIRNAME = "SAEA-SLURP-SEAL-PATH-PROFILE-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-seal-path-profile.md"
DEFAULT_RUN_ID = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1"
DEFAULT_ATTEMPT_ID = "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation"

SEAL_STAGES = (
    "outputs_write",
    "phases_write",
    "trace_manifest_write",
    "manifest_hashing",
    "run_manifest_write",
    "verify_bundle",
    "seal_scoring_inputs",
    "trace_facts_scan",
    "flight_receipts_write",
)
INFLIGHT_STAGES = ("trace_append_per_record", "trace_append_batched")
INPUT_STAGES = ("sealed_trace_read",)
ALL_STAGES = INPUT_STAGES + INFLIGHT_STAGES + SEAL_STAGES

CATEGORIES = (
    "io.read",
    "io.write",
    "io.open/close/stat",
    "fsync",
    "json.encode",
    "json.decode",
    "hash",
    "boundary/validate",
    "bundle.python",
    "other",
)


class ProfileError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_tree(root: Path) -> dict:
    files = {}
    for path in sorted(p for p in Path(root).rglob("*") if p.is_file()):
        files[str(path.relative_to(root))] = {"sha256": sha256_path(path), "bytes": path.stat().st_size}
    combined = hashlib.sha256(
        "".join(f"{k} {v['sha256']} {v['bytes']}\n" for k, v in sorted(files.items())).encode("utf-8")
    ).hexdigest()
    return {"files": files, "count": len(files), "bytes": sum(v["bytes"] for v in files.values()), "combined_sha256": combined}


def fs_type(path: Path) -> str:
    try:
        out = subprocess.run(["stat", "-f", "-c", "%T", str(path)], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception as error:  # noqa: BLE001 -- informational only
        return f"unknown ({type(error).__name__})"


def free_memory_gib() -> float | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except OSError:
        return None
    return None


def categorise(func: tuple) -> str:
    file, _line, name = func
    f = str(file).replace("\\", "/")
    if f == "~":
        n = name
        if "posix.fsync" in n or "posix.fdatasync" in n:
            return "fsync"
        if "_hashlib" in n or "openssl_sha" in n or "hexdigest" in n or "hashlib" in n:
            return "hash"
        if "_json" in n or "scanstring" in n:
            return "json.encode" if "encode" in n else "json.decode"
        if "of '_io." in n:
            if "read" in n or "__next__" in n:
                return "io.read"
            if "write" in n or "flush" in n:
                return "io.write"
            return "io.open/close/stat"
        if any(k in n for k in ("io.open", "posix.open", "posix.fdopen", "posix.stat", "posix.lstat", "posix.fstat",
                                "posix.replace", "posix.unlink", "posix.mkdir", "posix.rename", "posix.scandir",
                                "posix.listdir", "posix.remove", "posix.getpid", "posix.fspath", "posix.getcwd",
                                "posix.readlink", "posix.access", "fcntl", "posix.close")):
            return "io.open/close/stat"
        return "other"
    if f.endswith("json/encoder.py") or (f.endswith("json/__init__.py") and name in ("dumps", "dump")):
        return "json.encode"
    if f.endswith("json/decoder.py") or f.endswith("json/scanner.py") or (f.endswith("json/__init__.py") and name in ("loads", "load")):
        return "json.decode"
    if f.endswith("hashlib.py"):
        return "hash"
    if "/contracts/" in f:
        return "boundary/validate"
    if any(k in f for k in ("/core/bundle/", "/core/flight/", "/core/driver/", "/e0/artifacts.py", "/core/tracing.py", "/core/attempts", "/core/split_receipt", "/core/config", "/core/legality", "/data/splits")):
        return "bundle.python"
    return "other"


def summarise_profile(profile: cProfile.Profile) -> dict:
    stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stream)
    by_category = {c: 0.0 for c in CATEGORIES}
    calls_by_category = {c: 0 for c in CATEGORIES}
    entries = []
    for func, (cc, nc, tt, ct, _callers) in stats.stats.items():
        category = categorise(func)
        by_category[category] += tt
        calls_by_category[category] += nc
        entries.append((tt, ct, nc, func, category))
    entries.sort(key=lambda e: (-e[0], str(e[3])))
    total = sum(by_category.values())
    top = [
        {
            "function": f"{Path(str(func[0])).name}:{func[1]} {func[2]}" if func[0] != "~" else func[2],
            "category": category,
            "tottime_s": round(tt, 4),
            "cumtime_s": round(ct, 4),
            "calls": nc,
        }
        for tt, ct, nc, func, category in entries[:25]
    ]
    return {
        "tottime_total_s": round(total, 4),
        "by_category_s": {c: round(v, 4) for c, v in by_category.items()},
        "by_category_share": {c: (round(100.0 * v / total, 2) if total else 0.0) for c, v in by_category.items()},
        "calls_by_category": calls_by_category,
        "top_functions": top,
    }


class Timer:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def run(self, fn):
        gc.collect()
        if self.mode == "cprofile":
            profile = cProfile.Profile()
            start = time.perf_counter()
            profile.enable()
            try:
                out = fn()
            finally:
                profile.disable()
            wall = time.perf_counter() - start
            return out, wall, summarise_profile(profile)
        start = time.perf_counter()
        out = fn()
        return out, time.perf_counter() - start, None


# --------------------------------------------------------------------------
# The profile
# --------------------------------------------------------------------------


def run_profile(args) -> dict:
    from speech_aware_evidence_acquisition.core.bundle import BundleError
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_outputs,
        _verify_outputs_trace_binding,
        _verify_raw_trace,
    )
    from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
    from speech_aware_evidence_acquisition.core.driver.speech_native import read_attempt_trace_facts
    from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts, write_flight_receipts
    from speech_aware_evidence_acquisition.core.flight.scoring import seal_scoring_inputs
    from speech_aware_evidence_acquisition.e0.artifacts import sha256_file, write_json_artifact

    data_root = args.data_root.resolve()
    runs_root = (data_root / "runs").resolve()
    sealed = (runs_root / args.run_id / args.attempt_id).resolve()
    if not sealed.is_dir():
        raise ProfileError(f"sealed attempt directory missing: {sealed}")
    scratch = args.scratch_dir.resolve()
    if scratch.exists():
        raise ProfileError(f"scratch directory already exists, refusing to reuse it: {scratch}")
    if runs_root == scratch or runs_root in scratch.parents:
        raise ProfileError("the scratch directory must not live under the governed runs directory")
    if REPO == scratch or REPO in scratch.parents:
        raise ProfileError("the scratch directory must not live inside the repository")
    stages_wanted = set(ALL_STAGES) if not args.stages else set(args.stages.split(","))
    unknown = stages_wanted - set(ALL_STAGES)
    if unknown:
        raise ProfileError(f"unknown stage(s) {sorted(unknown)}; known: {ALL_STAGES}")

    run_id = args.run_id
    timer = Timer(args.mode)
    result: dict = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "attempt_id": args.attempt_id,
        "sealed_dir": str(sealed),
        "target_label": args.target_label,
        "scratch_dir": str(scratch),
        "mode": args.mode,
        "python": platform.python_version(),
        "kernel": platform.release(),
        "single_threaded": True,
        "stages": {},
        "notes": [],
    }

    print(f"[{args.target_label}/{args.mode}] hashing the sealed directory before", flush=True)
    before = hash_tree(sealed)
    result["sealed_before"] = {"count": before["count"], "bytes": before["bytes"], "combined_sha256": before["combined_sha256"]}
    sealed_hash_of = {k: v["sha256"] for k, v in before["files"].items()}

    manifest_path = sealed / f"{run_id}.run-manifest.json"
    generation_path = sealed / f"{run_id}.generation-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    expected = {
        "outputs": manifest["outputs"]["sha256"],
        "raw_trace": manifest["raw_trace"]["sha256"],
        "trace_manifest": manifest["trace_manifest"]["sha256"],
        "phases": sealed_hash_of.get(f"{run_id}.phases.json"),
        "flight_receipts": sealed_hash_of.get("flight-receipts.json"),
    }
    result["expected_sha256"] = expected
    result["sealed_sizes"] = {
        name: (sealed / name).stat().st_size
        for name in (
            f"{run_id}.outputs.jsonl", f"{run_id}.trace.jsonl", f"{run_id}.trace-manifest.json",
            f"{run_id}.phases.json", f"{run_id}.run-manifest.json", "flight-receipts.json",
        )
        if (sealed / name).is_file()
    }

    scratch.mkdir(parents=True, exist_ok=False)
    result["scratch_fs_type"] = fs_type(scratch)
    result["sealed_fs_type"] = fs_type(sealed)
    result["mem_available_gib_start"] = free_memory_gib()
    scratch_trace = scratch / f"{run_id}.trace.jsonl"
    scratch_outputs = scratch / f"{run_id}.outputs.jsonl"
    scratch_trace_manifest = scratch / f"{run_id}.trace-manifest.json"
    scratch_phases = scratch / f"{run_id}.phases.json"
    scratch_manifest = scratch / f"{run_id}.run-manifest.json"
    scratch_receipts = scratch / "flight-receipts.json"

    def record(name: str, wall: float, profile: dict | None, **extra) -> None:
        entry = {"wall_s": round(wall, 4), **extra}
        if profile is not None:
            entry["cprofile"] = profile
        result["stages"][name] = entry
        print(f"[{args.target_label}/{args.mode}] {name}: {wall:.3f} s {extra.get('bytes', '')}", flush=True)

    try:
        # ---- the sealed trace, read once (input; the mount's read side) ----
        trace_bytes: bytes | None = None
        trace_lines: list[str] = []
        if stages_wanted & (set(INFLIGHT_STAGES) | set(SEAL_STAGES) | {"sealed_trace_read"}):
            trace_bytes, wall, prof = timer.run(lambda: (sealed / f"{run_id}.trace.jsonl").read_bytes())
            record("sealed_trace_read", wall, prof, bytes=len(trace_bytes), mib_per_s=round(len(trace_bytes) / wall / 2**20, 1))
            text = trace_bytes.decode("utf-8")
            trace_lines = text.split("\n")
            if trace_lines and trace_lines[-1] == "":
                trace_lines.pop()
            del text
            result["trace_records"] = len(trace_lines)

        # ---- in-flight trace growth, replayed ----
        if "trace_append_per_record" in stages_wanted:
            def per_record():
                for line in trace_lines:
                    with scratch_trace.open("a", encoding="utf-8", newline="\n") as handle:
                        handle.write(line + "\n")
            _, wall, prof = timer.run(per_record)
            got = sha256_path(scratch_trace)
            record(
                "trace_append_per_record", wall, prof, bytes=scratch_trace.stat().st_size, records=len(trace_lines),
                per_record_ms=round(1000.0 * wall / max(1, len(trace_lines)), 4),
                mib_per_s=round(scratch_trace.stat().st_size / wall / 2**20, 1),
                byte_identical=(got == expected["raw_trace"]), sha256=got,
                pattern="TraceSink.emit: open('a') + write(line) + close per record; no fsync",
            )
        elif stages_wanted & set(SEAL_STAGES):
            # The seal stages need the trace on the scratch target; write it the batched way.
            with scratch_trace.open("w", encoding="utf-8", newline="\n") as handle:
                for line in trace_lines:
                    handle.write(line + "\n")
        if "trace_append_batched" in stages_wanted:
            batched_path = scratch / f"{run_id}.trace.batched.jsonl"
            def batched():
                with batched_path.open("a", encoding="utf-8", newline="\n") as handle:
                    for line in trace_lines:
                        handle.write(line + "\n")
            _, wall, prof = timer.run(batched)
            got = sha256_path(batched_path)
            record(
                "trace_append_batched", wall, prof, bytes=batched_path.stat().st_size, records=len(trace_lines),
                per_record_ms=round(1000.0 * wall / max(1, len(trace_lines)), 4),
                mib_per_s=round(batched_path.stat().st_size / wall / 2**20, 1),
                byte_identical=(got == expected["raw_trace"]), sha256=got,
                pattern="one open per file, the same lines in the same order",
            )
            batched_path.unlink()
        del trace_bytes
        trace_lines = []
        gc.collect()

        # ---- outputs ----
        if "outputs_write" in stages_wanted:
            rows = []
            with (sealed / f"{run_id}.outputs.jsonl").open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        rows.append(json.loads(line))
            def write_outputs():
                with scratch_outputs.open("w", encoding="utf-8") as handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            _, wall, prof = timer.run(write_outputs)
            got = sha256_path(scratch_outputs)
            record("outputs_write", wall, prof, bytes=scratch_outputs.stat().st_size, rows=len(rows),
                   byte_identical=(got == expected["outputs"]), sha256=got)
            del rows
        elif stages_wanted & set(SEAL_STAGES):
            shutil.copyfile(sealed / f"{run_id}.outputs.jsonl", scratch_outputs)

        # ---- phases ----
        if "phases_write" in stages_wanted:
            phases_doc = json.loads((sealed / f"{run_id}.phases.json").read_text(encoding="utf-8"))
            holder: dict = {}
            def phases_dumps():
                holder["text"] = json.dumps(phases_doc, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n"
            _, wall_dumps, prof_dumps = timer.run(phases_dumps)
            def phases_write():
                scratch_phases.write_text(holder["text"], encoding="utf-8", newline="\n")
            _, wall_write, prof_write = timer.run(phases_write)
            got = sha256_path(scratch_phases)
            entry_prof = None
            if prof_dumps is not None:
                entry_prof = {"serialise": prof_dumps, "write": prof_write}
            record("phases_write", wall_dumps + wall_write, entry_prof, bytes=scratch_phases.stat().st_size,
                   serialise_s=round(wall_dumps, 4), write_s=round(wall_write, 4),
                   write_mib_per_s=round(scratch_phases.stat().st_size / wall_write / 2**20, 1),
                   byte_identical=(got == expected["phases"]), sha256=got,
                   pattern="json.dumps(indent=2, sort_keys=True, default=str) is the pure-Python encoder (indent disables the C encoder)")
            del phases_doc, holder
            gc.collect()

        # ---- trace manifest (TraceSink.close) ----
        if "trace_manifest_write" in stages_wanted:
            tm_doc = json.loads((sealed / f"{run_id}.trace-manifest.json").read_text(encoding="utf-8"))
            _, wall, prof = timer.run(lambda: write_json_artifact(scratch_trace_manifest, tm_doc))
            got = sha256_path(scratch_trace_manifest)
            record("trace_manifest_write", wall, prof, bytes=scratch_trace_manifest.stat().st_size, records=len(tm_doc.get("records", {})),
                   byte_identical=(got == expected["trace_manifest"]), sha256=got,
                   pattern="write_json_artifact: json.dumps(indent=2) + write_text + sha256_file re-read")
            del tm_doc
        elif stages_wanted & set(SEAL_STAGES):
            shutil.copyfile(sealed / f"{run_id}.trace-manifest.json", scratch_trace_manifest)

        # ---- build_manifest's hashing ----
        session_receipt_path = Path(str((generation.get("session_receipt") or {}).get("path") or ""))
        if "manifest_hashing" in stages_wanted:
            targets = [scratch_outputs, scratch_trace, scratch_trace_manifest]
            if session_receipt_path.is_file():
                targets.append(session_receipt_path)
            def hash_all():
                return {p.name: sha256_file(p) for p in targets}
            hashes, wall, prof = timer.run(hash_all)
            total_bytes = sum(p.stat().st_size for p in targets)
            record("manifest_hashing", wall, prof, bytes=total_bytes, files=len(targets),
                   mib_per_s=round(total_bytes / wall / 2**20, 1),
                   byte_identical=(hashes.get(scratch_trace.name) == expected["raw_trace"] and hashes.get(scratch_outputs.name) == expected["outputs"]),
                   pattern="sha256_file over outputs, raw trace, trace manifest and the session receipt (1 MiB chunks)")

        # ---- the manifest itself (generation manifest with scratch paths) ----
        scratch_doc = json.loads(json.dumps(generation))
        for key, path in (("outputs", scratch_outputs), ("raw_trace", scratch_trace), ("trace_manifest", scratch_trace_manifest)):
            if isinstance(scratch_doc.get(key), dict):
                scratch_doc[key]["path"] = str(path.resolve())
        if "run_manifest_write" in stages_wanted or stages_wanted & {"verify_bundle", "seal_scoring_inputs"}:
            _, wall, prof = timer.run(lambda: write_json_artifact(scratch_manifest, scratch_doc))
            if "run_manifest_write" in stages_wanted:
                record("run_manifest_write", wall, prof, bytes=scratch_manifest.stat().st_size,
                       pattern="write_json_artifact over the sealed generation manifest with three artifact paths rewritten")

        # ---- verify_bundle ----
        if "verify_bundle" in stages_wanted:
            outcome: dict = {}
            def verify():
                try:
                    bundle = verify_bundle(scratch_manifest)
                    outcome["verified"] = True
                    outcome["outputs_rows"] = len(bundle.outputs_rows)
                    outcome["attempt_state"] = bundle.attempt_state
                except BundleError as error:
                    outcome["verified"] = False
                    outcome["error"] = str(error)[:300]
            _, wall, prof = timer.run(verify)
            record("verify_bundle", wall, prof, bytes=sum(p.stat().st_size for p in (scratch_outputs, scratch_trace, scratch_trace_manifest)),
                   pattern="verify_bundle: read_bytes + sha256 of every artifact, json.loads of every outputs row and trace record, "
                           "TraceRecord canonical re-serialisation + sha256 per record, outputs<->trace binding, plan and protocol re-derivation",
                   **outcome)
            if not outcome.get("verified"):
                result["notes"].append("verify_bundle refused the scratch manifest; the constituent verifiers were profiled instead")
                def constituents():
                    outputs_raw = scratch_outputs.read_bytes()
                    trace_raw = scratch_trace.read_bytes()
                    tm_raw = scratch_trace_manifest.read_bytes()
                    split_ids = frozenset(scratch_doc["split"]["ids"])
                    rows = _verify_outputs(outputs_raw, split_ids, scratch_doc["split"]["carrier_lock_key"], scratch_doc["arm"])
                    records = _verify_raw_trace(trace_raw, tm_raw)
                    _verify_outputs_trace_binding(rows, records)
                    return len(rows), len(records)
                counts, wall, prof = timer.run(constituents)
                record("verify_constituents", wall, prof, outputs_rows=counts[0], trace_records=counts[1])

        # ---- seal_scoring_inputs ----
        if "seal_scoring_inputs" in stages_wanted:
            ledger_cells = json.loads((sealed / "score-ledger-cells.json").read_text(encoding="utf-8"))
            _, wall, prof = timer.run(lambda: seal_scoring_inputs(scratch_manifest, run_id=run_id, attempt_id=args.attempt_id, ledger_cells=ledger_cells))
            record("seal_scoring_inputs", wall, prof,
                   bytes=sum((scratch / n).stat().st_size for n in (f"{run_id}.generation-manifest.json", "score-ledger-cells.json", "score-jobs.jsonl") if (scratch / n).is_file()),
                   fsyncs=3, pattern="three _write_once files: open('xb') + write + flush + fsync each")

        # ---- the flight-receipt builder's trace pass ----
        if "trace_facts_scan" in stages_wanted:
            facts, wall, prof = timer.run(lambda: read_attempt_trace_facts(scratch_trace))
            record("trace_facts_scan", wall, prof, bytes=scratch_trace.stat().st_size,
                   model_request_count=(facts.get("model_request_count") if isinstance(facts, dict) else None),
                   pattern="read_attempt_trace_facts: for line in file -> json.loads(line) per record, counts only")

        # ---- flight receipts (the worker's last write) ----
        if "flight_receipts_write" in stages_wanted and (sealed / "flight-receipts.json").is_file():
            doc = json.loads((sealed / "flight-receipts.json").read_text(encoding="utf-8"))
            receipts = FlightReceipts(run_id=doc["run_id"], attempt_id=doc["attempt_id"], stages=dict(doc["stages"]))
            _, wall, prof = timer.run(lambda: write_flight_receipts(scratch_receipts, receipts))
            got = sha256_path(scratch_receipts)
            record("flight_receipts_write", wall, prof, bytes=scratch_receipts.stat().st_size, stages=len(doc["stages"]),
                   byte_identical=(got == expected["flight_receipts"]), sha256=got, fsyncs=1,
                   pattern="write_flight_receipts: flock + json.dumps(indent=2) + open('xb') + write + flush + fsync + os.replace")
            del doc, receipts

        result["mem_available_gib_end"] = free_memory_gib()
        result["peak_rss_gib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024), 3)
    finally:
        if args.keep_scratch:
            result["notes"].append(f"scratch kept at {scratch} (--keep-scratch)")
        else:
            shutil.rmtree(scratch, ignore_errors=True)
            result["scratch_deleted"] = not scratch.exists()

    print(f"[{args.target_label}/{args.mode}] hashing the sealed directory after", flush=True)
    after = hash_tree(sealed)
    result["sealed_after"] = {"count": after["count"], "bytes": after["bytes"], "combined_sha256": after["combined_sha256"]}
    result["sealed_untouched"] = (before["files"] == after["files"])
    if not result["sealed_untouched"]:
        raise ProfileError("the sealed directory listing changed during the profile -- investigate before trusting anything")

    seal_total = sum(result["stages"][s]["wall_s"] for s in SEAL_STAGES if s in result["stages"])
    result["seal_total_wall_s"] = round(seal_total, 4)
    result["seal_stages_present"] = [s for s in SEAL_STAGES if s in result["stages"]]
    return result


# --------------------------------------------------------------------------
# Rendering the note from the collected JSON artefacts
# --------------------------------------------------------------------------


def fmt(v, places=2):
    return "--" if v is None else f"{v:.{places}f}"


def md_table(header, rows, right_from=1):
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" if i < right_from else "---:" for i in range(len(header))) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def merge_passes(profiles: list[dict]) -> tuple[dict, dict]:
    """One merged pass per (target, mode) from the primary invocations (suffix '', 'inflight'
    or 'seal', which split one pass across two processes); 'repeat*' invocations are kept
    aside as variability repeats and never merged into the primary."""
    primary: dict = {}
    repeats: dict = {}
    for p in profiles:
        key = (p["target_label"], p["mode"])
        suffix = str(p.get("out_suffix") or "")
        if suffix.startswith("repeat"):
            repeats.setdefault(key, []).append(p)
            continue
        if key not in primary:
            primary[key] = json.loads(json.dumps(p))
            primary[key]["merged_from"] = [suffix or "(single)"]
            continue
        target = primary[key]
        overlap = set(target["stages"]) & set(p["stages"]) - set(INPUT_STAGES)
        if overlap:
            raise ProfileError(f"two primary passes for {key} both carry stages {sorted(overlap)}; mark one as a repeat")
        # An input stage (the sealed trace read) runs in every invocation; the first one counts.
        target["stages"].update({k: v for k, v in p["stages"].items() if k not in target["stages"]})
        target["merged_from"].append(suffix or "(single)")
        target["sealed_untouched"] = bool(target["sealed_untouched"] and p["sealed_untouched"])
        target["scratch_deleted"] = bool(target.get("scratch_deleted") and p.get("scratch_deleted"))
        for k in ("trace_records",):
            target.setdefault(k, p.get(k))
    for entry in primary.values():
        entry["seal_total_wall_s"] = round(sum(entry["stages"][s]["wall_s"] for s in SEAL_STAGES if s in entry["stages"]), 4)
    return primary, repeats


def render(profiles: list[dict], markdown: Path, artefact_hashes: dict) -> str:
    by, repeats = merge_passes(profiles)
    labels = sorted({p["target_label"] for p in profiles}, key=lambda x: (x != "mount", x))
    wall = {lab: by.get((lab, "wall")) for lab in labels}
    prof = {lab: by.get((lab, "cprofile")) for lab in labels}
    ref = next(iter(profiles))
    run_id = ref["run_id"]
    sizes = ref.get("sealed_sizes", {})
    trace_mib = sizes.get(f"{run_id}.trace.jsonl", 0) / 2**20
    L = []
    A = L.append
    A("# Profile of the seal path: what the drvfs mount owns, measured over ROLL-2's sealed bundle")
    A("")
    A(
        "During the ROLL-2 flight the run directory grew at about 1.5 MB/s into two large files while `/mnt/e` (drvfs over 9p) "
        "writes sequentially at about 164 MB/s and ext4 at about 1,590 MB/s, so the coordinator asked whether the seal is mount-bound "
        "before moving the run root to ext4. This note profiles one complete offline replay of the seal writer's stages over the sealed "
        f"bytes of `{run_id}` ({fmt(ref['sealed_before']['bytes'] / 2**20, 0)} MiB in the attempt directory; trace {fmt(trace_mib, 0)} MiB, "
        f"{ref.get('trace_records', 0):,} records; 1,080 rows x 5 samples), to a scratch directory on the mount and to one on ext4, "
        "with `cProfile`. Measurement only: nothing about the flight machinery is changed."
    )
    A("")
    A(
        "**Method.** `scripts/analysis/slurp_seal_path_profile.py` (recipe `" + RECIPE_ID + "`). `FlightRuntime.seal()` needs a live composed "
        "flight, so it is not invoked; every stage it performs on the run directory is re-run with the repository's own functions where "
        "they take a path (`write_json_artifact`, `sha256_file`, `verify_bundle`, `seal_scoring_inputs`, `read_attempt_trace_facts`, "
        "`write_flight_receipts`) and with the exact writer expressions of `seal()` for `outputs.jsonl` and `phases.json`. The in-flight "
        "trace growth (`TraceSink.emit`: open-append-close per record) is replayed separately, once per record and once per file. Every "
        "reproduced file is hashed against the sealed artifact's sha256. Official scoring is a scorer contact and is not part of the "
        "profile (the deferred-scoring seal ends at `seal_scoring_inputs`; the scorer runs later in the score worker). Zero model, "
        "server, encoder, tokenizer, scorer, GPU or network contacts; single-threaded; each target profiled on its own, wall pass then "
        "`cProfile` pass, one process at a time, beside the live flight on port 8080 (which was neither started, stopped nor probed). "
        "Timings vary between runs; hashes, sizes, counts and byte-identity flags are deterministic."
    )
    A("")
    # Sealed untouched
    A("## 0. The sealed bytes were untouched")
    A("")
    rows = []
    for p in profiles:
        rows.append([p["target_label"], p["mode"], str(p.get("out_suffix") or "") or "--", p["sealed_before"]["count"], f"{p['sealed_before']['bytes']:,}",
                     f"`{p['sealed_before']['combined_sha256'][:16]}...`", f"`{p['sealed_after']['combined_sha256'][:16]}...`",
                     "yes" if p["sealed_untouched"] else "**NO**", "yes" if p.get("scratch_deleted") else "kept"])
    A(md_table(["target", "pass", "invocation", "files", "bytes", "listing sha256 before", "after", "identical", "scratch deleted"], rows, right_from=3))
    A("")
    A(f"Scratch targets: " + "; ".join(f"`{p['scratch_dir']}` ({p.get('scratch_fs_type')})" for p in profiles if p["mode"] == "wall") +
      f". Sealed directory filesystem: {ref.get('sealed_fs_type')}.")
    A("")
    # Byte identity
    A("## 1. Every reproduced artifact is byte-identical to the sealed one")
    A("")
    rows = []
    for stage in ("trace_append_per_record", "trace_append_batched", "outputs_write", "phases_write", "trace_manifest_write", "flight_receipts_write", "manifest_hashing"):
        for lab in labels:
            w = wall[lab]
            if w and stage in w["stages"]:
                s = w["stages"][stage]
                rows.append([stage, lab, f"{s.get('bytes', 0):,}", "yes" if s.get("byte_identical") else "**NO**", f"`{str(s.get('sha256', ''))[:16]}`" if s.get("sha256") else "--"])
    A(md_table(["stage", "target", "bytes written", "sha256 equals sealed", "sha256"], rows, right_from=2))
    A("")
    A("`verify_bundle` on the path-rewritten generation manifest: " + "; ".join(
        f"{lab}: {'verified, ' + str(wall[lab]['stages']['verify_bundle'].get('outputs_rows')) + ' rows, attempt state ' + str(wall[lab]['stages']['verify_bundle'].get('attempt_state')) if wall[lab] and wall[lab]['stages'].get('verify_bundle', {}).get('verified') else 'refused'}"
        for lab in labels if wall[lab]) + ".")
    A("")
    # Wall table
    A("## 2. Wall time per stage, mount against ext4")
    A("")
    rows = []
    stage_order = list(INPUT_STAGES) + list(INFLIGHT_STAGES) + list(SEAL_STAGES)
    for stage in stage_order:
        vals = {lab: (wall[lab]["stages"].get(stage, {}).get("wall_s") if wall[lab] else None) for lab in labels}
        if all(v is None for v in vals.values()):
            continue
        m = vals.get("mount")
        e = vals.get("ext4")
        delta = (m - e) if (m is not None and e is not None) else None
        share = (100.0 * delta / m) if (delta is not None and m) else None
        size = next((wall[lab]["stages"][stage].get("bytes") for lab in labels if wall[lab] and stage in wall[lab]["stages"]), None)
        rows.append([
            stage, ("seal" if stage in SEAL_STAGES else "in-flight" if stage in INFLIGHT_STAGES else "input"),
            f"{(size or 0) / 2**20:.1f}" if size else "--",
            fmt(m, 3), fmt(e, 3), fmt(delta, 3), fmt(share, 1),
            fmt((size / m / 2**20) if (size and m) else None, 1), fmt((size / e / 2**20) if (size and e) else None, 1),
        ])
    tm = wall.get("mount", {}).get("seal_total_wall_s") if wall.get("mount") else None
    te = wall.get("ext4", {}).get("seal_total_wall_s") if wall.get("ext4") else None
    rows.append(["**seal total** (the nine seal stages)", "seal", "--", f"**{fmt(tm, 3)}**", f"**{fmt(te, 3)}**",
                 fmt((tm - te) if (tm is not None and te is not None) else None, 3),
                 fmt((100.0 * (tm - te) / tm) if (tm and te is not None) else None, 1), "--", "--"])
    A(md_table(["stage", "kind", "MiB", "mount s", "ext4 s", "mount - ext4 s", "mount share of stage %", "MiB/s mount", "MiB/s ext4"], rows, right_from=2))
    A("")
    ph_m = wall["mount"]["stages"].get("phases_write", {}) if wall.get("mount") else {}
    ph_e = wall["ext4"]["stages"].get("phases_write", {}) if wall.get("ext4") else {}
    A(
        f"`phases_write` splits into serialise + write: mount {fmt(ph_m.get('serialise_s'), 2)} s + {fmt(ph_m.get('write_s'), 2)} s, "
        f"ext4 {fmt(ph_e.get('serialise_s'), 2)} s + {fmt(ph_e.get('write_s'), 2)} s; the serialisation is `json.dumps(indent=2)`, which "
        "is the pure-Python encoder because `indent` disables the C encoder."
    )
    A("")
    if repeats:
        A("Variability: a second wall pass per target (a live flight shares the host and the mount, so single passes carry its noise):")
        A("")
        rows = []
        for stage in stage_order:
            row = [stage]
            present = False
            for lab in labels:
                first = wall[lab]["stages"].get(stage, {}).get("wall_s") if wall[lab] else None
                reps = [r["stages"][stage]["wall_s"] for r in repeats.get((lab, "wall"), []) if stage in r["stages"]]
                row += [fmt(first, 3), ", ".join(fmt(v, 3) for v in reps) if reps else "--"]
                present = present or first is not None or bool(reps)
            if present:
                rows.append(row)
        header = ["stage"]
        for lab in labels:
            header += [f"{lab} pass 1 s", f"{lab} repeat s"]
        A(md_table(header, rows))
        A("")
    # In-flight append
    A("## 3. The in-flight trace append: per-record open/close against one open")
    A("")
    rows = []
    for stage in INFLIGHT_STAGES:
        for lab in labels:
            s = wall[lab]["stages"].get(stage) if wall[lab] else None
            if s:
                rows.append([stage, lab, f"{s.get('records', 0):,}", fmt(s["wall_s"], 2), fmt(s.get("per_record_ms"), 3), fmt(s.get("mib_per_s"), 1), "yes" if s.get("byte_identical") else "**NO**"])
    A(md_table(["pattern", "target", "records", "wall s", "ms per record", "MiB/s", "bytes identical"], rows, right_from=2))
    A("")
    pr_m = wall["mount"]["stages"].get("trace_append_per_record", {}) if wall.get("mount") else {}
    pb_m = wall["mount"]["stages"].get("trace_append_batched", {}) if wall.get("mount") else {}
    pr_e = wall["ext4"]["stages"].get("trace_append_per_record", {}) if wall.get("ext4") else {}
    pb_e = wall["ext4"]["stages"].get("trace_append_batched", {}) if wall.get("ext4") else {}
    A(
        "`TraceSink.emit` has no `fsync`; its per-record cost is the open/append/close round trip. On the mount the per-record pattern costs "
        f"{fmt(pr_m.get('per_record_ms'), 2)} ms per record against {fmt(pb_m.get('per_record_ms'), 3)} ms batched "
        f"({fmt((pr_m.get('wall_s') or 0) - (pb_m.get('wall_s') or 0), 1)} s of open/close overhead over the whole trace); on ext4 "
        f"{fmt(pr_e.get('per_record_ms'), 3)} ms against {fmt(pb_e.get('per_record_ms'), 3)} ms. Both patterns write the identical bytes. "
        "This is in-flight cost spread over the hours of the flight, not seal cost: at the flight's contact rate it is a fixed few "
        "milliseconds per record on the mount."
    )
    A("")
    # cProfile split
    A("## 4. Where the time goes inside each stage (`cProfile`, tottime by category)")
    A("")
    A("Categories: `io.read` / `io.write` are the C-level read and write calls; `io.open/close/stat` the open, close, stat, replace and "
      "lock calls (the 9p round trips); `fsync` is `os.fsync`; `json.encode` / `json.decode` are the `json` package's encoder and decoder "
      "frames (the pure-Python indent encoder lands here too); `hash` is `hashlib`; `boundary/validate` is `contracts.boundary` "
      "(`TraceRecord.validate` and the information-boundary walk); `bundle.python` is the repository's own bundle / flight / driver "
      "frames; `other` is interpreter overhead, `str.split`, decoding and the like. `for line in file` iteration is not a recorded call, "
      "so in `trace_facts_scan` the raw read hides in `other`. Shares are of the profiled pass's own tottime; the profiled pass is slower "
      "than the wall pass wherever Python frames dominate.")
    A("")
    for lab in labels:
        p = prof.get(lab)
        if not p:
            continue
        A(f"**{lab}** (profiled pass; wall of the profiled pass in the first column):")
        A("")
        rows = []
        for stage in stage_order:
            s = p["stages"].get(stage)
            if not s:
                continue
            cp = s.get("cprofile")
            if isinstance(cp, dict) and "by_category_share" not in cp:
                # phases_write carries two sub-profiles
                merged = {c: 0.0 for c in CATEGORIES}
                for sub in cp.values():
                    for c, v in sub["by_category_s"].items():
                        merged[c] += v
                total = sum(merged.values())
                shares = {c: (100.0 * v / total if total else 0.0) for c, v in merged.items()}
                tt = total
            elif isinstance(cp, dict):
                shares = cp["by_category_share"]
                tt = cp["tottime_total_s"]
            else:
                continue
            rows.append([stage, fmt(s["wall_s"], 2), fmt(tt, 2)] + [fmt(shares.get(c), 1) for c in CATEGORIES])
        A(md_table(["stage", "wall s", "tottime s"] + list(CATEGORIES), rows))
        A("")
    # Top functions of verify on the mount
    for lab in labels:
        p = prof.get(lab)
        if p and "verify_bundle" in p["stages"] and isinstance(p["stages"]["verify_bundle"].get("cprofile"), dict):
            top = p["stages"]["verify_bundle"]["cprofile"]["top_functions"][:12]
            A(f"Top functions of `verify_bundle` by tottime on {lab}:")
            A("")
            A(md_table(["function", "category", "tottime s", "cumtime s", "calls"], [[f"`{t['function']}`", t["category"], fmt(t["tottime_s"], 3), fmt(t["cumtime_s"], 3), f"{t['calls']:,}"] for t in top], right_from=2))
            A("")
    # fsync finding
    A("## 5. The fsync finding")
    A("")
    fs_stages = [(s, wall["mount"]["stages"][s]) for s in ("seal_scoring_inputs", "flight_receipts_write") if wall.get("mount") and s in wall["mount"]["stages"]]
    A(
        "There is no per-record `fsync` anywhere on the seal path or on the in-flight trace path. `os.fsync` is called exactly "
        + (", ".join(f"{s['fsyncs']} time(s) in `{name}`" for name, s in fs_stages) if fs_stages else "in seal_scoring_inputs (3) and write_flight_receipts (1)")
        + " -- four whole-file syncs per seal, each on a small file (the three scoring-input files) or one atomic 27 MB replace (the flight "
        "receipts). Their combined wall on the mount is "
        + fmt(sum(s["wall_s"] for _, s in fs_stages), 2) + " s"
        + (f" against {fmt(sum(wall['ext4']['stages'][n]['wall_s'] for n, _ in fs_stages if n in wall['ext4']['stages']), 2)} s on ext4" if wall.get("ext4") else "")
        + ". Batching them is therefore moot: there is nothing per-record to batch, and the per-record cost that does exist (the trace "
        "append's open/close) is bytes-neutral to batch, as section 3 shows, but lives in the flight, not in the seal."
    )
    A("")
    # Verdict
    A("## 6. What share of the seal the mount owns")
    A("")
    if tm is not None and te is not None:
        mount_owned = tm - te
        share = 100.0 * mount_owned / tm if tm else 0.0
        biggest = sorted(
            ((s, wall["mount"]["stages"][s]["wall_s"] - wall["ext4"]["stages"][s]["wall_s"]) for s in SEAL_STAGES if s in wall["mount"]["stages"] and s in wall["ext4"]["stages"]),
            key=lambda kv: -kv[1],
        )[:3]
        cpu_stage = max(((s, wall["ext4"]["stages"][s]["wall_s"]) for s in SEAL_STAGES if s in wall["ext4"]["stages"]), key=lambda kv: kv[1])
        # Bytes the SEAL writes: outputs, phases, trace manifest, manifest, receipts. The trace itself is written in flight.
        seal_bytes = sum(v for k, v in sizes.items() if k != f"{run_id}.trace.jsonl")
        facts_delta = (wall["mount"]["stages"].get("trace_facts_scan", {}).get("wall_s") or 0) - (wall["ext4"]["stages"].get("trace_facts_scan", {}).get("wall_s") or 0)
        rest_delta = mount_owned - facts_delta
        A(
            f"Over the nine seal stages the replay takes **{fmt(tm, 1)} s on the mount and {fmt(te, 1)} s on ext4**, so the mount owns "
            f"**{fmt(mount_owned, 1)} s = {fmt(share, 0)} % of the seal wall** and the remaining {fmt(100 - share, 0)} % is CPU that moves with "
            f"the run root nowhere (the repeat passes read {fmt(next((r['seal_total_wall_s'] for r in repeats.get(('mount', 'wall'), [])), None), 1)} s and "
            f"{fmt(next((r['seal_total_wall_s'] for r in repeats.get(('ext4', 'wall'), [])), None), 1)} s). The three stages where the mount costs most are "
            + ", ".join(f"`{s}` (+{fmt(d, 1)} s)" for s, d in biggest)
            + f"; the largest stage on ext4 -- pure CPU -- is `{cpu_stage[0]}` at {fmt(cpu_stage[1], 1)} s. But the mount's share is not "
            f"bandwidth: `trace_facts_scan` alone is +{fmt(facts_delta, 1)} s of the {fmt(mount_owned, 1)} s, and its profile puts "
            f"{fmt(prof['mount']['stages']['trace_facts_scan']['cprofile']['by_category_share'].get('bundle.python') if prof.get('mount') and 'trace_facts_scan' in prof['mount']['stages'] else None, 0)} % of "
            "that time inside `read_attempt_trace_facts`'s own frame -- the `for line in handle` iteration, which pulls the "
            f"{fmt(trace_mib, 0)} MiB trace through `TextIOWrapper`'s 8 KiB buffer, about 92,000 small reads over 9p. "
            "`verify_bundle` reads the same file with `read_bytes` (a few large reads) and pays about 4 s for it. Everything else the mount "
            f"owns is {fmt(rest_delta, 1)} s: whole-file hashing and the large writes at 40-200 MiB/s, i.e. the ~164 MB/s the mount is rated at. "
            f"The seal writes about {fmt(seal_bytes / 2**20, 0)} MiB (outputs, phases, trace manifest, manifest, receipts) and reads the "
            f"{fmt(trace_mib, 0)} MiB trace three times (hash, verify, trace facts). The 1.5 MB/s growth seen during the flight is consistent "
            f"with the trace's per-record open/append/close pattern, which replays at {fmt(pr_m.get('mib_per_s'), 1)} MiB/s on the mount while the "
            f"same bytes stream at {fmt(pb_m.get('mib_per_s'), 0)} MiB/s in one open; it is a round-trip cost, not a bandwidth ceiling. "
            f"Decision numbers: moving the run root to ext4 saves about {fmt(mount_owned, 0)} s per seal of this size (of which "
            f"{fmt(facts_delta, 0)} s is one function's small-read pattern that a `read_bytes`-then-split in `read_attempt_trace_facts` would "
            f"recover without moving anything) and about {fmt(((pr_m.get('wall_s') or 0) - (pr_e.get('wall_s') or 0)) / 60.0, 1)} minutes of trace "
            f"append spread over the flight; it leaves the {fmt(te, 0)} s of CPU untouched -- `verify_bundle`'s parse, boundary walk and canonical "
            "re-serialisation of every trace record, and the pure-Python indent encoder on the 160 MB `phases.json` and 27 MB receipts. "
            "Neither code change is made here."
        )
    else:
        A("Both targets' wall passes are required for the verdict; one is missing from the rendered set.")
    A("")
    A("## 7. Artefacts")
    A("")
    A(f"Under `SPEECHRL_DATA_DIR/analysis/{OUT_DIRNAME}/`:")
    A("")
    A(md_table(["file", "sha256"], [[f"`{k}`", f"`{v}`"] for k, v in sorted(artefact_hashes.items())], right_from=2))
    A("")
    A(f"Rendered {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `{RECIPE_ID}`; timings are measurements of their pass, everything else is deterministic.")
    A("")
    text = "\n".join(L)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(text, encoding="utf-8", newline="\n")
    return text


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    parser.add_argument("--target-label", choices=("mount", "ext4", "other"), default=None)
    parser.add_argument("--scratch-dir", type=Path, default=None, help="created by this run and deleted at its end; must not exist")
    parser.add_argument("--mode", choices=("wall", "cprofile"), default="wall")
    parser.add_argument("--stages", default="", help="comma-separated subset of stages (default: all)")
    parser.add_argument("--keep-scratch", action="store_true")
    parser.add_argument("--out-suffix", default="", help="suffix for the profile JSON name: 'inflight' / 'seal' split one pass across two invocations, 'repeat' marks a variability repeat")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--render", nargs="*", type=Path, default=None, help="render the note from these profile JSON files")
    parser.add_argument("--markdown", type=Path, default=REPO / DEFAULT_MARKDOWN)
    args = parser.parse_args()
    if not str(args.data_root):
        raise SystemExit("SPEECHRL_DATA_DIR is not set and --data-root was not given")
    out_dir = args.out_dir or (args.data_root.resolve() / "analysis" / OUT_DIRNAME)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.render is not None:
        profiles = [json.loads(p.read_text(encoding="utf-8")) for p in args.render]
        hashes = {p.name: sha256_path(p) for p in args.render}
        render(profiles, args.markdown, hashes)
        print(f"[render] {args.markdown}")
        return 0

    if args.target_label is None or args.scratch_dir is None:
        raise SystemExit("--target-label and --scratch-dir are required for a profile run")
    result = run_profile(args)
    result["out_suffix"] = args.out_suffix
    suffix = f"-{args.out_suffix}" if args.out_suffix else ""
    path = out_dir / f"profile-{args.target_label}-{args.mode}{suffix}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"[done] {path} seal_total {result['seal_total_wall_s']} s sealed_untouched {result['sealed_untouched']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProfileError as error:
        print(f"refused: {error}", file=sys.stderr)
        raise SystemExit(2)
