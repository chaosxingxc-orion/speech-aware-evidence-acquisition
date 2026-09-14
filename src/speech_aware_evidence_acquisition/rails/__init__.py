"""Rails: typed, versioned, hashable pipeline contracts.

The shared layer carries ObsPacket / EvidenceSet / SupplyPacket /
ConsumptionTrace plus the TRAIN-build KnowledgeSnapshot and DEV-use
QueryState / RankResult / FusionDecision seam.  AgentStepTransition binds
each loop action to the same speech query and to an exact evidence/state
delta.  The unified TaskAdapter and zero-model-contact runner skeleton let
experiments compose these contracts instead of adding ad-hoc per-experiment
scripts.

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
from .core_client import (
    DEFAULT_RAILS_ARM,
    CoreClient,
    FrozenCoreClient,
    FrozenCoreClientError,
    MockCoreClient,
    RequestTiming,
    build_payload_binding,
    build_slice_registry,
    probe_sample_rate_hz,
)
from .errors import RailsError
from .evidence import EvidenceItem, EvidenceSet, RetrievalKeyKind, RetrievalParams
from .knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
    assert_agent_step_binding,
    assert_knowledge_use_binding,
)
from .obs import AudioRef, ObsPacket, SpanRef, default_obs_packet
from .runner import (
    AgentContactPlan,
    AgentContactBatch,
    AgentContactRecord,
    AgentController,
    AgentLoopAdvance,
    AgentLoopResult,
    AgentLoopSummary,
    AgentRuntimeContext,
    AgentTraceSink,
    AgentWaveRecord,
    ContactDAGAdvance,
    ContactDAGCompletion,
    ArmResult,
    RailsRunnerError,
    RunSummary,
    agent_response_sha256,
    run_rails_experiment,
    run_speech_native_agent_loop,
    run_bounded_contact_dag,
)
from .supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .task_adapter import CandidateInventory, TaskAdapter, TaskSample

__all__ = [
    "ArmResult",
    "AgentStateArtifact",
    "AgentStepTransition",
    "AgentContactPlan",
    "AgentContactBatch",
    "AgentContactRecord",
    "AgentController",
    "AgentLoopAdvance",
    "AgentLoopResult",
    "AgentLoopSummary",
    "AgentRuntimeContext",
    "AgentTraceSink",
    "AgentWaveRecord",
    "ContactDAGAdvance",
    "ContactDAGCompletion",
    "AudioRef",
    "CandidateInventory",
    "ConsumptionOutcome",
    "ConsumptionRecord",
    "ConsumptionTrace",
    "CoreClient",
    "DEFAULT_RAILS_ARM",
    "EvidenceItem",
    "EvidenceSet",
    "FrozenCoreClient",
    "FrozenCoreClientError",
    "FusionDecision",
    "KeyFacet",
    "KnowledgeSnapshot",
    "MockCoreClient",
    "ObsPacket",
    "RailsError",
    "RailsRunnerError",
    "QueryState",
    "RankedFacet",
    "RankResult",
    "RequestTiming",
    "RetrievalKeyKind",
    "RetrievalParams",
    "RunSummary",
    "agent_response_sha256",
    "SpanRef",
    "SupplyDose",
    "SupplyForm",
    "SupplyItem",
    "SupplyPacket",
    "TaskAdapter",
    "TaskSample",
    "ValueBundle",
    "assert_agent_step_binding",
    "assert_knowledge_use_binding",
    "build_consumption_trace",
    "build_payload_binding",
    "build_slice_registry",
    "classify_outcome",
    "default_obs_packet",
    "probe_sample_rate_hz",
    "run_rails_experiment",
    "run_speech_native_agent_loop",
    "run_bounded_contact_dag",
]
