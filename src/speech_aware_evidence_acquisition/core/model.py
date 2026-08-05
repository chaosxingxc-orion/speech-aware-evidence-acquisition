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
import math
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from ..contracts import ExecutionPlan, assert_information_boundary
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .base import TRANSPORTS, CoreError, PayloadBindingContext
from .tracing import TraceSink


class FrozenCoreError(RuntimeError):
    """The adapter refuses: unknown arm, allowlist violation, exhausted budget,
    payload<->plan<->split value mismatch (I3), or media confinement (I4)."""


# Shared, pure media-path helpers (R0 repair T3, I4). Deliberately hold no
# object state: the adapter and the transport each call these with THEIR OWN
# root(s), so the transport's confinement check never depends on the adapter
# having run first -- two independent rails, one shared syntax rule.
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def _normalized_relative_path(value: object, label: str) -> str:
    """Reject anything that is not a normalized POSIX relative path: absolute,
    drive-letter, backslash, leading '/', or any '.'/'..' segment. Purely
    syntactic -- touches no filesystem -- so a forged value never reaches
    ``Path.__truediv__`` (whose join silently discards the left side for an
    absolute right side, the reproduced transport defect).

    Also refuses per-segment Windows-only looseness that would still let a
    forged relpath land on a legitimate file even though it is not, by
    itself, an escape: a trailing dot/space (Windows silently strips both
    from a path component, e.g. ``"5000001.mp3."`` -> ``"5000001.mp3"``) and
    a colon inside a segment (NTFS alternate-data-stream syntax)."""

    if not isinstance(value, str) or not value:
        raise FrozenCoreError(f"{label} must be a non-empty string")
    if "\\" in value:
        raise FrozenCoreError(f"{label} must not contain a backslash, got {value!r}")
    if value.startswith("/"):
        raise FrozenCoreError(f"{label} must be relative, got absolute path {value!r}")
    if _DRIVE_PREFIX.match(value):
        raise FrozenCoreError(f"{label} must not carry a drive letter, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise FrozenCoreError(f"{label} contains an empty or traversal segment: {value!r}")
    for part in parts:
        if part.rstrip(". ") != part:
            raise FrozenCoreError(
                f"{label} segment {part!r} has a trailing dot or space (Windows "
                f"silently strips these, so it would not name a normalized path): {value!r}"
            )
        if ":" in part:
            raise FrozenCoreError(
                f"{label} segment {part!r} contains ':' (NTFS alternate-data-stream "
                f"syntax): {value!r}"
            )
    return value


def _resolve_confined(
    join_root: Path, relative: str, confine_root: Path, label: str, *, strict: bool
) -> Path:
    """Join ``relative`` under ``join_root`` and refuse (``FrozenCoreError``) if
    the fully resolved path -- following any symlinks -- lands outside
    ``confine_root`` once both are resolved. ``strict=True`` also requires the
    final path to exist (used by the adapter, which must prove the loader
    fact-checked media is what will be sent); ``strict=False`` tolerates a
    missing leaf so a caller (the transport) can raise its own
    ``FileNotFoundError`` for that case specifically."""

    try:
        confine_resolved = Path(confine_root).resolve(strict=True)
    except OSError as error:
        raise FrozenCoreError(
            f"{label}: confinement root {confine_root} is unavailable: {error}"
        ) from error
    candidate = Path(join_root) / relative
    try:
        resolved = candidate.resolve(strict=strict)
    except OSError as error:
        raise FrozenCoreError(f"{label}: cannot resolve {candidate}: {error}") from error
    if not resolved.is_relative_to(confine_resolved):
        raise FrozenCoreError(
            f"{label} escapes its confined root {confine_root}: {relative!r}"
        )
    return resolved


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
        binding: PayloadBindingContext,
    ) -> None:
        if arm not in ARM_VISIBLE_FIELDS:
            raise FrozenCoreError(
                f"unknown arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}"
            )
        # Fail-closed constructor discipline (R0 repair T3): a binding context
        # is a required argument (no default -- omitting it is a TypeError
        # before this body ever runs) and is itself structurally validated
        # here. There is no "no checks" adapter: every request() call below
        # trusts only what this context says was verified for this run.
        if not isinstance(binding, PayloadBindingContext):
            raise FrozenCoreError(
                "FrozenCoreAdapter requires a PayloadBindingContext binding payload "
                f"values to the verified split and loader facts; got {type(binding).__name__}"
            )
        try:
            binding.validate()
        except CoreError as error:
            raise FrozenCoreError(f"invalid payload binding context: {error}") from error
        if binding.carrier_lock_key != plan.carrier_lock_key:
            raise FrozenCoreError(
                "payload binding context carrier_lock_key "
                f"{binding.carrier_lock_key!r} does not match the execution plan "
                f"carrier_lock_key {plan.carrier_lock_key!r}"
            )
        gate.assert_model_touch_allowed(plan)
        self._plan = plan
        self._arm = arm
        self._allowlist = frozenset(ARM_VISIBLE_FIELDS[arm])
        self._transport = transport
        self._sink = sink
        self._binding = binding
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
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
        ):
            raise FrozenCoreError("payload audio_seconds must be a finite positive number")
        self._enforce_payload_binding(payload, audio_seconds)
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
        # Metering counts the attempt as soon as the budget checks above have
        # passed and the request is about to leave the process — a transport
        # that raises (or returns a malformed response) after being invoked
        # must not be under-reported as free; a sent request is a consumed
        # request regardless of what comes back.
        self._calls_used += 1
        self._audio_seconds_used += float(audio_seconds)
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

    def _enforce_payload_binding(self, payload: Mapping[str, object], audio_seconds: object) -> None:
        """I3/I4: the payload's own claimed values must agree with what the
        driver actually verified for this run (the T1 split + carrier loader
        facts bound at construction), not merely be well-typed. A payload can
        name any carrier, sample, path or audio fact it likes; only what
        ``self._binding`` says was loaded is ever trusted."""

        binding = self._binding
        carrier_lock_key = payload["carrier_lock_key"]
        if carrier_lock_key != self._plan.carrier_lock_key:
            raise FrozenCoreError(
                f"payload carrier_lock_key {carrier_lock_key!r} does not match the "
                f"execution plan carrier_lock_key {self._plan.carrier_lock_key!r}"
            )
        sample_id = payload["sample_id"]
        if not isinstance(sample_id, str) or sample_id not in binding.allowed_sample_ids:
            raise FrozenCoreError(
                f"payload sample_id {sample_id!r} is not in the verified split bound "
                "to this run"
            )
        expected_speech_ref = f"{self._plan.carrier_lock_key}/{sample_id}"
        if payload["speech_ref"] != expected_speech_ref:
            raise FrozenCoreError(
                f"payload speech_ref {payload['speech_ref']!r} does not match the "
                f"expected {expected_speech_ref!r} for carrier_lock_key/sample_id"
            )
        fact_audio_seconds, fact_sample_rate_hz = binding.sample_facts[sample_id]
        if float(audio_seconds) != float(fact_audio_seconds):
            raise FrozenCoreError(
                f"payload audio_seconds {audio_seconds!r} disagrees with the loader "
                f"fact {fact_audio_seconds!r} for sample {sample_id!r}"
            )
        sample_rate_hz = payload["sample_rate_hz"]
        if (
            isinstance(sample_rate_hz, bool)
            or not isinstance(sample_rate_hz, int)
            or sample_rate_hz != fact_sample_rate_hz
        ):
            raise FrozenCoreError(
                f"payload sample_rate_hz {sample_rate_hz!r} disagrees with the loader "
                f"fact {fact_sample_rate_hz!r} for sample {sample_id!r}"
            )
        relative = _normalized_relative_path(payload["media_relpath"], "payload media_relpath")
        _resolve_confined(
            binding.data_root,
            relative,
            binding.carrier_root,
            "payload media_relpath",
            strict=True,
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
        # I4, independent second rail: refuse absolute/backslash/traversal
        # media_relpath and anything resolving outside self._data_root on the
        # transport's OWN authority -- this must hold even if the adapter's
        # binding-context check were somehow bypassed or absent (the
        # reproduced defect: `self._data_root / <absolute path>` silently
        # discards the data root via Path.__truediv__).
        relative = _normalized_relative_path(payload["media_relpath"], "transport media_relpath")
        media = _resolve_confined(
            self._data_root,
            relative,
            self._data_root,
            "transport media_relpath",
            strict=False,
        )
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
