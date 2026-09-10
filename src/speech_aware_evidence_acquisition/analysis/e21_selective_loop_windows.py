"""Recover every fixed window of a verified selective re-listen delivery.

The pinned plan chooses terminal contacts. The live repair hook reconstructs
selected word ranges and all predecessor backfills; no alternate answer is chosen.
"""
from __future__ import annotations

import math
import re
import subprocess
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

from ..core.base import RESPONSE_POSTPROCESSORS
from ..core.bundle.artifacts import VerifiedBundle
from ..core.bundle.delivery_replay import _request
from ..core.config import compose, effective_request_values
from ..core.delivery import normalize_terminal_response, terminal_response_saturated
from ..core.predecessor_snapshot import binding_from_values, load_predecessor_binding
from ..reproduction.obs_loop import OBS_RELISTEN_PLAN_SCHEMA, _load_unit_plan
from ..reproduction.repair_loop import REPAIR_FRAMES, RepairWindowHook
from .e21_window_pairing import (
    WindowPairingError,
    WindowSpan,
    assert_stitch_reproduces_outputs,
)


class SelectiveLoopWindowsError(ValueError):
    """A selective delivery disagrees with its sealed sources or live rule."""


def _values(bundle: VerifiedBundle, repo_root: Path) -> Mapping:
    commit = bundle.manifest.get("study_commit")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise SelectiveLoopWindowsError("bundle lacks recorded study commit")
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise SelectiveLoopWindowsError("retained source checkout unavailable") from error
    if head != commit:
        raise SelectiveLoopWindowsError("retained source is not bundle study commit")
    config = bundle.manifest.get("config", {})
    fragments = config.get("fragments") if isinstance(config, Mapping) else None
    if not isinstance(fragments, Mapping) or set(fragments) != {
        "model", "dataset", "baseline", "experiment",
    }:
        raise SelectiveLoopWindowsError("bundle lacks exact fragment identities")
    composed = compose(repo_root, **fragments)
    if composed.config_hash != config.get("config_hash"):
        raise SelectiveLoopWindowsError("retained config differs from bundle")
    values = effective_request_values(composed.values)
    if values.get("policy") not in {"obs-repair-loop", "obs-repair-loop-ojw"}:
        raise SelectiveLoopWindowsError("bundle is not selective repair LOOP")
    if not values.get("obs_unit_plan"):
        raise SelectiveLoopWindowsError("selective repair has no pinned unit plan")
    return values


def _same_number(actual, expected, label: str) -> None:
    if (
        isinstance(actual, bool) or not isinstance(actual, (int, float))
        or not math.isfinite(actual) or abs(actual - expected) > 1e-6
    ):
        raise SelectiveLoopWindowsError(f"OBS {label} differs from pinned plan")


def _terminal_records(bundle: VerifiedBundle, root: str, count: int) -> dict:
    records = {}
    for key, obs in bundle.trace_records.items():
        if not key.startswith(f"{root}-i") or not key.endswith("/obs"):
            continue
        iteration = obs.get("obs_iteration")
        if (
            isinstance(iteration, bool) or not isinstance(iteration, int)
            or iteration < 0 or iteration >= count or iteration in records
        ):
            raise SelectiveLoopWindowsError("invalid, duplicate or extra terminal OBS")
        request_id = key[:-4]
        base = f"{root}-i{iteration:04d}"
        if re.fullmatch(re.escape(base) + r"(?:-r[1-9][0-9]*)?", request_id) is None:
            raise SelectiveLoopWindowsError("terminal request id disagrees with iteration")
        if obs.get("obs_retry_of") != (base if request_id != base else None):
            raise SelectiveLoopWindowsError("terminal retry ancestry mismatch")
        records[iteration] = (request_id, obs)
    if set(records) != set(range(count)):
        raise SelectiveLoopWindowsError("unit lacks exactly one terminal OBS")
    return records


def verified_selective_loop_windows(
    bundle: VerifiedBundle, *, repo_root: Path, data_root: Path,
) -> dict[str, tuple[WindowSpan, ...]]:
    """Verify live selective delivery and return the full predecessor window grid.

    repo_root and data_root locate retained bytes only. The manifest's composed
    configuration and its pinned loaders remain the authority for every choice.
    """
    if not isinstance(bundle, VerifiedBundle):
        raise TypeError("verified_selective_loop_windows requires VerifiedBundle")
    if bundle.manifest.get("schema") != "saea-run-manifest-v1":
        raise SelectiveLoopWindowsError("selective windows require an ordinary run bundle")
    values = _values(bundle, Path(repo_root))
    relpath, digest = binding_from_values(values)
    snapshot = load_predecessor_binding(
        Path(repo_root) / "docs" / relpath, Path(data_root),
        expected_receipt_sha256=digest,
    )
    plan = _load_unit_plan(
        Path(repo_root), str(values["obs_unit_plan"]),
        str(values["obs_unit_plan_sha256"]), float(values["obs_buffer_seconds"]),
    )
    if plan.schema != OBS_RELISTEN_PLAN_SCHEMA:
        raise SelectiveLoopWindowsError("unit plan is not a selective re-listen plan")
    rule = RESPONSE_POSTPROCESSORS.resolve(str(values["response_postprocessor"]))(
        **(values.get("response_postprocessor_params") or {})
    )
    frame = REPAIR_FRAMES[str(values.get("repair_frame", "e21-entity-repair-frame-v1"))]
    max_tokens = values.get("decoding_params", {}).get("max_tokens")
    output_text = {}
    for row in bundle.outputs_rows:
        sample, text = row.get("sample_id"), row.get("text")
        if not isinstance(sample, str) or not isinstance(text, str) or sample in output_text:
            raise SelectiveLoopWindowsError("ordinary outputs have invalid sample/text coverage")
        output_text[sample] = text
    if (
        set(output_text) != set(bundle.split_ids)
        or set(output_text) != set(plan.units_by_sample)
    ):
        raise SelectiveLoopWindowsError("ordinary outputs and plan do not cover verified roster")

    result, consumed = {}, set()
    for row in bundle.outputs_rows:
        sample, root = row["sample_id"], row["request_id"]
        predecessors = snapshot.for_sample(sample)
        units = plan.units_for(sample, predecessors[-1].end_seconds)
        terminal = _terminal_records(bundle, root, len(units))
        hook = RepairWindowHook(
            sample_id=sample, predecessors=predecessors, frame=frame, rule=rule, units=units,
        )
        spans = [
            WindowSpan(
                sample, p.window_index, f"{snapshot.run_id}/{p.request_id}",
                p.start_seconds, p.end_seconds, p.audio_seconds, p.text, p.saturated,
            )
            for p in predecessors
        ]
        contacted = []
        prior_parent = 0
        for iteration, unit in enumerate(units):
            request_id, obs = terminal[iteration]
            consumed.add(f"{request_id}/obs")
            index = unit.parent_window_index
            if (
                isinstance(index, bool) or not isinstance(index, int)
                or not prior_parent < index <= len(predecessors)
            ):
                raise SelectiveLoopWindowsError("plan parent index is not unique and ascending")
            prior_parent = index
            parent = predecessors[index - 1]
            expected = {
                "obs_repair": True, "obs_relisten": True,
                "obs_boundary_mode": "fixed", "obs_unit_id": unit.unit_id,
                "obs_relisten_parent_window_index": index,
                "obs_relisten_predecessor_word_start": unit.predecessor_word_start,
                "obs_relisten_predecessor_word_end": unit.predecessor_word_end,
                "obs_repair_predecessor_window_id": parent.window_id,
                "obs_repair_predecessor_text_sha256": parent.text_sha256,
            }
            for name, value in expected.items():
                if obs.get(name) != value or type(obs.get(name)) is not type(value):
                    raise SelectiveLoopWindowsError(f"OBS {name} binding mismatch")
            request = _request(bundle, request_id, sample)["payload"]
            rate = request.get("sample_rate_hz")
            if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
                raise SelectiveLoopWindowsError("request sample rate is missing or invalid")
            # The shared cutter rounds planned seconds to PCM sample frames.
            # Compare exact frame boundaries, never relax the tolerance to hide drift.
            cut_start = round(unit.cut_start_seconds * rate) / rate
            cut_end = min(
                round(unit.cut_end_seconds * rate),
                round(predecessors[-1].end_seconds * rate),
            ) / rate
            _same_number(obs.get("obs_window_start_seconds"), cut_start, "start")
            _same_number(obs.get("obs_window_end_seconds"), cut_end, "end")
            _same_number(
                obs.get("obs_relisten_recut_seconds"), cut_end - cut_start, "recut duration",
            )
            _same_number(
                request.get("audio_seconds"), cut_end - cut_start, "request audio duration",
            )
            if request.get("decoding_params", {}).get("max_tokens") != max_tokens:
                raise SelectiveLoopWindowsError("terminal output cap differs from config")
            skipped, saturated = obs.get("obs_skipped"), obs.get("obs_saturated")
            if not isinstance(skipped, bool) or not isinstance(saturated, bool):
                raise SelectiveLoopWindowsError("OBS skip/saturation missing")
            response = bundle.trace_records.get(f"{request_id}/response")
            if skipped:
                if response is not None or saturated:
                    raise SelectiveLoopWindowsError("skipped request has response or saturation")
                raw = None
            else:
                if not isinstance(response, Mapping) or not isinstance(response.get("text"), str):
                    raise SelectiveLoopWindowsError("terminal response missing")
                raw = response["text"]
                if response.get("response_text_sha256") != sha256(raw.encode()).hexdigest():
                    raise SelectiveLoopWindowsError("response text hash mismatch")
                if terminal_response_saturated(response.get("usage"), max_tokens) != saturated:
                    raise SelectiveLoopWindowsError("terminal saturation differs from usage")
                contacted.append(request_id)
            actual, fields = hook.accept(
                iteration=iteration,
                record=SimpleNamespace(
                    start_seconds=cut_start, end_seconds=cut_end,
                ),
                transcript=normalize_terminal_response(raw, saturated=saturated, skipped=skipped),
                saturated=saturated, skipped=skipped,
            )
            for name, value in fields.items():
                if obs.get(name) != value:
                    raise SelectiveLoopWindowsError(f"OBS {name} differs from shared repair hook")
            if actual != obs.get("obs_delivered_text"):
                raise SelectiveLoopWindowsError("OBS backfill delivery differs from shared repair hook")
            spans[index - 1] = replace(
                spans[index - 1], text=fields["obs_relisten_window_text"],
                request_id=request_id, saturated=saturated,
            )
        stitch = bundle.trace_records.get(f"{root}/request", {})
        if stitch.get("stitch") is not True or stitch.get("stitched_request_ids") != contacted:
            raise SelectiveLoopWindowsError("terminal contacts differ from sealed stitch order")
        result[sample] = tuple(spans)
    all_terminal = {
        key for key, value in bundle.trace_records.items()
        if key.endswith("/obs") and "obs_iteration" in value
    }
    if consumed != all_terminal:
        raise SelectiveLoopWindowsError("trace contains unconsumed terminal OBS records")
    try:
        assert_stitch_reproduces_outputs(result, output_text)
    except WindowPairingError as error:
        raise SelectiveLoopWindowsError("recovered windows do not rebuild outputs") from error
    return result
