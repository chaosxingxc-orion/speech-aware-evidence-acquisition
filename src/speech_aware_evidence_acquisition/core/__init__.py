"""Shared Stage-2 engineering foundation (R0): one registry, one driver.

Importing this package registers all built-in components (carriers, evidence
sources, transports, policies, scorers).
"""

from . import (  # noqa: F401 (registration)
    carriers,
    evidence,
    instructions,
    model,
    policies,
    scorers,
    stage3_algorithms,
)
from .base import (
    AGENT_CONTROLLERS,
    CARRIERS,
    EVIDENCE_SOURCES,
    INSTRUCTION_FILLS,
    JUDGES,
    KNOWLEDGE_BUILDERS,
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_RANKERS,
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
from .configured_transport import build_configured_transport
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
    "AGENT_CONTROLLERS", "CARRIERS", "EVIDENCE_SOURCES", "INSTRUCTION_FILLS",
    "JUDGES",
    "KNOWLEDGE_BUILDERS", "KNOWLEDGE_FUSERS", "KNOWLEDGE_RANKERS",
    "POLICIES", "SCORERS", "TRANSPORTS",
    "LEDGER_COLUMNS", "BundleError", "ComposedConfig", "ConfigError", "CoreError",
    "CoreResponse", "EvidenceError", "EvidenceItem", "FinalizeResult", "FrozenCoreAdapter",
    "FrozenCoreError", "LlamaServerTransport", "MlflowUnavailable", "RunResult",
    "SampleContext", "SampleOutcome", "SplitReceiptError", "TraceSink", "TraceSinkError",
    "VerifiedBundle", "VerifiedSplit", "build_configured_transport", "build_manifest", "bundle_ledger_cells", "compose",
    "finalize_bundle", "ledger_row", "ledger_row_for_bundle", "load_split",
    "load_verified_split", "log_bundle", "log_run", "protocol_hash",
    "require_clean_study_repo", "run_experiment", "run_experiment_bundled", "verify_bundle",
]

# The driver subpackage must resolve lazily (PEP 562): an eager
# `from .driver import ...` here closes the import cycle
# rails/__init__ -> rails.consumption -> core.retrieval -> core/__init__ ->
# core.driver -> core.driver.speech_native -> rails (partially initialized).
_LAZY_DRIVER_NAMES = frozenset(
    {"driver", "load_split", "run_experiment", "run_experiment_bundled"}
)


def __getattr__(name: str) -> object:
    if name in _LAZY_DRIVER_NAMES:
        # importlib.import_module (not `from . import driver`): the from-import
        # form re-enters this __getattr__ through _handle_fromlist while the
        # submodule is still initializing and recurses without terminating.
        import importlib

        driver = importlib.import_module(".driver", __name__)
        if name == "driver":
            return driver
        return getattr(driver, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
