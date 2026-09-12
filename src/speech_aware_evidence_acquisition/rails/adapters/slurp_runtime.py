"""Config-driven SLURP adapter over the shared label-free frozen runtime view."""
from __future__ import annotations

import re
from typing import Mapping

from ...core.base import TASK_ADAPTERS
from ...core.instructions import resolve_active_task_instruction, resolve_task_instruction
from ...reproduction.slurp_scoring import parse_slu_response
from ..obs import AudioRef
from .runtime_view import (
    RuntimeViewError, configured_geometry, load_runtime_view, registered_population_ids,
)
from .slurp import SlurpAdapter, SlurpSample


_REGISTERED_DEV_SPLIT = re.compile(r"DEV-[0-9]+(?:-[A-Za-z0-9]+)*$")


def _allowed_runtime_split(split_id: str) -> bool:
    return split_id in {"devel", "discovery"} or bool(_REGISTERED_DEV_SPLIT.fullmatch(split_id))


def _sample_namespace(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) < 3 or parts[0] != "slurp":
        raise RuntimeViewError("runtime SLURP view contains a non-SLURP sample")
    return parts[1]


def _assert_sample_namespaces(
    samples, *, split_id: str, split_role: str,
    registered_population_bound: bool, runtime_split_name: str | None,
) -> None:
    namespaces = {_sample_namespace(sample.sample_id) for sample in samples}
    if len(namespaces) != 1:
        raise RuntimeViewError("runtime SLURP view must not mix train and devel samples")
    namespace = next(iter(namespaces))
    if namespace == "devel":
        if not _allowed_runtime_split(split_id):
            raise RuntimeViewError(
                "runtime SLURP devel samples require a discovery/devel or registered DEV split"
            )
        return
    if namespace != "train":
        label = (
            "non-discovery sample" if split_id == "discovery" else "non-devel sample"
        )
        raise RuntimeViewError(f"runtime SLURP view contains a {label}")
    if split_id == "devel" or _REGISTERED_DEV_SPLIT.fullmatch(split_id):
        raise RuntimeViewError("runtime SLURP view contains a non-devel sample")
    if split_role != "discovery":
        raise RuntimeViewError("runtime SLURP TRAIN samples require discovery split role")
    if not registered_population_bound:
        raise RuntimeViewError(
            "runtime SLURP TRAIN samples require an explicit registered population"
        )
    if split_id != "discovery" and split_id != runtime_split_name:
        raise RuntimeViewError(
            "runtime SLURP TRAIN split id must match its registered runtime split"
        )


def roster_samples(values, data_root_path, *, limit_sample_ids=None, workers=16):
    """Build only media-scoped samples, retaining the historical wrapper call shape."""
    rows = load_runtime_view(values, data_root_path, sample_ids=limit_sample_ids, workers=workers)
    samples = []
    for item in rows:
        sample_id = item["sample_id"]
        _sample_namespace(sample_id)
        parts = sample_id.split(":")
        samples.append(SlurpSample(
            sample_id=sample_id, audio_ref=AudioRef(
                path=item["media_relpath"], sha256=item["audio_sha256"],
            ).validate(), audio_seconds=float(item["audio_seconds"]),
            utterance_id=parts[2], media_relpath=item["media_relpath"],
            scenario="", action="", intent="", entities=(),
        ))
    samples = tuple(samples)
    plan = values.get("execution_plan", {})
    _assert_sample_namespaces(
        samples, split_id=str(values.get("split_id", "devel")),
        split_role=str(plan.get("split_role", "")),
        registered_population_bound=limit_sample_ids is not None,
        runtime_split_name=values.get("split_name"),
    )
    return samples


class RuntimeSlurpAdapter(SlurpAdapter):
    """Bind roster, instruction and serving geometry as data on the existing adapter."""

    def __init__(
        self, lock, root, *, repo_root, split_id, samples, instruction_text,
        serving_slots=None, serving_slot_tokens=None, serving_max_tokens=None,
        split_role="", registered_population_bound=False, runtime_split_name=None,
    ):
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        if not isinstance(instruction_text, str) or not instruction_text:
            raise RuntimeViewError("runtime SLURP requires a config-resolved instruction")
        self._instruction_text = instruction_text
        self._samples = tuple(samples)
        _assert_sample_namespaces(
            self._samples, split_id=split_id, split_role=split_role,
            registered_population_bound=registered_population_bound,
            runtime_split_name=runtime_split_name,
        )
        if any(
            sample.scenario or sample.action or sample.intent or sample.entities
            for sample in self._samples
        ):
            raise RuntimeViewError("runtime SLURP samples must contain no gold labels")
        for name, value in (
            ("SERVING_SLOTS", serving_slots), ("SERVING_SLOT_TOKENS", serving_slot_tokens),
            ("SERVING_MAX_TOKENS", serving_max_tokens),
        ):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    raise RuntimeViewError("runtime geometry values must be positive integers")
                setattr(self, name, value)

    def load_split(self, split_id, *, allow_heldout=False, allow_synthetic=False):
        if allow_heldout or allow_synthetic or split_id != self._split_id:
            raise RuntimeViewError("runtime adapter cannot expand its registered split")
        return self._samples

    def instruction(self, sample):
        return self._instruction_text

    def gold(self, sample):
        raise RuntimeViewError("gold never enters a runtime flight; score the sealed manifest")

    def score(self, sample, response: str) -> Mapping[str, object]:
        _, _, _, parsed = parse_slu_response(response)
        return {
            "sample_id": sample.sample_id, "parsed": parsed, "response_chars": len(response),
            "scored_post_hoc_by": "slurp-slu-official through core.scoring_batch",
        }

    def bind_runtime(self, runtime, values):
        from .slurp_runtime_material import bind_runtime_material
        bind_runtime_material(runtime, values, self._lock, self._root)


def build_runtime_adapter(values, lock, data_root, repo_root, *, dataset_fragment):
    instruction = (
        resolve_active_task_instruction(values, repo_root, lock, data_root)
        or resolve_task_instruction(values, repo_root, lock, data_root)
    )
    geometry = configured_geometry(values, defaults=(8, 8192, 64))
    population_ids = registered_population_ids(values, dataset_fragment)
    samples = roster_samples(
        values, data_root,
        limit_sample_ids=population_ids,
        workers=values.get("runtime_view_workers", 8),
    )
    return RuntimeSlurpAdapter(
        lock, data_root, repo_root=repo_root, split_id=str(values["split_id"]),
        samples=samples, instruction_text=instruction,
        serving_slots=geometry["slots"], serving_slot_tokens=geometry["slot_tokens"],
        serving_max_tokens=geometry["max_tokens"],
        split_role=str(values.get("execution_plan", {}).get("split_role", "")),
        registered_population_bound=population_ids is not None,
        runtime_split_name=values.get("split_name"),
    )


def register_runtime_adapter():
    if "slurp" not in TASK_ADAPTERS.names():
        TASK_ADAPTERS.register("slurp", build_runtime_adapter)
