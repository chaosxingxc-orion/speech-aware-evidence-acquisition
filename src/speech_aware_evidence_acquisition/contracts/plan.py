"""Stage-2 execution-scope guard and the structured ``ExecutionPlan`` contract.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
from dataclasses import InitVar, dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

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

# --------------------------------------------------------------------------- #
# The final-reporting split role (owner decisions 99 and 107; decision 108)
# --------------------------------------------------------------------------- #
#
# Owner decision 99 (2026-09-22) and owner decision 107 (2026-09-23),
# ``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``: exactly
# ONE complete official SLURP test-split read happens at the end of Stage 3,
# and its preparations (roster freeze, D1 media supplement, featcache packets,
# speech query vectors) are registered now and built ahead of time so the read
# waits on nothing.
#
# Section 6.3 of the one-shot read protocol draft
# (``docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md``,
# commit 16ed5b3f) states the shape of the remedy this block implements: "a
# paired code change admitting a machine role for it -- because no faithful
# role for final reporting exists in STAGE2_SPLIT_ROLES and 'confirmatory' is
# refused outright -- with its tests and the amendment cited in the code ...
# the code change should admit a role named for what it is (for example
# ``final-report``), never reuse ``dev``". Section 6.2 records why reusing
# ``dev`` would be exactly the relabeling the guard forbids: ``dev`` means
# "legal to calibrate against, never a final-reporting split".
#
# So ``final-report`` is admitted, and it is admitted FAIL-CLOSED. It is NOT a
# member of ``STAGE2_SPLIT_ROLES``: a plan carrying it is refused unless every
# one of the following holds, and each failure names what is missing.
#
#   1. the plan carries ``owner_allowance`` = {path, sha256};
#   2. ``path`` is a repo-relative POSIX path under ``docs/receipts/owner/``;
#   3. the execution profile is ``bounded-discovery-probe``;
#   4. the file exists and its BYTES hash to the pinned sha256;
#   5. it is a ``saea-owner-split-allowance-v1`` document of this study;
#   6. its ``status`` is exactly ``"authorised"``;
#   7. its ``split`` names this plan's carrier and split identity hash;
#   8. its ``permitted_run_ids`` contains this plan's run id, and partitions
#      into ``read_run_ids`` + ``preparation_run_ids``;
#   9. it names the dated owner decision, and states in ``venue`` why the read
#      and its preparations are not promoted to a ``papers/<slug>`` repository
#      (protocol section 6.2, Remedy A, which the draft recommends).
#
# The receipt committed today carries ``status: "pending-owner"``, so TODAY
# every ``final-report`` plan is refused at check 6. Decision 108 is the single
# owner ruling that unlocks it; flipping the status changes the receipt's bytes,
# which breaks every pinned sha256 until each is deliberately re-pinned.
#
# ``contracts`` stays dependency-free of ``core`` (see ``gate.py``'s
# circular-import note), so the receipt is read and hashed here with the
# standard library alone.

#: The machine role of a final-reporting read and of the label-free preparation
#: passes that touch the same rows. Never a member of ``STAGE2_SPLIT_ROLES``.
FINAL_REPORT_SPLIT_ROLE = "final-report"

#: The only execution profile a ``final-report`` plan may carry. The read is a
#: bounded, pre-registered probe of a frozen core, not a paper-scale campaign;
#: ``paper-scale-confirmatory`` remains refused by ``assert_execution_scope``.
FINAL_REPORT_EXECUTION_PROFILE = "bounded-discovery-probe"

OWNER_SPLIT_ALLOWANCE_SCHEMA = "saea-owner-split-allowance-v1"
OWNER_SPLIT_ALLOWANCE_RELDIR = "docs/receipts/owner"
OWNER_SPLIT_ALLOWANCE_AUTHORISED = "authorised"

#: The study checkout this module was imported from:
#: ``<repo>/src/speech_aware_evidence_acquisition/contracts/plan.py``. An
#: allowance receipt only counts when it is COMMITTED IN THIS REPOSITORY, so
#: the default resolution root is derived from the module's own location rather
#: than from a caller-supplied path. ``source_root`` overrides it for tests and
#: for ``FrozenCoreGate``, which pins its own ``source_root``.
_STUDY_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class OwnerSplitAllowance:
    """``{path, sha256}``: which committed owner-allowance receipt, and its bytes.

    A frozen dataclass rather than a mapping so an ``ExecutionPlan`` carrying
    one stays hashable, exactly as every other field leaves it.
    """

    path: str
    sha256: str

    @staticmethod
    def coerce(value: object) -> object:
        """A ``{path, sha256}`` mapping becomes an allowance; anything else is
        returned unchanged so ``validate`` can name what is wrong with it."""

        if isinstance(value, OwnerSplitAllowance) or value is None:
            return value
        if (
            isinstance(value, Mapping)
            and set(value) == {"path", "sha256"}
            and isinstance(value.get("path"), str)
            and isinstance(value.get("sha256"), str)
        ):
            return OwnerSplitAllowance(path=value["path"], sha256=value["sha256"])
        return value


def _allowance_receipt_path(allowance: OwnerSplitAllowance, source_root: object) -> Path:
    relpath = allowance.path
    if (
        not relpath
        or "\\" in relpath
        or relpath.startswith("/")
        or PurePosixPath(relpath).is_absolute()
        or ":" in relpath
        or any(part in ("", ".", "..") for part in PurePosixPath(relpath).parts)
        or not relpath.startswith(f"{OWNER_SPLIT_ALLOWANCE_RELDIR}/")
    ):
        raise ExecutionScopeError(
            f"owner allowance path {relpath!r} must be a repo-relative POSIX path under "
            f"{OWNER_SPLIT_ALLOWANCE_RELDIR!r} with no backslash, no drive letter, no "
            "leading slash and no '..' segment"
        )
    if _SHA256.fullmatch(allowance.sha256) is None:
        raise ExecutionScopeError(
            "owner allowance sha256 must be a 64-hex SHA-256 of the receipt's bytes, "
            f"got {allowance.sha256!r}"
        )
    root = Path(source_root) if source_root is not None else _STUDY_REPO_ROOT
    return root / relpath


def require_owner_split_allowance(
    *,
    run_id: str,
    execution_profile: str,
    carrier_lock_key: str,
    split_identity_hash: str,
    owner_allowance: object,
    source_root: object = None,
) -> Mapping[str, object]:
    """Verify a ``final-report`` authorisation, or raise naming what is missing.

    Returns the parsed receipt so a caller that has already paid for the read
    (``FrozenCoreGate``) can use its ``read_run_ids`` / ``preparation_run_ids``
    partition without re-reading the file. Every refusal is an
    :class:`ExecutionScopeError`; none of them is recoverable by relabeling.
    """

    # A caller reading the allowance out of a composed config fragment holds a
    # plain mapping; ``ExecutionPlan.__post_init__`` has already coerced its own
    # field. Coercing here too keeps every caller uniform, and a mapping of the
    # wrong shape still falls through to the refusal below.
    owner_allowance = OwnerSplitAllowance.coerce(owner_allowance)
    if owner_allowance is None:
        raise ExecutionScopeError(
            f"split role {FINAL_REPORT_SPLIT_ROLE!r} is a FINAL-REPORTING role and is "
            "refused unless the plan carries owner_allowance={'path','sha256'} naming a "
            f"committed {OWNER_SPLIT_ALLOWANCE_SCHEMA} receipt under "
            f"{OWNER_SPLIT_ALLOWANCE_RELDIR}/; no owner_allowance was declared (owner "
            "decisions 99 and 107; one-shot read protocol section 6.3)"
        )
    if not isinstance(owner_allowance, OwnerSplitAllowance):
        raise ExecutionScopeError(
            "execution plan owner_allowance must be an OwnerSplitAllowance or a mapping "
            "with exactly the string keys 'path' and 'sha256'; got "
            f"{owner_allowance!r}"
        )
    if execution_profile != FINAL_REPORT_EXECUTION_PROFILE:
        raise ExecutionScopeError(
            f"split role {FINAL_REPORT_SPLIT_ROLE!r} runs only under execution profile "
            f"{FINAL_REPORT_EXECUTION_PROFILE!r}; the plan declares {execution_profile!r}"
        )
    path = _allowance_receipt_path(owner_allowance, source_root)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ExecutionScopeError(
            f"owner allowance receipt is missing or unreadable ({path}): {error}; a "
            f"{FINAL_REPORT_SPLIT_ROLE!r} plan is refused until the committed receipt exists"
        ) from error
    measured = hashlib.sha256(raw).hexdigest()
    if measured != owner_allowance.sha256:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} hashes to {measured}, not the "
            f"pinned {owner_allowance.sha256}; a {FINAL_REPORT_SPLIT_ROLE!r} plan is refused "
            "on any byte drift (flipping the receipt's status is exactly such a drift and "
            "must be re-pinned deliberately)"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} is not readable JSON: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} must be a JSON object"
        )
    if document.get("schema") != OWNER_SPLIT_ALLOWANCE_SCHEMA:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} schema must be "
            f"{OWNER_SPLIT_ALLOWANCE_SCHEMA!r}, got {document.get('schema')!r}"
        )
    if document.get("study") != STUDY_SLUG:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} study identity must be "
            f"{STUDY_SLUG!r}, got {document.get('study')!r}"
        )
    status = document.get("status")
    if status != OWNER_SPLIT_ALLOWANCE_AUTHORISED:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} status is {status!r}, not "
            f"{OWNER_SPLIT_ALLOWANCE_AUTHORISED!r}; the dated owner decision that admits "
            f"this {FINAL_REPORT_SPLIT_ROLE!r} read and its preparations has not been "
            "taken, so the plan is refused"
        )
    split = document.get("split")
    if not isinstance(split, Mapping):
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} carries no 'split' object "
            "naming carrier_lock_key and split_identity_hash"
        )
    if split.get("carrier_lock_key") != carrier_lock_key:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} authorises carrier "
            f"{split.get('carrier_lock_key')!r}, not the plan's {carrier_lock_key!r}"
        )
    if split.get("split_identity_hash") != split_identity_hash:
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} authorises split identity "
            f"{split.get('split_identity_hash')!r}, not the plan's {split_identity_hash!r}"
        )
    permitted = document.get("permitted_run_ids")
    if (
        not isinstance(permitted, list)
        or not permitted
        or any(not isinstance(value, str) or not value for value in permitted)
        or len(set(permitted)) != len(permitted)
    ):
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} permitted_run_ids must be a "
            "non-empty list of distinct run ids"
        )
    read_ids = document.get("read_run_ids")
    preparation_ids = document.get("preparation_run_ids")
    if (
        not isinstance(read_ids, list)
        or not isinstance(preparation_ids, list)
        or set(read_ids) & set(preparation_ids)
        or set(read_ids) | set(preparation_ids) != set(permitted)
    ):
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} must partition "
            "permitted_run_ids into disjoint 'read_run_ids' and 'preparation_run_ids' "
            "lists that together name exactly the permitted run ids; the attempt budget "
            "of the one read depends on that partition"
        )
    if run_id not in permitted:
        raise ExecutionScopeError(
            f"run id {run_id!r} is not in the owner allowance's permitted_run_ids "
            f"{sorted(permitted)}; a {FINAL_REPORT_SPLIT_ROLE!r} plan may only carry a run "
            "id the owner named"
        )
    decision = document.get("dated_owner_decision")
    if not isinstance(decision, str) or not decision.strip():
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} must name the dated owner "
            "decision (its number and date) in 'dated_owner_decision'"
        )
    venue = document.get("venue")
    if not isinstance(venue, str) or not venue.strip():
        raise ExecutionScopeError(
            f"owner allowance receipt {owner_allowance.path} must state in 'venue' why this "
            "read and its preparations are not promoted to an independent papers/<slug> "
            "repository under " + PAPER_GATE_TOKEN + " (one-shot read protocol section 6.2, "
            "Remedy A, which the draft recommends)"
        )
    return document


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
    # Owner decisions 99/107 (see the FINAL_REPORT_SPLIT_ROLE block above):
    # which committed owner-allowance receipt authorises a ``final-report``
    # plan, and the sha256 its bytes must have. Optional and defaulted to
    # ``None``, so every pre-existing caller -- including ``e0/generate.py``'s
    # frozen dry-run construction -- is byte-identical to before it existed.
    # Declaring it on a ``discovery``/``dev`` plan is refused by ``validate``:
    # it is the final-report authorisation, not a decoration.
    #
    # An ``InitVar``, NOT an ordinary field, and deliberately so.
    # ``dataclasses.asdict(plan)`` is a SERIALIZED IDENTITY here: three frozen
    # launchers under ``docs/checks/`` compare it byte for byte against
    # committed execution-plan documents whose own SHA-256 they also assert,
    # ``core.driver.speech_native`` re-checks a RESUMED run's plan copy against
    # it, and ``core.driver.smoke`` writes it as the attempt's plan file. A
    # thirteenth field would have moved all of them at once and broken records
    # that must not be rewritten. An InitVar is an ``__init__`` parameter that
    # is not a field: ``fields()``, ``asdict()``, ``__eq__`` and ``__hash__``
    # all ignore it, so every serialized plan identity is byte-identical to
    # before -- while ``dataclasses.replace()`` still carries the value forward,
    # because an InitVar WITH a default is read back off the instance.
    #
    # What that costs, stated plainly: two plans differing only in their
    # allowance are equal and hash alike. That is the right semantics --
    # the allowance is AUTHORISATION, not identity -- and it is safe because
    # the receipt binds the run id and the split identity hash, both of which
    # ARE in the equality set, and because nothing reads the allowance off a
    # cached plan: ``validate`` and ``FrozenCoreGate`` each re-read and re-hash
    # the committed receipt on every call.
    owner_allowance: InitVar[object] = None

    def __post_init__(self, owner_allowance: object) -> None:
        # A plan built from JSON carries a {path, sha256} mapping; it is coerced
        # to the frozen ``OwnerSplitAllowance`` here so a caller can compare and
        # hash it. Anything else is stored exactly as given, so ``validate`` can
        # name what is wrong with it rather than raising an unrelated TypeError
        # at construction. The instance attribute shadows the class-level
        # InitVar default, which is what makes ``plan.owner_allowance`` and
        # ``replace()`` work.
        object.__setattr__(
            self, "owner_allowance", OwnerSplitAllowance.coerce(owner_allowance)
        )

    def validate(self, *, source_root: object = None) -> "ExecutionPlan":
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
        if self.split_role == FINAL_REPORT_SPLIT_ROLE:
            # Owner decisions 99 and 107; one-shot read protocol section 6.3.
            # The whole authority lives in the committed owner-allowance
            # receipt, and today's receipt says "pending-owner", so this call
            # refuses every final-report plan until decision 108 is taken.
            require_owner_split_allowance(
                run_id=self.run_id,
                execution_profile=self.execution_profile,
                carrier_lock_key=self.carrier_lock_key,
                split_identity_hash=self.split_identity_hash,
                owner_allowance=self.owner_allowance,
                source_root=source_root,
            )
        elif self.split_role not in STAGE2_SPLIT_ROLES:
            raise ExecutionScopeError(
                f"unknown split role {self.split_role!r}; Stage-2 roles are "
                f"{sorted(STAGE2_SPLIT_ROLES)} and the owner-allowance-gated "
                f"final-reporting role is {FINAL_REPORT_SPLIT_ROLE!r} (fail-closed)"
            )
        elif self.owner_allowance is not None:
            raise ExecutionScopeError(
                f"execution plan owner_allowance is only meaningful for split role "
                f"{FINAL_REPORT_SPLIT_ROLE!r}; a {self.split_role!r} plan that declares one "
                "is refused rather than silently ignored"
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
