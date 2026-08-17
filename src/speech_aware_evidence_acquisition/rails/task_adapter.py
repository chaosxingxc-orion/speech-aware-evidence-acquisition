"""TaskAdapter: the unified interface every carrier-specific task plugs into
the shared rails runner through -- exactly the five methods the B0 mission
freezes: ``load_split``, ``build_query``, ``assemble_prompt``, ``score``,
``extract_consumption``. Nothing else is abstract; ``ObsPacket``
construction is a plain, reusable function
(``rails.obs.default_obs_packet``), not a sixth interface method, so the
shape below matches the mission text exactly.
"""

from __future__ import annotations

import abc
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .consumption import ConsumptionTrace
from .obs import AudioRef, ObsPacket
from .supply import SupplyPacket


@runtime_checkable
class TaskSample(Protocol):
    """The minimal shape ``rails.obs.default_obs_packet`` needs -- a stable
    id plus enough audio identity to build a whole-file ``ObsPacket``.
    Concrete adapters attach whatever additional task-specific fields they
    need on their own sample dataclass (e.g. ``rails.adapters.audio2tool.
    Audio2ToolSample.media_relpath``); this Protocol names only the common
    subset the rails layer itself relies on."""

    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


class TaskAdapter(abc.ABC):
    """One task carrier's plug into the shared rails runner (mission-frozen
    five-method shape)."""

    @abc.abstractmethod
    def load_split(self, split_id: str) -> Sequence[TaskSample]:
        """Every sample belonging to ``split_id`` (e.g. a frozen probe
        receipt's ``split_role``, or a carrier-specific split name), sorted
        deterministically."""

    @abc.abstractmethod
    def build_query(self, sample: TaskSample, obs: ObsPacket) -> str:
        """The task-native query text for ``sample`` given its
        ``ObsPacket`` -- the string a retrieval-backed ``supply_builder``
        keys evidence retrieval against (``rails.runner.run_rails_experiment``'s
        ``supply_builder`` receives it directly)."""

    @abc.abstractmethod
    def assemble_prompt(
        self, sample: TaskSample, supply: SupplyPacket | None
    ) -> Sequence[Mapping[str, object]]:
        """Chat-style messages (``[{"role": ..., "content": ...}, ...]``)
        for ``sample``, with ``supply`` folded in as prompt-level text ONLY
        (owner ruling: no logit_bias anywhere in this study) when not
        ``None``; ``supply is None`` is the zero-supply arm."""

    @abc.abstractmethod
    def score(self, sample: TaskSample, response: str) -> Mapping[str, object]:
        """Task metrics for one response -- POST-HOC only (mirrors
        ``core.scorers``' own "scoring runs strictly after the runtime
        phase, never inside a request loop" discipline); gold enters here,
        never through ``assemble_prompt`` (D2, unchanged)."""

    @abc.abstractmethod
    def extract_consumption(
        self, sample: TaskSample, supply: SupplyPacket | None, response: str
    ) -> ConsumptionTrace:
        """USE/COPY/IGNORE attribution of ``supply`` against ``response`` --
        most adapters should build this via
        ``rails.consumption.build_consumption_trace`` rather than
        reimplementing the classification rule."""
