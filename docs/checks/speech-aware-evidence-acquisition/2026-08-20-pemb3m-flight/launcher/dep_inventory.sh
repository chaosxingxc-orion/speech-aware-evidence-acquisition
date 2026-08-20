#!/usr/bin/env bash
# Zero-contact dependency inventory for the M2/M3 control loaders.
# Imports libraries only -- loads NO model weights, embeds NOTHING.
source "$(dirname "$0")/env.sh"
python - <<'PY'
import importlib, os
from pathlib import Path

for name in ("torch", "torchaudio", "transformers", "einops", "sentencepiece",
             "huggingface_hub", "soundfile", "librosa", "numpy", "scipy"):
    try:
        m = importlib.import_module(name)
        print(f"{name:16s} OK   {getattr(m,'__version__','?')}")
    except ImportError as e:
        print(f"{name:16s} MISSING  ({e})")

import torch
print("torch.cuda.is_available:", torch.cuda.is_available())
print("torch.version.cuda:", torch.version.cuda)

# roberta-base availability offline (CLSP's CLAP.__init__ hard-requires it)
hub = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache" / "huggingface")))
print("HF_HOME candidate:", hub, "exists:", hub.exists())
for base in (hub / "hub", Path.home() / ".cache" / "huggingface" / "hub"):
    if base.exists():
        entries = sorted(p.name for p in base.iterdir())
        print(f"  {base}: {entries[:40]}")
print("HF_HUB_OFFLINE:", os.environ.get("HF_HUB_OFFLINE"))
print("TRANSFORMERS_OFFLINE:", os.environ.get("TRANSFORMERS_OFFLINE"))
PY
