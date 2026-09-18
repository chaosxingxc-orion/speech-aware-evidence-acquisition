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

    if not isinstance(block, Mapping) or set(block) != _PREDECESSOR_FIELDS:
        raise BundleError(
            "run manifest predecessor_attempt must be an object with exactly "
            f"{sorted(_PREDECESSOR_FIELDS)} ({RESUME_PREDECESSOR_INVARIANT})"
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
    return _verify_raw_trace(raw, None), kept


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
    predecessor_records: Mapping[str, Mapping[str, object]],
    kept_sample_ids: frozenset,
) -> None:
    """I7r: each row of a resumed bundle binds to EXACTLY one trace.

    Request ids are attempt-scoped (``rails.core_client`` mints them from a
    per-client counter), so the recovery attempt's own ``flight-0007`` and the
    predecessor's ``flight-0007`` are different contacts of, in general,
    different samples. Custody is therefore decided by SAMPLE id, and this
    function is what makes that decision safe:

    * every kept sample must be absent from the recovery attempt's own
      requests -- a kept row that was ALSO re-flown would have two candidate
      custodies and the merge would be a selection;
    * every flown sample must be present in them;
    * the request record a row names must itself carry that row's sample id,
      in the trace the row is held against, so a row can never be verified by
      another sample's contact that happens to share a request id.
    """

    if not outputs_rows:
        return
    predecessor_samples: dict[str, object] = {}
    for record_id, payload in predecessor_records.items():
        if record_id.endswith("/request"):
            sample_id = _request_record_sample_id(payload)
            if isinstance(sample_id, str):
                predecessor_samples[sample_id] = record_id
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
    for row in outputs_rows:
        sample_id = str(row.get("sample_id"))
        kept = sample_id in kept_sample_ids
        source = predecessor_records if kept else trace_records
        label = "predecessor" if kept else "recovery"
        if not kept and sample_id not in recovery_samples:
            raise BundleError(
                f"outputs row {sample_id!r} is not kept from the predecessor attempt "
                "and has no request of its own in this attempt's trace "
                f"({RESUME_PREDECESSOR_INVARIANT})"
            )
        if kept and sample_id not in predecessor_samples:
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
    predecessor_records: Mapping[str, Mapping[str, object]] | None = None,
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
    # a kept row against the declared PREDECESSOR attempt's trace, every other
    # row against this attempt's own. The rules below are byte for byte the
    # same either way; only the record source differs.
    if predecessor_records is not None:
        _verify_resume_custody(
            outputs_rows, trace_records, predecessor_records, kept_sample_ids
        )
    for row in outputs_rows:
        records = (
            predecessor_records
            if predecessor_records is not None
            and str(row.get("sample_id")) in kept_sample_ids
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
        bound_fields = (
            ("response_sha256",)
            if solver_group is not None
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
        if solver_group is not None:
            _verify_grouped_solver_trace_binding(row, solver_group, records)
