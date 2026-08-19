"""Shared run identity for the P-TRAP flight launcher, its binding step and
its pre-flight check.

Structurally the archived P-KEY flight's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-pkey2-flight/
launcher/flight_identity.py``), adapted only in run identity: RUN_ID names the
P-TRAP exposure row ``SAEA-PROBE-ptrap-120`` and the flight config is the
committed ``configs/probes/g0-binding/ptrap-flight.json``. The model fragment,
the three documented deltas and the hash formulas are byte-for-byte the P-KEY /
P-SLU-Stage-2 precedent's own -- "decode config identical to the consumed
P-SLU flights" is the registration's own requirement
(docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md section 1).

The three deltas from the committed model fragment, each with its reason
(unchanged from the P-KEY precedent):

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory (env ``SAEA_FEAT_CACHE_DIR`` = /home/chao/feat-cache/slurp-q4km,
   the SAME directory the consumed P-SLU/P-KEY flights warmed over these SAME
   60 samples), resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()``.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel; the rails ``FrozenCoreClient`` path has no batch executor.
3. A probe-identity block is merged in so this run's config hash actually names
   the probe, its two arms, its frozen sample manifest, its roster table and
   its trap-source provenance -- keys disjoint from the model fragment's own.

``server_args`` are the committed fragment's OWN argv, UNCHANGED (``-c 49152
-np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0``): V1/V2 render the SAME A3-form
100-entry roster the consumed P-SLU A3 arm flew inside a 12288-token slot,
plus at most 5 short appended ``type=value`` lines -- no A2T-style full-registry
prefill is involved, so the ``-np 1`` delta the Audio2Tool flights need does not
apply here and must NOT be introduced (it would change the decode config the
registration pins to the consumed P-SLU flights).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-ptrap-120"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
FLIGHT_CONFIG_RELPATH = "configs/probes/g0-binding/ptrap-flight.json"

D2_ARM = "fixed-legal-context"


def resolve_feat_cache_dir() -> str:
    """The campaign feature-cache directory, via the sanctioned named
    parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory silently: an unset env var is a hard error here, because this
    SLURP campaign must not write into the warm earnings21/22 cache."""

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
    if not resolved.rstrip("/").endswith("slurp-q4km"):
        raise RuntimeError(
            f"SAEA_FEAT_CACHE_DIR resolved to {resolved!r}; this flight writes only to "
            "/home/chao/feat-cache/slurp-q4km (never audio2tool-q4km, never q4km)"
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
            "status": flight["status"],
            "flight_config_version": flight["flight_config_version"],
            "flight_config": FLIGHT_CONFIG_RELPATH,
            "preregistration": flight["preregistration"],
            "carrier_lock_key": flight["carrier_lock_key"],
            "split_name": "devel",
            "sample_manifest": flight["sample_manifest"],
            "roster_table": flight["roster_table"],
            "arms": list(flight["arms"]),
            "trap_source_attempt": flight["trap_source"]["consumed_pslu_attempt_id"],
            "trap_source_arm": flight["trap_source"]["consumed_pslu_arm"],
            "trap_k_cap": flight["trap_source"]["trap_k_cap"],
            "trap_donor_seed": flight["trap_source"]["trap_donor_seed"],
            "orchestrator": "rails.probes.ptrap_flight.run_ptrap_flight",
            "launcher": "scratchpad tri/ptrap/launch_ptrap_flight.py (archived with the flight receipt)",
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
