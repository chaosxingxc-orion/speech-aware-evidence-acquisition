"""Config-bound Earnings21 adapter for the shared flight factory.

Reuse the existing carrier loader and original call-level split. The shared
execution path owns window materialization and stitching. OBS policies retain
their historical controller hook; direct/native phase programs consume explicit,
source-bound execution units without changing sample identities or speech.
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


def _validate_execution_route(values):
    """Keep historical OBS and explicit unit programs on their shared paths."""
    policy = values.get("policy")
    units = values.get("prepared_execution_units")
    if policy in ("obs-agent-loop-ojw", "obs-repair-loop-ojw"):
        if units is not None:
            raise CoreError("E21 OBS execution cannot silently ignore execution units")
        validate_window_controller(values)
        return
    from ...e0.d2_leakage import ARM_VISIBLE_FIELDS
    from ...reproduction.window_controller import PROGRAM_KEY
    from ..controllers import default_phase_program
    from ..errors import RailsError

    if not isinstance(units, Mapping) or not units:
        raise CoreError("E21 phase execution requires prepared_execution_units")
    if values.get(PROGRAM_KEY) is not None:
        raise CoreError("E21 phase execution cannot combine the OBS controller hook")
    try:
        program = default_phase_program(policy)
    except RailsError as error:
        raise CoreError(f"E21 phase program refused: {error}") from error
    if program.program_id != "phase-direct-only-v1" and program.stop_rule != "native-role-episode":
        raise CoreError("E21 unit execution requires the shared direct or native-role program")
    features = "speech_feature_parts" in ARM_VISIBLE_FIELDS.get(values.get("arm"), ())
    if not features and values.get("arm") != "raw-speech-agent-native-tools":
        raise CoreError("E21 unit execution requires an explicit speech arm")
    if features != (values.get("prepared_window_feature_packets") is not None):
        raise CoreError("E21 feature units require window packets; raw units refuse them")


class Earnings21RuntimeAdapter(Earnings21Adapter):
    """Use pinned config geometry and whole-manifest scoring on the existing loader."""

    #: The carrier and its whole split; a thin derivation (``earnings22_runtime``) overrides both.
    CARRIER_LOCK_KEY = "earnings21-original"
    DEFAULT_SPLIT = "discovery"

    def __init__(self, values, lock, root, repo_root, *, dataset_fragment):
        super().__init__(lock, root, repo_root=repo_root)
        self._values_hash = content_hash(values)
        self._split_id = values.get("split_name")
        dataset = read_fragment(Path(repo_root), "dataset", dataset_fragment)
        carrier = self.CARRIER_LOCK_KEY
        if values.get("carrier_lock_key") != carrier or dataset.get("carrier_lock_key") != carrier:
            raise CoreError(f"{self._label()} runtime adapter requires {carrier}")
        if not isinstance(self._split_id, str) or dataset.get("split_name") != self._split_id:
            raise CoreError(f"{self._label()} runtime split must exactly match its dataset fragment")
        self._verified_subset: VerifiedSplit | None = None
        if self._split_id != self.DEFAULT_SPLIT:
            self._refuse_subset_if_unsupported()
            subset = dataset.get("e21_runtime_subset")
            if not isinstance(subset, Mapping):
                raise CoreError(
                    "non-default E21 runtime split requires e21_runtime_subset metadata"
                )
            if set(subset) != {"receipt_split_name", "parent_split", "subset_role"}:
                raise CoreError("E21 runtime subset metadata has an unknown or missing key")
            if subset.get("receipt_split_name") != self._split_id:
                raise CoreError("E21 runtime subset receipt name differs from split_name")
            # The parent is the carrier's whole split (``DEFAULT_SPLIT``): discovery for
            # Earnings-21 (every message below is unchanged there), dev for Earnings-22.
            parent_name = self.DEFAULT_SPLIT
            if subset.get("parent_split") != parent_name:
                raise CoreError(f"E21 runtime subset must derive from frozen {parent_name}")
            if subset.get("subset_role") != "construction":
                raise CoreError("E21 runtime subset role must be construction")
            try:
                verified = load_verified_split(Path(repo_root), self._split_id, lock, root)
                parent = load_verified_split(Path(repo_root), parent_name, lock, root)
            except SplitReceiptError as error:
                raise CoreError(f"E21 runtime subset receipt refused: {error}") from error
            if (
                verified.carrier_lock_key != carrier
                or verified.split_role != parent_name
            ):
                raise CoreError(
                    f"E21 runtime subset must be {carrier} with {parent_name} role"
                )
            if not set(verified.prefixed_ids) <= set(parent.prefixed_ids):
                raise CoreError(
                    f"E21 runtime subset contains an id outside frozen {parent_name}"
                )
            self._verified_subset = verified
        _validate_execution_route(values)
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
            return super().load_split(self.DEFAULT_SPLIT)
        full = super().load_split(self.DEFAULT_SPLIT)
        selected = tuple(
            sample for sample in full if sample.sample_id in set(self._verified_subset.ids)
        )
        if {sample.sample_id for sample in selected} != set(self._verified_subset.ids):
            raise CoreError(
                f"E21 runtime subset ids are absent from loaded {self.DEFAULT_SPLIT} samples"
            )
        return selected

    def _label(self):
        return "E21" if self.CARRIER_LOCK_KEY == "earnings21-original" else "E22"

    def _refuse_subset_if_unsupported(self):
        """E21 carries construction subsets of discovery; a derivation may refuse them."""

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
        """Validate immutable config before the shared runtime binds its sources."""
        if content_hash(values) != self._values_hash:
            raise CoreError("E21 runtime config changed after adapter construction")
        _validate_execution_route(values)


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
