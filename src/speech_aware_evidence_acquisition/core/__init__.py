"""Shared Stage-2 engineering foundation (R0): one registry, one driver.

Importing this package registers all built-in components (carriers, evidence
sources, transports, policies, scorers).
"""

from . import carriers, evidence, model, policies, scorers  # noqa: F401 (registration)
from .base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    POLICIES,
    SCORERS,
    TRANSPORTS,
    CoreError,
    EvidenceError,
    EvidenceItem,
    RunResult,
    SampleContext,
    SampleOutcome,
)
from .config import ComposedConfig, ConfigError, compose, protocol_hash
from .driver import load_split, run_experiment
from .model import CoreResponse, FrozenCoreAdapter, FrozenCoreError, LlamaServerTransport
from .split_receipt import SplitReceiptError, VerifiedSplit, load_verified_split
from .tracing import TraceSink, TraceSinkError
from .tracking import LEDGER_COLUMNS, MlflowUnavailable, ledger_row, log_run

__all__ = [
    "CARRIERS", "EVIDENCE_SOURCES", "POLICIES", "SCORERS", "TRANSPORTS",
    "LEDGER_COLUMNS", "ComposedConfig", "ConfigError", "CoreError", "CoreResponse",
    "EvidenceError", "EvidenceItem", "FrozenCoreAdapter", "FrozenCoreError",
    "LlamaServerTransport", "MlflowUnavailable", "RunResult", "SampleContext",
    "SampleOutcome", "SplitReceiptError", "TraceSink", "TraceSinkError",
    "VerifiedSplit", "compose", "ledger_row", "load_split", "load_verified_split",
    "log_run", "protocol_hash", "run_experiment",
]
