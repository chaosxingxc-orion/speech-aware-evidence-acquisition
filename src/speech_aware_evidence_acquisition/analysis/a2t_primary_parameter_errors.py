"""Pure primary-call parameter error projection for Audio2Tool.

The projection uses the released official parameter normalization but does
not invoke an official or repository scorer.  It returns normalized key names
and counts only; parameter values never enter its result.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..reproduction.audio2tool_official.metrics import normalize_parameters
from ..reproduction.toolcall_scoring_v2 import _coerced_canonical_value


class PrimaryParameterError(ValueError):
    """A supplied parameter collection is not a valid mapping."""


def _validated_copy(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise PrimaryParameterError(f"{label} must be a parameter mapping")
    copied: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise PrimaryParameterError(
                f"{label} parameter keys must be nonempty strings"
            )
        copied[key] = item
    return copied


def _normalized(
    value: object, label: str
) -> tuple[dict[str, str], int]:
    copied = _validated_copy(value, label)
    normalized = normalize_parameters(copied)
    collision_count = len(copied) - len(normalized)
    return normalized, collision_count


def diagnose_primary_parameters(
    predicted: Mapping[str, object],
    reference: Mapping[str, object],
    defaults: Mapping[str, object],
) -> dict[str, object]:
    """Describe official-normalized primary-call parameter relations.

    Normalized-key collisions use the official normalizer's last-value-wins
    result and are counted separately as the number of collapsed input keys.
    Repository coercion is reported only for keys that remain unequal under
    official normalization and does not change ``param_exact``.
    """

    predicted_norm, predicted_collisions = _normalized(predicted, "predicted")
    reference_norm, reference_collisions = _normalized(reference, "reference")
    defaults_norm, default_collisions = _normalized(defaults, "defaults")

    predicted_keys = set(predicted_norm)
    reference_keys = set(reference_norm)
    shared_keys = predicted_keys & reference_keys

    correct_keys = sorted(
        key
        for key in shared_keys
        if predicted_norm[key] == reference_norm[key]
    )
    wrong_value_keys = sorted(shared_keys - set(correct_keys))
    missing_keys = sorted(reference_keys - predicted_keys)
    extra_keys = sorted(predicted_keys - reference_keys)
    extra_default_keys = sorted(
        key
        for key in extra_keys
        if key in defaults_norm and predicted_norm[key] == defaults_norm[key]
    )
    wrong_coercion_equal = sorted(
        key
        for key in wrong_value_keys
        if _coerced_canonical_value(predicted_norm[key])
        == _coerced_canonical_value(reference_norm[key])
    )

    return {
        "correct_keys": correct_keys,
        "missing_keys": missing_keys,
        "extra_keys": extra_keys,
        "wrong_value_keys": wrong_value_keys,
        "correct_normalized_key_count": len(correct_keys),
        "predicted_normalized_key_count": len(predicted_norm),
        "reference_normalized_key_count": len(reference_norm),
        "param_exact": not missing_keys and not extra_keys and not wrong_value_keys,
        "extra_keys_matching_declared_defaults": extra_default_keys,
        "wrong_keys_equal_under_repo_coercion": wrong_coercion_equal,
        "predicted_normalized_key_collision_count": predicted_collisions,
        "reference_normalized_key_collision_count": reference_collisions,
        "default_normalized_key_collision_count": default_collisions,
    }
