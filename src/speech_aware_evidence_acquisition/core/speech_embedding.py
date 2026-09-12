"""Shared pinned Omni-Embed recipe and exact source-frame audio observation."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from .preparation import hash_stable_file

DIMS = 2048
SAMPLE_RATE_HZ = 16000


class SpeechEmbeddingError(ValueError):
    """Refuse an unbound, truncated or malformed embedding input."""


def read_audio_span(source):
    """Read exact original frames and apply the established mono/resample recipe."""
    import soundfile

    path = Path(source["media_path"])
    before = path.stat()
    fingerprint = (before.st_ino, before.st_size, before.st_mtime_ns)
    bound = source.get("verified_fingerprint")
    if bound is not None and tuple(bound) != fingerprint:
        raise SpeechEmbeddingError("speech source changed after hash verification")
    if bound is None and source.get("audio_sha256") is not None:
        _size, sha, _fingerprint = hash_stable_file(path, "speech embedding input")
        if sha != source["audio_sha256"]:
            raise SpeechEmbeddingError("speech source hash changed")
    start, end = source["start_frame"], source["end_frame"]
    with soundfile.SoundFile(path) as audio:
        if (
            audio.frames != source["source_frames"]
            or audio.samplerate != source["source_sample_rate_hz"]
            or not 0 <= start < end <= audio.frames
        ):
            raise SpeechEmbeddingError("speech source frame geometry changed")
        audio.seek(start)
        wave = audio.read(end - start, dtype="float32", always_2d=False)
        rate = audio.samplerate
    after = path.stat()
    if (after.st_ino, after.st_size, after.st_mtime_ns) != fingerprint:
        raise SpeechEmbeddingError("speech source changed during decoding")
    array = np.asarray(wave, dtype=np.float32)
    if array.shape[0] != end - start:
        raise SpeechEmbeddingError("speech decoder omitted source frames")
    if array.ndim > 1:
        array = array.mean(axis=1).astype(np.float32)
    if rate != SAMPLE_RATE_HZ:
        import librosa

        array = librosa.resample(array, orig_sr=rate, target_sr=SAMPLE_RATE_HZ).astype(
            np.float32
        )
    if not np.isfinite(array).all():
        raise SpeechEmbeddingError("speech waveform is not finite")
    return array


def load_stack(model_dir: Path, *, local_files_only: bool = False):
    """The three shipped modules, reproduced through plain ``transformers``."""

    import torch
    from transformers import AutoModel, AutoProcessor

    if "sentence_transformers" in sys.modules:  # pragma: no cover - defensive
        raise SystemExit("sentence_transformers must not be imported in this process")
    template = (
        model_dir / "additional_chat_templates/sentence_transformers.jinja"
    ).read_text(encoding="utf-8")
    pooling = json.loads(
        (model_dir / "1_Pooling/config.json").read_text(encoding="utf-8")
    )
    if pooling.get("pooling_mode") != "mean" or not pooling.get("include_prompt"):
        raise SystemExit(f"unexpected pooling config {pooling!r}")
    if int(pooling.get("embedding_dimension", 0)) != DIMS:
        raise SystemExit(f"unexpected embedding dimension {pooling!r}")
    processor = AutoProcessor.from_pretrained(
        str(model_dir), trust_remote_code=True, local_files_only=local_files_only
    )
    model = AutoModel.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        local_files_only=local_files_only,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    model = model.to("cuda").eval()
    return processor, model, template


def render(processor, template: str, content: list[dict]) -> str:
    return processor.apply_chat_template(
        [{"role": "user", "content": content}],
        chat_template=template,
        tokenize=False,
        add_generation_prompt=False,
    )


def encode(
    processor,
    model,
    texts: list[str],
    audio: list | None,
    *,
    device: str = "cuda",
    max_audio_samples: int | None = None,
    require_complete_audio: bool = False,
    max_sequence_tokens: int | None = None,
    forward_event=None,
):
    """One forward pass -> L2-normalised mean-pooled vectors."""

    import torch

    if audio is not None:
        if max_audio_samples is not None and (len(audio) != 1 or len(texts) != 1):
            raise SpeechEmbeddingError(
                "bounded speech embedding requires one audio per request"
            )
        for wave in audio:
            array = np.asarray(wave)
            if array.ndim != 1 or not array.size or not np.isfinite(array).all():
                raise SpeechEmbeddingError("speech waveform must be finite mono audio")
            if max_audio_samples is not None and len(array) > max_audio_samples:
                raise SpeechEmbeddingError(
                    "speech waveform exceeds the registered input bound"
                )
    kwargs: dict[str, object] = {"text": texts, "return_tensors": "pt", "padding": True}
    if audio is not None:
        kwargs["audio"] = audio
        kwargs["sampling_rate"] = SAMPLE_RATE_HZ
        if require_complete_audio:
            if type(max_audio_samples) is not int or max_audio_samples <= 0:
                raise SpeechEmbeddingError(
                    "complete audio requires an explicit sample bound"
                )
            # Processor defaults can propagate a text-token max_length into
            # audio samples. Bind this modality explicitly; never truncate it.
            kwargs["audio_kwargs"] = {
                "max_length": max_audio_samples,
                "truncation": False,
            }
    inputs = processor(**kwargs)
    if require_complete_audio and audio is not None:
        mask = inputs.get("feature_attention_mask")
        hop = int(processor.feature_extractor.hop_length)
        expected = [math.ceil(len(wave) / hop) for wave in audio]
        if mask is None or mask.sum(-1).tolist() != expected:
            raise SpeechEmbeddingError(
                "audio processor did not preserve complete frame coverage"
            )
    if (
        max_sequence_tokens is not None
        and inputs["attention_mask"].shape[-1] > max_sequence_tokens
    ):
        raise SpeechEmbeddingError(
            "embedding sequence exceeds its registered token bound"
        )
    inputs = {
        key: (value.to(device) if hasattr(value, "to") else value)
        for key, value in inputs.items()
    }
    if forward_event is not None:
        forward_event("encoder_forward_started")
    with torch.inference_mode():
        outputs = model(**inputs, output_hidden_states=True, return_dict=True)
    hidden = outputs.hidden_states[-1].float()
    mask = inputs["attention_mask"].to(hidden.device).unsqueeze(-1).float()
    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
    pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
    result = [tuple(float(v) for v in row) for row in pooled.cpu()]
    if forward_event is not None:
        forward_event("encoder_forward_finished")
    return result
