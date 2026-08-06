"""``FrozenCoreGate`` assembly: the fail-closed entry gate in front of every
frozen-core (model) touch.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1).
The class itself is composed from four mixins (each its own module, split by
validation concern -- E0/scoring-freeze, media/reference identity, runtime/GGUF,
carrier-scope/exposure-ledger) purely so no single file needs to hold the whole
~1200-line validation surface; the mixins carry only methods (no dataclass
fields, no ``__init__``), so combining them via multiple inheritance changes
nothing about ``FrozenCoreGate``'s runtime behaviour, field set, equality or
hashing -- ``@dataclass(frozen=True)`` still processes exactly the 7 annotated
fields below, exactly as it did when every method lived in one class body.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import ExecutionScopeError, GateClosed
from .gate_e0 import _E0AndScoringFreezeMixin
from .gate_exposure import _ExposureAndCarrierMixin
from .gate_identity import _MediaReferenceIdentityMixin
from .gate_runtime import _RuntimeValidationMixin
from .identifiers import STUDY_SLUG
from .plan import MODEL_TOUCH_PROFILES, ExecutionPlan


@dataclass(frozen=True)
class FrozenCoreGate(
    _E0AndScoringFreezeMixin,
    _MediaReferenceIdentityMixin,
    _RuntimeValidationMixin,
    _ExposureAndCarrierMixin,
):
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
