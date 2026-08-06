"""Bundle verification: recompute every hash from bytes on disk; trust nothing else.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ...contracts import STUDY_SLUG, ExecutionPlan, ExecutionScopeError
from ...data.splits import prefixed as _prefixed_ids, split_identity_hash
from ..attempts import AttemptError, AttemptHandle
from ..base import SCORERS
from ..config import protocol_hash as _recompute_protocol_hash
from . import (
    RUN_MANIFEST_SCHEMA,
    STATUS_COMPLETED,
    UNAVAILABLE_COMMIT_PREFIX,
    _FULL_COMMIT_PATTERN,
    _SHA256_PATTERN,
    _VALID_STATUSES,
    ATTEMPT_STATE_NEVER_OPENED,
    BundleError,
)
from .artifacts import VerifiedBundle, _read_bytes, _verify_artifact
from .outputs import _verify_outputs, _verify_outputs_trace_binding, _verify_raw_trace


def verify_bundle(manifest_path: Path) -> VerifiedBundle:
    """Recompute every hash the manifest names from the bytes actually on
    disk right now, and cross-check outputs<->split<->trace. Never trusts a
    single number the manifest merely asserts about itself."""

    manifest_path = Path(manifest_path)
    manifest_bytes = _read_bytes(manifest_path, "run manifest")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"run manifest {manifest_path} is not valid JSON: {error}") from error
    if not isinstance(manifest, Mapping):
        raise BundleError(f"run manifest {manifest_path} must be a JSON object")
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
        raise BundleError(f"run manifest status must be one of {_VALID_STATUSES}, got {status!r}")

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
    scorer_names_value = manifest.get("scorers")
    if (
        not isinstance(scorer_names_value, list)
        or not scorer_names_value
        or not all(isinstance(name, str) and name.strip() for name in scorer_names_value)
    ):
        raise BundleError(
            "run manifest scorers must be a non-empty list of non-empty scorer names, got "
            f"{scorer_names_value!r}"
        )
    unregistered_scorers = sorted(set(scorer_names_value) - set(SCORERS.names()))
    if unregistered_scorers:
        raise BundleError(
            f"run manifest scorers names unregistered scorer(s) {unregistered_scorers}; a "
            "manifest cannot claim a scorer core.scorers never registered (MINOR 2 fix-wave3)"
        )

    if status == STATUS_COMPLETED:
        for label, key in (("outputs", "outputs"), ("raw trace", "raw_trace"), ("trace manifest", "trace_manifest")):
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
        if isinstance(study_commit, str) and study_commit.startswith(UNAVAILABLE_COMMIT_PREFIX):
            raise BundleError(
                "run manifest status is COMPLETED but study_commit carries the ABORTED-only "
                f"{UNAVAILABLE_COMMIT_PREFIX!r} marker; a COMPLETED record must always bind a "
                "real, clean study commit"
            )

    # Minor hardening (round-2 external-threat-model review): every artifact
    # this module itself ever writes -- outputs/raw_trace/trace_manifest/
    # scores -- always lands directly in the manifest's own run directory
    # (see core.driver.run_experiment and finalize_bundle). Confine each to
    # there at verify time too, not merely at write time, so a manifest
    # cannot bind another run's outputs (or an arbitrary filesystem path) by
    # simply naming it with a correct hash. session_receipt is deliberately
    # excluded -- see _verify_artifact's own docstring for why.
    run_dir_resolved = manifest_path.resolve().parent
    outputs_raw = _verify_artifact(manifest.get("outputs"), "outputs", confine_to=run_dir_resolved)
    raw_trace_raw = _verify_artifact(
        manifest.get("raw_trace"), "raw trace", confine_to=run_dir_resolved
    )
    trace_manifest_raw = _verify_artifact(
        manifest.get("trace_manifest"), "trace manifest", confine_to=run_dir_resolved
    )
    _verify_artifact(manifest.get("scores"), "scores", confine_to=run_dir_resolved)
    _verify_artifact(manifest.get("session_receipt"), "session receipt")

    # ------------------------------------------------------------------
    # I-1 fix: the split block's own identity is RE-DERIVED, never merely
    # asserted. Before this, ``split["ids"]`` was treated as truth with no
    # check that ``split["identity_hash"]`` actually described it -- a
    # manifest could be hand-relabelled to a different sample-id set while
    # leaving the (now-stale) identity_hash untouched, and verify_bundle had
    # no way to notice. ``split["ids"]`` stores BARE sample ids (matching
    # outputs rows' own ``sample_id`` field, cross-checked below) -- the
    # SAME convention ``core.split_receipt.VerifiedSplit.ids`` uses -- so the
    # hash recompute must first carrier-prefix them via
    # ``data.splits.prefixed`` before hashing, exactly mirroring
    # ``data.splits._spec``'s own construction of a genuine split's
    # identity_hash.
    # ------------------------------------------------------------------
    split = manifest.get("split")
    if not isinstance(split, Mapping):
        raise BundleError("run manifest lacks a usable split block")
    raw_ids = split.get("ids")
    if not isinstance(raw_ids, list) or not raw_ids or not all(
        isinstance(sample_id, str) and sample_id for sample_id in raw_ids
    ):
        raise BundleError("run manifest split.ids must be a non-empty list of strings")
    if len(set(raw_ids)) != len(raw_ids):
        raise BundleError("run manifest split.ids contains a duplicate id (I-1)")
    if raw_ids != sorted(raw_ids):
        raise BundleError("run manifest split.ids must be sorted (I-1)")
    declared_count = split.get("count")
    if declared_count != len(raw_ids):
        raise BundleError(
            f"run manifest split.count {declared_count!r} does not match "
            f"len(split.ids) {len(raw_ids)} (I-1)"
        )
    split_carrier_lock_key = split.get("carrier_lock_key")
    if not isinstance(split_carrier_lock_key, str) or not split_carrier_lock_key.strip():
        raise BundleError("run manifest split.carrier_lock_key must be a non-empty string")
    recomputed_split_identity = split_identity_hash(_prefixed_ids(split_carrier_lock_key, raw_ids))
    declared_split_identity = split.get("identity_hash")
    if recomputed_split_identity != declared_split_identity:
        raise BundleError(
            "run manifest split.identity_hash does not match a fresh recomputation "
            f"from split.ids under carrier_lock_key {split_carrier_lock_key!r} (I-1): "
            f"declared {str(declared_split_identity)[:12]}..., recomputed "
            f"{recomputed_split_identity[:12]}..."
        )
    split_ids = frozenset(raw_ids)

    # I7 round-2 (IMPORTANT fix): the manifest's own 'arm' field is validated
    # HERE -- moved up from its former position further below, where it fed
    # only the protocol_hash recompute -- so it, alongside the verified split
    # carrier, can bind each outputs row before that row is ever accepted.
    # See _verify_outputs's own comment for exactly what this closes.
    arm = manifest.get("arm")
    if not isinstance(arm, str) or not arm.strip():
        raise BundleError("run manifest lacks a usable 'arm' field (I-1)")

    outputs_rows = _verify_outputs(outputs_raw, split_ids, split_carrier_lock_key, arm)
    trace_records = _verify_raw_trace(raw_trace_raw, trace_manifest_raw)
    _verify_outputs_trace_binding(outputs_rows, trace_records)

    # ------------------------------------------------------------------
    # I-1 fix: the plan block is RE-VALIDATED as a genuine
    # ``contracts.ExecutionPlan``, never merely read as an inert dict. This
    # transitively refuses (``ExecutionScopeError`` -> ``BundleError``):
    # a paper-scale ``execution_profile`` (the exact value
    # ``contracts.assert_execution_scope`` exists to refuse -- including
    # ``paper-scale-confirmatory``), a ``split_role`` of ``confirmatory``,
    # an unknown Stage-2 split role, a malformed schema/study identity, and
    # a non-finite/non-positive/non-integral ``planned_model_calls`` /
    # ``planned_gpu_hours`` / ``planned_speech_audio_seconds``. It no longer
    # refuses a large planned budget value on its own (e.g. a
    # ``planned_model_calls`` of 999999) -- the first-slice numeric caps
    # ``ExecutionPlan.validate()`` used to enforce here were retired by the
    # 2026-08-06 owner amendment (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS).
    # ------------------------------------------------------------------
    plan_meta = manifest.get("plan")
    if not isinstance(plan_meta, Mapping):
        raise BundleError("run manifest lacks a usable plan block")
    try:
        reconstructed_plan = ExecutionPlan(**plan_meta)
    except TypeError as error:
        raise BundleError(f"run manifest plan block is malformed: {error}") from error
    try:
        reconstructed_plan.validate()
    except ExecutionScopeError as error:
        raise BundleError(
            f"run manifest plan block fails ExecutionPlan.validate() (I-1): {error}"
        ) from error
    if reconstructed_plan.run_id != manifest.get("run_id"):
        raise BundleError(
            "run manifest plan.run_id does not match the manifest's own run_id (I-1)"
        )
    if reconstructed_plan.carrier_lock_key != split_carrier_lock_key:
        raise BundleError(
            "run manifest plan.carrier_lock_key does not match split.carrier_lock_key (I-1)"
        )
    if reconstructed_plan.split_role != split.get("role"):
        raise BundleError(
            "run manifest plan.split_role does not match split.role (I-1)"
        )
    if reconstructed_plan.split_identity_hash != recomputed_split_identity:
        raise BundleError(
            "run manifest plan.split_identity_hash does not match the freshly "
            "recomputed split identity hash (I-1)"
        )

    # I-1 fix: protocol_hash is RE-DERIVED from (config.config_hash, arm, the
    # freshly-recomputed split identity hash) via the exact same
    # core.config.protocol_hash convention core.driver.run_experiment itself
    # checks before ever sending a request -- never merely trusted as a
    # manifest-asserted number. This is what actually defeats a manifest
    # whose split.ids/identity_hash were correctly recomputed TOGETHER for a
    # sample set the protocol_hash was never actually minted against: the
    # stale protocol_hash (still describing the ORIGINAL split) disagrees
    # with this recomputation and refuses.
    # 'arm' was already extracted and validated above (before _verify_outputs
    # was called, so it could bind each outputs row too).
    # MINOR 2 fix-wave3: config_hash's SHAPE is now checked (a genuine
    # 64-hex SHA-256), not merely "is a string" -- any self-consistent-
    # LOOKING pair (an arbitrary string paired with fragment names that
    # happen to also be arbitrary) previously passed here outright.
    # config_hash is NOT re-derived from the named fragments' actual file
    # contents: doing so needs repo_root plus the real config-fragment
    # files on disk, which verify_bundle (taking only a manifest path) has
    # no access to -- see docs/owner-decisions-pending.md item 6 for this
    # residue, stated plainly rather than silently narrowed.
    config_meta = manifest.get("config")
    if not isinstance(config_meta, Mapping) or not isinstance(config_meta.get("config_hash"), str):
        raise BundleError("run manifest lacks a usable config.config_hash")
    if _SHA256_PATTERN.fullmatch(config_meta["config_hash"]) is None:
        raise BundleError(
            f"run manifest config.config_hash must be a 64-hex SHA-256, got "
            f"{config_meta['config_hash']!r} (MINOR 2 fix-wave3)"
        )
    recomputed_protocol_hash = _recompute_protocol_hash(
        config_meta["config_hash"], arm, recomputed_split_identity
    )
    declared_protocol_hash = manifest.get("protocol_hash")
    if recomputed_protocol_hash != declared_protocol_hash:
        raise BundleError(
            "run manifest protocol_hash does not recompute from config.config_hash / "
            "arm / the verified split identity hash (I-1)"
        )
    if reconstructed_plan.protocol_hash != declared_protocol_hash:
        raise BundleError(
            "run manifest plan.protocol_hash does not match the manifest's own "
            "protocol_hash (I-1)"
        )

    # I-1 fix: cost.calls_used is derivable, for a COMPLETED bundle with a
    # non-empty VERIFIED outputs set, as a lower bound -- core.model.
    # FrozenCoreAdapter.request durably records a call (core.attempts) BEFORE
    # the transport is ever invoked, so no outputs row can exist without at
    # least one genuinely spent call behind it. Today's only registered
    # policy (FixedPolicy) makes this an exact equality; a future
    # retrying/re-resolving policy (X-series) could only ever need MORE
    # calls than rows, never fewer, so this stays a safe `>=` rather than a
    # strict `==` tied to FixedPolicy's specific shape. An ABORTED bundle
    # (empty outputs_rows) is NOT checked here: with zero verified outputs
    # rows there is nothing to derive a bound from, so
    # ``core.bundle._best_effort_cost_for_aborted_attempt``'s own read of
    # the durable attempt store is honestly NOT independently re-derivable
    # from bundle artifacts the way this check needs -- see that function's
    # docstring.
    cost = manifest.get("cost")
    if outputs_rows and isinstance(cost, Mapping):
        calls_used = cost.get("calls_used")
        if (
            isinstance(calls_used, (int, float))
            and not isinstance(calls_used, bool)
            and calls_used < len(outputs_rows)
        ):
            raise BundleError(
                f"run manifest cost.calls_used={calls_used!r} is less than the "
                f"{len(outputs_rows)} verified outputs rows it must have taken at "
                "least that many calls to produce (I-1)"
            )

    attempt_meta = manifest.get("attempt")
    if not isinstance(attempt_meta, Mapping) or not attempt_meta.get("state_path"):
        raise BundleError("run manifest lacks an attempt.state_path binding")
    if reconstructed_plan.attempt_id != attempt_meta.get("attempt_id"):
        raise BundleError(
            "run manifest plan.attempt_id does not match attempt.attempt_id (I-1)"
        )
    attempt_state_path = Path(str(attempt_meta["state_path"]))
    if not attempt_state_path.is_file():
        # A failure before FrozenCoreAdapter construction ever ran (e.g. a
        # protocol-hash/carrier mismatch caught earlier in run_experiment)
        # leaves no attempt file at all -- distinct from a genuine read/parse
        # failure below. Not OPENED either way, which is all finalize_bundle
        # needs to know to refuse it; not a bundle-integrity error by itself.
        attempt_state = ATTEMPT_STATE_NEVER_OPENED
    else:
        try:
            attempt_state = AttemptHandle(
                path=attempt_state_path,
                run_id=str(attempt_meta.get("run_id", manifest.get("run_id"))),
                attempt_id=str(attempt_meta.get("attempt_id", "")),
            ).state()
        except AttemptError as error:
            raise BundleError(f"cannot read this bundle's attempt state: {error}") from error

    outputs_meta = manifest.get("outputs")
    outputs_path = (
        Path(str(outputs_meta["path"])) if isinstance(outputs_meta, Mapping) else None
    )

    return VerifiedBundle(
        manifest_path=manifest_path,
        manifest=manifest,
        outputs_path=outputs_path,
        outputs_rows=outputs_rows,
        trace_records=trace_records,
        split_ids=split_ids,
        attempt_state=attempt_state,
    )
