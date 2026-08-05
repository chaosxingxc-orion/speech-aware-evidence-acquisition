"""Deterministic four-fragment config composition (model/dataset/baseline/experiment).

JSON, stdlib-only, no override semantics: top-level keys must be disjoint
across fragments so a later fragment can never silently rewrite an earlier
one. The composed hash and the protocol hash are the identity cells every
formal ledger row carries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..scoring import SCORING_STACK_VERSION

_KINDS = ("model", "dataset", "baseline", "experiment")


class ConfigError(RuntimeError):
    """A config fragment is missing, unreadable, or collides with another."""


@dataclass(frozen=True)
class ComposedConfig:
    values: Mapping[str, object]
    config_hash: str
    fragments: Mapping[str, str]


def _canonical_hash(document: Mapping[str, object]) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compose(
    repo_root: Path, model: str, dataset: str, baseline: str, experiment: str
) -> ComposedConfig:
    names = dict(zip(_KINDS, (model, dataset, baseline, experiment)))
    merged: dict[str, object] = {}
    origins: dict[str, str] = {}
    for kind in _KINDS:
        path = Path(repo_root) / "configs" / kind / f"{names[kind]}.json"
        if not path.is_file():
            raise ConfigError(f"missing config fragment: {path}")
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ConfigError(f"cannot read config fragment {path}: {error}") from error
        if not isinstance(fragment, dict):
            raise ConfigError(f"config fragment {path} must be a JSON object")
        for key, value in fragment.items():
            if key in merged:
                raise ConfigError(
                    f"config key collision: {key!r} defined by {origins[key]} and {kind}"
                )
            merged[key] = value
            origins[key] = kind
    return ComposedConfig(values=merged, config_hash=_canonical_hash(merged), fragments=names)


def protocol_hash(config_hash: str, arm: str, split_identity_hash: str) -> str:
    return _canonical_hash(
        {
            "arm": arm,
            "config": config_hash,
            "scoring": SCORING_STACK_VERSION,
            "split": split_identity_hash,
        }
    )
