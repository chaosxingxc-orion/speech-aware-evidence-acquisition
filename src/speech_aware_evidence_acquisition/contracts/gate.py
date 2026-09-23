"""``FrozenCoreGate`` assembly: the fail-closed entry gate in front of every
frozen-core (model) touch.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1).
The class itself is composed from five mixins (each its own module, split by
validation concern -- E0/scoring-freeze, media/reference identity, evidence
identity, runtime/GGUF, carrier-scope/exposure-ledger) purely so no single file
needs to hold the whole validation surface; the mixins carry only methods (no
dataclass fields, no ``__init__``), so combining them via multiple inheritance
changes nothing about ``FrozenCoreGate``'s runtime behaviour, field set,
equality or hashing -- ``@dataclass(frozen=True)`` still processes exactly the
7 annotated fields below, exactly as it did when every method lived in one
class body.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .errors import ExecutionScopeError, GateClosed
from .gate_e0 import _E0AndScoringFreezeMixin
from .gate_evidence_identity import _EvidenceIdentityMixin
from .gate_exposure import _ExposureAndCarrierMixin
from .gate_identity import _MediaReferenceIdentityMixin
from .gate_runtime import _RuntimeValidationMixin
from .identifiers import MODEL_LOCK_KEY, STUDY_SLUG
from .plan import (
    MODEL_TOUCH_PROFILES,
    TEXT_ENCODER_PLAN_SCHEMA,
    ExecutionPlan,
    assert_wsl_execution_environment,
)


@dataclass(frozen=True)
class FrozenCoreGate(
    _E0AndScoringFreezeMixin,
    _MediaReferenceIdentityMixin,
    _EvidenceIdentityMixin,
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
    - the runtime receipt binds this run's DECLARED model lock key
      (``expected_model_lock_key`` -- default: the frozen Q8_0
      ``contracts.MODEL_LOCK_KEY``, so every caller that does not opt in is
      unaffected) to canonical relative paths under the controlled asset root
      via that SAME key's own entry in the umbrella ``docs/datasets.lock.json``;
      the gate always re-reads the llama.cpp launcher binary AND every
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
    #: Optional alternate root holding the lock-relative GGUF paths. Dataset
    #: carriers remain under ``data_root``; only runtime model-byte identity is
    #: resolved here. ``None`` preserves the historical canonical-root path.
    model_root: Path | None = None
    #: Optional bounded D1 media successor. The immutable E0 D1 artifact is
    #: never rewritten; these bytes are accepted only when their configured
    #: digest and their own parent-D1 binding both verify.
    d1_media_supplement: Path | None = None
    d1_media_supplement_sha256: str | None = None
    #: Optional bounded D1 EVIDENCE-LAYER successor (2026-09-06, KC-E1
    #: precondition 1): one additive ``saea-d1-evidence-supplement-v1`` document
    #: declaring exactly one D1 layer key the base artifact does not carry --
    #: today ``conec``'s ``e21_participant_names``. Same discipline as the media
    #: supplement above: the immutable E0 D1 artifact is never rewritten, and
    #: these bytes are accepted only when their configured digest, their
    #: parent-D1 binding and their sample-universe binding all verify
    #: (``gate_evidence_identity._EvidenceIdentityMixin._d1_evidence_supplement_manifest``).
    d1_evidence_supplement: Path | None = None
    d1_evidence_supplement_sha256: str | None = None
    #: WHICH pinned model this run declares -- ``_validate_runtime``
    #: (``gate_runtime.py``) asserts the runtime receipt's own
    #: ``model_lock_key`` equals THIS value (never a bare module constant),
    #: and ``_lock_model_entry`` resolves the umbrella lock's model entry by
    #: THIS value too, so the GGUF file-set/size check is bound to the same
    #: declared model as the identity check above it. Defaults to the frozen
    #: Q8_0 ``contracts.MODEL_LOCK_KEY`` -- every existing caller that never
    #: sets this is byte-identical to before this field existed.
    expected_model_lock_key: str = MODEL_LOCK_KEY

    E0_DELIVERABLES = ("d1_identity", "d2_leakage", "d3_scoring", "d4_trace")

    #: Kept in sync BY HAND with ``core.config.DEFAULT_RUNTIME_RECEIPT_RELPATH``
    #: -- ``contracts`` stays dependency-free of ``core`` by design (module
    #: docstring's circular-import note), so this literal is intentionally
    #: duplicated rather than imported; both name the exact same on-disk
    #: default, ``docs/receipts/runtime.json``.
    _DEFAULT_RUNTIME_RECEIPT_RELPATH = "receipts/runtime.json"

    @classmethod
    def for_study_repo(
        cls,
        repo_root: Path,
        data_root: Path,
        runtime_root: Path,
        *,
        runtime_receipt_relpath: str = _DEFAULT_RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key: str = MODEL_LOCK_KEY,
        model_root: Path | None = None,
        d1_media_supplement_relpath: str | None = None,
        d1_media_supplement_sha256: str | None = None,
        d1_evidence_supplement_relpath: str | None = None,
        d1_evidence_supplement_sha256: str | None = None,
    ) -> "FrozenCoreGate":
        """The canonical production binding — the only gate a real run may use.

        Pins the committed receipts, the study exposure ledger and the umbrella lock
        of the registered adjacent-checkout layout. Constructing a gate against any
        other ledger (a copy, a temp file, a synthetic row) does not authorize
        anything: pre-registration means a row in ``docs/exposure-ledger.md``.

        ``runtime_receipt_relpath`` (relative to ``<repo_root>/docs/``) lets a
        caller pin a DIFFERENT committed runtime receipt -- e.g.
        ``"receipts/runtime-q4km.json"`` for a second pinned model -- while
        every existing caller that omits it keeps resolving the exact same
        ``docs/receipts/runtime.json`` as before. This governs only WHICH
        FILE is read.

        ``expected_model_lock_key`` is the matching identity half: the gate's
        own ``_validate_runtime`` asserts that file's ``model_lock_key``
        equals THIS value (never a bare module constant), and
        ``_lock_model_entry`` resolves the umbrella lock's model entry by it
        too. Selecting a receipt FILE for a different pinned model is
        therefore not, by itself, an authorization to open the gate against
        it -- a caller must ALSO declare that it expects that model, and the
        one sanctioned way to do so consistently is to derive both keyword
        arguments from the SAME composed run config
        (``core.config.runtime_receipt_relpath`` /
        ``core.config.model_lock_key``), exactly as ``core.driver.smoke.
        _cli_smoke`` and ``core.driver.cli._cli_run`` do -- see that
        pairing's own dedicated coverage in
        ``tests/contract/test_model_lock_key_binding.py``. Defaults to the
        frozen Q8_0 ``contracts.MODEL_LOCK_KEY``, so every existing caller
        that omits it keeps exactly its old behaviour.
        """

        root = Path(repo_root)
        if (d1_media_supplement_relpath is None) != (
            d1_media_supplement_sha256 is None
        ):
            raise ValueError(
                "d1_media_supplement_relpath and d1_media_supplement_sha256 "
                "must be configured together"
            )
        if (d1_evidence_supplement_relpath is None) != (
            d1_evidence_supplement_sha256 is None
        ):
            raise ValueError(
                "d1_evidence_supplement_relpath and d1_evidence_supplement_sha256 "
                "must be configured together"
            )
        return cls(
            e0_receipt=root / "docs" / "receipts" / "e0-closure.json",
            runtime_receipt=root / "docs" / runtime_receipt_relpath,
            data_root=Path(data_root),
            lock_path=root.parent.parent / "docs" / "datasets.lock.json",
            runtime_root=Path(runtime_root),
            exposure_ledger=root / "docs" / "exposure-ledger.md",
            source_root=root,
            model_root=Path(model_root) if model_root is not None else None,
            d1_media_supplement=(
                root / "docs" / d1_media_supplement_relpath
                if d1_media_supplement_relpath is not None
                else None
            ),
            d1_media_supplement_sha256=d1_media_supplement_sha256,
            d1_evidence_supplement=(
                root / "docs" / d1_evidence_supplement_relpath
                if d1_evidence_supplement_relpath is not None
                else None
            ),
            d1_evidence_supplement_sha256=d1_evidence_supplement_sha256,
            expected_model_lock_key=expected_model_lock_key,
        )

    def __post_init__(self) -> None:
        """ONE supplement per gate. The base D1 identity artifact is the only
        thing a run is ever entitled to assume; a bounded successor is a
        deliberate, named exception, and a run that needs TWO of them is a run
        whose identity closure should be rebuilt rather than patched twice.
        Enforced here so no caller path -- driver, script or test -- can
        assemble a two-supplement gate by accident."""

        if self.d1_media_supplement is not None and self.d1_evidence_supplement is not None:
            raise ValueError(
                "a FrozenCoreGate carries the base D1 identity plus AT MOST ONE "
                "supplement; a media supplement and an evidence supplement were both "
                "configured"
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
        arm: str | None = None,
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

        ``arm`` (E2.4, 2026-09-05) is the D2 arm this touch will send. It is
        optional and defaults to ``None``, so every pre-existing caller is
        byte-identical; it exists for exactly one check,
        :meth:`_require_construction_role_for_visible_targets`, which refuses a
        construction-gold-visible arm whose plan is not bound to a committed
        construction roster. Naming an arm can only ever ADD a refusal, never
        widen anything, and the payload allowlist itself remains
        ``core.model.FrozenCoreAdapter``'s job, unchanged.

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
                "retired by umbrella Decision-Log continuation entry 93 (semantic scope "
                "gate)"
            )
        ExecutionPlan.validate(plan, source_root=self.source_root)
        if plan.schema == TEXT_ENCODER_PLAN_SCHEMA:
            raise ExecutionScopeError(
                "a text-encoder plan cannot authorize a Qwen frozen-core model touch"
            )
        if plan.execution_profile not in MODEL_TOUCH_PROFILES:
            raise ExecutionScopeError(
                f"execution profile {plan.execution_profile!r} does not authorize a model "
                f"touch; model-facing Stage-2 profiles are {sorted(MODEL_TOUCH_PROFILES)}"
            )
        assert_wsl_execution_environment()
        self._require_construction_role_for_visible_targets(plan, arm)
        # Owner decisions 99 and 107 (2026-09-22/23): a ``final-report`` plan
        # carries the one-shot SLURP test-split read or one of its label-free
        # preparations. Beyond the owner allowance ``ExecutionPlan.validate``
        # already re-verified above, it must additionally prove -- HERE, from
        # live bytes, not from a committed receipt -- that its roster is
        # disjoint from every roster, knowledge store and exemplar pool the
        # control plane was built on, that it carries no construction-visible
        # arm, and that it has not already been attempted. Returns immediately
        # for every other split role.
        self._require_final_report_isolation(plan, arm)
        lock, lock_sha256 = self._load_lock_with_hash()
        self._require_exposure_preregistration(plan, lock)
        self._resolve_carrier_dataset_entry(plan.carrier_lock_key, lock)
        self._validate_e0()
        self._validate_runtime(lock, full_hash=full_hash, diagnostics=diagnostics)
        return lock_sha256
