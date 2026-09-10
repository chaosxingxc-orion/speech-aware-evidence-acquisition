"""Recover verified terminal delivery windows from a legacy OBS derivative."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Mapping

from ..core.base import CoreError, RESPONSE_POSTPROCESSORS
from ..core.bundle.artifacts import VerifiedBundle
from ..core.bundle.delivery import DELIVERY_MANIFEST_SCHEMA
from ..core.bundle.delivery_replay import canonical, sha256
from ..core.bundle.verify import verify_bundle
from ..core.delivery import deliver_terminal_response
from ..core.predecessor_snapshot import load_predecessor_binding
from .e21_window_pairing import (
    WindowPairingError,
    WindowSpan,
    assert_stitch_reproduces_outputs,
)


class DeliveryWindowsError(ValueError):
    """A derived OBS delivery cannot be reconstructed from verified provenance."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DeliveryWindowsError(f"{label} must be a mapping")
    return value


def _record_hash(record: Mapping[str, object]) -> str:
    return sha256(canonical(record))


def _parent_bundle(bundle: VerifiedBundle) -> VerifiedBundle:
    parent = _mapping(bundle.manifest.get("parent"), "derived parent")
    path = parent.get("path")
    if not isinstance(path, str) or not path:
        raise DeliveryWindowsError("derived parent has no manifest path")
    try:
        return verify_bundle(Path(path))
    except Exception as error:  # verified parent failures must be explicit
        raise DeliveryWindowsError(
            f"derived parent verification failed: {error}"
        ) from error


def _rule(bundle: VerifiedBundle):
    declaration = _mapping(bundle.manifest.get("declaration"), "delivery declaration")
    if declaration.get("source_selector") is not None:
        raise DeliveryWindowsError(
            "phase_sources delivery is not supported by legacy OBS windows"
        )
    name = declaration.get("response_postprocessor")
    params = declaration.get("response_postprocessor_params")
    if not isinstance(name, str) or not name or not isinstance(params, Mapping):
        raise DeliveryWindowsError(
            "legacy delivery declaration lacks its registered postprocessor"
        )
    try:
        rule = RESPONSE_POSTPROCESSORS.resolve(name)(**params)
    except (CoreError, KeyError, TypeError, ValueError) as error:
        raise DeliveryWindowsError(
            f"delivery postprocessor cannot be resolved: {error}"
        ) from error
    if not callable(rule):
        raise DeliveryWindowsError(
            "delivery postprocessor factory did not return a callable"
        )
    return rule


def _snapshot(bundle: VerifiedBundle):
    receipt = _mapping(
        bundle.manifest.get("predecessor_receipt"), "predecessor_receipt"
    )
    path, digest = receipt.get("path"), receipt.get("sha256")
    data_root = bundle.manifest.get("data_root")
    if (
        not isinstance(path, str)
        or not isinstance(digest, str)
        or not isinstance(data_root, str)
    ):
        raise DeliveryWindowsError(
            "legacy delivery lacks a pinned predecessor receipt or data root"
        )
    try:
        return load_predecessor_binding(
            Path(path), Path(data_root), expected_receipt_sha256=digest
        )
    except Exception as error:
        raise DeliveryWindowsError(f"predecessor binding failed: {error}") from error


def _source_windows(bundle: VerifiedBundle) -> dict[str, list[Mapping[str, object]]]:
    if bundle.manifest.get("schema") != DELIVERY_MANIFEST_SCHEMA:
        raise DeliveryWindowsError(
            "delivery windows require a saea-derived-delivery-v1 bundle"
        )
    if "phase_sources" in bundle.manifest:
        raise DeliveryWindowsError(
            "phase_sources delivery is not supported by legacy OBS windows"
        )
    raw = bundle.manifest.get("windows")
    if not isinstance(raw, list) or not raw:
        raise DeliveryWindowsError("legacy delivery bundle has no window provenance")
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    for item in raw:
        window = _mapping(item, "delivery window")
        sample_id, index = window.get("sample_id"), window.get("window_index")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or isinstance(index, bool)
            or not isinstance(index, int)
        ):
            raise DeliveryWindowsError("delivery window has no usable sample or index")
        key = (sample_id, index)
        if key in seen:
            raise DeliveryWindowsError("delivery window repeats a sample/index")
        seen.add(key)
        grouped[sample_id].append(window)
    for windows in grouped.values():
        windows.sort(key=lambda item: int(item["window_index"]))
    return dict(grouped)


def verified_delivery_windows(
    bundle: VerifiedBundle,
) -> dict[str, tuple[WindowSpan, ...]]:
    """Return delivered legacy-OBS windows from a verified derivative bundle.

    The derivative manifest selects the terminal request for every window. Its
    parent trace supplies only the raw terminal response and OBS bounds; derived
    text is recomputed with the registered pure delivery rule and is never read
    from that parent trace as if it were free or constrained delivery output.
    """
    if not isinstance(bundle, VerifiedBundle):
        raise TypeError("verified_delivery_windows requires VerifiedBundle")
    sources = _source_windows(bundle)
    parent = _parent_bundle(bundle)
    snapshot = _snapshot(bundle)
    rule = _rule(bundle)
    output_text: dict[str, str] = {}
    for row in bundle.outputs_rows:
        sample_id, text = row.get("sample_id"), row.get("text")
        if (
            not isinstance(sample_id, str)
            or not isinstance(text, str)
            or sample_id in output_text
        ):
            raise DeliveryWindowsError(
                "derived outputs have invalid sample/text coverage"
            )
        output_text[sample_id] = text
    if set(sources) != set(output_text):
        raise DeliveryWindowsError(
            "derived window provenance and outputs cover different samples"
        )

    result: dict[str, tuple[WindowSpan, ...]] = {}
    for sample_id, entries in sources.items():
        predecessors = snapshot.for_sample(sample_id)
        if len(entries) != len(predecessors):
            raise DeliveryWindowsError(
                "delivery window count differs from pinned predecessor"
            )
        spans: list[WindowSpan] = []
        for predecessor, source in zip(predecessors, entries):
            request_id = source.get("terminal_request_id")
            if (
                source.get("window_id") != predecessor.window_id
                or source.get("window_index") != predecessor.window_index
                or source.get("predecessor_text_sha256") != predecessor.text_sha256
                or not isinstance(request_id, str)
            ):
                raise DeliveryWindowsError(
                    "delivery window differs from pinned predecessor"
                )
            request = parent.trace_records.get(f"{request_id}/request")
            obs = parent.trace_records.get(f"{request_id}/obs")
            if not isinstance(request, Mapping) or not isinstance(obs, Mapping):
                raise DeliveryWindowsError(
                    "terminal delivery window lacks parent request or OBS record"
                )
            payload = request.get("payload")
            if (
                not isinstance(payload, Mapping)
                or payload.get("request_id") != request_id
                or payload.get("sample_id") != sample_id
                or source.get("request_record_sha256") != _record_hash(request)
                or source.get("obs_record_sha256") != _record_hash(obs)
            ):
                raise DeliveryWindowsError(
                    "terminal delivery request or OBS hash mismatch"
                )
            skipped, saturated = obs.get("obs_skipped"), obs.get("obs_saturated")
            if not isinstance(skipped, bool) or not isinstance(saturated, bool):
                raise DeliveryWindowsError(
                    "terminal OBS lacks skip or saturation state"
                )
            if (
                source.get("skipped") != skipped
                or source.get("saturated") != saturated
                or source.get("retry_of") != obs.get("obs_retry_of")
                or obs.get("obs_repair_predecessor_window_id") != predecessor.window_id
                or obs.get("obs_repair_predecessor_text_sha256")
                != predecessor.text_sha256
                or abs(
                    float(obs.get("obs_window_start_seconds"))
                    - predecessor.start_seconds
                )
                > 1e-6
                or abs(
                    float(obs.get("obs_window_end_seconds")) - predecessor.end_seconds
                )
                > 1e-6
            ):
                raise DeliveryWindowsError(
                    "terminal delivery metadata differs from parent OBS"
                )
            response = parent.trace_records.get(f"{request_id}/response")
            if skipped:
                if (
                    response is not None
                    or source.get("response_record_sha256") is not None
                ):
                    raise DeliveryWindowsError("skipped terminal window has a response")
                text = None
            else:
                if not isinstance(response, Mapping) or not isinstance(
                    response.get("text"), str
                ):
                    raise DeliveryWindowsError("terminal delivery response is missing")
                text = response["text"]
                if source.get("response_record_sha256") != _record_hash(
                    response
                ) or sha256(text.encode("utf-8")) != response.get(
                    "response_text_sha256"
                ):
                    raise DeliveryWindowsError(
                        "terminal delivery response hash mismatch"
                    )
            outcome = deliver_terminal_response(
                predecessor.text,
                text,
                rule=rule,
                saturated=saturated,
                skipped=skipped,
            )
            if source.get("delivered_text_sha256") != sha256(
                outcome.text.encode("utf-8")
            ):
                raise DeliveryWindowsError("derived delivery text hash mismatch")
            spans.append(
                WindowSpan(
                    sample_id=sample_id,
                    window_index=predecessor.window_index,
                    request_id=request_id,
                    start_seconds=predecessor.start_seconds,
                    end_seconds=predecessor.end_seconds,
                    audio_seconds=predecessor.audio_seconds,
                    text=outcome.text,
                    saturated=saturated,
                )
            )
        result[sample_id] = tuple(spans)
    try:
        assert_stitch_reproduces_outputs(result, output_text)
    except WindowPairingError as error:
        raise DeliveryWindowsError(
            f"derived windows do not rebuild outputs: {error}"
        ) from error
    return result


__all__ = ["DeliveryWindowsError", "verified_delivery_windows"]
