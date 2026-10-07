"""Compare frozen and prospective loaders on synthetic equivalent vector rows."""
import argparse
import ast
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import tracemalloc

LEGACY_SHA = "5cf42534f370b66afdeaf6423cd82b71469b77619e908ba373058d5c33fab49f"


def file_hash(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def worker(args):
    from speech_aware_evidence_acquisition.rails import phase_supply as ps
    name = "load_sealed_vectors" if args.kind == "vectors" else "load_sealed_segment_vectors"
    if args.implementation == "frozen":
        assert file_hash(args.legacy_source) == LEGACY_SHA
        tree = ast.parse(args.legacy_source.read_text())
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        namespace = dict(vars(ps))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(args.legacy_source), "exec"), namespace)
        loader = namespace[name]
    else:
        loader = getattr(ps, name)
    gc.collect()
    tracemalloc.start()
    started = time.monotonic()
    table = loader(args.fixture, expected_sha256=args.input_sha256, dimensions=("content",))
    elapsed = time.monotonic() - started
    retained, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    digest = hashlib.sha256()
    components = 0
    for entry_id, record in table.items():
        digest.update(entry_id.encode())
        if args.kind == "segments":
            digest.update(record.audio_sha256.encode())
            records = record.segments
        else:
            records = (record,)
        for dimension_record in records:
            for dimension, vector in dimension_record.items():
                digest.update(dimension.encode())
                for value in vector:
                    digest.update(value.hex().encode() + b"\n")
                    components += 1
    print(json.dumps({"implementation": args.implementation, "kind": args.kind,
                      "rows": len(table), "float_components": components,
                      "input_bytes": args.fixture.stat().st_size, "input_sha256": args.input_sha256,
                      "table_float_hex_sha256": digest.hexdigest(), "elapsed_seconds": elapsed,
                      "traced_retained_bytes": retained, "traced_peak_bytes": peak,
                      "ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--width", type=int, default=2048)
    parser.add_argument("--small-rows", type=int, default=128)
    parser.add_argument("--large-rows", type=int, default=1024)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--input-sha256")
    parser.add_argument("--kind", choices=("vectors", "segments"))
    parser.add_argument("--implementation", choices=("frozen", "streaming"))
    args = parser.parse_args()
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    assert file_hash(args.legacy_source) == LEGACY_SHA
    if args.worker:
        worker(args)
        return
    assert args.output is not None and not args.output.exists()
    vector = [0.12345678901234567 + (index % 19) * 1e-10 for index in range(args.width)]
    measurements = []
    with tempfile.TemporaryDirectory(prefix="saea-synthetic-vector-profile-") as temp:
        for kind in ("vectors", "segments"):
            for rows in (args.small_rows, args.large_rows):
                fixture = Path(temp) / f"{kind}-{rows}.jsonl"
                with fixture.open("w") as handle:
                    for number in range(rows):
                        if kind == "vectors":
                            row = {"id": f"synthetic:{number:06}", "vectors": {"content": vector}}
                        else:
                            row = {"id": f"synthetic:{number:06}", "audio_sha256": "a" * 64,
                                   "source_frames": 16000, "source_sample_rate_hz": 16000,
                                   "segments": [{"id": "synthetic-segment", "start_frame": 0,
                                                 "end_frame": 16000, "vectors": {"content": vector}}]}
                        handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                pin = file_hash(fixture)
                pair = []
                for implementation in ("frozen", "streaming"):
                    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker",
                               "--legacy-source", str(args.legacy_source), "--fixture", str(fixture),
                               "--input-sha256", pin, "--kind", kind, "--implementation", implementation]
                    completed = subprocess.run(command, check=True, text=True, capture_output=True, timeout=180)
                    result = json.loads(completed.stdout)
                    pair.append(result)
                    measurements.append(result)
                    print(json.dumps(result), flush=True)
                assert file_hash(fixture) == pin, "Synthetic source bytes changed"
                assert pair[0]["table_float_hex_sha256"] == pair[1]["table_float_hex_sha256"]
                assert pair[0]["float_components"] == pair[1]["float_components"]
                assert pair[1]["traced_peak_bytes"] < pair[0]["traced_peak_bytes"]
    from speech_aware_evidence_acquisition.rails import phase_supply as ps
    output = {"schema": "saea-model-free-sealed-vector-memory-profile-v1", "status": "PASS",
              "scope": "synthetic equivalent fixtures only; no model/API/scorer/task output",
              "legacy_source_sha256": LEGACY_SHA, "prospective_source_sha256": file_hash(Path(ps.__file__)),
              "profiler_sha256": file_hash(Path(__file__)), "measurements": measurements}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
