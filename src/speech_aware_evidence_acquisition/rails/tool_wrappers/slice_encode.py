"""``saea-tool-slice-encode-v1`` -- the ONE slice encoder, as a tool.

Wraps ``reproduction.obs_audio.encode_slice`` unchanged: the single place the
transform ORDER is decided (raw cut -> ``rms-norm`` -> tail silence) and the
one function both obs executors already call, so the tool cannot diverge from
what the sequential and the openJiuwen paths put on the wire.

This is the catalog's ONLY byte-changing tool, so it is the only one that
carries a :class:`~..tools.DerivationRecord`. The record is emitted on every
call, not only when a transform was declared: ``transforms`` is then empty and
``pre_sha256`` is ``None``, which is the record honestly saying the bytes are
the raw cut. Its three fields are the three
``core.model.SliceRegistry.register`` already requires, so a record produced
here drops into the payload-binding rail without translation.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

from ...reproduction.obs_audio import encode_slice

TOOL_ID = "saea-tool-slice-encode-v1"

#: The derivation-record schema this tool emits (manifest ``derivation_record``).
DERIVATION_RECORD = "saea-slice-derivation-v1"


def encode_slice_tool(
    slice_samples: Sequence[int],
    sample_rate_hz: int,
    *,
    preprocess: Sequence[str] = (),
    rms_target_dbfs: float = -20.0,
    tail_silence_seconds: float = 0.0,
):
    """``encode_slice(...)`` verbatim, plus its derivation record.

    ``ToolResult.result`` is the wrapped function's own
    ``(wav_bytes, transforms, pre_sha256)`` tuple, byte for byte -- nothing is
    re-encoded, re-hashed into it or re-ordered.
    """

    from ..tools import DerivationRecord, ToolResult

    result = encode_slice(
        slice_samples,
        sample_rate_hz,
        preprocess=preprocess,
        rms_target_dbfs=rms_target_dbfs,
        tail_silence_seconds=tail_silence_seconds,
    )
    wav_bytes, transforms, pre_sha256 = result
    return ToolResult(
        tool_id=TOOL_ID,
        result=result,
        derivation=DerivationRecord(
            tool_id=TOOL_ID,
            transforms=tuple(transforms),
            pre_sha256=pre_sha256,
            post_sha256=hashlib.sha256(wav_bytes).hexdigest(),
        ),
    )
