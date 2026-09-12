"""Load source-bound cached speech observations for the shared OBS tool path.

This module consumes preparation artifacts only.  It never invokes an ASR
decoder and never grants permission for a neural contact.  The finalized
``AttemptStore`` row and its exposure-ledger registration preserve the cost of
the original preparation; selecting cached evidence adds no neural call.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from ..contracts import (
    ExecutionPlan,
    ExecutionScopeError,
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from ..core.attempts.constants import ATTEMPT_SCHEMA, STATE_FINALIZED
from ..core.preparation import PreparationError, hash_stable_file, load_artifact
from .errors import RailsError


PREPARED_SPEECH_OBSERVATION_TOOL = "saea-tool-prepared-speech-observation-v1"
CATALOG_SCHEMA = "saea-prepared-speech-observation-catalog-v1"
OUTPUT_SCHEMA = "saea-prepared-speech-observation-v1"
SELECTION_SCHEMA = "saea-speech-observation-selection-v1"
RECEIPT_SCHEMA = "saea-speech-observation-catalog-receipt-v1"
ARTIFACT_KIND = "prepared-speech-observation-v1"
FINALIZATION_KIND = "speech-observation-catalog"
STATUSES = frozenset({"ok", "empty", "timeout", "unsupported"})
_SHA_CHARS = frozenset("0123456789abcdef")


class SpeechObservationError(RailsError):
    """A cached observation or its preparation lineage is not admissible."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpeechObservationError(f"{field} must be non-empty text")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - _SHA_CHARS:
        raise SpeechObservationError(f"{field} must be a lowercase SHA-256")
    return value


def _finite_positive(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise SpeechObservationError(f"{field} must be finite and positive")
    return float(value)


def _finite_nonnegative(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise SpeechObservationError(f"{field} must be finite and non-negative")
    return float(value)


def _exact_mapping(value: object, keys: set[str], field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise SpeechObservationError(f"{field} must contain exactly {sorted(keys)}")
    return value


def _confined(root: Path, relpath: object, field: str) -> tuple[str, Path]:
    rel = _text(relpath, field)
    segments = rel.split("/")
    if (
        "\\" in rel
        or ":" in rel
        or any(segment in {"", ".", ".."} for segment in segments)
    ):
        raise SpeechObservationError(
            f"{field} must be a canonical POSIX relative path confined to its declared root"
        )
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SpeechObservationError(f"{field} must be confined to its declared root")
    resolved_root = Path(root).resolve()
    resolved = (resolved_root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise SpeechObservationError(f"{field} must be confined to its declared root")
    return candidate.as_posix(), resolved


def _pinned_file(root: Path, pin: object, field: str) -> tuple[dict[str, str], Path]:
    value = _exact_mapping(pin, {"relpath", "sha256"}, field)
    relpath, path = _confined(root, value["relpath"], f"{field}.relpath")
    expected = _sha(value["sha256"], f"{field}.sha256")
    try:
        _, measured, _ = hash_stable_file(path, field)
    except PreparationError as error:
        raise SpeechObservationError(str(error)) from error
    if measured != expected:
        raise SpeechObservationError(f"{field} file hash mismatch")
    return {"relpath": relpath, "sha256": expected}, path


def _read_json(path: Path, field: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpeechObservationError(f"cannot read {field}: {error}") from error
    if not isinstance(value, Mapping):
        raise SpeechObservationError(f"{field} must be a JSON object")
    return value


def _load_execution_plan(repo_root: Path, pin: object) -> tuple[ExecutionPlan, dict[str, str]]:
    normalized, path = _pinned_file(repo_root, pin, "producer.execution_plan")
    envelope = _read_json(path, "producer execution plan")
    declaration = envelope.get("execution_plan")
    if not isinstance(declaration, Mapping):
        raise SpeechObservationError("producer execution plan envelope lacks execution_plan")
    try:
        plan = ExecutionPlan(**dict(declaration)).validate()
    except (TypeError, ExecutionScopeError) as error:
        raise SpeechObservationError(f"producer execution plan is invalid: {error}") from error
    return plan, normalized


def _ledger_row(repo_root: Path, pin: object, plan: ExecutionPlan) -> dict[str, str]:
    value = _exact_mapping(pin, {"relpath", "sha256", "row_id"}, "producer.ledger_row")
    normalized, path = _pinned_file(
        repo_root,
        {"relpath": value["relpath"], "sha256": value["sha256"]},
        "producer.ledger_row",
    )
    row_id = _text(value["row_id"], "producer.ledger_row.row_id")
    if row_id != plan.run_id:
        raise SpeechObservationError("ledger row identity differs from the execution plan")
    try:
        rows = _parse_ledger_tables(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise SpeechObservationError(f"cannot parse exposure ledger: {error}") from error
    matched = [row for row in rows if row.get(_EXPOSURE_RUN_COLUMN) == row_id]
    if len(matched) != 1:
        raise SpeechObservationError("exposure ledger must contain exactly one original preregistration row")
    row = matched[0]
    expected_text = {
        "execution profile": plan.execution_profile,
        "split role": plan.split_role,
        "split identity hash": plan.split_identity_hash,
    }
    for column, expected in expected_text.items():
        if row.get(column) != expected:
            raise SpeechObservationError(f"exposure ledger differs on {column}")
    carrier = row.get("speech carrier + split", "")
    if plan.carrier_lock_key not in carrier.replace(",", " ").split():
        raise SpeechObservationError("exposure ledger differs on carrier identity")
    # A consumer may legitimately read a finalized preparation whose row is
    # already consumed.  Only identity and registered capacity matter here.
    if row.get("consumed", "").strip().lower() not in {"yes", "no"}:
        raise SpeechObservationError("exposure ledger consumed field is invalid")
    for column, planned, parser in (
        ("calls", plan.planned_model_calls, int),
        ("speech audio seconds", plan.planned_speech_audio_seconds, int),
        ("gpu hours", plan.planned_gpu_hours, float),
    ):
        try:
            registered = parser(row[column])
        except (KeyError, TypeError, ValueError) as error:
            raise SpeechObservationError(f"exposure ledger {column} is invalid") from error
        if not math.isfinite(float(registered)) or registered < planned:
            raise SpeechObservationError(f"exposure ledger does not cover planned {column}")
    return {**normalized, "row_id": row_id}


def _artifact_inputs(
    row: Mapping[str, object],
    catalog: Mapping[str, object],
    producer: Mapping[str, object],
) -> dict[str, object]:
    return {
        "config_sha256": catalog["decoding_config_sha256"],
        "split_identity_hash": catalog["use_split_identity_hash"],
        "sources": {
            "sample_id": row["sample_id"],
            "speech_packet_id": row["speech_packet_id"],
            "speech_packet_sha256": row["speech_packet_sha256"],
            "source_audio_relpath": row["source_audio_relpath"],
            "source_audio_sha256": row["source_audio_sha256"],
            "source_audio_duration_seconds": row["source_audio_duration_seconds"],
            "span": dict(row["span"]),
            "checkpoint_receipt": dict(catalog["checkpoint_receipt"]),
            "producer_run_id": producer["run_id"],
            "producer_attempt_id": producer["attempt_id"],
            "execution_plan": dict(producer["execution_plan"]),
            "protocol_sha256": producer["protocol_sha256"],
            "ledger_row": dict(producer["ledger_row"]),
        },
    }


def _fallback(status: str) -> str:
    return (
        f"The prepared speech observation returned status: {status}. "
        "Keep the prior draft unless other evidence supports a change."
    )


@dataclass(frozen=True)
class SpeechObservationSelection:
    visible: Mapping[str, object]
    lineage: Mapping[str, object]

    def content_block(self) -> dict[str, object]:
        """Render one typed OBS block for runtime and actual-request validation."""
        status = self.visible["status"]
        text = (
            "Independent ASR observation of the original utterance:\n"
            + self.visible["transcript"]
            if status == "ok"
            else f"ASR observation status: {status}. No usable transcription was produced."
        )
        return {
            "type": "text",
            "text": text,
            "evidence_id": self.visible["evidence_id"],
            "source_uri": self.visible["source_uri"],
        }


@dataclass(frozen=True)
class _LoadedObservation:
    visible: Mapping[str, object]
    lineage: Mapping[str, object]


class LoadedSpeechObservationCatalog:
    """A validated, immutable per-roster cache of prepared OBS evidence."""

    def __init__(
        self,
        *,
        catalog_id: str,
        catalog_relpath: str,
        catalog_sha256: str,
        split_identity_hash: str,
        producer: Mapping[str, object],
        observations: Mapping[str, _LoadedObservation],
    ) -> None:
        self._catalog_id = catalog_id
        self._catalog_relpath = catalog_relpath
        self._catalog_sha256 = catalog_sha256
        self._split_identity_hash = split_identity_hash
        self._producer = dict(producer)
        self._observations = dict(observations)

    def select(self, *, context: object) -> SpeechObservationSelection:
        sample_id = getattr(context, "sample_id", None)
        query = getattr(context, "query_state", None)
        if (
            not isinstance(sample_id, str)
            or query is None
            or getattr(query, "query_sample_id", None) != sample_id
            or getattr(query, "use_split_identity_hash", None) != self._split_identity_hash
        ):
            raise SpeechObservationError("selection context has stale sample or split binding")
        observation = self._observations.get(sample_id)
        if observation is None:
            raise SpeechObservationError("selection context sample is outside the catalog")
        visible = observation.visible
        if (
            getattr(query, "speech_packet_id", None) != visible["speech_packet_id"]
            or getattr(query, "speech_packet_sha256", None)
            != visible["speech_packet_sha256"]
        ):
            raise SpeechObservationError("selection context has stale speech packet binding")
        return SpeechObservationSelection(visible=visible, lineage=observation.lineage)

    def receipt(self) -> dict[str, object]:
        return {
            "schema": RECEIPT_SCHEMA,
            "tool_id": PREPARED_SPEECH_OBSERVATION_TOOL,
            "catalog_id": self._catalog_id,
            "catalog_relpath": self._catalog_relpath,
            "catalog_sha256": self._catalog_sha256,
            "use_split_identity_hash": self._split_identity_hash,
            "prepared_count": len(self._observations),
            "producer_run_id": self._producer["run_id"],
            "producer_attempt_id": self._producer["attempt_id"],
            "producer_contacts": dict(self._producer["contacts"]),
            "execution_plan": dict(self._producer["execution_plan"]),
            "protocol_sha256": self._producer["protocol_sha256"],
            "ledger_row": dict(self._producer["ledger_row"]),
        }


def load_speech_observation_catalog(
    config: Mapping[str, object],
    *,
    data_root: Path,
    source_audio_bindings: Mapping[str, Mapping[str, object]],
    split_identity_hash: str,
    repo_root: Path,
) -> LoadedSpeechObservationCatalog | None:
    """Load a complete, finalized cache without touching audio or a decoder."""

    if not isinstance(config, Mapping):
        raise SpeechObservationError("config must be a mapping")
    declaration = config.get("prepared_speech_observations")
    if declaration is None or declaration == {}:
        return None
    normalized_pin, catalog_path = _pinned_file(
        Path(data_root), declaration, "prepared_speech_observations"
    )
    catalog = _read_json(catalog_path, "prepared speech observation catalog")
    catalog_keys = {
        "schema",
        "catalog_id",
        "use_split_identity_hash",
        "checkpoint_receipt",
        "decoding_config_sha256",
        "producer",
        "observations",
    }
    _exact_mapping(catalog, catalog_keys, "speech observation catalog")
    if catalog["schema"] != CATALOG_SCHEMA:
        raise SpeechObservationError("speech observation catalog schema is invalid")
    catalog_id = _text(catalog["catalog_id"], "catalog_id")
    split = _sha(catalog["use_split_identity_hash"], "use_split_identity_hash")
    if split != _sha(split_identity_hash, "split_identity_hash"):
        raise SpeechObservationError("catalog split identity differs from runtime")
    checkpoint, _ = _pinned_file(
        Path(repo_root), catalog["checkpoint_receipt"], "checkpoint_receipt"
    )
    decoding_sha = _sha(catalog["decoding_config_sha256"], "decoding_config_sha256")

    producer = _exact_mapping(
        catalog["producer"],
        {
            "run_id",
            "attempt_id",
            "execution_plan",
            "protocol_sha256",
            "ledger_row",
            "contacts",
        },
        "producer",
    )
    run_id = _text(producer["run_id"], "producer.run_id")
    attempt_id = _text(producer["attempt_id"], "producer.attempt_id")
    plan, execution_plan_pin = _load_execution_plan(Path(repo_root), producer["execution_plan"])
    protocol_sha = _sha(producer["protocol_sha256"], "producer.protocol_sha256")
    if (
        plan.run_id != run_id
        or plan.attempt_id != attempt_id
        or plan.split_identity_hash != split
        or plan.protocol_hash != protocol_sha
    ):
        raise SpeechObservationError("producer identity differs from its execution plan")
    ledger_pin = _ledger_row(Path(repo_root), producer["ledger_row"], plan)
    contacts = _exact_mapping(producer["contacts"], {"calls", "audio_seconds"}, "producer.contacts")
    calls = contacts["calls"]
    if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
        raise SpeechObservationError("producer contacts calls must be a positive integer")
    audio_seconds = _finite_positive(contacts["audio_seconds"], "producer contacts audio_seconds")
    if calls > plan.planned_model_calls or audio_seconds > plan.planned_speech_audio_seconds:
        raise SpeechObservationError("producer actual accounting exceeds the execution plan")

    producer_normalized = {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "execution_plan": execution_plan_pin,
        "protocol_sha256": protocol_sha,
        "ledger_row": ledger_pin,
        "contacts": {"calls": calls, "audio_seconds": audio_seconds},
    }
    attempt_relpath = f"attempts/{run_id}/{attempt_id}.json"
    _, attempt_path = _confined(Path(data_root), attempt_relpath, "attempt state")
    attempt = _read_json(attempt_path, "attempt state")
    if attempt.get("schema") != ATTEMPT_SCHEMA or attempt.get("state") != STATE_FINALIZED:
        raise SpeechObservationError("producer attempt must be FINALIZED under the existing attempt schema")
    if (
        attempt.get("run_id") != run_id
        or attempt.get("attempt_id") != attempt_id
        or attempt.get("carrier_lock_key") != plan.carrier_lock_key
        or attempt.get("contact_kind", "speech") != "speech"
    ):
        raise SpeechObservationError("producer attempt identity differs from the execution plan")
    reserved = attempt.get("reserved")
    actual = attempt.get("actual")
    if not isinstance(reserved, Mapping) or not isinstance(actual, Mapping):
        raise SpeechObservationError("producer attempt lacks reserved or actual accounting")
    reserved_calls = reserved.get("calls")
    actual_calls = actual.get("calls")
    if (
        isinstance(reserved_calls, bool)
        or not isinstance(reserved_calls, int)
        or isinstance(actual_calls, bool)
        or not isinstance(actual_calls, int)
    ):
        raise SpeechObservationError("producer attempt call accounting is invalid")
    reserved_audio = _finite_nonnegative(
        reserved.get("audio_seconds"), "producer reserved audio_seconds"
    )
    actual_audio = _finite_nonnegative(
        actual.get("audio_seconds"), "producer actual audio_seconds"
    )
    actual_gpu = _finite_nonnegative(
        actual.get("gpu_seconds", 0.0), "producer actual gpu_seconds"
    )
    if actual_calls != calls or actual_audio != audio_seconds:
        raise SpeechObservationError("producer attempt actual accounting differs from catalog")
    if (
        actual_calls > reserved_calls
        or reserved_calls > plan.planned_model_calls
        or actual_audio > reserved_audio
        or reserved_audio > plan.planned_speech_audio_seconds
        or actual_gpu > plan.planned_gpu_hours * 3600.0
    ):
        raise SpeechObservationError("producer attempt accounting exceeds a registered budget")
    expected_finalization = {
        "path": normalized_pin["relpath"],
        "sha256": normalized_pin["sha256"],
        "kind": FINALIZATION_KIND,
    }
    if attempt.get("finalization") != expected_finalization:
        raise SpeechObservationError("producer attempt finalization does not bind this catalog")

    rows = catalog["observations"]
    if not isinstance(rows, list) or not rows:
        raise SpeechObservationError("catalog observations must be a non-empty list")
    source_ids = set(source_audio_bindings)
    row_ids = [row.get("sample_id") for row in rows if isinstance(row, Mapping)]
    if len(row_ids) != len(rows) or len(set(row_ids)) != len(row_ids) or set(row_ids) != source_ids:
        raise SpeechObservationError("catalog observation roster differs from the validated source roster")
    if calls < len(rows):
        raise SpeechObservationError(
            "producer accounting must retain at least one contact per observation"
        )
    accounted_duration = 0.0
    for raw_row in rows:
        if not isinstance(raw_row, Mapping):
            raise SpeechObservationError("catalog observations must contain objects")
        accounted_duration += _finite_positive(
            raw_row.get("source_audio_duration_seconds"),
            "observation source duration",
        )
    if audio_seconds + 1e-6 < accounted_duration:
        raise SpeechObservationError(
            "producer audio accounting must cover all full-utterance durations"
        )

    loaded: dict[str, _LoadedObservation] = {}
    row_keys = {
        "sample_id",
        "speech_packet_id",
        "speech_packet_sha256",
        "source_audio_relpath",
        "source_audio_sha256",
        "source_audio_duration_seconds",
        "span",
        "artifact_relpath",
        "artifact_sha256",
        "output_sha256",
    }
    for raw_row in rows:
        row = _exact_mapping(raw_row, row_keys, "observation row")
        sample_id = _text(row["sample_id"], "observation sample_id")
        source = _exact_mapping(
            source_audio_bindings[sample_id],
            {
                "packet_id",
                "packet_sha256",
                "source_audio_relpath",
                "source_audio_sha256",
                "source_audio_duration_seconds",
            },
            "source binding",
        )
        duration = _finite_positive(row["source_audio_duration_seconds"], "source duration")
        claimed_source = {
            "packet_id": row["speech_packet_id"],
            "packet_sha256": row["speech_packet_sha256"],
            "source_audio_relpath": row["source_audio_relpath"],
            "source_audio_sha256": row["source_audio_sha256"],
            "source_audio_duration_seconds": duration,
        }
        if claimed_source != dict(source):
            raise SpeechObservationError("observation source binding differs from runtime")
        _text(row["speech_packet_id"], "speech_packet_id")
        _sha(row["speech_packet_sha256"], "speech_packet_sha256")
        _text(row["source_audio_relpath"], "source_audio_relpath")
        _sha(row["source_audio_sha256"], "source_audio_sha256")
        span = _exact_mapping(row["span"], {"kind", "start_seconds", "end_seconds"}, "span")
        if (
            span["kind"] != "full-utterance"
            or isinstance(span["start_seconds"], bool)
            or float(span["start_seconds"]) != 0.0
            or isinstance(span["end_seconds"], bool)
            or float(span["end_seconds"]) != duration
        ):
            raise SpeechObservationError("observation span must bind the full-utterance duration")
        artifact_relpath, artifact_path = _confined(
            Path(data_root), row["artifact_relpath"], "artifact relpath"
        )
        artifact_sha = _sha(row["artifact_sha256"], "artifact_sha256")
        output_sha = _sha(row["output_sha256"], "output_sha256")
        try:
            _, measured_artifact, _ = hash_stable_file(artifact_path, "speech observation artifact")
        except PreparationError as error:
            raise SpeechObservationError(str(error)) from error
        if measured_artifact != artifact_sha:
            raise SpeechObservationError("speech observation artifact file hash mismatch")
        inputs = _artifact_inputs(
            row,
            {
                **catalog,
                "checkpoint_receipt": checkpoint,
                "decoding_config_sha256": decoding_sha,
            },
            producer_normalized,
        )
        try:
            output = load_artifact(
                artifact_path,
                expected_sha256=artifact_sha,
                kind=ARTIFACT_KIND,
                inputs=inputs,
            )
        except PreparationError as error:
            raise SpeechObservationError(f"prepared artifact identity is invalid: {error}") from error
        wrapper = _read_json(artifact_path, "speech observation artifact")
        if wrapper.get("contact_class") != "speech-tool":
            raise SpeechObservationError("prepared artifact must retain speech-tool contact class")
        if wrapper.get("output_sha256") != output_sha:
            raise SpeechObservationError("prepared artifact output hash differs from catalog")
        output_value = _exact_mapping(
            output,
            {"schema", "status", "transcript", "diagnostics"},
            "speech observation output",
        )
        if output_value["schema"] != OUTPUT_SCHEMA:
            raise SpeechObservationError("speech observation output schema is invalid")
        status = output_value["status"]
        if status not in STATUSES:
            raise SpeechObservationError("speech observation status is invalid")
        transcript = output_value["transcript"]
        if not isinstance(transcript, str):
            raise SpeechObservationError("speech observation transcript must be text")
        if status == "ok" and not transcript.strip():
            raise SpeechObservationError("ok speech observation requires a non-empty transcript")
        if status != "ok" and transcript:
            raise SpeechObservationError("fallback speech observation requires an empty transcript")
        if not isinstance(output_value["diagnostics"], Mapping):
            raise SpeechObservationError("speech observation diagnostics must be a mapping")
        evidence_id = f"speech-observation:{catalog_id}:{sample_id}"
        visible = MappingProxyType(
            {
                "schema": SELECTION_SCHEMA,
                "evidence_id": evidence_id,
                "status": status,
                "transcript": transcript if status == "ok" else _fallback(status),
                "artifact_sha256": artifact_sha,
                "sample_id": sample_id,
                "use_split_identity_hash": split,
                "speech_packet_id": row["speech_packet_id"],
                "speech_packet_sha256": row["speech_packet_sha256"],
                "source_uri": f"prepared-speech-observation://{artifact_sha}/{evidence_id}",
            }
        )
        lineage = MappingProxyType(
            {
                "catalog_id": catalog_id,
                "catalog_relpath": normalized_pin["relpath"],
                "catalog_sha256": normalized_pin["sha256"],
                "artifact_relpath": artifact_relpath,
                "artifact_sha256": artifact_sha,
                "output_sha256": output_sha,
                "source_audio_relpath": row["source_audio_relpath"],
                "source_audio_sha256": row["source_audio_sha256"],
                "source_audio_duration_seconds": duration,
                "span": dict(span),
                "checkpoint_receipt": checkpoint,
                "decoding_config_sha256": decoding_sha,
                "producer_run_id": run_id,
                "producer_attempt_id": attempt_id,
                "execution_plan": execution_plan_pin,
                "protocol_sha256": protocol_sha,
                "ledger_row": ledger_pin,
                "preparation_contacts": {"calls": calls, "audio_seconds": audio_seconds},
            }
        )
        loaded[sample_id] = _LoadedObservation(visible=visible, lineage=lineage)

    return LoadedSpeechObservationCatalog(
        catalog_id=catalog_id,
        catalog_relpath=normalized_pin["relpath"],
        catalog_sha256=normalized_pin["sha256"],
        split_identity_hash=split,
        producer=producer_normalized,
        observations=loaded,
    )


__all__ = [
    "LoadedSpeechObservationCatalog",
    "PREPARED_SPEECH_OBSERVATION_TOOL",
    "SpeechObservationError",
    "SpeechObservationSelection",
    "load_speech_observation_catalog",
]
