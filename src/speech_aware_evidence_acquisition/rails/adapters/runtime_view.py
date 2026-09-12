"""Shared label-free runtime roster and geometry validation for thin adapters."""
from __future__ import annotations

import hashlib
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Mapping, Sequence


class RuntimeViewError(ValueError):
    """A frozen runtime view or its media identity is invalid."""


_MEDIA_FIELDS = {
    "sample_id", "media_relpath", "audio_sha256", "audio_seconds",
    "sample_rate_hz", "packet_id",
}


def registered_population_ids(
    values: Mapping[str, object], dataset_fragment: str,
) -> Sequence[str] | None:
    """Read exact selections from list or named-population metadata."""
    populations = values.get("populations", ())
    if isinstance(populations, Mapping):
        populations = tuple(populations.values())
    elif not isinstance(populations, (list, tuple)):
        raise RuntimeViewError("registered populations must be a list or mapping")
    if any(not isinstance(item, Mapping) for item in populations):
        raise RuntimeViewError("registered population entries must be mappings")
    matches = [
        item for item in populations
        if item.get("dataset_fragment") == dataset_fragment
    ]
    if len(matches) > 1:
        raise RuntimeViewError("dataset has multiple registered population selections")
    if not matches or "ids" not in matches[0]:
        return None
    ids = matches[0]["ids"]
    if not isinstance(ids, list) or not ids or any(not isinstance(item, str) or not item for item in ids):
        raise RuntimeViewError("registered population ids must be non-empty strings")
    if len(set(ids)) != len(ids):
        raise RuntimeViewError("registered population repeats a sample id")
    return tuple(ids)


def load_runtime_view(
    values: Mapping[str, object], data_root: Path, *,
    sample_ids: Sequence[str] | None = None, workers: int = 8,
) -> tuple[Mapping[str, object], ...]:
    """Validate media-only records and hash selected bytes; never load annotations."""
    items = values.get("items")
    if values.get("schema") != "saea-speech-native-runtime-view-v1" or not isinstance(items, list):
        raise RuntimeViewError("expected the registered speech-native runtime view")
    if values.get("count") != len(items):
        raise RuntimeViewError("runtime view count differs from its items")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise RuntimeViewError("runtime view workers must be a positive integer")
    root = Path(data_root).resolve()
    wanted = set(sample_ids) if sample_ids is not None else None
    seen: set[str] = set()
    selected = []
    for item in items:
        if not isinstance(item, Mapping) or not set(item) <= _MEDIA_FIELDS:
            raise RuntimeViewError("runtime view contains non-media or label-bearing fields")
        required = {"sample_id", "media_relpath", "audio_sha256", "audio_seconds"}
        if not required <= set(item):
            raise RuntimeViewError("runtime view is missing required media fields")
        sample_id = item["sample_id"]
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen:
            raise RuntimeViewError("runtime view has an invalid or duplicate sample id")
        seen.add(sample_id)
        relative = item["media_relpath"]
        if not isinstance(relative, str) or "\\" in relative:
            raise RuntimeViewError("runtime view media path must be confined beneath data root")
        path = root / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.resolve().is_relative_to(root):
            raise RuntimeViewError("runtime view media path must be confined beneath data root")
        seconds = item["audio_seconds"]
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            raise RuntimeViewError("runtime view audio_seconds must be finite and positive")
        if wanted is None or sample_id in wanted:
            selected.append(item)
    if wanted is not None and wanted - seen:
        raise RuntimeViewError(f"runtime view missing selected sample ids: {sorted(wanted - seen)}")
    if not selected:
        raise RuntimeViewError("runtime view selected no samples")

    def verify(item):
        path = root / item["media_relpath"]
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != item["audio_sha256"]:
            raise RuntimeViewError(f"runtime view media hash differs for {item['sample_id']}")
        return dict(item)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        verified = tuple(pool.map(verify, selected))
    return tuple(sorted(verified, key=lambda item: item["sample_id"]))


def configured_geometry(values: Mapping[str, object], *, defaults: tuple[int, int, int]) -> dict:
    """Require the fragment's actual server geometry to match the adapter data."""
    from ...core.config import effective_request_decoding_params

    slots = values.get("serving_slots", defaults[0])
    tokens = values.get("serving_slot_tokens", defaults[1])
    decoding = effective_request_decoding_params(values) or {}
    maximum = decoding.get("max_tokens", defaults[2])
    if isinstance(maximum, Mapping):
        maximum = defaults[2]
    for value in (slots, tokens, maximum):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RuntimeViewError("serving geometry must contain positive integers")
    argv = list(values.get("server_args", ()))
    for name, expected in (("-np", slots), ("-c", slots * tokens)):
        if argv.count(name) != 1:
            raise RuntimeViewError(f"server_args must declare {name} exactly once")
        try:
            actual = int(argv[argv.index(name) + 1])
        except (ValueError, IndexError) as error:
            raise RuntimeViewError(f"server_args {name} value is invalid") from error
        if actual != expected:
            raise RuntimeViewError(f"server_args {name} differs from adapter geometry")
    return {"slots": slots, "slot_tokens": tokens, "max_tokens": maximum}
