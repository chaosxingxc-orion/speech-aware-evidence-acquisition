"""GLAP in-process loader for the P-EMB-4R flight.

The GLAP half of the archived P-EMB-3M launcher's own ``control_loaders.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-flight/
launcher/control_loaders.py``), carried VERBATIM -- including its
device-placement fix and its soundfile-first / librosa-fallback decoder. CLSP
is deliberately absent: the P-EMB-4R registration documents it as
ENVIRONMENT-GATED and NOT flown (transformers 5.12 incompatibility), so this
flight never even constructs it.

This is the caller-owned loader function
``rails.local_encoder_client.LocalTransformersEncoderClient``'s own docstring
describes: "the ONE place ``transformers``/``torch`` are ever imported for that
module's own real (non-test) use". Every import here is function-local, so
importing THIS module costs nothing and loads no weights.

GLAP runs with the shared venv AS-IS. NOTHING is installed, downloaded or
upgraded: the loader runs with ``HF_HUB_OFFLINE``/``TRANSFORMERS_OFFLINE``
forced on (set by the flight's own env before any import), so a dependency that
is genuinely absent raises ``ImportError`` and
``rails.local_encoder_client.run_import_feasibility_gate`` reports DROPPED-DEPS,
while a model asset that is genuinely absent from the local HF cache raises
loudly instead of silently fetching an unregistered artifact from the network.

Audio decoding is soundfile-first with a librosa fallback -- ffmpeg is a PINNED
ABSENCE on this host and is never installed, and no path here shells out to it.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Sequence

GLAP_MODEL_SUBDIR = "models/glap"
GLAP_MODEL_ID = "glap"

TARGET_SAMPLE_RATE = 16000  # GLAP is a 16 kHz model (E-1 Mission A / its model card)


def decode_audio_to_mono_16k(audio_bytes: bytes):
    """Raw container bytes -> a 1-D float32 numpy waveform at 16 kHz, mono."""

    import numpy as np

    try:
        import soundfile as sf

        data, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
        wave = data.mean(axis=1)
    except Exception:  # noqa: BLE001 -- documented librosa fallback, never ffmpeg
        import librosa

        wave, sample_rate = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
        wave = np.asarray(wave, dtype="float32")

    if sample_rate != TARGET_SAMPLE_RATE:
        import librosa

        wave = librosa.resample(
            np.asarray(wave, dtype="float32"), orig_sr=sample_rate, target_sr=TARGET_SAMPLE_RATE
        )
    wave = np.asarray(wave, dtype="float32").reshape(-1)
    if wave.size == 0:
        raise ValueError("decoded waveform is empty")
    return wave


def _device():
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_remote_code_model(model_dir: Path):
    """``AutoModel.from_pretrained(<local dir>, trust_remote_code=True)``.

    ``trust_remote_code`` is what GLAP's card requires (E-1 Mission A) and the
    code executed is the code ALREADY ON DISK under the pinned model directory
    -- nothing is fetched."""

    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained(str(model_dir), trust_remote_code=True)
    model = model.eval().to(_device())
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    torch.set_grad_enabled(False)
    return model


def build_glap_client(data_root: Path):
    """GLAP (dim 1024, E-1 Mission A).

    Text side: ``GlapModel.encode_text([text])`` -- its own NLLB sentencepiece
    tokenizer is resolved from the pinned model directory itself, never
    downloaded. Audio side: ``GlapModel.encode_audio(waveform)`` -- a raw 16 kHz
    mono waveform; the encoder computes its own melspec and chunk-pools
    internally. Both sides are already L2-normalized by the model."""

    import torch

    from speech_aware_evidence_acquisition.rails.local_encoder_client import (
        GLAP_EMBEDDING_DIM,
        LocalTransformersEncoderClient,
    )

    model_dir = Path(data_root) / GLAP_MODEL_SUBDIR
    if not (model_dir / "config.json").is_file():
        raise FileNotFoundError(f"GLAP model directory is not present at {model_dir}")
    model = _load_remote_code_model(model_dir)
    device = _device()

    # GLAP's own ``encode_text`` builds its token-id and padding-mask tensors
    # with ``device="cpu"`` UNCONDITIONALLY, runs ``self.text_encoder`` on them,
    # and only then moves the ENCODER OUTPUT onto the projection's device. That
    # is upstream's own split-device contract: the SONAR text tower stays on CPU
    # while the audio tower runs on the accelerator. A blanket ``.to("cuda")``
    # breaks it and raises "index is on cpu, different from other tensors on
    # cuda:0" on the very first text embed -- observed live on this host on
    # 2026-08-20 during the P-EMB-3M flight. Restoring the contract is a DEVICE
    # PLACEMENT choice only: not one byte of the pinned remote code is edited.
    if device != "cpu":
        model.text_encoder.to("cpu")

    def encode_text(text: str) -> Sequence[float]:
        with torch.no_grad():
            vector = model.encode_text([text])
        return vector[0].detach().float().cpu().tolist()

    def encode_audio(audio_bytes: bytes) -> Sequence[float]:
        wave = decode_audio_to_mono_16k(audio_bytes)
        tensor = torch.from_numpy(wave).unsqueeze(0).to(device)
        with torch.no_grad():
            vector = model.encode_audio(tensor)
        return vector[0].detach().float().cpu().tolist()

    return LocalTransformersEncoderClient(
        model_id=GLAP_MODEL_ID,
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=encode_text,
        encode_audio_fn=encode_audio,
    )
