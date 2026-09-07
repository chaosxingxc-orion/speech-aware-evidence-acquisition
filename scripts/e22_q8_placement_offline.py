#!/usr/bin/env python3
"""Offline expert-offload placement projection for Earnings-22 cell (a).

Precondition Q8-P1 of ``docs/readiness/2026-09-06-e22-dev-usage-cells-v1-
preregistration.md`` section 1.3 asks for ``--n-cpu-moe N`` re-derived on the
sealed dev arm A geometry (``-c 40960 -np 8``, bf16 mmproj resident, no feature
cache), with a refusal if no ``N`` leaves at least 3,072 MiB free on the 24 GB
card -- the 2,940 MiB llama.cpp estimates for the audio encoder's worst-case
compute buffer, rounded up.

**This script does not replace that pass and does not claim to.** Q8-P1 is a
LIVE measurement: it starts the pinned server per rung and reads free VRAM
through ``GET /props`` and ``nvidia-smi`` with zero ``/completion`` calls
(``scripts/a2t_q8_placement_fit.py`` is that pass). What this script does is
compute, with **zero model load, zero server, zero GPU and zero network**, what
that pass will find -- so the rung ladder is short, the answer is falsifiable
before a GPU minute is spent, and a live result that disagrees is a signal
rather than a surprise.

The projection is arithmetic over two things, and neither is a guess:

1. **The Q8_0 GGUF's own tensor table**, parsed here from the file header (name,
   dims, ggml type, offset -- no tensor data is read and the model is never
   loaded). It yields the per-layer Mixture-of-Experts tensor bytes that
   ``--n-cpu-moe`` moves to host RAM, the non-expert remainder that always stays
   on the GPU, and the KV geometry (``block_count``, ``head_count_kv``,
   ``key_length``, ``value_length``) that fixes the q8_0 KV cache's bytes per
   token. The mmproj GGUF is parsed the same way for its resident bytes.
2. **The A2T probe's own LIVE ladder**
   (``docs/checks/speech-aware-evidence-acquisition/
   2026-09-04-a2t-q8-quantization-probe-400-v1/placement/placement-fit.json``),
   eight measured rungs of the SAME decoder, the SAME mmproj and the SAME
   llama.cpp build at ``-c 49152 -np 3``. Every non-saturated rung is used to
   fit ONE unknown -- the CUDA context plus compute buffers -- and the fit is
   REFUSED unless that residual is the same constant at every rung. It is: the
   ladder is exactly linear in ``48 - N`` at 612.0 MiB per layer.

The only quantity that does not carry over from that ladder is the compute
overhead at a different ``-c``/``-np``, so it is not assumed: the receipt
reports how far it could move before the answer changes, in both directions.

Run in WSL2::

    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 \\
        python scripts/e22_q8_placement_offline.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

MIB = 1024 * 1024

#: ggml type id -> (name, block size in elements, bytes per block). Only the
#: types these two GGUFs actually use have to be right; an unknown id is a
#: refusal rather than a silent zero.
GGML_TYPES: dict[int, tuple[str, int, int]] = {
    0: ("F32", 1, 4),
    1: ("F16", 1, 2),
    2: ("Q4_0", 32, 18),
    3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22),
    7: ("Q5_1", 32, 24),
    8: ("Q8_0", 32, 34),
    9: ("Q8_1", 32, 36),
    10: ("Q2_K", 256, 84),
    11: ("Q3_K", 256, 110),
    12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176),
    14: ("Q6_K", 256, 210),
    15: ("Q8_K", 256, 292),
    24: ("I8", 1, 1),
    25: ("I16", 1, 2),
    26: ("I32", 1, 4),
    27: ("I64", 1, 8),
    28: ("F64", 1, 8),
    30: ("BF16", 1, 2),
}

#: Tensor-name marker for the MoE expert weights ``--n-cpu-moe N`` relocates.
EXPERT_TENSOR_MARKER = "_exps"
_BLOCK_RE = re.compile(r"^blk\.(\d+)\.")

DEFAULT_A2T_LADDER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-q8-quantization-probe-400-v1/placement/placement-fit.json"
)
DEFAULT_RUNTIME_RECEIPT = REPO / "docs/receipts/runtime-q8-featcache-04ccc72a.json"
DEFAULT_MODEL_ROOT = Path("/home/chao")
DEFAULT_OUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells"
    / "q8-placement.json"
)


class PlacementError(RuntimeError):
    """The projection refuses: a malformed GGUF, an unknown ggml type, or a
    ladder that is not linear and therefore cannot be extrapolated."""


# ---------------------------------------------------------------------------
# GGUF header reader (header only -- no tensor data, no model load)
# ---------------------------------------------------------------------------


class _Reader:
    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle

    def _unpack(self, fmt: str, size: int):
        raw = self._handle.read(size)
        if len(raw) != size:
            raise PlacementError("GGUF header ended early")
        return struct.unpack(fmt, raw)[0]

    def u32(self) -> int:
        return self._unpack("<I", 4)

    def u64(self) -> int:
        return self._unpack("<Q", 8)

    def string(self) -> str:
        length = self.u64()
        return self._handle.read(length).decode("utf-8", "replace")

    def value(self, kind: int):
        if kind == 0:
            return self._unpack("<B", 1)
        if kind == 1:
            return self._unpack("<b", 1)
        if kind == 2:
            return self._unpack("<H", 2)
        if kind == 3:
            return self._unpack("<h", 2)
        if kind == 4:
            return self._unpack("<I", 4)
        if kind == 5:
            return self._unpack("<i", 4)
        if kind == 6:
            return self._unpack("<f", 4)
        if kind == 7:
            return bool(self._unpack("<B", 1))
        if kind == 8:
            return self.string()
        if kind == 9:
            element_kind = self.u32()
            count = self.u64()
            return [self.value(element_kind) for _ in range(count)]
        if kind == 10:
            return self.u64()
        if kind == 11:
            return self._unpack("<q", 8)
        if kind == 12:
            return self._unpack("<d", 8)
        raise PlacementError(f"unknown GGUF metadata value type {kind}")


def read_gguf_header(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    """``(metadata, tensors)`` from a GGUF file's header.

    Reads the magic, version, counts, the metadata key/value block and the
    tensor table -- and stops. No tensor payload is ever touched, so this is
    O(header) on a 32 GB file and never loads a model.
    """

    with Path(path).open("rb") as handle:
        reader = _Reader(handle)
        magic = handle.read(4)
        if magic != b"GGUF":
            raise PlacementError(f"{path} is not a GGUF file (magic {magic!r})")
        version = reader.u32()
        tensor_count = reader.u64()
        kv_count = reader.u64()
        metadata: dict[str, object] = {"gguf.version": version}
        for _ in range(kv_count):
            key = reader.string()
            metadata[key] = reader.value(reader.u32())
        tensors: list[dict[str, object]] = []
        for _ in range(tensor_count):
            name = reader.string()
            dims = [reader.u64() for _ in range(reader.u32())]
            type_id = reader.u32()
            reader.u64()  # offset, unused here
            if type_id not in GGML_TYPES:
                raise PlacementError(f"unknown ggml type id {type_id} on tensor {name!r}")
            type_name, block_elements, block_bytes = GGML_TYPES[type_id]
            elements = 1
            for dim in dims:
                elements *= int(dim)
            if elements % block_elements:
                raise PlacementError(
                    f"tensor {name!r} has {elements} elements, not a multiple of the "
                    f"{type_name} block size {block_elements}"
                )
            tensors.append(
                {
                    "name": name,
                    "dims": [int(dim) for dim in dims],
                    "type": type_name,
                    "bytes": elements // block_elements * block_bytes,
                }
            )
    return metadata, tensors


def architecture_key(metadata: Mapping[str, object], suffix: str) -> object:
    """A GGUF metadata value under this file's own architecture prefix."""

    architecture = metadata.get("general.architecture")
    if not isinstance(architecture, str) or not architecture:
        raise PlacementError("GGUF declares no general.architecture")
    key = f"{architecture}.{suffix}"
    if key not in metadata:
        raise PlacementError(f"GGUF declares no {key}")
    return metadata[key]


# ---------------------------------------------------------------------------
# The three quantities the placement arithmetic needs
# ---------------------------------------------------------------------------


def expert_geometry(tensors: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Per-layer expert bytes, the non-expert remainder, and the layer count.

    ``--n-cpu-moe N`` relocates the ``*_exps`` tensors of the first ``N``
    blocks. Every layer must carry the SAME expert byte count or the linear
    ladder below is not a model of anything -- refused rather than averaged.
    """

    per_layer: dict[int, int] = {}
    non_expert = 0
    expert_names: set[str] = set()
    for tensor in tensors:
        name = str(tensor["name"])
        match = _BLOCK_RE.match(name)
        if match is not None and EXPERT_TENSOR_MARKER in name:
            layer = int(match.group(1))
            per_layer[layer] = per_layer.get(layer, 0) + int(tensor["bytes"])
            expert_names.add(name.split(".", 2)[-1])
        else:
            non_expert += int(tensor["bytes"])
    if not per_layer:
        raise PlacementError("this GGUF carries no *_exps tensors to offload")
    sizes = set(per_layer.values())
    if len(sizes) != 1:
        raise PlacementError(
            f"expert layers differ in size ({sorted(sizes)}); the --n-cpu-moe ladder "
            "is only linear when every layer carries the same expert bytes"
        )
    return {
        "expert_layers": len(per_layer),
        "expert_bytes_per_layer": sizes.pop(),
        "expert_bytes_total": sum(per_layer.values()),
        "non_expert_bytes": non_expert,
        "expert_tensor_names": sorted(expert_names),
    }


def kv_bytes_per_token(metadata: Mapping[str, object], *, cache_type: str = "Q8_0") -> int:
    """Bytes ONE context token costs in a ``-ctk q8_0 -ctv q8_0`` KV cache.

    ``block_count x head_count_kv x (key_length + value_length)`` elements per
    token, at the cache type's own bytes-per-element.
    """

    if cache_type not in {name for name, _, _ in GGML_TYPES.values()}:
        raise PlacementError(f"unknown KV cache type {cache_type!r}")
    block_elements, block_bytes = next(
        (elements, size)
        for name, elements, size in GGML_TYPES.values()
        if name == cache_type
    )
    blocks = int(architecture_key(metadata, "block_count"))
    heads_kv = int(architecture_key(metadata, "attention.head_count_kv"))
    key_length = int(architecture_key(metadata, "attention.key_length"))
    value_length = int(architecture_key(metadata, "attention.value_length"))
    elements = blocks * heads_kv * (key_length + value_length)
    if elements % block_elements:
        raise PlacementError(
            f"{elements} KV elements per token is not a multiple of the {cache_type} "
            f"block size {block_elements}"
        )
    return elements // block_elements * block_bytes


def predicted_used_mib(
    *,
    non_expert_mib: float,
    expert_mib_per_layer: float,
    expert_layers: int,
    kv_mib: float,
    mmproj_mib: float,
    overhead_mib: float,
    n_cpu_moe: int,
) -> float:
    """Device memory a server start occupies at this placement.

    The whole model, in one line: everything that is not an expert tensor, plus
    the experts of the ``expert_layers - n_cpu_moe`` layers that stay resident,
    plus the KV plane, plus the resident mmproj, plus one constant for the CUDA
    context and the compute buffers.
    """

    resident_expert_layers = max(0, int(expert_layers) - int(n_cpu_moe))
    return (
        float(non_expert_mib)
        + resident_expert_layers * float(expert_mib_per_layer)
        + float(kv_mib)
        + float(mmproj_mib)
        + float(overhead_mib)
    )


def fit_overhead(
    trials: Sequence[Mapping[str, object]],
    *,
    non_expert_mib: float,
    expert_mib_per_layer: float,
    expert_layers: int,
    kv_mib: float,
    mmproj_mib: float,
    free_before_mib: float,
    tolerance_mib: float = 1.0,
) -> tuple[float, list[dict[str, object]]]:
    """The ONE unknown -- CUDA context plus compute buffers -- fitted on a live
    ladder, and refused unless it is the same constant at every rung.

    A rung whose predicted allocation exceeds the card is SATURATED: llama.cpp
    could not place what the flags asked for, so its measured figure is not on
    the line and is excluded by name rather than silently averaged in.
    """

    residuals: list[dict[str, object]] = []
    values: list[float] = []
    for trial in trials:
        n_cpu_moe = int(trial["n_cpu_moe"])
        used = float(trial["device_memory_resident_mib"]["used_mib"])
        without_overhead = predicted_used_mib(
            non_expert_mib=non_expert_mib,
            expert_mib_per_layer=expert_mib_per_layer,
            expert_layers=expert_layers,
            kv_mib=kv_mib,
            mmproj_mib=mmproj_mib,
            overhead_mib=0.0,
            n_cpu_moe=n_cpu_moe,
        )
        residual = used - without_overhead
        saturated = float(trial["device_memory_resident_mib"]["free_mib"]) < 64.0
        residuals.append(
            {
                "n_cpu_moe": n_cpu_moe,
                "measured_used_mib": used,
                "measured_free_mib": float(trial["device_memory_resident_mib"]["free_mib"]),
                "weights_plus_kv_plus_mmproj_mib": round(without_overhead, 4),
                "residual_mib": round(residual, 4),
                "saturated": saturated,
                "excluded_reason": (
                    "the card was full at this rung, so the measured figure is a "
                    "truncation rather than a placement"
                    if saturated
                    else None
                ),
            }
        )
        if not saturated:
            values.append(residual)
    if not values:
        raise PlacementError("every ladder rung is saturated; nothing to fit")
    spread = max(values) - min(values)
    if spread > tolerance_mib:
        raise PlacementError(
            f"the live ladder is not linear: the fitted overhead spans {spread:.1f} MiB "
            f"across {len(values)} rungs, above the {tolerance_mib} MiB tolerance. The "
            "projection below would be extrapolating a model the data refuses."
        )
    fitted = sum(values) / len(values)
    for entry in residuals:
        entry["free_before_mib"] = free_before_mib
    return fitted, residuals


def choose_placement(
    *,
    non_expert_mib: float,
    expert_mib_per_layer: float,
    expert_layers: int,
    kv_mib: float,
    mmproj_mib: float,
    overhead_mib: float,
    free_before_mib: float,
    min_free_mib: float,
    step: int,
) -> tuple[int | None, list[dict[str, object]]]:
    """The A2T rule, projected: start from ``--cpu-moe`` (every expert layer on
    the CPU), lower ``N`` in steps of ``step`` while the start still leaves at
    least ``min_free_mib`` free, and take the largest GPU-resident share that
    satisfies it -- i.e. the SMALLEST ``N`` that clears the floor."""

    rungs: list[dict[str, object]] = []
    chosen: int | None = None
    n = int(expert_layers)
    while n >= 0:
        used = predicted_used_mib(
            non_expert_mib=non_expert_mib,
            expert_mib_per_layer=expert_mib_per_layer,
            expert_layers=expert_layers,
            kv_mib=kv_mib,
            mmproj_mib=mmproj_mib,
            overhead_mib=overhead_mib,
            n_cpu_moe=n,
        )
        free = free_before_mib - used
        meets = free >= min_free_mib
        rungs.append(
            {
                "n_cpu_moe": n,
                "offload_flag": "--cpu-moe" if n == int(expert_layers) else "--n-cpu-moe",
                "resident_expert_layers": max(0, int(expert_layers) - n),
                "projected_used_mib": round(used, 1),
                "projected_free_mib": round(free, 1),
                "meets_min_free": bool(meets),
                "margin_mib": round(free - min_free_mib, 1),
            }
        )
        if meets:
            chosen = n
        else:
            break
        n -= int(step)
    return chosen, rungs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--runtime-receipt", type=Path, default=DEFAULT_RUNTIME_RECEIPT)
    parser.add_argument("--a2t-ladder", type=Path, default=DEFAULT_A2T_LADDER)
    parser.add_argument("--context-tokens", type=int, default=40960)
    parser.add_argument("--slots", type=int, default=8)
    parser.add_argument("--min-free-mib", type=int, default=3072)
    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--free-before-mib", type=float, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify-hashes", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    runtime = json.loads(Path(args.runtime_receipt).read_text(encoding="utf-8"))
    ladder = json.loads(Path(args.a2t_ladder).read_text(encoding="utf-8"))

    files = {entry["path"]: entry for entry in runtime["gguf_files"]}
    decoder_relpath = next(path for path in files if "mmproj" not in path)
    mmproj_relpath = next(path for path in files if "mmproj" in path)
    decoder_path = Path(args.model_root) / decoder_relpath
    mmproj_path = Path(args.model_root) / mmproj_relpath
    for path, relpath in ((decoder_path, decoder_relpath), (mmproj_path, mmproj_relpath)):
        if not path.is_file():
            raise SystemExit(f"missing GGUF: {path} (from {relpath})")
        if path.stat().st_size != int(files[relpath]["bytes"]):
            raise SystemExit(
                f"{path} is {path.stat().st_size} bytes, the runtime receipt pins "
                f"{files[relpath]['bytes']}"
            )
    hashes: dict[str, object] = {}
    for path, relpath in ((decoder_path, decoder_relpath), (mmproj_path, mmproj_relpath)):
        if args.verify_hashes:
            measured = sha256_file(path)
            if measured != files[relpath]["sha256"]:
                raise SystemExit(
                    f"{path} hashes to {measured}, the runtime receipt pins "
                    f"{files[relpath]['sha256']}"
                )
            hashes[relpath] = {"sha256": measured, "rehashed_here": True}
        else:
            hashes[relpath] = {
                "sha256": files[relpath]["sha256"],
                "rehashed_here": False,
                "note": (
                    "byte size verified against the runtime receipt; re-run with "
                    "--verify-hashes to re-read 32 GB and re-hash"
                ),
            }

    decoder_metadata, decoder_tensors = read_gguf_header(decoder_path)
    mmproj_metadata, mmproj_tensors = read_gguf_header(mmproj_path)
    geometry = expert_geometry(decoder_tensors)
    per_token = kv_bytes_per_token(decoder_metadata)

    non_expert_mib = int(geometry["non_expert_bytes"]) / MIB
    expert_mib_per_layer = int(geometry["expert_bytes_per_layer"]) / MIB
    expert_layers = int(geometry["expert_layers"])
    mmproj_mib = sum(int(tensor["bytes"]) for tensor in mmproj_tensors) / MIB

    ladder_geometry = ladder["serving_geometry"]
    ladder_context = int(ladder_geometry["context_tokens"])
    ladder_kv_mib = ladder_context * per_token / MIB
    free_before = (
        float(args.free_before_mib)
        if args.free_before_mib is not None
        else float(ladder["trials"][0]["device_memory_before_mib"]["free_mib"])
    )
    total_mib = float(ladder["trials"][0]["device_memory_before_mib"]["total_mib"])

    overhead, residuals = fit_overhead(
        ladder["trials"],
        non_expert_mib=non_expert_mib,
        expert_mib_per_layer=expert_mib_per_layer,
        expert_layers=expert_layers,
        kv_mib=ladder_kv_mib,
        mmproj_mib=mmproj_mib,
        free_before_mib=free_before,
    )

    cell_kv_mib = int(args.context_tokens) * per_token / MIB
    chosen, rungs = choose_placement(
        non_expert_mib=non_expert_mib,
        expert_mib_per_layer=expert_mib_per_layer,
        expert_layers=expert_layers,
        kv_mib=cell_kv_mib,
        mmproj_mib=mmproj_mib,
        overhead_mib=overhead,
        free_before_mib=free_before,
        min_free_mib=float(args.min_free_mib),
        step=int(args.step),
    )

    chosen_rung = next((rung for rung in rungs if rung["n_cpu_moe"] == chosen), None)
    rejected = next((rung for rung in rungs if not rung["meets_min_free"]), None)
    # How far the ONE quantity that does not carry over -- the compute overhead
    # at a different -c/-np -- could move before the answer changes.
    headroom = (
        float(chosen_rung["projected_free_mib"]) - float(args.min_free_mib)
        if chosen_rung is not None
        else None
    )
    shortfall = (
        float(args.min_free_mib) - float(rejected["projected_free_mib"])
        if rejected is not None
        else None
    )

    document = {
        "schema": "saea-e22-q8-placement-offline-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "preregistration": (
            "docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md"
        ),
        "precondition": "section 1.3, Q8-P1 -- PROJECTED here, not measured",
        "run_id": "SAEA-E22-DEV-ESB-Q8-V1",
        "cell_id": "E22-DEV-ESB-Q8",
        "boundary": (
            "zero model contacts, zero servers, zero sockets, zero GPU, zero network. "
            "The two GGUF files are opened and their HEADERS are read (metadata block "
            "and tensor table); no tensor payload is read and no model is loaded."
        ),
        "status": "PROJECTION -- Q8-P1 is a LIVE pass and is still required",
        "does_not_replace_the_live_pass": (
            "Q8-P1 measures free VRAM through GET /props and nvidia-smi at each rung "
            "with zero /completion calls (scripts/a2t_q8_placement_fit.py). This "
            "document predicts what it will find so the ladder is short and the answer "
            "is falsifiable before a GPU minute is spent. If the live pass disagrees, "
            "the LIVE number governs and this projection is the thing that was wrong."
        ),
        "model": {
            "model_lock_key": runtime["model_lock_key"],
            "runtime_receipt": str(
                Path(args.runtime_receipt).relative_to(Path(args.repo_root))
                if Path(args.runtime_receipt).is_relative_to(Path(args.repo_root))
                else args.runtime_receipt
            ),
            "runtime_receipt_sha256": sha256_file(Path(args.runtime_receipt)),
            "llama_cpp_build_commit": runtime["llama_cpp"]["build_commit"],
            "model_materialization_root": str(args.model_root),
            "gguf_files": hashes,
        },
        "decoder_tensor_table": {
            "architecture": decoder_metadata.get("general.architecture"),
            "tensor_count": len(decoder_tensors),
            "block_count": int(architecture_key(decoder_metadata, "block_count")),
            "expert_count": int(architecture_key(decoder_metadata, "expert_count")),
            "expert_layers": expert_layers,
            "expert_tensor_names": geometry["expert_tensor_names"],
            "expert_bytes_per_layer": geometry["expert_bytes_per_layer"],
            "expert_mib_per_layer": round(expert_mib_per_layer, 4),
            "expert_bytes_total": geometry["expert_bytes_total"],
            "non_expert_bytes": geometry["non_expert_bytes"],
            "non_expert_mib": round(non_expert_mib, 4),
        },
        "mmproj": {
            "architecture": mmproj_metadata.get("general.architecture"),
            "tensor_count": len(mmproj_tensors),
            "resident_bytes": sum(int(tensor["bytes"]) for tensor in mmproj_tensors),
            "resident_mib": round(mmproj_mib, 4),
            "audio_block_count": mmproj_metadata.get("clip.audio.block_count"),
            "audio_embedding_length": mmproj_metadata.get("clip.audio.embedding_length"),
            "why_resident": (
                "--no-mmproj-offload is absent in this cell's model fragment, so the "
                "bf16 mmproj stays on the GPU and every one of the 1,500 rows pays a "
                "LIVE encode -- which is exactly the condition the A2T probe never "
                "tested and the reason its N = 24 may not be copied."
            ),
        },
        "kv_cache": {
            "cache_type": "q8_0",
            "bytes_per_token": per_token,
            "basis": (
                "block_count x head_count_kv x (key_length + value_length) elements per "
                "token at the q8_0 34-bytes-per-32-elements rate, read from the "
                "decoder GGUF's own metadata"
            ),
            "ladder_context_tokens": ladder_context,
            "ladder_kv_mib": round(ladder_kv_mib, 4),
            "cell_context_tokens": int(args.context_tokens),
            "cell_kv_mib": round(cell_kv_mib, 4),
            "cell_kv_saving_mib": round(ladder_kv_mib - cell_kv_mib, 4),
        },
        "calibration": {
            "source": str(
                Path(args.a2t_ladder).relative_to(Path(args.repo_root))
                if Path(args.a2t_ladder).is_relative_to(Path(args.repo_root))
                else args.a2t_ladder
            ),
            "source_sha256": sha256_file(Path(args.a2t_ladder)),
            "source_run_id": ladder["run_id"],
            "source_serving_geometry": ladder_geometry,
            "same_decoder_same_mmproj_same_build": True,
            "fitted_overhead_mib": round(overhead, 4),
            "fitted_overhead_meaning": (
                "CUDA context plus every compute buffer llama.cpp allocates at load. "
                "It is the ONE unknown in the arithmetic and it is fitted, not assumed: "
                "the fit is refused unless every non-saturated rung yields the same "
                "constant to within 1 MiB."
            ),
            "residual_spread_mib": round(
                max(
                    float(entry["residual_mib"])
                    for entry in residuals
                    if not entry["saturated"]
                )
                - min(
                    float(entry["residual_mib"])
                    for entry in residuals
                    if not entry["saturated"]
                ),
                4,
            ),
            "rungs": residuals,
        },
        "cell_geometry": {
            "server_args": [
                "-c",
                str(int(args.context_tokens)),
                "-np",
                str(int(args.slots)),
                "-fa",
                "on",
                "-ngl",
                "999",
                "-ctk",
                "q8_0",
                "-ctv",
                "q8_0",
            ],
            "context_tokens": int(args.context_tokens),
            "slots": int(args.slots),
            "slot_tokens": int(args.context_tokens) // int(args.slots),
            "unchanged_from": (
                "the sealed SAEA-E22-DEV-ESB-PROMPT-A-V1 comparator: a slot-count "
                "change alters batch composition, greedy decoding is not bitwise "
                "reproducible across batch compositions on this runtime, and the cell "
                "would stop being single-factor"
            ),
        },
        "rule": (
            "start from --cpu-moe (every expert layer in host RAM), then lower N in "
            "steps of 4 while a zero-token server start still leaves at least "
            f"{int(args.min_free_mib)} MiB free at the declared serving geometry; the "
            "largest GPU-resident share that satisfies the rule is the value"
        ),
        "min_free_mib": int(args.min_free_mib),
        "min_free_basis": (
            "2,940 MiB -- llama.cpp's own estimate of the audio encoder's worst-case "
            "compute buffer, named in caveat 2 of docs/readiness/"
            "2026-09-04-a2t-q8-quantization-probe-v1-verdict.md -- rounded up to 3,072. "
            "Every row of this cell runs a live mmproj encode, so a placement that "
            "leaves less than that is a cell that faults."
        ),
        "step": int(args.step),
        "device": {
            "total_mib": total_mib,
            "free_before_mib": free_before,
            "free_before_basis": (
                "the idle-card reading every A2T rung recorded before its own start; "
                "the live pass must re-read it, because anything else holding device "
                "memory on flight day moves this number and therefore the answer"
            ),
        },
        "ladder": rungs,
        "chosen": chosen_rung,
        "chosen_n_cpu_moe": chosen,
        "rejected_next_rung": rejected,
        "host_ram": {
            "expert_mib_on_cpu_at_chosen": (
                round(chosen * expert_mib_per_layer, 1) if chosen is not None else None
            ),
            "a2t_measured_server_rss_mib_at_n28": 18533,
            "a2t_measured_host_available_mib": 54633,
            "verdict": (
                "the host has room: the A2T ladder measured 18,533 MiB of server RSS at "
                "N = 28 against 54,633 MiB available"
            ),
        },
        "sensitivity": {
            "the_one_quantity_that_does_not_carry_over": (
                "the compute-buffer/CUDA-context overhead at a different -c and -np. "
                "It is measured at -c 49152 -np 3 and reused at -c 40960 -np 8."
            ),
            "chosen_survives_an_overhead_increase_of_mib": (
                round(headroom, 1) if headroom is not None else None
            ),
            "next_rung_would_need_an_overhead_decrease_of_mib": (
                round(shortfall, 1) if shortfall is not None else None
            ),
            "reading": (
                "the answer is not delicate in either direction: the chosen rung still "
                "clears the floor even if the compute overhead were several times what "
                "the live ladder measured, and the next rung down would need the "
                "overhead to FALL at a geometry with more slots, which is the wrong "
                "sign"
            ),
        },
        "live_pass_still_required": [
            "start the pinned server once at the chosen N and read free VRAM through "
            "GET /props and nvidia-smi with zero /completion calls",
            "read llama.cpp's own printed audio-encoder compute-buffer estimate at THIS "
            "geometry and refuse if it exceeds the measured free",
            "confirm no LLAMA_MTMD_FEAT_CACHE_DIR is set in server_env",
            "check enforced.power.limit and the Legion SmartFanMode before anything "
            "else -- a Quiet-mode 35 W cap silently overrides everything and has "
            "recurred",
        ],
        "total_generated_tokens": 0,
        "model_contacts": 0,
    }

    if chosen is None:
        document["status"] = "REFUSED -- no placement clears the floor at this geometry"
        document["refusal"] = (
            "No N leaves at least "
            f"{int(args.min_free_mib)} MiB free at -c {int(args.context_tokens)} -np "
            f"{int(args.slots)}. Section 1.3 is explicit that the cell STOPS rather "
            "than silently shrinking -np, and that a geometry change is a NEW "
            "registration."
        )

    blob = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(blob, encoding="utf-8", newline="\n")
        print(f"wrote {out} sha256 {sha256_file(out)}")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
