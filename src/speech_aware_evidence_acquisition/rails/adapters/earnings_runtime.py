"""Config-bound Earnings21 adapter for the shared flight factory.

Reuse the existing carrier loader and original call-level split. The OBS
executor owns actual window materialization and stitching; the optional
single-phase controller hook changes neither sample identities nor speech.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from ...core.base import CoreError
from ...core.config import effective_request_decoding_params, read_fragment
from ...core.split_receipt import SplitReceiptError, VerifiedSplit, load_verified_split
from ...reproduction.window_controller import validate_window_controller
from ..hashing import content_hash
from .earnings import Earnings21Adapter


class Earnings21RuntimeAdapter(Earnings21Adapter):
    """Use pinned config geometry and whole-manifest scoring on the existing loader."""

    def __init__(self, values, lock, root, repo_root, *, dataset_fragment):
        super().__init__(lock, root, repo_root=repo_root)
        self._values_hash = content_hash(values)
        self._split_id = values.get("split_name")
        dataset = read_fragment(Path(repo_root), "dataset", dataset_fragment)
        if (
            values.get("carrier_lock_key") != "earnings21-original"
            or dataset.get("carrier_lock_key") != "earnings21-original"
        ):
            raise CoreError("E21 runtime adapter requires earnings21-original")
        if not isinstance(self._split_id, str) or dataset.get("split_name") != self._split_id:
            raise CoreError("E21 runtime split must exactly match its dataset fragment")
        self._verified_subset: VerifiedSplit | None = None
        if self._split_id != "discovery":
            subset = dataset.get("e21_runtime_subset")
            if not isinstance(subset, Mapping):
                raise CoreError(
                    "non-default E21 runtime split requires e21_runtime_subset metadata"
                )
            if set(subset) != {"receipt_split_name", "parent_split", "subset_role"}:
                raise CoreError("E21 runtime subset metadata has an unknown or missing key")
            if subset.get("receipt_split_name") != self._split_id:
                raise CoreError("E21 runtime subset receipt name differs from split_name")
            if subset.get("parent_split") != "discovery":
                raise CoreError("E21 runtime subset must derive from frozen discovery")
            if subset.get("subset_role") != "construction":
                raise CoreError("E21 runtime subset role must be construction")
            try:
                verified = load_verified_split(Path(repo_root), self._split_id, lock, root)
                parent = load_verified_split(Path(repo_root), "discovery", lock, root)
            except SplitReceiptError as error:
                raise CoreError(f"E21 runtime subset receipt refused: {error}") from error
            if (
                verified.carrier_lock_key != "earnings21-original"
                or verified.split_role != "discovery"
            ):
                raise CoreError(
                    "E21 runtime subset must be earnings21-original with discovery role"
                )
            if not set(verified.prefixed_ids) <= set(parent.prefixed_ids):
                raise CoreError(
                    "E21 runtime subset contains an id outside frozen discovery"
                )
            self._verified_subset = verified
        if values.get("policy") not in ("obs-agent-loop-ojw", "obs-repair-loop-ojw"):
            raise CoreError(
                "E21 current runtime requires the shared OpenJiuwen OBS executor"
            )
        validate_window_controller(values)
        geometry = values.get("serving_geometry")
        keys = {"slots", "slot_tokens", "max_tokens"}
        if (
            not isinstance(geometry, Mapping)
            or set(geometry) != keys
            or any(
                isinstance(geometry[key], bool)
                or not isinstance(geometry[key], int)
                or geometry[key] <= 0
                for key in keys
            )
        ):
            raise CoreError(
                "E21 runtime requires explicit positive integer serving_geometry"
            )
        if (
            (effective_request_decoding_params(values) or {}).get("max_tokens")
            != geometry["max_tokens"]
        ):
            raise CoreError(
                "E21 geometry max_tokens must match the unchanged decoding cap"
            )
        self._geometry = dict(geometry)
        instruction = values.get("task_instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise CoreError("E21 runtime requires the configured task_instruction")
        self._instruction = instruction

    def load_split(self, split_id):
        if split_id != self._split_id:
            raise CoreError("E21 runtime split differs from its dataset fragment")
        if self._verified_subset is None:
            return super().load_split("discovery")
        full = super().load_split("discovery")
        selected = tuple(
            sample for sample in full if sample.sample_id in set(self._verified_subset.ids)
        )
        if {sample.sample_id for sample in selected} != set(self._verified_subset.ids):
            raise CoreError("E21 runtime subset ids are absent from loaded discovery samples")
        return selected

    def serving_geometry(self):
        return dict(self._geometry)

    def instruction(self, sample):
        return self._instruction

    def preprocess_plan(self):
        return {"kind": "raw-speech-windows", "workers": 20}

    def score_response(self, gold, response):
        raise CoreError(
            "E21 runtime scoring requires one complete manifest through core.scoring_batch"
        )

    def bind_runtime(self, runtime, values):
        """Validate before preflight; shared OBS use sites bind the controller hook."""
        if content_hash(values) != self._values_hash:
            raise CoreError("E21 runtime config changed after adapter construction")
        validate_window_controller(values)


def build_runtime_adapter(values, lock, data_root, repo_root, *, dataset_fragment):
    """The shared factory's carrier seam; no model or preprocessing contact."""
    return Earnings21RuntimeAdapter(
        values, lock, data_root, repo_root, dataset_fragment=dataset_fragment
    )


def register_runtime_adapter():
    """Register once in the common task-adapter registry; never replace an owner."""
    from ...core.base import TASK_ADAPTERS

    if "earnings21-original" in TASK_ADAPTERS.names():
        if TASK_ADAPTERS.resolve("earnings21-original") is not build_runtime_adapter:
            raise CoreError(
                "earnings21-original runtime adapter is already registered differently"
            )
        return
    TASK_ADAPTERS.register("earnings21-original", build_runtime_adapter)
