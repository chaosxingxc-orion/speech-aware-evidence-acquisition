"""Config-bound Audio2Tool rosters for the common FlightRuntime factory."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from ...core.base import CoreError
from ...data.audio2tool_runtime_roster import (
    RUNTIME_ROSTER_BINDING_FIELDS,
    RUNTIME_ROSTER_MEDIA_FIELDS,
    RUNTIME_ROSTER_ALLOWED_FIELDS,
    load_runtime_roster,
    validate_runtime_roster,
)
from ...core.config import read_fragment
from ...core.instructions import resolve_active_task_instruction
from ..a2t_perception_state import (
    Audio2ToolPerceptionStateError as Audio2ToolPerceptionStateError,
    parse_audio2tool_perception_state as parse_audio2tool_perception_state,
)
from ..hashing import content_hash
from ..obs import AudioRef
from .audio2tool import Audio2ToolAdapter, Audio2ToolSample
from .runtime_view import (
    configured_geometry,
    load_runtime_view,
    registered_population_ids,
)


def _samples_from_roster(
    receipt,
    data_root_path,
    *,
    limit_sample_ids=None,
    media_prefix=None,
    workers=8,
):
    rows = []
    for item in receipt["items"]:
        if not isinstance(item, Mapping) or not set(item) <= RUNTIME_ROSTER_ALLOWED_FIELDS:
            raise CoreError("Audio2Tool roster contains non-media fields")
        if not RUNTIME_ROSTER_MEDIA_FIELDS <= set(item):
            raise CoreError("Audio2Tool roster is missing required media fields")
        relative = item["media_relpath"]
        if media_prefix is not None and (
            not isinstance(relative, str) or not relative.startswith(media_prefix + "/")
        ):
            raise CoreError(
                "Audio2Tool roster media is outside its declared derived root"
            )
        rows.append({key: item[key] for key in RUNTIME_ROSTER_MEDIA_FIELDS})
    view = {
        "schema": "saea-speech-native-runtime-view-v1",
        "count": len(rows),
        "items": rows,
    }
    verified = load_runtime_view(
        view,
        data_root_path,
        sample_ids=limit_sample_ids,
        workers=workers,
    )
    return tuple(
        Audio2ToolSample(
            sample_id=row["sample_id"],
            audio_ref=AudioRef(
                path=row["media_relpath"], sha256=row["audio_sha256"]
            ).validate(),
            audio_seconds=float(row["audio_seconds"]),
            media_relpath=row["media_relpath"],
        )
        for row in verified
    )


def roster_samples(
    roster_path: Path,
    roster_sha256: str,
    data_root_path: Path,
    *,
    limit_sample_ids: Sequence[str] | None = None,
    media_prefix: str | None = None,
    workers: int = 8,
) -> tuple[Audio2ToolSample, ...]:
    """Reuse the historical receipt loader through shared media-only validation."""
    return _samples_from_roster(
        load_runtime_roster(roster_path, roster_sha256),
        data_root_path,
        limit_sample_ids=limit_sample_ids,
        media_prefix=media_prefix,
        workers=workers,
    )


class Audio2ToolRuntimeAdapter(Audio2ToolAdapter):
    """Bind the existing task contract to one roster and one serving configuration."""

    def __init__(
        self,
        lock,
        root,
        *,
        repo_root,
        split_id,
        samples,
        instruction_text,
        geometry,
        task_contract_source="legacy-registry",
    ):
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        self._samples = tuple(samples)
        self._instruction_text = instruction_text
        if task_contract_source not in {"legacy-registry", "active-instruction"}:
            raise CoreError("Audio2Tool task_contract_source is unsupported")
        if task_contract_source == "active-instruction" and (
            not isinstance(instruction_text, str) or not instruction_text.strip()
        ):
            raise CoreError("Audio2Tool task contract requires an active instruction")
        self._task_contract_source = task_contract_source
        if not isinstance(geometry, Mapping) or set(geometry) != {
            "slots",
            "slot_tokens",
            "max_tokens",
        }:
            raise CoreError("Audio2Tool requires an exact serving geometry")
        if any(
            isinstance(v, bool) or not isinstance(v, int) or v < 1
            for v in geometry.values()
        ):
            raise CoreError("Audio2Tool geometry must contain positive integers")
        self.SERVING_SLOTS = geometry["slots"]
        self.SERVING_SLOT_TOKENS = geometry["slot_tokens"]
        self.SERVING_MAX_TOKENS = geometry["max_tokens"]
        self._values_hash = None

    def load_split(self, split_id):
        if split_id != self._split_id:
            raise CoreError("Audio2Tool runtime cannot expand its registered split")
        return self._samples

    def instruction(self, sample):
        if self._instruction_text is not None:
            return self._instruction_text
        return super().instruction(sample)

    def build_task_contract(self, sample, obs):
        """Use the configured native contract once when explicitly selected."""
        if self._task_contract_source == "active-instruction":
            return self._instruction_text
        return super().build_task_contract(sample, obs)

    def gold(self, sample):
        raise CoreError("gold never enters an Audio2Tool runtime flight")

    def score(self, sample, response):
        return {
            "sample_id": sample.sample_id,
            "response_chars": len(response),
            "scored_post_hoc_by": "a2t-toolcall-official through core.scoring_batch",
        }

    def score_response(self, gold, response):
        raise CoreError("Audio2Tool official scoring requires a complete manifest")

    def bind_runtime(self, runtime, values):
        if self._values_hash is not None and content_hash(values) != self._values_hash:
            raise CoreError(
                "Audio2Tool runtime config changed after adapter construction"
            )


def build_runtime_adapter(values, lock, data_root, repo_root, *, dataset_fragment):
    """Build from four fragments without loading raw task manifests or a service."""
    dataset = read_fragment(Path(repo_root), "dataset", dataset_fragment)
    if (
        values.get("carrier_lock_key") != "audio2tool"
        or dataset.get("carrier_lock_key") != "audio2tool"
    ):
        raise CoreError("Audio2Tool adapter requires audio2tool carrier")
    for key in RUNTIME_ROSTER_BINDING_FIELDS:
        if key not in dataset or values.get(key) != dataset[key]:
            raise CoreError(f"Audio2Tool {key} differs from its dataset binding")
    geometry = values.get("serving_geometry")
    if not isinstance(geometry, Mapping) or set(geometry) != {
        "slots",
        "slot_tokens",
        "max_tokens",
    }:
        raise CoreError("Audio2Tool requires an explicit serving geometry")
    if any(
        isinstance(v, bool) or not isinstance(v, int) or v < 1
        for v in geometry.values()
    ):
        raise CoreError("Audio2Tool geometry must contain positive integers")
    for key, field in (
        ("serving_slots", "slots"),
        ("serving_slot_tokens", "slot_tokens"),
    ):
        if key in values and values[key] != geometry[field]:
            raise CoreError("Audio2Tool flat and structured serving geometry differ")
    actual = configured_geometry(
        dict(
            values,
            serving_slots=geometry["slots"],
            serving_slot_tokens=geometry["slot_tokens"],
        ),
        defaults=(geometry["slots"], geometry["slot_tokens"], geometry["max_tokens"]),
    )
    if actual["max_tokens"] != geometry["max_tokens"]:
        raise CoreError("Audio2Tool geometry max_tokens differs from the request cap")
    relative = values["a2t_calibration_subset_receipt"]
    if (
        not isinstance(relative, str)
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise CoreError("Audio2Tool roster must be confined beneath the repository")
    root = Path(repo_root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise CoreError("Audio2Tool roster must be confined beneath the repository")
    receipt = load_runtime_roster(path, values["a2t_calibration_subset_receipt_sha256"])
    validate_runtime_roster(receipt, values)
    samples = _samples_from_roster(
        receipt,
        data_root,
        limit_sample_ids=registered_population_ids(values, dataset_fragment),
        media_prefix=values.get("a2t_calibration_derived_subdir"),
        workers=values.get("runtime_view_workers", 8),
    )
    adapter = Audio2ToolRuntimeAdapter(
        lock,
        data_root,
        repo_root=repo_root,
        split_id=values["split_id"],
        samples=samples,
        instruction_text=resolve_active_task_instruction(
            values, repo_root, lock, data_root
        ),
        geometry=geometry,
        task_contract_source=values.get("task_contract_source", "legacy-registry"),
    )
    adapter._values_hash = content_hash(values)
    return adapter


def register_runtime_adapter():
    """Register once without replacing an existing implementation."""
    from ...core.base import TASK_ADAPTERS

    if "audio2tool" in TASK_ADAPTERS.names():
        if TASK_ADAPTERS.resolve("audio2tool") is not build_runtime_adapter:
            raise CoreError(
                "audio2tool runtime adapter is already registered differently"
            )
        return
    TASK_ADAPTERS.register("audio2tool", build_runtime_adapter)
