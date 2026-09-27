"""Recover verified legacy and execution-unit terminal delivery windows."""

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


def _replayed_normalised_text(block: object, raw_text: str) -> str:
    """Re-derive a normalised unit's delivered text from its raw response (I7n).

    The receipt must name a registered delivery normaliser, its recorded input
    must be the raw response bytes, the rule must be deterministic, and its
    output must hash to the receipt's recorded output digest.
    """
    from ..core.base import DELIVERY_NORMALISERS, CoreError
    from ..rails import delivery_normalisers as _registrations  # noqa: F401

    receipt = _mapping(block, "delivery normalisation receipt")
    if {"normaliser_id", "input_sha256", "output_sha256"} - set(receipt):
        raise DeliveryWindowsError("delivery normalisation receipt lacks its identity or digests")
    if sha256(raw_text.encode("utf-8")) != receipt["input_sha256"]:
        raise DeliveryWindowsError(
            "delivery normalisation did not run on the recorded model response"
        )
    try:
        rule = DELIVERY_NORMALISERS.resolve(str(receipt["normaliser_id"]))
        first, second = rule(raw_text), rule(raw_text)
    except (CoreError, TypeError, ValueError) as error:
        raise DeliveryWindowsError(f"delivery normaliser cannot be replayed: {error}") from error
    if first.text != second.text:
        raise DeliveryWindowsError("delivery normaliser is not deterministic")
    if sha256(first.text.encode("utf-8")) != receipt["output_sha256"]:
        raise DeliveryWindowsError(
            "delivery normaliser replay differs from its recorded output"
        )
    return first.text


def verified_execution_unit_windows(
    bundle: VerifiedBundle,
) -> dict[str, tuple[WindowSpan, ...]]:
    """Replay recorded unit delivery with the shared pure stitch implementation.

    Consume source and terminal-response custody from the verified bundle.
    Do not reopen audio, model responses outside that bundle, or references.
    Native Solver selection comes from its recorded role-episode receipt.
    """
    import math

    from ..core.bundle import BundleError
    from ..core.bundle.outputs import _verify_outputs_trace_binding
    from ..rails.errors import RailsError
    from ..core.delivery import (
        native_abstention_records, normalize_terminal_response, stitch_execution_unit_results,
    )
    from ..core.model import SliceRecord
    from ..rails.execution_units import ExecutionUnit, ExecutionUnitRoster, execution_unit_scope
    from ..rails.native_episode_receipt import validate_native_episode_delivery_receipt

    if not isinstance(bundle, VerifiedBundle):
        raise TypeError("execution-unit windows require VerifiedBundle")
    if bundle.attempt_state != "FINALIZED" or bundle.manifest.get("status") != "COMPLETED":
        raise DeliveryWindowsError("execution-unit windows require finalized task outputs")
    rows = bundle.outputs_rows
    parents = tuple(row.get("sample_id") for row in rows)
    if (
        not rows or any(not isinstance(parent, str) or not parent for parent in parents)
        or len(set(parents)) != len(parents) or set(parents) != bundle.split_ids
    ):
        raise DeliveryWindowsError("execution-unit outputs must cover the complete parent roster")
    try:
        _verify_outputs_trace_binding(rows, bundle.trace_records)
    except BundleError as error:
        raise DeliveryWindowsError(str(error)) from error
    episodes = {}
    for record_id, record in bundle.trace_records.items():
        if "use_native_episode" not in record:
            continue
        scope = record_id.split("/", 1)[0]
        if scope in episodes:
            raise DeliveryWindowsError("execution unit has duplicate native episode receipts")
        episodes[scope] = _mapping(record["use_native_episode"], "native episode")

    units, terminals, expected_deliveries = [], [], []
    result = {}
    for row in rows:
        parent = row["sample_id"]
        delivery = _mapping(row.get("execution_unit_delivery"), "execution-unit delivery")
        if delivery.get("schema") != "saea-execution-unit-stitched-result-v1":
            raise DeliveryWindowsError("unsupported execution-unit delivery schema")
        sources = delivery.get("sources")
        if not isinstance(sources, list) or not sources:
            raise DeliveryWindowsError("execution-unit delivery has no ordered sources")
        stitch_id = row["request_id"]
        request = _mapping(bundle.trace_records.get(stitch_id + "/request"), "stitch request")
        response = _mapping(bundle.trace_records.get(stitch_id + "/response"), "stitch response")
        use = _mapping(bundle.trace_records.get(stitch_id + "/use"), "stitch USE")
        if (
            request.get("stitch") is not True or response.get("stitch") is not True
            or request.get("stitched_request_ids") != delivery.get("request_ids")
            or request.get("execution_unit_roster_sha256") != delivery.get("execution_unit_roster_sha256")
            or response.get("stitched_from_response_sha256s") != delivery.get("source_response_sha256s")
            or use.get("use_execution_unit_sources") != sources
            or use.get("use_stitched_iterations") != len(sources)
            or use.get("use_response_sha256") != row["response_sha256"]
            or use.get("use_admitted") is not True
        ):
            raise DeliveryWindowsError("execution-unit delivery differs from its stitch trace")
        spans = []
        for index, raw_source in enumerate(sources, start=1):
            source = _mapping(raw_source, "execution-unit source")
            binding = _mapping(source.get("execution_unit_binding"), "execution-unit binding")
            raw_slice = _mapping(binding.get("slice_record"), "execution-unit slice")
            try:
                record = SliceRecord(**{**raw_slice, "preprocess": tuple(raw_slice["preprocess"])})
                unit = ExecutionUnit(
                    binding["parent_sample_id"], binding["request_key"], record,
                    binding.get("speech_packet_id"), binding.get("speech_packet_sha256"),
                ).validate()
            except (KeyError, TypeError, ValueError, RailsError) as error:
                raise DeliveryWindowsError(f"invalid execution-unit binding: {error}") from error
            geometry = (record.start_seconds, record.end_seconds, record.audio_seconds)
            if (
                any(isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) for value in geometry)
                or record.start_seconds < 0 or record.end_seconds <= record.start_seconds
                or record.audio_seconds <= 0
                or isinstance(record.sample_rate_hz, bool)
                or not isinstance(record.sample_rate_hz, int) or record.sample_rate_hz <= 0
                or abs(record.end_seconds - record.start_seconds - record.audio_seconds)
                > 1 / record.sample_rate_hz
                or unit.parent_sample_id != parent
                or source.get("execution_unit_id") != unit.request_key
                or unit.as_json() != binding
            ):
                raise DeliveryWindowsError("execution-unit source geometry or identity changed")
            request_id = source.get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise DeliveryWindowsError("execution-unit source has no terminal request")
            raw_request = _mapping(
                bundle.trace_records.get(request_id + "/request"), "terminal request",
            )
            raw_response = _mapping(
                bundle.trace_records.get(request_id + "/response"), "terminal response",
            )
            text = raw_response.get("text")
            if (
                not isinstance(text, str)
                or raw_request.get("payload_sha256") != source.get("request_sha256")
                or raw_response.get("response_sha256") != source.get("response_sha256")
                or sha256(text.encode("utf-8")) != raw_response.get("response_text_sha256")
            ):
                raise DeliveryWindowsError("terminal request or response differs from delivery")
            raw_text_sha256 = raw_response["response_text_sha256"]
            episode = episodes.get(execution_unit_scope(unit.request_key))
            kind = "direct"
            if episode is not None:
                selected = validate_native_episode_delivery_receipt(
                    episode, episode.get("role_visits"), episode.get("planner_routes"),
                    error_type=DeliveryWindowsError,
                )
                kind = selected.kind
                if kind == "abstention":
                    expected_id, expected_request, expected_response = native_abstention_records(
                        sample_id=parent, source_contact=selected.final_contact,
                        finish_reason=selected.terminal_disposition["finish_reason"],
                    )
                    if (
                        request_id != expected_id or raw_request != expected_request
                        or raw_response != expected_response
                    ):
                        raise DeliveryWindowsError("native abstention differs from shared replay")
                else:
                    contact = selected.final_contact
                    if any(contact.get(key) != value for key, value in (
                        ("request_id", request_id),
                        ("request_sha256", source["request_sha256"]),
                        ("response_sha256", source["response_sha256"]),
                        ("response_text_sha256", raw_text_sha256),
                    )):
                        raise DeliveryWindowsError("delivery is not the recorded native Solver")
            elif (
                request_id + "/native-role-contact" in bundle.trace_records
                or raw_request.get("tool_id") == "native-terminal-abstention-v1"
            ):
                raise DeliveryWindowsError("native unit delivery has no episode receipt")
            # E11/E35: a unit whose episode ran the registered delivery
            # normaliser delivered that rule's output over the recorded raw
            # response, and its source hash names the DELIVERED bytes. Those
            # bytes are re-derived here from the raw response, never trusted.
            normalisation = episode.get("deliver_normaliser") if episode is not None else None
            if normalisation is None:
                delivered_text = text
            elif kind in ("abstention", "context-abstention"):
                raise DeliveryWindowsError(
                    "an abstention cannot carry a delivery normalisation receipt"
                )
            else:
                delivered_text = _replayed_normalised_text(normalisation, text)
            if sha256(delivered_text.encode("utf-8")) != source.get("raw_text_sha256"):
                raise DeliveryWindowsError("terminal request or response differs from delivery")
            if kind != "abstention":
                payload = _mapping(raw_request.get("payload"), "terminal request payload")
                if payload.get("sample_id") != parent or payload.get("request_id") != request_id:
                    raise DeliveryWindowsError("terminal request changed parent or identity")
            saturated, skipped = source.get("saturated"), source.get("skipped")
            if not isinstance(saturated, bool) or not isinstance(skipped, bool):
                raise DeliveryWindowsError("execution-unit terminal flags must be booleans")
            delivered = normalize_terminal_response(
                delivered_text, saturated=saturated, skipped=skipped
            )
            units.append(unit)
            terminals.append({
                "sample_id": parent, "execution_unit_id": unit.request_key,
                "execution_unit_binding": unit.as_json(), "request_id": request_id,
                "request_sha256": source["request_sha256"],
                "response_sha256": source["response_sha256"],
                "response_text_sha256": source["raw_text_sha256"],
                "text": delivered_text, "saturated": saturated, "skipped": skipped,
            })
            spans.append(WindowSpan(
                parent, index, request_id, record.start_seconds, record.end_seconds,
                record.audio_seconds, delivered, saturated,
                execution_unit_id=unit.request_key, delivery_kind=kind, skipped=skipped,
            ))
        result[parent] = tuple(spans)
        expected_deliveries.append(delivery)
    replayed = stitch_execution_unit_results(ExecutionUnitRoster(tuple(units)), parents, terminals)
    if any(actual != expected for actual, expected in zip(replayed, expected_deliveries, strict=True)):
        raise DeliveryWindowsError("execution-unit stitch replay differs from the recorded delivery")
    for row, replay in zip(rows, replayed, strict=True):
        if any(row[key] != replay[key] for key in (
            "sample_id", "text", "request_sha256", "response_sha256", "response_text_sha256",
        )):
            raise DeliveryWindowsError("execution-unit replay differs from scored parent output")
    assert_stitch_reproduces_outputs(result, {row["sample_id"]: row["text"] for row in rows})
    return result


__all__.append("verified_execution_unit_windows")
