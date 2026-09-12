"""Verify media-only Audio2Tool roster metadata for shared runtime consumers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ..core.base import CoreError
from .splits import prefixed, split_identity_hash


RUNTIME_ROSTER_MEDIA_FIELDS = {"sample_id", "media_relpath", "audio_sha256", "audio_seconds"}


RUNTIME_ROSTER_ALLOWED_FIELDS = RUNTIME_ROSTER_MEDIA_FIELDS | {
    "id",
    "key",
    "query_idx",
    "tier",
    "stratum",
    "sample_rate_hz",
    "bytes",
    "n_samples",
    "duration_delta_seconds",
    "samples_added",
    "samples_removed",
    "samples_added_by_tail",
    "parent_media_relpath",
    "source_sample_id",
    "source_key",
    "source_media_relpath",
    "source_audio_sha256",
    "source_audio_seconds",
    "source_sample_rate_hz",
    "source_n_samples",
    "source_active_share",
    "source_clipped_samples",
    "source_peak_abs",
    "source_peak_dbfs",
    "source_leading_silence_seconds",
    "source_trailing_silence_seconds",
    "source_energy_above_4k_share",
    "source_energy_above_6k_share",
    "source_energy_above_7k_share",
    "source_energy_above_8k_share",
    "standardized_audio_seconds",
    "standardized_clipped_samples",
    "standardized_n_samples",
    "standardized_peak_abs",
}


RUNTIME_ROSTER_BINDING_FIELDS = (
    "carrier_lock_key",
    "split_id",
    "a2t_calibration_subset_receipt",
    "a2t_calibration_subset_receipt_sha256",
    "a2t_calibration_split_name",
    "a2t_calibration_split_role",
    "a2t_calibration_split_identity_hash",
    "a2t_calibration_flight_split_identity_hash",
    "a2t_calibration_count",
)


def load_runtime_roster(path: Path, expected_sha256: str) -> Mapping[str, object]:
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CoreError("Audio2Tool roster receipt hash differs from configuration")
    try:
        doc = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise CoreError("Audio2Tool roster is not valid JSON") from error
    if not isinstance(doc, Mapping) or not isinstance(doc.get("items"), list):
        raise CoreError("Audio2Tool roster requires an items list")
    return doc


def validate_runtime_roster(receipt, values):
    if (
        receipt.get("schema") != "saea-a2t-agentloop-flight-roster-receipt-v1"
        or receipt.get("carrier") != "audio2tool"
    ):
        raise CoreError("Audio2Tool roster has the wrong schema or carrier")
    if receipt.get("split_role") != "discovery":
        raise CoreError("Audio2Tool configured flights require a discovery roster")
    if receipt.get("split_name") != values["split_id"]:
        raise CoreError("Audio2Tool receipt split differs from its configured split")
    items = receipt["items"]
    count = values["a2t_calibration_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise CoreError("Audio2Tool configured count must be a positive integer")
    if receipt.get("count") != count or len(items) != count:
        raise CoreError("Audio2Tool receipt count differs from its dataset")
    ids, keys = [], []
    seen = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise CoreError("Audio2Tool roster item must be media metadata")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise CoreError("Audio2Tool sample identity must be nonempty")
        if sample_id in seen:
            raise CoreError("Audio2Tool roster contains duplicate sample identities")
        key = item.get("key")
        if key != f"audio2tool:{sample_id}":
            raise CoreError("Audio2Tool roster key and sample identity differ")
        seen.add(sample_id)
        ids.append(sample_id)
        keys.append(key)
    expected = {
        "split_identity_hash": split_identity_hash(keys),
        "flight_split_identity_hash": split_identity_hash(prefixed("audio2tool", ids)),
    }
    for name, digest in expected.items():
        if receipt.get(name) != digest or values[f"a2t_calibration_{name}"] != digest:
            raise CoreError(f"Audio2Tool {name} identity differs from its roster")
    if values["a2t_calibration_split_name"] != values["split_id"]:
        raise CoreError("Audio2Tool dataset split names differ")
    if values["a2t_calibration_split_role"] != "discovery":
        raise CoreError("Audio2Tool dataset must retain discovery role")
