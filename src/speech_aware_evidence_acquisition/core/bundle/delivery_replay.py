"""Deterministic full-window delivery over an already verified parent trace.

Terminal OBS records define coverage, including exhausted windows omitted from
stitched_request_ids. No alternate retry or response is selected by quality.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from ..base import RESPONSE_POSTPROCESSORS
from ..delivery import (
    deliver_terminal_response,
    normalize_terminal_response,
    terminal_response_saturated,
)
from ..predecessor_snapshot import PredecessorSnapshot
from . import BundleError
from .artifacts import VerifiedBundle


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _request(parent, request_id, sample_id):
    request = parent.trace_records.get(f"{request_id}/request")
    if not isinstance(request, Mapping) or not isinstance(
        request.get("payload"), Mapping
    ):
        raise BundleError("terminal OBS lacks its actual model request")
    payload = request["payload"]
    if payload.get("request_id") != request_id or payload.get("sample_id") != sample_id:
        raise BundleError("terminal request identity disagrees with window sample")
    if sha256(canonical(payload)) != request.get("payload_sha256"):
        raise BundleError("terminal request payload hash mismatch")
    return request


def replay_delivery(
    parent: VerifiedBundle,
    snapshot: PredecessorSnapshot,
    declaration: Mapping,
    values: Mapping,
) -> tuple[list[dict], list[dict]]:
    """Recompute whole-call outputs and a content-free, all-window receipt."""
    rule = RESPONSE_POSTPROCESSORS.resolve(declaration["response_postprocessor"])(
        **declaration["response_postprocessor_params"]
    )
    max_tokens = values.get("decoding_params", {}).get("max_tokens")
    rows, windows = [], []
    consumed_obs = set()
    for source_row in parent.outputs_rows:
        sample_id, root_id = source_row["sample_id"], source_row["request_id"]
        predecessors = snapshot.for_sample(sample_id)
        terminal = {}
        for record_id, obs in parent.trace_records.items():
            if not record_id.startswith(f"{root_id}-i") or not record_id.endswith(
                "/obs"
            ):
                continue
            if (
                not obs.get("obs_repair")
                or obs.get("obs_relisten")
                or obs.get("obs_boundary_mode") != "fixed"
            ):
                raise BundleError("delivery replay requires full fixed repair windows")
            iteration = obs.get("obs_iteration")
            if (
                isinstance(iteration, bool)
                or not isinstance(iteration, int)
                or iteration in terminal
            ):
                raise BundleError(
                    "terminal OBS has invalid or duplicate window iteration"
                )
            terminal[iteration] = (record_id[:-4], obs)
            consumed_obs.add(record_id)
        if set(terminal) != set(range(len(predecessors))):
            raise BundleError(
                "terminal OBS coverage does not match all predecessor windows"
            )
        delivered, contacted = [], []
        for iteration, predecessor in enumerate(predecessors):
            request_id, obs = terminal[iteration]
            base = f"{root_id}-i{iteration:04d}"
            if (
                re.fullmatch(re.escape(base) + r"(?:-r[1-9][0-9]*)?", request_id)
                is None
            ):
                raise BundleError(
                    "terminal request id disagrees with its window iteration"
                )
            retry_of = base if request_id != base else None
            if obs.get("obs_retry_of") != retry_of:
                raise BundleError("terminal retry ancestry mismatch")
            if (
                obs.get("obs_repair_predecessor_window_id") != predecessor.window_id
                or obs.get("obs_repair_predecessor_text_sha256")
                != predecessor.text_sha256
            ):
                raise BundleError("terminal OBS predecessor binding mismatch")
            if (
                abs(float(obs["obs_window_start_seconds"]) - predecessor.start_seconds)
                > 1e-6
                or abs(float(obs["obs_window_end_seconds"]) - predecessor.end_seconds)
                > 1e-6
            ):
                raise BundleError(
                    "terminal OBS window bounds differ from bound predecessor"
                )
            request = _request(parent, request_id, sample_id)
            skipped, saturated = obs.get("obs_skipped"), obs.get("obs_saturated")
            if not isinstance(skipped, bool) or not isinstance(saturated, bool):
                raise BundleError("terminal OBS lacks explicit skip/saturation state")
            response = parent.trace_records.get(f"{request_id}/response")
            if skipped:
                if response is not None or saturated:
                    raise BundleError(
                        "exhausted terminal window must not fabricate a response"
                    )
                text = None
            else:
                if not isinstance(response, Mapping) or not isinstance(
                    response.get("text"), str
                ):
                    raise BundleError("successful terminal window lacks its response")
                text = response["text"]
                if sha256(text.encode("utf-8")) != response.get("response_text_sha256"):
                    raise BundleError("terminal response text hash mismatch")
                if (
                    terminal_response_saturated(response.get("usage"), max_tokens)
                    != saturated
                ):
                    raise BundleError(
                        "terminal saturation disagrees with configured cap and usage"
                    )
                contacted.append(request_id)
            normalized = normalize_terminal_response(
                text, saturated=saturated, skipped=skipped
            )
            outcome = deliver_terminal_response(
                predecessor.text, text, rule=rule, saturated=saturated, skipped=skipped
            )
            delivered.append(outcome.text)
            windows.append(
                {
                    "sample_id": sample_id,
                    "window_id": predecessor.window_id,
                    "window_index": predecessor.window_index,
                    "terminal_request_id": request_id,
                    "retry_of": retry_of,
                    "skipped": skipped,
                    "saturated": saturated,
                    "request_record_sha256": sha256(canonical(request)),
                    "response_record_sha256": None
                    if response is None
                    else sha256(canonical(response)),
                    "obs_record_sha256": sha256(canonical(obs)),
                    "predecessor_text_sha256": predecessor.text_sha256,
                    "normalized_input_sha256": sha256(normalized.encode("utf-8")),
                    "delivered_text_sha256": sha256(outcome.text.encode("utf-8")),
                    "refusal_reason": outcome.refusal_reason,
                }
            )
        root_request = parent.trace_records[f"{root_id}/request"]
        if root_request.get("stitched_request_ids") != contacted:
            raise BundleError(
                "terminal non-skipped windows disagree with parent stitch order"
            )
        text = " ".join(span for span in delivered if span)
        rows.append(
            {
                "request_id": f"{root_id}/delivery/{declaration['cell_id']}",
                "sample_id": sample_id,
                "carrier_lock_key": source_row["carrier_lock_key"],
                "arm": source_row["arm"],
                "text": text,
                "admitted": source_row["admitted"],
                "delivery_text_sha256": sha256(text.encode("utf-8")),
                "source_request_id": root_id,
                "source_output_sha256": sha256(canonical(source_row)),
            }
        )
    all_repair_obs = {
        rid
        for rid, payload in parent.trace_records.items()
        if rid.endswith("/obs") and payload.get("obs_repair")
    }
    if consumed_obs != all_repair_obs:
        raise BundleError("parent has unaccounted terminal repair windows")
    return rows, windows
