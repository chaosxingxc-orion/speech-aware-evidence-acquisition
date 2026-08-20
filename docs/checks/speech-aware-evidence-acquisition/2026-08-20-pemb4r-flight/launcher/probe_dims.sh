#!/usr/bin/env bash
# Offline, model-free: read each embedder GGUF's own declared embedding_length
# from its metadata header. No server, no GPU, zero model contact.
source "$(dirname "$0")/env.sh"
python - <<'PY'
from pathlib import Path
from gguf import GGUFReader

root = Path("/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data")
targets = {
    "lco3": root / "models/lco-embedding-omni-3b-gguf/LCO-Embedding-Omni-3B-Q8_0.gguf",
    "lco7": root / "models/lco-embedding-omni-7b-gguf/LCO-Embedding-Omni-7B-Q8_0.gguf",
    "qw": root / "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf",
}
for key, path in targets.items():
    reader = GGUFReader(str(path))
    fields = reader.fields
    arch = None
    for name in ("general.architecture",):
        if name in fields:
            arch = str(bytes(fields[name].parts[fields[name].data[0]]).decode("utf-8"))
    out = {"arch": arch}
    for name, field in fields.items():
        if name.endswith(".embedding_length") or name.endswith(".block_count") or name == "general.name":
            try:
                value = field.parts[field.data[0]]
                out[name] = value.tolist() if hasattr(value, "tolist") else value
            except Exception as error:
                out[name] = f"<{error}>"
    print(key, path.name, out, flush=True)
PY
