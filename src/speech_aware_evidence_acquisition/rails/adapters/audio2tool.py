"""Audio2Tool ``TaskAdapter`` (B0 rails, first concrete adapter).

Reuses the existing, already-verified Audio2Tool substrate directly rather
than re-deriving it: ``data.audio2tool.load_audio2tool``/
``audio2tool_receipts``/``render_tool_schemas`` for sample identity and the
frozen tool-registry text, and ``reproduction.toolcall_scoring``/
``data.audio2tool.load_expected_calls`` for scorer-side gold -- the SAME
scorer-side-only discipline ``reproduction.a2t_scorer`` already applies
(gold never enters ``assemble_prompt``/``build_task_contract``, only through
``gold``/``score_response``, both reached exclusively from ``score``).

Carrier admission: the bounded discovery-probe carrier admitted by the
2026-08-15 owner amendment (Amendment 1, umbrella
``wiki/experiments/speech-aware-evidence-acquisition/
2026-08-15-owner-go-dual-track-agentic.md``): the entity-knowledge leverage
probe (tool-registry roster injected vs not, tiers 2-3, clean/noisy). This
adapter is engineering scaffolding for that probe's rails, not the probe
execution itself -- constructing it touches no model and no live umbrella
lock; it only reads the same frozen probe-sample receipt(s)
``data.audio2tool`` already reads.

C2 consolidation: ``audio_ref``/``assemble_prompt``/``extract_consumption``
are now ``rails.task_adapter.TaskAdapter`` base defaults (see that module);
this adapter supplies only the Audio2Tool-specific ``instruction``/``gold``/
``score_response`` hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ...data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    audio2tool_receipts,
    load_audio2tool,
    load_expected_calls,
    load_tool_registry_with_sha256,
    render_tool_schemas,
)
from ...data.lock import REPO_ROOT
from ...data.variant_ids import published_sample_key
from ...reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text, score_item
from ..obs import AudioRef, ObsPacket
from ..task_adapter import CandidateInventory, TaskAdapter

AUDIO2TOOL_OUTPUT_INSTRUCTION = (
    'Respond with ONLY a JSON array of tool calls, e.g. [{"name": "x", "arguments": {}}].'
)
_INSTRUCTION_TEMPLATE = (
    "You control tools. Available tools:\n{tool_schemas}\n\n"
    'Respond with ONLY a JSON array of tool calls, e.g. [{{"name": "x", "arguments": {{}}}}].'
)


def render_audio2tool_instruction(
    tool_schemas: str,
    *,
    auxiliary_context: str | None = None,
) -> str:
    """Render the direct contract, optionally inserting context before its suffix.

    The no-context result is byte-identical to the historical template.  A
    successor may add English Agent state or evidence only ahead of the same
    final output sentence and exact ``name``/``arguments`` example.
    """

    if not isinstance(tool_schemas, str) or not tool_schemas.strip():
        raise ValueError("Audio2Tool tool schemas must be non-empty text")
    direct = _INSTRUCTION_TEMPLATE.format(tool_schemas=tool_schemas)
    if auxiliary_context is None:
        return direct
    if not isinstance(auxiliary_context, str) or not auxiliary_context.strip():
        raise ValueError("Audio2Tool auxiliary context must be non-empty text")
    prefix = direct[: -len(AUDIO2TOOL_OUTPUT_INSTRUCTION)]
    return f"{prefix}{auxiliary_context}\n\n{AUDIO2TOOL_OUTPUT_INSTRUCTION}"


@dataclass(frozen=True)
class Audio2ToolSample:
    """One receipt-scoped Audio2Tool sample -- the ``TaskSample`` this
    adapter's methods carry throughout. ``sample_id``/``audio_ref``/
    ``audio_seconds`` satisfy ``rails.task_adapter.TaskSample``;
    ``media_relpath`` is Audio2Tool-specific, needed by the base
    ``TaskAdapter.assemble_prompt`` default to point the message at the
    actual wav."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float
    media_relpath: str


class Audio2ToolAdapter(TaskAdapter):
    """``TaskAdapter`` over the frozen-receipt-scoped Audio2Tool carrier."""

    # Owner-documented serving geometry (rails.task_adapter.TaskAdapter.
    # serving_geometry docstring): fewer slots, wider per-slot budget --
    # tool-call responses are short, but the tool registry + evidence
    # context injected ahead of them can be large.
    SERVING_SLOTS = 2
    SERVING_SLOT_TOKENS = 32768
    SERVING_MAX_TOKENS = 1024

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
        self._candidate_inventory: CandidateInventory | None = None

    def candidate_inventory(self) -> CandidateInventory:
        """Return the public registry's complete ordered legal tool roster."""

        if self._candidate_inventory is None:
            rows, source_sha256 = load_tool_registry_with_sha256(
                self._lock, self._root
            )
            self._candidate_inventory = CandidateInventory(
                candidate_ids=tuple(row["tool_name"] for row in rows),
                source_sha256=source_sha256,
                source_authority="audio2tool-public-tool-registry",
            )
        return self._candidate_inventory

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
                audio_ref=self.audio_ref(ref.media_relpath),
                audio_seconds=ref.audio_seconds,
                media_relpath=ref.media_relpath,
            )
            for ref in refs
            if ref.sample_id in wanted_ids
        ]
        return tuple(sorted(samples, key=lambda sample: sample.sample_id))

    def build_task_contract(self, sample: Audio2ToolSample, obs: ObsPacket) -> str:
        """Return the full frozen tool registry as stable task schema.

        The spoken command remains the query; this contract defines the tool
        vocabulary against which that speech observation must be interpreted
        (``data.audio2tool.render_tool_schemas``) -- never a text
        transcript of the audio itself (the command is spoken, never
        available as text before the model hears it)."""

        return render_tool_schemas(self._lock, self._root)

    def instruction(self, sample: Audio2ToolSample) -> str:
        """The direct-contract instruction: the frozen tool registry plus
        the fixed output-format sentence (``render_audio2tool_instruction``)
        -- the same text for every sample, so ``sample`` is unused."""

        return render_audio2tool_instruction(render_tool_schemas(self._lock, self._root))

    def gold(self, sample: Audio2ToolSample) -> tuple[ToolCall, ...]:
        """Look up ``sample``'s frozen expected tool call(s) -- read HERE
        (module docstring), never in ``assemble_prompt``/
        ``build_task_contract`` above.

        VARIANT-ID RAIL (2026-09-07): a derived-media population carries
        ``<published id>@<variant>`` ids (``data.variant_ids``), so the
        published key is recovered before the lookup. Inert for every
        unsuffixed id, and not a skeleton key -- a foreign published key
        still refuses below, and the refusal names the RAW id that was
        flown.
        """

        expected_by_id = load_expected_calls(self._lock, self._root, repo_root=self._repo_root)
        expected = expected_by_id.get(published_sample_key(sample.sample_id))
        if expected is None:
            raise ValueError(
                f"sample {sample.sample_id!r} is not in the frozen audio2tool probe receipt"
            )
        return expected

    def score_response(self, gold: tuple[ToolCall, ...], response: str) -> Mapping[str, object]:
        predicted, parsed = parse_tool_calls_text(response)
        item = score_item(gold, predicted)
        return {
            "tool_accuracy": item.tool_accuracy,
            "exact_match": item.exact_match,
            "slot_precision": item.slot_precision,
            "slot_recall": item.slot_recall,
            "slot_f1": item.slot_f1,
            "parsed": parsed,
        }


__all__ = [
    "AUDIO2TOOL_LOCK_KEY",
    "AUDIO2TOOL_OUTPUT_INSTRUCTION",
    "Audio2ToolAdapter",
    "Audio2ToolSample",
    "render_audio2tool_instruction",
]
