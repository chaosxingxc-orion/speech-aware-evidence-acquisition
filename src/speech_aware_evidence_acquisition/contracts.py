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
(``full_hash=True``), or at least once per process/session for a real model touch (the
gate's own default). Runtime libraries under ``build/bin`` are UNCHANGED: always fully
hashed, unconditionally, every time (they are ~249 MB, cheap, and are the code that runs).
Stated precisely: the fast path defends against a WRONG, PARTIAL, or ACCIDENTALLY-REPLACED
model set (a swapped-in file, a truncated/resumed download, a stale/foreign data root) — it
does NOT defend against an adversary who edits a GGUF file's bytes in place while
deliberately preserving its size, mtime and OS file identity. See
``FrozenCoreGate._validate_runtime`` and the module comment above
``_SESSION_FULL_HASH_DONE`` for the exact mechanics.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# NOTE: core.attempts is imported lazily (function-local, see
# _require_exposure_preregistration) rather than at module scope. core/__init__.py
# eagerly imports core.model, which imports THIS module (contracts.py) for
# ExecutionPlan -- a module-level `from .core.attempts import ...` here would make
# importing contracts.py first trigger core/__init__.py, which would try to import
# core.model, which would try to import contracts.py while it is still mid-load
# (ExecutionPlan not yet defined): a circular import. A local import deferred until
# the method actually runs sidesteps this: by then contracts.py has always already
# finished loading.


FORBIDDEN_RUNTIME_FIELDS = frozenset(
    {
        "gold",
        "gold_answer",
        "gold_label",
        "gold_transcript",
        "reference",
        "reference_transcript",
        "reference_answer",
        "test_annotation",
        "test_label",
        "answer_key",
        "future_turn",
        "future_turns",
    }
)

TRACE_CHANNELS = (
    "OBS",
    "ORG",
    "SUPPLY",
    "USE",
    "MODEL_REQUEST",
    "MODEL_RESPONSE",
    "TOOL",
    "COST",
)
_CHANNEL_PREFIX = {
    "OBS": "obs_",
    "ORG": "org_",
    "SUPPLY": "supply_",
    "USE": "use_",
}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_FULL_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
# IMPORTANT 3 (external-threat-model review round 3): the ONE canonical
# identifier pattern for every run_id/attempt_id/session_id this study ever
# embeds verbatim into a filesystem path -- core.attempts (an attempt's
# directory name + file stem), core.tracing (a trace file's stem),
# core.session (a session receipt's file stem), and now ExecutionPlan.validate
# itself. Previously each of those three core modules independently defined
# its OWN compiled copy of this exact same regex text; none of them was ever
# consulted by ExecutionPlan.validate, which accepted "any non-empty string"
# for run_id -- so a run_id containing `/`, `\`, or a `..` traversal segment
# (rejected by every one of those three copies) sailed straight through plan
# construction/validation. Defined HERE, at the bottom of the module's
# dependency graph (contracts.py imports nothing from core/), and imported by
# every consumer instead of re-copied, so there is exactly one definition of
# "a safe identifier" a fourth divergent regex could never quietly drift from.
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

STUDY_SLUG = "speech-aware-evidence-acquisition"
MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf"
E0_RECEIPT_SCHEMA = "saea-e0-closure-receipt-v1"
RUNTIME_RECEIPT_SCHEMA = "saea-runtime-receipt-v2"
# Owner decision 2026-08-06 (docs/owner-decisions-pending.md item 7): a cheap-identity
# fast path for the pinned (34.7 GB) GGUF set only -- runtime libraries under
# build/bin stay fully hashed unconditionally, always (module docstring below,
# FrozenCoreGate._validate_runtime_libraries). The cache is a convenience record,
# never an authority: it is bound to the runtime receipt's OWN sha256 (a new/changed
# receipt invalidates it outright) and any missing/corrupt/mismatched cache falls
# back to a full re-hash, fail-safe. See ``_cheap_file_identity`` and
# ``FrozenCoreGate._validate_runtime`` for exactly what this does and does not
# defend against.
RUNTIME_IDENTITY_CACHE_SCHEMA = "saea-runtime-identity-cache-v1"
RUNTIME_IDENTITY_CACHE_FILENAME = ".saea-runtime-identity-cache.json"
SCORING_PACKAGE_RELPATH = "src/speech_aware_evidence_acquisition/scoring"
_REPORTED_BUILD = re.compile(r"\(([0-9a-f]{7,40})\)")
# IMPORTANT B follow-up (round-2 external-threat-model review): the module
# prefix every real scoring submodule imports under, e.g.
# ``speech_aware_evidence_acquisition.scoring.wer`` -- used to scan
# ``sys.modules`` for scoring code THIS process has already loaded (see
# ``FrozenCoreGate._assert_no_relocated_bytecode_cache``).
_SCORING_MODULE_PREFIX = "speech_aware_evidence_acquisition.scoring"

ALLOWED_EXECUTION_PROFILES = (
    "model-free-check",
    "baseline-reproduction",
    "bounded-discovery-probe",
)
MODEL_TOUCH_PROFILES = frozenset({"baseline-reproduction", "bounded-discovery-probe"})
PAPER_GATE_TOKEN = "OWNER_GO_AND_PAPER_EXECUTION_CONTRACT"
_PAPER_SCALE_MARKERS = ("paper", "confirmatory", "production")

EXECUTION_PLAN_SCHEMA = "saea-execution-plan-v1"
STAGE2_SPLIT_ROLES = frozenset({"discovery", "dev"})
FIRST_SLICE_CAPS = {
    "planned_model_calls": 3000,
    "planned_gpu_hours": 40.0,
    "planned_speech_audio_seconds": 72000,
}
_EXPOSURE_RUN_COLUMN = "run/experiment id"
_EXPOSURE_CARRIER_COLUMN = "speech carrier + split"
# Every column name `_require_exposure_preregistration` looks up on a matched or
# summed row. Used (I2) to decide whether an UNRECOGNIZED table header -- one
# that does not carry `_EXPOSURE_RUN_COLUMN` -- might still be a disguised or
# malformed contract table (sharing a contract column name) and must therefore
# be refused rather than silently ignored.
_ALL_LEDGER_COLUMNS = frozenset(
    {
        _EXPOSURE_RUN_COLUMN,
        _EXPOSURE_CARRIER_COLUMN,
        "execution profile",
        "split role",
        "split identity hash",
        "consumed",
        "calls",
        "speech audio seconds",
        "gpu hours",
    }
)
# Tokenizes the free-text "speech carrier + split" cell (e.g. "earnings21-original
# + earnings22-original + conec, identity layers; e22 subset10 (dev)") so a plan's
# carrier can be matched exactly against a known lock key rather than by
# unanchored substring -- an unanchored `plan.carrier_lock_key in cell_text` check
# lets one row that happens to name two carriers authorize either identity, and
# lets a carrier name that is a prefix of another (e.g. "earnings2" as a substring
# of "earnings22-original") falsely match.
_CARRIER_CELL_TOKEN_SPLIT = re.compile(r"[\s,;+()]+")

# The study's excluded-carrier config is the single source of truth for which
# umbrella-lock entries are explicitly out of research scope (human speech and its
# linguistic content only: ASR, entities, contextual biasing, spoken QA, meeting
# speech). ``e0/d2_leakage.py`` already enforces, as a negative control, that no
# excluded asset name is ever hard-coded in package source -- only read from this
# config; this gate reads the same file for the same reason, so the two names
# named in it never drift apart and package source stays free of them (the only
# permitted occurrences of the excluded names themselves are inside the config
# file and inside refusal tests).
_GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH = "configs/experiment/e0-model-free-closure.yaml"
_EXCLUDED_LOCK_KEYS_MARKER = "excluded_lock_keys:"
_EXCLUDED_LOCK_KEY_LINE = re.compile(r"\s+-\s+(\S+)")


def general_audio_deny_lock_keys(repo_root: Path) -> frozenset[str]:
    """Parse the excluded-carrier denylist from the E0 experiment config.

    Mirrors ``e0.d2_leakage.excluded_lock_keys`` (kept independent rather than
    imported, to avoid a circular import: ``e0.d2_leakage`` already imports from
    this module). Fail-closed: an unreadable config or an empty list refuses
    rather than silently allowing every carrier."""

    config = Path(repo_root) / _GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise GateClosed(
            f"cannot read general-audio exclusion config {config}: {error}"
        ) from error
    keys: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.split("#", 1)[0].rstrip()
        if stripped.strip() == _EXCLUDED_LOCK_KEYS_MARKER:
            collecting = True
            continue
        if collecting:
            match = _EXCLUDED_LOCK_KEY_LINE.fullmatch(stripped)
            if match:
                keys.append(match.group(1))
                continue
            if stripped.strip():
                break
    if not keys:
        raise GateClosed(f"no excluded_lock_keys parsed from {config}")
    return frozenset(keys)


# The umbrella lock's speech-aware-* profiles (docs/datasets.lock.json `profiles`,
# 2026-08-04 semantic migration) that may legitimately back a plan carrier: core
# evaluation carriers, secondary public carriers, entity/rare-word diagnostics and
# small optional public assets. `speech-aware-annotations` is deliberately excluded:
# it holds annotation-only entries with no speech audio of their own, so it can
# never back a model touch. `frozen-baseline`, `local-candidates`,
# `retained-cross-domain` and `deferred` are non-speech-aware profiles and are
# never allowed here.
ALLOWED_CARRIER_PROFILES = frozenset(
    {
        "speech-aware-core",
        "speech-aware-secondary",
        "speech-aware-diagnostics",
        "speech-aware-small-public",
    }
)

# IMPORTANT 2 (external-threat-model review round 3): the D1 identity
# artifact layer key holding per-file (id, bytes, sha256) reference-file
# identity -- ``FrozenCoreGate.verify_reference_identity`` reads this the
# same way ``verify_media_identity`` reads the ``media`` layer key.
_NLP_REFERENCE_D1_LAYER_KEY = "nlp_references"
# Mirrors ``data.references._NLP_SUBDIR`` exactly (kept independent rather
# than imported, same reasoning as ``general_audio_deny_lock_keys``'s own
# docstring: this module stays stdlib-only and never imports ``data.*``) --
# the only carrier lock keys ``reference_tokens`` can actually read a
# reference layer for today. ``conec`` is deliberately absent: it has no
# reference layer of its own that ``reference_tokens`` resolves (its D1
# identity layer is named ``e21_nlp_references``, a DIFFERENT key with
# DIFFERENT bytes than earnings21-original's own ``nlp_references`` --
# scoring conec was never reachable through ``reference_tokens`` and this
# gate correctly refuses it too rather than silently reusing earnings21's
# facts for a key that names a distinct file set). See
# docs/owner-decisions-pending.md item 5.
_REFERENCE_SCOPED_CARRIER_LOCK_KEYS = frozenset({"earnings21-original", "earnings22-original"})


class BoundaryViolation(ValueError):
    """A payload tries to move gold/reference/test/future information across the runtime boundary."""


class TraceContractError(ValueError):
    """A trace record violates the OBS/SUPPLY separation or serializability contract."""


class ExposureSchemaError(ValueError):
    """An exposure claim does not carry the four required fields in the required shapes."""


class GateClosed(RuntimeError):
    """The frozen-core entry gate refuses: E0 closure or the runtime receipt is missing/invalid."""


class ExecutionScopeError(RuntimeError):
    """The requested execution profile is outside this study repository's Stage-2 authority."""


def assert_execution_scope(profile: object) -> str:
    """Fail-closed Stage-2 execution-scope guard (consolidated contract §6/§7, 续91/续92).

    This study repository accepts exactly the profiles in ``ALLOWED_EXECUTION_PROFILES``.
    ``paper-scale-confirmatory`` — and any other paper/confirmatory/production-scale
    profile — is never accepted here: Stage-3 work requires promotion to an independent
    ``papers/<slug>`` repository under ``OWNER_GO_AND_PAPER_EXECUTION_CONTRACT``. Unknown
    or forged profile strings are refused rather than normalized.
    """

    if not isinstance(profile, str) or not profile.strip():
        raise ExecutionScopeError("execution profile must be a non-empty string")
    if profile in ALLOWED_EXECUTION_PROFILES:
        return profile
    lowered = profile.lower()
    if any(marker in lowered for marker in _PAPER_SCALE_MARKERS):
        raise ExecutionScopeError(
            f"execution profile {profile!r} is paper-scale: this Stage-2 study repository "
            f"never runs it; Stage-3 requires {PAPER_GATE_TOKEN} and an independent "
            "papers/<slug> repository (Decision-Log 续91/续92)"
        )
    raise ExecutionScopeError(
        f"unknown execution profile {profile!r}; allowed Stage-2 profiles are "
        f"{ALLOWED_EXECUTION_PROFILES} (fail-closed)"
    )


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured, contract-bound plan for one model-facing run (v1, umbrella 续93).

    Every field is a value the consolidated execution contract already freezes
    (profiles, Stage-2 split roles, first-slice budget caps, hash disciplines); the
    schema is therefore not speculative design and may be extended at R0 only via a
    dated owner decision. A profile label alone never authorizes a run: the gate
    validates this plan before reading any receipt, so a paper-scale run cannot be
    smuggled in under an allowed profile name.
    """

    run_id: str
    execution_profile: str
    carrier_lock_key: str
    split_role: str
    split_identity_hash: str
    planned_model_calls: int
    planned_gpu_hours: float
    planned_speech_audio_seconds: int
    protocol_hash: str
    # Optional, defaulted (R0 repair T4, invariant I6): a mandatory-with-no-default
    # field here would turn e0/generate.py's frozen dry-run ExecutionPlan construction
    # into a hard TypeError unrelated to any gate check (e0/ is frozen and never
    # constructs a real attempt_id). Refusal for a missing/malformed attempt_id
    # happens explicitly where a model touch actually becomes possible --
    # FrozenCoreAdapter construction, the one true model request path -- not here.
    attempt_id: str | None = None
    schema: str = EXECUTION_PLAN_SCHEMA
    study: str = STUDY_SLUG

    def validate(self) -> "ExecutionPlan":
        if self.schema != EXECUTION_PLAN_SCHEMA:
            raise ExecutionScopeError(
                f"execution plan schema must be {EXECUTION_PLAN_SCHEMA!r}, got {self.schema!r}"
            )
        if self.study != STUDY_SLUG:
            raise ExecutionScopeError(
                f"execution plan study identity must be {STUDY_SLUG!r}, got {self.study!r}"
            )
        if not isinstance(self.run_id, str) or RUN_ID_PATTERN.fullmatch(self.run_id) is None:
            raise ExecutionScopeError(
                f"execution plan run_id must match {RUN_ID_PATTERN.pattern!r} (no path "
                "separator, no leading dot/dash, non-empty) -- IMPORTANT 3 fix-wave3: a "
                "run_id is embedded verbatim into filesystem paths downstream (core.attempts, "
                f"core.tracing, core.bundle); got {self.run_id!r}"
            )
        # attempt_id stays optional (see the field's own comment above) but, when
        # present, must satisfy the SAME identifier discipline as run_id -- it too is
        # embedded verbatim into a filesystem path (core.attempts.AttemptStore,
        # core.bundle's attempt.state_path).
        if self.attempt_id is not None and (
            not isinstance(self.attempt_id, str) or RUN_ID_PATTERN.fullmatch(self.attempt_id) is None
        ):
            raise ExecutionScopeError(
                f"execution plan attempt_id must be None or match {RUN_ID_PATTERN.pattern!r}, "
                f"got {self.attempt_id!r}"
            )
        assert_execution_scope(self.execution_profile)
        if not isinstance(self.carrier_lock_key, str) or not self.carrier_lock_key.strip():
            raise ExecutionScopeError("execution plan carrier_lock_key must be a non-empty string")
        if not isinstance(self.split_role, str) or not self.split_role.strip():
            raise ExecutionScopeError("execution plan split_role must be a non-empty string")
        if self.split_role == "confirmatory":
            raise ExecutionScopeError(
                "confirmatory execution is not a Stage-2 authority: reading confirmatory "
                f"results requires {PAPER_GATE_TOKEN} (independent paper repository) or a "
                "dated owner allowance; relabeling the profile does not change this"
            )
        if self.split_role not in STAGE2_SPLIT_ROLES:
            raise ExecutionScopeError(
                f"unknown split role {self.split_role!r}; Stage-2 roles are "
                f"{sorted(STAGE2_SPLIT_ROLES)} (fail-closed)"
            )
        for label, value in (
            ("split_identity_hash", self.split_identity_hash),
            ("protocol_hash", self.protocol_hash),
        ):
            if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
                raise ExecutionScopeError(f"execution plan {label} must be a 64-hex SHA-256")
        for field_name, cap in FIRST_SLICE_CAPS.items():
            value = getattr(self, field_name)
            integral = field_name in ("planned_model_calls", "planned_speech_audio_seconds")
            if (
                isinstance(value, bool)
                or not isinstance(value, int if integral else (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ExecutionScopeError(
                    f"execution plan {field_name} must be a finite positive "
                    f"{'integer' if integral else 'number'}"
                )
            if value > cap:
                raise ExecutionScopeError(
                    f"execution plan {field_name}={value} exceeds the frozen first-slice "
                    f"cap {cap}; a larger run is paper-scale regardless of its profile label"
                )
        return self


def assert_information_boundary(payload: object, _path: str = "$") -> None:
    """Recursively reject any forbidden field name anywhere in a runtime-bound payload.

    Fail-closed: the top-level payload must be a mapping, and unknown container types
    are rejected rather than skipped.
    """

    if _path == "$" and not isinstance(payload, Mapping):
        raise BoundaryViolation(f"runtime payload must be a mapping, got {type(payload).__name__}")
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if not isinstance(key, str):
                raise BoundaryViolation(f"{_path}: non-string key {key!r}")
            if key.lower() in FORBIDDEN_RUNTIME_FIELDS:
                raise BoundaryViolation(f"{_path}.{key}: forbidden field crosses the boundary")
            assert_information_boundary(value, f"{_path}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_information_boundary(item, f"{_path}[{index}]")
    elif payload is not None and not isinstance(payload, (str, int, float, bool)):
        raise BoundaryViolation(f"{_path}: unserializable value type {type(payload).__name__}")


@dataclass(frozen=True)
class TraceRecord:
    """One versioned trace event; research-axis payload keys are namespaced per channel."""

    channel: str
    record_id: str
    payload: Mapping[str, object]

    def validate(self) -> "TraceRecord":
        if self.channel not in TRACE_CHANNELS:
            raise TraceContractError(f"unknown trace channel {self.channel!r}")
        if not self.record_id or not isinstance(self.record_id, str):
            raise TraceContractError("record_id must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise TraceContractError("payload must be a mapping")
        prefix = _CHANNEL_PREFIX.get(self.channel)
        axis_prefixes = tuple(_CHANNEL_PREFIX.values())
        for key in self.payload:
            if not isinstance(key, str):
                raise TraceContractError(f"non-string payload key {key!r}")
            if prefix is not None and not key.startswith(prefix):
                raise TraceContractError(
                    f"{self.channel} payload key {key!r} must start with {prefix!r} "
                    "(OBS, ORG, SUPPLY and USE namespaces are disjoint by contract)"
                )
            other_prefixes = tuple(candidate for candidate in axis_prefixes if candidate != prefix)
            if prefix is not None and key.startswith(other_prefixes):
                raise TraceContractError(
                    f"{self.channel} payload smuggles another research-axis field {key!r}"
                )
        assert_information_boundary(dict(self.payload))
        return self

    def serialize(self) -> str:
        self.validate()
        try:
            return json.dumps(
                {
                    "channel": self.channel,
                    "record_id": self.record_id,
                    "payload": self.payload,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=_reject_unserializable,
            )
        except TypeError as error:
            raise TraceContractError(f"payload is not JSON-serializable: {error}") from error

    def content_hash(self) -> str:
        return hashlib.sha256(self.serialize().encode("utf-8")).hexdigest()


def _reject_unserializable(value: object) -> object:
    raise TypeError(f"unserializable trace value of type {type(value).__name__}")


EXPOSURE_FIELDS = ("scope", "date", "counts", "inherited")


def validate_exposure_claim(claim: Mapping[str, object]) -> Mapping[str, object]:
    """Validate the four-field exposure claim contract (scope/date/counts/inherited)."""

    if not isinstance(claim, Mapping):
        raise ExposureSchemaError("exposure claim must be a mapping")
    if set(claim) != set(EXPOSURE_FIELDS):
        raise ExposureSchemaError(
            f"exposure claim must have exactly the fields {EXPOSURE_FIELDS}, got {sorted(claim)}"
        )
    if not isinstance(claim["scope"], str) or not claim["scope"].strip():
        raise ExposureSchemaError("scope must be a non-empty string")
    if not isinstance(claim["date"], str) or _DATE.fullmatch(claim["date"]) is None:
        raise ExposureSchemaError("date must be YYYY-MM-DD")
    counts = claim["counts"]
    if not isinstance(counts, Mapping) or not counts:
        raise ExposureSchemaError("counts must be a non-empty mapping")
    for key, value in counts.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int):
            raise ExposureSchemaError(f"counts[{key!r}] must be an integer")
        if value < 0:
            raise ExposureSchemaError(f"counts[{key!r}] must be >= 0")
    if not isinstance(claim["inherited"], str) or not claim["inherited"].strip():
        raise ExposureSchemaError(
            "inherited must be a non-empty statement of inherited prior exposure"
        )
    return claim


def _safe_relative_path(value: object, label: str) -> str:
    """Reject absolute paths, drive letters, backslashes and any traversal segment."""

    if not isinstance(value, str) or not value.strip():
        raise GateClosed(f"{label} must be a non-empty relative path")
    if "\\" in value or value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise GateClosed(f"{label} must be a relative POSIX path, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise GateClosed(f"{label} contains empty or traversal segments: {value!r}")
    return value


def _resolve_under(root: Path, relative: str, label: str) -> Path:
    """Resolve a receipt-declared relative path strictly inside its controlled root."""

    try:
        root_resolved = Path(root).resolve(strict=True)
    except OSError as error:
        raise GateClosed(f"{label}: controlled root {root} is unavailable: {error}") from error
    candidate = (root_resolved / relative).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise GateClosed(f"{label} escapes its controlled root: {relative!r}")
    if not candidate.is_file():
        raise GateClosed(f"{label} does not exist as a regular file: {relative!r}")
    return candidate


def _split_table_row(line: str) -> tuple[bool, list[str]]:
    """Recognize a markdown table row and split it into raw (unlowered) cells.

    A "row" is any line whose stripped form starts and ends with ``|`` -- this
    intentionally matches header, separator and data rows alike; callers tell
    them apart afterward."""

    stripped = line.strip()
    if len(stripped) < 2 or not (stripped.startswith("|") and stripped.endswith("|")):
        return False, []
    return True, [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_separator_row(cells: list[str]) -> bool:
    """A GFM header-separator row: every cell is only ``-``, ``:`` or space."""

    return bool(cells) and all(not cell.strip("-: ") for cell in cells)


# IMPORTANT C (round-2 external-threat-model review): the ledger parser must
# know it is reading MARKDOWN, not merely "any line that looks like a table
# row". Two GFM constructs make content invisible to a human reading the
# RENDERED ledger while still being plain text to a naive line-by-line
# scanner: an HTML comment (``<!-- ... -->``, possibly spanning many lines)
# and a fenced code block (opened/closed by a line of 3+ backticks or
# tildes, the natural way to document the row format as an illustrative
# example). Demonstrated: a complete contract table inside an HTML comment
# parsed as a real, binding registration that a human reading the rendered
# ledger sees NOTHING of; a contract table inside a fenced example block
# silently exhausted the campaign slice cap.
#
# IMPORTANT 1 fix-wave3 (round-3 external-threat-model review): the round-2
# fix above over-corrected. Its own justification -- "a line containing
# ``<!--`` is never itself a genuine table row (a real row is exactly
# ``| ... |``)" -- is FALSE: ``| 2026-08-05 | RUN-OLD | ... | scope amended
# <!-- see git history --> |`` is a completely genuine, GFM-legal table row
# that GitHub renders normally, hiding only the comment text inside its last
# cell. Consuming that WHOLE LINE (as round-2 did, for ANY line containing
# ``<!--``) made the ENTIRE row -- including its budget-relevant cells:
# ``calls``, ``consumed``, etc. -- invisible to every check below, even
# though a human reading the rendered ledger sees the row perfectly clearly.
# Demonstrated: an honest ledger whose slice total was 3100 calls (correctly
# REFUSED) was wrongly ACCEPTED once an inline ``<!-- ... -->`` was added
# inside one row's notes cell; a ``consumed = yes`` row became invisible to
# the consumed check the same way; and an UNCLOSED ``<!--`` inside a cell
# silently dropped every row below it for the rest of the document while
# ``saw_contract_header`` stayed True, so the gate never failed closed at
# all -- exactly the "silently drop rows" failure mode I2 already exists to
# prevent, just via a different trigger.
#
# The fix distinguishes two shapes precisely:
#
# 1. A comment that both OPENS and CLOSES on the SAME line -- the demonstrated
#    defect's shape -- is stripped from that line's TEXT (see
#    :func:`_strip_same_line_comments`), leaving every surrounding
#    character -- including the REST of that same row's other cells --
#    completely untouched. Row/header recognition then runs on the
#    comment-stripped text exactly as if the comment had never been there,
#    so a genuine row is never lost, and a ``consumed``/budget cell hidden
#    only by an inline comment is read correctly.
# 2. A comment that OPENS on one line without also closing on it begins a
#    genuinely multi-line span; every line up to and including the one that
#    finally closes it is consumed WHOLE, UNCHANGED from the round-2
#    behavior -- this is what keeps the round-2 "a complete table hidden
#    inside a comment block" case (its own dedicated header-then-rows-then-
#    close-marker shape, each on its own line) invisible exactly as before:
#    that case never involves a genuine, otherwise-recognizable row losing
#    only its comment tail, so it needs no different treatment.
#
# A comment opened this way that NEVER closes before end-of-document is no
# longer silently equivalent to "everything after it is invisible prose" --
# it now FAILS CLOSED (:class:`GateClosed`) at the end of parsing, since an
# unterminated comment could, in principle, be hiding a real row's remainder
# (or an entire real table) that this parser can never distinguish from
# intentionally-hidden draft content once the comment never closes.
_HTML_COMMENT_OPEN = "<!--"
_HTML_COMMENT_CLOSE = "-->"
_FENCE = re.compile(r"^(`{3,}|~{3,})")


def _strip_same_line_comments(line: str) -> tuple[str, bool]:
    """Remove every ``<!-- ... -->`` span that both opens AND closes on
    ``line``, leaving all other characters -- including a row's OTHER cells
    on either side -- completely untouched; handles more than one such span
    per line. Returns ``(visible_text, opens_unterminated)`` where
    ``opens_unterminated`` is True iff, after removing every already-closed
    same-line span, the text still contains a ``<!--`` with no matching
    ``-->`` later on this SAME line -- the caller's signal to fall back to
    the existing whole-line multi-line-comment consumption, unchanged."""

    parts: list[str] = []
    i = 0
    n = len(line)
    while True:
        open_idx = line.find(_HTML_COMMENT_OPEN, i)
        if open_idx == -1:
            parts.append(line[i:])
            return "".join(parts), False
        close_idx = line.find(_HTML_COMMENT_CLOSE, open_idx + len(_HTML_COMMENT_OPEN))
        if close_idx == -1:
            parts.append(line[i:open_idx])
            return "".join(parts), True
        parts.append(line[i:open_idx])
        i = close_idx + len(_HTML_COMMENT_CLOSE)


def _parse_ledger_tables(text: str) -> list[dict[str, str]]:
    """Parse EVERY markdown table in ``text``, not just the first (I2).

    The reproduced defect: the old parser walked lines once and stopped at the
    first non-table line found after its header, so a second table -- or even
    a single stray prose line between two data rows of the same table -- made
    every row after it invisible to the budget/duplicate/consumed checks.

    A table row immediately followed by a GFM separator row (dashes/colons
    only) is unambiguously a header, independent of anything earlier or later
    in the document -- so a stray prose line elsewhere can never end a table
    early, and a later plain data row can never be mistaken for a new header.
    A recognized header (its lowered cells carry ``_EXPOSURE_RUN_COLUMN``)
    opens a contract table: every following data row -- up to the next header
    -- is captured as a ``{column_name: cell}`` mapping keyed by THAT table's
    own header (M4: a row whose cell count disagrees with its governing
    header is refused outright, never positionally misaligned). A header
    that is NOT recognized either belongs to a genuinely unrelated table
    (silently ignored, e.g. a legend/description table) or, if it shares any
    contract column name or the current contract header's width, is refused
    fail-closed rather than risking silently dropped budget rows (I2).

    IMPORTANT C (round-2 external-threat-model review): before any row/header
    recognition, every line is first classified as being inside a fenced code
    block or an HTML comment; a line consumed whole by either state is never
    treated as a row, a separator, or a header, and never allowed to close
    the CURRENTLY open contract table (matching the existing "a stray prose
    line never drops rows below it" discipline: content the rendered ledger
    hides is exactly as inert as ordinary prose to the table state machine).
    A whole table hidden inside a comment or framed by a documentation fence
    is therefore simply invisible -- IGNORED, never a registration and never
    a fail-closed refusal on their own: a comment is a legitimate way to keep
    old/draft content out of the rendered view without deleting it, and
    content a human reader cannot see can never satisfy this file's whole
    purpose as the OWNER-VISIBLE pre-registration record either way, so there
    is nothing gained by refusing outright over silently not treating it as
    binding.

    IMPORTANT 1 fix-wave3 (round-3 external-threat-model review): comment
    handling is now CELL-TEXT-aware, not merely line-level -- see the module
    comment above :func:`_strip_same_line_comments` for exactly what changed
    and why. A comment that never closes before end-of-document fails closed
    rather than silently discarding every row after it."""

    lines = text.splitlines()
    n = len(lines)
    current_header: list[str] | None = None
    rows: list[dict[str, str]] = []
    saw_contract_header = False
    in_comment = False
    in_fence = False
    fence_char = ""
    fence_len = 0
    i = 0
    while i < n:
        line = lines[i]

        if in_comment:
            if _HTML_COMMENT_CLOSE in line:
                in_comment = False
            i += 1
            continue

        stripped_for_fence = line.strip()
        if in_fence:
            fence_match = _FENCE.match(stripped_for_fence)
            if (
                fence_match
                and fence_match.group(1)[0] == fence_char
                and len(fence_match.group(1)) >= fence_len
            ):
                in_fence = False
            i += 1
            continue
        fence_match = _FENCE.match(stripped_for_fence)
        if fence_match:
            in_fence = True
            fence_char = fence_match.group(1)[0]
            fence_len = len(fence_match.group(1))
            i += 1
            continue

        # IMPORTANT 1 fix-wave3: strip any comment(s) that both open AND close
        # on THIS line from its text, leaving every surrounding character --
        # including the rest of the SAME row's other cells -- untouched, and
        # continue treating the (possibly modified) line as an ordinary
        # row/header/data candidate below. A comment that opens here WITHOUT
        # also closing here is a genuinely multi-line span: fall back to the
        # existing whole-line consumption, unchanged from round-2.
        line, opens_unterminated = _strip_same_line_comments(line)
        if opens_unterminated:
            in_comment = True
            i += 1
            continue

        is_row, cells = _split_table_row(line)
        if not is_row:
            i += 1
            continue
        if _is_separator_row(cells):
            # A bare separator with nothing recognized as its header: never
            # data, never a header by itself -- skip wherever it appears.
            i += 1
            continue
        next_is_row, next_cells = (
            _split_table_row(lines[i + 1]) if i + 1 < n else (False, [])
        )
        if next_is_row and _is_separator_row(next_cells):
            lowered = [cell.lower() for cell in cells]
            if len(lowered) != len(set(lowered)):
                raise GateClosed(
                    f"exposure ledger table header has duplicate columns: {cells!r}"
                )
            if _EXPOSURE_RUN_COLUMN in lowered:
                current_header = lowered
                saw_contract_header = True
            else:
                overlap = set(lowered) & _ALL_LEDGER_COLUMNS
                same_width = current_header is not None and len(lowered) == len(current_header)
                if overlap or same_width:
                    raise GateClosed(
                        f"exposure ledger contains a table header {cells!r} that is not "
                        f"the recognized contract header ({_EXPOSURE_RUN_COLUMN!r} column) "
                        "but shares contract-shaped columns or width with one; refusing "
                        "rather than silently ignoring rows that might be contract rows "
                        "(I2 fail-closed)"
                    )
                current_header = None  # a genuinely unrelated table: its rows are ignored
            i += 2  # consume header + separator row together
            continue
        # Not a header (no separator immediately follows): a data row of
        # whichever contract table is currently active, if any.
        if current_header is not None:
            if len(cells) != len(current_header):
                raise GateClosed(
                    f"exposure ledger row {cells!r} has {len(cells)} cells but its "
                    f"table header has {len(current_header)} columns {current_header!r}; "
                    "refusing rather than guessing column alignment (M4)"
                )
            rows.append(dict(zip(current_header, cells)))
        i += 1
    # IMPORTANT 1 fix-wave3: an HTML comment that opens somewhere in the
    # document and NEVER closes before end-of-file must fail closed, not
    # silently behave as "everything after it is invisible prose" -- the
    # reproduced defect (3 registered rows / 3500 calls silently became 0
    # rows / 0 calls, with saw_contract_header still True so nothing ever
    # refused). An unterminated comment could in principle be hiding a real
    # row's remainder, or an entire real table, that this line-oriented
    # parser can never distinguish from deliberately-hidden draft content
    # once the comment never closes -- so it refuses outright instead of
    # guessing either way.
    if in_comment:
        raise GateClosed(
            "exposure ledger contains an unterminated HTML comment (a `<!--` with no "
            "matching `-->` before end of file); refusing rather than silently treating "
            "everything after it as invisible prose -- a genuine row could be hidden "
            "behind it (fail-closed)"
        )
    if not saw_contract_header:
        raise GateClosed(
            f"exposure ledger lacks a table header with a {_EXPOSURE_RUN_COLUMN!r} column"
        )
    return rows


def _measure_file(path: Path, label: str) -> tuple[int, str]:
    """Re-read the actual bytes: return (size, sha256). Never trust recorded strings."""

    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise GateClosed(f"{label}: cannot read bytes: {error}") from error
    return size, digest.hexdigest()


# ---------------------------------------------------------------------------
# GGUF cheap-identity fast path (owner decision 2026-08-06,
# docs/owner-decisions-pending.md item 7): re-hashing the pinned ~34.7 GB GGUF
# set on EVERY gate open (142-175s measured over the WSL2 9p mount onto the
# Windows-hosted data root) makes routine verification painful without making
# any run safer than a cheap, well-scoped identity check already would for the
# overwhelmingly common case -- nothing about the files changed since the last
# genuine full verification. STATED GUARANTEE, precisely, not overstated: a
# fast-path PASS proves the file at this path has the same size, last-modified
# time and OS file identity (inode+device) as it did the last time this
# process (or an earlier trusted cache write) actually read every byte and
# recomputed its SHA-256. It defends against a WRONG, PARTIAL, or
# ACCIDENTALLY-REPLACED model set -- a different file swapped in, a truncated
# or resumed download, a stale/foreign directory pointed to by
# SPEECHRL_DATA_DIR. It does NOT defend against an adversary who edits a
# file's bytes IN PLACE while deliberately preserving its size, mtime and file
# identity (e.g. `open(path, "r+b")` followed by `os.utime()` restoring the
# original timestamp) -- that is a genuine, accepted, owner-approved residual
# weakness, not an oversight (see the module/FrozenCoreGate docstrings and
# docs/owner-decisions-pending.md item 7 for the full record; pinned by
# ``tests/contract/test_runtime_identity_fastpath.py``).
# ---------------------------------------------------------------------------

# Process-local floor: ``FrozenCoreGate.assert_model_touch_allowed``'s own
# default (``full_hash=None``, and no recognized ``RUNTIME_FULL_HASH_ENV``
# override -- see below) must still perform ONE genuine full SHA-256
# verification of the pinned GGUF set, per runtime-receipt identity, per
# process, before it will ever trust a fast-path cheap-identity cache -- even
# a pre-existing, on-disk, apparently-valid one written by an EARLIER process
# (e.g. a prior ``scripts/reproduce.sh`` dry run). Keyed by the runtime
# receipt's own SHA-256 (not a bare process-wide bool) so a receipt rotation
# mid-process is treated as a genuinely new floor, never silently inherited
# from a stale receipt this process happened to fully verify earlier. There is
# no cross-process synchronization by design: "session" here means exactly
# "this interpreter process" (reset only by process restart) -- a real model
# touch (``core.model.FrozenCoreAdapter``, which never overrides ``full_hash``
# and runs in its own freshly-started process) therefore always pays the full
# cost at least once before it can ever be fast-pathed within that same run,
# UNLESS ``RUNTIME_FULL_HASH_ENV`` happens to already be set to a fast value in
# that process's own environment -- an operational responsibility of whatever
# launched it, not a gap in this module (see ``RUNTIME_FULL_HASH_ENV``'s own
# comment for why ``scripts/reproduce.sh`` setting it is safe: the export is
# scoped to that script's own short-lived subprocess tree, never a parent
# interactive shell).
_SESSION_FULL_HASH_DONE: set[str] = set()

# ``src/.../e0/**`` is a frozen, previously-reviewed surface this task does not
# touch, so the CLI (``e0.generate._verify``, invoked by ``scripts/
# reproduce.sh``) cannot be given a new ``--full`` argument to forward as an
# explicit ``full_hash=`` keyword the way a real caller could. Instead, when a
# caller passes ``full_hash=None`` (its own default -- the CLI never overrides
# this), this environment variable is consulted BEFORE falling back to the
# session/process floor above: a recognized value is honored as if the caller
# had passed that literal bool; anything unset or unrecognized falls through
# to the safe auto/session behavior (never silently treated as either explicit
# value). ``scripts/reproduce.sh`` exports this only around its own `python -m
# ... verify` invocation -- a subprocess of that one script run, never
# persisted into the caller's interactive shell -- so a real model touch
# started independently, in a separate shell command, is unaffected by it.
RUNTIME_FULL_HASH_ENV = "SAEA_RUNTIME_FULL_HASH"
_ENV_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_ENV_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _resolve_full_hash_override(explicit: bool | None) -> bool | None:
    """An explicit caller value always wins. Otherwise a recognized
    ``RUNTIME_FULL_HASH_ENV`` value is honored as if it had been passed
    explicitly. Anything unset or unrecognized returns ``None`` unchanged --
    "let the auto/session floor decide" (the safe behavior) -- a malformed
    environment value therefore fails toward the SAFE (full-hash) side, never
    silently toward the fast one."""

    if explicit is not None:
        return explicit
    raw = os.environ.get(RUNTIME_FULL_HASH_ENV)
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in _ENV_TRUE_VALUES:
        return True
    if normalized in _ENV_FALSE_VALUES:
        return False
    return None


_CHEAP_IDENTITY_FIELDS = ("size", "mtime_ns", "st_ino", "st_dev")


def _cheap_file_identity(path: Path, label: str) -> dict[str, int]:
    """No-byte-read file identity: size, last-modified time (nanoseconds) and
    OS file identity (inode + device). ``os.stat`` is used UNCHANGED on every
    platform this study runs on: on POSIX (the WSL2/ext4 compute authority)
    ``st_ino``/``st_dev`` are the kernel's own inode/device pair; on Windows,
    CPython's own ``os.stat`` already populates the SAME two attributes from
    the NTFS file ID via ``GetFileInformationByHandle`` -- verified
    empirically on this checkout (stable and non-zero across repeated
    ``os.stat()`` calls on the same file) -- so no separate ``ctypes``/
    ``nFileIndex`` path was needed."""

    try:
        info = path.stat()
    except OSError as error:
        raise GateClosed(f"{label}: cannot stat for cheap identity check: {error}") from error
    return {
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "st_ino": info.st_ino,
        "st_dev": info.st_dev,
    }


def _cheap_identity_matches(current: Mapping[str, int], cached: object) -> bool:
    """Every cheap-identity field must be present, integral and equal. A
    missing/malformed cached record (or a non-mapping) never matches -- the
    caller then falls back to a full re-hash, fail-safe."""

    if not isinstance(cached, Mapping):
        return False
    for field in _CHEAP_IDENTITY_FIELDS:
        value = cached.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or current[field] != value:
            return False
    return True


def _load_identity_cache(
    cache_path: Path, receipt_sha256: str
) -> Mapping[str, Mapping[str, int]] | None:
    """Fail-safe: any missing, unreadable, malformed or receipt-mismatched
    cache is treated as simply ABSENT (never fail-open) -- the caller then
    re-hashes every file for real. Never raises."""

    try:
        raw = cache_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, Mapping):
        return None
    if (
        document.get("schema") != RUNTIME_IDENTITY_CACHE_SCHEMA
        or document.get("study") != STUDY_SLUG
        # Bound to the runtime receipt's own bytes (item 1c): any change to
        # the receipt -- a new build, a re-pinned file, even an unrelated
        # field -- invalidates every cached identity record outright.
        or document.get("runtime_receipt_sha256") != receipt_sha256
    ):
        return None
    entries = document.get("gguf_files")
    if not isinstance(entries, Mapping):
        return None
    return entries


def _write_identity_cache(
    cache_path: Path, receipt_sha256: str, entries: Mapping[str, Mapping[str, int]]
) -> None:
    """Best-effort convenience write: the cache is never an authority (module
    docstring above), so a write failure (read-only mount, disk full,
    permissions) must never fail a gate check that has already genuinely
    succeeded -- it only means the NEXT gate open pays the full cost again.
    Atomic (write-then-replace) so a process interrupted mid-write never
    leaves a half-written, misleadingly-parseable cache file behind."""

    document = {
        "schema": RUNTIME_IDENTITY_CACHE_SCHEMA,
        "study": STUDY_SLUG,
        "runtime_receipt_sha256": receipt_sha256,
        "gguf_files": entries,
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_name(f"{cache_path.name}.tmp-{os.getpid()}")
        tmp_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        tmp_path.replace(cache_path)
    except OSError:
        pass


@dataclass(frozen=True)
class FrozenCoreGate:
    """Fail-closed entry gate in front of every frozen-core (model) touch.

    The gate opens only when both receipts exist, carry the study-versioned schemas,
    and are **true**, not merely well-formed:

    - the E0 closure receipt binds every D1-D4 deliverable to an artifact file whose
      recomputed SHA-256 matches the receipt; the D3 artifact's frozen scoring-source
      hashes are additionally re-measured against the live tree under ``source_root``,
      and the scoring package may contain no source file the freeze does not name;
    - the runtime receipt binds the frozen model lock key from the umbrella
      ``docs/datasets.lock.json`` to canonical relative paths under the controlled
      asset root; the gate always re-reads the llama.cpp launcher binary AND every
      runtime library in the launcher's directory (exact set — an unlisted or
      missing file refuses) and recomputes size and SHA-256 itself. The pinned GGUF
      set (owner decision 2026-08-06, docs/owner-decisions-pending.md item 7) is, by
      default, verified via a cheap size+mtime+OS-file-identity check against a
      cache bound to the runtime receipt's own SHA-256, falling back to a full
      SHA-256 re-hash on any cache miss/mismatch, on explicit request
      (``full_hash=True``), or at least once per process for a real model touch
      (``assert_model_touch_allowed``'s own default) — see ``_validate_runtime``'s
      docstring for the exact semantics and the STATED, narrower guarantee this
      leaves for the GGUF set specifically;
    - the pre-registered exposure row must agree with the ``ExecutionPlan`` field by
      field (profile, split role, split identity hash, carrier, consumed=no, planned
      budgets); the plan's carrier must additionally resolve to a genuine speech
      dataset entry of this study's scope in the umbrella lock, never a model entry
      or a general-audio asset;
    - absolute paths, drive letters, ``..`` traversal, path escapes, duplicates and
      extra/missing model files are all refused.

    Any missing file, malformed JSON, schema/identity mismatch, lock mismatch or byte
    drift refuses the touch. Verification proves the state at measurement time for
    every check EXCEPT the GGUF fast path described above (which proves only cheap
    identity, not bytes, unless it falls back to a full re-hash). The process that
    opens the gate must be the process that starts llama-server, immediately
    afterward — the gate's own pass/fail DECISION must never be cached, shared across
    processes, or separated from the launch it authorizes; every other check here
    (E0 closure, scoring freeze, exposure pre-registration, carrier scope, llama.cpp
    build binary, runtime libraries) is unconditionally re-verified from scratch on
    EVERY call regardless of the GGUF identity cache, which is a narrow, internal
    performance optimization for one sub-check, never a substitute for calling this
    gate at all.
    """

    e0_receipt: Path
    runtime_receipt: Path
    data_root: Path
    lock_path: Path
    runtime_root: Path
    exposure_ledger: Path
    source_root: Path

    E0_DELIVERABLES = ("d1_identity", "d2_leakage", "d3_scoring", "d4_trace")

    @classmethod
    def for_study_repo(
        cls, repo_root: Path, data_root: Path, runtime_root: Path
    ) -> "FrozenCoreGate":
        """The canonical production binding — the only gate a real run may use.

        Pins the committed receipts, the study exposure ledger and the umbrella lock
        of the registered adjacent-checkout layout. Constructing a gate against any
        other ledger (a copy, a temp file, a synthetic row) does not authorize
        anything: pre-registration means a row in ``docs/exposure-ledger.md``.
        """

        root = Path(repo_root)
        return cls(
            e0_receipt=root / "docs" / "receipts" / "e0-closure.json",
            runtime_receipt=root / "docs" / "receipts" / "runtime.json",
            data_root=Path(data_root),
            lock_path=root.parent.parent / "docs" / "datasets.lock.json",
            runtime_root=Path(runtime_root),
            exposure_ledger=root / "docs" / "exposure-ledger.md",
            source_root=root,
        )

    def _load(self, path: Path, label: str) -> Mapping[str, object]:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(f"{label} missing or unreadable ({path}): {error}") from error
        if not isinstance(document, Mapping):
            raise GateClosed(f"{label} must be a JSON object ({path})")
        return document

    def _require_schema(self, document: Mapping[str, object], expected: str, label: str) -> None:
        if document.get("schema") != expected:
            raise GateClosed(
                f"{label} schema mismatch: expected {expected!r}, found {document.get('schema')!r}"
            )
        if document.get("study") != STUDY_SLUG:
            raise GateClosed(
                f"{label} study identity mismatch: expected {STUDY_SLUG!r}, "
                f"found {document.get('study')!r}"
            )

    def _validate_e0(self) -> None:
        e0 = self._load(self.e0_receipt, "E0 closure receipt")
        self._require_schema(e0, E0_RECEIPT_SCHEMA, "E0 closure receipt")
        if set(e0) != {"schema", "study", "deliverables"}:
            raise GateClosed("E0 closure receipt must have exact schema/study/deliverables keys")
        deliverables = e0["deliverables"]
        if not isinstance(deliverables, Mapping) or set(deliverables) != set(self.E0_DELIVERABLES):
            raise GateClosed(
                f"E0 receipt deliverables must be exactly {self.E0_DELIVERABLES}"
            )
        artifacts_root = Path(self.e0_receipt).parent
        artifact_paths: dict[str, Path] = {}
        for name in self.E0_DELIVERABLES:
            entry = deliverables[name]
            if not isinstance(entry, Mapping) or set(entry) != {"status", "artifact", "sha256"}:
                raise GateClosed(f"E0 deliverable {name} must have exact status/artifact/sha256")
            if entry["status"] != "CLOSED":
                raise GateClosed(
                    f"E0 deliverable {name} is not CLOSED (found {entry['status']!r}); "
                    "model touch refused"
                )
            recorded = entry["sha256"]
            if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
                raise GateClosed(f"E0 deliverable {name} lacks a valid artifact sha256")
            relative = _safe_relative_path(entry["artifact"], f"E0 deliverable {name} artifact")
            artifact = _resolve_under(artifacts_root, relative, f"E0 deliverable {name} artifact")
            _, actual = _measure_file(artifact, f"E0 deliverable {name} artifact")
            if actual != recorded:
                raise GateClosed(
                    f"E0 deliverable {name} artifact hash drift: receipt {recorded[:12]}..., "
                    f"actual {actual[:12]}...; model touch refused"
                )
            artifact_paths[name] = artifact
        self._validate_scoring_freeze(artifact_paths["d3_scoring"])

    def _validate_scoring_freeze(self, d3_artifact: Path) -> None:
        """The D3 freeze is enforced, not asserted: re-hash every frozen scoring
        source against the live tree and refuse any unlisted scoring module.

        Without this, editing ``scoring/*.py`` after closure would leave every
        receipt hash intact — the artifact records hashes of code that would no
        longer be the code doing the scoring."""

        document = self._load(d3_artifact, "D3 scoring artifact")
        frozen = document.get("frozen_sources_sha256")
        if not isinstance(frozen, Mapping) or not frozen:
            raise GateClosed(
                "D3 scoring artifact lacks a non-empty frozen_sources_sha256 mapping; "
                "an unfrozen scoring stack cannot open the model gate"
            )
        for relpath, recorded in frozen.items():
            if not isinstance(recorded, str) or _SHA256.fullmatch(recorded) is None:
                raise GateClosed(f"frozen scoring source {relpath!r} lacks a valid sha256")
            relative = _safe_relative_path(relpath, f"frozen scoring source {relpath!r}")
            source = _resolve_under(self.source_root, relative, f"frozen scoring source {relpath!r}")
            _, actual = _measure_file(source, f"frozen scoring source {relpath!r}")
            if actual != recorded:
                raise GateClosed(
                    f"scoring freeze drift: {relpath} is {actual[:12]}... on disk but the "
                    f"D3 receipt froze {recorded[:12]}...; model touch refused"
                )
        scoring_dir = Path(self.source_root) / SCORING_PACKAGE_RELPATH
        if not scoring_dir.is_dir():
            raise GateClosed(f"scoring package directory missing: {scoring_dir}")
        self._assert_no_relocated_bytecode_cache(scoring_dir)
        actual_sources: set[str] = set()
        for entry in sorted(scoring_dir.rglob("*")):
            rel_parts = entry.relative_to(scoring_dir).parts
            # Symlink refusal must precede the __pycache__ skip: a symlinked
            # directory NAMED __pycache__ would otherwise slip through by name.
            if entry.is_dir() and entry.is_symlink():
                raise GateClosed(
                    "scoring package contains a symlinked directory "
                    f"{'/'.join(rel_parts)!r}; rglob does not descend through it, "
                    "so its contents would be importable yet invisible to the "
                    "freeze — refused"
                )
            # M-1 (external-threat-model review): a __pycache__ entry is no longer
            # silently invisible to the freeze. Demonstrated defect: a hand-planted
            # .pyc whose SOURCE hash still matched the D3 receipt (Python's import
            # machinery can be made to trust a hash-based .pyc without ever
            # re-checking it against the .py bytes) made scoring run different code
            # than the receipt described, with every hash the gate checks staying
            # green. The freeze covers Python SOURCE only (module docstring above) --
            # so any bytecode cache under the frozen scoring package, planted or
            # merely stale, is refused outright rather than skipped.
            if "__pycache__" in rel_parts:
                raise GateClosed(
                    "scoring package contains a __pycache__ entry "
                    f"{'/'.join(rel_parts)!r}; the D3 freeze binds source bytes only, "
                    "so cached/forged bytecode next to frozen sources is refused rather "
                    "than silently ignored -- purge it (PYTHONDONTWRITEBYTECODE=1 keeps "
                    "it from reappearing) before opening the gate"
                )
            if entry.is_dir():
                continue
            if entry.is_file() and entry.name.endswith(".py"):
                actual_sources.add(f"{SCORING_PACKAGE_RELPATH}/{'/'.join(rel_parts)}")
                continue
            raise GateClosed(
                "scoring package contains a non-source entry "
                f"{'/'.join(rel_parts)!r} (data file or dangling symlink); the freeze "
                "covers Python sources only, so nothing else may live there"
            )
        declared = set(frozen)
        unlisted = sorted(actual_sources - declared)
        if unlisted:
            raise GateClosed(
                f"scoring package contains source files the D3 freeze does not name: "
                f"{unlisted}; model touch refused"
            )

    def _assert_no_relocated_bytecode_cache(self, scoring_dir: Path) -> None:
        """IMPORTANT B follow-up (round-2 external-threat-model review).

        The on-disk ``__pycache__`` walk in :meth:`_validate_scoring_freeze`
        only ever sees a bytecode cache co-located with the frozen scoring
        sources. ``sys.pycache_prefix`` -- settable via the
        ``PYTHONPYCACHEPREFIX`` environment variable -- relocates EVERY
        ``.pyc`` Python would read or write (forged or merely stale) into a
        mirrored tree elsewhere on disk that walk never visits, so on its own
        the ``__pycache__`` refusal is not a guarantee against bytecode the
        interpreter would still execute. Demonstrated: a forged
        ``UNCHECKED_HASH`` ``.pyc`` placed in the relocated prefix tree
        executed while ``wer.py``'s source hash still matched the D3 freeze
        and ``_validate_scoring_freeze`` PASSED. Separately,
        ``PYTHONDONTWRITEBYTECODE=1`` (the previously prescribed mitigation)
        stops Python from WRITING a new ``.pyc`` -- it does nothing to stop an
        ALREADY-planted one from being READ and executed; writing is not
        reading, and the old runbook wording conflated the two.

        Two checks, stated exactly for what each closes:

        1. Refuse outright if EITHER ``sys.pycache_prefix`` or the
           ``PYTHONPYCACHEPREFIX`` environment variable is set for this
           process. Whatever the on-disk walk found, an active relocated-
           cache configuration means that walk did not see everywhere this
           interpreter would actually look for (or write) a ``.pyc`` -- so
           the freeze cannot vouch for what would run. This is the primary,
           load-bearing check: with no relocation configured, Python only
           ever reads/writes a ``.pyc`` directly beside its ``.py`` source,
           exactly the location the walk above already refuses any entry
           under.
        2. For every ``speech_aware_evidence_acquisition.scoring[.*]``
           submodule THIS process has already imported FROM this exact
           ``scoring_dir`` (``sys.modules``, filtered by ``__file__``
           resolving inside ``scoring_dir`` -- a module imported from a
           DIFFERENT ``scoring_dir``, e.g. a synthetic test fixture's own
           tree, is simply not this gate's concern and is skipped): refuse
           if its ``__file__`` does not end in ``.py`` (a sourceless/
           bytecode-only import -- the exact shape a hash-based-forged
           ``.pyc`` with no matching ``.py`` on disk would take), or if its
           ``__cached__`` resolves OUTSIDE ``scoring_dir`` (a relocated
           cache still recorded on the module even if the prefix that
           produced it has since been unset in THIS process).

        STATED GUARANTEE -- precise, not overstated: with this check
        passing, (a) THIS process has no active relocated-cache
        configuration that could make Python read or write a ``.pyc``
        anywhere other than directly beside its ``.py`` source (where the
        walk above already refuses any entry), and (b) every scoring
        submodule THIS process has already imported from ``scoring_dir`` was
        loaded from a ``.py`` file inside it, with no bytecode cache
        recorded outside it. It does NOT -- and cannot -- prove that no
        OTHER process (its own ``PYTHONPYCACHEPREFIX``, running concurrently
        or having run earlier or later) holds or will hold a forged cache it
        can execute independently of this gate check, nor does it retroactively
        validate an import that happens in THIS process AFTER this check
        runs. The freeze covers Python source bytes read by a clean import
        of this checked tree; it was never, and is still not, a guarantee
        about interpreter-wide bytecode-loading configuration beyond that.
        """

        prefix = sys.pycache_prefix
        env_prefix = os.environ.get("PYTHONPYCACHEPREFIX")
        if prefix or env_prefix:
            raise GateClosed(
                "a relocated bytecode cache is configured for this process "
                f"(sys.pycache_prefix={prefix!r}, PYTHONPYCACHEPREFIX={env_prefix!r}); "
                "this moves every .pyc -- forged or stale -- outside the tree the "
                "scoring __pycache__ refusal can see, so the freeze cannot vouch for "
                "what bytecode this process would execute; unset it and retry"
            )
        scoring_dir_resolved = Path(scoring_dir).resolve()
        for name, module in list(sys.modules.items()):
            if module is None or not (
                name == _SCORING_MODULE_PREFIX or name.startswith(_SCORING_MODULE_PREFIX + ".")
            ):
                continue
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue  # a namespace/frozen/builtin entry -- nothing on disk to check
            try:
                module_file_resolved = Path(module_file).resolve()
            except OSError:
                continue
            if not module_file_resolved.is_relative_to(scoring_dir_resolved):
                # Loaded from a DIFFERENT scoring_dir entirely (e.g. a
                # synthetic test fixture's own tmp tree) -- not this gate's
                # concern; only modules genuinely loaded from THIS checked
                # directory are in scope.
                continue
            if module_file_resolved.suffix != ".py":
                raise GateClosed(
                    f"scoring module {name!r} was loaded from a non-source file "
                    f"({module_file!r}); this process's import machinery did not use "
                    "the frozen .py source, so the D3 freeze cannot vouch for what "
                    "runs -- refused"
                )
            cached = getattr(module, "__cached__", None)
            if cached is not None:
                try:
                    cached_resolved = Path(cached).resolve()
                except OSError:
                    cached_resolved = Path(cached)
                if not cached_resolved.is_relative_to(scoring_dir_resolved):
                    raise GateClosed(
                        f"scoring module {name!r} has a bytecode cache recorded outside "
                        f"the checked scoring package ({cached!r}); a relocated cache "
                        "cannot be vouched for by this freeze -- refused"
                    )

    def _d1_identity_artifact_path(self) -> Path:
        """Resolve D1's own artifact path THROUGH the E0 closure receipt (never a
        hardcoded filename) -- the same discipline :meth:`_validate_e0` already
        uses for every deliverable, applied here for exactly one of them so
        :meth:`verify_media_identity` can independently load D1's per-sample
        media facts without depending on ``_validate_e0`` having run first in
        the same call (it always will in the real ``FrozenCoreGate.
        for_study_repo`` production path via ``assert_model_touch_allowed``,
        but this method is a second, independently callable rail — see its own
        docstring)."""

        e0 = self._load(self.e0_receipt, "E0 closure receipt")
        deliverables = e0.get("deliverables")
        if not isinstance(deliverables, Mapping) or "d1_identity" not in deliverables:
            raise GateClosed("E0 closure receipt lacks a d1_identity deliverable")
        entry = deliverables["d1_identity"]
        if not isinstance(entry, Mapping) or "artifact" not in entry:
            raise GateClosed("E0 closure receipt d1_identity deliverable is malformed")
        relative = _safe_relative_path(entry["artifact"], "E0 deliverable d1_identity artifact")
        return _resolve_under(
            Path(self.e0_receipt).parent, relative, "E0 deliverable d1_identity artifact"
        )

    # I-4 (external-threat-model review): a documented, generous MP3 bitrate
    # plausibility band, derived empirically from the two core carriers'
    # real, D1-frozen media -- observed 16-320 kbps across all 44 earnings21
    # and all 125 earnings22 samples (bytes from the committed D1 manifest,
    # seconds from each carrier's own metadata CSV). Widened well past that
    # observed range on both ends so genuine data never trips it, while still
    # catching the demonstrated attack by many orders of magnitude: replacing
    # a CSV's audio_length cell so 4422s of metered audio read as 0.044s
    # implies ~2.4 GILLION kbps against the file's real (D1-frozen) byte size
    # -- nowhere close to this band. This is a PLAUSIBILITY bound, not an
    # exact duration re-derivation (decoding MP3 frames to prove the exact
    # second count is out of scope here -- see the docstring below and
    # docs/owner-decisions-pending.md for the residue this leaves).
    _MIN_PLAUSIBLE_KBPS = 4.0
    _MAX_PLAUSIBLE_KBPS = 512.0

    def _assert_plausible_audio_seconds(
        self, sample_id: str, audio_seconds: object, media_bytes: int
    ) -> None:
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
        ):
            raise GateClosed(
                f"sample {sample_id!r} audio_seconds must be a finite positive number, "
                f"got {audio_seconds!r}"
            )
        implied_kbps = (media_bytes * 8 / 1000.0) / float(audio_seconds)
        if not (self._MIN_PLAUSIBLE_KBPS <= implied_kbps <= self._MAX_PLAUSIBLE_KBPS):
            raise GateClosed(
                f"sample {sample_id!r}: CSV-derived audio_seconds={audio_seconds!r} implies "
                f"{implied_kbps:.1f} kbps against the D1-recorded media size ({media_bytes} "
                f"bytes) -- outside the plausible MP3 bitrate band "
                f"[{self._MIN_PLAUSIBLE_KBPS}, {self._MAX_PLAUSIBLE_KBPS}] kbps (observed "
                "16-320 kbps across both core carriers' real media); a metadata CSV cell "
                "cannot silently inflate or deflate the metered audio budget (I-4); model "
                "touch refused"
            )

    def verify_media_identity(
        self, carrier_lock_key: str, media_facts: Mapping[str, tuple[str, float]]
    ) -> None:
        """I-4 (external-threat-model review): verify, AT MODEL-TOUCH TIME, that
        the media this run is actually about to send is the same bytes D1
        closed over -- as a re-measured FILE, never merely as a receipt's
        claim about a file.

        PRECISE SCOPE (round-2 external-threat-model review, IMPORTANT A):
        this method only ever re-hashes what ``media_facts`` NAMES -- i.e.
        what the caller's ``PayloadBindingContext.media_relpaths`` says the
        verified split bound for each sample id. It was previously possible
        for the actual outbound payload's own ``media_relpath`` to name a
        DIFFERENT file than the one this method verified (confined under the
        same carrier root, but never compared) -- so this docstring's claim
        that the media "this run is actually about to send" is checked was
        true only once ``core.model.FrozenCoreAdapter._enforce_payload_
        binding`` also enforces, as a precondition of ever reaching the
        transport, that the payload's ``media_relpath`` for a sample EXACTLY
        equals ``binding.media_relpaths[sample_id]`` -- the same value this
        method is handed. With that binding in place the two checks compose
        into the claim above; on its own, re-hashing the binding's claimed
        path is a check about what the BINDING names, not yet a check on the
        literal bytes leaving the process.

        ``media_facts`` maps each sample id the run's VERIFIED SPLIT will touch
        to ``(media_relpath, audio_seconds)`` -- exactly, and only, the samples
        this specific run can send (never the whole ~770 MB carrier). Cost was
        measured, not assumed: re-hashing a full carrier on every gate open was
        rejected as needlessly slow for what a bounded first-slice run can ever
        touch (dev/discovery splits here are 10-44 samples, a few hundred MB at
        most -- seconds, not minutes); re-hashing exactly the run's split scales
        with what the run can actually touch instead. See
        docs/owner-decisions-pending.md for the exact measurement and the
        residue this leaves unclosed.

        Two things are checked per sample, both against D1's OWN frozen
        per-file facts (``docs/receipts/artifacts/d1-identity.json``, itself
        already byte-verified against the E0 closure receipt by
        ``_validate_e0``):

        1. **Byte identity** — the live file's re-measured (size, SHA-256) must
           equal D1's recorded (size, SHA-256) for that sample id. This closes
           the demonstrated defect that an ``.mp3``'s bytes could be replaced
           on disk and the loader/adapter would proceed without complaint: D1
           recorded the fact once at closure time, but nothing ever compared
           it to disk again before this.
        2. **Audio-seconds plausibility** — the CSV-derived ``audio_seconds``
           the loader reports (which meters the contractual ≤20h audio budget)
           must imply a plausible MP3 bitrate against that SAME frozen byte
           size (:meth:`_assert_plausible_audio_seconds`). D1 does not record
           durations at all (only per-file byte/hash identity and the set of
           sample ids each metadata CSV names -- never the numeric field
           values inside it), so an exact re-derivation of "the real duration"
           is not possible from what D1 already closed over without decoding
           audio; this is a deliberately-scoped plausibility bound, not an
           exact one -- stated plainly, not silently narrowed. It still
           catches the demonstrated attack (4422s edited to 0.044s) by many
           orders of magnitude of margin.

        ``carrier_lock_key`` of ``conec`` resolves to ``earnings21-original``'s
        D1 media layer: ConEC carries no media of its own (D1:
        ``conec.canonical_identity == "earnings21-original media"``).
        """

        if not isinstance(media_facts, Mapping) or not media_facts:
            raise GateClosed(
                "verify_media_identity requires a non-empty sample_id -> "
                "(media_relpath, audio_seconds) mapping"
            )
        identity_carrier = "earnings21-original" if carrier_lock_key == "conec" else carrier_lock_key
        document = self._load(self._d1_identity_artifact_path(), "D1 identity artifact")
        carriers = document.get("carriers")
        carrier_doc = carriers.get(identity_carrier) if isinstance(carriers, Mapping) else None
        if not isinstance(carrier_doc, Mapping):
            raise GateClosed(
                f"D1 identity artifact has no per-sample media identity for carrier "
                f"{identity_carrier!r} (plan carrier {carrier_lock_key!r}); model touch refused"
            )
        layers = carrier_doc.get("layers")
        media_layer = layers.get("media") if isinstance(layers, Mapping) else None
        manifest_entries = media_layer.get("manifest") if isinstance(media_layer, Mapping) else None
        if not isinstance(manifest_entries, list) or not manifest_entries:
            raise GateClosed(
                f"D1 identity artifact carrier {identity_carrier!r} lacks a media manifest; "
                "model touch refused"
            )
        recorded: dict[str, tuple[int, str]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, Mapping):
                raise GateClosed("D1 media manifest entry is not an object")
            sample_id = entry.get("id")
            rec_bytes = entry.get("bytes")
            rec_sha = entry.get("sha256")
            if (
                not isinstance(sample_id, str)
                or not sample_id
                or isinstance(rec_bytes, bool)
                or not isinstance(rec_bytes, int)
                or rec_bytes <= 0
                or not isinstance(rec_sha, str)
                or _SHA256.fullmatch(rec_sha) is None
            ):
                raise GateClosed(f"D1 media manifest entry is malformed: {entry!r}")
            recorded[sample_id] = (rec_bytes, rec_sha)

        for sample_id, fact in media_facts.items():
            if (
                not isinstance(sample_id, str)
                or not isinstance(fact, tuple)
                or len(fact) != 2
            ):
                raise GateClosed(
                    f"media_facts[{sample_id!r}] must be a (media_relpath, audio_seconds) pair"
                )
            relpath, audio_seconds = fact
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no D1-recorded "
                    "media identity; a sample outside D1's identity closure can never be "
                    "sent to the frozen core"
                )
            rec_bytes, rec_sha = d1_fact
            relative = _safe_relative_path(relpath, f"media_facts[{sample_id!r}] media relpath")
            resolved = _resolve_under(self.data_root, relative, f"media for sample {sample_id!r}")
            actual_bytes, actual_sha = _measure_file(resolved, f"media for sample {sample_id!r}")
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"media identity drift for sample {sample_id!r}: D1 recorded "
                    f"{rec_bytes} bytes / {rec_sha[:12]}..., the live file is now "
                    f"{actual_bytes} bytes / {actual_sha[:12]}...; model touch refused (I-4)"
                )
            self._assert_plausible_audio_seconds(sample_id, audio_seconds, rec_bytes)

    def verify_reference_identity(
        self, carrier_lock_key: str, reference_facts: Mapping[str, str]
    ) -> None:
        """IMPORTANT 2 (external-threat-model review round 3): the reference-
        layer counterpart to :meth:`verify_media_identity`, re-verified AS
        FILES, never merely trusted as a bare ``read_text()`` claim.

        Every formal WER is ``f(frozen scoring code, hypothesis text,
        reference bytes)``. Before this, only the first two were pinned: the
        D3 freeze binds the scoring SOURCE (``_validate_scoring_freeze``),
        and I7's ``response_text_sha256`` re-derivation binds the hypothesis
        -- but ``data.references.reference_tokens`` did a bare
        ``read_text()`` on ``<data_root>/<carrier>/transcripts/
        nlp_references/<sample_id>.nlp`` with no hash/size check at all,
        even though D1 already recorded byte size + SHA-256 for every one of
        these files (the same ``{count, ids_sha256, manifest,
        manifest_sha256, total_bytes}`` shape :meth:`verify_media_identity`
        already reads for ``media``, here under the ``nlp_references`` layer
        key instead). An interrupted asset fetch or a wrong
        ``SPEECHRL_DATA_DIR`` silently produces the identical symptom as a
        deliberate substitution: a WER computed against the wrong bytes with
        every other check green.

        ``reference_facts`` maps each sample id THIS bundle's own verified
        split touches to its reference file's path, relative to
        ``self.data_root`` -- computed by the caller (``core.scorers``, via
        ``data.references.reference_file_relpath``, the SAME relative-path
        convention ``reference_tokens`` itself resolves) rather than
        re-derived here: this module stays stdlib-only and never imports
        ``data.lock``/``data.references`` (module docstring). Scoped to
        exactly the bundle's own split -- never the whole ~169-file corpus
        -- mirroring :meth:`verify_media_identity`'s cost discipline (a
        dev/discovery split here is 10-125 samples).

        A carrier lock key with no D1-recorded reference-layer identity this
        gate can re-verify fails closed rather than silently skipping the
        check -- see ``_REFERENCE_SCOPED_CARRIER_LOCK_KEYS`` (mirrors
        ``data.references._NLP_SUBDIR`` exactly: today, ``earnings21-original``
        and ``earnings22-original`` only -- ``conec`` has no reference layer
        ``reference_tokens`` can read at all, so scoring it was never
        possible and this method correctly refuses it too) and
        ``docs/owner-decisions-pending.md`` item 5 for the residue this
        leaves if that set ever needs to grow.
        """

        if not isinstance(reference_facts, Mapping) or not reference_facts:
            raise GateClosed(
                "verify_reference_identity requires a non-empty sample_id -> "
                "reference_relpath mapping"
            )
        if carrier_lock_key not in _REFERENCE_SCOPED_CARRIER_LOCK_KEYS:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} has no D1-recorded reference-layer "
                "identity this gate can re-verify; scoring against an unverified reference "
                "layer is refused rather than silently trusted (IMPORTANT 2 fail-closed; "
                "see docs/owner-decisions-pending.md item 5)"
            )
        document = self._load(self._d1_identity_artifact_path(), "D1 identity artifact")
        carriers = document.get("carriers")
        carrier_doc = carriers.get(carrier_lock_key) if isinstance(carriers, Mapping) else None
        if not isinstance(carrier_doc, Mapping):
            raise GateClosed(
                f"D1 identity artifact has no per-sample identity for carrier "
                f"{carrier_lock_key!r}; model touch refused"
            )
        layers = carrier_doc.get("layers")
        ref_layer = (
            layers.get(_NLP_REFERENCE_D1_LAYER_KEY) if isinstance(layers, Mapping) else None
        )
        manifest_entries = ref_layer.get("manifest") if isinstance(ref_layer, Mapping) else None
        if not isinstance(manifest_entries, list) or not manifest_entries:
            raise GateClosed(
                f"D1 identity artifact carrier {carrier_lock_key!r} lacks a "
                f"{_NLP_REFERENCE_D1_LAYER_KEY!r} manifest; model touch refused"
            )
        recorded: dict[str, tuple[int, str]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, Mapping):
                raise GateClosed("D1 reference manifest entry is not an object")
            sample_id = entry.get("id")
            rec_bytes = entry.get("bytes")
            rec_sha = entry.get("sha256")
            if (
                not isinstance(sample_id, str)
                or not sample_id
                or isinstance(rec_bytes, bool)
                or not isinstance(rec_bytes, int)
                or rec_bytes <= 0
                or not isinstance(rec_sha, str)
                or _SHA256.fullmatch(rec_sha) is None
            ):
                raise GateClosed(f"D1 reference manifest entry is malformed: {entry!r}")
            recorded[sample_id] = (rec_bytes, rec_sha)

        for sample_id, relpath in reference_facts.items():
            if not isinstance(sample_id, str) or not isinstance(relpath, str):
                raise GateClosed(
                    f"reference_facts[{sample_id!r}] must be a string reference relpath"
                )
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no D1-recorded "
                    "reference identity; a sample outside D1's identity closure can never be "
                    "scored against"
                )
            rec_bytes, rec_sha = d1_fact
            relative = _safe_relative_path(relpath, f"reference_facts[{sample_id!r}] relpath")
            resolved = _resolve_under(
                self.data_root, relative, f"reference for sample {sample_id!r}"
            )
            actual_bytes, actual_sha = _measure_file(
                resolved, f"reference for sample {sample_id!r}"
            )
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"reference identity drift for sample {sample_id!r}: D1 recorded "
                    f"{rec_bytes} bytes / {rec_sha[:12]}..., the live file is now "
                    f"{actual_bytes} bytes / {actual_sha[:12]}...; scoring refused "
                    "(IMPORTANT 2)"
                )

    def _load_lock_with_hash(self) -> tuple[Mapping[str, object], str]:
        """M-3: read ``docs/datasets.lock.json`` exactly ONCE and derive both the
        parsed document and its SHA-256 from that single read.

        Before this, one ``assert_model_touch_allowed`` call independently
        re-read and re-parsed the lock file up to three times (exposure
        pre-registration, carrier scope resolution, the runtime model-entry
        lookup) -- each a separate ``open()``/``json.loads`` with no guarantee
        all three observed the same bytes, and the file's own identity never
        entered the run manifest or the ledger (a "dataset rev" cell stayed
        hand-supplied). This reads the bytes once, hashes them, and returns
        both; callers needing the parsed lock take it as a parameter instead of
        re-reading. The umbrella lock file itself is deliberately NOT frozen by
        this: it is an editable, shared, program-level asset (outside this
        repository), not a study-owned receipt -- the hash is recorded so a
        downstream reader can tell WHICH revision a run used, not to pin it.
        """

        path = Path(self.lock_path)
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise GateClosed(f"datasets lock missing or unreadable ({path}): {error}") from error
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(f"datasets lock missing or unreadable ({path}): {error}") from error
        if not isinstance(document, Mapping):
            raise GateClosed(f"datasets lock must be a JSON object ({path})")
        return document, hashlib.sha256(raw).hexdigest()

    def _lock_model_entry(self, lock: Mapping[str, object] | None = None) -> Mapping[str, object]:
        if lock is None:
            lock, _ = self._load_lock_with_hash()
        models = lock.get("models")
        if not isinstance(models, list):
            raise GateClosed("datasets lock lacks a models list")
        for entry in models:
            if isinstance(entry, Mapping) and entry.get("name") == MODEL_LOCK_KEY:
                subdir = entry.get("local_subdir")
                files = entry.get("files")
                size_bytes = entry.get("size_bytes")
                if (
                    not isinstance(subdir, str)
                    or not subdir
                    or isinstance(files, bool)
                    or not isinstance(files, int)
                    or files <= 0
                    or isinstance(size_bytes, bool)
                    or not isinstance(size_bytes, int)
                    or size_bytes <= 0
                ):
                    raise GateClosed(
                        f"datasets lock entry {MODEL_LOCK_KEY} lacks usable "
                        "local_subdir/files/size_bytes"
                    )
                return entry
        raise GateClosed(f"frozen model key {MODEL_LOCK_KEY!r} not found in datasets lock")

    def _validate_runtime(
        self,
        lock: Mapping[str, object] | None = None,
        *,
        full_hash: bool | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        """Verify the runtime receipt: llama.cpp build, GGUF set, runtime libraries.

        ``full_hash`` governs ONLY the GGUF set (runtime libraries below are always
        fully hashed -- module-level comment above ``_SESSION_FULL_HASH_DONE``,
        ``_validate_runtime_libraries``). Resolution order (``_resolve_full_hash_
        override``):

        1. An explicit ``True``/``False`` argument always wins.
        2. Otherwise, a recognized ``RUNTIME_FULL_HASH_ENV`` environment value is
           honored as if it had been passed explicitly (this is how
           ``scripts/reproduce.sh --full``/default reaches this gate without this
           study's frozen ``e0/`` CLI surface needing its own new argument -- see
           that constant's own comment).
        3. Otherwise (both unset/unrecognized) -- auto/session: the first call THIS
           PROCESS makes for a given runtime-receipt identity forces a full
           re-hash (ignoring even a valid pre-existing cache); subsequent calls in
           the same process behave like ``False``. This is the gate's own SAFE
           default -- a real model touch (``core.model.FrozenCoreAdapter``, which
           never overrides ``full_hash`` and does not itself set the env var)
           always pays the full cost at least once per session.

        Meaning of the resolved value once known:

        - ``True`` -- always fully re-hash every GGUF file from bytes (the
          authoritative check; ignores any cache).
        - ``False`` -- always attempt the cheap-identity fast path first, falling
          back to a full re-hash per file on any cache miss/mismatch (owner
          decision item 7, rules a/b/c).

        ``diagnostics``, if given a mutable dict, is populated with
        ``gguf_files_total``, ``gguf_files_full_hashed`` and
        ``gguf_fast_path_used`` (True iff EVERY GGUF file was verified via the
        cache this call, i.e. zero bytes were re-hashed) -- a caller that wants an
        honest, accurate report of what actually happened (never merely what was
        requested) reads this back after the call.
        """

        runtime = self._load(self.runtime_receipt, "runtime receipt")
        self._require_schema(runtime, RUNTIME_RECEIPT_SCHEMA, "runtime receipt")
        expected_keys = {
            "schema",
            "study",
            "model_lock_key",
            "llama_cpp",
            "gguf_files",
            "runtime_libraries",
        }
        if set(runtime) != expected_keys:
            raise GateClosed(f"runtime receipt must have exact keys {sorted(expected_keys)}")
        if runtime["model_lock_key"] != MODEL_LOCK_KEY:
            raise GateClosed(
                f"runtime receipt model_lock_key {runtime['model_lock_key']!r} does not match "
                f"the frozen key {MODEL_LOCK_KEY!r}"
            )
        lock_entry = self._lock_model_entry(lock)
        subdir = str(lock_entry["local_subdir"]).rstrip("/")

        files = runtime["gguf_files"]
        if not isinstance(files, list) or not files:
            raise GateClosed("runtime receipt lacks a non-empty gguf_files list")
        if len(files) != lock_entry["files"]:
            raise GateClosed(
                f"runtime receipt declares {len(files)} model files but the lock freezes "
                f"{lock_entry['files']}; extra or missing model files are refused"
            )
        # Owner decision 2026-08-06 (item 7): resolve the fast/full policy and the
        # identity cache BEFORE the per-file loop. ``receipt_sha256`` is the
        # cache's binding key (item 1c) -- read directly from the receipt's own
        # bytes, independent of ``self._load``'s already-parsed document, so this
        # is a genuine re-hash of what is actually on disk, not a re-derivation
        # from the parsed JSON.
        try:
            receipt_sha256 = hashlib.sha256(Path(self.runtime_receipt).read_bytes()).hexdigest()
        except OSError as error:
            raise GateClosed(
                f"runtime receipt: cannot read bytes for identity cache: {error}"
            ) from error
        resolved_full_hash = _resolve_full_hash_override(full_hash)
        do_full = (
            resolved_full_hash
            if resolved_full_hash is not None
            else receipt_sha256 not in _SESSION_FULL_HASH_DONE
        )
        cache_path = Path(self.data_root) / RUNTIME_IDENTITY_CACHE_FILENAME
        cached_entries = None if do_full else _load_identity_cache(cache_path, receipt_sha256)

        seen: set[str] = set()
        total_bytes = 0
        new_cache_entries: dict[str, dict[str, int]] = {}
        full_hashed_count = 0
        for index, entry in enumerate(files):
            label = f"runtime receipt gguf_files[{index}]"
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise GateClosed(f"{label} must have exact path/bytes/sha256")
            relative = _safe_relative_path(entry["path"], f"{label}.path")
            if relative in seen:
                raise GateClosed(f"{label} duplicates model file {relative!r}")
            seen.add(relative)
            if not relative.startswith(subdir + "/"):
                raise GateClosed(
                    f"{label}.path {relative!r} is outside the lock's canonical subdir {subdir!r}"
                )
            recorded_bytes = entry["bytes"]
            recorded_sha = entry["sha256"]
            if (
                isinstance(recorded_bytes, bool)
                or not isinstance(recorded_bytes, int)
                or recorded_bytes <= 0
                or not isinstance(recorded_sha, str)
                or _SHA256.fullmatch(recorded_sha) is None
            ):
                raise GateClosed(f"{label} lacks valid bytes/sha256")
            resolved = _resolve_under(self.data_root, relative, f"{label}.path")

            cheap = _cheap_file_identity(resolved, f"{label}.path")
            cached_entry = cached_entries.get(relative) if cached_entries is not None else None
            if cached_entry is not None and _cheap_identity_matches(cheap, cached_entry):
                # Fast path (items 1/2): size/mtime/file-id match the cache bound
                # to THIS exact runtime receipt -- skip re-reading the bytes.
                # STATED LIMITATION (module comment above, owner-decisions-pending
                # item 7): this defends a wrong/partial/accidentally-replaced
                # model set, NOT an adversary who edits bytes in place while
                # preserving size, mtime and OS file identity.
                actual_bytes = cheap["size"]
            else:
                actual_bytes, actual_sha = _measure_file(resolved, f"{label}.path")
                if actual_bytes != recorded_bytes:
                    raise GateClosed(
                        f"{label} size drift: receipt {recorded_bytes}, actual {actual_bytes}; "
                        "model touch refused"
                    )
                if actual_sha != recorded_sha:
                    raise GateClosed(
                        f"{label} SHA-256 drift: receipt {recorded_sha[:12]}..., "
                        f"actual {actual_sha[:12]}...; model touch refused"
                    )
                full_hashed_count += 1
            new_cache_entries[relative] = cheap
            total_bytes += actual_bytes
        if total_bytes != lock_entry["size_bytes"]:
            raise GateClosed(
                f"model files total {total_bytes} bytes but the lock freezes "
                f"{lock_entry['size_bytes']}; model touch refused"
            )

        # Persist the cache only after every GGUF file verified successfully --
        # never cache a partial/failed check. A write failure is swallowed
        # (best-effort convenience, module docstring); it never fails an already-
        # successful gate check.
        _write_identity_cache(cache_path, receipt_sha256, new_cache_entries)
        if full_hashed_count == len(files):
            # Every file was just genuinely, fully re-hashed from bytes this
            # call -- this satisfies the process/session floor (see
            # ``_SESSION_FULL_HASH_DONE``'s own docstring) regardless of
            # whether that full pass was explicitly forced or auto-decided.
            _SESSION_FULL_HASH_DONE.add(receipt_sha256)
        if diagnostics is not None:
            diagnostics["gguf_files_total"] = len(files)
            diagnostics["gguf_files_full_hashed"] = full_hashed_count
            diagnostics["gguf_fast_path_used"] = full_hashed_count == 0

        build = runtime["llama_cpp"]
        if not isinstance(build, Mapping) or set(build) != {
            "build_commit",
            "reported_build",
            "binary_path",
            "binary_bytes",
            "binary_sha256",
        }:
            raise GateClosed(
                "runtime receipt llama_cpp must have exact "
                "build_commit/reported_build/binary_path/binary_bytes/binary_sha256"
            )
        commit = build["build_commit"]
        if not isinstance(commit, str) or _FULL_COMMIT.fullmatch(commit) is None:
            raise GateClosed(
                "llama_cpp.build_commit must be a full 40-hex commit backed by the build binary"
            )
        reported = build["reported_build"]
        reported_match = _REPORTED_BUILD.search(reported) if isinstance(reported, str) else None
        if reported_match is None or not commit.startswith(reported_match.group(1)):
            raise GateClosed(
                "llama_cpp.reported_build must carry the binary's self-reported build hash "
                "(from `llama-server --version` at receipt time) and it must prefix-match "
                f"build_commit; got {reported!r} vs {commit[:12]}..."
            )
        recorded_bytes = build["binary_bytes"]
        recorded_sha = build["binary_sha256"]
        if (
            isinstance(recorded_bytes, bool)
            or not isinstance(recorded_bytes, int)
            or recorded_bytes <= 0
            or not isinstance(recorded_sha, str)
            or _SHA256.fullmatch(recorded_sha) is None
        ):
            raise GateClosed("llama_cpp binary evidence lacks valid bytes/sha256")
        relative = _safe_relative_path(build["binary_path"], "llama_cpp.binary_path")
        binary = _resolve_under(self.runtime_root, relative, "llama_cpp.binary_path")
        actual_bytes, actual_sha = _measure_file(binary, "llama_cpp.binary_path")
        if actual_bytes != recorded_bytes or actual_sha != recorded_sha:
            raise GateClosed(
                "llama_cpp build binary drift: the receipt's build_commit is not backed by "
                "the on-disk binary bytes; model touch refused"
            )
        self._validate_runtime_libraries(runtime, relative)

    def _validate_runtime_libraries(self, runtime: Mapping[str, object], binary_rel: str) -> None:
        """The launcher is ~18 KB of stub; the inference code lives in the shared
        libraries next to it. Bind the launcher's whole directory as an exact set:
        every runtime file re-hashed, no unlisted file tolerated — a rebuilt
        ``libllama*.so`` or ``libggml-cuda.so`` re-closes the gate."""

        libraries = runtime["runtime_libraries"]
        if not isinstance(libraries, list) or not libraries:
            raise GateClosed("runtime receipt lacks a non-empty runtime_libraries list")
        bin_dir_rel = binary_rel.rsplit("/", 1)[0]
        seen: set[str] = set()
        for index, entry in enumerate(libraries):
            label = f"runtime receipt runtime_libraries[{index}]"
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise GateClosed(f"{label} must have exact path/bytes/sha256")
            relative = _safe_relative_path(entry["path"], f"{label}.path")
            if relative in seen or relative == binary_rel:
                raise GateClosed(f"{label} duplicates runtime file {relative!r}")
            seen.add(relative)
            if relative.rsplit("/", 1)[0] != bin_dir_rel:
                raise GateClosed(
                    f"{label}.path {relative!r} is outside the launcher directory {bin_dir_rel!r}"
                )
            recorded_bytes = entry["bytes"]
            recorded_sha = entry["sha256"]
            if (
                isinstance(recorded_bytes, bool)
                or not isinstance(recorded_bytes, int)
                or recorded_bytes <= 0
                or not isinstance(recorded_sha, str)
                or _SHA256.fullmatch(recorded_sha) is None
            ):
                raise GateClosed(f"{label} lacks valid bytes/sha256")
            resolved = _resolve_under(self.runtime_root, relative, f"{label}.path")
            actual_bytes, actual_sha = _measure_file(resolved, f"{label}.path")
            if actual_bytes != recorded_bytes or actual_sha != recorded_sha:
                raise GateClosed(
                    f"{label} drift: runtime library {relative!r} does not match the "
                    "receipt; model touch refused"
                )
        bin_dir = Path(self.runtime_root) / bin_dir_rel
        actual_files: set[str] = set()
        try:
            for entry in bin_dir.iterdir():
                if entry.is_file():
                    actual_files.add(f"{bin_dir_rel}/{entry.name}")
                else:
                    raise GateClosed(
                        f"runtime directory contains a non-file entry {entry.name!r} "
                        "(subdirectory or dangling symlink); the exact-set contract "
                        "covers regular files only, so nothing else may live there"
                    )
        except OSError as error:
            raise GateClosed(f"cannot enumerate runtime directory {bin_dir}: {error}") from error
        declared = seen | {binary_rel}
        if actual_files != declared:
            raise GateClosed(
                "runtime directory drift: on-disk files "
                f"{sorted(actual_files ^ declared)} are unlisted or missing versus the "
                "receipt; model touch refused"
            )

    def _lock_dataset_entries(
        self, lock: Mapping[str, object] | None = None
    ) -> dict[str, Mapping[str, object]]:
        """Every ``kind: dataset`` entry in the umbrella lock, keyed by name.

        Real speech-aware carriers live in ``asset_catalog`` alongside the
        frozen-baseline ``datasets`` list, local-candidate assets and the
        general-audio assets explicitly excluded from this study. Model entries
        live in a disjoint ``models`` list and never appear here — a plan cannot
        claim a model lock key as its speech carrier."""

        if lock is None:
            lock, _ = self._load_lock_with_hash()
        entries: dict[str, Mapping[str, object]] = {}
        for list_key in ("datasets", "asset_catalog"):
            value = lock.get(list_key)
            if not isinstance(value, list):
                continue
            for item in value:
                if (
                    isinstance(item, Mapping)
                    and item.get("kind") == "dataset"
                    and isinstance(item.get("name"), str)
                ):
                    entries[item["name"]] = item
        if not entries:
            raise GateClosed("datasets lock yields no named dataset entries")
        return entries

    def _resolve_carrier_dataset_entry(
        self, carrier_lock_key: str, lock: Mapping[str, object] | None = None
    ) -> Mapping[str, object]:
        """Resolve and scope-check a plan's carrier against the umbrella lock (I2).

        A carrier must: (a) exist as a ``kind: dataset`` entry in the umbrella lock
        — model entries and unknown keys are refused; (b) not be one of the
        general-audio assets this study explicitly excludes; and (c) carry a
        non-empty ``profiles`` list intersecting this study's speech-aware scope.
        A dataset entry with no ``profiles`` field fails closed rather than being
        assumed in scope: naming a key in the lock never by itself proves it is a
        speech-domain carrier of this study."""

        entry = self._lock_dataset_entries(lock).get(carrier_lock_key)
        if entry is None:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is not a dataset entry in "
                "the umbrella datasets lock (model entries and unknown keys are "
                "never a valid speech carrier); model touch refused"
            )
        if carrier_lock_key in general_audio_deny_lock_keys(self.source_root):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is a general-audio asset "
                "explicitly excluded from the speech-aware-evidence-acquisition "
                "study, whose scope is human speech and its linguistic content "
                "only (ASR, entities, contextual biasing, spoken QA, meeting "
                "speech); model touch refused"
            )
        profiles = entry.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} has no profiles field in "
                "the umbrella datasets lock; scope cannot be proven so the touch "
                "is refused (fail-closed)"
            )
        if not (set(profiles) & ALLOWED_CARRIER_PROFILES):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} profiles {profiles!r} do "
                "not intersect this study's speech-only scope "
                f"{sorted(ALLOWED_CARRIER_PROFILES)}; model touch refused"
            )
        return entry

    def _require_exposure_preregistration(
        self, plan: "ExecutionPlan", lock: Mapping[str, object] | None = None
    ) -> None:
        """The pre-registered row is cross-checked field by field against the plan.

        A run id string alone proves nothing: the row must have been written with
        the same profile, split role, split identity hash and budgets the plan now
        claims, and must still read ``consumed = no``. EVERY markdown table in the
        ledger whose header carries the contract's run-id column contributes rows
        (I2) -- a second table, or a stray prose line between two data rows of one
        table, can never make a registered row invisible to the duplicate/consumed/
        budget checks below."""

        try:
            text = Path(self.exposure_ledger).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise GateClosed(
                f"exposure ledger missing or unreadable ({self.exposure_ledger}): {error}"
            ) from error
        rows = _parse_ledger_tables(text)

        def cell(row: Mapping[str, str], column_name: str) -> str:
            if column_name not in row:
                raise GateClosed(
                    f"exposure row lacks column {column_name!r} (its governing table "
                    "header does not declare it)"
                )
            return row[column_name]

        matched = [row for row in rows if cell(row, _EXPOSURE_RUN_COLUMN) == plan.run_id]
        if not matched:
            raise GateClosed(
                f"model touch refused: run {plan.run_id!r} has no pre-registered exposure "
                f"row in {self.exposure_ledger} (rows are written before results are read)"
            )
        if len(matched) > 1:
            raise GateClosed(f"run {plan.run_id!r} is pre-registered more than once")
        row = matched[0]
        for column_name, expected in (
            ("execution profile", plan.execution_profile),
            ("split role", plan.split_role),
            ("split identity hash", plan.split_identity_hash),
        ):
            actual = cell(row, column_name)
            if actual != expected:
                raise GateClosed(
                    f"exposure row disagrees with the execution plan on {column_name!r}: "
                    f"row {actual!r} vs plan {expected!r}; model touch refused"
                )
        carrier_cell = cell(row, _EXPOSURE_CARRIER_COLUMN)
        known_carrier_keys = set(self._lock_dataset_entries(lock))
        carrier_tokens = [
            token for token in _CARRIER_CELL_TOKEN_SPLIT.split(carrier_cell) if token
        ]
        named_carriers = [token for token in carrier_tokens if token in known_carrier_keys]
        if len(named_carriers) != 1:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} ({carrier_cell!r}) must "
                "name exactly one known carrier lock key unambiguously; found "
                f"{named_carriers or 'none'}; model touch refused (I2: ambiguous carrier "
                "metadata fails closed)"
            )
        if named_carriers[0] != plan.carrier_lock_key:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} names carrier "
                f"{named_carriers[0]!r}, not the execution plan's carrier "
                f"{plan.carrier_lock_key!r}; model touch refused (I2: carrier scope and "
                "exposure carrier must bind)"
            )
        if cell(row, "consumed").lower() != "no":
            raise GateClosed(
                f"exposure row for {plan.run_id!r} is already consumed; a consumed run "
                "cannot be re-executed"
            )
        for column_name, planned, parse in (
            ("calls", plan.planned_model_calls, int),
            ("speech audio seconds", plan.planned_speech_audio_seconds, int),
            ("gpu hours", plan.planned_gpu_hours, float),
        ):
            raw = cell(row, column_name)
            try:
                registered = parse(raw)
            except ValueError as error:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a number, got {raw!r}"
                ) from error
            if not math.isfinite(registered) or registered < 0:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a finite non-negative "
                    f"number, got {raw!r}; NaN or negative cells would disable the "
                    "budget arithmetic"
                )
            if registered < planned:
                raise GateClosed(
                    f"execution plan claims {planned} {column_name} but only {registered} "
                    "were pre-registered; model touch refused"
                )

        # The first-slice caps are SLICE totals (consolidated contract §6), not
        # per-run allowances: sum every registered row — consumed or not — and
        # refuse when the campaign total would exceed the frozen budget. N
        # individually-bounded runs cannot smuggle a paper-scale campaign.
        #
        # R0 repair T4 (I6): registration alone is advisory -- what a row *claims*
        # it will spend, written before any request happens. Actual attempt usage
        # persisted under <data_root>/attempts/ (core.attempts.AttemptStore) is what
        # was genuinely spent. Take the conservative (larger) of the two per column
        # so a ledger edited to understate registration after real usage already
        # accrued -- or any other registered/actual drift -- cannot silently reopen
        # spent slice budget. Imported locally: see the module-level NOTE on why
        # core.attempts is never imported at this module's top level.
        from .core.attempts import AttemptError, AttemptStore

        # Minor (fix-wave2, external-threat-model review round 2): a stray,
        # malformed-name directory directly under <data_root>/attempts/ (never
        # created by this study's own code, which only ever mints
        # validate_id()-checked run_id directories, but plausibly left behind
        # by manual tampering or an unrelated tool) made AttemptStore.
        # all_actual_usage's internal validate_id() call raise a bare
        # AttemptError that escaped assert_model_touch_allowed entirely --
        # an internal implementation detail leaking out of the gate's own
        # exception contract (every other refusal here is GateClosed).
        # Wrapped fail-closed: still refuses the touch, but as the gate's own
        # documented exception type.
        try:
            actual_calls, actual_audio, actual_gpu_seconds = AttemptStore(
                Path(self.data_root) / "attempts"
            ).all_actual_usage()
        except AttemptError as error:
            raise GateClosed(
                "cannot compute the slice-wide actual usage total from "
                f"{Path(self.data_root) / 'attempts'}: {error}; model touch refused"
            ) from error
        # Minor (fix-wave2): gpu hours previously had no derived counterpart --
        # calls/audio_seconds folded durable actual usage into the conservative
        # max below, but gpu hours was taken purely from self-declared ledger
        # cells even though gpu_seconds IS measured per run
        # (core.resources.ResourceSampler.summary, fed back into the durable
        # attempt record by core.driver.run_experiment via
        # AttemptHandle.record_gpu_seconds). Converted seconds -> hours here,
        # the same unit the ledger's "gpu hours" column and
        # planned_gpu_hours/FIRST_SLICE_CAPS["planned_gpu_hours"] already use.
        actual_by_column = {
            "calls": actual_calls,
            "speech audio seconds": actual_audio,
            "gpu hours": actual_gpu_seconds / 3600.0,
        }
        for column_name, cap_field, parse in (
            ("calls", "planned_model_calls", int),
            ("speech audio seconds", "planned_speech_audio_seconds", int),
            ("gpu hours", "planned_gpu_hours", float),
        ):
            cap = FIRST_SLICE_CAPS[cap_field]
            total = 0.0
            for row in rows:
                raw = cell(row, column_name)
                try:
                    registered = parse(raw)
                except ValueError as error:
                    raise GateClosed(
                        f"exposure ledger column {column_name!r} holds a non-numeric "
                        f"value {raw!r}; every registered row counts against the slice "
                        "budget and must parse"
                    ) from error
                if not math.isfinite(registered) or registered < 0:
                    raise GateClosed(
                        f"exposure ledger column {column_name!r} holds {raw!r}; slice "
                        "accounting requires finite non-negative registrations — a NaN "
                        "or negative row would silently re-open spent budget"
                    )
                total += registered
            total = max(total, actual_by_column.get(column_name, 0.0))
            if total > cap:
                raise GateClosed(
                    f"registered/actual {column_name} across the slice total {total}, "
                    f"exceeding the frozen first-slice cap {cap}; a new run requires a "
                    "new owner slice decision, not another row"
                )

    def assert_model_touch_allowed(
        self,
        plan: ExecutionPlan,
        *,
        full_hash: bool | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> str:
        """Refuse the touch unless a validated Stage-2 ``ExecutionPlan`` authorizes it
        AND both receipts verify. Plan/scope validation runs before any receipt or
        ledger byte is read, so a paper-scale request — however labeled — is refused
        first; then the run must be pre-registered in the exposure ledger (I2: the
        row's carrier column must name the plan's carrier), and the carrier itself
        must resolve to a genuine speech-dataset entry of this study's scope in the
        umbrella lock (never a model entry, never a general-audio asset, never an
        entry whose scope cannot be proven).

        ``full_hash`` (owner decision 2026-08-06, docs/owner-decisions-pending.md
        item 7) governs ONLY how the pinned GGUF set is verified; it is forwarded
        unchanged to :meth:`_validate_runtime` (see that method's own docstring for
        the exact True/False/None/``RUNTIME_FULL_HASH_ENV`` resolution order). The
        default, ``None``, is the gate's own SAFE choice: a real model touch
        (``core.model.FrozenCoreAdapter``, which never overrides this parameter and
        does not itself set ``RUNTIME_FULL_HASH_ENV``) always pays for one genuine
        full SHA-256 verification of the GGUF set per process/session before it can
        ever be fast-pathed. Runtime libraries under ``build/bin`` are unaffected —
        they are always fully hashed, regardless of ``full_hash`` (module
        docstring). ``diagnostics``, if given a mutable dict, is populated by
        :meth:`_validate_runtime` with what actually happened (never merely what
        was requested) — see its own docstring.

        Returns the umbrella lock's SHA-256 (M-3): the lock is read exactly ONCE
        here (:meth:`_load_lock_with_hash`) and the same parsed document is
        threaded into every check below that needs it, rather than each
        independently re-reading the file — so two reads within one call can
        never disagree, and the hash is available to bind into the run manifest
        (see ``core.model.FrozenCoreAdapter``) for the ledger's "dataset rev" cell.
        """

        if type(plan) is not ExecutionPlan:
            raise ExecutionScopeError(
                "a model touch requires a structured ExecutionPlan (the exact contract "
                "type — subclasses could override validate); bare profile strings were "
                "retired by 续93 (semantic scope gate)"
            )
        ExecutionPlan.validate(plan)
        if plan.execution_profile not in MODEL_TOUCH_PROFILES:
            raise ExecutionScopeError(
                f"execution profile {plan.execution_profile!r} does not authorize a model "
                f"touch; model-facing Stage-2 profiles are {sorted(MODEL_TOUCH_PROFILES)}"
            )
        lock, lock_sha256 = self._load_lock_with_hash()
        self._require_exposure_preregistration(plan, lock)
        self._resolve_carrier_dataset_entry(plan.carrier_lock_key, lock)
        self._validate_e0()
        self._validate_runtime(lock, full_hash=full_hash, diagnostics=diagnostics)
        return lock_sha256
