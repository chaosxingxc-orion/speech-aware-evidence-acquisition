#!/usr/bin/env python3
"""Pin the Thinking GGUF for the 266-E bare-core read and write its model fragments and runtime receipts.

Owner decision 266-E (2026-10-11) admits ``qwen3-omni-30b-a3b-thinking-gguf-q4km`` for ONE bare-core read on TRAIN Fold B. The
umbrella lock (``docs/datasets.lock.json``) is the single live source of the model's identity; this module never copies a hash
into prose. It reads the per-file SHA-256 from the local receipts the downloader left (``/home/chao/thinking-gguf-*.sha256``),
proves that the same two hashes appear in the lock entry's ``revision`` text with the same byte sizes, and REFUSES to write
anything if a hash is absent or differs. The fragment and the runtime receipts then carry the pins exactly as the Instruct ones
do (``gguf_files`` of ``docs/receipts/runtime-q4km-mmproj-free.json``).

Model-free: reads two small receipt files and the lock; never opens a GGUF, never starts a process.

    python -B scripts/flights/direct/direct_fb_pins.py --write
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

LOCK_KEY = "qwen3-omni-30b-a3b-thinking-gguf-q4km"
UMBRELLA_LOCK_WSL = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
UMBRELLA_LOCK_WIN = Path("D:/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
LOCAL_MAIN_RECEIPT = Path("/home/chao/thinking-gguf-main.sha256")
LOCAL_MMPROJ_RECEIPT = Path("/home/chao/thinking-gguf-mmproj.sha256")

MAIN_NAME = "Qwen3-Omni-30B-A3B-Thinking-Q4_K_M.gguf"
MMPROJ_NAME = "mmproj-Qwen3-Omni-30B-A3B-Thinking-bf16.gguf"
MODEL_SUBDIR = "models/qwen3-omni-30b-a3b-thinking-gguf-q4km"
MAIN_BYTES = 18557053248
MMPROJ_BYTES = 2207465664

SERVING_FRAGMENT = "q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max2048-v1"
PREPROCESS_FRAGMENT = "q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1"
SERVING_RECEIPT = "docs/receipts/runtime-q4km-thinking-mmproj-free.json"
PREPROCESS_RECEIPT = "docs/receipts/runtime-q4km-thinking-preprocess.json"
INSTRUCT_SERVING_RECEIPT = "docs/receipts/runtime-q4km-mmproj-free.json"
INSTRUCT_PREPROCESS_RECEIPT = "docs/receipts/runtime-q4km-preprocess.json"
INSTRUCT_SERVING_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
INSTRUCT_PREPROCESS_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar"

THINKING_PACKET_ROOT = "/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6"
THINKING_LEGACY_CACHE = "/home/chao/feat-cache/slurp-thinking-q4km"
#: The completion cap of the Thinking geometry (justified in the package README: 24,576-token slots, direct-only prompt about 2.3k).
THINKING_MAX_TOKENS = 2048
#: The server flags that keep reasoning out of ``message.content`` on the pinned featcache build (tools/server/README.md).
REASONING_ARGS = ["--reasoning-format", "deepseek"]

SHA = re.compile(r"[0-9a-f]{64}")


class PinError(SystemExit):
    """Raised (as a SystemExit) when a pin is absent or disagrees; nothing is written."""


def read_local_receipt(path: Path) -> str:
    try:
        first = Path(path).read_text(encoding="utf-8").split()[0]
    except (OSError, IndexError, UnicodeError) as error:
        raise PinError(f"local hash receipt {path} is unreadable: {error}") from error
    if SHA.fullmatch(first) is None:
        raise PinError(f"local hash receipt {path} does not start with a 64-hex sha256")
    return first


def lock_entry(lock_path: Path) -> dict:
    document = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    for entry in document.get("models", ()):
        if entry.get("name") == LOCK_KEY:
            return entry
    raise PinError(f"lock {lock_path} has no model entry {LOCK_KEY}")


def resolve_pins(*, lock_path: Path, main_receipt: Path = LOCAL_MAIN_RECEIPT, mmproj_receipt: Path = LOCAL_MMPROJ_RECEIPT) -> dict:
    """The two pinned files: each hash read from its local receipt and PROVEN to appear in the lock entry's ``revision`` text."""

    entry = lock_entry(lock_path)
    if entry.get("status") != "COMPLETE":
        raise PinError(f"lock entry {LOCK_KEY} is {entry.get('status')!r}, not COMPLETE")
    revision = str(entry.get("revision", ""))
    pins = {}
    for label, name, receipt, size in (("main", MAIN_NAME, main_receipt, MAIN_BYTES), ("mmproj", MMPROJ_NAME, mmproj_receipt, MMPROJ_BYTES)):
        sha = read_local_receipt(receipt)
        if f"{name} {sha} ({size} bytes)" not in revision:
            raise PinError(
                f"{label}: local hash {sha[:12]}... for {name} does not match the lock entry's pinned file hash and size; "
                "refusing to write any fragment"
            )
        pins[label] = {"bytes": size, "path": f"{MODEL_SUBDIR}/{name}", "sha256": sha}
    return pins


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def build_receipts(pins: dict, repo_root: Path = REPO_ROOT) -> dict[str, dict]:
    """Thinking runtime receipts: the Instruct ones with ONLY the model files (and the lock key) replaced."""

    serving = _json(repo_root / INSTRUCT_SERVING_RECEIPT)
    serving["model_lock_key"] = LOCK_KEY
    serving["gguf_files"] = [pins["main"]]
    preprocess = _json(repo_root / INSTRUCT_PREPROCESS_RECEIPT)
    preprocess["model_lock_key"] = LOCK_KEY
    preprocess["gguf_files"] = [pins["main"], pins["mmproj"]]
    return {SERVING_RECEIPT: serving, PREPROCESS_RECEIPT: preprocess}


def _swap(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise PinError(f"expected exactly one {old!r} in the Instruct fragment, found {text.count(old)}")
    return text.replace(old, new)


GEOMETRY_BASIS = (
    "Same geometry family as the resident Instruct session: four decoder-only 24576-token slots under c98304 np4, q8_0 KV, "
    "mmproj-free decode over pre-materialised speech packets. ONLY the model (the Thinking GGUF), its own packet root (the "
    "audio-encoder tensors of the two mmproj files differ, so the Instruct packets are not valid input), the completion cap "
    "(2048 tokens: a thinking completion is long, the direct-only prompt is about 2.3k tokens, so 2.3k + 2048 is 18 percent of "
    "a 24576-token slot) and the reasoning flag (--reasoning-format deepseek: thoughts go to message.reasoning_content, which "
    "the transport never reads, and never into message.content) differ. Owner decision 266-E admits this model for one "
    "bare-core read and nothing else."
)

PREPROCESS_BASIS = (
    "IDENTICAL to configs/model/" + INSTRUCT_PREPROCESS_FRAGMENT + ".json (the CPU-only packet-preparation sidecar of the SLURP "
    "folds) except the model (the Thinking decoder AND its own bf16 mmproj, pinned by " + PREPROCESS_RECEIPT + ") and the legacy "
    "feature-cache directory. HELD: the packet-preparation driver scripts/slurp_evo_fold_preprocess.py is wired to the Instruct "
    "runtime receipt and packet root, so an encoder pass over TRAIN Fold B with this fragment needs its own driver variant, root "
    "lease, registration and owner authorisation; none is given here."
)


def build_fragments(pins: dict, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    """The Thinking serving fragment and the packet-preparation sidecar fragment, as TEXT: the Instruct fragments with exactly the
    registered substitutions (model lock key, runtime receipt, completion cap, reasoning flags, packet root and decoder pin), so
    every other byte equals the Instruct fragment's."""

    text = (repo_root / "configs/model" / f"{INSTRUCT_SERVING_FRAGMENT}.json").read_text(encoding="utf-8")
    text = _swap(text, '"model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km"', f'"model_lock_key": "{LOCK_KEY}"')
    text = _swap(text, '"runtime_receipt": "receipts/runtime-q4km-mmproj-free.json"',
                 '"runtime_receipt": "' + SERVING_RECEIPT.removeprefix("docs/") + '"')
    text = _swap(text, '"--slot-prompt-similarity", "0"\n  ]', '"--slot-prompt-similarity", "0",\n    "--reasoning-format", "deepseek"\n  ]')
    text = _swap(text, '"max_tokens": 512,', f'"max_tokens": {THINKING_MAX_TOKENS},')
    root_line = '"/home/chao/feat-cache/slurp-q4km-packets-04ccc72a"'
    if text.count(root_line) != 2:
        raise PinError("expected the Instruct packet root twice (speech_feature_root and server_env)")
    text = text.replace(root_line, f'"{THINKING_PACKET_ROOT}"')
    text = _swap(text, '"LLAMA_SPEECH_DECODER_SHA256": "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"',
                 '"LLAMA_SPEECH_DECODER_SHA256": "' + pins["main"]["sha256"] + '"')
    cut = text.index('  "geometry_basis"')
    text = text[:cut] + '  "reasoning_content_guard": "refuse-think-marker-in-content",\n  "geometry_basis": ' + json.dumps(GEOMETRY_BASIS) + "\n}\n"
    sidecar = (repo_root / "configs/model" / f"{INSTRUCT_PREPROCESS_FRAGMENT}.json").read_text(encoding="utf-8")
    sidecar = _swap(sidecar, '"model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km"', f'"model_lock_key": "{LOCK_KEY}"')
    sidecar = _swap(sidecar, '"runtime_receipt": "receipts/runtime-q4km-preprocess.json"',
                    '"runtime_receipt": "' + PREPROCESS_RECEIPT.removeprefix("docs/") + '"')
    sidecar = _swap(sidecar, '"LLAMA_MTMD_FEAT_CACHE_DIR": "/home/chao/feat-cache/slurp-q4km"',
                    f'"LLAMA_MTMD_FEAT_CACHE_DIR": "{THINKING_LEGACY_CACHE}"')
    cut = sidecar.rindex("\n}")
    sidecar = sidecar[:cut] + ',\n  "variant_basis": ' + json.dumps(PREPROCESS_BASIS) + "\n}\n"
    for body in (text, sidecar):
        json.loads(body)
    return {f"configs/model/{SERVING_FRAGMENT}.json": text, f"configs/model/{PREPROCESS_FRAGMENT}.json": sidecar}


def verify_fragment_pins(fragment: dict, receipt: dict, pins: dict) -> list[str]:
    """Findings (empty = pinned) for a Thinking serving fragment and its runtime receipt against the resolved pins."""

    findings: list[str] = []
    if fragment.get("model_lock_key") != LOCK_KEY:
        findings.append("model_lock_key is not the Thinking lock key")
    files = receipt.get("gguf_files")
    if not isinstance(files, list) or not files:
        findings.append("runtime receipt carries no gguf_files (unpinned)")
    elif files[0] != pins["main"]:
        findings.append("runtime receipt main GGUF path/bytes/sha256 differ from the lock-verified pin")
    if (fragment.get("server_env") or {}).get("LLAMA_SPEECH_DECODER_SHA256") != pins["main"]["sha256"]:
        findings.append("LLAMA_SPEECH_DECODER_SHA256 is not the pinned main-file sha256")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--lock-path", type=Path, default=None)
    args = parser.parse_args(argv)
    lock = args.lock_path or (UMBRELLA_LOCK_WSL if UMBRELLA_LOCK_WSL.exists() else UMBRELLA_LOCK_WIN)
    pins = resolve_pins(lock_path=lock)
    outputs = {**{k: _dump(v) for k, v in build_receipts(pins).items()}, **build_fragments(pins)}
    for relpath, body in outputs.items():
        if args.write:
            target = REPO_ROOT / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            io.open(target, "w", encoding="utf-8", newline="").write(body)
        print(("wrote " if args.write else "would write ") + relpath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
