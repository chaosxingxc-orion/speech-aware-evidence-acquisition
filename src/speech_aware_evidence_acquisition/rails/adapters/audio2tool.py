"""Audio2Tool ``TaskAdapter`` (B0 rails, first concrete adapter).

Reuses the existing, already-verified Audio2Tool substrate directly rather
than re-deriving it: ``data.audio2tool.load_audio2tool``/
``audio2tool_receipts``/``render_tool_schemas`` for sample identity and the
frozen tool-registry text, and ``reproduction.toolcall_scoring``/
``data.audio2tool.load_expected_calls`` for scorer-side gold -- the SAME
scorer-side-only discipline ``reproduction.a2t_scorer`` already applies
(gold never enters ``assemble_prompt``/``build_task_contract``, only ``score``).

Carrier admission: the bounded discovery-probe carrier admitted by the
2026-08-15 owner amendment (Amendment 1, umbrella
``wiki/experiments/speech-aware-evidence-acquisition/
2026-08-15-owner-go-dual-track-agentic.md``): the entity-knowledge leverage
probe (tool-registry roster injected vs not, tiers 2-3, clean/noisy). This
adapter is engineering scaffolding for that probe's rails, not the probe
execution itself -- constructing it touches no model and no live umbrella
lock; it only reads the same frozen probe-sample receipt(s)
``data.audio2tool`` already reads.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ...data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    audio2tool_receipts,
    load_audio2tool,
    load_expected_calls,
    render_tool_schemas,
)
from ...data.lock import REPO_ROOT
from ...reproduction.toolcall_scoring import parse_tool_calls_text, score_item
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..obs import AudioRef, ObsPacket
from ..supply import SupplyPacket
from ..task_adapter import TaskAdapter

_INSTRUCTION_TEMPLATE = (
    "You control tools. Available tools:\n{tool_schemas}\n\n"
    'Respond with ONLY a JSON array of tool calls, e.g. [{{"name": "x", "arguments": {{}}}}].'
)


@dataclass(frozen=True)
class Audio2ToolSample:
    """One receipt-scoped Audio2Tool sample -- the ``TaskSample`` this
    adapter's methods carry throughout. ``sample_id``/``audio_ref``/
    ``audio_seconds`` satisfy ``rails.task_adapter.TaskSample``;
    ``media_relpath`` is Audio2Tool-specific, needed by ``assemble_prompt``
    to point the message at the actual wav."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    media_relpath: str


class Audio2ToolAdapter(TaskAdapter):
    """``TaskAdapter`` over the frozen-receipt-scoped Audio2Tool carrier."""

    def __init__(
        self, lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None
    ) -> None:
        self._lock = lock
        self._root = Path(root)
        # Same default-resolution convention data.audio2tool.load_audio2tool
        # itself uses: repo_root defaults to this study checkout (where the
        # committed probe receipt lives), overridable so tests can point it
        # at a synthetic repo.
        self._repo_root = Path(REPO_ROOT if repo_root is None else repo_root)

    def load_split(self, split_id: str) -> Sequence[Audio2ToolSample]:
        """``split_id`` names a frozen probe-sample receipt's ``split_role``
        (``"discovery"`` or ``"dev"``, the Stage-2 roles ``data.audio2tool``
        already enforces) -- every sample belonging to a receipt with that
        role, sorted by ``sample_id``."""

        receipts = audio2tool_receipts(self._repo_root)
        wanted_ids = {
            f"{item['tier']}:{int(item['id']):06d}"
            for payload in receipts.values()
            if payload.get("split_role") == split_id
            for item in payload["items"]
        }
        if not wanted_ids:
            raise ValueError(f"no audio2tool probe receipt declares split_role={split_id!r}")
        refs = load_audio2tool(self._lock, self._root, repo_root=self._repo_root)
        samples = [
            Audio2ToolSample(
                sample_id=ref.sample_id,
                audio_ref=self._audio_ref(ref.media_relpath),
                audio_seconds=ref.audio_seconds,
                media_relpath=ref.media_relpath,
            )
            for ref in refs
            if ref.sample_id in wanted_ids
        ]
        return tuple(sorted(samples, key=lambda sample: sample.sample_id))

    def _audio_ref(self, media_relpath: str) -> AudioRef:
        media_path = self._root / media_relpath
        digest = hashlib.sha256(media_path.read_bytes()).hexdigest()
        return AudioRef(path=media_relpath, sha256=digest).validate()

    def build_task_contract(self, sample: Audio2ToolSample, obs: ObsPacket) -> str:
        """Return the full frozen tool registry as stable task schema.

        The spoken command remains the query; this contract defines the tool
        vocabulary against which that speech observation must be interpreted
        (``data.audio2tool.render_tool_schemas``) -- never a text
        transcript of the audio itself (the command is spoken, never
        available as text before the model hears it)."""

        return render_tool_schemas(self._lock, self._root)

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        instruction = _INSTRUCTION_TEMPLATE.format(
            tool_schemas=render_tool_schemas(self._lock, self._root)
        )
        content: list[Mapping[str, object]] = []
        if supply is not None:
            content.append({"type": "text", "text": supply.prompt_block})
        content.append({"type": "input_audio", "media_relpath": sample.media_relpath})
        return (
            {"role": "system", "content": instruction},
            {"role": "user", "content": content},
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        """Post-hoc only (module docstring): gold is read HERE, never in
        ``assemble_prompt``/``build_task_contract`` above."""

        expected_by_id = load_expected_calls(self._lock, self._root, repo_root=self._repo_root)
        expected = expected_by_id.get(sample.sample_id)
        if expected is None:
            raise ValueError(
                f"sample {sample.sample_id!r} is not in the frozen audio2tool probe receipt"
            )
        predicted, parsed = parse_tool_calls_text(response)
        item = score_item(expected, predicted)
        return {
            "tool_accuracy": item.tool_accuracy,
            "exact_match": item.exact_match,
            "slot_precision": item.slot_precision,
            "slot_recall": item.slot_recall,
            "slot_f1": item.slot_f1,
            "parsed": parsed,
        }

    def extract_consumption(
        self, sample: Audio2ToolSample, supply: SupplyPacket | None, response: str
    ) -> ConsumptionTrace:
        return build_consumption_trace(span_id="full", supply=supply, response_text=response)


__all__ = ["AUDIO2TOOL_LOCK_KEY", "Audio2ToolAdapter", "Audio2ToolSample"]
