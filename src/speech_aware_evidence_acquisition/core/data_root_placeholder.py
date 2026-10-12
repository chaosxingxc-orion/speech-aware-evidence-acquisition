"""The data-root placeholder (owner rulings 289 B / 290 B, 2026-10-12): stdlib-only, importable from any light module.

A repository config, plan or protocol document never names where the data root lives. A string such as
``"${SAEA_DATA_ROOT}/runs/X/y.json"`` names a file below it, and the loader that reads the document expands the
placeholder with :func:`expand_data_root`. Hashes of composed configs and of pinned document bytes are taken over the
UNEXPANDED text, so a cell's identity does not move when the data root moves.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


#: The one data-root placeholder a config fragment may carry (owner rulings 289 B / 290 B, 2026-10-12): a string
#: such as ``"${SAEA_DATA_ROOT}/runs/X/y.json"`` names a file below the data root without naming the root. The
#: composed hash and every fragment hash are taken over the UNEXPANDED text, so a cell's identity does not move when
#: the data root moves; :func:`compose` hands consumers the expanded ``values``.
DATA_ROOT_PLACEHOLDER = "${SAEA_DATA_ROOT}"
_DATA_ROOT_ENVS = ("SAEA_DATA_ROOT", "SPEECHRL_DATA_DIR")


def resolve_data_root_text(data_root: "str | Path | None" = None) -> str | None:
    """The data root used to expand :data:`DATA_ROOT_PLACEHOLDER`: the explicit argument, else
    ``SAEA_DATA_ROOT``, else ``SPEECHRL_DATA_DIR``; ``None`` when none is set (placeholders then stay verbatim, so
    offline hashing works and any real file use fails closed on a path that cannot exist)."""

    if data_root is not None and str(data_root).strip():
        return str(data_root).rstrip("/") or "/"
    for name in _DATA_ROOT_ENVS:
        raw = os.environ.get(name, "").strip()
        if raw:
            return raw.rstrip("/") or "/"
    return None


def expand_data_root(value: object, data_root: "str | Path | None" = None) -> object:
    """``value`` with every :data:`DATA_ROOT_PLACEHOLDER` in every string (recursively through lists and mappings,
    keys untouched) replaced by the resolved data root; unchanged when no root is resolvable."""

    root = resolve_data_root_text(data_root)
    if root is None:
        return value

    def walk(item: object) -> object:
        if isinstance(item, str):
            return item.replace(DATA_ROOT_PLACEHOLDER, root) if DATA_ROOT_PLACEHOLDER in item else item
        if isinstance(item, list):
            return [walk(v) for v in item]
        if isinstance(item, dict):
            return {k: walk(v) for k, v in item.items()}
        return item

    return walk(value)


def collapse_data_root(value: object, data_root: "str | Path | None" = None) -> object:
    """The inverse of :func:`expand_data_root`: every occurrence of the resolved data root at the start of a path
    component inside a string becomes :data:`DATA_ROOT_PLACEHOLDER` again. Hash recomputation over expanded values
    (``config._canonical_hash``) goes through it, so a composed config hashes the same whatever root it was expanded
    with. A no-op when no root is resolvable or the root is ``/``."""

    root = resolve_data_root_text(data_root)
    if root is None or root == "/":
        return value
    pattern = re.compile(re.escape(root) + r"(?=/|$|[^A-Za-z0-9._-])")

    def walk(item: object) -> object:
        if isinstance(item, str):
            return pattern.sub(DATA_ROOT_PLACEHOLDER, item) if root in item else item
        if isinstance(item, list):
            return [walk(v) for v in item]
        if isinstance(item, dict):
            return {k: walk(v) for k, v in item.items()}
        return item

    return walk(value)
