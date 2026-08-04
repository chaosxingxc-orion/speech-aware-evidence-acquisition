"""Fail-closed E0 engineering contracts.

Model-free contracts frozen by the current owner execution authority
(``SAEA-OWNER-CONSOLIDATED-EXECUTION-CONTRACT-2026-08-04``; the earlier
``SAEA-OWNER-SPEECH-SCOPE-AND-IDENTITY-2026-08-04`` is an inherited source record, not the
current contract): the runtime information boundary, OBS/ORG/SUPPLY/USE trace separation,
exposure-claim schema, the Stage-2 execution-scope guard with its structured
``ExecutionPlan``, and the frozen-core entry gate. Everything here is standard-library only
so the contracts are testable before any ML stack is installed and before any model is
touched.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


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

STUDY_SLUG = "speech-aware-evidence-acquisition"
MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf"
E0_RECEIPT_SCHEMA = "saea-e0-closure-receipt-v1"
RUNTIME_RECEIPT_SCHEMA = "saea-runtime-receipt-v2"
SCORING_PACKAGE_RELPATH = "src/speech_aware_evidence_acquisition/scoring"
_REPORTED_BUILD = re.compile(r"\(([0-9a-f]{7,40})\)")

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
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ExecutionScopeError("execution plan run_id must be a non-empty string")
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
      asset root; the gate re-reads every declared GGUF file, the llama.cpp launcher
      binary AND every runtime library in the launcher's directory (exact set — an
      unlisted or missing file refuses) and recomputes size and SHA-256 itself;
    - the pre-registered exposure row must agree with the ``ExecutionPlan`` field by
      field (profile, split role, split identity hash, consumed=no, planned budgets);
    - absolute paths, drive letters, ``..`` traversal, path escapes, duplicates and
      extra/missing model files are all refused.

    Any missing file, malformed JSON, schema/identity mismatch, lock mismatch or byte
    drift refuses the touch. Verification is instantaneous: it proves the bytes at
    measurement time. The process that opens the gate must be the process that starts
    llama-server, immediately afterward — a gate result must never be cached, shared
    across processes, or separated from the launch it authorizes.
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
            if "__pycache__" in rel_parts:
                continue
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

    def _lock_model_entry(self) -> Mapping[str, object]:
        lock = self._load(self.lock_path, "datasets lock")
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

    def _validate_runtime(self) -> None:
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
        lock_entry = self._lock_model_entry()
        subdir = str(lock_entry["local_subdir"]).rstrip("/")

        files = runtime["gguf_files"]
        if not isinstance(files, list) or not files:
            raise GateClosed("runtime receipt lacks a non-empty gguf_files list")
        if len(files) != lock_entry["files"]:
            raise GateClosed(
                f"runtime receipt declares {len(files)} model files but the lock freezes "
                f"{lock_entry['files']}; extra or missing model files are refused"
            )
        seen: set[str] = set()
        total_bytes = 0
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
            total_bytes += actual_bytes
        if total_bytes != lock_entry["size_bytes"]:
            raise GateClosed(
                f"model files total {total_bytes} bytes but the lock freezes "
                f"{lock_entry['size_bytes']}; model touch refused"
            )

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

    def _lock_asset_names(self) -> set[str]:
        lock = self._load(self.lock_path, "datasets lock")
        names = {
            item["name"]
            for value in lock.values()
            if isinstance(value, list)
            for item in value
            if isinstance(item, Mapping) and isinstance(item.get("name"), str)
        }
        if not names:
            raise GateClosed("datasets lock yields no named assets")
        return names

    def _require_exposure_preregistration(self, plan: "ExecutionPlan") -> None:
        """The pre-registered row is cross-checked field by field against the plan.

        A run id string alone proves nothing: the row must have been written with
        the same profile, split role, split identity hash and budgets the plan now
        claims, and must still read ``consumed = no``. Only the first ledger table
        is parsed — a later table cannot inject rows into the contract columns."""

        try:
            text = Path(self.exposure_ledger).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise GateClosed(
                f"exposure ledger missing or unreadable ({self.exposure_ledger}): {error}"
            ) from error
        header: list[str] | None = None
        rows: list[list[str]] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("|") and stripped.endswith("|")):
                if header is not None:
                    break
                continue
            cells = [cell.strip() for cell in stripped[1:-1].split("|")]
            if header is None:
                lowered = [cell.lower() for cell in cells]
                if _EXPOSURE_RUN_COLUMN in lowered:
                    header = lowered
                continue
            if all(not cell.strip("-: ") for cell in cells):
                continue
            rows.append(cells)
        if header is None:
            raise GateClosed(
                f"exposure ledger lacks a table header with a {_EXPOSURE_RUN_COLUMN!r} column"
            )

        def cell(cells: list[str], column_name: str) -> str:
            if column_name not in header:
                raise GateClosed(f"exposure ledger header lacks column {column_name!r}")
            index = header.index(column_name)
            if index >= len(cells):
                raise GateClosed(f"exposure row for {plan.run_id!r} lacks column {column_name!r}")
            return cells[index]

        matched = [
            cells for cells in rows if cell(cells, _EXPOSURE_RUN_COLUMN) == plan.run_id
        ]
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
        for column_name, cap_field, parse in (
            ("calls", "planned_model_calls", int),
            ("speech audio seconds", "planned_speech_audio_seconds", int),
            ("gpu hours", "planned_gpu_hours", float),
        ):
            cap = FIRST_SLICE_CAPS[cap_field]
            total = 0.0
            for cells in rows:
                raw = cell(cells, column_name)
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
            if total > cap:
                raise GateClosed(
                    f"registered {column_name} across the slice total {total}, exceeding "
                    f"the frozen first-slice cap {cap}; a new run requires a new owner "
                    "slice decision, not another row"
                )

    def assert_model_touch_allowed(self, plan: ExecutionPlan) -> None:
        """Refuse the touch unless a validated Stage-2 ``ExecutionPlan`` authorizes it
        AND both receipts verify. Plan/scope validation runs before any receipt or
        ledger byte is read, so a paper-scale request — however labeled — is refused
        first; then the run must be pre-registered in the exposure ledger and its
        carrier must exist in the umbrella lock."""

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
        self._require_exposure_preregistration(plan)
        if plan.carrier_lock_key not in self._lock_asset_names():
            raise GateClosed(
                f"carrier lock key {plan.carrier_lock_key!r} is not in the umbrella "
                "datasets lock"
            )
        self._validate_e0()
        self._validate_runtime()
