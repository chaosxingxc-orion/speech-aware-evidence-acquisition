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
from .bundle import (
    BundleError,
    FinalizeResult,
    VerifiedBundle,
    build_manifest,
    finalize_bundle,
    require_clean_study_repo,
    verify_bundle,
)
from .config import ComposedConfig, ConfigError, compose, protocol_hash
from .driver import load_split, run_experiment, run_experiment_bundled
from .model import CoreResponse, FrozenCoreAdapter, FrozenCoreError, LlamaServerTransport
from .split_receipt import SplitReceiptError, VerifiedSplit, load_verified_split
from .tracing import TraceSink, TraceSinkError
from .tracking import (
    LEDGER_COLUMNS,
    MlflowUnavailable,
    bundle_ledger_cells,
    ledger_row,
    ledger_row_for_bundle,
    log_bundle,
    log_run,
)

__all__ = [
    "CARRIERS", "EVIDENCE_SOURCES", "POLICIES", "SCORERS", "TRANSPORTS",
    "LEDGER_COLUMNS", "BundleError", "ComposedConfig", "ConfigError", "CoreError",
    "CoreResponse", "EvidenceError", "EvidenceItem", "FinalizeResult", "FrozenCoreAdapter",
    "FrozenCoreError", "LlamaServerTransport", "MlflowUnavailable", "RunResult",
    "SampleContext", "SampleOutcome", "SplitReceiptError", "TraceSink", "TraceSinkError",
    "VerifiedBundle", "VerifiedSplit", "build_manifest", "bundle_ledger_cells", "compose",
    "finalize_bundle", "ledger_row", "ledger_row_for_bundle", "load_split",
    "load_verified_split", "log_bundle", "log_run", "protocol_hash",
    "require_clean_study_repo", "run_experiment", "run_experiment_bundled", "verify_bundle",
]
