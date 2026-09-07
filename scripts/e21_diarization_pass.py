#!/usr/bin/env python3
"""``SAEA-E21-TOOL-DIARIZATION-V1`` -- the Earnings-21 speaker-diarization pass.

The runner for the pre-registered OBS row
(``docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md``): it builds
the pass's inputs from the flight's OWN sealed audio, drives the pinned frozen
diarization tool, and seals a ``saea-diarization-v1`` artifact that the reader
re-derives window for window.

Three phases, each its own subcommand and each its own receipt, so a failure never
leaves a half-built artifact behind:

``inputs``
    Concatenate the sealed 90-second obs-slices of
    ``SAEA-E21-FULL44-DIRECT-BASELINE-V2`` into one 16 kHz mono WAV per call, after
    verifying every slice's SHA-256 against the sealed ``obs-derivation`` receipt.
    Nothing is decoded from MP3, ``ffmpeg`` is not invoked, and no sample is
    resampled: the diarizer hears exactly the bytes the frozen core heard.

``diarize``
    One ``nemo-speech diarize`` invocation, with the model GGUF and the runtime
    binary both re-hashed against the umbrella lock BEFORE the process starts. GPU
    memory is sampled throughout, so the receipt carries a measured peak rather than
    an assumption.

``artifact``
    Parse the RTTM output, build every call block through
    ``reproduction.diarization.build_call_block`` -- the same code the reader
    re-derives with -- then load the sealed file back through ``load_diarization``
    and refuse to report if it does not validate.

**Zero frozen-core contacts.** The Qwen3-Omni core is not started, not queried and
not involved; no transcript, word or text of any kind is produced. Every tool fact
(model path, model SHA-256, runtime, binary path, binary SHA-256, pinned commit) is
read from the umbrella lock through ``data.lock`` at run time and never copied into
this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.e21_window_pairing import (  # noqa: E402
    window_id,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    lock_entry,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.reproduction.diarization import (  # noqa: E402
    DIARIZATION_SCHEMA,
    SpeakerSegment,
    build_call_block,
    load_diarization,
    window_grid,
    window_speakers,
)

RUN_ID = "SAEA-E21-TOOL-DIARIZATION-V1"
STUDY_SLUG = "speech-aware-evidence-acquisition"
CARRIER_LOCK_KEY = "earnings21-original"
TOOL_LOCK_KEY = "diar-sortformer-4spk-v2"
SOURCE_RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
WINDOW_SECONDS = 90.0
SAMPLE_RATE_HZ = 16000

ROSTER_RECEIPT = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
WINDOW_PAIRING_RECEIPT = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-window-pairing/reaggregation.json"
)


class PassError(RuntimeError):
    """A precondition of the pass does not hold -- stop, never guess."""


def _read_json(path: Path) -> Mapping[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_lock(args: argparse.Namespace):
    path = Path(args.lock) if args.lock else umbrella_lock_path(REPO_ROOT)
    return path, load_lock(path)


# ---------------------------------------------------------------------------
# Phase 1 -- inputs
# ---------------------------------------------------------------------------


def cmd_inputs(args: argparse.Namespace) -> int:
    roster = _read_json(ROSTER_RECEIPT)
    attempt_id = args.attempt_id or str(
        _read_json(WINDOW_PAIRING_RECEIPT)["source_attempt_id"]
    )
    root = data_root()
    attempt_dir = root / "runs" / SOURCE_RUN_ID / attempt_id
    if not attempt_dir.is_dir():
        raise PassError(f"sealed attempt directory {attempt_dir} does not exist")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    started = time.monotonic()
    for call in roster["calls"]:
        sample_id = str(call["sample_id"])
        derivation_path = attempt_dir / f"{SOURCE_RUN_ID}.obs-derivation.{sample_id}.json"
        derivation = _read_json(derivation_path)
        if str(derivation.get("boundary_mode")) != "fixed":
            raise PassError(f"call {sample_id} was not sliced in fixed-window mode")
        slices = sorted(derivation["slices"], key=lambda row: int(row["iteration"]))
        if [int(row["iteration"]) for row in slices] != list(range(len(slices))):
            raise PassError(f"call {sample_id} has a gapped slice iteration sequence")

        target = out_dir / f"{sample_id}.wav"
        frames_total = 0
        slice_rows = []
        with wave.open(str(target), "wb") as sink:
            sink.setnchannels(1)
            sink.setsampwidth(2)
            sink.setframerate(SAMPLE_RATE_HZ)
            for entry in slices:
                source = root / str(entry["media_relpath"])
                digest = sha256_file(source)
                if digest != str(entry["sha256"]):
                    raise PassError(
                        f"slice {source} sha256 {digest} does not match the sealed "
                        f"obs-derivation receipt {entry['sha256']}"
                    )
                with wave.open(str(source), "rb") as handle:
                    if (
                        handle.getnchannels() != 1
                        or handle.getsampwidth() != 2
                        or handle.getframerate() != SAMPLE_RATE_HZ
                    ):
                        raise PassError(f"slice {source} is not 16 kHz mono 16-bit PCM")
                    frames = handle.getnframes()
                    sink.writeframes(handle.readframes(frames))
                frames_total += frames
                slice_rows.append(digest)

        audio_seconds = frames_total / SAMPLE_RATE_HZ
        derived_windows = math.ceil(audio_seconds / WINDOW_SECONDS)
        roster_windows = int(call["fixed_90s_windows"])
        if derived_windows != roster_windows:
            raise PassError(
                f"call {sample_id} concatenates to {audio_seconds}s, which tiles into "
                f"{derived_windows} windows, but the sealed roster records {roster_windows}"
            )
        rows.append(
            {
                "sample_id": sample_id,
                "slice_count": len(slices),
                "slices_sha256_verified": len(slice_rows),
                # A single digest over the ordered slice hashes: recomputable from the
                # sealed obs-derivation receipt alone, so the concatenation input chain
                # stays byte-provable without copying 1,593 hashes into Git.
                "slice_sha256_chain": hashlib.sha256(
                    "\n".join(slice_rows).encode("utf-8")
                ).hexdigest(),
                "frames": frames_total,
                "audio_seconds": audio_seconds,
                "audio_sha256": sha256_file(target),
                "audio_bytes": target.stat().st_size,
                "audio_relpath": str(target.relative_to(root)),
                "windows": derived_windows,
                "roster_audio_seconds": float(call["audio_seconds"]),
                "roster_windows": roster_windows,
                "decoded_duration_seconds": float(derivation["decoded_duration_seconds"]),
                "parent_media_relpath": str(derivation["parent_media_relpath"]),
                "parent_sha256": str(derivation["parent_sha256"]),
            }
        )

    totals = {
        "calls": len(rows),
        "slices": sum(row["slice_count"] for row in rows),
        "audio_seconds": sum(row["audio_seconds"] for row in rows),
        "windows": sum(row["windows"] for row in rows),
        "audio_bytes": sum(row["audio_bytes"] for row in rows),
    }
    expected_windows = int(roster["totals"]["all_44"]["fixed_90s_windows"])
    if totals["windows"] != expected_windows:
        raise PassError(
            f"the concatenated inputs tile into {totals['windows']} windows, not the "
            f"sealed roster's {expected_windows}"
        )

    report = {
        "schema": "saea-e21-diarization-inputs-v1",
        "study": STUDY_SLUG,
        "run_id": RUN_ID,
        "carrier_lock_key": CARRIER_LOCK_KEY,
        "source_run_id": SOURCE_RUN_ID,
        "source_attempt_id": attempt_id,
        "window_seconds": WINDOW_SECONDS,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "output_dir_relpath": str(out_dir.relative_to(root)),
        "construction": (
            "each call is the byte concatenation of its sealed 90-second obs-slices in "
            "iteration order; every slice sha256 was re-verified against the sealed "
            "obs-derivation receipt before its frames were appended. No MP3 was decoded, "
            "no resampling was applied and ffmpeg was not invoked"
        ),
        "totals": totals,
        "roster_totals": roster["totals"]["all_44"],
        "elapsed_seconds": time.monotonic() - started,
        "generated_at": _now(),
        "calls": rows,
        "zero_contact": (
            "file reads, sha256 verification and PCM frame concatenation only. No model "
            "was loaded, no GPU was touched, no frozen-core contact was made"
        ),
    }
    digest = _write_json(Path(args.json_out), report)
    print(json.dumps({"receipt_sha256": digest, "totals": totals}, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Phase 2 -- the tool contact
# ---------------------------------------------------------------------------


class GpuSampler(threading.Thread):
    """Sample GPU memory and utilisation while the tool runs, so the receipt
    carries a MEASURED peak instead of a guess."""

    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(daemon=True)
        self.interval = interval
        # NOT ``self._stop`` -- that name is ``threading.Thread``'s own method.
        self._halt = threading.Event()
        self.samples: list[dict[str, float]] = []

    def run(self) -> None:
        while not self._halt.is_set():
            try:
                out = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=memory.used,utilization.gpu,power.draw",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                parts = out.stdout.strip().split(",")
                if len(parts) == 3:
                    self.samples.append(
                        {
                            "memory_used_mib": float(parts[0]),
                            "utilization_pct": float(parts[1]),
                            "power_w": float(parts[2]),
                        }
                    )
            except Exception:  # noqa: BLE001 -- a sampler must never break the pass
                pass
            self._halt.wait(self.interval)

    def stop(self) -> dict[str, object]:
        self._halt.set()
        self.join(timeout=15)
        if not self.samples:
            return {"samples": 0}
        return {
            "samples": len(self.samples),
            "peak_memory_used_mib": max(s["memory_used_mib"] for s in self.samples),
            "peak_utilization_pct": max(s["utilization_pct"] for s in self.samples),
            "peak_power_w": max(s["power_w"] for s in self.samples),
            "mean_utilization_pct": (
                sum(s["utilization_pct"] for s in self.samples) / len(self.samples)
            ),
        }


def _tool_identity(args: argparse.Namespace) -> dict[str, object]:
    lock_path, lock = _resolve_lock(args)
    entry = lock_entry(lock, TOOL_LOCK_KEY)
    root = data_root()
    model_dir = root / str(entry["local_subdir"])
    declared = next(
        row for row in entry["source"]["files"] if str(row["filename"]).endswith(".q8_0.gguf")
    )
    model_path = model_dir / str(declared["filename"])
    model_sha = sha256_file(model_path)
    if model_sha != str(declared["sha256"]):
        raise PassError(f"model {model_path} sha256 {model_sha} does not match the lock pin")
    deployment = entry["deployment_runtime"]
    binary = Path(str(deployment["checkout"])) / str(deployment["binary"])
    binary_sha = sha256_file(binary)
    if binary_sha != str(deployment["binary_sha256"]):
        raise PassError(
            f"runtime binary {binary} sha256 {binary_sha} does not match the lock pin"
        )
    return {
        "lock_path": str(lock_path),
        "lock_key": TOOL_LOCK_KEY,
        "revision": str(entry.get("revision")),
        "license": str(entry.get("license")),
        "model_path": str(model_path),
        "model_filename": str(declared["filename"]),
        "model_sha256": model_sha,
        "model_sha256_matches_lock": True,
        "runtime": str(deployment["runtime"]),
        "runtime_commit": str(deployment["commit"]),
        "runtime_binary": str(binary),
        "runtime_binary_sha256": binary_sha,
        "runtime_binary_sha256_matches_lock": True,
        "claim_limit": str(entry.get("claim_limit")),
    }


def cmd_diarize(args: argparse.Namespace) -> int:
    identity = _tool_identity(args)
    target = Path(args.input)
    if not target.exists():
        raise PassError(f"diarization input {target} does not exist")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    argv = [
        str(identity["runtime_binary"]),
        "diarize",
        str(target),
        "--model",
        str(identity["model_path"]),
        "--format",
        "rttm",
        "--device",
        args.device,
    ]
    if target.is_dir():
        argv += ["--output-dir", str(output_dir)]
    else:
        # The tool accepts --output-dir only for a directory input; a single-file
        # contact names its own sink and its own RTTM recording id.
        argv += [
            "--recording-id",
            target.stem,
            "--output",
            str(output_dir / f"{target.stem}.rttm"),
        ]
    argv.append("--force")
    if args.recursive:
        argv.append("--recursive")
    if args.concurrency:
        argv += ["--concurrency", str(args.concurrency)]

    version = subprocess.run(
        [str(identity["runtime_binary"]), "--version"], capture_output=True, text=True
    ).stdout.strip()

    sampler = GpuSampler()
    sampler.start()
    started = time.monotonic()
    completed = subprocess.run(argv, capture_output=True, text=True)
    wall_seconds = time.monotonic() - started
    gpu = sampler.stop()

    produced = sorted(path.name for path in output_dir.rglob("*.rttm"))
    report = {
        "schema": "saea-e21-diarization-contact-v1",
        "study": STUDY_SLUG,
        "run_id": RUN_ID,
        "phase": args.phase,
        "argv": argv,
        "tool_version": version,
        "tool": identity,
        "device": args.device,
        "return_code": completed.returncode,
        "wall_seconds": wall_seconds,
        "gpu": gpu,
        "stderr_tail": completed.stderr.strip().splitlines()[-12:],
        "stdout_tail": completed.stdout.strip().splitlines()[-5:],
        "rttm_files": produced,
        "rttm_count": len(produced),
        "output_dir": str(output_dir),
        "generated_at": _now(),
        "frozen_core_contacts": 0,
    }
    digest = _write_json(Path(args.json_out), report)
    print(
        json.dumps(
            {
                "receipt_sha256": digest,
                "return_code": completed.returncode,
                "wall_seconds": round(wall_seconds, 3),
                "gpu": gpu,
                "rttm_count": len(produced),
            },
            indent=2,
        )
    )
    return 0 if completed.returncode == 0 else 1


# ---------------------------------------------------------------------------
# Phase 3 -- the artifact
# ---------------------------------------------------------------------------


def parse_rttm(path: Path) -> list[SpeakerSegment]:
    """RTTM ``SPEAKER <rec> <chan> <start> <dur> <NA> <NA> <speaker> <NA> <NA>``."""

    segments: list[SpeakerSegment] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        text = line.strip()
        if not text:
            continue
        fields = text.split()
        if len(fields) < 8 or fields[0] != "SPEAKER":
            raise PassError(f"{path}:{line_number} is not an RTTM SPEAKER line")
        start = float(fields[3])
        duration = float(fields[4])
        speaker = fields[7]
        if duration <= 0:
            raise PassError(f"{path}:{line_number} has a non-positive duration")
        segments.append(
            SpeakerSegment(start_seconds=start, end_seconds=start + duration, speaker=speaker)
        )
    if not segments:
        raise PassError(f"{path} carries no speaker segments")
    return segments


def _histogram(labels) -> dict[str, int]:
    table: dict[str, int] = {}
    for label in labels:
        table[label] = table.get(label, 0) + 1
    return dict(sorted(table.items()))


def cmd_artifact(args: argparse.Namespace) -> int:
    inputs = _read_json(Path(args.inputs_receipt))
    contacts = [_read_json(Path(item)) for item in args.contact_receipt]
    rttm_dir = Path(args.rttm_dir)
    root = data_root()

    batch = next((row for row in contacts if row.get("phase") == "full-pass"), contacts[-1])
    tool = batch["tool"]

    call_blocks = []
    per_call = []
    for row in inputs["calls"]:
        sample_id = str(row["sample_id"])
        rttm_path = rttm_dir / f"{sample_id}.rttm"
        if not rttm_path.is_file():
            raise PassError(f"call {sample_id} has no RTTM output at {rttm_path}")
        segments = parse_rttm(rttm_path)
        block = build_call_block(
            sample_id=sample_id,
            audio_seconds=float(row["audio_seconds"]),
            segments=segments,
            window_seconds=WINDOW_SECONDS,
            window_id_of=window_id,
        )
        block["audio_sha256"] = str(row["audio_sha256"])
        block["rttm_sha256"] = sha256_file(rttm_path)
        call_blocks.append(block)
        speakers = sorted({str(seg["speaker"]) for seg in block["segments"]})
        per_call.append(
            {
                "sample_id": sample_id,
                "audio_seconds": float(row["audio_seconds"]),
                "windows": len(block["windows"]),
                "segments": len(block["segments"]),
                "speakers": speakers,
                "speaker_count": len(speakers),
                "speech_seconds": sum(
                    float(seg["end_seconds"]) - float(seg["start_seconds"])
                    for seg in block["segments"]
                ),
            }
        )

    document = {
        "schema": DIARIZATION_SCHEMA,
        "study": STUDY_SLUG,
        "run_id": RUN_ID,
        "attempt_id": args.attempt_id,
        "carrier_lock_key": CARRIER_LOCK_KEY,
        "window_seconds": WINDOW_SECONDS,
        "generated_at": _now(),
        "source_run_id": SOURCE_RUN_ID,
        "source_attempt_id": inputs["source_attempt_id"],
        "inputs_receipt_sha256": sha256_file(Path(args.inputs_receipt)),
        "tool": {
            "lock_key": str(tool["lock_key"]),
            "revision": str(tool["revision"]),
            "license": str(tool["license"]),
            "model_filename": str(tool["model_filename"]),
            "model_sha256": str(tool["model_sha256"]),
            "runtime": str(tool["runtime"]),
            "runtime_commit": str(tool["runtime_commit"]),
            "runtime_binary_sha256": str(tool["runtime_binary_sha256"]),
            "device": str(batch["device"]),
            "claim_limit": str(tool["claim_limit"]),
        },
        "speaker_ids_are_anonymous": (
            "the tool emits speaker_N ids that carry no identity and are not comparable "
            "across calls; no mapping to a roster name is made anywhere in this artifact"
        ),
        "no_accuracy_claim": (
            "no diarization error rate is measured or claimed; the tool 4-speaker design "
            "bound is narrower than an earnings call roster, so speaker_count saturates"
        ),
        "frozen_core_contacts": 0,
        "calls": call_blocks,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    artifact_sha256 = sha256_file(out_path)

    artifact = load_diarization(out_path)  # refuses any self-disagreement
    count_strata = artifact.window_strata("count")
    dominance_strata = artifact.window_strata("dominance")

    overlaps = sorted(
        window.overlap_share for call in artifact.calls.values() for window in call.windows
    )
    windows_total = len(overlaps)

    # The 4-speaker bound, reported rather than absorbed: how many calls name more
    # than four participants on their own ConEC roster, and how many windows those
    # calls carry. A COUNT of roster lines only -- no name is recorded here, no
    # speaker id is mapped to a name, and no accuracy is measured (preregistration
    # section 6).
    lock_path, lock = _resolve_lock(args)
    roster_dir = asset_dir(lock, "conec", root) / "earnings21" / "contexts" / "participant_names"
    roster_rows = []
    for row in per_call:
        names_path = roster_dir / f"{row['sample_id']}.names.txt"
        named = len(
            [
                line
                for line in names_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        )
        roster_rows.append(
            {
                "sample_id": row["sample_id"],
                "roster_participants": named,
                "windows": row["windows"],
                "tool_speaker_count": row["speaker_count"],
                "exceeds_tool_bound": named > 4,
            }
        )
    over_bound = [row for row in roster_rows if row["exceeds_tool_bound"]]

    speaker_counts = sorted(row["speaker_count"] for row in per_call)
    summary = {
        "schema": "saea-e21-diarization-obs-summary-v1",
        "study": STUDY_SLUG,
        "run_id": RUN_ID,
        "attempt_id": args.attempt_id,
        "lock_path": str(lock_path),
        "artifact_path": str(out_path),
        "artifact_relpath": str(out_path.relative_to(root)),
        "artifact_sha256": artifact_sha256,
        "artifact_bytes": out_path.stat().st_size,
        "reader_validation": "PASS",
        "reader_validation_detail": (
            "load_diarization re-derived every window dominant speaker, dominant share, "
            "speaker count and overlap share from that call own segment list and found no "
            f"disagreement, on all {len(artifact.calls)} calls and all {windows_total} windows"
        ),
        "calls": len(artifact.calls),
        "windows": windows_total,
        "segments": sum(len(call.segments) for call in artifact.calls.values()),
        "audio_seconds": sum(call.audio_seconds for call in artifact.calls.values()),
        "speaker_count_min": speaker_counts[0],
        "speaker_count_median": speaker_counts[len(speaker_counts) // 2],
        "speaker_count_max": speaker_counts[-1],
        "speaker_count_histogram": {
            str(value): speaker_counts.count(value) for value in sorted(set(speaker_counts))
        },
        "count_strata": _histogram(count_strata.values()),
        "dominance_strata": _histogram(dominance_strata.values()),
        "both_strata": _histogram(artifact.window_strata("both").values()),
        "overlap_share": {
            "mean": sum(overlaps) / windows_total,
            "median": overlaps[windows_total // 2],
            "p90": overlaps[int(0.90 * (windows_total - 1))],
            "max": overlaps[-1],
            "windows_with_any_overlap": sum(1 for value in overlaps if value > 0.0),
        },
        "four_speaker_bound_caveat": {
            "tool_bound": 4,
            "calls_whose_roster_exceeds_the_bound": len(over_bound),
            "windows_in_those_calls": sum(row["windows"] for row in over_bound),
            "windows_total": windows_total,
            "roster_participant_min": min(row["roster_participants"] for row in roster_rows),
            "roster_participant_max": max(row["roster_participants"] for row in roster_rows),
            "read": (
                "a COUNT of non-empty lines in each call ConEC participant_names file (a "
                "runtime-legal-input layer already hashed by the committed brief-provenance "
                "receipt). No name was recorded, no speaker id was mapped to a name, and no "
                "diarization accuracy was measured"
            ),
        },
        "per_call": per_call,
        "roster_bound_rows": roster_rows,
        "contacts": [
            {
                "phase": row["phase"],
                "device": row["device"],
                "wall_seconds": row["wall_seconds"],
                "return_code": row["return_code"],
                "rttm_count": row["rttm_count"],
                "gpu": row["gpu"],
            }
            for row in contacts
        ],
        "frozen_core_contacts": 0,
        "generated_at": _now(),
    }
    digest = _write_json(Path(args.summary_out), summary)
    print(
        json.dumps(
            {
                "artifact_sha256": artifact_sha256,
                "summary_sha256": digest,
                "reader_validation": "PASS",
                "calls": summary["calls"],
                "windows": summary["windows"],
                "speaker_count_min_median_max": [
                    summary["speaker_count_min"],
                    summary["speaker_count_median"],
                    summary["speaker_count_max"],
                ],
                "count_strata": summary["count_strata"],
                "dominance_strata": summary["dominance_strata"],
            },
            indent=2,
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Phase 3b -- serving-geometry agreement on the stop-rule call
# ---------------------------------------------------------------------------


def cmd_agreement(args: argparse.Namespace) -> int:
    """Does the tool say the same thing about one call under two serving
    geometries, and does any difference reach the reporting unit?

    The preregistration names Route A as the fallback if Route B "disagrees with
    itself" on the preflight call. The preflight runs one file (one worker, dynamic
    batching OFF); the corpus pass runs a directory (four workers, batching ON), and
    a batched GPU reduction is not bit-identical to an unbatched one -- the same
    effect this program already records for greedy llama-server decoding. This
    subcommand measures the size of that difference AND, decisively, whether it
    changes any of the window STRATUM labels that are the only thing the artifact is
    read for. Model-free: two files in, one receipt out, no contact of any kind.
    """

    inputs = _read_json(Path(args.inputs_receipt))
    row = next(
        entry for entry in inputs["calls"] if str(entry["sample_id"]) == args.sample_id
    )
    audio_seconds = float(row["audio_seconds"])
    grid = window_grid(audio_seconds, WINDOW_SECONDS)

    def _windows(path: Path):
        segments = sorted(
            parse_rttm(path), key=lambda seg: (seg.start_seconds, seg.speaker)
        )
        return segments, [
            window_speakers(
                segments,
                window_id=window_id(args.sample_id, index),
                window_index=index,
                start_seconds=start,
                end_seconds=end,
            )
            for index, (start, end) in enumerate(grid, start=1)
        ]

    a_segments, a_windows = _windows(Path(args.rttm_a))
    b_segments, b_windows = _windows(Path(args.rttm_b))

    disagreements = []
    for left, right in zip(a_windows, b_windows):
        row_out = {
            "window_id": left.window_id,
            "count_stratum_a": left.count_stratum,
            "count_stratum_b": right.count_stratum,
            "dominance_stratum_a": left.dominance_stratum,
            "dominance_stratum_b": right.dominance_stratum,
            "dominant_speaker_a": left.dominant_speaker,
            "dominant_speaker_b": right.dominant_speaker,
        }
        if (
            left.count_stratum != right.count_stratum
            or left.dominance_stratum != right.dominance_stratum
            or left.dominant_speaker != right.dominant_speaker
        ):
            disagreements.append(row_out)

    report = {
        "schema": "saea-e21-diarization-geometry-agreement-v1",
        "study": STUDY_SLUG,
        "run_id": RUN_ID,
        "sample_id": args.sample_id,
        "audio_seconds": audio_seconds,
        "windows": len(grid),
        "geometry_a": args.label_a,
        "geometry_b": args.label_b,
        "rttm_a": str(args.rttm_a),
        "rttm_b": str(args.rttm_b),
        "rttm_a_sha256": sha256_file(Path(args.rttm_a)),
        "rttm_b_sha256": sha256_file(Path(args.rttm_b)),
        "segments_a": len(a_segments),
        "segments_b": len(b_segments),
        "speech_seconds_a": sum(seg.duration_seconds for seg in a_segments),
        "speech_seconds_b": sum(seg.duration_seconds for seg in b_segments),
        "speakers_a": sorted({seg.speaker for seg in a_segments}),
        "speakers_b": sorted({seg.speaker for seg in b_segments}),
        "count_stratum_disagreements": sum(
            1 for row_out in disagreements
            if row_out["count_stratum_a"] != row_out["count_stratum_b"]
        ),
        "dominance_stratum_disagreements": sum(
            1 for row_out in disagreements
            if row_out["dominance_stratum_a"] != row_out["dominance_stratum_b"]
        ),
        "dominant_speaker_disagreements": sum(
            1 for row_out in disagreements
            if row_out["dominant_speaker_a"] != row_out["dominant_speaker_b"]
        ),
        "disagreeing_windows": disagreements,
        "reading": (
            "the two geometries are not bit-identical -- a batched GPU reduction moves "
            "a frame-level activation across the onset/offset threshold, so segment "
            "boundaries shift by a frame or two. What matters for this artifact is "
            "whether that reaches the STRATUM, which is the only field a verdict reads"
        ),
        "zero_contact": (
            "two committed RTTM files re-read offline. No model, GPU, tool, network or "
            "frozen-core contact"
        ),
        "generated_at": _now(),
    }
    digest = _write_json(Path(args.json_out), report)
    print(
        json.dumps(
            {
                "receipt_sha256": digest,
                "windows": report["windows"],
                "segments_a_b": [report["segments_a"], report["segments_b"]],
                "count_stratum_disagreements": report["count_stratum_disagreements"],
                "dominance_stratum_disagreements": report["dominance_stratum_disagreements"],
                "dominant_speaker_disagreements": report["dominant_speaker_disagreements"],
            },
            indent=2,
        )
    )
    return 0


def cmd_table(args: argparse.Namespace) -> int:
    """The per-call table the receipt publishes, rendered from the sealed summary
    so the numbers in Markdown and the numbers in JSON cannot drift."""

    summary = _read_json(Path(args.summary))
    roster = {row["sample_id"]: row for row in summary["roster_bound_rows"]}
    lines = [
        "| call | audio s | windows | segments | tool speakers | speech share | "
        "roster participants | roster > tool bound |",
        "|---|---:|---:|---:|---:|---:|---:|:--:|",
    ]
    for row in summary["per_call"]:
        bound = roster[row["sample_id"]]
        lines.append(
            "| {id} | {sec:.1f} | {win} | {seg} | {spk} | {share:.1%} | {named} | {flag} |".format(
                id=row["sample_id"],
                sec=row["audio_seconds"],
                win=row["windows"],
                seg=row["segments"],
                spk=row["speaker_count"],
                share=row["speech_seconds"] / row["audio_seconds"],
                named=bound["roster_participants"],
                flag="yes" if bound["exceeds_tool_bound"] else "no",
            )
        )
    text = "\n".join(lines) + "\n"
    Path(args.out).write_text(text, encoding="utf-8", newline="\n")
    print(f"{args.out}: {len(summary['per_call'])} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    inputs = sub.add_parser("inputs", help="concatenate the sealed slices per call")
    inputs.add_argument("--out-dir", required=True)
    inputs.add_argument("--json-out", required=True)
    inputs.add_argument("--attempt-id", default=None)
    inputs.set_defaults(func=cmd_inputs)

    diarize = sub.add_parser("diarize", help="one pinned tool contact")
    diarize.add_argument("--input", required=True)
    diarize.add_argument("--output-dir", required=True)
    diarize.add_argument("--json-out", required=True)
    diarize.add_argument("--device", default="cuda:0")
    diarize.add_argument("--phase", default="full-pass")
    diarize.add_argument("--recursive", action="store_true")
    diarize.add_argument("--concurrency", type=int, default=None)
    diarize.set_defaults(func=cmd_diarize)

    artifact = sub.add_parser("artifact", help="build, validate and seal the artifact")
    artifact.add_argument("--inputs-receipt", required=True)
    artifact.add_argument("--contact-receipt", action="append", required=True)
    artifact.add_argument("--rttm-dir", required=True)
    artifact.add_argument("--attempt-id", required=True)
    artifact.add_argument("--out", required=True)
    artifact.add_argument("--summary-out", required=True)
    artifact.set_defaults(func=cmd_artifact)

    agreement = sub.add_parser(
        "agreement", help="compare one call's RTTM under two serving geometries"
    )
    agreement.add_argument("--inputs-receipt", required=True)
    agreement.add_argument("--sample-id", required=True)
    agreement.add_argument("--rttm-a", required=True)
    agreement.add_argument("--rttm-b", required=True)
    agreement.add_argument("--label-a", default="preflight: one file, 1 worker, batching off")
    agreement.add_argument("--label-b", default="corpus pass: directory, 4 workers, batching on")
    agreement.add_argument("--json-out", required=True)
    agreement.set_defaults(func=cmd_agreement)

    table = sub.add_parser("table", help="render the receipt's per-call table")
    table.add_argument("--summary", required=True)
    table.add_argument("--out", required=True)
    table.set_defaults(func=cmd_table)

    args = parser.parse_args(argv)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
