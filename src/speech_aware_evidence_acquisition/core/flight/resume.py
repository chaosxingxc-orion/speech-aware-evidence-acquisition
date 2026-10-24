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
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

#: The manifest block a resumed attempt writes, and the only shape
#: ``core.bundle.verify_bundle`` accepts for one.
RESUME_PREDECESSOR_SCHEMA = "saea-resume-predecessor-attempt-v1"

#: The trace record-id suffix a settled native episode's receipt carries.
NATIVE_EPISODE_RECORD_SUFFIX = "/native-episode"

#: E4-1 (2026-09-29): the per-contact USE record ``<request_id>/native-role-
#: contact`` whose ``use_role_id`` names the role that made the contact, and
#: the role id the post-accept relisten stage's shadow contacts carry
#: (``rails.runner._dispatch_relisten_contact``).
NATIVE_ROLE_CONTACT_RECORD_SUFFIX = "/native-role-contact"
RELISTEN_ROLE_ID = "relisten"


def _relisten_kind(schema_name: object) -> str | None:
    from ...rails.relisten import CONTACT_KIND_BY_SCHEMA_NAME  # noqa: PLC0415

    return CONTACT_KIND_BY_SCHEMA_NAME.get(schema_name) if isinstance(schema_name, str) else None


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
    trace_sha256: str | None = None
    #: Mode B (owner decision 309, 2026-10-14): the pin of the predecessor's
    #: ``<run_id>.rows.ckpt.jsonl`` instead of its trace. Exactly one of
    #: ``trace_sha256`` (mode A, trace replay) and ``checkpoint_sha256`` (mode B,
    #: checkpoint replay) is declared.
    checkpoint_sha256: str | None = None

    @property
    def mode(self) -> str:
        return "checkpoint" if self.checkpoint_sha256 is not None else "trace"

    @classmethod
    def from_document(cls, document: object) -> "ResumeDeclaration":
        if not isinstance(document, Mapping) or set(document) not in (
            {"attempt_id", "trace_sha256"}, {"attempt_id", "checkpoint_sha256"},
        ):
            raise ResumeRecoveryError(
                "resume_from must declare exactly {'attempt_id', 'trace_sha256'} "
                "(mode A, trace replay) or {'attempt_id', 'checkpoint_sha256'} "
                "(mode B, checkpoint replay)"
            )
        attempt_id = document["attempt_id"]
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise ResumeRecoveryError("resume_from.attempt_id must be a non-empty string")
        if "checkpoint_sha256" in document:
            checkpoint_sha256 = document["checkpoint_sha256"]
            if not _is_sha256(checkpoint_sha256):
                raise ResumeRecoveryError(
                    "resume_from.checkpoint_sha256 must be a 64-hex SHA-256 of the "
                    "predecessor attempt's row checkpoint file"
                )
            return cls(attempt_id=attempt_id, checkpoint_sha256=checkpoint_sha256)
        trace_sha256 = document["trace_sha256"]
        if not _is_sha256(trace_sha256):
            raise ResumeRecoveryError(
                "resume_from.trace_sha256 must be a 64-hex SHA-256 of the "
                "predecessor attempt's trace file"
            )
        return cls(attempt_id=attempt_id, trace_sha256=trace_sha256)


def resume_declarations_from_document(
    document: object,
) -> tuple[ResumeDeclaration, ...]:
    """Normalize a ``resume_from`` config value into an ordered declaration list.

    E10d (2026-09-29, multi-predecessor seal-only completion): ``resume_from``
    now accepts either the original single mapping (``{"attempt_id",
    "trace_sha256"}``) or a non-empty, ordered list of such mappings -- one per
    pinned predecessor attempt of THIS run id. The order is significant: it is
    the declared order a conflict is reported against (see
    :class:`MergedPredecessors`), never a priority a row is silently resolved
    by.

    Refuses a document that is neither shape, an empty list, or a list naming
    the same predecessor ``attempt_id`` twice -- a predecessor is named once
    or not at all.
    """

    if isinstance(document, Mapping):
        return (ResumeDeclaration.from_document(document),)
    if isinstance(document, Sequence) and not isinstance(document, (str, bytes)):
        if not document:
            raise ResumeRecoveryError(
                "resume_from must declare at least one predecessor attempt"
            )
        declarations = tuple(
            ResumeDeclaration.from_document(item) for item in document
        )
        attempt_ids = [declaration.attempt_id for declaration in declarations]
        if len(set(attempt_ids)) != len(attempt_ids):
            duplicate = sorted(
                {attempt_id for attempt_id in attempt_ids if attempt_ids.count(attempt_id) > 1}
            )
            raise ResumeRecoveryError(
                f"resume_from names the same predecessor attempt twice: {duplicate}"
            )
        return declarations
    raise ResumeRecoveryError(
        "resume_from must be a mapping {'attempt_id', 'trace_sha256'} or a "
        "non-empty list of such mappings"
    )


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
    #: E4-1 (2026-09-29): the role the contact's ``USE <request_id>/native-
    #: role-contact`` record names, and -- for a relisten contact only -- its
    #: kind (``"blind"``/``"confirm"``) read off the request's pinned
    #: response-format schema name. ``None`` when the trace records neither.
    role_id: str | None = None
    relisten_kind: str | None = None
    #: P-SV-1 seal fix (2026-09-29): ``(evidence_id, sha256(content))`` of each
    #: ``perception-branch-presentation:<branch_id>`` item the recorded REQUEST
    #: carried -- digests only, the custody a Perception-branch replay needs to
    #: re-derive a branch's presentation outcome. Empty for every other contact.
    presentation_blocks: tuple[tuple[str, str], ...] = ()
    #: E10e (2026-09-29, seal-only read gap): this ONE contact's own recorded
    #: ``COST`` payload fields -- ``audio_seconds``/``prompt_tokens``/
    #: ``completion_tokens`` -- the same per-request accounting
    #: ``core.model.adapter.FrozenCoreAdapter`` sums into
    #: ``cost_summary()``. ``None`` when the trace carries no ``COST`` record
    #: for this request (never assumed zero, so a summation over these stays
    #: honest about what it actually added).
    audio_seconds: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    #: NX-T R1 seal fix (2026-10-15): the three decoding fields a thinking-policy arm moves (``thinking_budget_tokens``,
    #: ``chat_template_kwargs``, ``max_tokens``) as the recorded REQUEST carried them, and the recorded wire response's
    #: ``finish_reason`` -- the custody the offline seal replay needs to run the bundle's thinking-policy wire check (v5 receipts)
    #: and the absent-Solver-column check over a predecessor trace. ``None`` when the trace records neither.
    decoding_view: Mapping[str, object] | None = None
    finish_reason: str | None = None

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

    ``final_response_text`` is the DELIVERED text: the delivered contact's
    recorded response, or -- when the receipt carries a ``deliver_normaliser``
    block -- that rule's reproduced output over it.

    ``relisten`` (E4-1, 2026-09-29) is the row's ``saea-relisten-v1`` receipt
    re-derived from its recorded relisten contacts
    (``rails.relisten.replay_relisten_receipt``) when the cell arms
    ``native_episode.relisten``; ``contacts`` then excludes those shadow
    contacts, exactly as a live result's ``contacts`` does (the live runner
    never adds a relisten contact there), so
    ``FlightRuntime._result_contact_count`` counts each contact once.
    """

    sample_id: str
    final_response_text: str
    contacts: tuple[PredecessorContact, ...]
    native_episode_receipt: Mapping[str, object]
    solver_group: Mapping[str, object] | None = None
    relisten: Mapping[str, object] | None = None


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

    def cost_totals(self) -> dict[str, object]:
        """This attempt's OWN real spend, summed over EVERY contact of EVERY
        started sample -- kept, incomplete and (for a partial resume)
        subsequently re-flown alike, exactly the total
        ``core.model.adapter.FrozenCoreAdapter.cost_summary()`` would have
        reported had this attempt itself reached ``seal()`` (E10e,
        2026-09-29, seal-only read gap: an ABORTED predecessor -- the
        ordinary case a resume-recovery exists for -- never reaches seal(),
        so it never writes a ``<run_id>.generation-manifest.json`` or
        ``<run_id>.run-manifest.json`` of its own; this attempt's TRACE,
        already scanned into :attr:`contacts`, is the one place its real
        cost survives).

        Every field sums only the contacts that actually carry it (a
        ``COST`` record this module could not read is skipped, not counted
        as zero), so this is a lower bound when the trace is incomplete,
        never a silently wrong total.
        """

        totals = {
            "calls_used": 0,
            "audio_seconds_used": 0.0,
            "latency_seconds_total": 0.0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "tool_calls": 0,
        }
        for contacts in self.contacts.values():
            for contact in contacts:
                totals["calls_used"] += 1
                totals["audio_seconds_used"] += contact.audio_seconds or 0.0
                totals["latency_seconds_total"] += contact.latency_seconds
                totals["prompt_tokens_total"] += contact.prompt_tokens or 0
                totals["completion_tokens_total"] += contact.completion_tokens or 0
                totals["tool_calls"] += contact.native_tool_calls or 0
        return totals

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


@dataclass(frozen=True)
class MergedPredecessors:
    """The union of N pinned predecessor attempts' COMPLETE rows (E10d).

    Every predecessor's :attr:`PredecessorAttempt.complete_sample_ids` set
    must be pairwise disjoint from every other predecessor's -- checked once,
    here, at construction, over every pair. A sample COMPLETE in two
    predecessors is a conflict and the merge refuses outright (naming both
    attempts) rather than keeping either one: silently preferring the first
    declared occurrence would be a selection, exactly what a resume-recovery
    must never make (module docstring).

    Once a merge exists, classification is total and stable: a kept sample's
    single occurrence (the only one the disjointness check above allows) IS
    its "first complete occurrence in the declared order" -- the predecessor
    at the smallest index in :attr:`predecessors` whose own
    ``complete_sample_ids`` contains it. :meth:`origin` and
    :meth:`manifest_blocks` both read the declared predecessor order, never
    an incidental dict/set order.

    Exposes the same read surface :class:`PredecessorAttempt` gives a
    single-predecessor resume (:attr:`complete_sample_ids`, :attr:`incomplete`,
    :meth:`replay`) so ``core.flight.runtime.FlightRuntime`` can treat one
    predecessor and N predecessors identically everywhere except where the
    manifest block itself must name every predecessor (:meth:`manifest_blocks`).
    """

    predecessors: tuple[PredecessorAttempt, ...]

    def __post_init__(self) -> None:
        if not self.predecessors:
            raise ResumeRecoveryError(
                "a merge requires at least one predecessor attempt"
            )
        owner: dict[str, str] = {}
        for predecessor in self.predecessors:
            for sample_id in predecessor.complete_sample_ids:
                held_by = owner.get(sample_id)
                if held_by is not None:
                    raise ResumeRecoveryError(
                        f"sample {sample_id!r} is COMPLETE in two predecessor "
                        f"attempts, {held_by!r} and {predecessor.attempt_id!r}; a "
                        "multi-predecessor resume requires pairwise non-overlapping "
                        "complete rows -- refusing rather than choosing one"
                    )
                owner[sample_id] = predecessor.attempt_id

    @property
    def complete_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            sample_id
            for predecessor in self.predecessors
            for sample_id in predecessor.complete_sample_ids
        ))

    @property
    def incomplete(self) -> Mapping[str, str]:
        """Every predecessor's own INCOMPLETE reasons, merged.

        A sample started-but-not-COMPLETE in more than one predecessor keeps
        the first (declared-order) reason -- an arbitrary but stable tie
        break over report text only; it decides nothing about custody (a row
        is only ever KEPT through :attr:`complete_sample_ids`, which the
        disjointness check above already guarantees is unambiguous).
        """

        merged: dict[str, str] = {}
        for predecessor in self.predecessors:
            for sample_id, reason in predecessor.incomplete.items():
                merged.setdefault(sample_id, reason)
        return merged

    def origin(self, sample_id: str) -> PredecessorAttempt:
        """The one predecessor whose COMPLETE set kept ``sample_id``."""

        for predecessor in self.predecessors:
            if sample_id in predecessor.complete:
                return predecessor
        raise ResumeRecoveryError(
            f"sample {sample_id!r} is not COMPLETE in any declared predecessor"
        )

    def cost_totals(self) -> dict[str, object]:
        """The sum, field by field, of every declared predecessor's OWN
        :meth:`PredecessorAttempt.cost_totals` (E10e, 2026-09-29) -- the real
        spend a seal-only completion's ``<run_id>.generation-manifest.json``
        reports in place of this attempt's own (honestly zero) cost."""

        totals = {
            "calls_used": 0,
            "audio_seconds_used": 0.0,
            "latency_seconds_total": 0.0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "tool_calls": 0,
        }
        for predecessor in self.predecessors:
            for key, value in predecessor.cost_totals().items():
                totals[key] += value
        return totals

    def replay(
        self, sample_ids: Sequence[str], *, controller_policy_id: str | None = None,
    ) -> tuple[tuple[ReplayedPhaseSummary, ...], tuple[object, ...]]:
        """Return ``(phase_summaries, timings)`` for ``sample_ids``, merged.

        ``FlightRuntime._rows_from_phase_summaries`` requires every phase
        summary it is handed to describe the SAME sample roster (it fails
        closed otherwise -- "every phase of a program must run the same
        whole roster"), so this never hands back one ``ReplayedPhaseSummary``
        per predecessor. Instead it replays each predecessor's own subset
        through that predecessor's own (already-verified)
        :meth:`PredecessorAttempt.replay`, and concatenates the resulting
        single-summary results into ONE merged summary -- exactly the shape
        a one-predecessor resume already returns, so the seal stage sees no
        difference between one predecessor and many.
        """

        requested = list(dict.fromkeys(str(sample_id) for sample_id in sample_ids))
        available = set(self.complete_sample_ids)
        missing = [sample_id for sample_id in requested if sample_id not in available]
        if missing:
            raise ResumeRecoveryError(
                f"{len(missing)} requested sample(s) are not COMPLETE in any "
                f"declared predecessor, e.g. {missing[:5]}"
            )
        results: list[object] = []
        timings: list[object] = []
        for predecessor in self.predecessors:
            own = [
                sample_id for sample_id in requested
                if sample_id in predecessor.complete
            ]
            if not own:
                continue
            (summary,), part_timings = predecessor.replay(
                own, controller_policy_id=controller_policy_id,
            )
            results.extend(summary.results)
            timings.extend(part_timings)
        return (ReplayedPhaseSummary(tuple(results), controller_policy_id),), tuple(timings)

    def manifest_blocks(
        self, kept_sample_ids: Sequence[str], *, flown: int, partial: int,
    ) -> tuple[dict[str, object], ...]:
        """One ``predecessor_attempt``-shaped block PER predecessor that kept
        at least one of ``kept_sample_ids`` -- the list a multi-predecessor
        manifest declares under ``predecessor_attempts``. ``flown``/``partial``
        describe this resuming attempt as a whole (there is only one flown
        roster, shared across every predecessor's block) exactly as they do
        for a single-predecessor :meth:`PredecessorAttempt.manifest_block`.
        """

        kept = set(str(sample_id) for sample_id in kept_sample_ids)
        blocks = []
        for predecessor in self.predecessors:
            own_kept = sorted(
                sample_id
                for sample_id in predecessor.complete_sample_ids
                if sample_id in kept
            )
            if not own_kept:
                continue
            blocks.append(
                predecessor.manifest_block(own_kept, flown=flown, partial=partial)
            )
        return tuple(blocks)


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


def _presentation_blocks(request_payload: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    """``(evidence_id, sha256(content))`` of every Perception-branch
    presentation item a recorded request's ``supplied_evidence`` carries.

    The live runner seals ``contrast_block_sha256`` as the sha256 of the
    block's text, and the wire keeps that text as the item's ``content``.
    Only the digest leaves this function; the text is never held.
    """

    from ...rails.supply_variants import (  # noqa: PLC0415 (cycle guard)
        PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX,
    )

    items = request_payload.get("supplied_evidence")
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        return ()
    found: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        evidence_id = item.get("evidence_id")
        content = item.get("content")
        if (
            isinstance(evidence_id, str)
            and evidence_id.startswith(PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX)
            and isinstance(content, str)
        ):
            found.append(
                (evidence_id, hashlib.sha256(content.encode("utf-8")).hexdigest())
            )
    return tuple(found)


#: The decoding fields ``core.bundle.outputs._THINKING_WIRE_KEYS`` compares per node (restated: this module never imports the bundle).
_THINKING_DECODING_KEYS = ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens")


def _sampling_contact_ids(row: object, axis: str) -> list[object] | None:
    """The ordered sample contact ids of a v6 branch row's ``sampling[axis]`` record, or ``None`` when the row declares none."""

    sampling = row.get("sampling") if isinstance(row, Mapping) else None
    record = sampling.get(axis) if isinstance(sampling, Mapping) else None
    samples = record.get("samples") if isinstance(record, Mapping) else None
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
        return None
    return [sample.get("contact_id") if isinstance(sample, Mapping) else None for sample in samples]


def _is_perception_branch_solver_fanout(
    receipt: Mapping[str, object], solver_receipt: Mapping[str, object],
) -> bool:
    """True when a multi-contact delivered Solver visit is a LEVEL-2
    Perception-branch fan-out, not a grouped (M2) Solver commit.

    At level 2 the Solver's first visit spends one contact per declared
    branch, delivering branch A last (``rails.runner``'s level-2 fan-out,
    design section 3 "Level 2"): the delivered text is A's own recorded
    response, exactly one contact, with no vote or aggregate to re-derive. It
    is recognised only by its exact custody: the visit's contacts are the
    branches' own ``solver_contact_id`` values in declared order and the final
    (delivered) contact is A's. Anything else keeps the grouped refusal.
    Before 2026-09-29 every such row was INCOMPLETE, so a seal-only replay of
    P-SV-1 would have kept none of its 1,045 first-visit-accepted rows.
    """

    block = receipt.get("perception_branches")
    if not isinstance(block, Mapping) or block.get("level") != 2:
        return False
    branches = block.get("branches")
    if not isinstance(branches, Sequence) or isinstance(branches, (str, bytes)) or not branches:
        return False
    declared: list[object] = []
    for row in branches:
        samples = _sampling_contact_ids(row, "solver_samples")
        if samples is not None:
            # Decision 338 (receipt v6): a ``solver_samples`` branch spends n consecutive Solver contacts, sample 0 first and
            # named by the row's own solver_contact_id.
            if not samples or samples[0] != row.get("solver_contact_id"):
                return False
            declared.extend(samples)
        else:
            declared.append(row.get("solver_contact_id") if isinstance(row, Mapping) else None)
    contacts = solver_receipt.get("contacts")
    final = solver_receipt.get("final_contact")
    visit = [
        contact.get("agent_contact_id") if isinstance(contact, Mapping) else None
        for contact in contacts
    ] if isinstance(contacts, Sequence) else []
    return (
        all(isinstance(value, str) and value for value in declared)
        and visit == declared
        and isinstance(final, Mapping)
        and final.get("agent_contact_id") == declared[-1]
    )


def _replay_perception_branches(
    receipt: Mapping[str, object], contacts: Sequence[PredecessorContact],
) -> tuple[Mapping[str, object] | None, str | None]:
    """Re-derive a row's ``perception_branches`` block from its recorded
    contacts (P-SV-1 seal fix, 2026-09-29).

    The block IS persisted in the trace (inside the compact episode receipt,
    unlike E4-1's in-memory relisten receipt), but a block sealed before the
    fix carries the old verbatim candidate lists (a repeated intent refused at
    seal, I7v) and, at level 2, a dropped presentation outcome. The replay
    rebuilds it under receipt schema v2 from the trace itself
    (``rails.supply_variants.replay_perception_branch_block``): the agent
    contact ids the receipt names resolve, through the receipt's own
    ``role_visits`` custody, to recorded request ids, whose recorded response
    text and request presentation digests re-derive every note and
    presentation field. Any contact that cannot be accounted for returns a
    reason and the row is INCOMPLETE (re-flown), never approximated.
    """

    from ...rails.supply_variants import (  # noqa: PLC0415 (cycle guard)
        PerceptionBranchError,
        PerceptionBranchReplayContact,
        replay_perception_branch_block,
    )

    by_request = {contact.request_id: contact for contact in contacts}
    by_agent: dict[str, PerceptionBranchReplayContact] = {}
    for claimed in _receipt_contacts(receipt):
        agent_id = claimed.get("agent_contact_id")
        request_id = claimed.get("request_id")
        recorded = by_request.get(request_id) if isinstance(request_id, str) else None
        if not isinstance(agent_id, str) or recorded is None:
            continue
        replay_contact = PerceptionBranchReplayContact(
            request_sha256=recorded.request_sha256,
            response_text_sha256=recorded.response_text_sha256,
            text=recorded.text,
            presentation_block_sha256=dict(recorded.presentation_blocks),
        )
        if by_agent.setdefault(agent_id, replay_contact) != replay_contact:
            return None, (
                f"agent contact {agent_id!r} names two different recorded contacts"
            )
    try:
        block = replay_perception_branch_block(
            receipt["perception_branches"], contacts=by_agent,
        )
    except PerceptionBranchError as error:
        return None, f"the perception-branch receipt cannot be re-derived: {error}"
    return block, None


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
    #: E10e (2026-09-29): the same ``COST`` payload's other accounting
    #: fields, keyed by request id exactly as ``latency`` already is.
    audio_seconds: dict[str, float] = {}
    prompt_tokens: dict[str, int] = {}
    completion_tokens: dict[str, int] = {}
    tool_calls: dict[str, int | None] = {}
    finish_reasons: dict[str, str] = {}
    roles: dict[str, str] = {}
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
                decoding = inner.get("decoding_params")
                response_format = (
                    decoding.get("response_format") if isinstance(decoding, Mapping) else None
                )
                schema = (
                    response_format.get("json_schema")
                    if isinstance(response_format, Mapping) else None
                )
                requests[request_id] = {
                    "sample_id": sample_id,
                    "request_sha256": payload.get("payload_sha256"),
                    "schema_name": (
                        schema.get("name") if isinstance(schema, Mapping) else None
                    ),
                    "presentation_blocks": _presentation_blocks(inner),
                    "decoding_view": (
                        {key: decoding.get(key) for key in _THINKING_DECODING_KEYS}
                        if isinstance(decoding, Mapping) else None
                    ),
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
                finish = payload.get("finish_reason")
                if isinstance(finish, str) and finish:
                    finish_reasons[record_id[: -len("/wire-response")]] = finish
            elif channel == "COST" and record_id.endswith("/cost"):
                request_id = record_id[: -len("/cost")]
                seconds = payload.get("latency_seconds")
                if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
                    latency[request_id] = float(seconds)
                audio = payload.get("audio_seconds")
                if isinstance(audio, (int, float)) and not isinstance(audio, bool):
                    audio_seconds[request_id] = float(audio)
                prompt = payload.get("prompt_tokens")
                if isinstance(prompt, int) and not isinstance(prompt, bool):
                    prompt_tokens[request_id] = prompt
                completion = payload.get("completion_tokens")
                if isinstance(completion, int) and not isinstance(completion, bool):
                    completion_tokens[request_id] = completion
            elif channel == "USE" and record_id.endswith(NATIVE_ROLE_CONTACT_RECORD_SUFFIX):
                role_id = payload.get("use_role_id")
                if isinstance(role_id, str) and role_id:
                    roles[record_id[: -len(NATIVE_ROLE_CONTACT_RECORD_SUFFIX)]] = role_id
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
                    audio_seconds=audio_seconds.get(request_id),
                    prompt_tokens=prompt_tokens.get(request_id),
                    completion_tokens=completion_tokens.get(request_id),
                    role_id=roles.get(request_id),
                    relisten_kind=(
                        _relisten_kind(meta.get("schema_name"))
                        if roles.get(request_id) == RELISTEN_ROLE_ID else None
                    ),
                    presentation_blocks=meta.get("presentation_blocks", ()),
                    decoding_view=meta.get("decoding_view"),
                    finish_reason=finish_reasons.get(request_id),
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
    relisten_config: object = None,
) -> tuple[ReplayedEpisodeResult | None, str | None]:
    """COMPLETE (a replayed result) or INCOMPLETE (the reason), never both.

    ``relisten_config`` is the cell's parsed ``rails.relisten.RelistenConfig``
    when it arms ``native_episode.relisten`` (E4-1, 2026-09-29), else
    ``None``; see :class:`ReplayedEpisodeResult`'s ``relisten``.
    """

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
        if (
            isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) > 1
            and not _is_perception_branch_solver_fanout(receipt, solver_receipt)
        ):
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
        normalisation = receipt.get("deliver_normaliser")
        if normalisation is not None:
            # 2026-09-29 (COMP-1 resume attempt 3 seal abort): a row whose
            # episode ran the delivery-time normaliser node (E11) delivered
            # the node's OUTPUT, not the accepted contact's raw response. The
            # live runner (``rails.runner``) replaces ``final_text`` with the
            # normaliser output before it becomes ``final_response_text``, and
            # the seal binds that text to the receipt's ``output_sha256``. The
            # replay therefore re-applies the SAME registered rule to the
            # recorded response -- never a copy of it -- and keeps the row
            # only when the rule reproduces the recorded output digest.
            final_text, reason = _replay_delivery_normalisation(normalisation, final_text)
            if final_text is None:
                return None, reason
    # P-SV-1 (2026-09-29): a branched Perception row's ``perception_branches``
    # block is re-derived from the recorded contacts under receipt schema v2.
    if "perception_branches" in receipt:
        branches_block, reason = _replay_perception_branches(receipt, contacts)
        if branches_block is None:
            return None, reason
        receipt = {**receipt, "perception_branches": branches_block}
    # E4-1 (2026-09-29): the post-accept relisten stage's SHADOW contacts. The
    # live row carries its ``saea-relisten-v1`` receipt only in memory until
    # the seal writes it, so a replay that dropped it would seal the row
    # without its shadow columns and leave its trailing relisten contacts
    # unexplained. Re-derive it from the recorded contacts with the runner's
    # own walk, or re-fly the row -- never approximate.
    relisten_contacts = [
        contact for contact in contacts if contact.role_id == RELISTEN_ROLE_ID
    ]
    relisten_receipt = None
    if relisten_config is None:
        if relisten_contacts:
            return None, (
                f"{len(relisten_contacts)} relisten contact(s) are recorded but the cell "
                "declares no native_episode.relisten"
            )
    elif delivery.kind in {"abstention", "context-abstention"}:
        if relisten_contacts:
            return None, "an abstention row records relisten contacts"
    else:
        from ...rails.relisten import RelistenError, replay_relisten_receipt  # noqa: PLC0415

        try:
            relisten_receipt = replay_relisten_receipt(
                sample_id=sample_id, delivered_text=final_text,
                contacts=[
                    (contact.request_id, contact.relisten_kind, contact.text)
                    for contact in relisten_contacts
                ],
                config=relisten_config,
            )
        except RelistenError as error:
            return None, f"the relisten receipt cannot be re-derived: {error}"
    return (
        ReplayedEpisodeResult(
            sample_id=sample_id,
            final_response_text=final_text,
            contacts=tuple(
                contact for contact in contacts if contact.role_id != RELISTEN_ROLE_ID
            ),
            native_episode_receipt=dict(receipt),
            relisten=relisten_receipt,
        ),
        None,
    )


def _replay_delivery_normalisation(
    block: object, source_text: str,
) -> tuple[str | None, str | None]:
    """Re-derive a normalised row's delivered bytes from its recorded response.

    Returns ``(delivered_text, None)`` when the registered rule named by the
    receipt, run over ``source_text`` (the delivered contact's recorded
    response), reproduces the receipt's ``output_sha256``; otherwise
    ``(None, reason)`` and the row is re-flown rather than approximated. The
    same four facts the bundle's I7n re-checks: the block is structured, its
    input is the recorded response, the rule resolves, and its output is the
    recorded output. Reasons carry ids and digest prefixes only, never text.
    """

    if not isinstance(block, Mapping):
        return None, "the delivery normalisation receipt is not a structured block"
    missing = sorted({"normaliser_id", "input_sha256", "output_sha256"} - set(block))
    if missing:
        return None, f"the delivery normalisation receipt is missing {missing}"
    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    if block["input_sha256"] != source_sha256:
        return None, (
            "the delivery normaliser did not run on the delivered contact's recorded "
            f"response (input {str(block['input_sha256'])[:12]}..., recorded "
            f"{source_sha256[:12]}...)"
        )
    from ...rails import delivery_normalisers as _normalisers  # noqa: PLC0415, F401
    from ..base import DELIVERY_NORMALISERS, CoreError  # noqa: PLC0415

    normaliser_id = str(block["normaliser_id"])
    try:
        normaliser = DELIVERY_NORMALISERS.resolve(normaliser_id)
    except CoreError:
        return None, f"delivery normaliser {normaliser_id!r} is not registered"
    try:
        outcome = normaliser(source_text)
    except Exception as error:  # noqa: BLE001 - any rule failure re-flies the row
        return None, (
            f"delivery normaliser {normaliser_id!r} failed over the recorded "
            f"response: {type(error).__name__}"
        )
    output_sha256 = hashlib.sha256(outcome.text.encode("utf-8")).hexdigest()
    if output_sha256 != block["output_sha256"]:
        return None, (
            f"delivery normaliser {normaliser_id!r} does not reproduce its recorded "
            f"output under this code (recomputed {output_sha256[:12]}..., recorded "
            f"{str(block['output_sha256'])[:12]}...)"
        )
    return outcome.text, None


def read_predecessor_attempt(
    *,
    run_id: str,
    attempt_id: str,
    attempt_dir: Path,
    expected_trace_sha256: str | None = None,
    program_id: str | None = None,
    relisten: object = None,
) -> PredecessorAttempt:
    """Scan one aborted attempt's trace; zero model contact, read-only.

    ``expected_trace_sha256`` is the declaration's pin: the bytes on disk must
    hash to it, or the resume refuses. ``None`` measures without comparing,
    which is what a read-only audit of an attempt whose hash is not yet
    pinned needs.

    ``relisten`` (E4-1, 2026-09-29) is the cell's composed
    ``native_episode.relisten`` block (raw mapping or parsed
    ``rails.relisten.RelistenConfig``), or ``None`` when the cell does not
    arm it. Armed, every complete row carries its re-derived
    ``saea-relisten-v1`` receipt; unarmed, a row that nevertheless records
    relisten contacts is INCOMPLETE.
    """

    relisten_config = None
    if relisten is not None:
        from ...rails.relisten import (  # noqa: PLC0415
            RelistenConfig,
            RelistenError,
            parse_relisten,
        )

        if isinstance(relisten, RelistenConfig):
            relisten_config = relisten
        else:
            try:
                relisten_config = parse_relisten(relisten)
            except RelistenError as error:
                raise ResumeRecoveryError(
                    f"native_episode.relisten is invalid for a resume replay: {error}"
                ) from error
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
        result, reason = _classify(
            sample_id, episodes.get(sample_id), contacts[sample_id],
            relisten_config=relisten_config,
        )
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


#: The ``mode`` a manifest ``predecessor_attempt`` block carries when its rows
#: were kept from a row checkpoint (mode B) rather than a replayed trace.
RESUME_MODE_CHECKPOINT = "checkpoint"


@dataclass(frozen=True)
class CheckpointPredecessor(PredecessorAttempt):
    """Mode B (owner decision 309, 2026-10-14): a predecessor read from its
    ``<run_id>.rows.ckpt.jsonl`` instead of its trace.

    The checkpoint stores each row's CANONICAL outputs record exactly as the
    seal renders it, so nothing is replayed: a kept row is the stored record.
    The bundle still holds every kept row against exactly one trace (I7r): this
    object materializes the kept rows' own serialized trace lines, in
    checkpoint order, as a trace file under THIS attempt's directory (never in
    the predecessor's), and ``trace_path`` / ``trace_sha256`` name that file.
    The verifier re-derives it from the pinned checkpoint, so it is a pure
    function of bytes the predecessor wrote durably.
    """

    mode: str = RESUME_MODE_CHECKPOINT
    checkpoint_path: Path = Path()
    checkpoint_sha256: str = ""
    canonical: Mapping[str, tuple] = field(default_factory=dict)
    row_costs: Mapping[str, Mapping[str, object]] = field(default_factory=dict)

    @property
    def started_sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.row_costs))

    def contact_count(self) -> int:
        return sum(int(cost.get("calls", 0)) for cost in self.row_costs.values())

    def cost_totals(self) -> dict[str, object]:
        """The spend the checkpoint made durable. A row that was in flight when
        the process died never reached the file, so its contacts are not here:
        this is a lower bound, exactly as a trace-derived total is."""

        totals = {
            "calls_used": 0, "audio_seconds_used": 0.0, "latency_seconds_total": 0.0,
            "prompt_tokens_total": 0, "completion_tokens_total": 0, "tool_calls": 0,
        }
        for cost in self.row_costs.values():
            totals["calls_used"] += int(cost.get("calls", 0))
            totals["audio_seconds_used"] += float(cost.get("audio_seconds", 0.0))
            totals["latency_seconds_total"] += float(cost.get("latency_seconds", 0.0))
            totals["prompt_tokens_total"] += int(cost.get("prompt_tokens", 0))
            totals["completion_tokens_total"] += int(cost.get("completion_tokens", 0))
            totals["tool_calls"] += int(cost.get("tool_calls", 0))
        return totals

    def replay(self, sample_ids, *, controller_policy_id=None):
        raise ResumeRecoveryError(
            "a checkpoint predecessor keeps stored canonical rows and replays nothing; "
            "use canonical_rows_for()"
        )

    def results_for(self, sample_ids: Sequence[str]) -> tuple[ReplayedEpisodeResult, ...]:
        missing = [s for s in sample_ids if s not in self.complete]
        if missing:
            raise ResumeRecoveryError(
                f"{len(missing)} requested sample(s) are not COMPLETE in checkpoint of "
                f"attempt {self.attempt_id!r}, e.g. {missing[:5]}; a resume keeps every "
                "complete row and re-flies every other one -- it never selects"
            )
        order = {sample_id: index for index, sample_id in enumerate(self._sample_order)}
        return tuple(self.complete[s] for s in sorted(sample_ids, key=order.__getitem__))

    def canonical_rows_for(self, sample_ids: Sequence[str]) -> list[Mapping[str, object]]:
        """The stored canonical outputs rows of ``sample_ids`` (all COMPLETE)."""

        return [
            dict(self.canonical[result.sample_id][0])
            for result in self.results_for(list(sample_ids))
        ]

    def manifest_block(
        self, kept_sample_ids: Sequence[str], *, flown: int, partial: int,
    ) -> dict[str, object]:
        return {
            **super().manifest_block(kept_sample_ids, flown=flown, partial=partial),
            "mode": RESUME_MODE_CHECKPOINT,
            "checkpoint_path": str(self.checkpoint_path),
            "checkpoint_sha256": self.checkpoint_sha256,
        }


def read_checkpoint_predecessor(
    *,
    run_id: str,
    attempt_id: str,
    attempt_dir: Path,
    expected_checkpoint_sha256: str,
    materialize_dir: Path,
    protocol_hash: str | None = None,
    split_identity_hash: str | None = None,
    implementation: Mapping[str, str] | None = None,
) -> CheckpointPredecessor:
    """Read one aborted attempt's row checkpoint (mode B); model-free, read-only.

    Refuses, by name: a missing or re-hashed file, a broken chain, a header for
    another run / attempt / protocol / split, and -- per ROW, never for the
    file -- a row that is not COMPLETE, whose arm group is not complete, whose
    stored record does not name its own sample, or whose named request is not in
    its own stored trace. Those rows are INCOMPLETE and re-flown whole.
    """

    from ..row_checkpoint import (  # noqa: PLC0415
        RowCheckpointError, checkpoint_path, kept_trace_text, read_checkpoint,
        sha256_file,
    )

    path = checkpoint_path(Path(attempt_dir), run_id)
    if not path.is_file():
        raise ResumeRecoveryError(
            f"predecessor attempt {attempt_id!r} has no row checkpoint at {path}"
        )
    try:
        document = read_checkpoint(path, expected_sha256=expected_checkpoint_sha256)
    except RowCheckpointError as error:
        raise ResumeRecoveryError(str(error)) from error
    header = document.header
    for name, expected in (
        ("run_id", run_id), ("attempt_id", attempt_id),
        ("protocol_hash", protocol_hash), ("split_identity_hash", split_identity_hash),
    ):
        if expected is not None and header.get(name) != expected:
            raise ResumeRecoveryError(
                f"row checkpoint {path} was written for {name} {header.get(name)!r}, not "
                f"{expected!r}; a resume applies only when the code, config and split "
                "are unchanged"
            )
    if implementation is not None:
        # Owner decision 22: a resume applies only when the code is unchanged. A
        # stored row is used verbatim, so a flown row rendered by different code
        # would make the merged outputs a blend of two implementations.
        recorded = header.get("implementation")
        if recorded != dict(implementation):
            differing = sorted(
                key for key in set(dict(implementation)) | set(recorded or {})
                if (recorded or {}).get(key) != dict(implementation).get(key)
            )
            detail = ", ".join(differing) if differing else "no code identity recorded"
            raise ResumeRecoveryError(
                f"row checkpoint {path} was written by different code ({detail}); a "
                "resume applies only when the code that flew the predecessor is the "
                "code that finishes it"
            )
    kept_rows = []
    incomplete: dict[str, str] = {}
    complete: dict[str, ReplayedEpisodeResult] = {}
    canonical: dict[str, tuple] = {}
    for row in document.rows:
        defect = row.keep_defect()
        if defect is None:
            record = row.output_rows[0]
            wanted = {f"{record.get('request_id')}/request", f"{record.get('request_id')}/response"}
            present = set()
            for line in row.trace_lines:
                present.add(json.loads(line)["record_id"])
            if len(row.output_rows) != 1 or record.get("sample_id") != row.sample_id:
                defect = "the stored record does not name its own sample"
            elif not wanted <= present:
                defect = "the stored trace lacks the request/response the stored record names"
        if defect is not None:
            incomplete[row.sample_id] = defect
            continue
        kept_rows.append(row)
        record = row.output_rows[0]
        complete[row.sample_id] = ReplayedEpisodeResult(
            sample_id=row.sample_id,
            final_response_text=str(record.get("pre_projection_text", record.get("text", ""))),
            contacts=(),
            native_episode_receipt=dict(record.get("native_episode_receipt") or {}),
            solver_group=record.get("solver_group"),
            relisten=record.get("relisten"),
        )
        canonical[row.sample_id] = row.output_rows
    destination = Path(materialize_dir) / f"{run_id}.trace.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".partial")
    temporary.write_text(kept_trace_text(kept_rows), encoding="utf-8", newline="\n")
    os.replace(temporary, destination)
    return CheckpointPredecessor(
        run_id=run_id,
        attempt_id=attempt_id,
        trace_path=destination,
        trace_sha256=sha256_file(destination),
        contacts={},
        complete=complete,
        incomplete=incomplete,
        record_count=sum(len(row.trace_lines) for row in kept_rows),
        _sample_order=tuple(row.sample_id for row in document.rows),
        checkpoint_path=path,
        checkpoint_sha256=document.sha256,
        canonical=canonical,
        row_costs={row.sample_id: dict(row.cost) for row in document.rows},
    )


__all__ = [
    "CheckpointPredecessor",
    "RESUME_MODE_CHECKPOINT",
    "read_checkpoint_predecessor",
    "NATIVE_EPISODE_RECORD_SUFFIX",
    "NATIVE_ROLE_CONTACT_RECORD_SUFFIX",
    "NON_WIRE_CONTACT_BLOCKS",
    "RELISTEN_ROLE_ID",
    "RESUME_PREDECESSOR_SCHEMA",
    "MergedPredecessors",
    "PredecessorAttempt",
    "PredecessorContact",
    "ReplayedEpisodeResult",
    "ReplayedPhaseSummary",
    "ResumeDeclaration",
    "ResumeRecoveryError",
    "kept_sample_ids_sha256",
    "predecessor_trace_path",
    "read_predecessor_attempt",
    "resume_declarations_from_document",
]
