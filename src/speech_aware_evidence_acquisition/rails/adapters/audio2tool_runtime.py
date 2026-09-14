"""Config-bound Audio2Tool rosters for the common FlightRuntime factory."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
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
from ..hashing import content_hash
from ..obs import AudioRef
from .audio2tool import Audio2ToolAdapter, Audio2ToolSample
from .runtime_view import (
    configured_geometry,
    load_runtime_view,
    registered_population_ids,
)


_PERCEPTION_STATE_KEYS = {"actions", "global_constraints"}
_PERCEPTION_ACTION_KEYS = {
    "action_id",
    "candidate_tools",
    "evidence",
    "uncertain_arguments",
}
_ACTION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", flags=re.ASCII)
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", flags=re.ASCII)


class Audio2ToolPerceptionStateError(ValueError):
    """Reject malformed or unbound native Audio2Tool Perception state."""


@dataclass(frozen=True)
class Audio2ToolPerceptionAction:
    """One ordered action occurrence proposed by Perception."""

    action_id: str
    candidate_tools: tuple[str, ...]
    evidence: str
    uncertain_arguments: tuple[str, ...]


@dataclass(frozen=True)
class Audio2ToolPerceptionState:
    """A non-authoritative, immutable Perception state."""

    actions: tuple[Audio2ToolPerceptionAction, ...]
    global_constraints: tuple[str, ...]
    unique_tool_names: tuple[str, ...]


def _strict_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Audio2ToolPerceptionStateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise Audio2ToolPerceptionStateError(f"invalid non-finite JSON constant: {value}")


def _positive_bound(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Audio2ToolPerceptionStateError(f"{name} must be a positive integer")


def _text_list(value, *, name):
    if not isinstance(value, list):
        raise Audio2ToolPerceptionStateError(f"{name} must be an ordered list")
    if any(not isinstance(item, str) for item in value):
        raise Audio2ToolPerceptionStateError(f"{name} must contain text")
    return tuple(value)


def parse_audio2tool_perception_state(
    text: str,
    *,
    legal_tool_names: Sequence[str],
    max_actions: int,
    max_candidates_per_action: int,
) -> Audio2ToolPerceptionState:
    """Parse a bounded candidate state without granting answer authority."""
    _positive_bound("max_actions", max_actions)
    _positive_bound("max_candidates_per_action", max_candidates_per_action)
    if isinstance(legal_tool_names, (str, bytes)) or not isinstance(
        legal_tool_names, Sequence
    ):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names must be an ordered authoritative inventory"
        )
    legal = tuple(legal_tool_names)
    if not legal:
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names must be a non-empty authoritative inventory"
        )
    if any(
        not isinstance(name, str) or _TOOL_NAME.fullmatch(name) is None
        for name in legal
    ):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names contains a non-canonical tool name"
        )
    if len(set(legal)) != len(legal):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names contains duplicate tool names"
        )
    legal_set = frozenset(legal)

    if not isinstance(text, str) or not text.strip() or '```' in text:
        raise Audio2ToolPerceptionStateError(
            "Perception state must be one unfenced JSON object"
        )
    try:
        document = json.loads(
            text,
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
    except Audio2ToolPerceptionStateError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise Audio2ToolPerceptionStateError(
            "Perception state must be valid JSON"
        ) from exc
    if not isinstance(document, dict):
        raise Audio2ToolPerceptionStateError("Perception state must be a JSON object")
    if set(document) != _PERCEPTION_STATE_KEYS:
        raise Audio2ToolPerceptionStateError(
            "Perception state must contain exactly actions and global_constraints"
        )

    raw_actions = document["actions"]
    if not isinstance(raw_actions, list):
        raise Audio2ToolPerceptionStateError("actions must be an ordered list")
    if len(raw_actions) > max_actions:
        raise Audio2ToolPerceptionStateError("actions exceeds max_actions")

    action_ids = set()
    actions = []
    unique_tool_names = []
    seen_tool_names = set()
    for position, raw_action in enumerate(raw_actions):
        if not isinstance(raw_action, dict):
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}] must be a JSON object"
            )
        if set(raw_action) != _PERCEPTION_ACTION_KEYS:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}] must contain exactly action_id, "
                "candidate_tools, evidence, and uncertain_arguments"
            )
        action_id = raw_action["action_id"]
        if not isinstance(action_id, str) or _ACTION_ID.fullmatch(action_id) is None:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].action_id must be a canonical occurrence ID"
            )
        if action_id in action_ids:
            raise Audio2ToolPerceptionStateError(f"duplicate action_id: {action_id}")
        action_ids.add(action_id)

        raw_candidates = raw_action["candidate_tools"]
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].candidate_tools must be a non-empty ordered list"
            )
        if len(raw_candidates) > max_candidates_per_action:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].candidate_tools exceeds max_candidates_per_action"
            )
        candidates = []
        for candidate in raw_candidates:
            if (
                not isinstance(candidate, str)
                or _TOOL_NAME.fullmatch(candidate) is None
            ):
                raise Audio2ToolPerceptionStateError(
                    f"actions[{position}].candidate_tools contains "
                    "a non-canonical tool name"
                )
            if candidate not in legal_set:
                raise Audio2ToolPerceptionStateError(
                    f"tool {candidate} is outside the authoritative inventory"
                )
            candidates.append(candidate)
            if candidate not in seen_tool_names:
                seen_tool_names.add(candidate)
                unique_tool_names.append(candidate)

        evidence = raw_action["evidence"]
        if not isinstance(evidence, str):
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].evidence must be text"
            )
        uncertain_arguments = _text_list(
            raw_action["uncertain_arguments"],
            name=f"actions[{position}].uncertain_arguments",
        )
        actions.append(
            Audio2ToolPerceptionAction(
                action_id=action_id,
                candidate_tools=tuple(candidates),
                evidence=evidence,
                uncertain_arguments=uncertain_arguments,
            )
        )

    return Audio2ToolPerceptionState(
        actions=tuple(actions),
        global_constraints=_text_list(
            document["global_constraints"], name="global_constraints"
        ),
        unique_tool_names=tuple(unique_tool_names),
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
