"""Rails (B0): typed, versioned, hashable pipeline contracts (ObsPacket /
EvidenceSet / SupplyPacket / ConsumptionTrace) plus the unified TaskAdapter
interface and a zero-model-contact runner skeleton every future experiment
composes on top of, instead of ad-hoc per-experiment scripts.

Scope note (owner ruling, 2026-08-17): multi-view speech embeddings are OUT
of this study's scope (deferred to a future memory-focused study) -- see
``rails.obs``'s own module docstring; ``ObsPacket`` carries no ``views``
field and ``rails.evidence.RetrievalParams`` carries no ``views`` field
either.

Concrete task adapters (``rails.adapters.audio2tool.Audio2ToolAdapter``, the
``rails.adapters.slurp.SlurpAdapter`` stub) are NOT re-exported here: they
pull in their own carrier-specific loader modules, which this lightweight
top-level package deliberately does not force-import for a caller who only
wants the contracts/runner.
"""

from __future__ import annotations

from .consumption import (
    ConsumptionOutcome,
    ConsumptionRecord,
    ConsumptionTrace,
    build_consumption_trace,
    classify_outcome,
)
from .core_client import CoreClient, MockCoreClient
from .errors import RailsError
from .evidence import EvidenceItem, EvidenceSet, RetrievalKeyKind, RetrievalParams
from .obs import AudioRef, ObsPacket, SpanRef, default_obs_packet
from .runner import ArmResult, RailsRunnerError, RunSummary, run_rails_experiment
from .supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .task_adapter import TaskAdapter, TaskSample

__all__ = [
    "ArmResult",
    "AudioRef",
    "ConsumptionOutcome",
    "ConsumptionRecord",
    "ConsumptionTrace",
    "CoreClient",
    "EvidenceItem",
    "EvidenceSet",
    "MockCoreClient",
    "ObsPacket",
    "RailsError",
    "RailsRunnerError",
    "RetrievalKeyKind",
    "RetrievalParams",
    "RunSummary",
    "SpanRef",
    "SupplyDose",
    "SupplyForm",
    "SupplyItem",
    "SupplyPacket",
    "TaskAdapter",
    "TaskSample",
    "build_consumption_trace",
    "classify_outcome",
    "default_obs_packet",
    "run_rails_experiment",
]
