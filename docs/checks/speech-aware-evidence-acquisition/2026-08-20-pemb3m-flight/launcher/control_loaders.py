"""M2/M3 control-arm loaders (GLAP / CLSP) for the P-EMB-3M flight.

These are the caller-owned loader functions
``rails.local_encoder_client.LocalTransformersEncoderClient``'s own docstring
describes: "the ONE place ``transformers``/``torch`` are ever imported for that
module's own real (non-test) use". Every import here is function-local, so
importing THIS module costs nothing and loads no weights.

Both controls run with the shared venv AS-IS. NOTHING is installed, downloaded
or upgraded: the loaders run with ``HF_HUB_OFFLINE``/``TRANSFORMERS_OFFLINE``
forced on (set by the flight's own env before any import), so a dependency that
is genuinely absent raises ``ImportError`` and
``rails.local_encoder_client.run_import_feasibility_gate`` reports DROPPED-DEPS,
while a model asset that is genuinely absent from the local HF cache raises
loudly instead of silently fetching an unregistered artifact from the network.
CLSP's own remote code hard-requires ``roberta-base`` at construction time
(``CLAP.__init__`` -> ``RobertaTokenizer.from_pretrained("roberta-base")``),
which is why offline-cache presence is a real, checked precondition rather than
an assumption.

Audio decoding is soundfile-first with a librosa fallback -- ffmpeg is a PINNED
ABSENCE on this host and is never installed, and no path here shells out to it.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable, Sequence

GLAP_MODEL_SUBDIR = "models/glap"
CLSP_MODEL_SUBDIR = "models/clsp"

TARGET_SAMPLE_RATE = 16000  # both controls are 16 kHz models (E-1 Mission A / their model cards)


def decode_audio_to_mono_16k(audio_bytes: bytes):
    """Raw container bytes -> a 1-D float32 numpy waveform at 16 kHz, mono.

    soundfile handles the SLURP carrier (flac) and the synthetic gate WAV
    directly; librosa is the documented fallback for anything soundfile cannot
    open (the SAME fallback the buf90 slicing used, for the SAME reason: ffmpeg
    must never be installed on this host)."""

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

    ``trust_remote_code`` is what both control cards require (E-1 Mission A) and
    the code executed is the code ALREADY ON DISK under the pinned model
    directory -- nothing is fetched. An absent python dependency inside that
    remote code surfaces as ``ImportError``, which is precisely the signal
    ``run_import_feasibility_gate`` converts into DROPPED-DEPS."""

    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained(str(model_dir), trust_remote_code=True)
    model = model.eval().to(_device())
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    torch.set_grad_enabled(False)
    return model


def build_glap_client(data_root: Path):
    """GLAP (CONTROL, audio-event TYPE space; dim 1024, E-1 Mission A).

    Text side: ``GlapModel.encode_text([text])`` -- its own NLLB sentencepiece
    tokenizer is resolved from the pinned model directory itself
    (``sentencepiece.source.256000.model``), never downloaded.
    Audio side: ``GlapModel.encode_audio(waveform)`` -- a raw 16 kHz mono
    waveform; the encoder computes its own melspec and chunk-pools internally.
    Both sides are already L2-normalized by the model."""

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
    # and only then moves the ENCODER OUTPUT onto the projection's device
    # (``self.text_proj(sentence_embeddings.to(device))``). That is upstream's
    # own split-device contract: the SONAR text tower stays on CPU while the
    # audio tower runs on the accelerator. A blanket ``.to("cuda")`` breaks it
    # and raises "index is on cpu, different from other tensors on cuda:0" on
    # the very first text embed -- observed live on this host at 11:06:15Z on
    # 2026-08-20, one gate contact spent. Restoring the contract is a DEVICE
    # PLACEMENT choice only: not one byte of the pinned remote code is edited,
    # and the computation is the model's own, unchanged.
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
        model_id="glap",
        expected_dim=GLAP_EMBEDDING_DIM,
        encode_text_fn=encode_text,
        encode_audio_fn=encode_audio,
    )


def build_clsp_client(data_root: Path):
    """CLSP (CONTROL, speaking-STYLE space; dim 512, E-1 Mission A).

    Both sides go through the model's own ``forward``, which is where its
    projection + MLP transform + L2 normalization live; calling the raw encoder
    sub-modules would return an unprojected, unnormalized vector in the wrong
    space. Text-only and audio-only calls are both first-class in that forward
    (each side is guarded by its own ``is not None`` branch)."""

    import torch

    from speech_aware_evidence_acquisition.rails.local_encoder_client import (
        CLSP_EMBEDDING_DIM,
        LocalTransformersEncoderClient,
    )

    model_dir = Path(data_root) / CLSP_MODEL_SUBDIR
    if not (model_dir / "config.json").is_file():
        raise FileNotFoundError(f"CLSP model directory is not present at {model_dir}")
    model = _load_remote_code_model(model_dir)
    device = _device()

    def encode_text(text: str) -> Sequence[float]:
        with torch.no_grad():
            _audio_embedding, text_embedding, _scale = model(audio=None, audio_lens=None, text=[text])
        return text_embedding[0].detach().float().cpu().tolist()

    def encode_audio(audio_bytes: bytes) -> Sequence[float]:
        wave = decode_audio_to_mono_16k(audio_bytes)
        tensor = torch.from_numpy(wave).unsqueeze(0).to(device)
        lengths = torch.tensor([tensor.shape[-1]], device=device)
        with torch.no_grad():
            audio_embedding, _text_embedding, _scale = model(audio=tensor, audio_lens=lengths, text=None)
        return audio_embedding[0].detach().float().cpu().tolist()

    return LocalTransformersEncoderClient(
        model_id="clsp",
        expected_dim=CLSP_EMBEDDING_DIM,
        encode_text_fn=encode_text,
        encode_audio_fn=encode_audio,
    )


CONTROL_BUILDERS: dict[str, Callable[[Path], object]] = {
    "m2-glap-control": build_glap_client,
    "m3-clsp-control": build_clsp_client,
}
CONTROL_MODEL_IDS: dict[str, str] = {"m2-glap-control": "glap", "m3-clsp-control": "clsp"}
