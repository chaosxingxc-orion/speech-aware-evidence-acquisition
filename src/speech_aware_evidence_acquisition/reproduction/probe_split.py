"""Probe-sample receipts as verified splits (P1 scaffold).

The three contract splits (discovery/dev/confirmatory) live in
``docs/receipts/splits.json`` and verify through ``core.split_receipt``'s
strict-parse + live-recompute path. The sampled reproduction probes (P0.D,
sample-once policy) freeze their item identity in per-probe receipts under
``docs/receipts/probe-samples/`` instead; this module turns one such receipt
into the same :class:`core.split_receipt.VerifiedSplit` shape the driver's
split<->plan<->config cross-checks consume.

TWO hashes, deliberately:

1. **Receipt-integrity hash** — the receipt's own ``split_identity_hash``,
   computed by ``scripts/build_probe_samples.py`` over the raw item keys
   (``"audio2tool:tier1_direct:000045"`` — colon convention). Recomputed
   here fail-closed via ``reproduction.sampling.split_identity_hash``: a
   receipt whose items were edited without its hash (or vice versa) refuses.
   This is the value the probe manifest (``configs/probes/manifest.json``)
   binds.
2. **Run-identity hash** — the ``VerifiedSplit.identity_hash`` this module
   RETURNS, derived under the E0 ledger convention (``data.splits``:
   SHA-256 over LF-joined sorted ``f"{lock_key}/{sample_id}"``). This is the
   value an ``ExecutionPlan``/run manifest carries, because
   ``core.bundle.verify_bundle`` independently recomputes exactly that
   convention from the manifest's carrier + bare sample ids. The derivation
   is deterministic from the same frozen identity set — the two hashes name
   the same items in two serializations, and either one pins the other.

Trust split (documented, not accidental): this module verifies IDENTITY
only; on-disk existence of every item is enforced by the carrier loader
inside ``core.driver.run_experiment`` (its "split ids missing from the
carrier's loaded samples" check plus the loader's own fail-closed media
resolution). The receipt itself is committed, and the plan's
``split_identity_hash`` cross-check in ``core.driver.split_check`` binds any
run to what this module verified.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

from ..core.split_receipt import SplitReceiptError, VerifiedSplit
from ..data.splits import prefixed, split_identity_hash as _slash_hash
from .sampling import split_identity_hash as _key_hash

PROBE_SAMPLES_DIRNAME = "probe-samples"

_SPLIT_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_STAGE2_SPLIT_ROLES = frozenset({"discovery", "dev"})


def probe_split_receipt_path(repo_root: Path, split_name: str) -> Path:
    if not isinstance(split_name, str) or not _SPLIT_NAME_PATTERN.fullmatch(split_name):
        raise SplitReceiptError(
            f"probe split name {split_name!r} is not a plain receipt name "
            "(no path separators, no leading dot/dash)"
        )
    return (
        Path(repo_root) / "docs" / "receipts" / PROBE_SAMPLES_DIRNAME / f"{split_name}.json"
    )


def _fail(split_name: str, reason: str) -> SplitReceiptError:
    return SplitReceiptError(f"probe sample receipt {split_name!r} {reason}")


def load_verified_probe_split(repo_root: Path, split_name: str) -> VerifiedSplit:
    """Strictly parse + hash-verify one probe-sample receipt into a
    :class:`VerifiedSplit` (module docstring: what is and is not verified)."""

    path = probe_split_receipt_path(repo_root, split_name)
    if not path.is_file():
        raise SplitReceiptError(
            f"probe sample receipt missing for split {split_name!r}: {path} "
            "(frozen contract splits are 'discovery'/'dev'/'confirmatory'; every other "
            "split name must be a committed probe-sample receipt)"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise _fail(split_name, f"cannot be read: {error}") from error
    if not isinstance(payload, Mapping):
        raise _fail(split_name, "must be a JSON object")

    carrier = payload.get("carrier")
    if not isinstance(carrier, str) or not carrier.strip():
        raise _fail(split_name, "carrier must be a non-empty string")

    split_role = payload.get("split_role")
    if split_role not in _STAGE2_SPLIT_ROLES:
        raise _fail(
            split_name,
            f"split_role {split_role!r} is not a Stage-2 role "
            f"{sorted(_STAGE2_SPLIT_ROLES)} (fail-closed; confirmatory probe "
            "receipts can never exist)",
        )

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise _fail(split_name, "items must be a non-empty list")
    key_prefix = f"{carrier}:"
    keys: list[str] = []
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("key"), str):
            raise _fail(split_name, f"has a malformed item: {item!r}")
        key = item["key"]
        if not key.startswith(key_prefix) or key == key_prefix:
            raise _fail(
                split_name,
                f"item key {key!r} is not prefixed {key_prefix!r} (every probe item "
                "key must be carrier-prefixed)",
            )
        keys.append(key)
    try:
        recomputed = _key_hash(keys)
    except ValueError as error:
        raise _fail(split_name, f"has duplicate item keys: {error}") from error
    stored = payload.get("split_identity_hash")
    if recomputed != stored:
        raise _fail(
            split_name,
            f"split_identity_hash {stored!r} does not match the hash recomputed from "
            f"its own item keys ({recomputed!r}); refusing a tampered receipt",
        )

    bare_ids = tuple(sorted(key[len(key_prefix):] for key in keys))
    prefixed_ids = tuple(prefixed(carrier, bare_ids))
    return VerifiedSplit(
        name=split_name,
        carrier_lock_key=carrier,
        split_role=str(split_role),
        ids=bare_ids,
        prefixed_ids=prefixed_ids,
        identity_hash=_slash_hash(prefixed_ids),
    )
