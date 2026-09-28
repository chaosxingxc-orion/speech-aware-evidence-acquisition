"""Resume-recovery of an aborted attempt (owner decision 22, 2026-09-18).

A resume-recovery is a recovery re-registration that applies ONLY when the
code and the request bytes are unchanged -- an infrastructure failure (the
resident server was killed, the host rebooted), never a harness or config
defect. Under that precondition:

* every COMPLETE row of the aborted attempt is kept, without selection;
* every partial or unstarted row is flown by the recovery attempt, under the
  SAME run id and its own new attempt id;
* the merged manifest declares the predecessor attempt (trace sha256, the
  sorted kept sample ids and their hash, the kept/flown/partial counts) and
  scores once;
* ``core.bundle.verify_bundle`` verifies every kept row against the
  predecessor trace, byte for byte.

This module is the model-free half: it reads an aborted attempt's trace and
reports, per sample, either a COMPLETE replayed episode or the reason it is
INCOMPLETE. It contacts nothing -- no model, tokenizer, encoder, scorer or
socket -- and it never writes to the attempt directory it reads.

It re-derives nothing by hand. A native episode's own terminal custody is
already in its trace: ``rails.runner.run_speech_native_agent_loop`` emits the
compact episode receipt as ``USE <sample_id>/<program_id>/native-episode``
once the episode has settled, and every contact's request/response bytes are
in the MODEL_REQUEST / MODEL_RESPONSE records. So the replay
* classifies terminal delivery with the SAME validator the seal uses
  (:func:`rails.native_episode_receipt.validate_native_episode_delivery_receipt`,
  in its documented post-seal reader mode), and
* rebuilds the ``rails.core_client.RequestTiming`` records and the phase
  result objects the live runner would have handed to
  ``core.flight.runtime.FlightRuntime._canonical_output_rows``,
so the sealed row is rendered by that one canonical stage rather than by a
second copy of it. This is the same discipline
``analysis.native_commit_replay`` follows for COMMIT policies: read the
recorded custody, re-apply the registered code, never re-implement it.

Request ids are attempt-scoped (``rails.core_client`` mints
``f"{prefix}-{counter:04d}"`` against a per-client counter), so a recovery
attempt's own request ids restart at 1 and can repeat a predecessor request
id for a DIFFERENT sample. Custody is therefore decided by SAMPLE id: a kept
sample's contacts live only in the predecessor trace, a flown sample's
contacts only in the recovery trace, and the bundle verifier holds both
directions (``core.bundle.outputs``).
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

#: The manifest block a resumed attempt writes, and the only shape
#: ``core.bundle.verify_bundle`` accepts for one.
RESUME_PREDECESSOR_SCHEMA = "saea-resume-predecessor-attempt-v1"

#: The trace record-id suffix a settled native episode's receipt carries.
NATIVE_EPISODE_RECORD_SUFFIX = "/native-episode"


class ResumeRecoveryError(RuntimeError):
    """A resume-recovery cannot proceed: bad declaration, or unreadable custody."""


def kept_sample_ids_sha256(sample_ids: Sequence[str]) -> str:
    """Hash the sorted kept-row list exactly as the manifest records it."""

    ordered = sorted(str(sample_id) for sample_id in sample_ids)
    return hashlib.sha256(
        json.dumps(ordered, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class ResumeDeclaration:
    """What a recovery cell declares about the attempt it resumes."""

    attempt_id: str
    trace_sha256: str

    @classmethod
    def from_document(cls, document: object) -> "ResumeDeclaration":
        if not isinstance(document, Mapping) or set(document) != {
            "attempt_id", "trace_sha256",
        }:
            raise ResumeRecoveryError(
                "resume_from must declare exactly {'attempt_id', 'trace_sha256'}"
            )
        attempt_id = document["attempt_id"]
        trace_sha256 = document["trace_sha256"]
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise ResumeRecoveryError("resume_from.attempt_id must be a non-empty string")
        if not _is_sha256(trace_sha256):
            raise ResumeRecoveryError(
                "resume_from.trace_sha256 must be a 64-hex SHA-256 of the "
                "predecessor attempt's trace file"
            )
        return cls(attempt_id=attempt_id, trace_sha256=trace_sha256)


@dataclass(frozen=True)
class PredecessorContact:
    """One recorded model contact of the aborted attempt.

    ``text`` is the recorded response text. It is kept only so the replayed
    row can deliver the exact bytes the frozen core returned; nothing in this
    module ever prints, logs or hashes it into a receipt.
    """

    request_id: str
    sample_id: str
    request_sha256: str
    response_sha256: str | None = None
    response_text_sha256: str | None = None
    text: str | None = None
    latency_seconds: float = 0.0
    native_tool_calls: int | None = None

    @property
    def answered(self) -> bool:
        return self.text is not None


@dataclass(frozen=True)
class ReplayedEpisodeResult:
    """The in-memory shape ``FlightRuntime`` reads off a live phase result.

    Deliberately narrow: exactly the attributes
    ``_rows_from_phase_summaries`` and ``_canonical_output_rows`` read
    (``sample_id``, ``final_response_text``, ``contacts``,
    ``native_episode_receipt``, ``solver_group``). A replayed row that needed
    anything else would be a row this module must refuse rather than
    approximate.
    """

    sample_id: str
    final_response_text: str
    contacts: tuple[PredecessorContact, ...]
    native_episode_receipt: Mapping[str, object]
    solver_group: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ReplayedPhaseSummary:
    """One phase summary carrying the replayed results, in roster order."""

    results: tuple[ReplayedEpisodeResult, ...]
    controller_policy_id: str | None = None


@dataclass(frozen=True)
class PredecessorAttempt:
    """A scanned, model-free view of one aborted attempt's trace."""

    run_id: str
    attempt_id: str
    trace_path: Path
    trace_sha256: str
    contacts: Mapping[str, tuple[PredecessorContact, ...]]
    complete: Mapping[str, ReplayedEpisodeResult]
    incomplete: Mapping[str, str]
    record_count: int = 0
    _sample_order: tuple[str, ...] = field(default=())

    @property
    def complete_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.complete))

    @property
    def incomplete_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.incomplete))

    @property
    def started_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.contacts))

    def contact_count(self) -> int:
        return sum(len(items) for items in self.contacts.values())

    def replay(
        self, sample_ids: Sequence[str], *, controller_policy_id: str | None = None,
    ) -> tuple[tuple[ReplayedPhaseSummary, ...], tuple[object, ...]]:
        """Return ``(phase_summaries, timings)`` for ``sample_ids``.

        The timings are real :class:`rails.core_client.RequestTiming` records
        -- the same class the live client appends -- built from the recorded
        request/response identity hashes, in trace order, so the LAST timing
        of a sample is that sample's last contact exactly as it is live.
        """

        from ...rails.core_client import RequestTiming  # noqa: PLC0415 (cycle guard)

        requested = list(dict.fromkeys(str(sample_id) for sample_id in sample_ids))
        missing = [sample_id for sample_id in requested if sample_id not in self.complete]
        if missing:
            raise ResumeRecoveryError(
                f"{len(missing)} requested sample(s) are not COMPLETE in predecessor "
                f"attempt {self.attempt_id!r}, e.g. {missing[:5]}; a resume keeps every "
                "complete row and re-flies every other one -- it never selects"
            )
        keep = set(requested)
        results = tuple(
            self.complete[sample_id]
            for sample_id in self._sample_order
            if sample_id in keep
        )
        timings = tuple(
            RequestTiming(
                request_id=contact.request_id,
                sample_id=contact.sample_id,
                # The trace carries no wall-clock stamp for a contact (only
                # its COST latency), and nothing on the sealing path reads
                # this field. Recorded as empty rather than invented.
                started_at="",
                latency_seconds=contact.latency_seconds,
                request_sha256=contact.request_sha256,
                response_sha256=contact.response_sha256,
                response_text_sha256=contact.response_text_sha256,
                native_tool_calls=contact.native_tool_calls,
            )
            for sample_id in self._sample_order
            if sample_id in keep
            for contact in self.contacts[sample_id]
        )
        return (ReplayedPhaseSummary(results, controller_policy_id),), timings

    def manifest_block(
        self, kept_sample_ids: Sequence[str], *, flown: int, partial: int,
    ) -> dict[str, object]:
        """The ``predecessor_attempt`` block the resumed manifest declares."""

        kept = sorted(str(sample_id) for sample_id in kept_sample_ids)
        if len(set(kept)) != len(kept):
            raise ResumeRecoveryError("kept sample ids must be unique")
        return {
            "schema": RESUME_PREDECESSOR_SCHEMA,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "trace_path": str(self.trace_path),
            "trace_sha256": self.trace_sha256,
            "kept_sample_ids": kept,
            "kept_sample_ids_sha256": kept_sample_ids_sha256(kept),
            "counts": {"kept": len(kept), "flown": int(flown), "partial": int(partial)},
        }


def predecessor_trace_path(attempt_dir: Path, run_id: str) -> Path:
    return Path(attempt_dir) / f"{run_id}.trace.jsonl"


def _native_tool_calls(payload: Mapping[str, object]) -> int | None:
    """How many native tool calls a recorded wire response carried.

    Mirrors ``rails.core_client.FrozenCoreClient._dispatch_payload`` exactly:
    ``None`` when the choice message carries no ``tool_calls`` key (the model
    answered as text), otherwise the number of calls. Derived from the
    MODEL_WIRE_RESPONSE record, which ``core.model.request_types.
    wire_response_message`` already binds to ``CoreResponse.tool_calls``.
    """

    raw = payload.get("response_b64")
    if not isinstance(raw, str):
        return None
    try:
        document = json.loads(base64.b64decode(raw, validate=True).decode("utf-8"))
        message = document["choices"][0]["message"]
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
        return None
    if not isinstance(message, Mapping):
        return None
    calls = message.get("tool_calls")
    return len(calls) if isinstance(calls, list) else None


def _scan_trace(
    trace_path: Path, *, program_id: str | None,
) -> tuple[
    dict[str, list[PredecessorContact]],
    dict[str, Mapping[str, object]],
    list[str],
    int,
]:
    """One streaming pass over the trace. Never holds a request payload."""

    requests: dict[str, dict[str, object]] = {}
    responses: dict[str, tuple[str, str, str]] = {}
    latency: dict[str, float] = {}
    tool_calls: dict[str, int | None] = {}
    episodes: dict[str, Mapping[str, object]] = {}
    order: list[str] = []
    per_sample: dict[str, list[str]] = {}
    record_count = 0
    suffix = (
        NATIVE_EPISODE_RECORD_SUFFIX
        if program_id is None
        else f"/{program_id}{NATIVE_EPISODE_RECORD_SUFFIX}"
    )
    try:
        handle = trace_path.open("r", encoding="utf-8")
    except OSError as error:
        raise ResumeRecoveryError(f"cannot read predecessor trace {trace_path}: {error}") from error
    with handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record_count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ResumeRecoveryError(
                    f"predecessor trace {trace_path} line {number} is malformed: {error}"
                ) from error
            if not isinstance(record, Mapping):
                raise ResumeRecoveryError(
                    f"predecessor trace {trace_path} line {number} is not an object"
                )
            channel = record.get("channel")
            record_id = record.get("record_id")
            payload = record.get("payload")
            if not isinstance(record_id, str) or not isinstance(payload, Mapping):
                raise ResumeRecoveryError(
                    f"predecessor trace {trace_path} line {number} lacks record_id/payload"
                )
            if channel == "MODEL_REQUEST" and record_id.endswith("/request"):
                request_id = record_id[: -len("/request")]
                inner = payload.get("payload")
                if not isinstance(inner, Mapping):
                    continue
                sample_id = inner.get("sample_id")
                if not isinstance(sample_id, str) or not sample_id:
                    continue
                if request_id in requests:
                    raise ResumeRecoveryError(
                        f"predecessor trace repeats request id {request_id!r}"
                    )
                requests[request_id] = {
                    "sample_id": sample_id,
                    "request_sha256": payload.get("payload_sha256"),
                }
                if sample_id not in per_sample:
                    per_sample[sample_id] = []
                    order.append(sample_id)
                per_sample[sample_id].append(request_id)
            elif channel == "MODEL_RESPONSE" and record_id.endswith("/response"):
                request_id = record_id[: -len("/response")]
                text = payload.get("text")
                if not isinstance(text, str):
                    continue
                responses[request_id] = (
                    payload.get("response_sha256"),
                    payload.get("response_text_sha256"),
                    text,
                )
            elif channel == "MODEL_WIRE_RESPONSE" and record_id.endswith("/wire-response"):
                tool_calls[record_id[: -len("/wire-response")]] = _native_tool_calls(payload)
            elif channel == "COST" and record_id.endswith("/cost"):
                seconds = payload.get("latency_seconds")
                if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
                    latency[record_id[: -len("/cost")]] = float(seconds)
            elif channel == "USE" and record_id.endswith(suffix):
                receipt = payload.get("use_native_episode")
                sample_id = record_id[: -len(suffix)]
                if isinstance(receipt, Mapping) and sample_id:
                    if sample_id in episodes:
                        raise ResumeRecoveryError(
                            f"predecessor trace carries two episode receipts for "
                            f"sample {sample_id!r}"
                        )
                    episodes[sample_id] = receipt

    contacts: dict[str, list[PredecessorContact]] = {}
    for sample_id in order:
        items = []
        for request_id in per_sample[sample_id]:
            meta = requests[request_id]
            answer = responses.get(request_id)
            items.append(
                PredecessorContact(
                    request_id=request_id,
                    sample_id=sample_id,
                    request_sha256=meta["request_sha256"],
                    response_sha256=None if answer is None else answer[0],
                    response_text_sha256=None if answer is None else answer[1],
                    text=None if answer is None else answer[2],
                    latency_seconds=latency.get(request_id, 0.0),
                    native_tool_calls=tool_calls.get(request_id),
                )
            )
        contacts[sample_id] = items
    return contacts, episodes, order, record_count


#: Episode-receipt blocks whose ``contacts`` arrays are per-contact ANNOTATIONS
#: keyed by the agent ``contact_id`` -- never wire contacts, so they carry no
#: ``request_id`` and cannot be checked against a MODEL_REQUEST record:
#:
#: * ``context_fit`` -- ``rails.runner``'s compact-or-abstain context-fit
#:   custody (one row per contact: contact id, role id, compaction);
#: * ``solver_citations`` -- ``rails.solver_citation``'s cited-answer custody
#:   (one record per cited contact: ids and digests only).
#:
#: The wire contacts they annotate are already claimed, with their request,
#: response and response-text digests, by ``role_visits[].execution_receipt``
#: and ``accepted_solver_receipt``, which the walk still verifies in full.
#: Walking into these two blocks made every row of a cell carrying either one
#: INCOMPLETE ("names contact None"), so a resume kept nothing (2026-09-28,
#: the COMP-1 arm: 0 of 471 settled rows classified COMPLETE).
NON_WIRE_CONTACT_BLOCKS = frozenset({"context_fit", "solver_citations"})


def _receipt_contacts(receipt: Mapping[str, object]) -> list[Mapping[str, object]]:
    """Every WIRE contact the episode receipt itself claims, in receipt order.

    The :data:`NON_WIRE_CONTACT_BLOCKS` annotation blocks are skipped by key;
    every other ``contacts`` array anywhere in the receipt is still claimed.
    """

    found: list[Mapping[str, object]] = []

    def walk(node: object) -> None:
        if isinstance(node, Mapping):
            raw = node.get("contacts")
            if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
                found.extend(item for item in raw if isinstance(item, Mapping))
            for key, value in node.items():
                if key in NON_WIRE_CONTACT_BLOCKS:
                    continue
                walk(value)
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            for item in node:
                walk(item)

    walk(receipt)
    return found


def _classify(
    sample_id: str,
    receipt: Mapping[str, object] | None,
    contacts: Sequence[PredecessorContact],
) -> tuple[ReplayedEpisodeResult | None, str | None]:
    """COMPLETE (a replayed result) or INCOMPLETE (the reason), never both."""

    from ...rails.native_episode_receipt import (  # noqa: PLC0415 (cycle guard)
        validate_native_episode_delivery_receipt,
    )

    if receipt is None:
        return None, "the episode emitted no terminal receipt"
    unanswered = [contact.request_id for contact in contacts if not contact.answered]
    if unanswered:
        return None, (
            f"{len(unanswered)} contact(s) have no recorded model response, "
            f"e.g. {unanswered[:3]}"
        )
    by_request = {contact.request_id: contact for contact in contacts}
    try:
        delivery = validate_native_episode_delivery_receipt(
            receipt, error_type=ResumeRecoveryError,
        )
    except ResumeRecoveryError as error:
        return None, f"terminal delivery is unreadable: {error}"
    for claimed in _receipt_contacts(receipt):
        request_id = claimed.get("request_id")
        recorded = by_request.get(request_id) if isinstance(request_id, str) else None
        if recorded is None:
            return None, (
                f"the episode receipt names contact {request_id!r}, which this "
                "sample has no request record for"
            )
        for name in ("request_sha256", "response_sha256", "response_text_sha256"):
            if claimed.get(name) != getattr(recorded, name):
                return None, (
                    f"contact {request_id!r} {name} in the episode receipt differs "
                    "from the recorded request/response bytes"
                )
    solver_receipt = delivery.solver_receipt
    if isinstance(solver_receipt, Mapping):
        raw = solver_receipt.get("contacts")
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) > 1:
            # A grouped Solver visit (module M2) delivers a COMMIT policy's
            # aggregate, and its per-sample vote custody (``solver_group``)
            # is NOT in the trace -- only the compact episode receipt is. The
            # delivered bytes therefore cannot be re-derived here, so the row
            # is re-flown rather than approximated.
            return None, (
                "the delivered Solver visit is grouped; its commit custody is not "
                "in the trace, so this row is re-flown rather than replayed"
            )
    final_contact = delivery.final_contact
    if delivery.kind == "abstention":
        final_text = ""
    else:
        recorded = by_request.get(final_contact.get("request_id"))
        if recorded is None or recorded.text is None:
            return None, "the delivered contact has no recorded model response"
        if (
            hashlib.sha256(recorded.text.encode("utf-8")).hexdigest()
            != final_contact.get("response_text_sha256")
        ):
            return None, "the delivered response text does not match its recorded hash"
        final_text = recorded.text
    return (
        ReplayedEpisodeResult(
            sample_id=sample_id,
            final_response_text=final_text,
            contacts=tuple(contacts),
            native_episode_receipt=dict(receipt),
        ),
        None,
    )


def read_predecessor_attempt(
    *,
    run_id: str,
    attempt_id: str,
    attempt_dir: Path,
    expected_trace_sha256: str | None = None,
    program_id: str | None = None,
) -> PredecessorAttempt:
    """Scan one aborted attempt's trace; zero model contact, read-only.

    ``expected_trace_sha256`` is the declaration's pin: the bytes on disk must
    hash to it, or the resume refuses. ``None`` measures without comparing,
    which is what a read-only audit of an attempt whose hash is not yet
    pinned needs.
    """

    attempt_dir = Path(attempt_dir)
    trace_path = predecessor_trace_path(attempt_dir, run_id)
    if not trace_path.is_file():
        raise ResumeRecoveryError(
            f"predecessor attempt {attempt_id!r} has no trace at {trace_path}"
        )
    digest = hashlib.sha256()
    with trace_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    trace_sha256 = digest.hexdigest()
    if expected_trace_sha256 is not None and trace_sha256 != expected_trace_sha256:
        raise ResumeRecoveryError(
            f"predecessor trace {trace_path} hashes to {trace_sha256}, not the "
            f"declared {expected_trace_sha256}; a resume-recovery applies only when "
            "the predecessor's recorded bytes are exactly what was declared"
        )
    contacts, episodes, order, record_count = _scan_trace(trace_path, program_id=program_id)
    unknown = sorted(set(episodes) - set(contacts))
    if unknown:
        raise ResumeRecoveryError(
            f"predecessor trace carries {len(unknown)} episode receipt(s) for sample(s) "
            f"with no request record, e.g. {unknown[:5]}"
        )
    complete: dict[str, ReplayedEpisodeResult] = {}
    incomplete: dict[str, str] = {}
    for sample_id in order:
        result, reason = _classify(sample_id, episodes.get(sample_id), contacts[sample_id])
        if result is None:
            incomplete[sample_id] = str(reason)
        else:
            complete[sample_id] = result
    return PredecessorAttempt(
        run_id=run_id,
        attempt_id=attempt_id,
        trace_path=trace_path,
        trace_sha256=trace_sha256,
        contacts={key: tuple(value) for key, value in contacts.items()},
        complete=complete,
        incomplete=incomplete,
        record_count=record_count,
        _sample_order=tuple(order),
    )


__all__ = [
    "NATIVE_EPISODE_RECORD_SUFFIX",
    "NON_WIRE_CONTACT_BLOCKS",
    "RESUME_PREDECESSOR_SCHEMA",
    "PredecessorAttempt",
    "PredecessorContact",
    "ReplayedEpisodeResult",
    "ReplayedPhaseSummary",
    "ResumeDeclaration",
    "ResumeRecoveryError",
    "kept_sample_ids_sha256",
    "predecessor_trace_path",
    "read_predecessor_attempt",
]
