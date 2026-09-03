"""One-shot governance around the local batched semantic embedding tool.

The wrapper deliberately stays outside the generic ``EmbeddingClient``.  It
binds the one local Qwen3 embedding service used by the 104-row semantic
flight to its own execution plan and attempt, while preserving the client's
``embed_text_batch`` return value unchanged.  Seven HTTP requests carry 208
logical embedding contacts; those two quantities are both durable and never
silently conflated.

This module performs no contact at import or construction time.  The first
delegated operation opens the supplied ``FrozenCoreGate`` and one attempt.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
from speech_aware_evidence_acquisition.core.attempts import (
    AttemptError,
    AttemptHandle,
    AttemptStore,
    STATE_OPENED,
)
from speech_aware_evidence_acquisition.core.config import (
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (
    TextEmbeddingBatchItem,
    _validate_text_batch_items,
)


EMBEDDING_RUNTIME_RECEIPT_RELPATH = "receipts/runtime-qwen3-embedding-q8.json"
EMBEDDING_MODEL_LOCK_KEY = "qwen3-embedding-0.6b-gguf"
EMBEDDING_RUN_ID = "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED"
LOGICAL_CONTACT_CEILING = 208
PHYSICAL_REQUEST_CEILING = 7
_SHA256 = frozenset("0123456789abcdef")


class GovernedEmbeddingError(RuntimeError):
    """A closed gate, budget violation, malformed batch, or terminal wrapper."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def build_embedding_gate(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    model_root: Path,
    composed_values: Mapping[str, object],
) -> FrozenCoreGate:
    """Build the dedicated local-embedding gate from flight configuration.

    The receipt and model-lock pair are constants for this tool.  The D1
    supplement is derived from the same composed configuration as the
    generation gate, so the fresh 104-row media roster stays bound whenever
    the local encoder is opened.
    """

    return FrozenCoreGate.for_study_repo(
        Path(repo_root),
        Path(data_root),
        Path(runtime_root),
        runtime_receipt_relpath=EMBEDDING_RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=EMBEDDING_MODEL_LOCK_KEY,
        model_root=Path(model_root),
        d1_media_supplement_relpath=d1_media_supplement_relpath(composed_values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(composed_values),
    )


class GovernedEmbeddingClient:
    """Transparent ``embed_text_batch`` wrapper with a separate tool attempt.

    ``planned_model_calls`` records logical embedding contacts (208), matching
    the embedding client's own contact model.  The seven request ceiling is a
    separate transport budget.  Text-only calls consume no speech seconds;
    the positive one-second plan value exists only because the shared
    Stage-2 execution-plan schema requires a positive speech-audio field.
    """

    def __init__(
        self,
        *,
        client: object,
        gate: FrozenCoreGate | object,
        plan: ExecutionPlan,
        preregistration_path: Path,
        preregistration_sha256: str,
        attempts_root: Path,
        receipt_path: Path,
    ) -> None:
        if type(plan) is not ExecutionPlan:
            raise GovernedEmbeddingError("embedding tool requires an exact ExecutionPlan")
        try:
            plan.validate()
        except Exception as error:
            raise GovernedEmbeddingError(f"embedding ExecutionPlan is invalid: {error}") from error
        if plan.planned_model_calls != LOGICAL_CONTACT_CEILING:
            raise GovernedEmbeddingError(
                "embedding ExecutionPlan must reserve exactly 208 logical contacts"
            )
        if plan.run_id != EMBEDDING_RUN_ID:
            raise GovernedEmbeddingError(
                "embedding ExecutionPlan must use the dedicated embedding run identifier"
            )
        if plan.planned_speech_audio_seconds != 1:
            raise GovernedEmbeddingError(
                "embedding ExecutionPlan must use the schema-minimum one speech-audio second"
            )
        if not _is_sha256(preregistration_sha256):
            raise GovernedEmbeddingError("embedding preregistration SHA-256 is malformed")
        if not callable(getattr(client, "embed_text_batch", None)):
            raise GovernedEmbeddingError("underlying client lacks embed_text_batch")
        if not callable(getattr(gate, "assert_model_touch_allowed", None)):
            raise GovernedEmbeddingError("embedding gate lacks assert_model_touch_allowed")

        self.client = client
        self.gate = gate
        self.plan = plan
        self.preregistration_path = Path(preregistration_path)
        self.preregistration_sha256 = preregistration_sha256
        self.store = AttemptStore(Path(attempts_root))
        self.receipt_path = Path(receipt_path)
        self._attempt: AttemptHandle | None = None
        self._gate_lock_sha256: str | None = None
        self._physical_request_count = 0
        self._logical_contact_count = 0
        self._batches: list[dict[str, object]] = []
        self._terminal_receipt: dict[str, object] | None = None

    @property
    def physical_request_count(self) -> int:
        return self._physical_request_count

    @property
    def logical_contact_count(self) -> int:
        return self._logical_contact_count

    @classmethod
    def for_local_semantic_flight(
        cls,
        *,
        client: object,
        plan: ExecutionPlan,
        preregistration_path: Path,
        preregistration_sha256: str,
        attempts_root: Path,
        receipt_path: Path,
        repo_root: Path,
        data_root: Path,
        runtime_root: Path,
        model_root: Path,
        composed_values: Mapping[str, object],
    ) -> "GovernedEmbeddingClient":
        """Create the wrapper with the pinned Qwen3 embedding gate."""

        return cls(
            client=client,
            gate=build_embedding_gate(
                repo_root=repo_root,
                data_root=data_root,
                runtime_root=runtime_root,
                model_root=model_root,
                composed_values=composed_values,
            ),
            plan=plan,
            preregistration_path=preregistration_path,
            preregistration_sha256=preregistration_sha256,
            attempts_root=attempts_root,
            receipt_path=receipt_path,
        )

    def _assert_live(self) -> None:
        if self._terminal_receipt is not None:
            raise GovernedEmbeddingError("embedding wrapper is terminal; no retry is permitted")

    def _validate_preregistration(self) -> None:
        try:
            actual = _sha256_bytes(self.preregistration_path.read_bytes())
        except OSError as error:
            raise GovernedEmbeddingError(
                f"embedding preregistration is unavailable: {error}"
            ) from error
        if actual != self.preregistration_sha256:
            raise GovernedEmbeddingError("embedding preregistration SHA-256 drift")

    def _open_if_needed(self) -> None:
        if self._attempt is not None:
            return
        self._validate_preregistration()
        try:
            result = self.gate.assert_model_touch_allowed(self.plan)
            self._attempt = self.store.open_attempt(
                self.plan.run_id,
                self.plan.attempt_id or "",
                carrier_lock_key=self.plan.carrier_lock_key,
                reserved_calls=LOGICAL_CONTACT_CEILING,
                reserved_audio_seconds=float(self.plan.planned_speech_audio_seconds),
            )
        except Exception as error:
            if isinstance(error, GovernedEmbeddingError):
                raise
            raise GovernedEmbeddingError(f"embedding gate or attempt refused: {error}") from error
        self._gate_lock_sha256 = result if _is_sha256(result) else None

    def _record_logical_contacts(self, count: int) -> None:
        """Durably meter text contacts before the corresponding HTTP request.

        ``AttemptHandle.record_usage`` is intentionally speech-oriented and
        requires positive audio seconds.  This tool is text-only, so it uses
        the same atomic state file while keeping actual speech seconds at
        exactly zero; the receipt states that distinction explicitly.
        """

        assert self._attempt is not None
        document = self._attempt._read()  # noqa: SLF001 - preserves zero text-only audio
        if document.get("state") != STATE_OPENED:
            raise GovernedEmbeddingError("embedding attempt is not open")
        actual = document.get("actual")
        if not isinstance(actual, dict) or not isinstance(actual.get("calls"), int):
            raise GovernedEmbeddingError("embedding attempt actual usage is malformed")
        actual["calls"] += count
        if actual["calls"] > LOGICAL_CONTACT_CEILING:
            raise GovernedEmbeddingError("embedding logical contact budget exceeded")
        if actual.get("audio_seconds") != 0.0:
            raise GovernedEmbeddingError("text-only embedding attempt recorded non-zero audio")
        self._attempt._write(document)  # noqa: SLF001 - atomic durable update

    @staticmethod
    def _request_body(items: Sequence[tuple[str, str, str]]) -> bytes:
        # This is byte-for-byte the body construction in EmbeddingClient.
        return json.dumps(
            {"content": [prefix + text for _contact_id, text, prefix in items]}
        ).encode("utf-8")

    @staticmethod
    def _response_vectors_hash(vectors: Sequence[object]) -> str:
        rows: list[dict[str, object]] = []
        for vector in vectors:
            contact_id = getattr(vector, "contact_id", None)
            kind = getattr(vector, "kind", None)
            values = getattr(vector, "values", None)
            if (
                not isinstance(contact_id, str)
                or kind != "text"
                or isinstance(values, (str, bytes))
                or not isinstance(values, Sequence)
            ):
                raise GovernedEmbeddingError("embedding response vector is malformed")
            try:
                vector_hash = _sha256_bytes(_canonical_json(list(values)))
            except (TypeError, ValueError) as error:
                raise GovernedEmbeddingError("embedding response vector is not JSON-hashable") from error
            rows.append(
                {
                    "contact_id": contact_id,
                    "dimensions": len(values),
                    "vector_sha256": vector_hash,
                }
            )
        return _sha256_bytes(_canonical_json(rows))

    def _write_receipt(self, *, status: str, reason: str | None = None) -> dict[str, object]:
        if status not in {"FINALIZED", "ABORTED"}:
            raise GovernedEmbeddingError("embedding receipt status is invalid")
        document: dict[str, object] = {
            "schema": "saea-governed-embedding-tool-receipt-v1",
            "status": status,
            "closed_at": _utc_now(),
            "run_id": self.plan.run_id,
            "attempt_id": self.plan.attempt_id,
            "execution_plan_sha256": _sha256_bytes(_canonical_json(asdict(self.plan))),
            "preregistration_sha256": self.preregistration_sha256,
            "pinned_runtime_receipt_relpath": "docs/" + EMBEDDING_RUNTIME_RECEIPT_RELPATH,
            "pinned_model_lock_key": EMBEDDING_MODEL_LOCK_KEY,
            "umbrella_lock_sha256": self._gate_lock_sha256,
            "physical_request_ceiling": PHYSICAL_REQUEST_CEILING,
            "physical_request_count": self._physical_request_count,
            "logical_contact_ceiling": LOGICAL_CONTACT_CEILING,
            "logical_contact_count": self._logical_contact_count,
            "actual_speech_audio_seconds": 0,
            "plan_speech_audio_seconds_note": (
                "The shared execution-plan schema requires the positive minimum of one, "
                "but this local embedding tool processes text only and used zero speech seconds."
            ),
            "batches": list(self._batches),
        }
        if reason is not None:
            document["reason"] = reason
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.receipt_path.with_name(self.receipt_path.name + ".tmp")
        try:
            temporary.write_text(
                json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            temporary.replace(self.receipt_path)
        except OSError as error:
            raise GovernedEmbeddingError(f"cannot persist embedding receipt: {error}") from error
        self._terminal_receipt = document
        return document

    def _abort_after_failure(self, reason: str) -> dict[str, object]:
        if self._attempt is not None:
            try:
                self._attempt.mark_aborted(reason)
            except AttemptError:
                pass
        return self._write_receipt(status="ABORTED", reason=reason)

    def verify_media_marker(self) -> Mapping[str, object]:
        """Delegate the optional client check only after the governed gate opens."""

        self._assert_live()
        self._open_if_needed()
        verifier = getattr(self.client, "verify_media_marker", None)
        if not callable(verifier):
            raise GovernedEmbeddingError("underlying client lacks verify_media_marker")
        return verifier()

    def open(self) -> None:
        """Open the gate and one-shot attempt immediately before service start.

        Flight integration calls this after all local validation and directly
        before spawning the embedding service.  ``embed_text_batch`` retains
        a defensive lazy-open path for callers that omit the explicit call.
        """

        self._assert_live()
        self._open_if_needed()

    def embed_text_batch(
        self, items: Sequence[TextEmbeddingBatchItem]
    ) -> tuple[object, ...]:
        """Delegate one exact local batch with pre-send durable accounting."""

        self._assert_live()
        normalized = _validate_text_batch_items(items)
        if self._physical_request_count >= PHYSICAL_REQUEST_CEILING:
            raise GovernedEmbeddingError("embedding physical request budget exceeded")
        if self._logical_contact_count + len(normalized) > LOGICAL_CONTACT_CEILING:
            raise GovernedEmbeddingError("embedding logical contact budget exceeded")
        self._open_if_needed()
        request_body = self._request_body(normalized)
        before = getattr(self.client, "http_request_count", None)
        if not isinstance(before, int) or before < 0:
            raise GovernedEmbeddingError("underlying client lacks a valid physical request count")
        self._record_logical_contacts(len(normalized))
        self._physical_request_count += 1
        self._logical_contact_count += len(normalized)
        batch = {
            "physical_ordinal": self._physical_request_count,
            "logical_contact_count": len(normalized),
            "logical_contact_ids_sha256": _sha256_bytes(
                _canonical_json([contact_id for contact_id, _text, _prefix in normalized])
            ),
            "request_body_sha256": _sha256_bytes(request_body),
            # A failure after transport send has no response vector to hash;
            # preserving this explicit null proves it was not silently omitted.
            "response_vectors_sha256": None,
        }
        self._batches.append(batch)
        try:
            vectors = tuple(self.client.embed_text_batch(normalized))
            after = getattr(self.client, "http_request_count", None)
            if after != before + 1:
                raise GovernedEmbeddingError("underlying client physical request accounting drift")
            if len(vectors) != len(normalized) or tuple(
                getattr(vector, "contact_id", None) for vector in vectors
            ) != tuple(contact_id for contact_id, _text, _prefix in normalized):
                raise GovernedEmbeddingError("embedding response contacts differ from the request")
            batch["response_vectors_sha256"] = self._response_vectors_hash(vectors)
            return vectors
        except Exception as error:
            if self._terminal_receipt is None:
                self._abort_after_failure(f"embedding batch failed: {type(error).__name__}")
            raise

    def close(self) -> dict[str, object]:
        """Close only a complete seven-request, 208-contact tool attempt."""

        self._assert_live()
        if self._attempt is None:
            raise GovernedEmbeddingError("embedding wrapper cannot close before opening")
        if (
            self._physical_request_count != PHYSICAL_REQUEST_CEILING
            or self._logical_contact_count != LOGICAL_CONTACT_CEILING
        ):
            return self._abort_after_failure("embedding close before the exact registered budgets")
        closer = getattr(self.client, "close", None)
        if not callable(closer):
            return self._abort_after_failure("underlying embedding client lacks close")
        try:
            closer()
            self._attempt.mark_finalized()
        except Exception as error:
            if self._terminal_receipt is None:
                return self._abort_after_failure(f"embedding close failed: {type(error).__name__}")
            raise
        return self._write_receipt(status="FINALIZED")

    def abort(self, reason: str) -> dict[str, object]:
        """Durably stop an incomplete tool attempt; never reopen it."""

        self._assert_live()
        if not isinstance(reason, str) or not reason.strip():
            raise GovernedEmbeddingError("embedding abort reason must be non-empty English text")
        return self._abort_after_failure(reason)

    def __getattr__(self, name: str) -> object:
        """Expose read-only client attributes without widening the contact surface."""

        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.client, name)


__all__ = [
    "EMBEDDING_MODEL_LOCK_KEY",
    "EMBEDDING_RUN_ID",
    "EMBEDDING_RUNTIME_RECEIPT_RELPATH",
    "GovernedEmbeddingClient",
    "GovernedEmbeddingError",
    "LOGICAL_CONTACT_CEILING",
    "PHYSICAL_REQUEST_CEILING",
    "build_embedding_gate",
]
