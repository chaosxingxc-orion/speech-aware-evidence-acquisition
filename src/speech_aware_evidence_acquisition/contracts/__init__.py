"""Fail-closed E0 engineering contracts.

Model-free contracts frozen by the current owner execution authority
(``SAEA-OWNER-CONSOLIDATED-EXECUTION-CONTRACT-2026-08-04``; the earlier
``SAEA-OWNER-SPEECH-SCOPE-AND-IDENTITY-2026-08-04`` is an inherited source record, not the
current contract): the runtime information boundary, OBS/ORG/SUPPLY/USE trace separation,
exposure-claim schema, the Stage-2 execution-scope guard with its structured
``ExecutionPlan``, and the frozen-core entry gate. Everything here is standard-library only
so the contracts are testable before any ML stack is installed and before any model is
touched.

CHANGED GUARANTEE (owner decision 2026-08-06, docs/owner-decisions-pending.md item 7):
``FrozenCoreGate`` no longer re-hashes the pinned ~34.7 GB GGUF set from bytes on every
gate open. It defaults to a cheap-identity fast path (size + last-modified time + OS file
identity against a cache bound to the runtime receipt's own SHA-256), falling back to a
genuine full SHA-256 re-hash on any cache miss/mismatch, on explicit request
(``full_hash=True``), or at least once per process/session for a real model touch
(the gate's own default). Runtime libraries under ``build/bin`` are UNCHANGED: always fully
hashed, unconditionally, every time (they are ~249 MB, cheap, and are the code that runs).
Stated precisely: the fast path defends against a WRONG, PARTIAL, or ACCIDENTALLY-REPLACED
model set (a swapped-in file, a truncated/resumed download, a stale/foreign data root) — it
does NOT defend against an adversary who edits a GGUF file's bytes in place while
deliberately preserving its size, mtime and OS file identity. See
``FrozenCoreGate._validate_runtime`` and the module comment above
``_SESSION_FULL_HASH_DONE`` for the exact mechanics.

R0 repair refactor stage 1 (behaviour-preserving): this used to be one ~2200-line
``contracts.py`` module. It is now this package, split by concern (errors, the
ExecutionPlan/scope guard, the runtime information boundary, the exposure-ledger
parser, receipt/identity measurement helpers, and the FrozenCoreGate assembly split
across four validation mixins) purely for file size -- every name below was already
part of this module's public surface and remains importable from exactly
``speech_aware_evidence_acquisition.contracts`` as before.
"""

from __future__ import annotations

# NOTE: core.attempts is imported lazily (function-local, see
# _require_exposure_preregistration) rather than at module scope. core/__init__.py
# eagerly imports core.model, which imports THIS module (contracts.py) for
# ExecutionPlan -- a module-level `from .core.attempts import ...` here would make
# importing contracts.py first trigger core/__init__.py, which would try to import
# core.model, which would try to import contracts.py while it is still mid-load
# (ExecutionPlan not yet defined): a circular import. A local import deferred until
# the method actually runs sidesteps this: by then contracts.py has always already
# finished loading.
#
# (R0 repair refactor stage 1: preserved verbatim from the pre-split module. No
# submodule below actually imports core.attempts any more -- the slice-wide
# summation that used it was retired by the 2026-08-06 owner amendment -- but the
# note is kept as-is per the refactor's behaviour-preserving, no-drive-by-fixes
# rule; see the refactor report.)

from .boundary import (
    EXPOSURE_FIELDS,
    FORBIDDEN_RUNTIME_FIELDS,
    TRACE_CHANNELS,
    TraceRecord,
    _CHANNEL_PREFIX,
    _DATE,
    _reject_unserializable,
    assert_information_boundary,
    validate_exposure_claim,
)
from .errors import (
    BoundaryViolation,
    ExecutionScopeError,
    ExposureSchemaError,
    GateClosed,
    TraceContractError,
)
from .gate import FrozenCoreGate
from .gate_exposure import ALLOWED_CARRIER_PROFILES
from .gate_identity import _NLP_REFERENCE_D1_LAYER_KEY, _REFERENCE_SCOPED_CARRIER_LOCK_KEYS
from .gate_runtime import _FULL_COMMIT, _REPORTED_BUILD
from .gate_e0 import _SCORING_MODULE_PREFIX
from .identifiers import (
    CONSTRUCTION_VISIBLE_ARMS,
    CONSTRUCTION_VISIBLE_FIELD,
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    RUN_ID_PATTERN,
    RUNTIME_RECEIPT_SCHEMA,
    RUNTIME_RECEIPT_SCHEMA_V3,
    SCORING_PACKAGE_RELPATH,
    STUDY_SLUG,
    _SHA256,
)
from .identity_cache import (
    RUNTIME_FULL_HASH_ENV,
    RUNTIME_IDENTITY_CACHE_FILENAME,
    RUNTIME_IDENTITY_CACHE_SCHEMA,
    _CHEAP_IDENTITY_FIELDS,
    _ENV_FALSE_VALUES,
    _ENV_TRUE_VALUES,
    _SESSION_FULL_HASH_DONE,
    _cheap_file_identity,
    _cheap_identity_matches,
    _load_identity_cache,
    _resolve_full_hash_override,
    _write_identity_cache,
)
from .ledger import (
    _ALL_LEDGER_COLUMNS,
    _CARRIER_CELL_TOKEN_SPLIT,
    _EXPOSURE_CARRIER_COLUMN,
    _EXPOSURE_RUN_COLUMN,
    _FENCE,
    _HTML_COMMENT_CLOSE,
    _HTML_COMMENT_OPEN,
    _is_separator_row,
    _parse_ledger_tables,
    _split_table_row,
    _strip_same_line_comments,
)
from .plan import (
    ALLOWED_EXECUTION_PROFILES,
    EXECUTION_PLAN_SCHEMA,
    FINAL_REPORT_EXECUTION_PROFILE,
    FINAL_REPORT_SPLIT_ROLE,
    MODEL_TOUCH_PROFILES,
    OWNER_SPLIT_ALLOWANCE_AUTHORISED,
    OWNER_SPLIT_ALLOWANCE_RELDIR,
    OWNER_SPLIT_ALLOWANCE_SCHEMA,
    PAPER_GATE_TOKEN,
    STAGE2_SPLIT_ROLES,
    TEXT_ENCODER_PLAN_SCHEMA,
    ExecutionPlan,
    OwnerSplitAllowance,
    _PAPER_SCALE_MARKERS,
    assert_execution_scope,
    assert_wsl_execution_environment,
    require_owner_split_allowance,
)
from .receipts import (
    _DRIVE_PREFIX,
    _EXCLUDED_LOCK_KEY_LINE,
    _EXCLUDED_LOCK_KEYS_MARKER,
    _GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH,
    _measure_file,
    _resolve_under,
    _safe_relative_path,
    general_audio_deny_lock_keys,
)

__all__ = [
    "ALLOWED_CARRIER_PROFILES",
    "ALLOWED_EXECUTION_PROFILES",
    "BoundaryViolation",
    "CONSTRUCTION_VISIBLE_ARMS",
    "CONSTRUCTION_VISIBLE_FIELD",
    "E0_RECEIPT_SCHEMA",
    "EXECUTION_PLAN_SCHEMA",
    "EXPOSURE_FIELDS",
    "ExecutionPlan",
    "ExecutionScopeError",
    "ExposureSchemaError",
    "FINAL_REPORT_EXECUTION_PROFILE",
    "FINAL_REPORT_SPLIT_ROLE",
    "FORBIDDEN_RUNTIME_FIELDS",
    "FrozenCoreGate",
    "GateClosed",
    "MODEL_LOCK_KEY",
    "MODEL_TOUCH_PROFILES",
    "OWNER_SPLIT_ALLOWANCE_AUTHORISED",
    "OWNER_SPLIT_ALLOWANCE_RELDIR",
    "OWNER_SPLIT_ALLOWANCE_SCHEMA",
    "OwnerSplitAllowance",
    "PAPER_GATE_TOKEN",
    "RUNTIME_FULL_HASH_ENV",
    "RUNTIME_IDENTITY_CACHE_FILENAME",
    "RUNTIME_IDENTITY_CACHE_SCHEMA",
    "RUNTIME_RECEIPT_SCHEMA",
    "RUNTIME_RECEIPT_SCHEMA_V3",
    "RUN_ID_PATTERN",
    "SCORING_PACKAGE_RELPATH",
    "STAGE2_SPLIT_ROLES",
    "STUDY_SLUG",
    "TEXT_ENCODER_PLAN_SCHEMA",
    "TRACE_CHANNELS",
    "TraceContractError",
    "TraceRecord",
    "assert_execution_scope",
    "assert_information_boundary",
    "assert_wsl_execution_environment",
    "general_audio_deny_lock_keys",
    "require_owner_split_allowance",
    "validate_exposure_claim",
    "_ALL_LEDGER_COLUMNS",
    "_CARRIER_CELL_TOKEN_SPLIT",
    "_CHANNEL_PREFIX",
    "_CHEAP_IDENTITY_FIELDS",
    "_DATE",
    "_DRIVE_PREFIX",
    "_ENV_FALSE_VALUES",
    "_ENV_TRUE_VALUES",
    "_EXCLUDED_LOCK_KEYS_MARKER",
    "_EXCLUDED_LOCK_KEY_LINE",
    "_EXPOSURE_CARRIER_COLUMN",
    "_EXPOSURE_RUN_COLUMN",
    "_FENCE",
    "_FULL_COMMIT",
    "_GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH",
    "_HTML_COMMENT_CLOSE",
    "_HTML_COMMENT_OPEN",
    "_NLP_REFERENCE_D1_LAYER_KEY",
    "_PAPER_SCALE_MARKERS",
    "_REFERENCE_SCOPED_CARRIER_LOCK_KEYS",
    "_REPORTED_BUILD",
    "_SCORING_MODULE_PREFIX",
    "_SESSION_FULL_HASH_DONE",
    "_SHA256",
    "_cheap_file_identity",
    "_cheap_identity_matches",
    "_is_separator_row",
    "_load_identity_cache",
    "_measure_file",
    "_parse_ledger_tables",
    "_reject_unserializable",
    "_resolve_full_hash_override",
    "_resolve_under",
    "_safe_relative_path",
    "_split_table_row",
    "_strip_same_line_comments",
    "_write_identity_cache",
]
