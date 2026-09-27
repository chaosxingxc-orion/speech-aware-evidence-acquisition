#!/usr/bin/env python3
"""Acceptance of the two trace-path throughput fixes by byte identity over one sealed bundle.

WHAT IS ACCEPTED (owner decision 140; docs/results/2026-09-26-slurp-seal-path-profile.md):

1. ``core.tracing.TraceSink.emit`` keeps one append handle open and flushes per record instead
   of opening, appending and closing the trace file per record (7.06 ms per record on the
   drvfs/9p run root, 355.6 s over ROLL-2's 50,380 records).
2. ``core.driver.speech_native.read_attempt_trace_facts`` reads the trace through a few large
   raw reads instead of ``TextIOWrapper``'s 8 KiB chunks (14.6 s of the 37.9 s seal).

HOW. Exactly the way the profile proved its replay: every stage is re-run against a scratch
directory this script creates and deletes, never against the sealed directory, whose listing is
hashed before and after and must be identical.

* **Sink replay through the real classes.** The sealed trace's records are replayed, in order,
  through the OLD ``TraceSink`` (imported from a ``git archive`` of ``--old-commit`` extracted
  under ``--old-tree-dir``) and through the NEW one (this tree), each in its own subprocess
  with its own ``sys.path`` and an assertion on the imported module's file; both scratch traces
  and both trace manifests are hashed against the sealed artifacts.
* **Pure write patterns**, the profile's own units: per-record open/append/close (old) against
  one open with ``flush()`` per record (new), the same lines in the same order, hashed against
  the sealed trace.
* **Facts through the real functions.** OLD and NEW ``read_attempt_trace_facts`` over the
  scratch trace, each in its own subprocess (wall, peak RSS, and the facts object, which must
  be equal).
* **The nine seal stages** of the profile with this tree's code (``write_json_artifact``,
  ``sha256_file``, ``verify_bundle``, ``seal_scoring_inputs``, ``read_attempt_trace_facts``,
  ``write_flight_receipts`` and the exact ``outputs.jsonl`` / ``phases.json`` writer
  expressions of ``FlightRuntime.seal``), every reproduced file hashed against the sealed one.

ZERO CONTACTS: no model, server, encoder, tokenizer, scorer, GPU or network. Single-threaded;
one target at a time. Nothing is printed or persisted from the sealed content except sizes,
counts, timings, hashes and the label-free facts object.

Run (WSL, speechrl venv, from the tree under test)::

    P=scripts/analysis/trace_path_throughput_acceptance.py
    python -B $P run --target-label mount --old-commit <pre-fix commit> \
        --old-tree-dir /home/chao/saea-worktrees/.tracefix-scratch/old-tree \
        --scratch-dir $SPEECHRL_DATA_DIR/analysis/SAEA-TRACE-PATH-FIX-V1/scratch-mount \
        --out $SPEECHRL_DATA_DIR/analysis/SAEA-TRACE-PATH-FIX-V1/acceptance-mount.json
    python -B $P run --target-label ext4 ... --scratch-dir /home/chao/saea-worktrees/.tracefix-scratch/ext4
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import io
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

RECIPE_ID = "trace-path-throughput-acceptance-v1"
SCHEMA = "saea-trace-path-throughput-acceptance-v1"
DEFAULT_RUN_ID = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1"
DEFAULT_ATTEMPT_ID = "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation"
PACKAGE = "speech_aware_evidence_acquisition"
BLOCK = 64 * 1024 * 1024
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


class AcceptanceError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# shared helpers (no repository imports; the workers pick their own tree)
# --------------------------------------------------------------------------


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_tree(root: Path) -> dict:
    files = {}
    for path in sorted(p for p in Path(root).rglob("*") if p.is_file()):
        files[str(path.relative_to(root))] = {"bytes": path.stat().st_size, "sha256": sha256_path(path)}
    combined = hashlib.sha256(json.dumps(files, sort_keys=True).encode("utf-8")).hexdigest()
    return {"files": files, "count": len(files), "bytes": sum(f["bytes"] for f in files.values()), "combined_sha256": combined}


def fs_type(path: Path) -> str:
    try:
        out = subprocess.run(["stat", "-f", "-c", "%T", str(path)], capture_output=True, text=True, check=False)
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def peak_rss_gib() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024), 3)


def iter_lines_bytes(path: Path, block: int = BLOCK):
    """Local chunked line reader (bytes, no terminator); tree-independent."""

    carry = b""
    with Path(path).open("rb", buffering=0) as handle:
        while True:
            data = handle.read(block)
            if not data:
                break
            if carry:
                data = carry + data
            pieces = data.split(b"\n")
            carry = pieces.pop()
            yield from pieces
    if carry:
        yield carry


def assert_tree(module, src: Path) -> str:
    file = Path(module.__file__).resolve()
    if not str(file).startswith(str(Path(src).resolve())):
        raise AcceptanceError(f"{module.__name__} imported from {file}, not from {src}")
    return str(file)


def canonical_sha256(document) -> str:
    return hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# workers (one tree per process)
# --------------------------------------------------------------------------


def worker_sink_replay(args) -> int:
    sys.path.insert(0, str(args.src))
    import importlib

    tracing = importlib.import_module(f"{PACKAGE}.core.tracing")
    module_file = assert_tree(tracing, args.src)
    run_dir = Path(args.run_dir)
    if run_dir.exists():
        raise AcceptanceError(f"run dir must not exist: {run_dir}")
    sink = tracing.TraceSink(run_dir, args.run_id)
    records = 0
    started = time.perf_counter()
    for raw in iter_lines_bytes(Path(args.sealed_trace)):
        record = json.loads(raw)
        sink.emit(record["channel"], record["record_id"], record["payload"])
        records += 1
    wall_emit = time.perf_counter() - started
    started = time.perf_counter()
    manifest_hash = sink.close()
    wall_close = time.perf_counter() - started
    trace_path = run_dir / f"{args.run_id}.trace.jsonl"
    manifest_path = run_dir / f"{args.run_id}.trace-manifest.json"
    report = {
        "tree": args.label,
        "module_file": module_file,
        "records": records,
        "wall_emit_s": round(wall_emit, 4),
        "per_record_ms": round(1000.0 * wall_emit / max(1, records), 4),
        "wall_close_s": round(wall_close, 4),
        "trace_bytes": trace_path.stat().st_size,
        "trace_sha256": sha256_path(trace_path),
        "trace_manifest_sha256": sha256_path(manifest_path),
        "trace_manifest_hash_returned": manifest_hash,
        "peak_rss_gib": peak_rss_gib(),
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def worker_facts(args) -> int:
    sys.path.insert(0, str(args.src))
    import importlib

    speech_native = importlib.import_module(f"{PACKAGE}.core.driver.speech_native")
    module_file = assert_tree(speech_native, args.src)
    import tracemalloc

    rss_before = peak_rss_gib()
    started = time.perf_counter()
    facts = speech_native.read_attempt_trace_facts(Path(args.trace))
    wall = time.perf_counter() - started
    # A second, traced call for the reader's own allocation peak (tracemalloc
    # slows allocation-heavy code, so it never sits inside the timed call).
    tracemalloc.start()
    traced_facts = speech_native.read_attempt_trace_facts(Path(args.trace))
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if traced_facts != facts:
        raise AcceptanceError("two reads of the same trace returned different facts")
    report = {
        "tree": args.label,
        "module_file": module_file,
        "wall_s": round(wall, 4),
        "trace_bytes": Path(args.trace).stat().st_size,
        "mib_per_s": round(Path(args.trace).stat().st_size / wall / 2**20, 1),
        "facts": facts,
        "facts_sha256": canonical_sha256(facts),
        "peak_rss_gib_before_read": rss_before,
        "peak_rss_gib": peak_rss_gib(),
        "read_traced_peak_mib": round(traced_peak / 2**20, 1),
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


def run_worker(kind: str, src: Path, label: str, report: Path, **kw) -> dict:
    cmd = [sys.executable, "-B", str(Path(__file__).resolve()), kind, "--src", str(src), "--label", label, "--report", str(report)]
    for key, value in kw.items():
        cmd += [f"--{key.replace('_', '-')}", str(value)]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(src)
    completed = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if completed.returncode != 0:
        raise AcceptanceError(f"worker {kind}/{label} failed:\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    return json.loads(report.read_text(encoding="utf-8"))


def extract_old_tree(old_commit: str, target: Path) -> Path:
    if target.exists():
        raise AcceptanceError(f"old tree dir already exists, refusing to reuse it: {target}")
    target.mkdir(parents=True, exist_ok=False)
    archive = subprocess.run(["git", "-C", str(REPO), "archive", old_commit, "src"], capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as tar:
        tar.extractall(target)
    return target / "src"


# --------------------------------------------------------------------------
# the orchestrated run
# --------------------------------------------------------------------------


def run(args) -> dict:
    from speech_aware_evidence_acquisition.core.bundle import BundleError
    from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
    from speech_aware_evidence_acquisition.core.driver import speech_native
    from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts, write_flight_receipts
    from speech_aware_evidence_acquisition.core.flight.scoring import seal_scoring_inputs
    from speech_aware_evidence_acquisition.e0.artifacts import sha256_file, write_json_artifact
    from speech_aware_evidence_acquisition.core import tracing

    new_src = SRC
    assert_tree(tracing, new_src)
    assert_tree(speech_native, new_src)

    data_root = Path(args.data_root).resolve()
    runs_root = (data_root / "runs").resolve()
    sealed = (runs_root / args.run_id / args.attempt_id).resolve()
    if not sealed.is_dir():
        raise AcceptanceError(f"sealed attempt directory missing: {sealed}")
    scratch = Path(args.scratch_dir).resolve()
    if scratch.exists():
        raise AcceptanceError(f"scratch directory already exists, refusing to reuse it: {scratch}")
    for name, path in (("scratch", scratch), ("old tree", Path(args.old_tree_dir).resolve())):
        if runs_root == path or runs_root in path.parents:
            raise AcceptanceError(f"the {name} directory must not live under the governed runs directory")
        if REPO == path or REPO in path.parents:
            raise AcceptanceError(f"the {name} directory must not live inside the repository")
    run_id = args.run_id

    result: dict = {
        "schema": SCHEMA,
        "recipe_id": RECIPE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "attempt_id": args.attempt_id,
        "sealed_dir": str(sealed),
        "target_label": args.target_label,
        "scratch_dir": str(scratch),
        "old_commit": args.old_commit,
        "new_tree": str(REPO),
        "new_head": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "python": platform.python_version(),
        "kernel": platform.release(),
        "single_threaded": True,
        "stages": {},
        "notes": [],
    }

    def log(message: str) -> None:
        print(f"[{args.target_label}] {message}", flush=True)

    log("hashing the sealed directory before")
    before = hash_tree(sealed)
    result["sealed_before"] = {k: before[k] for k in ("count", "bytes", "combined_sha256")}
    sealed_hash_of = {k: v["sha256"] for k, v in before["files"].items()}
    manifest = json.loads((sealed / f"{run_id}.run-manifest.json").read_text(encoding="utf-8"))
    generation = json.loads((sealed / f"{run_id}.generation-manifest.json").read_text(encoding="utf-8"))
    expected = {
        "outputs": manifest["outputs"]["sha256"],
        "raw_trace": manifest["raw_trace"]["sha256"],
        "trace_manifest": manifest["trace_manifest"]["sha256"],
        "phases": sealed_hash_of.get(f"{run_id}.phases.json"),
        "flight_receipts": sealed_hash_of.get("flight-receipts.json"),
    }
    result["expected_sha256"] = expected
    sealed_trace = sealed / f"{run_id}.trace.jsonl"

    scratch.mkdir(parents=True, exist_ok=False)
    result["scratch_fs_type"] = fs_type(scratch)
    result["sealed_fs_type"] = fs_type(sealed)
    old_tree_root = Path(args.old_tree_dir).resolve()
    old_src = None

    def record(name: str, **entry) -> None:
        result["stages"][name] = entry
        wall = entry.get("wall_s", entry.get("wall_emit_s"))
        log(f"{name}: {wall} s identical={entry.get('byte_identical', entry.get('facts_identical', '-'))}")

    only = set(args.only.split(",")) if args.only else {"patterns", "classes", "readers"}
    unknown = only - {"patterns", "classes", "readers"}
    if unknown:
        raise AcceptanceError(f"unknown --only group(s) {sorted(unknown)}")
    result["only"] = sorted(only)

    try:
        old_src = extract_old_tree(args.old_commit, old_tree_root)
        result["old_src"] = str(old_src)

        # ---- the sealed trace, read once ----
        started = time.perf_counter()
        lines = list(iter_lines_bytes(sealed_trace))
        wall = time.perf_counter() - started
        record("sealed_trace_read", wall_s=round(wall, 4), bytes=sealed_trace.stat().st_size, records=len(lines))
        result["trace_records"] = len(lines)

        # ---- pure write patterns: old (open/append/close per record) vs new (one open, flush per record) ----
        patterns = (
            ("trace_append_per_record", "old: open('a') + write(line) + close per record; no fsync"),
            ("trace_append_open_once_flush", "new: one open('a'), write(line) + flush() per record; no fsync"),
        )
        scratch_trace = scratch / f"{run_id}.trace.jsonl"
        if "classes" not in only and "readers" in only:
            # No class replay in this pass: the readers still need the trace on the target.
            with scratch_trace.open("w", encoding="utf-8", newline="\n") as handle:
                for raw in lines:
                    handle.write(raw.decode("utf-8") + "\n")
            got = sha256_path(scratch_trace)
            if got != expected["raw_trace"]:
                raise AcceptanceError("the plain copy of the sealed trace does not hash to the sealed trace")
        for name, description in (patterns if "patterns" in only else ()):
            target = scratch / f"{run_id}.{name}.jsonl"
            started = time.perf_counter()
            if name == "trace_append_per_record":
                for raw in lines:
                    with target.open("a", encoding="utf-8", newline="\n") as handle:
                        handle.write(raw.decode("utf-8") + "\n")
            else:
                handle = target.open("a", encoding="utf-8", newline="\n")
                for raw in lines:
                    handle.write(raw.decode("utf-8") + "\n")
                    handle.flush()
                handle.close()
            wall = time.perf_counter() - started
            got = sha256_path(target)
            record(
                name, wall_s=round(wall, 4), records=len(lines), bytes=target.stat().st_size,
                per_record_ms=round(1000.0 * wall / max(1, len(lines)), 4),
                mib_per_s=round(target.stat().st_size / wall / 2**20, 1),
                byte_identical=(got == expected["raw_trace"]), sha256=got, pattern=description,
            )
            target.unlink()
        del lines
        gc.collect()

        # ---- the real classes: old TraceSink vs new TraceSink ----
        for label, src in ((("old", old_src), ("new", new_src)) if "classes" in only else ()):
            run_dir = scratch / f"class-{label}"
            report = run_worker(
                "sink-replay", src, label, scratch / f"sink-{label}.json",
                sealed_trace=sealed_trace, run_dir=run_dir, run_id=run_id,
            )
            report["byte_identical"] = (
                report["trace_sha256"] == expected["raw_trace"]
                and report["trace_manifest_sha256"] == expected["trace_manifest"]
            )
            report["trace_identical"] = report["trace_sha256"] == expected["raw_trace"]
            report["trace_manifest_identical"] = report["trace_manifest_sha256"] == expected["trace_manifest"]
            record(f"sink_class_{label}", **report)
            (scratch / f"sink-{label}.json").unlink()
            if label == "old":
                shutil.rmtree(run_dir)
        if "classes" in only:
            # the NEW sink's trace is the scratch trace for everything downstream
            os.replace(scratch / "class-new" / f"{run_id}.trace.jsonl", scratch_trace)
            shutil.rmtree(scratch / "class-new")
        if "readers" not in only:
            result["orchestrator_peak_rss_gib"] = peak_rss_gib()
            raise _Done()

        # ---- the real readers: old vs new read_attempt_trace_facts ----
        facts = {}
        for label, src in (("old", old_src), ("new", new_src)):
            report = run_worker("facts", src, label, scratch / f"facts-{label}.json", trace=scratch_trace)
            facts[label] = report.pop("facts")
            record(f"facts_{label}", **report)
            (scratch / f"facts-{label}.json").unlink()
        identical = facts["old"] == facts["new"]
        result["facts_identical"] = identical
        result["facts_sha256"] = {k: canonical_sha256(v) for k, v in facts.items()}
        result["facts_new"] = facts["new"]
        log(f"facts identical old==new: {identical}")

        # ---- the nine seal stages with this tree's code ----
        scratch_outputs = scratch / f"{run_id}.outputs.jsonl"
        scratch_trace_manifest = scratch / f"{run_id}.trace-manifest.json"
        scratch_phases = scratch / f"{run_id}.phases.json"
        scratch_manifest = scratch / f"{run_id}.run-manifest.json"
        scratch_receipts = scratch / "flight-receipts.json"

        rows = []
        with (sealed / f"{run_id}.outputs.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
        started = time.perf_counter()
        with scratch_outputs.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        wall = time.perf_counter() - started
        got = sha256_path(scratch_outputs)
        record("outputs_write", wall_s=round(wall, 4), bytes=scratch_outputs.stat().st_size, rows=len(rows),
               byte_identical=(got == expected["outputs"]), sha256=got)
        del rows

        phases_doc = json.loads((sealed / f"{run_id}.phases.json").read_text(encoding="utf-8"))
        started = time.perf_counter()
        text = json.dumps(phases_doc, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n"
        scratch_phases.write_text(text, encoding="utf-8", newline="\n")
        wall = time.perf_counter() - started
        got = sha256_path(scratch_phases)
        record("phases_write", wall_s=round(wall, 4), bytes=scratch_phases.stat().st_size,
               byte_identical=(got == expected["phases"]), sha256=got)
        del phases_doc, text
        gc.collect()

        tm_doc = json.loads((sealed / f"{run_id}.trace-manifest.json").read_text(encoding="utf-8"))
        started = time.perf_counter()
        write_json_artifact(scratch_trace_manifest, tm_doc)
        wall = time.perf_counter() - started
        got = sha256_path(scratch_trace_manifest)
        record("trace_manifest_write", wall_s=round(wall, 4), bytes=scratch_trace_manifest.stat().st_size,
               byte_identical=(got == expected["trace_manifest"]), sha256=got)
        del tm_doc

        session_receipt_path = Path(str((generation.get("session_receipt") or {}).get("path") or ""))
        targets = [scratch_outputs, scratch_trace, scratch_trace_manifest]
        if session_receipt_path.is_file():
            targets.append(session_receipt_path)
        started = time.perf_counter()
        hashes = {p.name: sha256_file(p) for p in targets}
        wall = time.perf_counter() - started
        total = sum(p.stat().st_size for p in targets)
        record("manifest_hashing", wall_s=round(wall, 4), bytes=total, files=len(targets),
               mib_per_s=round(total / wall / 2**20, 1),
               byte_identical=(hashes.get(scratch_trace.name) == expected["raw_trace"] and hashes.get(scratch_outputs.name) == expected["outputs"]))

        scratch_doc = json.loads(json.dumps(generation))
        for key, path in (("outputs", scratch_outputs), ("raw_trace", scratch_trace), ("trace_manifest", scratch_trace_manifest)):
            if isinstance(scratch_doc.get(key), dict):
                scratch_doc[key]["path"] = str(path.resolve())
        started = time.perf_counter()
        write_json_artifact(scratch_manifest, scratch_doc)
        wall = time.perf_counter() - started
        record("run_manifest_write", wall_s=round(wall, 4), bytes=scratch_manifest.stat().st_size)

        outcome: dict = {}
        started = time.perf_counter()
        try:
            bundle = verify_bundle(scratch_manifest)
            outcome = {"verified": True, "outputs_rows": len(bundle.outputs_rows), "attempt_state": bundle.attempt_state}
        except BundleError as error:
            outcome = {"verified": False, "error": str(error)[:300]}
        wall = time.perf_counter() - started
        record("verify_bundle", wall_s=round(wall, 4), **outcome)

        ledger_cells = json.loads((sealed / "score-ledger-cells.json").read_text(encoding="utf-8"))
        started = time.perf_counter()
        seal_scoring_inputs(scratch_manifest, run_id=run_id, attempt_id=args.attempt_id, ledger_cells=ledger_cells)
        wall = time.perf_counter() - started
        record("seal_scoring_inputs", wall_s=round(wall, 4), fsyncs=3)

        started = time.perf_counter()
        facts_inproc = speech_native.read_attempt_trace_facts(scratch_trace)
        wall = time.perf_counter() - started
        record("trace_facts_scan", wall_s=round(wall, 4), bytes=scratch_trace.stat().st_size,
               mib_per_s=round(scratch_trace.stat().st_size / wall / 2**20, 1),
               facts_identical=(facts_inproc == facts["old"]), reader="new (this tree, in-process)")

        if (sealed / "flight-receipts.json").is_file():
            doc = json.loads((sealed / "flight-receipts.json").read_text(encoding="utf-8"))
            receipts = FlightReceipts(run_id=doc["run_id"], attempt_id=doc["attempt_id"], stages=dict(doc["stages"]))
            started = time.perf_counter()
            write_flight_receipts(scratch_receipts, receipts)
            wall = time.perf_counter() - started
            got = sha256_path(scratch_receipts)
            record("flight_receipts_write", wall_s=round(wall, 4), bytes=scratch_receipts.stat().st_size,
                   byte_identical=(got == expected["flight_receipts"]), sha256=got, fsyncs=1)
            del doc, receipts
        result["orchestrator_peak_rss_gib"] = peak_rss_gib()
    except _Done:
        pass
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        result["scratch_deleted"] = not scratch.exists()
        shutil.rmtree(old_tree_root, ignore_errors=True)
        result["old_tree_deleted"] = not old_tree_root.exists()

    log("hashing the sealed directory after")
    after = hash_tree(sealed)
    result["sealed_after"] = {k: after[k] for k in ("count", "bytes", "combined_sha256")}
    result["sealed_untouched"] = before["files"] == after["files"]
    if not result["sealed_untouched"]:
        raise AcceptanceError("the sealed directory listing changed during the acceptance -- investigate before trusting anything")
    result["seal_total_wall_s"] = round(sum(result["stages"][s]["wall_s"] for s in SEAL_STAGES if s in result["stages"]), 4)
    identity_flags = [
        entry.get("byte_identical") for name, entry in result["stages"].items() if "byte_identical" in entry
    ]
    if "readers" in only:
        identity_flags += [
            result["facts_identical"],
            result["stages"]["trace_facts_scan"]["facts_identical"],
            result["stages"]["verify_bundle"].get("verified"),
        ]
    result["all_identical"] = bool(identity_flags) and all(identity_flags)
    return result


class _Done(Exception):
    """Internal: this pass ends before the reader stages (``--only``)."""


def summary(result: dict) -> str:
    s = result["stages"]
    out = [
        f"target {result['target_label']} ({result['scratch_fs_type']}), sealed {result['sealed_fs_type']}, new HEAD {result['new_head'][:8]}, old {result['old_commit'][:8]}, groups {result['only']}",
        f"sealed listing before {result['sealed_before']['combined_sha256'][:16]} after {result['sealed_after']['combined_sha256'][:16]} untouched={result['sealed_untouched']} scratch_deleted={result['scratch_deleted']}",
        "",
        "| stage | wall s | ms/record | MiB/s | identical | sha256 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for name in ("trace_append_per_record", "trace_append_open_once_flush", "sink_class_old", "sink_class_new", "facts_old", "facts_new", *SEAL_STAGES):
        e = s.get(name)
        if not e:
            continue
        wall = e.get("wall_s", e.get("wall_emit_s"))
        ident = e.get("byte_identical", e.get("facts_identical", e.get("verified", "-")))
        sha = e.get("sha256", e.get("trace_sha256", e.get("facts_sha256", "")))
        out.append(f"| {name} | {wall} | {e.get('per_record_ms', '-')} | {e.get('mib_per_s', '-')} | {ident} | {str(sha)[:16]} |")
    out.append("")
    if "facts_identical" in result:
        out.append(
            f"facts old==new: {result['facts_identical']} ({result['facts_sha256']['old'][:16]} / {result['facts_sha256']['new'][:16]}); "
            f"reader peak RSS old {s['facts_old']['peak_rss_gib']} GiB, new {s['facts_new']['peak_rss_gib']} GiB"
        )
        out.append(f"seal total (nine stages): {result['seal_total_wall_s']} s")
    for name in ("sink_class_old", "sink_class_new"):
        if name in s:
            out.append(f"{name}: trace identical {s[name]['trace_identical']}, trace manifest identical {s[name]['trace_manifest_identical']}, peak RSS {s[name]['peak_rss_gib']} GiB")
    out.append(f"all identical: {result['all_identical']}")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    p.add_argument("--run-id", default=DEFAULT_RUN_ID)
    p.add_argument("--attempt-id", default=DEFAULT_ATTEMPT_ID)
    p.add_argument("--scratch-dir", type=Path, required=True)
    p.add_argument("--target-label", required=True)
    p.add_argument("--old-commit", required=True)
    p.add_argument("--old-tree-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--only", default="",
        help="comma-separated subset of patterns,classes,readers so one pass on the mount stays short; default all",
    )
    for kind in ("sink-replay", "facts"):
        w = sub.add_parser(kind)
        w.add_argument("--src", type=Path, required=True)
        w.add_argument("--label", required=True)
        w.add_argument("--report", type=Path, required=True)
        if kind == "sink-replay":
            w.add_argument("--sealed-trace", type=Path, required=True)
            w.add_argument("--run-dir", type=Path, required=True)
            w.add_argument("--run-id", required=True)
        else:
            w.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "sink-replay":
        return worker_sink_replay(args)
    if args.command == "facts":
        return worker_facts(args)
    if not str(args.data_root):
        raise AcceptanceError("--data-root or SPEECHRL_DATA_DIR is required")
    result = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(summary(result))
    print(f"written {args.out}")
    return 0 if result["all_identical"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AcceptanceError as error:
        print(f"acceptance refused: {error}", file=sys.stderr)
        sys.exit(2)
