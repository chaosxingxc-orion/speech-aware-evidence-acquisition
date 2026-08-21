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

# A model fragment may pin a SECOND runtime receipt (e.g.
# "receipts/runtime-q4km.json" for a Q4_K_M pinned model alongside the
# default Q8_0) via an optional top-level "runtime_receipt" key, relative to
# the study repo's docs/ directory. Every fragment that predates this key
# (and every fragment that simply never sets it) resolves to exactly this
# same default -- unchanged behaviour, unchanged config_hash for any
# fragment that omits the key entirely (the default is applied here, at
# CONSUMPTION time, never injected into `compose()`'s merged dict, so an
# existing fragment's canonical hash never shifts under it). A fragment that
# DOES set the key changes `config_hash` -> `protocol_hash` automatically,
# the same way any other model-config key already does: `compose()` merges
# every fragment's top-level keys verbatim before hashing.
DEFAULT_RUNTIME_RECEIPT_RELPATH = "receipts/runtime.json"
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


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


def runtime_receipt_relpath(values: Mapping[str, object]) -> str:
    """Resolve a composed config's ``runtime_receipt`` model key (relative to
    the study repo's ``docs/`` directory), defaulting to today's committed
    ``receipts/runtime.json`` when the key is absent -- so every fragment
    that predates the key, or simply never sets it, behaves identically to
    before. Fails closed (``ConfigError``) on a malformed value: this string
    is about to be joined onto a filesystem path (``resolve_runtime_receipt_
    path``), so the same absolute/drive-letter/backslash/traversal refusals
    the rest of this study applies to any path-shaped config value apply
    here too, before it ever reaches a caller."""

    value = values.get("runtime_receipt", DEFAULT_RUNTIME_RECEIPT_RELPATH)
    if not isinstance(value, str) or not value:
        raise ConfigError(
            f"model config runtime_receipt must be a non-empty string, got {value!r}"
        )
    if "\\" in value:
        raise ConfigError(f"model config runtime_receipt must not contain a backslash: {value!r}")
    if value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise ConfigError(f"model config runtime_receipt must be relative, got {value!r}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise ConfigError(
            f"model config runtime_receipt contains an empty or traversal segment: {value!r}"
        )
    return value


def model_lock_key(values: Mapping[str, object]) -> str:
    """Resolve a composed config's ``model_lock_key`` -- the pinned model
    THIS RUN declares. Read directly, no default: every model fragment names
    its own frozen umbrella-lock entry explicitly (unlike ``runtime_receipt``,
    which is genuinely optional), so an omitted or malformed value fails
    closed rather than silently falling back to any one model. This is the
    SAME declaration ``runtime_receipt_relpath`` already uses to pick the
    receipt FILE -- callers bind both to the identical ``values`` mapping so
    a run can never pair one model's config with a different model's
    receipt (``contracts.FrozenCoreGate``'s ``expected_model_lock_key``)."""

    value = values.get("model_lock_key")
    if not isinstance(value, str) or not value:
        raise ConfigError(f"model config model_lock_key must be a non-empty string, got {value!r}")
    return value


def model_materialization_root(values: Mapping[str, object]) -> str | None:
    """Return the explicit root holding lock-relative model bytes.

    The canonical dataset root remains the default when the model fragment
    omits this key.  A configured value is a POSIX absolute path because all
    formal inference runs execute inside WSL2; relative paths, traversal,
    repeated separators, backslashes and non-string values are refused before
    they can select a different host file by accident.
    """

    value = values.get("model_materialization_root")
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            "model config model_materialization_root must be a non-empty POSIX "
            f"absolute path, got {value!r}"
        )
    if not value.startswith("/") or "\\" in value:
        raise ConfigError(
            "model config model_materialization_root must be a POSIX absolute "
            f"path, got {value!r}"
        )
    if any(part in ("", ".", "..") for part in value[1:].split("/")):
        raise ConfigError(
            "model config model_materialization_root contains an empty or "
            f"traversal segment: {value!r}"
        )
    return value


def resolve_runtime_receipt_path(repo_root: Path, values: Mapping[str, object]) -> Path:
    """The absolute path a composed config's ``runtime_receipt`` key names,
    under ``<repo_root>/docs/`` -- the one place every caller (driver smoke,
    ``saea-driver run``, and ``contracts.FrozenCoreGate.for_study_repo``'s
    own default) should derive this path from, rather than each
    re-implementing the same join."""

    return Path(repo_root) / "docs" / runtime_receipt_relpath(values)


def protocol_hash(config_hash: str, arm: str, split_identity_hash: str) -> str:
    return _canonical_hash(
        {
            "arm": arm,
            "config": config_hash,
            "scoring": SCORING_STACK_VERSION,
            "split": split_identity_hash,
        }
    )
