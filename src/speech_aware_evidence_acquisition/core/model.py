"""Frozen-core adapter and transports: the ONLY model request path (R0).

Discipline (docs/engineering.md): the gate is checked in the same process
that sends requests (no check-then-run-elsewhere TOCTOU gap); the D2 per-arm
visible-field allowlist is enforced as an exact key set on every request —
the choke point that makes a leakage a hard error rather than a convention.
The real llama-server endpoint shape is confirmed at R0 smoke time against
the receipt-pinned build — tests inject `post` and never open a socket.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from ..contracts import ExecutionPlan, assert_information_boundary
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .base import TRANSPORTS
from .tracing import TraceSink


class FrozenCoreError(RuntimeError):
    """The adapter refuses: unknown arm, allowlist violation, or exhausted budget."""


# The exact set of decoding_params keys the frozen core will ever accept. This is
# the governance choke point (FrozenCoreAdapter.request): a config-supplied
# decoding_params mapping can never smuggle a "messages"/"model"/"stream"/... key
# through to the transport, where it would otherwise silently replace the
# constructed chat-completions body (dropping audio while the adapter still
# meters it as delivered).
ALLOWED_DECODING_KEYS = frozenset(
    {
        "temperature",
        "seed",
        "top_p",
        "top_k",
        "min_p",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
    }
)


@dataclass(frozen=True)
class CoreResponse:
    text: str
    usage: Mapping[str, int]
    request_sha256: str
    response_sha256: str
    latency_seconds: float


def _canonical(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class FrozenCoreAdapter:
    def __init__(
        self,
        gate: object,
        plan: ExecutionPlan,
        arm: str,
        transport: Callable[[bytes], bytes],
        sink: TraceSink,
    ) -> None:
        if arm not in ARM_VISIBLE_FIELDS:
            raise FrozenCoreError(
                f"unknown arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}"
            )
        gate.assert_model_touch_allowed(plan)
        self._plan = plan
        self._arm = arm
        self._allowlist = frozenset(ARM_VISIBLE_FIELDS[arm])
        self._transport = transport
        self._sink = sink
        self._calls_used = 0
        self._audio_seconds_used = 0.0
        self._latency_total = 0.0
        self._prompt_tokens = 0
        self._completion_tokens = 0

    def request(self, payload: Mapping[str, object]) -> CoreResponse:
        keys = set(payload)
        if keys != self._allowlist:
            raise FrozenCoreError(
                f"arm {self._arm!r} allowlist violation: "
                f"extra={sorted(keys - self._allowlist)} "
                f"missing={sorted(self._allowlist - keys)}"
            )
        if "decoding_params" in self._allowlist:
            decoding_params = payload["decoding_params"]
            if not isinstance(decoding_params, Mapping):
                raise FrozenCoreError("payload decoding_params must be a mapping")
            disallowed_decoding_keys = set(decoding_params) - ALLOWED_DECODING_KEYS
            if disallowed_decoding_keys:
                raise FrozenCoreError(
                    "payload decoding_params contains disallowed keys: "
                    f"{sorted(disallowed_decoding_keys)}"
                )
        assert_information_boundary(dict(payload))
        audio_seconds = payload["audio_seconds"]
        if not isinstance(audio_seconds, (int, float)) or audio_seconds <= 0:
            raise FrozenCoreError("payload audio_seconds must be a positive number")
        if self._calls_used + 1 > self._plan.planned_model_calls:
            raise FrozenCoreError(
                f"call budget exhausted: plan {self._plan.run_id} allows "
                f"{self._plan.planned_model_calls} calls"
            )
        if (
            self._audio_seconds_used + float(audio_seconds)
            > self._plan.planned_speech_audio_seconds
        ):
            raise FrozenCoreError(
                f"audio budget exhausted: plan {self._plan.run_id} allows "
                f"{self._plan.planned_speech_audio_seconds} speech audio seconds"
            )
        request_id = str(payload["request_id"])
        request_bytes = _canonical(payload)
        request_sha256 = hashlib.sha256(request_bytes).hexdigest()
        self._sink.emit(
            "MODEL_REQUEST",
            f"{request_id}/request",
            {"arm": self._arm, "payload": dict(payload), "payload_sha256": request_sha256},
        )
        started = time.monotonic()
        response_bytes = self._transport(request_bytes)
        latency = time.monotonic() - started
        response_sha256 = hashlib.sha256(response_bytes).hexdigest()
        try:
            parsed = json.loads(response_bytes.decode("utf-8"))
            text = parsed["text"]
            usage = {str(k): int(v) for k, v in dict(parsed.get("usage", {})).items()}
        except (KeyError, TypeError, ValueError, UnicodeError) as error:
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        self._sink.emit(
            "MODEL_RESPONSE",
            f"{request_id}/response",
            {"response_sha256": response_sha256, "text": text, "usage": usage},
        )
        self._calls_used += 1
        self._audio_seconds_used += float(audio_seconds)
        self._latency_total += latency
        self._prompt_tokens += usage.get("prompt_tokens", 0)
        self._completion_tokens += usage.get("completion_tokens", 0)
        self._sink.emit(
            "COST",
            f"{request_id}/cost",
            {
                "calls": 1,
                "audio_seconds": float(audio_seconds),
                "latency_seconds": latency,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        )
        return CoreResponse(
            text=text,
            usage=usage,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            latency_seconds=latency,
        )

    def cost_summary(self) -> dict[str, object]:
        return {
            "calls_used": self._calls_used,
            "audio_seconds_used": self._audio_seconds_used,
            "latency_seconds_total": self._latency_total,
            "prompt_tokens_total": self._prompt_tokens,
            "completion_tokens_total": self._completion_tokens,
        }


def _default_post(timeout_seconds: float) -> Callable[[str, bytes], bytes]:
    def post(url: str, body: bytes) -> bytes:
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


class LlamaServerTransport:
    def __init__(
        self,
        base_url: str,
        data_root: Path,
        timeout_seconds: float = 300.0,
        post: Callable[[str, bytes], bytes] | None = None,
    ) -> None:
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._data_root = Path(data_root)
        self._post = post or _default_post(timeout_seconds)

    def __call__(self, request_bytes: bytes) -> bytes:
        payload: Mapping[str, object] = json.loads(request_bytes.decode("utf-8"))
        media = self._data_root / str(payload["media_relpath"])
        if not media.is_file():
            raise FileNotFoundError(f"media missing for transport: {media}")
        audio_b64 = base64.b64encode(media.read_bytes()).decode("ascii")
        content: list[dict[str, object]] = [
            {
                "type": "input_audio",
                "input_audio": {"data": audio_b64, "format": media.suffix.lstrip(".").lower()},
            }
        ]
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                content.append(
                    {"type": "text", "text": f"[evidence {item['evidence_id']}] {item['content']}"}
                )
        body: dict[str, object] = {
            "messages": [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ],
        }
        for key, value in dict(payload.get("decoding_params", {})).items():  # type: ignore[arg-type]
            if key in body:
                raise FrozenCoreError(
                    f"decoding_params key {key!r} collides with the constructed "
                    "request body and would silently override it"
                )
            body[key] = value
        raw = self._post(self._url, json.dumps(body).encode("utf-8"))
        try:
            parsed = json.loads(raw.decode("utf-8"))
            text = parsed["choices"][0]["message"]["content"]
            usage = {str(k): int(v) for k, v in dict(parsed.get("usage", {})).items()}
        except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as error:
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        return json.dumps({"text": text, "usage": usage}).encode("utf-8")


def _llama_server_factory(values: Mapping[str, object], data_root: Path):
    return LlamaServerTransport(
        str(values["base_url"]), data_root, float(values.get("timeout_seconds", 300.0))
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
