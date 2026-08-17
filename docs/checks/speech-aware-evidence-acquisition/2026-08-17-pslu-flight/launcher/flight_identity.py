"""Shared run identity for the P-SLU flight launcher and its pre-flight check.

Why the launcher builds its own ``values`` mapping instead of calling
``core.config.compose``: ``compose`` needs four COMMITTED fragments
(model/dataset/baseline/experiment) and this repository ships no SLURP
dataset/baseline/experiment fragment -- creating three new config files just
to name a probe that already has its own committed binding
(``configs/probes/g0-binding/pslu-flight.json``) would dirty the tree for the
whole flight and duplicate the binding that config already is. The P-SLU
flight config's own execution_plan note sanctions exactly this: "protocol_hash
and run_id/attempt_id are assigned by the flying agent's own launcher at
flight time, never frozen here."

The identity is still fully reproducible: ``values`` is the COMMITTED model
fragment ``configs/model/q4km-featcache.json`` read verbatim, with exactly
three documented deltas, plus a probe-identity block read verbatim from the
committed flight config. ``config_hash_of`` is byte-for-byte
``core.config._canonical_hash``'s formula, and ``protocol_hash`` is computed by
``core.config.protocol_hash`` itself.

The three deltas from the committed model fragment, each with its reason:

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory, resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()`` (env ``SAEA_FEAT_CACHE_DIR``).
   The fragment hand-types the LEGACY ``/home/chao/feat-cache/q4km`` (26 GB,
   warm for earnings21/22); ``docs/featcache-directories.md`` requires a NEW
   dataset campaign to use ``/home/chao/feat-cache/<dataset>-<encoder>/`` and
   forbids mixing a new campaign's writes into the legacy directory.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED. That value is a
   sentinel the BATCH EXECUTOR resolves to an allocated integer slot; the rails
   ``FrozenCoreClient`` path has no batch executor, and
   ``core.model.adapter.request`` refuses an unresolved sentinel so it can
   never reach the server as a string (``core.model.request_types``'s own
   comment on ALLOWED_DECODING_KEYS).
3. A probe-identity block is merged in so this run's config hash actually
   names the probe, its arms, its frozen sample manifest and its roster table
   -- keys disjoint from the model fragment's own, exactly the disjointness
   ``compose`` enforces across fragments.

``server_args`` are the committed fragment's OWN argv, unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-pslu-n60"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
FLIGHT_CONFIG_RELPATH = "configs/probes/g0-binding/pslu-flight.json"

D2_ARM = "fixed-legal-context"


def resolve_feat_cache_dir() -> str:
    """The campaign feature-cache directory, via the sanctioned named
    parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory silently: an unset env var is a hard error here, because this
    launcher's whole point is that a NEW dataset campaign must not write into
    the warm earnings21/22 cache."""

    from speech_aware_evidence_acquisition.core.session import (
        FEAT_CACHE_DIR_DEFAULT,
        feat_cache_dir,
    )

    resolved = feat_cache_dir()
    if resolved == FEAT_CACHE_DIR_DEFAULT:
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is unset (or set to the legacy q4km directory); "
            "this SLURP campaign must never write into the warm earnings21/22 cache "
            f"({FEAT_CACHE_DIR_DEFAULT}) -- see docs/featcache-directories.md"
        )
    return resolved


def build_values(repo: Path) -> dict[str, object]:
    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    flight = json.loads((repo / FLIGHT_CONFIG_RELPATH).read_text(encoding="utf-8"))

    values = dict(fragment)

    # Delta 1: campaign-own feature cache.
    server_env = dict(values.get("server_env", {}))
    server_env["LLAMA_MTMD_FEAT_CACHE_DIR"] = resolve_feat_cache_dir()
    values["server_env"] = server_env

    # Delta 2: drop the batch-executor-only id_slot sentinel.
    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    # Delta 3: probe identity, read verbatim from the committed flight config.
    values.update(
        {
            "arm": D2_ARM,
            "probe": flight["probe"],
            "flight_config_version": flight["flight_config_version"],
            "flight_config": FLIGHT_CONFIG_RELPATH,
            "preregistration": flight["preregistration"],
            "carrier_lock_key": flight["carrier_lock_key"],
            "split_name": "devel",
            "sample_manifest": flight["sample_manifest"],
            "roster_table": flight["roster_table"],
            "arms": list(flight["arms"]),
            "launcher": "scratchpad pslufly/launch_pslu_flight.py (archived with the flight receipt)",
        }
    )
    return values


def config_hash_of(values: Mapping[str, object]) -> str:
    """Byte-identical to ``core.config._canonical_hash``."""

    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def decoding_params(values: Mapping[str, object]) -> dict[str, object]:
    return dict(values.get("decoding_params", {}))


def server_args(values: Mapping[str, object]) -> list[str]:
    raw = values.get("server_args", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("server_args must be a list")
    return [str(token) for token in raw]


def server_env(values: Mapping[str, object]) -> dict[str, str]:
    raw = values.get("server_env", {})
    if not isinstance(raw, Mapping):
        raise ValueError("server_env must be a mapping")
    return {str(k): str(v) for k, v in raw.items()}
