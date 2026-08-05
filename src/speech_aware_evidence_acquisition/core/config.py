"""Deterministic four-fragment config composition (model/dataset/baseline/experiment).

JSON, stdlib-only, no override semantics: top-level keys must be disjoint
across fragments so a later fragment can never silently rewrite an earlier
one. The composed hash and the protocol hash are the identity cells every
formal ledger row carries.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..scoring import SCORING_STACK_VERSION

_KINDS = ("model", "dataset", "baseline", "experiment")
_FRAGMENT_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class ConfigError(RuntimeError):
    """A config fragment is missing, unreadable, or collides with another."""


def _reject_duplicate_keys(fragment_path: Path):
    """``object_pairs_hook`` factory (M-5 fix): a human reading a JSON
    fragment top-to-bottom sees the FIRST value for a repeated key, but
    ``json.loads``'s default dict-building silently keeps the LAST -- the
    two readers of the same fragment (a person, and this composer) would
    disagree about what the fragment means. Raising here, at parse time,
    turns that silent last-write-wins behavior into a fail-closed
    :class:`ConfigError` naming both the offending key and the fragment
    file, before the duplicate can ever reach ``compose``'s own (unrelated)
    cross-fragment collision check below."""

    def hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        seen: dict[str, object] = {}
        for key, value in pairs:
            if key in seen:
                raise ConfigError(
                    f"config fragment {fragment_path} has a duplicate key {key!r}; "
                    "a human reading it top-to-bottom sees the FIRST value but JSON "
                    "parsing would otherwise silently keep the LAST -- refused"
                )
            seen[key] = value
        return seen

    return hook


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
        name = names[kind]
        if not isinstance(name, str) or not _FRAGMENT_NAME_PATTERN.fullmatch(name):
            raise ConfigError(f"invalid config fragment name for {kind}: {name!r}")
        path = Path(repo_root) / "configs" / kind / f"{name}.json"
        if not path.is_file():
            raise ConfigError(f"missing config fragment: {path}")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ConfigError(f"cannot read config fragment {path}: {error}") from error
        try:
            # M-5 fix: object_pairs_hook rejects a duplicate top-level key
            # before json.loads ever builds the (last-value-wins) dict --
            # ConfigError raised inside the hook propagates straight out of
            # json.loads uncaught below, since it is not a json.JSONDecodeError.
            fragment = json.loads(text, object_pairs_hook=_reject_duplicate_keys(path))
        except json.JSONDecodeError as error:
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
