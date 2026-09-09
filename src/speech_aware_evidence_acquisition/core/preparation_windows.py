"""Actual independent speech windows for model-free request preparation.

Use the live cutter, lineage registry, and per-window instruction factory.
No adapter request, response, acceptance, scoring, or model trace is produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .preparation import PreparationError


@dataclass(frozen=True)
class WindowRequestBatch:
    payloads: tuple[Mapping[str, object], ...]
    request_keys: tuple[str, ...]
    source_bindings: tuple[Mapping[str, object], ...]

    def request_key(self, payload):
        identity = (payload["sample_id"], payload["media_relpath"])
        for key, source in zip(self.request_keys, self.source_bindings, strict=True):
            if identity == (source["sample_id"], source["media_relpath"]):
                return key
        raise PreparationError("request does not belong to this window batch")


def materialize_window_requests(
    contexts: Sequence[object], *, expected_sample_ids: Sequence[str], hook_factory=None
) -> WindowRequestBatch:
    """Prepare the entire verified call roster without opening a model client."""
    from ..reproduction import obs_loop
    from ..reproduction.repair_loop import build_repair_window_hook
    from .model.paths import _normalized_relative_path, _resolve_confined

    ids = [ctx.sample.sample_id for ctx in contexts]
    if (
        not ids
        or len(ids) != len(set(ids))
        or len(expected_sample_ids) != len(set(expected_sample_ids))
        or set(ids) != set(expected_sample_ids)
    ):
        raise PreparationError("window fit requires the complete unique call roster")
    payloads, keys, sources = [], [], []
    for ctx in contexts:
        values = ctx.extras["config_values"]
        cfg = obs_loop.ObsLoopConfig.from_values(values, Path(ctx.extras["repo_root"]))
        if (
            cfg.boundary_mode != "fixed"
            or cfg.condition_tail_chars != 0
            or cfg.vad_trim_min_seconds != 0
            or cfg.batch_slices <= 1
        ):
            raise PreparationError(
                "window fit requires independent fixed parallel windows"
            )
        root = Path(ctx.extras["data_root"])
        sample = ctx.sample
        relative = _normalized_relative_path(sample.media_relpath, "window parent")
        parent = _resolve_confined(root, relative, root, "window parent", strict=True)
        rate = obs_loop.SLICE_SAMPLE_RATE_HZ
        pcm = obs_loop.decode_parent_pcm(parent, rate)
        if not len(pcm):
            raise PreparationError("window parent decoded to zero samples")
        hook = (hook_factory or build_repair_window_hook)(ctx, cfg, root, sample)
        registry = ctx.extras["slice_registry"]
        windows, records = obs_loop.materialize_fixed_windows(
            cfg,
            registry,
            root,
            sample,
            rate,
            pcm,
            len(pcm) / rate,
            obs_loop._sha256_file(parent),
        )
        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        allow_empty = (
            evidence is not None
            and not evidence
            and values.get("evidence_source") == "derived-candidates"
        )
        for window, record in zip(windows, records, strict=True):
            request_id, factory = obs_loop.window_request_factory(
                ctx,
                window,
                sample=sample,
                rate=rate,
                evidence=evidence,
                allow_empty_evidence=allow_empty,
                window_hook=hook,
                slot=0 if ctx.decoding_params.get("id_slot") == "per-sample" else None,
            )
            payloads.append(factory(request_id))
            keys.append(f"{sample.sample_id}#w{record.iteration + 1:04d}")
            sources.append(record.trace_view())
    if not payloads:
        raise PreparationError("window fit materialized no requests")
    return WindowRequestBatch(tuple(payloads), tuple(keys), tuple(sources))
