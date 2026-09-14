"""``verify_bundle``'s manifest-header checks: schema/study/status,
``study_commit`` shape, ``scorers`` shape+registration, and the
COMPLETED-only artifact-presence + stale-marker refusals.

Split out of ``verify.py`` (R0 repair refactor stage 2, part C, pure move,
no behaviour change) purely for file size. This chunk is self-contained: it
only ever reads ``manifest`` and returns the validated ``status`` string --
nothing later in ``verify_bundle`` feeds back into it.
"""

from __future__ import annotations

from typing import Mapping

from ...contracts import STUDY_SLUG
from ..base import SCORERS
from . import (
    RUN_MANIFEST_SCHEMA,
    STATUS_COMPLETED,
    UNAVAILABLE_COMMIT_PREFIX,
    _FULL_COMMIT_PATTERN,
    _VALID_STATUSES,
    BundleError,
)


def _verify_manifest_header(manifest: Mapping[str, object]) -> str:
    """Schema/study/status/``study_commit``-shape/``scorers`` checks; returns
    the validated ``status``. Raises :class:`BundleError` on any refusal."""

    if manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        raise BundleError(
            f"run manifest schema must be {RUN_MANIFEST_SCHEMA!r}, got {manifest.get('schema')!r}"
        )
    if manifest.get("study") != STUDY_SLUG:
        raise BundleError(
            f"run manifest study must be {STUDY_SLUG!r}, got {manifest.get('study')!r}"
        )
    status = manifest.get("status")
    if status not in _VALID_STATUSES:
        raise BundleError(
            f"run manifest status must be one of {_VALID_STATUSES}, got {status!r}"
        )

    # MINOR 2 fix-wave3: study_commit's SHAPE is now genuinely checked, not
    # merely "is a string" -- previously ANY string (including a hand-typed
    # placeholder) passed here and was then emitted by bundle_ledger_cells as
    # a "verified" ledger cell, refusing a human who supplied the truthful
    # value instead. A well-formed value is either a genuine 40-hex git
    # commit or the ABORTED-only UNAVAILABLE:<non-empty reason> marker (the
    # COMPLETED-specific check just below additionally refuses the marker
    # form for a COMPLETED manifest). This is shape validation, not full
    # re-derivation: verify_bundle does not re-run `git rev-parse HEAD`
    # against a live repo (a manifest legitimately outlives the commit it was
    # built against), so a well-SHAPED but wrong 40-hex value is not caught
    # here -- see docs/owner-decisions-pending.md item 6 for this residue.
    study_commit_value = manifest.get("study_commit")
    if not isinstance(study_commit_value, str) or not (
        _FULL_COMMIT_PATTERN.fullmatch(study_commit_value)
        or (
            study_commit_value.startswith(UNAVAILABLE_COMMIT_PREFIX)
            and len(study_commit_value) > len(UNAVAILABLE_COMMIT_PREFIX)
        )
    ):
        raise BundleError(
            f"run manifest study_commit must be a 40-hex git commit or an "
            f"{UNAVAILABLE_COMMIT_PREFIX!r}-prefixed marker with a non-empty reason, got "
            f"{study_commit_value!r} (MINOR 2 fix-wave3: this ledger cell is machine-"
            "checked, not merely asserted)"
        )

    # MINOR 2 fix-wave3: `scorers` is now bound to something real -- every
    # registered scorer name (SCORERS.names()), never an arbitrary/garbage
    # list. This does NOT re-derive the set from the composed config (that
    # would require repo_root + real config-fragment files verify_bundle has
    # no access to; see docs/owner-decisions-pending.md item 6 for exactly
    # what remains unbound: a manifest whose scorers were legitimately
    # trimmed to omit the task metric, e.g. ["cost"] alone, still verifies).
    result_kind = manifest.get("result_kind", "task-answer")
    artifact_result = manifest.get("artifact_result")
    scorer_names_value = manifest.get("scorers")
    if result_kind == "artifact":
        if not isinstance(artifact_result, Mapping):
            raise BundleError(
                "artifact result manifest requires an exact artifact_result binding"
            )
        legacy = (
            artifact_result.get("schema") == "saea-artifact-result-binding-v1"
            and artifact_result.get("role") == "training-feedback-proposal"
            and set(artifact_result) == {"schema", "role", "construction_roster"}
        )
        hypotheses = (
            artifact_result.get("schema") == "saea-artifact-result-binding-v2"
            and artifact_result.get("role") == "slurp-intent-hypotheses"
            and set(artifact_result)
            == {"schema", "role", "source_roster", "content_contract"}
        )
        typed_proposals = (
            artifact_result.get("schema") == "saea-artifact-result-binding-v3"
            and artifact_result.get("role") == "training-feedback-proposal"
            and set(artifact_result)
            == {"schema", "role", "construction_roster", "content_contract"}
        )
        if not legacy and not hypotheses and not typed_proposals:
            raise BundleError("artifact_result schema or proposal role is invalid")
        roster = artifact_result.get(
            "construction_roster" if legacy or typed_proposals else "source_roster"
        )
        if not isinstance(roster, Mapping) or set(roster) != {"repo_relpath", "sha256"}:
            raise BundleError("artifact_result construction_roster pin is invalid")
        relpath, digest = roster.get("repo_relpath"), roster.get("sha256")
        if (
            not isinstance(relpath, str)
            or not relpath
            or "\\" in relpath
            or ":" in relpath
            or any(part in {"", ".", ".."} for part in relpath.split("/"))
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise BundleError("artifact_result construction_roster pin is invalid")
        if scorer_names_value != []:
            raise BundleError("artifact result manifest requires empty scorers")
    elif result_kind == "task-answer":
        if artifact_result is not None:
            raise BundleError(
                "artifact_result is valid only for artifact result manifests"
            )
        if (
            not isinstance(scorer_names_value, list)
            or not scorer_names_value
            or not all(
                isinstance(name, str) and name.strip() for name in scorer_names_value
            )
        ):
            raise BundleError(
                "run manifest scorers must be a non-empty list of non-empty scorer names, got "
                f"{scorer_names_value!r}"
            )
    else:
        raise BundleError("run manifest result_kind must be task-answer or artifact")
    unregistered_scorers = sorted(set(scorer_names_value) - set(SCORERS.names()))
    if unregistered_scorers:
        raise BundleError(
            f"run manifest scorers names unregistered scorer(s) {unregistered_scorers}; a "
            "manifest cannot claim a scorer core.scorers never registered (MINOR 2 fix-wave3)"
        )

    if status == STATUS_COMPLETED:
        for label, key in (
            ("outputs", "outputs"),
            ("raw trace", "raw_trace"),
            ("trace manifest", "trace_manifest"),
        ):
            entry = manifest.get(key)
            if not isinstance(entry, Mapping) or not entry.get("path"):
                raise BundleError(
                    f"run manifest status is COMPLETED but lacks a usable {label} entry"
                )
        # T6 fix-2 round: a COMPLETED manifest may never carry the
        # ABORTED-only "commit unavailable" marker (see
        # _resolve_study_commit) -- structurally build_manifest never
        # produces this combination itself, but this is checked here too,
        # independently, as defense in depth against a hand-tampered
        # manifest that flips status to COMPLETED while leaving a stale
        # UNAVAILABLE study_commit behind.
        study_commit = manifest.get("study_commit")
        if isinstance(study_commit, str) and study_commit.startswith(
            UNAVAILABLE_COMMIT_PREFIX
        ):
            raise BundleError(
                "run manifest status is COMPLETED but study_commit carries the ABORTED-only "
                f"{UNAVAILABLE_COMMIT_PREFIX!r} marker; a COMPLETED record must always bind a "
                "real, clean study commit"
            )

    return status
