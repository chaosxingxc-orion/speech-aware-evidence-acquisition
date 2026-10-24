"""Bundle verification: outputs.jsonl / raw-trace parsing and the outputs<->trace
cross-checks (I7, and for a grouped-Solver row I7g).

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).

E2d (2026-09-17, SLURP v2 base program M2): module M2 lets ONE Solver visit
make N metered contacts and deliver a registered, deterministic COMMIT
policy's aggregate of the N structured answers (``rails.commit_policies``,
``reproduction.ojw.native_group_solver``). The delivered text is then a
deterministic function of the N raw response texts and equals none of them in
general, which I7's "the delivered text IS one model response's bytes"
reading cannot express. I7 is right and stays exactly as it is for every row
WITHOUT a ``solver_group`` receipt. A row WITH one is additionally held to
I7g -- a strictly stronger custody form, not a relaxation: every raw sample's
own response bytes must still be in the trace under that sample's own contact
id, the named commit policy must be registered in
``core.base.COMMIT_POLICIES`` and reproduce itself, and re-running it over the
row's own recorded samples must reproduce the delivered bytes exactly.

E11 (2026-09-18, owner directive 26): the delivery-time normaliser node does
the same thing one step later. A row whose episode ran a registered
``core.base.DELIVERY_NORMALISERS`` entry carries a ``deliver_normaliser``
block inside its ``native_episode_receipt``, and its delivered text is that
rule's output over the accepted answer rather than the accepted answer's own
bytes. I7 is again untouched and still binds the row's ``text`` to its own
``response_text_sha256``; such a row is additionally held to I7n, which is
again strictly stronger custody: the recorded model response for the row's
own request id must be exactly the rule's recorded INPUT, the named rule must
be registered and deterministic, and re-running it over those response bytes
must reproduce the delivered bytes byte for byte.

Item E4 (2026-09-28, owner decision 185): the post-accept targeted relisten
stage is a SHADOW mechanism -- it never mutates the delivered ``text`` --
so I7 is unaffected by its presence. A row whose episode ran it carries a
top-level ``relisten`` receipt (``rails.relisten.seal_relisten_receipt``),
and is additionally held to I7l: every entity's blind (and, when fired,
forced-choice) contact named in that receipt must be a real, traced contact
of the row, and its disposition/vote must re-derive from the trace's own
recorded response text rather than from the receipt's claim alone.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ...contracts import BoundaryViolation, TraceContractError, TraceRecord
from . import BundleError


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _minimum_model_calls_from_trace(
    trace_records: Mapping[str, Mapping[str, object]],
    *,
    output_request_ids: frozenset[str] | None = None,
) -> int:
    """Derive the model-call cost floor while admitting traced tool composites.

    A normal model request carries the transport envelope fields ``arm``,
    ``payload``, and ``payload_sha256``. A deterministic tool-derived output
    instead carries ``tool_id`` and must bind either a model response in the
    same trace or immutable source bytes whose SHA-256 is re-measured here.
    The latter is what lets a complete prediction manifest reuse a frozen M0
    row without pretending that the current attempt made another model call.
    """

    model_requests = 0
    derived_ids = (
        output_request_ids
        if output_request_ids is not None
        else frozenset(
            record_id[: -len("/request")]
            for record_id, payload in trace_records.items()
            if record_id.endswith("/request") and "tool_id" in payload
        )
    )
    for record_id, payload in trace_records.items():
        if not record_id.endswith("/request"):
            continue
        request_id = record_id[: -len("/request")]
        if (
            isinstance(payload.get("arm"), str)
            and isinstance(payload.get("payload"), Mapping)
            and _is_sha256(payload.get("payload_sha256"))
        ):
            model_requests += 1
            continue
        # Legacy OBS roots are output identities too, but their request record is
        # a stitch/observation envelope rather than a model or deterministic-tool
        # request. Only an explicit tool_id opts a non-model request into the
        # derived-output provenance contract.
        if request_id not in derived_ids or "tool_id" not in payload:
            continue
        tool_id = payload.get("tool_id")
        source = payload.get("source")
        if not isinstance(tool_id, str) or not tool_id or not isinstance(source, Mapping):
            raise BundleError(
                f"tool-derived output {request_id!r} lacks bound source provenance"
            )
        source_request_id = source.get("source_request_id")
        if isinstance(source_request_id, str) and source_request_id:
            if f"{source_request_id}/response" not in trace_records:
                raise BundleError(
                    f"tool-derived output {request_id!r} source provenance names "
                    f"missing response {source_request_id!r}"
                )
            continue
        source_path_value = source.get("source_artifact_path")
        source_sha256 = source.get("source_artifact_sha256")
        if not isinstance(source_path_value, str) or not _is_sha256(source_sha256):
            raise BundleError(
                f"tool-derived output {request_id!r} lacks bound source provenance"
            )
        source_path = Path(source_path_value)
        if not source_path.is_absolute() or not source_path.is_file():
            raise BundleError(
                f"tool-derived output {request_id!r} source artifact is unavailable"
            )
        actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual_sha256 != source_sha256:
            raise BundleError(
                f"tool-derived output {request_id!r} source artifact hash drifted"
            )
    return model_requests


#: The invariant code a grouped-Solver custody refusal names, so a failed
#: seal is never confused with I7's single-response identity check.
SOLVER_GROUP_INVARIANT = "I7g"
SUPPLY_VARIANT_INVARIANT = "I7v"

#: E11 (owner directive 26, 2026-09-18): the invariant code a delivery-time
#: normalisation custody refusal names, so it is never confused with I7's
#: single-response identity check or with I7g's grouped-commit re-derivation.
DELIVER_NORMALISER_INVARIANT = "I7n"

#: E10 (owner decision 22, 2026-09-18): the invariant code a resume-recovery
#: custody refusal names. I7 is unchanged and still decides every row; this
#: says only WHICH trace a row is held against.
RESUME_PREDECESSOR_INVARIANT = "I7r"

#: The only ``predecessor_attempt`` block shape a manifest may declare.
#: Restated here rather than imported from ``core.flight.resume`` so bundle
#: verification keeps no runtime import (the same discipline
#: ``rails.native_episode_receipt`` follows).
RESUME_PREDECESSOR_SCHEMA = "saea-resume-predecessor-attempt-v1"

_PREDECESSOR_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "attempt_id",
        "trace_path",
        "trace_sha256",
        "kept_sample_ids",
        "kept_sample_ids_sha256",
        "counts",
    }
)


#: The extra fields of a checkpoint-mode (mode B) block: ``mode`` is the
#: literal ``"checkpoint"``; the path and whole-file sha256 pin the
#: predecessor's ``<run_id>.rows.ckpt.jsonl``, from which ``trace_path`` (a file
#: this resume materialized) is a pure function.
_CHECKPOINT_PREDECESSOR_FIELDS = frozenset({"mode", "checkpoint_path", "checkpoint_sha256"})


def _verify_checkpoint_predecessor(block: Mapping[str, object], raw_trace: bytes) -> None:
    """I7r for mode B: the declared trace is exactly the kept rows' stored
    trace lines, in checkpoint order, from the pinned checkpoint.

    The checkpoint is re-hashed against its declared sha256 and its chain is
    re-verified; every kept sample must be a COMPLETE, arm-complete row of it;
    and the predecessor trace the rows are held against must equal, byte for
    byte, what those rows' stored trace lines concatenate to. So a mode-B kept
    row is held against the bytes its own attempt durably recorded, through the
    same one-trace-per-row check a mode-A row gets.
    """

    from ..row_checkpoint import (  # noqa: PLC0415
        RowCheckpointError, kept_trace_text, read_checkpoint,
    )

    try:
        document = read_checkpoint(
            Path(str(block["checkpoint_path"])),
            expected_sha256=str(block["checkpoint_sha256"]),
        )
    except RowCheckpointError as error:
        raise BundleError(f"{error} ({RESUME_PREDECESSOR_INVARIANT})") from error
    by_sample = document.by_sample()
    kept_rows = []
    for sample_id in block["kept_sample_ids"]:
        row = by_sample.get(sample_id)
        if row is None or not row.keepable:
            raise BundleError(
                f"predecessor_attempt keeps sample {sample_id!r}, which is not a COMPLETE "
                f"row of the pinned checkpoint ({RESUME_PREDECESSOR_INVARIANT})"
            )
        kept_rows.append(row)
    kept_rows.sort(key=lambda row: row.seq)
    if raw_trace != kept_trace_text(kept_rows).encode("utf-8"):
        raise BundleError(
            "predecessor_attempt trace is not the kept rows' stored trace lines from the "
            f"pinned checkpoint ({RESUME_PREDECESSOR_INVARIANT})"
        )


def _kept_sample_ids_sha256(sample_ids: Sequence[str]) -> str:
    """The kept-row list hash, byte for byte as ``core.flight.resume`` mints it."""

    ordered = sorted(str(sample_id) for sample_id in sample_ids)
    return hashlib.sha256(
        json.dumps(ordered, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _validate_predecessor_block(
    block: object, *, run_id: object, attempt_id: object
) -> Mapping[str, object]:
    """Shape and self-consistency of a ``predecessor_attempt`` block.

    Shared by ``core.bundle.manifest.build_manifest`` (refuse before writing)
    and :func:`verify_predecessor_attempt` (refuse before trusting), so the
    two can never drift into disagreeing about what a resumed manifest is.
    """

    # Owner decision 309 (2026-10-14): a block whose rows were kept from a row
    # checkpoint (mode B) carries three more fields. Without ``mode`` the block
    # is the original mode-A shape, byte for byte.
    is_checkpoint = isinstance(block, Mapping) and block.get("mode") == "checkpoint"
    expected_fields = (
        _PREDECESSOR_FIELDS | _CHECKPOINT_PREDECESSOR_FIELDS
        if is_checkpoint else _PREDECESSOR_FIELDS
    )
    if not isinstance(block, Mapping) or set(block) != expected_fields:
        raise BundleError(
            "run manifest predecessor_attempt must be an object with exactly "
            f"{sorted(expected_fields)} ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if is_checkpoint and (
        not isinstance(block.get("checkpoint_path"), str)
        or not block["checkpoint_path"].strip()
        or not _is_sha256(block.get("checkpoint_sha256"))
    ):
        raise BundleError(
            "predecessor_attempt.checkpoint_path / checkpoint_sha256 must be a path and a "
            f"64-hex SHA-256 ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if block.get("schema") != RESUME_PREDECESSOR_SCHEMA:
        raise BundleError(
            f"predecessor_attempt.schema must be {RESUME_PREDECESSOR_SCHEMA!r} "
            f"({RESUME_PREDECESSOR_INVARIANT})"
        )
    if block.get("run_id") != run_id:
        raise BundleError(
            "predecessor_attempt.run_id must be this manifest's own run id -- a "
            "resume-recovery continues ONE run, under a new attempt id "
            f"({RESUME_PREDECESSOR_INVARIANT})"
        )
    predecessor_attempt_id = block.get("attempt_id")
    if (
        not isinstance(predecessor_attempt_id, str)
        or not predecessor_attempt_id.strip()
        or predecessor_attempt_id == attempt_id
    ):
        raise BundleError(
            "predecessor_attempt.attempt_id must be a different, non-empty attempt "
            f"of this run ({RESUME_PREDECESSOR_INVARIANT})"
        )
    trace_path = block.get("trace_path")
    if not isinstance(trace_path, str) or not trace_path.strip():
        raise BundleError(
            f"predecessor_attempt.trace_path must be a path ({RESUME_PREDECESSOR_INVARIANT})"
        )
    # ``core.tracing.TraceSink`` writes exactly one file name per run, so a
    # predecessor trace that is not named after this run is not a trace of
    # this run -- refused before its bytes are ever read.
    if Path(trace_path).name != f"{run_id}.trace.jsonl":
        raise BundleError(
            f"predecessor_attempt.trace_path must name {run_id!r}'s own trace file "
            f"({RESUME_PREDECESSOR_INVARIANT})"
        )
    if not _is_sha256(block.get("trace_sha256")):
        raise BundleError(
            "predecessor_attempt.trace_sha256 must be a 64-hex SHA-256 "
            f"({RESUME_PREDECESSOR_INVARIANT})"
        )
    kept = block.get("kept_sample_ids")
    if (
        not isinstance(kept, list)
        or not kept
        or any(not isinstance(sample_id, str) or not sample_id for sample_id in kept)
        or len(set(kept)) != len(kept)
        or kept != sorted(kept)
    ):
        raise BundleError(
            "predecessor_attempt.kept_sample_ids must be a sorted, unique, non-empty "
            f"list of sample ids ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if block.get("kept_sample_ids_sha256") != _kept_sample_ids_sha256(kept):
        raise BundleError(
            "predecessor_attempt.kept_sample_ids_sha256 does not match a fresh hash "
            "of kept_sample_ids -- the kept-row list was edited after it was "
            f"declared ({RESUME_PREDECESSOR_INVARIANT})"
        )
    counts = block.get("counts")
    if (
        not isinstance(counts, Mapping)
        or set(counts) != {"kept", "flown", "partial"}
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counts.values()
        )
    ):
        raise BundleError(
            "predecessor_attempt.counts must carry non-negative kept/flown/partial "
            f"integers ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if counts["kept"] != len(kept):
        raise BundleError(
            f"predecessor_attempt.counts.kept {counts['kept']!r} does not match "
            f"len(kept_sample_ids) {len(kept)} ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if counts["partial"] > counts["flown"]:
        raise BundleError(
            "predecessor_attempt.counts.partial cannot exceed counts.flown "
            f"({RESUME_PREDECESSOR_INVARIANT})"
        )
    return dict(block)


def verify_predecessor_attempt(
    manifest: Mapping[str, object],
    *,
    split_ids: frozenset,
    attempt_id: object,
) -> tuple[Mapping[str, Mapping[str, object]], frozenset]:
    """Re-derive a declared predecessor attempt from the bytes on disk.

    Returns ``(trace_records, kept_sample_ids)`` -- empty for a manifest that
    declares no predecessor, which is every manifest this repository sealed
    before E10 and every ordinary flight after it.

    Trusts nothing the block asserts: the trace file is re-hashed against the
    declared sha256, the kept-row list is re-hashed against its own declared
    hash, and every kept id must belong to the frozen split.
    """

    block = manifest.get("predecessor_attempt")
    if block is None:
        return {}, frozenset()
    block = _validate_predecessor_block(
        block, run_id=manifest.get("run_id"), attempt_id=attempt_id
    )
    kept = frozenset(str(sample_id) for sample_id in block["kept_sample_ids"])
    outside = sorted(kept - split_ids)
    if outside:
        raise BundleError(
            f"predecessor_attempt keeps {len(outside)} sample(s) outside the frozen "
            f"split, e.g. {outside[:5]} ({RESUME_PREDECESSOR_INVARIANT})"
        )
    trace_path = Path(str(block["trace_path"]))
    if not trace_path.is_file():
        raise BundleError(
            f"predecessor_attempt trace {trace_path} does not exist; a kept row's "
            f"custody cannot be verified without it ({RESUME_PREDECESSOR_INVARIANT})"
        )
    raw = trace_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != block["trace_sha256"]:
        raise BundleError(
            f"predecessor_attempt trace {trace_path} hashes to {actual}, but the "
            f"manifest declares {block['trace_sha256']} -- the predecessor trace "
            f"changed after it was declared ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if block.get("mode") == "checkpoint":
        _verify_checkpoint_predecessor(block, raw)
    return _verify_raw_trace(raw, None), kept


#: E10d (2026-09-29): the field set a ``predecessor_attempts`` LIST entry
#: takes -- byte-identical to a single ``predecessor_attempt`` block
#: (:data:`_PREDECESSOR_FIELDS`); every entry is independently validated by
#: :func:`_validate_predecessor_block`, so this module needs no second shape.
def _validate_predecessor_blocks_list(
    blocks: object, *, run_id: object, attempt_id: object,
) -> tuple[Mapping[str, object], ...]:
    """Shape and CROSS-block self-consistency of a ``predecessor_attempts`` list.

    E10d (2026-09-29, multi-predecessor seal-only completion): each entry is
    checked exactly as a single-predecessor ``predecessor_attempt`` block is
    (:func:`_validate_predecessor_block`); this additionally refuses two
    entries naming the same predecessor ``attempt_id`` or claiming the same
    ``kept_sample_ids`` entry -- defence in depth, independent of whatever
    built the manifest, mirroring ``core.flight.resume.MergedPredecessors``'s
    own disjointness check on the writing side.
    """

    if not isinstance(blocks, list) or not blocks:
        raise BundleError(
            "run manifest predecessor_attempts must be a non-empty list of "
            f"predecessor_attempt objects ({RESUME_PREDECESSOR_INVARIANT})"
        )
    validated = tuple(
        _validate_predecessor_block(block, run_id=run_id, attempt_id=attempt_id)
        for block in blocks
    )
    attempt_ids = [str(block["attempt_id"]) for block in validated]
    if len(set(attempt_ids)) != len(attempt_ids):
        raise BundleError(
            "run manifest predecessor_attempts names the same predecessor "
            f"attempt twice ({RESUME_PREDECESSOR_INVARIANT})"
        )
    owner: dict[str, str] = {}
    for block in validated:
        for sample_id in block["kept_sample_ids"]:
            held_by = owner.get(sample_id)
            if held_by is not None:
                raise BundleError(
                    f"run manifest predecessor_attempts keeps sample {sample_id!r} "
                    f"in two predecessor attempts, {held_by!r} and "
                    f"{block['attempt_id']!r} ({RESUME_PREDECESSOR_INVARIANT})"
                )
            owner[sample_id] = str(block["attempt_id"])
    return validated


def verify_predecessor_attempts(
    manifest: Mapping[str, object],
    *,
    split_ids: frozenset,
    attempt_id: object,
) -> tuple[Mapping[str, Mapping[str, Mapping[str, object]]], frozenset]:
    """Re-derive every declared predecessor attempt from the bytes on disk.

    E10d (2026-09-29): generalizes :func:`verify_predecessor_attempt` to a
    manifest declaring MULTIPLE pinned predecessors under
    ``predecessor_attempts`` (a resume-recovery whose union of predecessors'
    COMPLETE rows may or may not have covered the whole roster). Returns
    ``(trace_records_by_sample, kept_sample_ids)`` where
    ``trace_records_by_sample`` maps each KEPT sample id to the trace-records
    dict of the ONE predecessor attempt that kept it -- never a flat,
    cross-predecessor-merged dict. Request ids are attempt-scoped
    (``rails.core_client`` mints them per-client) and CAN repeat across
    different predecessor attempts for entirely different samples, so a
    merged flat dict could let a row's request id resolve against the wrong
    predecessor's contact; binding per SAMPLE keeps each row checked against
    exactly the one trace :func:`core.flight.resume.MergedPredecessors`
    itself bound it to.

    A manifest declaring neither ``predecessor_attempt`` nor
    ``predecessor_attempts`` returns ``({}, frozenset())`` -- every manifest
    sealed before E10 and every ordinary flight since. Declaring both is
    refused as ambiguous.
    """

    single = manifest.get("predecessor_attempt")
    multiple = manifest.get("predecessor_attempts")
    if single is not None and multiple is not None:
        raise BundleError(
            "run manifest declares both predecessor_attempt and "
            f"predecessor_attempts ({RESUME_PREDECESSOR_INVARIANT})"
        )
    if single is not None:
        trace_records, kept = verify_predecessor_attempt(
            manifest, split_ids=split_ids, attempt_id=attempt_id,
        )
        return {sample_id: trace_records for sample_id in kept}, kept
    if multiple is None:
        return {}, frozenset()
    blocks = _validate_predecessor_blocks_list(
        multiple, run_id=manifest.get("run_id"), attempt_id=attempt_id,
    )
    per_sample: dict[str, Mapping[str, Mapping[str, object]]] = {}
    kept_all: set[str] = set()
    for block in blocks:
        kept = frozenset(str(sample_id) for sample_id in block["kept_sample_ids"])
        outside = sorted(kept - split_ids)
        if outside:
            raise BundleError(
                f"predecessor_attempts[{block['attempt_id']!r}] keeps "
                f"{len(outside)} sample(s) outside the frozen split, e.g. "
                f"{outside[:5]} ({RESUME_PREDECESSOR_INVARIANT})"
            )
        trace_path = Path(str(block["trace_path"]))
        if not trace_path.is_file():
            raise BundleError(
                f"predecessor_attempts[{block['attempt_id']!r}] trace {trace_path} "
                f"does not exist; a kept row's custody cannot be verified without "
                f"it ({RESUME_PREDECESSOR_INVARIANT})"
            )
        raw = trace_path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != block["trace_sha256"]:
            raise BundleError(
                f"predecessor_attempts[{block['attempt_id']!r}] trace {trace_path} "
                f"hashes to {actual}, but the manifest declares "
                f"{block['trace_sha256']} -- the predecessor trace changed after "
                f"it was declared ({RESUME_PREDECESSOR_INVARIANT})"
            )
        if block.get("mode") == "checkpoint":
            _verify_checkpoint_predecessor(block, raw)
        trace_records = _verify_raw_trace(raw, None)
        for sample_id in kept:
            per_sample[sample_id] = trace_records
        kept_all |= kept
    return per_sample, frozenset(kept_all)


def _row_label(row: Mapping[str, object]) -> str:
    return f"outputs row {row.get('sample_id')!r} (request {row.get('request_id')!r})"


def _committed_text(row: Mapping[str, object]) -> str:
    """The exact bytes a grouped row's COMMIT policy delivered.

    ``core.flight.runtime._canonical_output_rows`` writes the committed
    rendering into ``text``. When the E4 SLURP projection-v3 delivery
    transform is also on, that same stage keeps the committed rendering
    verbatim under ``pre_projection_text`` and puts the projected bytes into
    ``text``. So the commit recomputation targets ``pre_projection_text``
    whenever the row records one and ``text`` otherwise -- in both cases
    exactly the bytes the runner wrote as the commit policy's own output.
    """

    if "pre_projection_text" in row:
        committed = row["pre_projection_text"]
        if not isinstance(committed, str):
            raise BundleError(
                f"{_row_label(row)}: 'pre_projection_text' must be a string "
                f"({SOLVER_GROUP_INVARIANT})"
            )
        return committed
    return str(row["text"])


def _first_difference(recomputed: str, recorded: str) -> str:
    """Name WHERE two texts differ without reprinting either of them: a
    delivered SLURP answer carries slot fillers taken from speech, and a
    refusal message is not a place to re-emit them."""

    limit = min(len(recomputed), len(recorded))
    offset = next(
        (index for index in range(limit) if recomputed[index] != recorded[index]),
        limit,
    )
    return (
        f"first difference at character offset {offset} "
        f"(recomputed length {len(recomputed)}, recorded length {len(recorded)})"
    )


def _verify_grouped_commit(row: Mapping[str, object]) -> None:
    """I7g: re-derive a grouped Solver row's delivered text from its own
    recorded raw samples, and refuse the row when it does not reproduce.

    Three things must hold for such a row; this function checks the last two
    (the first -- every sample's response hash against the trace's own
    MODEL_RESPONSE bytes -- needs the trace and lives in
    :func:`_verify_grouped_solver_trace_binding`):

    2. ``solver_group.commit_policy_id`` resolves in
       ``core.base.COMMIT_POLICIES`` and is deterministic (re-applied twice
       over the same recorded votes it must return the same answer).
    3. re-running that policy over the row's own recorded samples, through
       ``analysis.native_commit_replay.replay_row`` -- the same code the
       offline sensitivity table runs -- reproduces the delivered bytes
       (:func:`_committed_text`) byte for byte.

    A grouped row is refused, never silently accepted, when it does not carry
    the parameters the policy was applied with: without them the delivered
    text cannot be re-derived at all, and a bundle carries no composed
    configuration to recover them from.
    """

    label = _row_label(row)
    solver_group = row.get("solver_group")
    if not isinstance(solver_group, Mapping):
        raise BundleError(
            f"{label}: 'solver_group' must be a JSON object "
            f"({SOLVER_GROUP_INVARIANT})"
        )
    if "commit_params" not in solver_group:
        raise BundleError(
            f"{label}: its grouped Solver receipt names commit policy "
            f"{solver_group.get('commit_policy_id')!r} but records no "
            "'commit_params', so the delivered text cannot be re-derived from the "
            f"recorded samples ({SOLVER_GROUP_INVARIANT})"
        )
    records = solver_group.get("samples")
    if (
        not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or not records
    ):
        raise BundleError(
            f"{label}: solver_group carries no sample records "
            f"({SOLVER_GROUP_INVARIANT})"
        )
    from ...rails.native_episode_receipt import (  # noqa: PLC0415
        validate_solver_group_receipt,
    )

    try:
        validate_solver_group_receipt(
            solver_group, samples=len(records), error_type=BundleError
        )
    except BundleError as error:
        raise BundleError(
            f"{label}: grouped Solver custody is malformed: {error} "
            f"({SOLVER_GROUP_INVARIANT})"
        ) from error

    from ...analysis.native_commit_replay import (  # noqa: PLC0415
        NativeCommitReplayError,
        replay_row,
    )
    from ..base import COMMIT_POLICIES, CoreError  # noqa: PLC0415

    # Function-local: importing rails.commit_policies is what POPULATES
    # core.base.COMMIT_POLICIES (the same registration discipline every other
    # caller of this registry follows).
    from ...rails import commit_policies as _commit_policies  # noqa: PLC0415, F401

    policy_id = str(solver_group["commit_policy_id"])
    commit_params = dict(solver_group["commit_params"])
    try:
        policy = COMMIT_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise BundleError(
            f"{label}: commit policy {policy_id!r} is not registered in "
            "core.base.COMMIT_POLICIES -- a grouped row's delivered text is custody "
            "only when a registered, deterministic policy can re-derive it "
            f"({SOLVER_GROUP_INVARIANT})"
        ) from error
    try:
        replayed = replay_row(row, policy=policy, commit_params=commit_params)
        again = replay_row(row, policy=policy, commit_params=commit_params)
    except (NativeCommitReplayError, ValueError, TypeError, KeyError) as error:
        raise BundleError(
            f"{label}: re-running commit policy {policy_id!r} over the recorded "
            f"samples failed: {error} ({SOLVER_GROUP_INVARIANT})"
        ) from error
    if replayed != again:
        raise BundleError(
            f"{label}: commit policy {policy_id!r} did not reproduce itself over the "
            "same recorded samples -- a COMMIT policy must be deterministic "
            f"({SOLVER_GROUP_INVARIANT})"
        )
    recomputed = replayed["final_response_text"]
    recorded = _committed_text(row)
    if recomputed != recorded:
        raise BundleError(
            f"{label}: the delivered text is not what commit policy {policy_id!r} "
            "produces from this row's own recorded samples -- recomputed sha256 "
            f"{hashlib.sha256(recomputed.encode('utf-8')).hexdigest()[:12]}..., "
            f"recorded {hashlib.sha256(recorded.encode('utf-8')).hexdigest()[:12]}...; "
            f"{_first_difference(recomputed, recorded)} ({SOLVER_GROUP_INVARIANT})"
        )


def _delivery_normalisation_receipt(
    row: Mapping[str, object],
) -> Mapping[str, object] | None:
    """The row's ``deliver_normaliser`` custody block, or ``None``.

    It rides INSIDE the row's ``native_episode_receipt`` rather than beside
    it, because it is a fact about how the EPISODE delivered: the node is a
    node of the episode, applied once between the Planner's ACCEPT and the
    delivered answer, and every other episode-level fact (role visits,
    Planner routes, the accepted Solver receipt) is already sealed there.
    """

    receipt = row.get("native_episode_receipt")
    if not isinstance(receipt, Mapping):
        return None
    block = receipt.get("deliver_normaliser")
    if block is None:
        return None
    if not isinstance(block, Mapping):
        raise BundleError(
            f"{_row_label(row)}: 'native_episode_receipt.deliver_normaliser' must "
            f"be a JSON object ({DELIVER_NORMALISER_INVARIANT})"
        )
    return block


def _verify_delivery_normalisation(
    row: Mapping[str, object],
    block: Mapping[str, object],
    response_payload: Mapping[str, object],
) -> None:
    """I7n: re-derive a normalised row's delivered text from the recorded
    model response, and refuse the row when it does not reproduce.

    Four things must hold:

    1. the row carries no ``solver_group`` receipt -- a grouped commit and a
       delivery normalisation would make the delivered bytes a function of
       two rules with only one of them in custody, which is why
       ``rails.native_episode_config`` refuses the combination before any
       contact and why the bundle refuses it again here;
    2. the trace's own MODEL_RESPONSE bytes for this row's request id are
       exactly the rule's recorded INPUT (``input_sha256``) -- this is what
       replaces I7's relaxed ``text`` / ``response_text_sha256`` equality and
       keeps the delivered answer anchored to a real model response;
    3. the named rule resolves in ``core.base.DELIVERY_NORMALISERS`` and is
       deterministic (applied twice to the same input it returns the same
       bytes);
    4. re-running it over those response bytes reproduces the row's delivered
       ``text`` byte for byte, and the rule's own recorded ``output_sha256``
       agrees.

    A refusal names the invariant and the first differing character offset,
    never the text: a delivered SLURP answer carries slot fillers taken from
    speech.
    """

    label = _row_label(row)
    if "solver_group" in row:
        raise BundleError(
            f"{label}: a grouped Solver row cannot also carry a delivery "
            f"normalisation receipt ({DELIVER_NORMALISER_INVARIANT})"
        )
    missing = sorted({"normaliser_id", "input_sha256", "output_sha256"} - set(block))
    if missing:
        raise BundleError(
            f"{label}: its delivery normalisation receipt is missing {missing}, so "
            "the delivered text cannot be re-derived from the recorded response "
            f"({DELIVER_NORMALISER_INVARIANT})"
        )
    source_text = response_payload.get("text")
    if not isinstance(source_text, str):
        raise BundleError(
            f"{label}: its trace response record carries no text to re-derive the "
            f"delivered answer from ({DELIVER_NORMALISER_INVARIANT})"
        )
    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if source_sha256 != block["input_sha256"]:
        raise BundleError(
            f"{label}: the delivery normaliser recorded input "
            f"{str(block['input_sha256'])[:12]}..., but the trace's own response "
            f"bytes hash to {source_sha256[:12]}... -- a normalised row's delivered "
            "text is custody only when the rule ran on the recorded model response "
            f"({DELIVER_NORMALISER_INVARIANT})"
        )
    from ...rails import delivery_normalisers as _normalisers  # noqa: PLC0415, F401
    from ..base import DELIVERY_NORMALISERS, CoreError  # noqa: PLC0415

    normaliser_id = str(block["normaliser_id"])
    try:
        normaliser = DELIVERY_NORMALISERS.resolve(normaliser_id)
    except CoreError as error:
        raise BundleError(
            f"{label}: delivery normaliser {normaliser_id!r} is not registered in "
            "core.base.DELIVERY_NORMALISERS -- a normalised row's delivered text is "
            "custody only when a registered, deterministic rule can re-derive it "
            f"({DELIVER_NORMALISER_INVARIANT})"
        ) from error
    expected_carrier = getattr(normaliser, "carrier_lock_key", None)
    if (not expected_carrier or row.get("carrier_lock_key") != expected_carrier
            or block.get("carrier_lock_key") != expected_carrier):
        raise BundleError(
            f"{label}: the delivery normaliser, row and receipt must name the same "
            f"carrier ({DELIVER_NORMALISER_INVARIANT})"
        )
    try:
        replayed = normaliser(source_text)
        again = normaliser(source_text)
    except Exception as error:  # noqa: BLE001 - any rule failure is a refusal
        raise BundleError(
            f"{label}: re-running delivery normaliser {normaliser_id!r} over the "
            f"recorded response failed: {type(error).__name__} "
            f"({DELIVER_NORMALISER_INVARIANT})"
        ) from error
    if replayed.text != again.text:
        raise BundleError(
            f"{label}: delivery normaliser {normaliser_id!r} did not reproduce "
            "itself over the same recorded response -- a delivery normaliser must "
            f"be deterministic ({DELIVER_NORMALISER_INVARIANT})"
        )
    recorded = str(row["text"])
    if replayed.text != recorded:
        raise BundleError(
            f"{label}: the delivered text is not what delivery normaliser "
            f"{normaliser_id!r} produces from this row's own recorded response -- "
            "recomputed sha256 "
            f"{hashlib.sha256(replayed.text.encode('utf-8')).hexdigest()[:12]}..., "
            f"recorded {hashlib.sha256(recorded.encode('utf-8')).hexdigest()[:12]}"
            f"...; {_first_difference(replayed.text, recorded)} "
            f"({DELIVER_NORMALISER_INVARIANT})"
        )
    if block["output_sha256"] != hashlib.sha256(recorded.encode("utf-8")).hexdigest():
        raise BundleError(
            f"{label}: its delivery normalisation receipt records an output digest "
            f"that is not the delivered text's own ({DELIVER_NORMALISER_INVARIANT})"
        )


def _verify_grouped_solver_trace_binding(
    row: Mapping[str, object],
    solver_group: Mapping[str, object],
    trace_records: Mapping[str, Mapping[str, object]],
) -> None:
    """I7g custody: every RAW sample of a grouped Solver visit must appear in
    the trace under its own contact id, carrying exactly the response bytes the
    ``solver_group`` receipt records for it -- and the row's own transport
    identity must be that group's LAST sample contact.

    This is what stops a grouped row from being a free-floating aggregate: the
    delivered text is re-derived from the recorded samples
    (:func:`_verify_grouped_commit`), and the recorded samples are pinned here
    to real model responses in this same bundle's trace.
    """

    label = _row_label(row)
    if not isinstance(solver_group, Mapping):
        raise BundleError(
            f"{label}: 'solver_group' must be a JSON object "
            f"({SOLVER_GROUP_INVARIANT})"
        )
    records = solver_group.get("samples")
    if (
        not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or not records
    ):
        raise BundleError(
            f"{label}: solver_group carries no sample records "
            f"({SOLVER_GROUP_INVARIANT})"
        )
    last: Mapping[str, object] | None = None
    for record in records:
        if not isinstance(record, Mapping):
            raise BundleError(
                f"{label}: a solver_group sample record must be a JSON object "
                f"({SOLVER_GROUP_INVARIANT})"
            )
        index = record.get("sample_index")
        contacts = record.get("contacts")
        if (
            not isinstance(contacts, Sequence)
            or isinstance(contacts, (str, bytes))
            or not contacts
        ):
            raise BundleError(
                f"{label}: solver_group sample {index!r} records no contact "
                f"({SOLVER_GROUP_INVARIANT})"
            )
        for contact in contacts:
            if not isinstance(contact, Mapping):
                raise BundleError(
                    f"{label}: a solver_group contact must be a JSON object "
                    f"({SOLVER_GROUP_INVARIANT})"
                )
            contact_request_id = contact.get("request_id")
            if not isinstance(contact_request_id, str) or not contact_request_id:
                raise BundleError(
                    f"{label}: solver_group sample {index!r} has a contact without a "
                    f"request id ({SOLVER_GROUP_INVARIANT})"
                )
            request_record_id = f"{contact_request_id}/request"
            response_record_id = f"{contact_request_id}/response"
            absent = [
                record_id
                for record_id in (request_record_id, response_record_id)
                if record_id not in trace_records
            ]
            if absent:
                raise BundleError(
                    f"{label}: solver_group sample {index!r} contact "
                    f"{contact_request_id!r} has no trace record {absent[0]!r} -- every "
                    "raw sample of a grouped Solver visit must stay in the trace "
                    f"({SOLVER_GROUP_INVARIANT})"
                )
            payload = trace_records[response_record_id]
            text = payload.get("text")
            recorded_text_sha256 = contact.get("response_text_sha256")
            if (
                not isinstance(text, str)
                or hashlib.sha256(text.encode("utf-8")).hexdigest()
                != recorded_text_sha256
            ):
                raise BundleError(
                    f"{label}: solver_group sample {index!r} contact "
                    f"{contact_request_id!r} records a response_text_sha256 that does "
                    "not match the trace's own recorded model response bytes "
                    f"({SOLVER_GROUP_INVARIANT})"
                )
            for field, value in (
                ("response_text_sha256", recorded_text_sha256),
                ("response_sha256", contact.get("response_sha256")),
            ):
                if payload.get(field) != value:
                    raise BundleError(
                        f"{label}: solver_group sample {index!r} contact "
                        f"{contact_request_id!r} {field} disagrees with the trace "
                        f"record {response_record_id!r} ({SOLVER_GROUP_INVARIANT})"
                    )
            if trace_records[request_record_id].get("payload_sha256") != contact.get(
                "request_sha256"
            ):
                raise BundleError(
                    f"{label}: solver_group sample {index!r} contact "
                    f"{contact_request_id!r} request_sha256 disagrees with the trace "
                    f"record {request_record_id!r} ({SOLVER_GROUP_INVARIANT})"
                )
            last = contact
    if (
        last is None
        or row.get("request_id") != last.get("request_id")
        or row.get("request_sha256") != last.get("request_sha256")
        or row.get("response_sha256") != last.get("response_sha256")
    ):
        raise BundleError(
            f"{label}: a grouped row's own request/response identity must be its "
            "group's LAST raw sample contact -- the delivered text is the commit "
            "policy's aggregate, but the row's transport identity is still one real "
            f"contact ({SOLVER_GROUP_INVARIANT})"
        )


def _verify_supply_variant_trace_binding(
    row: Mapping[str, object], trace_records: Mapping[str, Mapping[str, object]],
) -> None:
    """Bind every Solver arm visit to its trace and the final arm to the row.

    Under the default ``arm_visits`` ("every", or a v1 receipt with no such
    key at all) the output carries the FINAL visit's arm selection and every
    Solver visit carries every declared arm -- unchanged since item E42.

    Item E42b (2026-09-27, owner decision 172, merge set B): under
    ``arm_visits: "first"`` the arm group fans out ONLY at the Solver's FIRST
    visit (``visit_index`` 0 -- the schema's own field, always 0, since it is
    always that visit's receipt that is sealed, section 2 of the svinst
    design); the receipt's arm rows then describe that first visit, not
    necessarily the final (delivered) one, and every OTHER Solver visit
    carries exactly one ordinary contact with no arm custody of its own. The
    row's own identity still binds to the truly final contact of the truly
    final visit, whichever visit that is.

    Earlier revision visits remain in ``native_episode_receipt.role_visits``.
    The bundle has no raw composed configuration; declaration identity was
    checked at flight seal.
    """

    label = _row_label(row)

    def refuse(reason: str) -> None:
        raise BundleError(f"{label}: {reason} ({SUPPLY_VARIANT_INVARIANT})")

    variants = row.get("supply_variants")
    if not isinstance(variants, Mapping):
        refuse("supply_variants must be a receipt object")
    arms = variants.get("arms")
    if not isinstance(arms, Sequence) or isinstance(arms, (str, bytes)) or not arms:
        refuse("supply_variants has no ordered arms")
    arm_ids = [arm.get("arm_id") if isinstance(arm, Mapping) else None for arm in arms]
    if any(not isinstance(arm_id, str) or not arm_id for arm_id in arm_ids):
        refuse("supply_variants contains an arm without an id")
    arm_visits = variants.get("arm_visits", "every")
    if arm_visits not in ("every", "first"):
        refuse("supply_variants.arm_visits must be 'every' or 'first'")

    episode = row.get("native_episode_receipt")
    visits = episode.get("role_visits") if isinstance(episode, Mapping) else None
    if not isinstance(visits, Sequence) or isinstance(visits, (str, bytes)):
        refuse("supply_variants has no native episode role visits")
    solver_visits = [visit for visit in visits if isinstance(visit, Mapping)
                     and visit.get("stage") == "solver"]
    if not solver_visits:
        refuse("supply_variants has no Solver visit")
    # The visit whose contacts the receipt's arm rows describe: the FIRST
    # visit under "first" arm visits (the only one that ever fans out), the
    # FINAL visit otherwise ("today: the final one", unchanged since E42).
    reference_visit = solver_visits[0] if arm_visits == "first" else solver_visits[-1]
    reference_execution = reference_visit.get("execution_receipt")
    reference_contacts = (
        reference_execution.get("contacts")
        if isinstance(reference_execution, Mapping) else None
    )
    if not isinstance(reference_contacts, Sequence) or isinstance(reference_contacts, (str, bytes)):
        refuse("the arm-bearing Solver visit has no contacts")
    if [arm.get("contact_id") for arm in arms] != [
        contact.get("agent_contact_id") if isinstance(contact, Mapping) else None
        for contact in reference_contacts
    ]:
        refuse("declared arm contact ids disagree with the arm-bearing Solver visit")

    from ...rails.native_episode_receipt import validate_supply_variant_receipt

    states = [payload.get("org_final_query_state") for payload in trace_records.values()
              if isinstance(payload.get("org_final_query_state"), Mapping)
              and payload["org_final_query_state"].get("query_sample_id") == row.get("sample_id")]
    if len(states) != 1:
        refuse("supply_variants needs exactly one final QueryState in the trace")
    retrieved_ids = states[0].get("retrieved_value_ids")
    if not isinstance(retrieved_ids, Sequence) or isinstance(retrieved_ids, (str, bytes)):
        refuse("final QueryState has no retrieved value ids")
    try:
        validate_supply_variant_receipt(
            variants, arm_ids=arm_ids, delivered_arm_id=arm_ids[-1],
            phase_id=str(reference_visit.get("role_id")),
            retrieved_value_ids=retrieved_ids, error_type=BundleError,
        )
    except BundleError as error:
        refuse(f"supply-variant receipt is invalid: {error}")

    seen_contacts: set[str] = set()
    last: Mapping[str, object] | None = None
    for visit_index, visit in enumerate(solver_visits):
        execution = visit.get("execution_receipt")
        contacts = execution.get("contacts") if isinstance(execution, Mapping) else None
        if not isinstance(contacts, Sequence) or isinstance(contacts, (str, bytes)):
            refuse(f"Solver visit {visit_index} has no contacts")
        is_fanout_visit = arm_visits != "first" or visit_index == 0
        expected_len = len(arm_ids) if is_fanout_visit else 1
        if len(contacts) != expected_len:
            refuse(f"Solver visit {visit_index} does not carry its expected contact count")
        if execution.get("final_contact") != contacts[-1]:
            refuse(f"Solver visit {visit_index} final contact is not its last arm")
        for position, contact in enumerate(contacts):
            if not isinstance(contact, Mapping):
                refuse(f"Solver visit {visit_index} contact {position} has no contact")
            contact_id = contact.get("agent_contact_id")
            request_id = contact.get("request_id")
            if (not isinstance(contact_id, str) or not contact_id
                    or contact_id in seen_contacts
                    or not isinstance(request_id, str) or not request_id):
                refuse(f"Solver visit {visit_index} contact {position} has invalid identity")
            seen_contacts.add(contact_id)
            request = trace_records.get(f"{request_id}/request")
            response = trace_records.get(f"{request_id}/response")
            if not isinstance(request, Mapping) or not isinstance(response, Mapping):
                refuse(f"Solver visit {visit_index} contact {position} has no trace pair")
            response_text = response.get("text")
            if (request.get("payload_sha256") != contact.get("request_sha256")
                    or _request_record_sample_id(request) != row.get("sample_id")
                    or not isinstance(response_text, str)
                    or hashlib.sha256(response_text.encode("utf-8")).hexdigest()
                    != contact.get("response_text_sha256")
                    or response.get("response_text_sha256") != contact.get("response_text_sha256")
                    or response.get("response_sha256") != contact.get("response_sha256")):
                refuse(f"Solver visit {visit_index} contact {position} differs from its trace")
            last = contact
    if (last is None or row.get("request_id") != last.get("request_id")
            or row.get("request_sha256") != last.get("request_sha256")
            or row.get("response_sha256") != last.get("response_sha256")):
        refuse("output identity is not the final delivering arm contact")


def _verify_perception_branch_trace_binding(
    row: Mapping[str, object], trace_records: Mapping[str, Mapping[str, object]],
) -> None:
    """Bind every Perception branch's contact to its trace pair (same-flight
    instrument, PHASE 2, merge set C, design section 3, "I7v, Perception
    path" -- same invariant id, :data:`SUPPLY_VARIANT_INVARIANT`, as the
    Solver arm route's own).

    Structurally :func:`_verify_supply_variant_trace_binding`'s twin, over
    the Perception role's own custody
    (``native_episode_receipt.perception_branches``, sealed by
    ``reproduction.ojw.native_episode._ApplyRole`` into
    ``state["latest_perception"]`` -- see ``rails.runner``) rather than a
    top-level sibling of the row: Perception is not necessarily the
    episode's own final delivering role, so its custody cannot be read off
    ``row["delivery"]`` the way a Solver arm group's can.

    Perception has exactly ONE visit per row (design section 3, "Branch
    visits"), so unlike the Solver arm route's ``arm_visits`` choice there
    is no later-visit carry-forward to walk: the row's ONE Perception
    ``role_visits`` entry names every declared branch's contact, in
    declared order, in its own ``execution_receipt``.

    The additional Perception-specific invariant this checks beyond the
    generic per-contact trace binding: branch A's (the delivering branch's)
    own ``note_sha256`` equals its own ``response_text_sha256`` -- A's note
    IS its own response text, by construction
    (``rails.runner.read_perception_branch_record``), so this is the
    receipt-level statement of "A's note_sha256 equals the sealed
    Perception state's hash". "Every later request history carries A's
    note hash and no other" is a structural guarantee of
    ``rails.runner.perception_branch_messages`` and ``settle`` (only A's
    own contact ever registers downstream state -- checked live, fail-
    closed, before any later contact is composed) rather than something
    re-derived here from raw request bodies; ``tests/unit/
    test_perception_branch_live.py`` proves it on a real episode.
    """

    label = _row_label(row)

    def refuse(reason: str) -> None:
        raise BundleError(f"{label}: {reason} ({SUPPLY_VARIANT_INVARIANT})")

    episode = row.get("native_episode_receipt")
    branches = episode.get("perception_branches") if isinstance(episode, Mapping) else None
    if not isinstance(branches, Mapping):
        refuse("perception_branches must be a receipt object")
    branch_rows = branches.get("branches")
    if (
        not isinstance(branch_rows, Sequence)
        or isinstance(branch_rows, (str, bytes))
        or not branch_rows
    ):
        refuse("perception_branches has no ordered branches")
    branch_ids = [
        item.get("branch_id") if isinstance(item, Mapping) else None for item in branch_rows
    ]
    if any(not isinstance(branch_id, str) or not branch_id for branch_id in branch_ids):
        refuse("perception_branches contains a branch without an id")

    visits = episode.get("role_visits") if isinstance(episode, Mapping) else None
    if not isinstance(visits, Sequence) or isinstance(visits, (str, bytes)):
        refuse("perception_branches has no native episode role visits")
    perception_visits = [
        visit for visit in visits
        if isinstance(visit, Mapping) and visit.get("stage") == "perception"
    ]
    if len(perception_visits) != 1:
        refuse("perception_branches requires exactly one Perception visit")
    perception_visit = perception_visits[0]
    execution = perception_visit.get("execution_receipt")
    contacts = execution.get("contacts") if isinstance(execution, Mapping) else None
    if not isinstance(contacts, Sequence) or isinstance(contacts, (str, bytes)):
        refuse("the Perception visit has no contacts")
    # Decision 338 (receipt v6): a ``perception_samples`` branch spends k consecutive Perception contacts -- sample 0 is the
    # row's own contact, the rest are named only by its sampling record. Every other row owns exactly one contact. The expected
    # contact sequence is derived from the receipt, then held to the visit's own contact list below.
    sampling_receipt = branches.get("schema") == "saea-perception-branch-arms-v6"
    contact_owner: list[tuple[Mapping[str, object], int | None]] = []
    expected_ids: list[object] = []
    for item in branch_rows:
        samples = _perception_sample_rows(item) if sampling_receipt else None
        if samples is None:
            contact_owner.append((item, None))
            expected_ids.append(item.get("contact_id"))
            continue
        if not samples or samples[0].get("contact_id") != item.get("contact_id"):
            refuse("a perception_samples row's sample 0 must be the row's own contact")
        for position, sample in enumerate(samples):
            contact_owner.append((item, position))
            expected_ids.append(sample.get("contact_id"))
    if expected_ids != [
        contact.get("agent_contact_id") if isinstance(contact, Mapping) else None
        for contact in contacts
    ]:
        refuse("declared branch contact ids disagree with the Perception visit")

    from ...rails.native_episode_receipt import (
        PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS,
        PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5,
        parse_perception_branch_note,
        validate_perception_branch_receipt,
    )

    delivered_branch_id = branch_ids[-1]
    twin_branch_id = None
    for item in branch_rows:
        if isinstance(item, Mapping) and item.get("replicate_of") is not None:
            twin_branch_id = item.get("branch_id")
            break
    if twin_branch_id is None and branches.get("schema") != PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5:
        refuse("perception_branches has no declared twin")
    try:
        validate_perception_branch_receipt(
            branches, branch_ids=branch_ids, delivered_branch_id=delivered_branch_id,
            twin_branch_id=twin_branch_id, phase_id=str(perception_visit.get("role_id")),
            level=branches.get("level"), error_type=BundleError,
        )
    except BundleError as error:
        refuse(f"perception-branch receipt is invalid: {error}")

    seen_contacts: set[str] = set()
    for position, ((branch_row, sample_position), contact) in enumerate(zip(contact_owner, contacts, strict=True)):
        if not isinstance(contact, Mapping):
            refuse(f"Perception branch {position} contact has no contact")
        contact_id = contact.get("agent_contact_id")
        request_id = contact.get("request_id")
        if (
            not isinstance(contact_id, str) or not contact_id
            or contact_id in seen_contacts
            or not isinstance(request_id, str) or not request_id
        ):
            refuse(f"Perception branch {position} contact has invalid identity")
        seen_contacts.add(contact_id)
        request = trace_records.get(f"{request_id}/request")
        response = trace_records.get(f"{request_id}/response")
        if not isinstance(request, Mapping) or not isinstance(response, Mapping):
            refuse(f"Perception branch {position} contact has no trace pair")
        response_text = response.get("text")
        if (
            request.get("payload_sha256") != contact.get("request_sha256")
            or _request_record_sample_id(request) != row.get("sample_id")
            or not isinstance(response_text, str)
            or hashlib.sha256(response_text.encode("utf-8")).hexdigest()
            != contact.get("response_text_sha256")
            or response.get("response_text_sha256") != contact.get("response_text_sha256")
            or response.get("response_sha256") != contact.get("response_sha256")
        ):
            refuse(f"Perception branch {position} contact differs from its trace")
        if sample_position not in (None, 0) and sampling_receipt:
            continue_after_sample = True
        else:
            continue_after_sample = False
        if sample_position is not None:
            sample = _perception_sample_rows(branch_row)[sample_position]
            if (
                sample.get("request_sha256") != contact.get("request_sha256")
                or sample.get("response_text_sha256") != contact.get("response_text_sha256")
            ):
                refuse(f"Perception branch {position} sample record disagrees with its own contact")
            sample_status, sample_ids, _raw = parse_perception_branch_note(response_text)
            if sample.get("note_parse_status") != sample_status or list(sample.get("candidate_intent_ids") or ()) != list(sample_ids):
                refuse(f"Perception branch {position} sample note fields do not re-derive from its recorded response")
            _verify_sample_wire(request, sample, refuse=refuse, what=f"Perception branch {position} sample")
        if continue_after_sample:
            continue
        if (
            not isinstance(branch_row, Mapping)
            or branch_row.get("request_sha256") != contact.get("request_sha256")
            or branch_row.get("response_text_sha256") != contact.get("response_text_sha256")
        ):
            refuse(
                f"Perception branch {position} record disagrees with its own contact"
            )
        # Schema v2 (2026-09-29): the note-parse fields must RE-DERIVE from the
        # trace's own recorded response text (as I7l re-derives a relisten
        # disposition), never merely from the receipt's own say-so. Checked
        # whenever the note IS the response (every live branch so far).
        if (
            branches.get("schema") in PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS
            and branch_row.get("note_sha256") == branch_row.get("response_text_sha256")
        ):
            status, candidates, raw_count = parse_perception_branch_note(response_text)
            if (
                branch_row.get("note_parse_status") != status
                or list(branch_row.get("candidate_intent_ids") or ()) != list(candidates)
                or branch_row.get("candidate_intent_ids_raw_count") != raw_count
            ):
                refuse(
                    f"Perception branch {position} note-parse fields do not re-derive "
                    "from its recorded response"
                )

    a_row = branch_rows[-1]
    if (
        not isinstance(a_row, Mapping)
        or a_row.get("note_sha256") != a_row.get("response_text_sha256")
    ):
        refuse(
            "the delivering branch's note_sha256 must equal its own "
            "response_text_sha256 (its note IS its own response)"
        )
    _verify_absent_solver_columns(branch_rows, visits, trace_records, refuse=refuse)
    if sampling_receipt:
        _verify_sampling_columns(branch_rows, contacts, visits, trace_records, refuse=refuse)
    if branches.get("schema") == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5:
        _verify_thinking_policy_wire(
            branch_rows, contacts, visits, trace_records, refuse=refuse,
        )


def _perception_sample_rows(row: object) -> list[Mapping[str, object]] | None:
    """The per-sample rows of a v6 branch row's ``sampling.perception_samples`` record, or ``None`` when it declares none."""

    sampling = row.get("sampling") if isinstance(row, Mapping) else None
    record = sampling.get("perception_samples") if isinstance(sampling, Mapping) else None
    samples = record.get("samples") if isinstance(record, Mapping) else None
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
        return None
    return [sample if isinstance(sample, Mapping) else {} for sample in samples]


def _verify_sample_wire(request: Mapping[str, object], sample: Mapping[str, object], *, refuse, what: str) -> None:
    """Decision 338: the recorded request carried exactly the seed -- and, for a sampled stream, the sampling override -- its
    sample row declares. Read from the trace's own request payload, never from the receipt's say-so."""

    payload = request.get("payload")
    decoding = payload.get("decoding_params") if isinstance(payload, Mapping) else None
    if not isinstance(decoding, Mapping):
        refuse(f"{what} request carries no decoding_params to compare with its sampling record")
    if decoding.get("seed") != sample.get("seed"):
        refuse(f"{what} request carries another seed than its sampling record declares")
    override = sample.get("override")
    if override is not None:
        for name, value in dict(override).items():
            if decoding.get(name) != value:
                refuse(f"{what} request carries another {name} than its sampling record declares")


def _verify_sampling_columns(branch_rows, perception_contacts, visits, trace_records, *, refuse) -> None:
    """Decision 338 (receipt v6): re-derive every sampling record from the trace.

    * ``perception_samples``: the merged list, the appended ids and the support counts re-derive from the k recorded sample
      notes through the registered merge policy.
    * ``solver_samples``: the n sample contacts are consecutive contacts of the first Solver visit, sample 0 is the row's own
      Solver column, each sample's hashes, seed and override match the recorded request, its parse status re-derives from the
      recorded response text (or the wire ``finish_reason`` of a finite completion), and the commit outcome re-derives through
      the registered commit policy (N1 is unavailable in flight, so a configured gate reports ``n1-unavailable``).
    """

    from ...rails.supply_variants import (  # noqa: PLC0415
        PerceptionBranchError, PerceptionSamplesAxis, SolverSamplesAxis, commit_solver_samples,
        merge_perception_samples, solver_sample_parse_status,
    )

    contacts_by_agent = {
        contact.get("agent_contact_id"): contact
        for contact in perception_contacts if isinstance(contact, Mapping)
    }

    def response_text_of(contact: Mapping[str, object]) -> str | None:
        record = trace_records.get(f"{contact.get('request_id')}/response")
        text = record.get("text") if isinstance(record, Mapping) else None
        return text if isinstance(text, str) else None

    solver_visits = [v for v in visits if isinstance(v, Mapping) and v.get("stage") == "solver"]
    solver_execution = solver_visits[0].get("execution_receipt") if solver_visits else None
    solver_by_agent = {
        contact.get("agent_contact_id"): contact
        for contact in (solver_execution.get("contacts") if isinstance(solver_execution, Mapping) else None) or ()
        if isinstance(contact, Mapping)
    }
    for row in branch_rows:
        sampling = row.get("sampling") if isinstance(row, Mapping) else None
        if not isinstance(sampling, Mapping):
            continue
        branch_id = row.get("branch_id")
        record = sampling.get("perception_samples")
        if isinstance(record, Mapping):
            axis = PerceptionSamplesAxis(
                k=record["k"], decoding=tuple(sorted(record["decoding"].items())), seed_offsets=tuple(record["seed_offsets"]),
                merge_policy=record["merge_policy"], cap=record["cap"],
            )
            texts = []
            for sample in record["samples"]:
                contact = contacts_by_agent.get(sample.get("contact_id"))
                if contact is None:
                    refuse(f"perception samples of branch {branch_id!r} name a contact the Perception visit did not make")
                texts.append(response_text_of(contact))
            try:
                outcome = merge_perception_samples(axis, texts)
            except PerceptionBranchError as error:
                refuse(f"perception samples of branch {branch_id!r} cannot be merged: {error}")
            if (
                list(outcome.merged_candidate_ids) != record["merged_candidate_ids"]
                or list(outcome.appended_candidate_ids) != record["appended_candidate_ids"]
                or [(r["intent_id"], r["support"], r["best_rank"]) for r in record["support_counts"]]
                != [(i, sup, rank) for (i, sup), (_same, rank) in zip(outcome.support_counts, outcome.best_ranks)]
            ):
                refuse(f"perception samples of branch {branch_id!r} merge differently from their recorded outcome")
        record = sampling.get("solver_samples")
        if isinstance(record, Mapping):
            axis = SolverSamplesAxis(
                n=record["n"], decoding=tuple(sorted(record["decoding"].items())), seed_offsets=tuple(record["seed_offsets"]),
                commit_policy=record["commit"]["policy"], min_support=record["commit"]["min_support"],
                similarity_threshold=record["commit"]["similarity_threshold"], n1_min=record["commit"]["n1_min"],
                empty_votes_min=record["commit"]["empty_votes_min"],
            )
            samples = record["samples"]
            if not samples or samples[0].get("contact_id") != row.get("solver_contact_id"):
                refuse(f"solver samples of branch {branch_id!r}: sample 0 must be the row's own Solver column")
            texts = []
            for sample in samples:
                contact = solver_by_agent.get(sample.get("contact_id"))
                if contact is None:
                    refuse(f"solver samples of branch {branch_id!r} name a contact the Solver visit did not make")
                if (
                    sample.get("request_sha256") != contact.get("request_sha256")
                    or sample.get("response_text_sha256") != contact.get("response_text_sha256")
                ):
                    refuse(f"solver sample of branch {branch_id!r} disagrees with its own contact")
                request = trace_records.get(f"{contact.get('request_id')}/request")
                if not isinstance(request, Mapping):
                    refuse(f"solver sample of branch {branch_id!r} has no recorded request")
                _verify_sample_wire(request, sample, refuse=refuse, what=f"solver sample of branch {branch_id!r}")
                status = sample.get("parse_status")
                if isinstance(status, str) and status.startswith("finite-completion:"):
                    wire = trace_records.get(f"{contact.get('request_id')}/wire-response")
                    if not isinstance(wire, Mapping) or wire.get("finish_reason") != status.partition(":")[2]:
                        refuse(f"solver sample of branch {branch_id!r} claims {status!r} but its wire response says otherwise")
                    texts.append(None)
                    continue
                text = response_text_of(contact)
                if solver_sample_parse_status(text) != status:
                    refuse(f"solver sample of branch {branch_id!r} parse status does not re-derive from its recorded response")
                texts.append(text)
            outcome = commit_solver_samples(axis, texts, n1=None)
            recorded = record["outcome"]
            if (
                recorded["intent_support"] != outcome.intent_support
                or recorded["entity_supports"] != [{"type": e.type, "support": e.support} for e in outcome.entities]
                or recorded["delivered_entity_count"] != len(outcome.entities)
                or recorded["gate"] != (None if outcome.gate is None else dict(outcome.gate))
            ):
                refuse(f"solver samples of branch {branch_id!r} commit differently from their recorded outcome")


def _verify_absent_solver_columns(branch_rows, visits, trace_records, *, refuse) -> None:
    """NX-T R1 seal fix (2026-10-15): every ``solver_absent`` Solver column is a real, traced contact that ended on the finite
    completion its ``absent_reason`` names.

    The receipt's own say-so is not enough: the absent row's Solver contact must be one of the first Solver visit's contacts, carry the
    request/response digests the row records, and its recorded wire response must carry exactly the ``finish_reason`` the reason
    names (``finite-completion:length`` needs ``length``). The delivering branch can never be absent (the receipt validator refuses
    it), so the delivering arm's custody is untouched by this check.
    """

    absent = [row for row in branch_rows if isinstance(row, Mapping) and row.get("solver_absent")]
    if not absent:
        return
    solver_visits = [
        visit for visit in visits if isinstance(visit, Mapping) and visit.get("stage") == "solver"
    ]
    execution = solver_visits[0].get("execution_receipt") if solver_visits else None
    solver_contacts = execution.get("contacts") if isinstance(execution, Mapping) else None
    if not isinstance(solver_contacts, Sequence) or isinstance(solver_contacts, (str, bytes)):
        refuse("an absent Solver column has no Solver visit contacts to be bound to")
    by_agent = {
        contact.get("agent_contact_id"): contact
        for contact in solver_contacts if isinstance(contact, Mapping)
    }
    for row in absent:
        branch_id = row.get("branch_id")
        contact = by_agent.get(row.get("solver_contact_id"))
        if contact is None:
            refuse(f"absent Solver column of branch {branch_id!r} names a contact the Solver visit did not make")
        if (
            contact.get("request_sha256") != row.get("solver_request_sha256")
            or contact.get("response_text_sha256") != row.get("solver_response_text_sha256")
        ):
            refuse(f"absent Solver column of branch {branch_id!r} disagrees with its own contact")
        request_id = contact.get("request_id")
        wire = trace_records.get(f"{request_id}/wire-response") if isinstance(request_id, str) else None
        expected = str(row.get("absent_reason", "")).partition(":")[2]
        if not isinstance(wire, Mapping) or not expected or wire.get("finish_reason") != expected:
            refuse(
                f"absent Solver column of branch {branch_id!r} claims {row.get('absent_reason')!r} but its recorded wire "
                "response carries another finish_reason (or none)"
            )


#: The decoding fields a thinking-policy arm moves (``core.reasoning_knobs``): compared, per node, to the arm's declared policy.
_THINKING_WIRE_KEYS = ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens")


def _verify_thinking_policy_wire(branch_rows, perception_contacts, visits, trace_records, *, refuse) -> None:
    """NX-T R1 (schema v5): every arm's Perception and level-2 Solver request carries the thinking decoding its row declares.

    A node WITHOUT an entry in the arm's policy must carry exactly the delivering arm's (A's) thinking fields for that node; a
    node WITH one must carry ``chat_template_kwargs = {"enable_thinking": false}`` and no budget when it is off, and
    ``thinking_budget_tokens`` equal to its declared budget when it names one. Read from the trace's own request payload, never
    from the receipt's say-so. Counts nothing and prints nothing from any response.
    """

    solver_visits = [
        visit for visit in visits if isinstance(visit, Mapping) and visit.get("stage") == "solver"
    ]
    solver_contacts = []
    if solver_visits:
        execution = solver_visits[0].get("execution_receipt")
        solver_contacts = list(execution.get("contacts") or ()) if isinstance(execution, Mapping) else []
    solver_request_by_agent = {
        contact.get("agent_contact_id"): contact.get("request_id")
        for contact in solver_contacts if isinstance(contact, Mapping)
    }

    def decoding_of(request_id: object, what: str) -> Mapping[str, object]:
        record = trace_records.get(f"{request_id}/request") if isinstance(request_id, str) else None
        payload = record.get("payload") if isinstance(record, Mapping) else None
        decoding = payload.get("decoding_params") if isinstance(payload, Mapping) else None
        if not isinstance(decoding, Mapping):
            refuse(f"{what} request carries no decoding_params to compare with its thinking policy")
        return decoding

    def thinking_view(decoding: Mapping[str, object]) -> dict[str, object]:
        return {key: decoding.get(key) for key in _THINKING_WIRE_KEYS}

    a_row = branch_rows[-1]
    a_view = {
        "perception": thinking_view(decoding_of(perception_contacts[-1].get("request_id"), "delivering Perception")),
        "solver": thinking_view(decoding_of(solver_request_by_agent.get(a_row.get("solver_contact_id")), "delivering Solver")),
    }
    for position, branch_row in enumerate(branch_rows):
        policy = branch_row.get("thinking_policy") or {}
        for kind in ("perception", "solver"):
            request_id = (
                perception_contacts[position].get("request_id") if kind == "perception"
                else solver_request_by_agent.get(branch_row.get("solver_contact_id"))
            )
            what = f"Perception branch {position} {kind}"
            view = thinking_view(decoding_of(request_id, what))
            entry = policy.get(kind)
            if entry is None:
                if view != a_view[kind]:
                    refuse(f"{what} request moved a thinking field its arm's thinking_policy does not name")
                continue
            if entry.get("enable_thinking") is False:
                if view["chat_template_kwargs"] != {"enable_thinking": False} or view["thinking_budget_tokens"] is not None:
                    refuse(f"{what} request is not the no-think form its thinking_policy declares")
            elif "reasoning_budget_tokens" in entry and view["thinking_budget_tokens"] != entry["reasoning_budget_tokens"]:
                refuse(f"{what} request carries another thinking budget than its thinking_policy declares")


#: Item E4 (owner decision 185, 2026-09-28): the invariant code a post-accept
#: targeted-relisten custody refusal names. I7 is unchanged and still binds
#: the row's delivered TEXT to its own response (the relisten stage's shadow
#: delivery never mutates it); a row that also carries a ``relisten`` receipt
#: is additionally held to I7l -- every entity's blind (and, when fired,
#: forced-choice) contact must be a real, traced contact of THIS row, and its
#: disposition/vote must re-derive from that trace's own recorded response
#: text, never merely from the receipt's own say-so.
RELISTEN_INVARIANT = "I7l"


def _verify_relisten_trace_binding(
    row: Mapping[str, object], trace_records: Mapping[str, Mapping[str, object]],
) -> None:
    """I7l: bind every relisten entity's contact(s) to the row's own trace.

    Design ``docs/superpowers/specs/2026-09-28-e4-core-native-targeted-
    relisten-design.md`` section 1's receipt paragraph: the ``saea-
    relisten-v1`` receipt seals contact ids, hashes and flags, never the
    value's own bytes. This re-derives each entity's disposition (and, when
    fired, its forced-choice vote) from the TRACE's own recorded response
    text via ``rails.relisten``'s own parsers -- the same re-derivation
    ``rails.relisten.bind_shadow_entities``'s caller
    (``scripts/analysis/stage3_rollout_score.py``'s
    ``render_relisten_shadow_columns``) performs to bind an ACCEPTED value --
    rather than trusting the receipt's claim alone, and confirms
    ``contacts_used`` is exactly the row's own relisten spend: one blind
    contact per triggered entity plus one forced-choice contact per entity
    whose ``confirm`` block is present.

    Unlike :func:`_verify_supply_variant_trace_binding` and
    :func:`_verify_perception_branch_trace_binding`, a relisten contact is
    never named inside ``native_episode_receipt.role_visits`` (design section
    6: the stage is wired beside ``rails.runner``'s node-context-cleaning
    contact, not as a phase of the program), so this check reads the
    ``relisten`` receipt's own contact ids directly rather than cross
    checking against a role visit's ``execution_receipt``.
    """

    from ...rails.relisten import (
        RELISTEN_RECEIPT_SCHEMA, canonical_value, parse_blind_response,
        parse_confirm_letter, resolve_confirm_vote,
    )

    label = _row_label(row)

    def refuse(reason: str) -> None:
        raise BundleError(f"{label}: {reason} ({RELISTEN_INVARIANT})")

    receipt = row.get("relisten")
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RELISTEN_RECEIPT_SCHEMA:
        refuse("relisten must be a saea-relisten-v1 receipt object")
    entities = receipt.get("entities")
    if not isinstance(entities, Sequence) or isinstance(entities, (str, bytes)):
        refuse("relisten receipt carries no entities list")

    contacts_used = 0
    seen_contacts: set[str] = set()
    for entity in entities:
        if not isinstance(entity, Mapping):
            refuse("relisten entity is not an object")
        blind = entity.get("blind")
        if not isinstance(blind, Mapping):
            refuse("relisten entity carries no blind block")
        contact_id = blind.get("contact_id")
        if not isinstance(contact_id, str) or not contact_id or contact_id in seen_contacts:
            refuse("relisten blind contact has invalid identity")
        seen_contacts.add(contact_id)
        request = trace_records.get(f"{contact_id}/request")
        response = trace_records.get(f"{contact_id}/response")
        if not isinstance(request, Mapping) or not isinstance(response, Mapping):
            refuse(f"relisten blind contact {contact_id!r} has no trace pair")
        if _request_record_sample_id(request) != row.get("sample_id"):
            refuse(f"relisten blind contact {contact_id!r} belongs to another sample")
        text = response.get("text")
        if not isinstance(text, str):
            refuse(f"relisten blind contact {contact_id!r} has no recorded response text")
        parsed = parse_blind_response(text)
        if parsed.disposition != blind.get("disposition"):
            refuse(f"relisten blind contact {contact_id!r} disposition disagrees with its trace")
        expected_value_sha = (
            None if parsed.value is None
            else hashlib.sha256(parsed.value.encode("utf-8")).hexdigest()
        )
        expected_canonical_sha = (
            None if parsed.value is None
            else hashlib.sha256(canonical_value(parsed.value).encode("utf-8")).hexdigest()
        )
        if (
            blind.get("value_sha256") != expected_value_sha
            or blind.get("canonical_sha256") != expected_canonical_sha
        ):
            refuse(f"relisten blind contact {contact_id!r} value hash disagrees with its trace")
        contacts_used += 1

        confirm = entity.get("confirm")
        if confirm is None:
            continue
        if not isinstance(confirm, Mapping):
            refuse("relisten entity confirm block is malformed")
        confirm_contact_id = confirm.get("contact_id")
        if (
            not isinstance(confirm_contact_id, str) or not confirm_contact_id
            or confirm_contact_id in seen_contacts
        ):
            refuse("relisten confirm contact has invalid identity")
        seen_contacts.add(confirm_contact_id)
        confirm_request = trace_records.get(f"{confirm_contact_id}/request")
        confirm_response = trace_records.get(f"{confirm_contact_id}/response")
        if not isinstance(confirm_request, Mapping) or not isinstance(confirm_response, Mapping):
            refuse(f"relisten confirm contact {confirm_contact_id!r} has no trace pair")
        if _request_record_sample_id(confirm_request) != row.get("sample_id"):
            refuse(f"relisten confirm contact {confirm_contact_id!r} belongs to another sample")
        confirm_text = confirm_response.get("text")
        order = confirm.get("order")
        if (
            not isinstance(confirm_text, str)
            or not isinstance(order, Sequence) or isinstance(order, (str, bytes))
            or len(order) != 2
        ):
            refuse(f"relisten confirm contact {confirm_contact_id!r} has no recorded response")
        vote = resolve_confirm_vote(parse_confirm_letter(confirm_text), tuple(order))
        if vote != confirm.get("vote"):
            refuse(f"relisten confirm contact {confirm_contact_id!r} vote disagrees with its trace")
        contacts_used += 1

    if receipt.get("contacts_used") != contacts_used:
        refuse("relisten contacts_used disagrees with its own entity contacts")


def _split_jsonl(text: str) -> list[str]:
    """Split on the literal record separator only (matches ``core.tracing``'s
    and ``core.scorers``' own discipline): ``json.dumps(ensure_ascii=False)``
    leaves U+2028/U+2029 inside string values, which ``str.splitlines()``
    would wrongly treat as line breaks."""

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


_REQUIRED_OUTPUTS_FIELDS = frozenset(
    {
        "request_id",
        "sample_id",
        "carrier_lock_key",
        "arm",
        "text",
        "admitted",
        "request_sha256",
        "response_sha256",
        "response_text_sha256",
    }
)


def _verify_outputs(
    raw: bytes | None, split_ids: frozenset, carrier_lock_key: str, arm: str
) -> tuple[Mapping[str, object], ...]:
    if raw is None:
        return ()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"outputs artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    if not lines:
        raise BundleError("outputs artifact is empty")
    rows: list[Mapping[str, object]] = []
    seen: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"outputs line {number} malformed: {error}") from error
        if not isinstance(row, Mapping):
            raise BundleError(f"outputs line {number} must be a JSON object")
        missing = _REQUIRED_OUTPUTS_FIELDS - set(row)
        if missing:
            raise BundleError(f"outputs line {number} lacks required fields {sorted(missing)}")
        # IMPORTANT fix (round-2 external-threat-model review): an outputs
        # row's own carrier_lock_key/arm must BIND to the manifest's
        # VERIFIED split carrier/arm, never merely be internally present.
        # Before this, verify_bundle only checked that carrier_lock_key
        # existed on each row -- core.scorers.score_asr_outputs then resolves
        # the reference corpus straight from that unverified field.
        # Demonstrated: a manifest split carrier of earnings21-original with
        # every outputs row rewritten to carrier_lock_key=earnings22-original
        # (text and every row hash left untouched, only the outer outputs
        # artifact hash recomputed) verified successfully and scored a
        # "totally wrong" hypothesis against the OTHER carrier's references
        # (mean_wer=0.0) -- an internally inconsistent bundle that
        # verify_bundle had no check that would ever notice. `arm` is bound
        # the same way: it is load-bearing for the protocol_hash
        # re-derivation below, so an outputs row silently disagreeing with
        # the manifest's own arm must refuse too, not merely be ignored.
        row_carrier = row["carrier_lock_key"]
        if row_carrier != carrier_lock_key:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} carrier_lock_key {row_carrier!r} "
                "does not match the manifest's verified split carrier_lock_key "
                f"{carrier_lock_key!r} -- an outputs row must bind to the split it claims "
                "to belong to, never merely carry some carrier value of its own (I7 round-2)"
            )
        row_arm = row["arm"]
        if row_arm != arm:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} arm {row_arm!r} does not match the "
                f"manifest's own arm {arm!r} -- arm is load-bearing for the protocol-hash "
                "re-derivation and must bind to the manifest, not merely be present"
            )
        text_value = row["text"]
        if not isinstance(text_value, str):
            raise BundleError(f"outputs line {number} field 'text' must be a string")
        recomputed = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        if recomputed != row["response_text_sha256"]:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} (request {row.get('request_id')!r}): "
                "text does not match its recorded response_text_sha256 -- the text was "
                "mutated after the model response was recorded (I7)"
            )
        # E2d: a grouped-Solver row satisfies I7 above exactly like every other
        # row (``core.flight.runtime`` hashes the DELIVERED bytes for it), and
        # must ADDITIONALLY re-derive those bytes from its own recorded raw
        # samples. A row without a solver_group receipt is untouched by this.
        # E11 (I7n): the combination is refused HERE, at the row stage, so
        # the refusal names the invariant that forbids it rather than
        # whichever of the two re-derivations happens to fail first. It is
        # also refused before any contact, by
        # ``rails.native_episode_config.load_native_episode_config``.
        if _delivery_normalisation_receipt(row) is not None and "solver_group" in row:
            raise BundleError(
                f"{_row_label(row)}: a grouped Solver row cannot also carry a "
                "delivery normalisation receipt -- the delivered bytes would be a "
                "function of two rules with only one of them in custody "
                f"({DELIVER_NORMALISER_INVARIANT})"
            )
        if "solver_group" in row:
            _verify_grouped_commit(row)
        sample_id = row["sample_id"]
        if not isinstance(sample_id, str):
            raise BundleError(f"outputs line {number} field 'sample_id' must be a string")
        seen[sample_id] = seen.get(sample_id, 0) + 1
        rows.append(row)
    duplicates = sorted(sample_id for sample_id, count in seen.items() if count > 1)
    if duplicates:
        raise BundleError(f"outputs sample set contains duplicate sample ids: {duplicates}")
    row_ids = frozenset(seen)
    missing_ids = sorted(split_ids - row_ids)
    if missing_ids:
        raise BundleError(
            f"outputs sample set is missing frozen split ids: {missing_ids[:10]}"
            + (" (+more)" if len(missing_ids) > 10 else "")
        )
    extra_ids = sorted(row_ids - split_ids)
    if extra_ids:
        raise BundleError(
            f"outputs sample set contains ids outside the frozen split: {extra_ids[:10]}"
            + (" (+more)" if len(extra_ids) > 10 else "")
        )
    return tuple(rows)


def _verify_raw_trace(
    raw: bytes | None, trace_manifest_raw: bytes | None
) -> Mapping[str, Mapping[str, object]]:
    if raw is None:
        return {}
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"raw trace artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    records: dict[str, Mapping[str, object]] = {}
    hashes: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"raw trace line {number} malformed: {error}") from error
        if not isinstance(document, Mapping) or not {"channel", "record_id", "payload"} <= set(
            document
        ):
            raise BundleError(f"raw trace line {number} must carry channel/record_id/payload")
        record_id = document["record_id"]
        if not isinstance(record_id, str):
            raise BundleError(f"raw trace line {number} record_id must be a string")
        if record_id in records:
            raise BundleError(f"raw trace contains duplicate record_id {record_id!r}")
        try:
            content_hash = TraceRecord(
                channel=document["channel"], record_id=record_id, payload=document["payload"]
            ).content_hash()
        except (TraceContractError, BoundaryViolation) as error:
            raise BundleError(f"raw trace record {record_id!r} is invalid: {error}") from error
        records[record_id] = dict(document["payload"])
        hashes[record_id] = content_hash

    if trace_manifest_raw is not None:
        try:
            trace_manifest_doc = json.loads(trace_manifest_raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise BundleError(f"trace manifest artifact is not valid JSON: {error}") from error
        manifest_records = trace_manifest_doc.get("records")
        if not isinstance(manifest_records, Mapping):
            raise BundleError("trace manifest artifact lacks a 'records' mapping")
        missing_in_manifest = sorted(set(hashes) - set(manifest_records))
        extra_in_manifest = sorted(set(manifest_records) - set(hashes))
        if missing_in_manifest or extra_in_manifest:
            raise BundleError(
                "trace manifest does not match the raw trace record set: "
                f"missing_in_manifest={missing_in_manifest[:10]} "
                f"extra_in_manifest={extra_in_manifest[:10]}"
            )
        for record_id, recorded_hash in manifest_records.items():
            if hashes[record_id] != recorded_hash:
                raise BundleError(
                    f"trace manifest hash for record {record_id!r} does not match the "
                    "raw trace record bytes (I7: trace manifest must match raw trace)"
                )
    return records


def _request_record_sample_id(payload: Mapping[str, object]) -> object:
    """The sample id a MODEL_REQUEST record carries inside its own payload."""

    inner = payload.get("payload")
    return inner.get("sample_id") if isinstance(inner, Mapping) else None


def _verify_resume_custody(
    outputs_rows: tuple[Mapping[str, object], ...],
    trace_records: Mapping[str, Mapping[str, object]],
    predecessor_records: Mapping[str, Mapping[str, Mapping[str, object]]],
    kept_sample_ids: frozenset,
) -> None:
    """I7r: each row of a resumed bundle binds to EXACTLY one trace.

    Request ids are attempt-scoped (``rails.core_client`` mints them from a
    per-client counter), so the recovery attempt's own ``flight-0007`` and a
    predecessor's ``flight-0007`` are different contacts of, in general,
    different samples -- and, since E10d, of possibly DIFFERENT predecessor
    attempts too. Custody is therefore decided by SAMPLE id, and this
    function is what makes that decision safe:

    * every kept sample must be absent from the recovery attempt's own
      requests -- a kept row that was ALSO re-flown would have two candidate
      custodies and the merge would be a selection;
    * every flown sample must be present in them;
    * every kept sample must have at least one request in the ONE predecessor
      trace ``predecessor_records`` binds it to (``predecessor_records`` maps
      each kept sample id to that predecessor's own trace-records dict --
      never a flat, cross-predecessor-merged one, so a row can never be
      checked against a DIFFERENT predecessor's trace than the one that kept
      it: see :func:`verify_predecessor_attempts`);
    * the request record a row names must itself carry that row's sample id,
      in the trace the row is held against, so a row can never be verified by
      another sample's contact that happens to share a request id.
    """

    if not outputs_rows:
        return
    recovery_samples: dict[str, object] = {}
    for record_id, payload in trace_records.items():
        if record_id.endswith("/request"):
            sample_id = _request_record_sample_id(payload)
            if isinstance(sample_id, str):
                recovery_samples[sample_id] = record_id
    re_flown = sorted(kept_sample_ids & set(recovery_samples))
    if re_flown:
        raise BundleError(
            f"{len(re_flown)} kept sample(s) were also flown by the recovery attempt, "
            f"e.g. {re_flown[:5]} -- a resume keeps a complete row OR re-flies it, "
            f"never both ({RESUME_PREDECESSOR_INVARIANT})"
        )
    predecessor_presence: dict[str, bool] = {}
    for sample_id in kept_sample_ids:
        records = predecessor_records.get(sample_id) or {}
        predecessor_presence[sample_id] = any(
            record_id.endswith("/request")
            and _request_record_sample_id(payload) == sample_id
            for record_id, payload in records.items()
        )
    for row in outputs_rows:
        sample_id = str(row.get("sample_id"))
        kept = sample_id in kept_sample_ids
        source = predecessor_records.get(sample_id, {}) if kept else trace_records
        label = "predecessor" if kept else "recovery"
        if not kept and sample_id not in recovery_samples:
            raise BundleError(
                f"outputs row {sample_id!r} is not kept from the predecessor attempt "
                "and has no request of its own in this attempt's trace "
                f"({RESUME_PREDECESSOR_INVARIANT})"
            )
        if kept and not predecessor_presence.get(sample_id, False):
            raise BundleError(
                f"outputs row {sample_id!r} is declared kept but has no request in "
                f"the predecessor trace ({RESUME_PREDECESSOR_INVARIANT})"
            )
        request_record_id = f"{row['request_id']}/request"
        payload = source.get(request_record_id)
        if payload is None:
            raise BundleError(
                f"outputs row {sample_id!r} names request {row['request_id']!r}, "
                f"which is absent from the {label} trace it is held against "
                f"({RESUME_PREDECESSOR_INVARIANT})"
            )
        recorded = _request_record_sample_id(payload)
        if recorded != sample_id:
            raise BundleError(
                f"outputs row {sample_id!r} names request {row['request_id']!r}, but "
                f"the {label} trace records that request for sample {recorded!r} "
                f"({RESUME_PREDECESSOR_INVARIANT})"
            )


def _verify_outputs_trace_binding(
    outputs_rows: tuple[Mapping[str, object], ...],
    trace_records: Mapping[str, Mapping[str, object]],
    predecessor_records: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
    kept_sample_ids: frozenset = frozenset(),
) -> None:
    # CRITICAL fix (T6 fix round): the ORIGINAL code also returned early when
    # trace_records was empty -- "there are no trace records to bind against"
    # -- which meant an emptied (or never-populated) trace silently defeated
    # this ENTIRE check for a non-empty outputs file: truncate raw_trace to
    # nothing, empty trace_manifest's records, recompute those two outer
    # hashes, and any forged outputs text (with its response_text_sha256
    # recomputed to match) sailed straight through verify_bundle. There is
    # no legitimate reason for a COMPLETED, non-empty outputs bundle to have
    # zero trace records (every sample emits at least an OBS record and a
    # MODEL_RESPONSE record) -- so an empty/short trace against non-empty
    # outputs must FAIL, not silently skip. Only truly EMPTY outputs (already
    # refused earlier as "outputs artifact is empty" whenever an outputs
    # artifact exists at all) has nothing to bind.
    if not outputs_rows:
        return
    # E10 (I7r): a resumed bundle holds each row against exactly one trace --
    # a kept row against the ONE declared PREDECESSOR attempt's trace that
    # kept it, every other row against this attempt's own. The rules below
    # are byte for byte the same either way; only the record source differs.
    # E10d (2026-09-29): ``predecessor_records`` is keyed by SAMPLE id (each
    # kept sample maps to its OWN predecessor's trace-records dict), never a
    # single flat dict shared by every kept row -- a multi-predecessor resume
    # keeps different rows against different trace files.
    if predecessor_records is not None:
        _verify_resume_custody(
            outputs_rows, trace_records, predecessor_records, kept_sample_ids
        )
    for row in outputs_rows:
        sample_id = str(row.get("sample_id"))
        records = (
            predecessor_records.get(sample_id, {})
            if predecessor_records is not None and sample_id in kept_sample_ids
            else trace_records
        )
        request_id = row["request_id"]
        response_record_id = f"{request_id}/response"
        if response_record_id not in records:
            raise BundleError(
                f"outputs request_id {request_id!r} has no matching trace record "
                f"{response_record_id!r} (I7: every outputs request_id must appear in the trace)"
            )
        payload = records[response_record_id]
        # E2d (I7g): a grouped Solver row's ``text`` is the COMMIT policy's
        # aggregate over N raw samples and its ``response_text_sha256``
        # describes those delivered bytes, so neither can equal the ONE trace
        # response record its request_id names. What still binds to THIS record
        # is the raw transport envelope hash; the delivered bytes are re-derived
        # from the recorded samples (``_verify_grouped_commit``) and those
        # samples are pinned to real trace responses by
        # ``_verify_grouped_solver_trace_binding`` below. Every row without a
        # solver_group receipt keeps all three comparisons.
        solver_group = row.get("solver_group")
        # E11 (I7n): a normalised row's ``text`` is the registered delivery
        # rule's output over this very record's bytes, so those two fields
        # cannot equal the trace record either. What still binds directly is
        # the raw transport envelope hash; the delivered bytes are re-derived
        # from this record's own response text by
        # ``_verify_delivery_normalisation`` below.
        deliver_normaliser = _delivery_normalisation_receipt(row)
        bound_fields = (
            ("response_sha256",)
            if solver_group is not None or deliver_normaliser is not None
            else ("text", "response_sha256", "response_text_sha256")
        )
        for field in bound_fields:
            if payload.get(field) != row.get(field):
                raise BundleError(
                    f"outputs {field} for request {request_id!r} disagrees with the trace "
                    f"record {response_record_id!r}"
                )
        # LOW/INFO fix (T6 fix-2 round): this was previously hedged
        # (`if request_payload is not None and ...`), so deleting the
        # `{request_id}/request` trace record (and its trace-manifest entry,
        # self-consistently) let a hand-forged request_sha256 pass -- the
        # SAME "must exist" discipline the /response check above already
        # enforces unconditionally, now applied here too.
        request_record_id = f"{request_id}/request"
        if request_record_id not in records:
            raise BundleError(
                f"outputs request_id {request_id!r} has no matching trace record "
                f"{request_record_id!r} (I7: every outputs request_id must appear in the trace)"
            )
        request_payload = records[request_record_id]
        if request_payload.get("payload_sha256") != row.get("request_sha256"):
            raise BundleError(
                f"outputs request_sha256 for request {request_id!r} disagrees with the trace "
                f"record {request_record_id!r}"
            )
        episode = row.get("native_episode_receipt")
        if isinstance(episode, Mapping) and "candidate_proposal" in episode:
            from ...rails.slurp_candidate_proposal import validate_candidate_proposal_consumption
            validate_candidate_proposal_consumption(
                episode, sample_id=row.get("sample_id"), trace_records=records,
                error_type=BundleError,
            )
        if deliver_normaliser is not None:
            _verify_delivery_normalisation(row, deliver_normaliser, payload)
        if solver_group is not None:
            _verify_grouped_solver_trace_binding(row, solver_group, records)
        if "supply_variants" in row:
            if solver_group is not None:
                raise BundleError(
                    f"{_row_label(row)}: supply variants cannot also carry a "
                    f"grouped Solver commit ({SUPPLY_VARIANT_INVARIANT})"
                )
            _verify_supply_variant_trace_binding(row, records)
        episode_for_branches = row.get("native_episode_receipt")
        if (
            isinstance(episode_for_branches, Mapping)
            and "perception_branches" in episode_for_branches
        ):
            _verify_perception_branch_trace_binding(row, records)
        if "relisten" in row:
            _verify_relisten_trace_binding(row, records)
