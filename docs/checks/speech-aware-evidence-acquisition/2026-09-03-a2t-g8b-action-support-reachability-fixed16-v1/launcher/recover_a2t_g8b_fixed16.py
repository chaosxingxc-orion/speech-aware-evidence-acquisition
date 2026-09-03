#!/usr/bin/env python3
"""Recover the sealed G8B flight without model, scorer, gold, audio, or network access.

The recovery is a diagnostic derivative of an ABORTED attempt.  It verifies
the pinned terminal source, replays each sealed response exactly once through
the G8B state machine, and emits write-once EXTERNALLY_SEALED_UNVERIFIABLE
artifacts.  It deliberately cannot create a normal run manifest or a scoring
job plan because the source attempt is already ABORTED.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

_LAUNCHER_PATH = Path(__file__).with_name("launch_a2t_g8b_fixed16.py")
_SPEC = importlib.util.spec_from_file_location("_saea_g8b_recovery_source", _LAUNCHER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the G8B state-machine source")
g8b = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, g8b)
_SPEC.loader.exec_module(g8b)

from speech_aware_evidence_acquisition.contracts import TraceRecord  # noqa: E402
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer, TraceSink  # noqa: E402


RUN_ID = g8b.RUN_ID
ATTEMPT_ID = "attempt-20260903t023615z-g8b-fixed16"
RECOVERY_ID = "g8b-zero-contact-recovery-fixed-source-v1"
EXPECTED_CONTACTS = 538
BRANCH_ORDER = g8b.BRANCH_ORDER
SOURCE_FLIGHT_RELPATH = Path(
    "runs/SAEA-A2T-G8B-ACTION-SUPPORT-REACHABILITY-FIXED16-V1/"
    "flight-20260903T024054Z"
)
DEFAULT_RECOVERY_RELPATH = Path(
    "runs/SAEA-A2T-G8B-ACTION-SUPPORT-REACHABILITY-FIXED16-V1/"
    "g8b-zc-recovery-v1"
)


class RecoveryError(RuntimeError):
    """The sealed source or the model-free derivative failed closed."""


@dataclass(frozen=True)
class SourceHashes:
    transport_trace_sha256: str
    transport_manifest_sha256: str
    failure_receipt_sha256: str


PINNED_SOURCE_HASHES = SourceHashes(
    transport_trace_sha256=(
        "8bad0a5d2b42ae06eadf2fc7d3208349c0212fc4f04f2209494e3cec040f9def"
    ),
    transport_manifest_sha256=(
        "dbdca4130023c73716fbcb8c302be5b31354057e7e9ceece8829269aa98fff30"
    ),
    failure_receipt_sha256=(
        "90f94b92982d9920e5e5d3a957db33f4b0f6994a34846e78908abcfd7809ac84"
    ),
)
EXECUTION_PLAN_SHA256 = "83fc2093a0c9f03530baded99c29ef7d246e385cef6b7227508ebc106078efdc"
SESSION_RECEIPT_SHA256 = "4019be36e94aaa7ac44c9464d4fee42fa1d45574d5bdfd1e9411a805486f94c8"
STOP_RECEIPT_SHA256 = "87b6e66fb5f9378d63f39368173a4294d67d205ab355ea374bc869a8fe5f295b"
ATTEMPT_STATE_SHA256 = "fce94a99e30f3deb83da8a2f30f94ef1a28cc426ee220e88950ca784b7a9e998"
PARTIAL_AGENT_TRACE_SHA256 = "1292787da0f2814ad88fdcd87d0b9318e5e7911c4cf0fbb55f2c383076c648c3"
PARTIAL_AGENT_MANIFEST_SHA256 = "a2eb4bb78afa53e933bf0058f9650cdaa1f4f6f4c08de71d195a29d9e4b6c192"


@dataclass(frozen=True)
class SourceContact:
    sample_id: str
    contact_id: str
    source_request_id: str
    slot_id: int
    request_record: Mapping[str, object]
    response_record: Mapping[str, object]
    cost_record: Mapping[str, object]
    response_bytes: bytes


@dataclass(frozen=True)
class SealedTransport:
    contacts: Mapping[tuple[str, str], SourceContact]
    physical_cost: Mapping[str, object]
    record_count: int
    hashes: SourceHashes


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecoveryError(f"cannot read JSON source {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise RecoveryError(f"JSON source is not an object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _assert_sha256(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise RecoveryError(f"{label} SHA-256 drift")


def _transport_paths(flight: Path) -> tuple[Path, Path, Path]:
    trace_dir = Path(flight) / "g8b" / "transport-trace"
    return (
        trace_dir / f"{RUN_ID}.trace.jsonl",
        trace_dir / f"{RUN_ID}.trace-manifest.json",
        Path(flight) / "failure-receipt.json",
    )


def load_sealed_transport(
    flight: Path,
    *,
    expected: SourceHashes = PINNED_SOURCE_HASHES,
    expected_contact_count: int = EXPECTED_CONTACTS,
) -> SealedTransport:
    """Verify and index complete request/response/cost triples by exact contact key."""

    trace_path, manifest_path, failure_path = _transport_paths(Path(flight))
    _assert_sha256(trace_path, expected.transport_trace_sha256, "transport trace")
    _assert_sha256(manifest_path, expected.transport_manifest_sha256, "transport manifest")
    _assert_sha256(failure_path, expected.failure_receipt_sha256, "failure receipt")

    failure = _read_json(failure_path)
    if (
        failure.get("run_id") != RUN_ID
        or failure.get("attempt_id") != ATTEMPT_ID
        or failure.get("terminal") is not True
        or failure.get("branch_manifests_emitted") is not False
        or failure.get("scoring_started") is not False
        or failure.get("retry_or_repair_authorized") is not False
        or "TraceContractError" not in str(failure.get("error", ""))
        or "OBS payload key 'sample_id'" not in str(failure.get("error", ""))
    ):
        raise RecoveryError("failure receipt is not the pinned terminal audit-emission failure")

    manifest = _read_json(manifest_path)
    manifest_records = manifest.get("records")
    if manifest.get("run_id") != RUN_ID or not isinstance(manifest_records, Mapping):
        raise RecoveryError("transport manifest identity is malformed")

    raw = trace_path.read_bytes()
    if not raw.endswith(b"\n"):
        raise RecoveryError("transport trace is not newline terminated")
    records: dict[str, Mapping[str, object]] = {}
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        try:
            line = raw_line.decode("utf-8")
            document = json.loads(line)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise RecoveryError(f"transport trace line {line_number} is malformed") from error
        if not isinstance(document, Mapping):
            raise RecoveryError(f"transport trace line {line_number} is not an object")
        record_id = document.get("record_id")
        channel = document.get("channel")
        payload = document.get("payload")
        if not isinstance(record_id, str) or record_id in records or not isinstance(payload, Mapping):
            raise RecoveryError(f"transport trace line {line_number} has malformed identity")
        record = TraceRecord(str(channel), record_id, payload)
        if record.serialize() != line:
            raise RecoveryError(f"transport trace line {line_number} is not canonical")
        if manifest_records.get(record_id) != record.content_hash():
            raise RecoveryError(f"transport trace record hash drift: {record_id}")
        records[record_id] = document
    if set(records) != set(manifest_records):
        raise RecoveryError("transport trace and manifest record identities differ")
    if len(records) != expected_contact_count * 3:
        raise RecoveryError("transport trace does not contain the exact triple count")

    grouped: dict[str, dict[str, Mapping[str, object]]] = {}
    for record_id, document in records.items():
        if "/" not in record_id:
            raise RecoveryError(f"transport record lacks a triple suffix: {record_id}")
        source_request_id, suffix = record_id.rsplit("/", 1)
        if suffix not in {"request", "response", "cost"}:
            raise RecoveryError(f"transport record has an unknown triple suffix: {record_id}")
        grouped.setdefault(source_request_id, {})[suffix] = document
    if len(grouped) != expected_contact_count or any(
        set(parts) != {"request", "response", "cost"} for parts in grouped.values()
    ):
        raise RecoveryError("transport trace has an incomplete or duplicate source triple")

    contacts: dict[tuple[str, str], SourceContact] = {}
    costs: list[Mapping[str, object]] = []
    for source_request_id, triple in grouped.items():
        request = triple["request"]
        response = triple["response"]
        cost = triple["cost"]
        if (
            request.get("channel") != "MODEL_REQUEST"
            or response.get("channel") != "MODEL_RESPONSE"
            or cost.get("channel") != "COST"
        ):
            raise RecoveryError(f"source triple channels drift: {source_request_id}")
        request_outer = request["payload"]
        response_payload = response["payload"]
        cost_payload = cost["payload"]
        assert isinstance(request_outer, Mapping)
        assert isinstance(response_payload, Mapping)
        assert isinstance(cost_payload, Mapping)
        request_payload = request_outer.get("payload")
        if not isinstance(request_payload, Mapping):
            raise RecoveryError(f"source request payload is malformed: {source_request_id}")
        history = request_payload.get("history")
        decoding = request_payload.get("decoding_params")
        if (
            request_payload.get("request_id") != source_request_id
            or not isinstance(request_payload.get("sample_id"), str)
            or not isinstance(history, list)
            or len(history) != 1
            or not isinstance(history[0], Mapping)
            or not isinstance(history[0].get("contact_id"), str)
            or not isinstance(decoding, Mapping)
            or isinstance(decoding.get("id_slot"), bool)
            or not isinstance(decoding.get("id_slot"), int)
        ):
            raise RecoveryError(f"source request contact binding is malformed: {source_request_id}")
        sample_id = str(request_payload["sample_id"])
        contact_id = str(history[0]["contact_id"])
        text = response_payload.get("text")
        if not isinstance(text, str):
            raise RecoveryError(f"source response text is malformed: {source_request_id}")
        response_bytes = text.encode("utf-8")
        if hashlib.sha256(response_bytes).hexdigest() != response_payload.get(
            "response_text_sha256"
        ):
            raise RecoveryError(f"source response UTF-8 hash drift: {source_request_id}")
        if cost_payload.get("calls") != 1:
            raise RecoveryError(f"source cost is not one physical call: {source_request_id}")
        key = (sample_id, contact_id)
        if key in contacts:
            raise RecoveryError(f"duplicate sample/contact source key: {key!r}")
        contacts[key] = SourceContact(
            sample_id=sample_id,
            contact_id=contact_id,
            source_request_id=source_request_id,
            slot_id=int(decoding["id_slot"]),
            request_record=MappingProxyType(dict(request)),
            response_record=MappingProxyType(dict(response)),
            cost_record=MappingProxyType(dict(cost)),
            response_bytes=response_bytes,
        )
        costs.append(cost_payload)

    def integer_sum(key: str) -> int:
        values = [row.get(key) for row in costs]
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise RecoveryError(f"source cost field {key!r} is malformed")
        return sum(int(value) for value in values)

    def float_sum(key: str) -> float:
        values = [row.get(key) for row in costs]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise RecoveryError(f"source cost field {key!r} is malformed")
        return math.fsum(float(value) for value in values)

    physical_cost = {
        "calls_used": integer_sum("calls"),
        "audio_seconds_used": float_sum("audio_seconds"),
        "latency_seconds_total": float_sum("latency_seconds"),
        "prompt_tokens_total": integer_sum("prompt_tokens"),
        "completion_tokens_total": integer_sum("completion_tokens"),
    }
    if physical_cost["calls_used"] != expected_contact_count:
        raise RecoveryError("source physical call accounting drift")
    return SealedTransport(
        contacts=MappingProxyType(contacts),
        physical_cost=MappingProxyType(physical_cost),
        record_count=len(records),
        hashes=expected,
    )


class ReplayClient:
    """A no-I/O FrozenCoreClient substitute backed only by sealed response bytes."""

    def __init__(self, sealed: SealedTransport) -> None:
        self._sealed = sealed
        self._used: set[tuple[str, str]] = set()

    def slot_for(self, sample_id: str, contact_id: str) -> int:
        try:
            return self._sealed.contacts[(sample_id, contact_id)].slot_id
        except KeyError as error:
            raise RecoveryError(
                f"no sealed response for exact contact {(sample_id, contact_id)!r}"
            ) from error

    def complete(self, _messages: object, **kwargs: object) -> str:
        sample_id = kwargs.get("speech_feature_sample_id")
        contact_id = kwargs.get("agent_contact_id")
        if not isinstance(sample_id, str) or not isinstance(contact_id, str):
            raise RecoveryError("replay request lacks an exact sample/contact key")
        key = (sample_id, contact_id)
        if key in self._used:
            raise RecoveryError(f"sealed source contact used more than once: {key!r}")
        try:
            source = self._sealed.contacts[key]
        except KeyError as error:
            raise RecoveryError(f"no sealed response for exact contact {key!r}") from error
        decoding = kwargs.get("decoding_params")
        if not isinstance(decoding, Mapping) or decoding.get("id_slot") != source.slot_id:
            raise RecoveryError(f"replay slot differs from sealed source: {key!r}")
        text = source.response_bytes.decode("utf-8")
        if text.encode("utf-8") != source.response_bytes:
            raise RecoveryError(f"replay changed sealed response bytes: {key!r}")
        self._used.add(key)
        return text

    def assert_complete(self, *, expected_count: int = EXPECTED_CONTACTS) -> None:
        if len(self._used) != expected_count or self._used != set(self._sealed.contacts):
            raise RecoveryError("replay did not consume every source triple exactly once")

    @property
    def used(self) -> frozenset[tuple[str, str]]:
        return frozenset(self._used)


def _replay_runner(client: ReplayClient):
    """Return a deterministic state-machine runner that performs no external I/O."""

    def run(states: Sequence[object], **callbacks: object) -> Sequence[object]:
        prepare = callbacks["prepare_wave"]
        invoke = callbacks["invoke_contact"]
        aggregate = callbacks["aggregate_wave"]
        should_continue = callbacks["should_continue"]
        if not all(callable(item) for item in (prepare, invoke, aggregate, should_continue)):
            raise RecoveryError("replay runner received malformed state-machine callbacks")
        session = object()
        for state in states:
            while should_continue(state):  # type: ignore[operator]
                count = prepare(state, session)  # type: ignore[operator]
                responses = []
                for index in range(count):
                    context = state.current[index]
                    slot = client.slot_for(state.sample.sample_id, context.contact_id)
                    responses.append(invoke(state, index, slot))  # type: ignore[operator]
                aggregate(state, tuple(responses), session)  # type: ignore[operator]
        return states

    return run


def write_diagnostic_branches(
    *,
    output_dir: Path,
    recovery_id: str,
    sample_ids: Sequence[str],
    branch_texts: Mapping[str, Mapping[str, str]],
    source_binding: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    """Write four complete diagnostic derivatives and an explicit scoring refusal."""

    output_dir = Path(output_dir)
    if output_dir.exists():
        raise RecoveryError(f"recovery output directory already exists: {output_dir}")
    ids = tuple(sample_ids)
    if (
        not recovery_id
        or len(ids) != len(set(ids))
        or set(branch_texts) != set(BRANCH_ORDER)
        or any(set(branch_texts[branch]) != set(ids) for branch in BRANCH_ORDER)
    ):
        raise RecoveryError("diagnostic branch inputs are not identity-complete")
    output_dir.mkdir(parents=True, exist_ok=False)
    result: dict[str, Mapping[str, object]] = {}
    for branch in BRANCH_ORDER:
        branch_dir = output_dir / "branches" / branch.lower()
        outputs = branch_dir / "outputs.jsonl"
        rows = tuple(
            {
                "run_id": RUN_ID,
                "recovery_id": recovery_id,
                "sample_id": sample_id,
                "branch": branch,
                "text": branch_texts[branch][sample_id],
                "response_text_utf8_sha256": hashlib.sha256(
                    branch_texts[branch][sample_id].encode("utf-8")
                ).hexdigest(),
                "diagnostic_only": True,
                "scoring_eligible": False,
            }
            for sample_id in ids
        )
        _write_jsonl(outputs, rows)
        manifest = branch_dir / "diagnostic-manifest.json"
        manifest_document = {
            "schema": "saea-a2t-g8b-externally-sealed-unverifiable-branch-v1",
            "status": "EXTERNALLY_SEALED_UNVERIFIABLE",
            "run_id": RUN_ID,
            "recovery_id": recovery_id,
            "branch": branch,
            "row_count": len(rows),
            "sample_ids": list(ids),
            "outputs": {"path": str(outputs.resolve()), "sha256": _sha256(outputs)},
            "source": dict(source_binding),
            "normal_run_manifest": False,
            "scoring_eligible": False,
            "scoring_refusal": (
                "The inherited physical-contact attempt is ABORTED and cannot be "
                "finalized or admitted to official scoring."
            ),
        }
        _write_json(manifest, manifest_document)
        result[branch] = {
            "outputs": str(outputs.resolve()),
            "outputs_sha256": _sha256(outputs),
            "manifest": str(manifest.resolve()),
            "manifest_sha256": _sha256(manifest),
        }
    _write_json(
        output_dir / "scoring-disposition.json",
        {
            "schema": "saea-a2t-g8b-recovery-scoring-disposition-v1",
            "run_id": RUN_ID,
            "recovery_id": recovery_id,
            "official_scoring_authorized": False,
            "jobs": [],
            "reason": (
                "No score job plan is emitted from an ABORTED source attempt; a fresh "
                "authorized successor is required for official scoring."
            ),
        },
    )
    return result


def _validate_pinned_flight(data_root: Path, flight: Path, sealed: SealedTransport) -> dict[str, object]:
    expected_flight = (Path(data_root) / SOURCE_FLIGHT_RELPATH).resolve()
    if Path(flight).resolve() != expected_flight:
        raise RecoveryError("recovery source is not the exact pinned terminal G8B flight")
    paths = {
        "execution_plan": flight / "g8b" / "execution-plan.json",
        "session_receipt": flight / "service" / "session-receipt.json",
        "stop_receipt": flight / "service" / "stop-receipt.json",
        "partial_agent_trace": flight / "g8b" / "agent-trace" / f"{RUN_ID}.trace.jsonl",
        "partial_agent_manifest": (
            flight / "g8b" / "agent-trace" / f"{RUN_ID}.trace-manifest.json"
        ),
        "attempt_state": (
            Path(data_root) / "attempts" / RUN_ID / f"{ATTEMPT_ID}.json"
        ),
    }
    expected_hashes = {
        "execution_plan": EXECUTION_PLAN_SHA256,
        "session_receipt": SESSION_RECEIPT_SHA256,
        "stop_receipt": STOP_RECEIPT_SHA256,
        "partial_agent_trace": PARTIAL_AGENT_TRACE_SHA256,
        "partial_agent_manifest": PARTIAL_AGENT_MANIFEST_SHA256,
        "attempt_state": ATTEMPT_STATE_SHA256,
    }
    for label, path in paths.items():
        _assert_sha256(path, expected_hashes[label], label.replace("_", " "))
    plan = _read_json(paths["execution_plan"])
    attempt = _read_json(paths["attempt_state"])
    if (
        plan.get("run_id") != RUN_ID
        or plan.get("attempt_id") != ATTEMPT_ID
        or plan.get("planned_model_calls") != g8b.MAX_MODEL_CONTACTS
        or attempt.get("run_id") != RUN_ID
        or attempt.get("attempt_id") != ATTEMPT_ID
        or attempt.get("state") != "ABORTED"
        or not isinstance(attempt.get("actual"), Mapping)
        or attempt["actual"].get("calls") != EXPECTED_CONTACTS
        or abs(
            float(attempt["actual"].get("audio_seconds", -1))
            - float(sealed.physical_cost["audio_seconds_used"])
        )
        > 1e-9
    ):
        raise RecoveryError("execution plan or ABORTED attempt-state binding drift")
    trace_path, manifest_path, failure_path = _transport_paths(flight)
    return {
        "flight": str(flight.resolve()),
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT_ID,
        "attempt_state": "ABORTED",
        "transport_trace_path": str(trace_path.resolve()),
        "transport_trace_sha256": sealed.hashes.transport_trace_sha256,
        "transport_manifest_path": str(manifest_path.resolve()),
        "transport_manifest_sha256": sealed.hashes.transport_manifest_sha256,
        "failure_receipt_path": str(failure_path.resolve()),
        "failure_receipt_sha256": sealed.hashes.failure_receipt_sha256,
        **{
            f"{label}_path": str(path.resolve())
            for label, path in paths.items()
        },
        **{
            f"{label}_sha256": digest
            for label, digest in expected_hashes.items()
        },
        "physical_cost": dict(sealed.physical_cost),
    }


def _load_model_free_context(data_root: Path) -> Mapping[str, object]:
    promotion_receipt = g8b.PROMOTION_RECEIPT
    if not promotion_receipt.is_file() and os.name == "nt":
        linux_path = promotion_receipt.as_posix()
        if linux_path.startswith("/home/"):
            promotion_receipt = Path(
                "\\\\wsl.localhost\\Ubuntu-24.04" + linux_path.replace("/", "\\")
            )
    for path, expected in (
        (g8b.G8B_ROSTER, g8b.ROSTER_SHA256),
        (g8b.G1_RECEIPT, g8b.G1_RECEIPT_SHA256),
        (g8b.GROUND_CORPUS, g8b.GROUND_SHA256),
        (g8b.GROUND_STRUCTURED, g8b.GROUND_STRUCTURED_SHA256),
        (g8b.GROUND_RECEIPT, g8b.GROUND_RECEIPT_SHA256),
        (promotion_receipt, g8b.PROMOTION_RECEIPT_SHA256),
    ):
        if g8b._v1._sha256(path) != expected:
            raise RecoveryError(f"model-free recovery asset hash drift: {path}")
    m0_path = Path(data_root) / g8b.M0_RELPATH
    if not m0_path.is_file() or g8b._v1._sha256(m0_path) != g8b.M0_SHA256:
        raise RecoveryError("frozen M0 source hash drift")
    original_promotion_receipt = g8b.PROMOTION_RECEIPT
    try:
        g8b.PROMOTION_RECEIPT = promotion_receipt
        surface = g8b.load_runtime_surface()
    finally:
        g8b.PROMOTION_RECEIPT = original_promotion_receipt
    sample_ids = tuple(sample.sample_id for sample in surface.samples)
    return {
        "surface": surface,
        "ground": g8b._v1.load_ground(),
        "sample_ids": sample_ids,
        "m0_texts": g8b._v1.load_m0_outputs(m0_path, sample_ids),
        "m0_path": m0_path,
        "m0_sha256": g8b.M0_SHA256,
    }


def _validate_recovery_destination(
    source_flight: Path,
    destination: Path,
    *,
    write_output: bool,
) -> None:
    """Keep recovery writes separate while allowing repeatable read-only audits."""

    source_flight = Path(source_flight).resolve()
    destination = Path(destination).resolve()
    if destination == source_flight or source_flight in destination.parents:
        raise RecoveryError("recovery destination must be distinct from the source flight")
    if write_output and destination.exists():
        raise RecoveryError(f"recovery output directory already exists: {destination}")


def recover_flight(
    data_root: Path,
    *,
    source_flight: Path | None = None,
    output_dir: Path | None = None,
    recovery_id: str = RECOVERY_ID,
    verify_only: bool = False,
) -> Mapping[str, object]:
    """Replay the exact terminal source and optionally write diagnostic derivatives."""

    data_root = Path(data_root).resolve()
    flight = Path(source_flight or data_root / SOURCE_FLIGHT_RELPATH).resolve()
    destination = Path(output_dir or data_root / DEFAULT_RECOVERY_RELPATH).resolve()
    _validate_recovery_destination(
        flight,
        destination,
        write_output=not verify_only,
    )
    sealed = load_sealed_transport(flight)
    source_binding = _validate_pinned_flight(data_root, flight, sealed)
    context = _load_model_free_context(data_root)
    expected_ids = tuple(context["sample_ids"])
    if set(key[0] for key in sealed.contacts) != set(expected_ids):
        raise RecoveryError("sealed transport sample identities differ from the G8B roster")

    replay_client = ReplayClient(sealed)
    audit_buffer = TraceBuffer(RUN_ID)
    summary = g8b.run_openjiuwen_phase(
        surface=context["surface"],
        ground=context["ground"],
        client=replay_client,
        trace_sink=audit_buffer,
        workflow_runner=_replay_runner(replay_client),
    )
    replay_client.assert_complete()
    if summary.physical_model_contacts != EXPECTED_CONTACTS:
        raise RecoveryError("replayed state machine did not realize exactly 538 contacts")
    for state in summary.results:
        for contact in state.contacts:
            source = sealed.contacts[(state.sample.sample_id, contact.contact_id)]
            if source.response_bytes != source.response_bytes.decode("utf-8").encode("utf-8"):
                raise RecoveryError("replay did not preserve exact source response bytes")
            if hashlib.sha256(source.response_bytes).hexdigest() != contact.response_sha256:
                raise RecoveryError("replayed contact hash differs from sealed source")
        branch_sources = {
            "EXHAUSTIVE_G7": "g7-resolve",
            "SUPPORT_ONLY_RESOLVE": "g8-support-only-resolve",
            "DECOMPOSED_SELECT_BIND_RESOLVE": (
                "g8-decomposed-select"
                if state.invalid_stage == "DECOMPOSED_SELECT"
                else "g8-decomposed-bind"
                if state.invalid_stage == "DECOMPOSED_BIND"
                else "g8-decomposed-resolve"
            ),
        }
        for branch, contact_id in branch_sources.items():
            source = sealed.contacts[(state.sample.sample_id, contact_id)]
            if state.branch_texts[branch].encode("utf-8") != source.response_bytes:
                raise RecoveryError("branch derivative changed sealed final response bytes")

    verification = {
        "status": "PINNED_SOURCE_REPLAY_VERIFIED",
        "run_id": RUN_ID,
        "recovery_id": recovery_id,
        "source_record_count": sealed.record_count,
        "source_contact_triples": len(sealed.contacts),
        "source_triples_used_exactly_once": len(replay_client.used),
        "replayed_physical_contacts": summary.physical_model_contacts,
        "new_model_contacts": 0,
        "new_scorer_contacts": 0,
        "gold_opened": False,
        "audio_opened": False,
        "network_opened": False,
        "gate_touched": False,
        "service_started": False,
        "source": source_binding,
    }
    if verify_only:
        return verification

    branch_texts = {
        "STOP_M0": dict(context["m0_texts"]),
        **{
            branch: {
                state.sample.sample_id: state.branch_texts[branch]
                for state in summary.results
            }
            for branch in BRANCH_ORDER[1:]
        },
    }
    source_for_manifests = {
        key: value
        for key, value in source_binding.items()
        if key.endswith("_sha256") or key in {"run_id", "attempt_id", "attempt_state"}
    }
    branches = write_diagnostic_branches(
        output_dir=destination,
        recovery_id=recovery_id,
        sample_ids=expected_ids,
        branch_texts=branch_texts,
        source_binding=source_for_manifests,
    )
    plan = {
        "schema": "saea-a2t-g8b-zero-contact-recovery-plan-v1",
        "recovery_id": recovery_id,
        "source_run_id": RUN_ID,
        "source_attempt_id": ATTEMPT_ID,
        "source_attempt_state": "ABORTED",
        "model_execution_plan_required": False,
        "inherited_execution_plan_sha256": EXECUTION_PLAN_SHA256,
        "new_model_contacts": 0,
        "new_scorer_contacts": 0,
        "allowed_actions": [
            "hash-verify-pinned-source",
            "replay-sealed-response-by-exact-sample-and-contact",
            "emit-diagnostic-derivatives",
        ],
        "prohibited_actions": [
            "start-service",
            "touch-gate",
            "touch-model",
            "open-audio",
            "open-gold",
            "touch-scorer",
            "network",
            "mutate-source-flight",
            "emit-normal-run-manifest",
            "emit-score-job-plan",
        ],
        "recovery_module_sha256": _sha256(Path(__file__)),
        "corrected_launcher_sha256": _sha256(_LAUNCHER_PATH),
    }
    _write_json(destination / "recovery-plan.json", plan)
    agent_dir = destination / "corrected-agent-trace"
    sink = TraceSink(agent_dir, RUN_ID)
    audit_buffer.flush_into(sink)
    agent_manifest_hash = sink.close()
    agent_trace_path = agent_dir / f"{RUN_ID}.trace.jsonl"
    agent_manifest_path = agent_dir / f"{RUN_ID}.trace-manifest.json"

    # Re-hash every pinned source after all writes; the destination is a sibling,
    # so any accidental write to the source flight is detected before sealing.
    load_sealed_transport(flight)
    _validate_pinned_flight(data_root, flight, sealed)
    receipt = {
        "schema": "saea-a2t-g8b-zero-contact-recovery-receipt-v1",
        **verification,
        "status": "EXTERNALLY_SEALED_UNVERIFIABLE",
        "source_artifacts_unchanged": True,
        "corrected_agent_trace": {
            "path": str(agent_trace_path.resolve()),
            "sha256": _sha256(agent_trace_path),
            "manifest_path": str(agent_manifest_path.resolve()),
            "manifest_sha256": agent_manifest_hash,
            "record_count": len(audit_buffer.records) if audit_buffer.records else len(
                _read_json(agent_manifest_path)["records"]
            ),
        },
        "branches": branches,
        "normal_run_manifests_emitted": False,
        "score_job_plan_emitted": False,
        "official_scoring_authorized": False,
        "scoring_disposition": str((destination / "scoring-disposition.json").resolve()),
        "recovery_plan": {
            "path": str((destination / "recovery-plan.json").resolve()),
            "sha256": _sha256(destination / "recovery-plan.json"),
        },
    }
    _write_json(destination / "recovery-receipt.json", receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify-only", action="store_true")
    mode.add_argument("--recover", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--source-flight", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--recovery-id", default=RECOVERY_ID)
    args = parser.parse_args(argv)
    data_root = args.data_root or g8b._v1.data_root()
    result = recover_flight(
        data_root,
        source_flight=args.source_flight,
        output_dir=args.output_dir,
        recovery_id=args.recovery_id,
        verify_only=args.verify_only,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
