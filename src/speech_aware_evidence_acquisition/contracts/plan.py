"""Stage-2 execution-scope guard and the structured ``ExecutionPlan`` contract.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import math
import os
import platform
from dataclasses import dataclass

from .errors import ExecutionScopeError
from .identifiers import RUN_ID_PATTERN, STUDY_SLUG, _SHA256

ALLOWED_EXECUTION_PROFILES = (
    "model-free-check",
    "baseline-reproduction",
    "bounded-discovery-probe",
)
MODEL_TOUCH_PROFILES = frozenset({"baseline-reproduction", "bounded-discovery-probe"})
PAPER_GATE_TOKEN = "OWNER_GO_AND_PAPER_EXECUTION_CONTRACT"
_PAPER_SCALE_MARKERS = ("paper", "confirmatory", "production")

EXECUTION_PLAN_SCHEMA = "saea-execution-plan-v1"
TEXT_ENCODER_PLAN_SCHEMA = "saea-text-encoder-plan-v1"
STAGE2_SPLIT_ROLES = frozenset({"discovery", "dev"})


def assert_wsl_execution_environment(
    *,
    os_name: str | None = None,
    kernel_release: str | None = None,
) -> str:
    """Require the repository's sole formal execution authority: WSL2.

    Windows is a source-control synchronization surface only. Native Windows,
    native Linux, containers, and compatibility layers must never perform a
    formal model touch for this study. Optional arguments make the platform
    decision independently testable; production callers always omit them and
    therefore use the running kernel identity.
    """

    resolved_os_name = os.name if os_name is None else os_name
    resolved_kernel_release = (
        platform.release() if kernel_release is None else kernel_release
    )
    normalized_release = resolved_kernel_release.casefold()
    if (
        resolved_os_name != "posix"
        or "microsoft-standard-wsl2" not in normalized_release
    ):
        raise ExecutionScopeError(
            "formal execution requires the WSL2 compute authority; native Windows "
            "is restricted to Git/status synchronization and no experiment or model "
            "contact may run there"
        )
    return "wsl2"


def assert_execution_scope(profile: object) -> str:
    """Fail-closed Stage-2 execution-scope guard (contract sections 6 and 7).

    This study repository accepts exactly the profiles in ``ALLOWED_EXECUTION_PROFILES``.
    ``paper-scale-confirmatory`` -- and any other paper/confirmatory/production-scale
    profile -- is never accepted here: Stage-3 work requires promotion to an independent
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
    """Structured, contract-bound plan for one governed contact run.

    Every field is a value the consolidated execution contract already freezes
    (profiles, Stage-2 split roles, hash disciplines); the schema is therefore not
    speculative design and may be extended at R0 only via a dated owner decision. A
    profile label alone never authorizes a run: the gate validates this plan before
    reading any receipt, so a paper-scale run cannot be smuggled in under an allowed
    profile name. Calls and GPU hours are finite and positive. Speech seconds
    are positive under the historical execution schema and exactly integer
    zero under the explicit text-encoder schema. All three are cross-checked
    against their pre-registered exposure-ledger row
    (``FrozenCoreGate._require_exposure_preregistration``), but carry no numeric
    ceiling of their own -- the first-slice caps that used to live here were retired
    by the 2026-08-06 owner amendment (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS).
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
        if self.schema not in {EXECUTION_PLAN_SCHEMA, TEXT_ENCODER_PLAN_SCHEMA}:
            raise ExecutionScopeError(
                "execution plan schema must be "
                f"{EXECUTION_PLAN_SCHEMA!r} or {TEXT_ENCODER_PLAN_SCHEMA!r}, "
                f"got {self.schema!r}"
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
        # Owner amendment 2026-08-06: field validation (finite, positive, integral
        # where applicable) stays; the comparison against a global first-slice cap
        # that used to run here does not -- see the module-level comment above
        # this class for the retirement record.
        for field_name in ("planned_model_calls", "planned_gpu_hours"):
            value = getattr(self, field_name)
            integral = field_name == "planned_model_calls"
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
        speech_seconds = self.planned_speech_audio_seconds
        if self.schema == TEXT_ENCODER_PLAN_SCHEMA:
            if type(speech_seconds) is not int or speech_seconds != 0:
                raise ExecutionScopeError(
                    "text-encoder execution plan planned_speech_audio_seconds "
                    "must be exactly integer zero"
                )
        elif (
            isinstance(speech_seconds, bool)
            or not isinstance(speech_seconds, int)
            or speech_seconds <= 0
        ):
            raise ExecutionScopeError(
                "execution plan planned_speech_audio_seconds must be a finite "
                "positive integer"
            )
        return self
