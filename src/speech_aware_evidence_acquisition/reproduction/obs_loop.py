"""The ``obs-agent-loop`` policy: model-driven OBS segmentation of long calls.

Owner directive (session message, 2026-08-08; supersedes the fixed-window
segment-as-sample design): the frozen core must never be asked to process a
whole 40-75-minute earnings call in one request, and the OBS layer is a
model-driven agent loop INSIDE a policy -- one sample stays ONE whole call
(splits and D1 identity untouched); per sample the policy maintains a
sliding audio buffer over the parent PCM, sends ONE buffer slice per
request, and advances by a boundary resolved through three tiers
(``reproduction.obs_audio.resolve_advance``):

1. the model's rough end-of-last-complete-sentence estimate, parsed from the
   frozen-format response (``TRANSCRIPT: ... BOUNDARY_SECONDS: <n>``);
2. deterministic VAD snap to the nearest speech/non-speech transition within
   ``+/- obs_silence_snap_seconds`` (owner addition 2026-08-08: VAD
   transitions; v1 engine is the zero-dependency pure-Python energy VAD,
   ``obs_vad: "energy"``; ``webrtcvad`` is runtime-detected, never a
   pyproject dependency -- the dependency set is pinned at zero);
3. clamp into ``[obs_min_advance_seconds, obs_max_advance_seconds]``; an
   unparseable/out-of-range estimate falls back to
   ``obs_fallback_advance_seconds`` and is flagged in the OBS trace.

Transcript acceptance is the deterministic sentence-cut rule
(``obs_audio.accept_up_to_boundary``); the final buffer accepts everything.
The per-sample hypothesis is the ordered concatenation of accepted spans --
the outputs row carries it once per sample, so the frozen ``asr-wer`` scorer
and every downstream shape are unchanged.

Slices are cut at runtime (one decode per sample) and written under
``derived/obs-slices/<run_id>/`` inside the controlled data root; every
slice registers a :class:`core.model.SliceRecord` derivation record BEFORE
the request that names it, and the payload-binding rail admits it only
through that chain (``core.model.slices`` module docstring). VAD pre-trim
(owner addition): non-speech spans longer than ``obs_vad_trim_min_seconds``
are skipped before a buffer is cut -- trimmed seconds never enter a request
and are therefore never metered; every trim is an OBS trace record.
Preprocessing v1 (default OFF): ``obs_preprocess: ["rms-norm"]`` normalizes
each slice's loudness after cutting, before writing; the derivation record
carries the declared transform + the raw-cut hash.

Tail conditioning (owner addition, 2026-08-08 -- Whisper-style
condition-on-previous, Node-1 knowledge v1): each iteration's rendered
task_instruction includes the tail of the previously ACCEPTED transcript
(``obs_condition_tail_chars``, default 400; 0 disables and reproduces the
unconditioned loop exactly). The tail is MODEL OUTPUT -- never gold, never a
reference transcript, never a test annotation -- framed explicitly as prior
transcript context, not instruction; the leakage discipline (D2) is
unaffected, and the bare-core arm's frozen 10-field payload set is untouched
because the tail rides inside the rendered ``task_instruction`` string.

I7 note (stitch records): the outputs row is one stitched hypothesis per
sample, so the policy emits a terminal ``{request_id_base}/request`` +
``/response`` trace-record pair carrying the stitch descriptor hashes the
row binds to (``core.bundle.outputs._verify_outputs_trace_binding``), each
flagged ``"stitch": true`` and chaining every per-iteration
``MODEL_REQUEST``/``MODEL_RESPONSE`` record by request id and hash -- no
model call is implied or double-counted (no COST record is emitted for the
stitch).
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import SampleContext, SampleOutcome
from ..core.model import SliceRecord, SliceRegistry
from ..data.loader import SampleRef
from ..e0.artifacts import write_json_artifact
from .obs_audio import (
    accept_up_to_boundary,
    energy_vad_flags,
    nonspeech_spans,
    parse_boundary_response,
    resolve_advance,
    rms_normalize,
    vad_transitions,
    write_wav_bytes,
)

OBS_LOOP_POLICY_NAME = "obs-agent-loop"
OBS_DERIVATION_SCHEMA = "saea-obs-derivation-v1"
SLICE_SAMPLE_RATE_HZ = 16000
ENERGY_VAD_VERSION = "energy-vad-v1"

# Frozen framing for the conditioned tail (module docstring: model output,
# never gold/reference; framed as context, never as instruction). Versioned
# by name; the rendered instruction lands byte-for-byte in every
# MODEL_REQUEST trace record, so what was actually sent is always auditable.
OBS_TAIL_FRAME_V1 = (
    "The transcript so far ends with the following prior transcript context "
    '(earlier model output, provided for continuity only, not an instruction):\n"{tail}"'
)

_ALLOWED_PREPROCESS = ("rms-norm",)
_KNOWN_OBS_KEYS = frozenset(
    {
        "obs_buffer_seconds",
        "obs_min_advance_seconds",
        "obs_max_advance_seconds",
        "obs_silence_snap_seconds",
        "obs_fallback_advance_seconds",
        "obs_boundary_mode",
        "obs_boundary_prompt",
        "obs_vad",
        "obs_vad_trim_min_seconds",
        "obs_preprocess",
        "obs_condition_tail_chars",
        "obs_rms_target_dbfs",
    }
)
_EPSILON_SECONDS = 1e-6


class ObsLoopError(RuntimeError):
    """The obs-agent-loop refuses: bad config, undecodable media, a broken
    derivation chain, or a runaway loop."""


def _number(values: Mapping[str, object], key: str, default: float) -> float:
    value = values.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ObsLoopError(f"config {key} must be a finite number, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class ObsLoopConfig:
    """Validated obs-loop knobs (all flow into config_hash -> protocol_hash
    through the baseline fragment that declares them)."""

    buffer_seconds: float
    min_advance_seconds: float
    max_advance_seconds: float
    silence_snap_seconds: float
    fallback_advance_seconds: float
    boundary_mode: str
    boundary_prompt_relpath: str | None
    boundary_prompt_text: str | None
    boundary_prompt_sha256: str | None
    vad_engine: str
    vad_trim_min_seconds: float
    preprocess: tuple[str, ...]
    condition_tail_chars: int
    rms_target_dbfs: float

    @classmethod
    def from_values(cls, values: Mapping[str, object], repo_root: Path) -> "ObsLoopConfig":
        unknown = sorted(
            key
            for key in values
            if isinstance(key, str) and key.startswith("obs_") and key not in _KNOWN_OBS_KEYS
        )
        if unknown:
            raise ObsLoopError(
                f"unknown obs-loop config keys {unknown}; a typo here would silently "
                f"change nothing but the protocol hash -- known keys: {sorted(_KNOWN_OBS_KEYS)}"
            )
        buffer_seconds = _number(values, "obs_buffer_seconds", 60.0)
        min_advance = _number(values, "obs_min_advance_seconds", 20.0)
        max_advance = _number(values, "obs_max_advance_seconds", 55.0)
        snap = _number(values, "obs_silence_snap_seconds", 2.0)
        fallback = _number(values, "obs_fallback_advance_seconds", 50.0)
        trim_min = _number(values, "obs_vad_trim_min_seconds", 5.0)
        rms_target = _number(values, "obs_rms_target_dbfs", -20.0)
        if buffer_seconds <= 0:
            raise ObsLoopError(f"obs_buffer_seconds must be positive, got {buffer_seconds}")
        if not (0 < min_advance <= max_advance <= buffer_seconds):
            raise ObsLoopError(
                "obs advance window must satisfy 0 < min <= max <= buffer, got "
                f"min={min_advance} max={max_advance} buffer={buffer_seconds}"
            )
        if not (min_advance <= fallback <= max_advance):
            raise ObsLoopError(
                f"obs_fallback_advance_seconds {fallback} must lie inside "
                f"[{min_advance}, {max_advance}]"
            )
        if snap < 0 or trim_min < 0:
            raise ObsLoopError("obs snap/trim seconds must be >= 0 (0 disables)")
        mode = values.get("obs_boundary_mode", "model")
        if mode not in ("model", "fixed"):
            raise ObsLoopError(f"obs_boundary_mode must be 'model' or 'fixed', got {mode!r}")
        engine = values.get("obs_vad", "energy")
        if engine not in ("energy", "webrtc"):
            raise ObsLoopError(f"obs_vad must be 'energy' or 'webrtc', got {engine!r}")
        raw_preprocess = values.get("obs_preprocess", [])
        if not isinstance(raw_preprocess, (list, tuple)) or not all(
            isinstance(name, str) for name in raw_preprocess
        ):
            raise ObsLoopError("obs_preprocess must be a list of transform names")
        bad = sorted(set(raw_preprocess) - set(_ALLOWED_PREPROCESS))
        if bad:
            raise ObsLoopError(
                f"obs_preprocess names unsupported transforms {bad}; v1 supports "
                f"{list(_ALLOWED_PREPROCESS)} only"
            )
        tail_chars = values.get("obs_condition_tail_chars", 400)
        if isinstance(tail_chars, bool) or not isinstance(tail_chars, int) or tail_chars < 0:
            raise ObsLoopError(
                f"obs_condition_tail_chars must be an integer >= 0, got {tail_chars!r}"
            )
        prompt_relpath = values.get("obs_boundary_prompt")
        prompt_text: str | None = None
        prompt_sha256: str | None = None
        if mode == "model":
            if not isinstance(prompt_relpath, str) or not prompt_relpath.strip():
                raise ObsLoopError(
                    "obs_boundary_mode 'model' requires obs_boundary_prompt (a frozen "
                    "template path under configs/)"
                )
            template = Path(repo_root) / "configs" / prompt_relpath
            try:
                prompt_text = template.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise ObsLoopError(
                    f"cannot read obs boundary prompt template {template}: {error}"
                ) from error
            prompt_sha256 = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        return cls(
            buffer_seconds=buffer_seconds,
            min_advance_seconds=min_advance,
            max_advance_seconds=max_advance,
            silence_snap_seconds=snap,
            fallback_advance_seconds=fallback,
            boundary_mode=str(mode),
            boundary_prompt_relpath=prompt_relpath if mode == "model" else None,
            boundary_prompt_text=prompt_text,
            boundary_prompt_sha256=prompt_sha256,
            vad_engine=str(engine),
            vad_trim_min_seconds=trim_min,
            preprocess=tuple(raw_preprocess),
            condition_tail_chars=tail_chars,
            rms_target_dbfs=rms_target,
        )


# ---------------------------------------------------------------------------
# Parent decode (heavy imports stay function-local; tests monkeypatch this)
# ---------------------------------------------------------------------------


def decode_parent_pcm(path: Path, sample_rate_hz: int = SLICE_SAMPLE_RATE_HZ) -> array:
    """Decode the parent media to 16 kHz mono int16 PCM, exactly once per
    sample. Preference order: ffmpeg (resamples deterministically for a
    pinned build), then librosa (the WSL speechrl venv ships it), then
    soundfile (only when the native rate already matches -- soundfile has no
    resampler). Fail-closed with a clear operator message otherwise."""

    path = Path(path)
    if not path.is_file():
        raise ObsLoopError(f"parent media missing: {path}")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "decoded.wav"
            command = [
                ffmpeg, "-v", "error", "-y", "-i", str(path),
                "-ac", "1", "-ar", str(sample_rate_hz),
                "-c:a", "pcm_s16le", "-map_metadata", "-1", "-bitexact", str(out),
            ]
            proc = subprocess.run(command, capture_output=True, text=True)
            if proc.returncode != 0:
                raise ObsLoopError(
                    f"ffmpeg failed to decode {path}: {proc.stderr.strip()[:500]}"
                )
            with wave.open(str(out), "rb") as handle:
                frames = handle.readframes(handle.getnframes())
            samples = array("h")
            samples.frombytes(frames)
            return samples
    try:
        import librosa  # noqa: PLC0415 (heavy import stays function-local)
        import numpy  # noqa: PLC0415

        floats, _ = librosa.load(str(path), sr=sample_rate_hz, mono=True)
        clipped = numpy.clip(numpy.rint(floats * 32767.0), -32768, 32767).astype("int16")
        return array("h", clipped.tolist())
    except ImportError:
        pass
    try:
        import soundfile  # noqa: PLC0415

        data, rate = soundfile.read(str(path), dtype="int16", always_2d=True)
        if rate != sample_rate_hz:
            raise ObsLoopError(
                f"soundfile decoded {path} at {rate} Hz and cannot resample to "
                f"{sample_rate_hz} Hz; install ffmpeg or librosa in the WSL venv"
            )
        mono = array("h")
        for row in data:
            mono.append(int(sum(int(v) for v in row) / len(row)))
        return mono
    except ImportError:
        pass
    raise ObsLoopError(
        f"no decoder available for {path}: need ffmpeg on PATH, or librosa, or "
        "soundfile (16 kHz media only) in the environment"
    )


def _vad_flags(samples: Sequence[int], rate: int, engine: str) -> tuple[list[bool], str]:
    """(flags, engine descriptor). ``webrtc`` is runtime-detected and
    fail-closed when asked for but absent -- never a silent fallback."""

    if engine == "energy":
        return energy_vad_flags(samples, rate), ENERGY_VAD_VERSION
    try:
        import webrtcvad  # noqa: PLC0415 (runtime-detected, never in pyproject)
    except ImportError as error:
        raise ObsLoopError(
            "obs_vad 'webrtc' requested but webrtcvad is not installed in this "
            "environment; install it in the WSL venv or use obs_vad 'energy'"
        ) from error
    vad = webrtcvad.Vad(2)
    frame_len = int(0.03 * rate)
    raw = array("h", samples).tobytes()
    frame_bytes = frame_len * 2
    flags = []
    for start in range(0, len(raw) - frame_bytes + 1, frame_bytes):
        flags.append(bool(vad.is_speech(raw[start : start + frame_bytes], rate)))
    version = getattr(webrtcvad, "__version__", "unknown")
    return flags, f"webrtcvad-{version}"


class ObsAgentLoopPolicy:
    """One whole-call sample -> N buffer-slice requests -> one stitched
    hypothesis (module docstring). Stateless; every run fact arrives through
    ``SampleContext`` (``extras``: slice_registry / data_root / run_dir /
    repo_root / config_values, supplied by ``core.driver.run_experiment``)."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        registry = ctx.extras.get("slice_registry")
        if not isinstance(registry, SliceRegistry):
            raise ObsLoopError(
                "obs-agent-loop requires a core.model.SliceRegistry in "
                "SampleContext.extras['slice_registry'] (supplied by "
                "core.driver.run_experiment); refusing to cut unchained slices"
            )
        try:
            data_root = Path(ctx.extras["data_root"])
            run_dir = Path(ctx.extras["run_dir"])
            repo_root = Path(ctx.extras["repo_root"])
            config_values = ctx.extras["config_values"]
        except KeyError as error:
            raise ObsLoopError(
                f"obs-agent-loop SampleContext.extras lacks {error}; supplied only by "
                "core.driver.run_experiment"
            ) from error
        cfg = ObsLoopConfig.from_values(config_values, repo_root)
        sample: SampleRef = ctx.sample
        rate = SLICE_SAMPLE_RATE_HZ
        parent_path = data_root / sample.media_relpath
        pcm = decode_parent_pcm(parent_path, rate)
        if not len(pcm):
            raise ObsLoopError(f"decoded zero samples from {parent_path}")
        duration = len(pcm) / rate
        parent_sha256 = _sha256_file(parent_path)

        need_vad = cfg.boundary_mode == "model" or cfg.vad_trim_min_seconds > 0
        flags: list[bool] = []
        engine_descriptor = "vad-not-run"
        transitions: list[float] = []
        trim_spans: list[tuple[float, float]] = []
        if need_vad:
            flags, engine_descriptor = _vad_flags(pcm, rate, cfg.vad_engine)
            frame_seconds = 0.03
            transitions = vad_transitions(flags, frame_seconds)
            if cfg.vad_trim_min_seconds > 0:
                trim_spans = nonspeech_spans(
                    flags, frame_seconds, min_seconds=cfg.vad_trim_min_seconds
                )

        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        accepted_spans: list[str] = []
        request_ids: list[str] = []
        iteration_request_sha256s: list[str] = []
        iteration_response_sha256s: list[str] = []
        slice_records: list[SliceRecord] = []
        trim_events: list[dict[str, object]] = []
        iteration = 0
        trims = 0
        cursor = 0.0
        effective_min = (
            cfg.buffer_seconds if cfg.boundary_mode == "fixed" else cfg.min_advance_seconds
        )
        max_iterations = math.ceil(duration / max(effective_min, 1e-9)) + len(trim_spans) + 8

        while cursor < duration - _EPSILON_SECONDS:
            trimmed = self._next_trim(trim_spans, cursor, cfg.vad_trim_min_seconds)
            if trimmed is not None:
                span_start, span_end = trimmed
                new_cursor = min(span_end, duration)
                ctx.sink.emit(
                    "OBS",
                    f"{ctx.request_id_base}-trim{trims:04d}/obs",
                    {
                        "obs_trim_from_seconds": cursor,
                        "obs_trim_to_seconds": new_cursor,
                        "obs_trim_span_start_seconds": span_start,
                        "obs_trim_span_end_seconds": span_end,
                        "obs_vad_engine": engine_descriptor,
                    },
                )
                trim_events.append(
                    {"from_seconds": cursor, "to_seconds": new_cursor, "engine": engine_descriptor}
                )
                trims += 1
                cursor = new_cursor
                continue

            start_frame = int(round(cursor * rate))
            end_frame = min(int(round((cursor + cfg.buffer_seconds) * rate)), len(pcm))
            if end_frame <= start_frame:
                break
            slice_samples = pcm[start_frame:end_frame]
            slice_seconds = (end_frame - start_frame) / rate
            is_final = end_frame >= len(pcm)
            raw_bytes = write_wav_bytes(slice_samples, rate)
            pre_sha256: str | None = None
            if "rms-norm" in cfg.preprocess:
                pre_sha256 = hashlib.sha256(raw_bytes).hexdigest()
                slice_samples = rms_normalize(slice_samples, cfg.rms_target_dbfs)
                raw_bytes = write_wav_bytes(slice_samples, rate)
            relpath = registry.slice_relpath(sample.sample_id, iteration)
            slice_path = data_root / relpath
            slice_path.parent.mkdir(parents=True, exist_ok=True)
            slice_path.write_bytes(raw_bytes)
            record = SliceRecord(
                sample_id=sample.sample_id,
                parent_media_relpath=sample.media_relpath,
                parent_sha256=parent_sha256,
                start_seconds=start_frame / rate,
                end_seconds=end_frame / rate,
                audio_seconds=slice_seconds,
                sample_rate_hz=rate,
                media_relpath=relpath,
                sha256=hashlib.sha256(raw_bytes).hexdigest(),
                bytes=len(raw_bytes),
                iteration=iteration,
                preprocess=cfg.preprocess,
                pre_sha256=pre_sha256,
            )
            registry.register(record)
            slice_records.append(record)

            stitched_so_far = " ".join(span for span in accepted_spans if span)
            tail = (
                stitched_so_far[-cfg.condition_tail_chars :]
                if cfg.condition_tail_chars > 0 and stitched_so_far
                else ""
            )
            instruction = ctx.task_instruction
            if cfg.boundary_mode == "model":
                instruction = f"{instruction}\n\n{cfg.boundary_prompt_text}"
            if tail:
                instruction = f"{instruction}\n\n{OBS_TAIL_FRAME_V1.format(tail=tail)}"

            slice_ref = SampleRef(
                carrier_lock_key=sample.carrier_lock_key,
                sample_id=sample.sample_id,
                media_relpath=relpath,
                audio_seconds=slice_seconds,
                sample_rate_hz=rate,
            )
            request_id = f"{ctx.request_id_base}-i{iteration:04d}"
            # Deferred import: core.policies imports THIS module's policy class
            # to register it; importing build_arm_payload back at module level
            # would be circular. By run time both modules are always loaded.
            from ..core.policies import build_arm_payload

            payload = build_arm_payload(
                ctx.arm,
                slice_ref,
                request_id,
                instruction,
                ctx.decoding_params,
                evidence=evidence,
                retrieval_query=ctx.retrieval_query,
            )
            response = ctx.adapter.request(payload)

            if cfg.boundary_mode == "model":
                transcript, estimate = parse_boundary_response(response.text)
            else:
                transcript, estimate = response.text.strip(), None
            if is_final:
                accepted, dropped = transcript, ""
                resolution: dict[str, object] = {
                    "estimate": estimate,
                    "snapped": None,
                    "advance": slice_seconds,
                    "clamped": False,
                    "fallback": False,
                }
            elif cfg.boundary_mode == "fixed":
                accepted, dropped = transcript, ""
                resolution = {
                    "estimate": None,
                    "snapped": None,
                    "advance": slice_seconds,
                    "clamped": False,
                    "fallback": False,
                }
            else:
                window_start = start_frame / rate
                local_transitions = [
                    t - window_start
                    for t in transitions
                    if window_start <= t <= window_start + slice_seconds
                ]
                resolution = resolve_advance(
                    estimate,
                    transitions=local_transitions,
                    snap_window=cfg.silence_snap_seconds,
                    min_advance=cfg.min_advance_seconds,
                    max_advance=cfg.max_advance_seconds,
                    fallback_advance=cfg.fallback_advance_seconds,
                    buffer_seconds=slice_seconds,
                )
                advance = min(float(resolution["advance"]), slice_seconds)
                resolution["advance"] = advance
                accepted, dropped = accept_up_to_boundary(transcript, advance / slice_seconds)

            ctx.sink.emit(
                "OBS",
                f"{request_id}/obs",
                {
                    "obs_iteration": iteration,
                    "obs_window_start_seconds": record.start_seconds,
                    "obs_window_end_seconds": record.end_seconds,
                    "obs_final_window": is_final,
                    "obs_slice_relpath": relpath,
                    "obs_slice_sha256": record.sha256,
                    "obs_pre_sha256": pre_sha256,
                    "obs_preprocess": list(cfg.preprocess),
                    "obs_vad_engine": engine_descriptor,
                    "obs_boundary_mode": cfg.boundary_mode,
                    "obs_boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                    "obs_boundary_estimate_seconds": resolution["estimate"],
                    "obs_boundary_snapped_seconds": resolution["snapped"],
                    "obs_boundary_advance_seconds": resolution["advance"],
                    "obs_boundary_clamped": resolution["clamped"],
                    "obs_boundary_fallback": resolution["fallback"],
                    "obs_accepted_chars": len(accepted),
                    "obs_dropped_chars": len(dropped),
                    "obs_tail_chars_used": len(tail),
                    "obs_tail_sha256": (
                        hashlib.sha256(tail.encode("utf-8")).hexdigest() if tail else None
                    ),
                },
            )
            accepted_spans.append(accepted.strip())
            request_ids.append(request_id)
            iteration_request_sha256s.append(response.request_sha256)
            iteration_response_sha256s.append(response.response_sha256)
            cursor = record.start_seconds + float(resolution["advance"])
            iteration += 1
            if iteration > max_iterations:
                raise ObsLoopError(
                    f"obs loop exceeded {max_iterations} iterations for sample "
                    f"{sample.sample_id!r}; refusing a runaway loop"
                )

        if not request_ids:
            raise ObsLoopError(
                f"sample {sample.sample_id!r} produced no requests (entirely trimmed "
                "as non-speech?); refusing to emit an empty hypothesis silently"
            )

        stitched = " ".join(span for span in accepted_spans if span)
        write_json_artifact(
            run_dir / f"{ctx.sink.run_id}.obs-derivation.{sample.sample_id}.json",
            {
                "schema": OBS_DERIVATION_SCHEMA,
                "run_id": ctx.sink.run_id,
                "sample_id": sample.sample_id,
                "parent_media_relpath": sample.media_relpath,
                "parent_sha256": parent_sha256,
                "decoded_duration_seconds": duration,
                "vad_engine": engine_descriptor,
                "boundary_mode": cfg.boundary_mode,
                "boundary_prompt_relpath": cfg.boundary_prompt_relpath,
                "boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                "condition_tail_chars": cfg.condition_tail_chars,
                "trims": trim_events,
                "slices": [record.trace_view() for record in slice_records],
            },
        )

        request_descriptor = _canonical_bytes(
            {
                "stitched_request_ids": request_ids,
                "iteration_request_sha256s": iteration_request_sha256s,
            }
        )
        request_sha256 = hashlib.sha256(request_descriptor).hexdigest()
        response_descriptor = _canonical_bytes(
            {
                "stitched_text": stitched,
                "stitched_from_response_sha256s": iteration_response_sha256s,
            }
        )
        response_sha256 = hashlib.sha256(response_descriptor).hexdigest()
        response_text_sha256 = hashlib.sha256(stitched.encode("utf-8")).hexdigest()
        ctx.sink.emit(
            "MODEL_REQUEST",
            f"{ctx.request_id_base}/request",
            {
                "arm": ctx.arm,
                "payload_sha256": request_sha256,
                "stitch": True,
                "stitched_request_ids": request_ids,
            },
        )
        ctx.sink.emit(
            "MODEL_RESPONSE",
            f"{ctx.request_id_base}/response",
            {
                "text": stitched,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "stitch": True,
                "stitched_from_response_sha256s": iteration_response_sha256s,
            },
        )
        ctx.sink.emit(
            "USE",
            f"{ctx.request_id_base}/use",
            {
                "use_response_sha256": response_sha256,
                "use_admitted": True,
                "use_stitched_iterations": len(request_ids),
            },
        )
        return SampleOutcome(
            sample_id=sample.sample_id,
            request_ids=tuple(request_ids),
            text=stitched,
            admitted=True,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            response_text_sha256=response_text_sha256,
        )

    @staticmethod
    def _next_trim(
        trim_spans: Sequence[tuple[float, float]], cursor: float, trim_min: float
    ) -> tuple[float, float] | None:
        """The first long non-speech span the cursor currently sits in (or at
        the edge of), if the remaining part of that span is itself still
        trim-worthy. Exact rule: span (s, e) applies when ``s <= cursor + 0.5``
        and ``e - max(s, cursor) >= trim_min``."""

        for span_start, span_end in trim_spans:
            if span_start <= cursor + 0.5 and span_end - max(span_start, cursor) >= trim_min:
                return (span_start, span_end)
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(document: Mapping[str, object]) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
