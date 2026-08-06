"""Atomic run bundle: manifest build + verify + finalize (R0 repair T6, invariant I7).

Reproduced defect (task-6 brief): scoring reads only ``carrier_lock_key``/
``sample_id``/``text`` from each outputs row -- a row whose ``text`` was
mutated while keeping its old ``response_sha256`` scores normally. Nothing
checks that the outputs sample set equals the frozen split, that request ids
appear in the trace, or that the trace manifest matches the raw trace.
``core.tracking.log_run`` uploads only outputs + trace manifest (never the raw
trace, never a score artifact), and ``core.base.RunResult`` carries no
outputs/scores hash. There is no single verifiable transaction binding
run -> artifacts -> scores -> ledger row.

This module is that transaction. One attempt produces exactly one
``run-manifest.json`` (schema ``saea-run-manifest-v1``) binding: the study
commit (read from git, fail-closed for a COMPLETED manifest if the tree is
dirty or the commit cannot be read -- see :func:`_study_commit`; an ABORTED
manifest tolerates this instead, see :func:`_resolve_study_commit`), the four
config fragment names + config_hash, the protocol hash, the FULL
:class:`~..contracts.ExecutionPlan` (including ``attempt_id``), the exposure
run id, the split name/role/identity_hash/ids, the session receipt
path+sha256 (when the profile touches the model), the outputs/raw-trace/
trace-manifest/scores path+sha256, the actual cost, and a terminal status
(``COMPLETED``/``ABORTED``) with a failure reason when aborted.

:func:`verify_bundle` re-derives every hash from bytes on disk -- never trusts
the manifest's own numbers -- and cross-checks: every outputs row's
``response_text_sha256`` against a fresh ``sha256(text)`` (the adapter-side
fix in ``core.model.CoreResponse``, see its docstring for why the raw
``response_sha256`` alone is not strictly re-derivable from ``text`` after the
fact); the outputs sample-id set against the frozen split's ids (no missing,
extra, or duplicate); every outputs ``request_id`` against the raw trace's
record ids; and the trace manifest's per-record hashes against records
re-hashed straight from the raw trace file. The attempt's OWN durable state
file (``core.attempts.AttemptHandle``) is re-read fresh, never trusted from
the manifest's self-reported ``status`` -- this is what makes "finalize an
ABORTED attempt as COMPLETED" fail even if the manifest's ``status`` field is
hand-edited afterward.

R0 repair I-1 (external-threat-model review, closing a gap the T6 round left
open): the manifest's own IDENTITY block -- ``split``/``plan``/
``protocol_hash``/``arm`` -- is now likewise RE-DERIVED, not merely read as
an asserted dict. ``split.identity_hash`` is recomputed from ``split.ids``
via the exact carrier-prefix-then-hash convention ``data.splits`` itself
uses; ``split.count`` must equal ``len(split.ids)``; the ``plan`` block is
reconstructed into a genuine :class:`~..contracts.ExecutionPlan` and
re-validated (transitively refusing a paper-scale ``execution_profile``, a
``confirmatory`` ``split_role``, or a non-finite/non-positive planned budget
field -- a hand-edited plan cannot smuggle these past a naive dict read the
way it previously could; a planned budget value alone is no longer capped,
per the 2026-08-06 owner amendment retiring the first-slice numeric caps);
``protocol_hash`` is recomputed from
``config.config_hash``/``arm``/the freshly-verified split identity hash via
``core.config.protocol_hash``, the exact convention
``core.driver.run_experiment`` itself checks before ever sending a request;
and ``cost.calls_used`` is checked against a lower bound derived from the
verified outputs row count. Before this, a COMPLETED dev-split bundle could
be relabelled to a different (e.g. confirmatory) sample-id set while leaving
its ``split.identity_hash``/``protocol_hash`` at their original, now-stale
values, and ``verify_bundle`` had no check that would ever notice.

:func:`finalize_bundle` is the only path that transitions an attempt to
FINALIZED: verify -> run the manifest's configured scorers (via
``core.scorers.score_bundle``, which refuses anything but a genuine
:class:`VerifiedBundle`) -> write a scores artifact -> attach it to the
manifest -> re-verify -> (stubbable) MLflow upload -> a machine-derived
ledger row (``core.tracking.ledger_row_for_bundle``, which refuses any
hand-supplied cell that contradicts the verified manifest) -> mark the
attempt FINALIZED.

ACCEPTED SCOPE BOUNDARY (state this bluntly; do not let a reader over-trust
this module): everything above is a CONSISTENCY check over files on disk, not
an AUTHENTICITY check that those files were ever genuinely produced by the
frozen model. An attacker (or a bug) with plain filesystem write access to a
run's ``run_dir`` -- the same access level a legitimate run already needs to
create outputs/trace files in the first place -- can synthesize a FULLY
SELF-CONSISTENT bundle from scratch: real split ids, self-matching
``response_sha256``/``response_text_sha256`` pairs, a raw trace whose records
hash-agree with a hand-built trace manifest, all outer artifact hashes
correct. ``finalize_bundle`` accepts such a bundle end to end, because
``response_sha256`` hashes the raw transport bytes, and those bytes are never
independently persisted anywhere outside files the same writer controls --
there is no external, write-once anchor proving a response actually crossed
the ``LlamaServerTransport``/``SessionReceipt`` boundary (I5) rather than
being typed into ``outputs.jsonl`` by hand. The external anchors this module
DOES provide -- a real clean git commit (proves what CODE would have run, not
that it did); the split/plan/protocol_hash identity block, since I-1
INDEPENDENTLY RE-DERIVED rather than merely asserted -- the CLAIMED
sample-id set is now proven internally self-consistent with its own
identity_hash, and the plan proven a genuine, Stage-2-legal
``ExecutionPlan``, neither of which was true before I-1 (a hand-relabelled
``split.ids`` with a stale, un-recomputed ``identity_hash`` previously
verified regardless). This re-derivation still does NOT prove that
``split.ids`` names the CURRENT frozen dev/discovery split recorded in the
committed ``docs/receipts/splits.json`` -- that binding is made only once,
at manifest BUILD time, by ``core.split_receipt.load_verified_split`` (the
live carrier-loader recomputation ``core.driver.run_experiment_bundled``
calls before a request is ever sent); ``verify_bundle`` takes only a
manifest path, not a repo root, and never re-reads that receipt, so a
manifest handed to it in isolation -- long after the receipt may have
legitimately moved on -- proves internal self-consistency and Stage-2
legality, never membership in the CURRENT frozen split, and never that
responses were genuinely produced by the frozen model at all; and the
``core.attempts`` state-machine transition (a genuine one-time gate only if
the attacker lacks write access to ``SPEECHRL_DATA_DIR/attempts/`` too, which
an attacker with run_dir access under the same controlled data root very
plausibly also has) -- do not close this gap. Closing it would require a
genuinely separate, append-only/immutable transport log written independently
of anything the same writer later controls, or a remote/signed attestation
anchor outside the local filesystem; both are out of scope for R0's local,
single-machine, single-operator trust model and are not attempted here. I7
should be read as "the recorded artifacts stayed internally coherent from
when they were written to when they were finalized," not "these are proven
genuine model outputs."

R0 repair refactor stage 1 (behaviour-preserving): this used to be one
~1400-line ``bundle.py`` module. It is now this package (``manifest.py`` for
build, ``verify.py`` for verify_bundle, ``finalize.py`` for finalize_bundle +
abort_attempt_if_opened, shared constants/errors/path-confinement helpers
here) purely for file size -- every name below was already part of this
module's public surface and remains importable from exactly
``speech_aware_evidence_acquisition.core.bundle`` as before.
"""

from __future__ import annotations

import re
from pathlib import Path

from ...e0.artifacts import REPO_ROOT

RUN_MANIFEST_SCHEMA = "saea-run-manifest-v1"
STATUS_COMPLETED = "COMPLETED"
STATUS_ABORTED = "ABORTED"
_VALID_STATUSES = (STATUS_COMPLETED, STATUS_ABORTED)

# T6 fix-2 round: an ABORTED manifest's study_commit sentinel when git itself
# could not be read (dirty tree, unreadable repo). See _resolve_study_commit
# and require_clean_study_repo's docstring for why this exists and why it is
# structurally impossible for a COMPLETED manifest (verify_bundle also
# refuses to accept one that claims otherwise -- defense in depth against a
# hand-tampered manifest).
UNAVAILABLE_COMMIT_PREFIX = "UNAVAILABLE:"

# MINOR 2 fix-wave3 (external-threat-model review round 3): shape patterns so
# verify_bundle can genuinely CHECK, not merely assert, the two hash-shaped
# manifest cells bundle_ledger_cells/ledger_row_for_bundle treat as
# machine-derived (docs/owner-decisions-pending.md item 6 records exactly
# what remains a residue after this).
_FULL_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")

# VerifiedBundle.attempt_state sentinel for "no attempt file exists at all"
# (a failure before FrozenCoreAdapter ever opened one) -- distinct from every
# real core.attempts state (RESERVED/OPENED/FINALIZED/ABORTED), but like all
# of those except OPENED, never eligible for finalize_bundle to proceed.
ATTEMPT_STATE_NEVER_OPENED = "NEVER_OPENED"


class BundleError(RuntimeError):
    """A run manifest cannot be built, or a bundle fails verification/finalization."""


# ---------------------------------------------------------------------------
# Repo confinement (IMPORTANT fix, T6 fix round): no bundle artifact --
# manifest, scores, or ledger row -- may ever be written INSIDE the study
# repository. ``core.tracing.TraceSink`` already refuses an in-repo run_dir
# for outputs/trace files; the ORIGINAL build_manifest/finalize_bundle never
# re-checked this independently, so an aborted-run manifest (which does not
# go through TraceSink at all -- it is written directly by write_json_artifact)
# could land inside the checkout. Fixed here as an independent rail, mirroring
# the two-rail discipline T3 established for I3/I4 (adapter AND transport each
# check media confinement on their own authority, never trusting the other).
# ---------------------------------------------------------------------------


def _refuse_if_inside_repo(path: Path, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise BundleError(
            f"{label} {resolved} is inside the study repository ({REPO_ROOT}); run bundle "
            "artifacts (manifest, scores, ledger rows) are NEVER written into the repository "
            "(study contract) -- use a run_dir under SPEECHRL_DATA_DIR or another location "
            "outside the repository checkout"
        )
    return resolved


# IMPORTANT 3 (external-threat-model review round 3): every manifest/scores/
# ledger path this module writes embeds ``run_id`` (plain f-string
# interpolation) with NOTHING confining the result to stay inside its own run
# directory. ``contracts.ExecutionPlan.validate`` now refuses a run_id/
# attempt_id containing a path separator or traversal segment (fix-wave3) --
# but that refusal is not guaranteed to have run on a PARTICULAR plan object
# before it reaches this module: ``core.driver.run_experiment_bundled``'s own
# ABORTED-manifest path calls ``build_manifest`` with the SAME plan whenever
# ``run_experiment`` fails for ANY reason, including ``core.tracing.
# TraceSink``'s OWN (unrelated) run_id format check raising FIRST -- before
# the gate/adapter construction that would otherwise be the first thing to
# call ``plan.validate()``. Demonstrated: a plan built directly from an
# operator-supplied JSON file (``core.driver._cli_run``, never itself calling
# ``.validate()``) with ``run_id="../../VICTIM/pwned"`` reached
# ``build_manifest`` this way and wrote a manifest OUTSIDE its run directory.
# This confinement is therefore a second, independent rail -- mirroring this
# module's own I3/I4 two-rail precedent elsewhere (adapter AND transport each
# independently check media/payload confinement, never trusting the other)
# -- that holds regardless of whether ``ExecutionPlan.validate()`` ever ran
# on the plan that produced ``filename``.
def _confine_child_path(parent_dir: Path, filename: str, label: str) -> Path:
    """``parent_dir / filename``, refused (:class:`BundleError`) unless the
    resolved result is BOTH a direct child of ``parent_dir`` and outside the
    study repository. ``filename`` is expected to embed a run_id/attempt_id
    verbatim (e.g. ``f"{run_id}.run-manifest.json"``) -- a value containing
    ``/``, ``\\``, or a ``..`` segment resolves outside ``parent_dir`` and is
    refused here rather than silently written wherever it lands."""

    parent_resolved = Path(parent_dir).resolve()
    resolved = (parent_resolved / filename).resolve()
    if resolved.parent != parent_resolved:
        raise BundleError(
            f"{label} {resolved} would not land directly inside its own run directory "
            f"{parent_resolved}; refused -- a run_id/attempt_id can never steer an "
            "artifact path outside where it belongs (IMPORTANT 3 fix-wave3)"
        )
    return _refuse_if_inside_repo(resolved, label)


from .verify import VerifiedBundle, verify_bundle  # noqa: E402
from .manifest import build_manifest, require_clean_study_repo  # noqa: E402
from .finalize import FinalizeResult, abort_attempt_if_opened, finalize_bundle  # noqa: E402

__all__ = [
    "ATTEMPT_STATE_NEVER_OPENED",
    "RUN_MANIFEST_SCHEMA",
    "STATUS_ABORTED",
    "STATUS_COMPLETED",
    "UNAVAILABLE_COMMIT_PREFIX",
    "BundleError",
    "FinalizeResult",
    "VerifiedBundle",
    "abort_attempt_if_opened",
    "build_manifest",
    "finalize_bundle",
    "require_clean_study_repo",
    "verify_bundle",
]
