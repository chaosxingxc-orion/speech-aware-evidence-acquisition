"""Reuse the TRAIN-only SLURP task contract with verified source identities."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Mapping

from . import slurp as slurp_source
from .lock import lock_entry
from .slurp import (
    SLURP_LOCK_KEY,
    _SPLIT_FILES,
    _governed_roots,
    load_slurp_ontology,
    render_slurp_ontology,
)

_CACHE_SCHEMA = "slurp-contract-cache-v1"
_IMPLEMENTATION_SHA256 = hashlib.sha256(
    Path(slurp_source.__file__).read_bytes()
).hexdigest()
_MAX_ENTRIES = 8
_CACHE_LOCK = RLock()
_CACHE: OrderedDict[tuple[object, ...], str] = OrderedDict()


class SlurpContractCacheError(RuntimeError):
    """The source changed while its task contract was being constructed."""


def clear_slurp_contract_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def _file_digest(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError as error:
        raise SlurpContractCacheError(
            f"cannot fingerprint SLURP contract source {path}: {error}"
        ) from error


def _cache_key(lock: Mapping[str, object], root: Path) -> tuple[object, ...]:
    _, _, metadata_dir = _governed_roots(lock, root)
    source = metadata_dir / _SPLIT_FILES["train"]
    entry = json.dumps(
        lock_entry(lock, SLURP_LOCK_KEY), sort_keys=True, separators=(",", ":")
    )
    return (
        _CACHE_SCHEMA,
        _IMPLEMENTATION_SHA256,
        entry,
        str(root),
        str(source.resolve()),
        _file_digest(source),
        # Bind the historical default explicitly; runtime never widens to synthetic.
        ("include_synthetic", False),
    )


def load_cached_slurp_contract(lock: Mapping[str, object], root: Path) -> str:
    """Hash source bytes on every lookup; parse and render identical bytes once.

    Keep only immutable strings in a bounded process-local cache. Recheck the
    fingerprint after a cold load so changed sources cannot publish a stale
    entry. Neither the query sample nor its annotations enter this function.
    """
    resolved_root = Path(root).resolve()
    with _CACHE_LOCK:
        key = _cache_key(lock, resolved_root)
        if key in _CACHE:
            rendered = _CACHE.pop(key)
            _CACHE[key] = rendered
            return rendered
        ontology = load_slurp_ontology(lock, resolved_root, include_synthetic=False)
        rendered = render_slurp_ontology(ontology)
        if _cache_key(lock, resolved_root) != key:
            raise SlurpContractCacheError(
                "SLURP ontology source changed while loading; refusing to publish contract"
            )
        _CACHE[key] = rendered
        while len(_CACHE) > _MAX_ENTRIES:
            _CACHE.popitem(last=False)
        return rendered
