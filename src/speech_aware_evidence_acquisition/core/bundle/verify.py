"""Bundle verification: recompute every hash from bytes on disk; trust nothing else.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). R0 repair refactor stage 2 (part C):
the manifest-header checks (schema/study/status, ``study_commit`` shape,
``scorers`` shape+registration, COMPLETED-only presence/marker refusals)
moved to ``verify_header.py``'s ``_verify_manifest_header``, again purely for
file size and again a pure move -- it only ever reads ``manifest`` and
returns the validated ``status``, feeding nothing else back into this module.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan, ExecutionScopeError
from ...data.splits import prefixed as _prefixed_ids, split_identity_hash
from ..attempts import AttemptError, AttemptHandle
from ..config import protocol_hash as _recompute_protocol_hash
from . import _SHA256_PATTERN, ATTEMPT_STATE_NEVER_OPENED, BundleError
from .artifacts import VerifiedBundle, _read_bytes, _verify_artifact
from .outputs import (
    _minimum_model_calls_from_trace,
    _verify_outputs,
    _verify_outputs_trace_binding,
    _verify_raw_trace,
    verify_predecessor_attempts,
)
from .verify_header import _verify_manifest_header


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
    from .delivery import DELIVERY_MANIFEST_SCHEMA, verify_delivery_bundle

    if manifest.get("schema") == DELIVERY_MANIFEST_SCHEMA:
        return verify_delivery_bundle(manifest_path, manifest)
    from .hypothesis_source import PREPARATION_KIND, verify_hypothesis_source

    if (
        manifest.get("schema") == "saea-prepared-artifact-v1"
        and manifest.get("kind") == PREPARATION_KIND
    ):
        return verify_hypothesis_source(manifest_path)
    _verify_manifest_header(manifest)

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
    artifact_content_source_raw = _verify_artifact(
        manifest.get("artifact_content_source"), "artifact content source"
    )

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
    artifact_result = manifest.get("artifact_result")
    if (
        isinstance(artifact_result, Mapping)
        and artifact_result.get("schema") in {
            "saea-artifact-result-binding-v2",
            "saea-artifact-result-binding-v3",
        }
    ):
        from ..base import ARTIFACT_CONTENT_VALIDATORS, CoreError
        from ...rails.artifact_results import register_artifact_content_v1
        from ...rails.training_feedback_artifacts import (
            TrainingFeedbackArtifactError,
            artifact_content_source_pin,
        )

        source_meta = manifest.get("artifact_content_source")
        contract = artifact_result.get("content_contract")
        try:
            source_pin = artifact_content_source_pin(contract)
        except (AttributeError, TrainingFeedbackArtifactError) as error:
            raise BundleError(f"typed artifact content is invalid: {error}") from error
        if (
            artifact_content_source_raw is None
            or not isinstance(source_meta, Mapping)
            or not isinstance(source_meta.get("path"), str)
            or not isinstance(source_pin, Mapping)
            or not isinstance(source_pin.get("data_relpath"), str)
        ):
            raise BundleError("typed artifact bundle lacks its content source artifact")
        try:
            register_artifact_content_v1()
            source_path = Path(source_meta["path"]).resolve()
            data_root = source_path
            for _part in source_pin["data_relpath"].split("/"):
                data_root = data_root.parent
            if (data_root / source_pin["data_relpath"]).resolve() != source_path:
                raise BundleError("typed artifact content source path is not canonical")
            factory = ARTIFACT_CONTENT_VALIDATORS.resolve(str(contract.get("id")))
            validator = factory(contract, data_root=data_root)
            for row in outputs_rows:
                canonical = validator.canonicalize(
                    row["text"], sample_id=str(row["sample_id"])
                )
                if (
                    row.get("artifact_role") != artifact_result.get("role")
                    or row.get("artifact_content") != canonical
                    or row.get("artifact_content_sha256")
                    != hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    or row.get("artifact_source_sha256") != validator.source_sha256
                ):
                    raise BundleError(
                        "typed artifact output differs from its registered canonical content"
                    )
        except (KeyError, IndexError, CoreError, ValueError) as error:
            if isinstance(error, BundleError):
                raise
            raise BundleError(f"typed artifact content is invalid: {error}") from error
    trace_records = _verify_raw_trace(raw_trace_raw, trace_manifest_raw)
    # E10 (owner decision 22, 2026-09-18): a resume-recovery's manifest
    # declares the aborted attempt whose COMPLETE rows it kept. The
    # predecessor trace is re-hashed against the declared sha256 and the
    # kept-row list against its own declared hash, exactly as every other
    # number in this function is re-derived rather than believed; a manifest
    # that declares none keeps byte-identical behaviour.
    attempt_binding = manifest.get("attempt")
    predecessor_records, kept_sample_ids = verify_predecessor_attempts(
        manifest,
        split_ids=split_ids,
        attempt_id=(
            attempt_binding.get("attempt_id")
            if isinstance(attempt_binding, Mapping)
            else None
        ),
    )
    _verify_outputs_trace_binding(
        outputs_rows,
        trace_records,
        predecessor_records=predecessor_records if kept_sample_ids else None,
        kept_sample_ids=kept_sample_ids,
    )
    # Owner decision 309 (2026-10-14): an attempt that made its rows durable
    # pins its row checkpoint in the manifest. The file is re-hashed, its chain
    # re-verified, and every COMPLETE row's stored canonical record must equal
    # the sealed outputs row of the same sample byte for byte. A manifest
    # without the block (every manifest sealed before this change) is unchanged.
    row_checkpoint_block = manifest.get("row_checkpoint")
    if row_checkpoint_block is not None:
        from ..row_checkpoint import RowCheckpointError, verify_manifest_block

        try:
            verify_manifest_block(row_checkpoint_block, outputs_rows)
        except RowCheckpointError as error:
            raise BundleError(f"row_checkpoint: {error}") from error

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

    # I-1 fix, extended for deterministic derived composites: cost.calls_used
    # is lower-bounded by MODEL REQUESTS freshly derived from the verified
    # trace, not blindly by output-row count. A direct run still has one
    # model request per output. A complete composite can additionally bind a
    # row to a deterministic TOOL request whose source is either a model
    # response in the same trace or immutable source bytes re-hashed by
    # _minimum_model_calls_from_trace. This preserves honest current-attempt
    # accounting when frozen M0 rows are reused. A retrying policy can only
    # require more calls than this floor. An ABORTED bundle (empty
    # outputs_rows) is NOT checked here: with zero verified outputs rows
    # there is nothing to derive a bound from, so
    # ``core.bundle._best_effort_cost_for_aborted_attempt``'s own read of
    # the durable attempt store is honestly NOT independently re-derivable
    # from bundle artifacts the way this check needs -- see that function's
    # docstring.
    cost = manifest.get("cost")
    if outputs_rows and isinstance(cost, Mapping):
        calls_used = cost.get("calls_used")
        minimum_model_calls = _minimum_model_calls_from_trace(
            trace_records,
            output_request_ids=frozenset(str(row["request_id"]) for row in outputs_rows),
        )
        if (
            isinstance(calls_used, (int, float))
            and not isinstance(calls_used, bool)
            and calls_used < minimum_model_calls
        ):
            raise BundleError(
                f"run manifest cost.calls_used={calls_used!r} is less than the "
                f"{minimum_model_calls} verified model requests in its trace (I-1)"
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
