"""Shared run identity for the P-CORR-F flight launcher, its binding step and
its pre-flight check.

Structurally the archived P-TRAP flight's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/
launcher/flight_identity.py``), adapted in exactly two ways:

1. ``RUN_ID`` names the P-CORR-F exposure row ``SAEA-PROBE-pcorrf-240``.
2. **There is no committed ``configs/probes/g0-binding/pcorrf-flight.json``.**
   P-CORR-F's machinery carries its own pinned, drift-checked binding config
   document instead (``rails.probes.pcorrf_flight.build_binding_config_
   document`` / ``BINDING_CONFIG_SHA256``), which the registration's own
   section 4 makes the authoritative arm/seed/pool/L2b/legality pin. Delta 3
   below therefore sources the probe-identity block from THAT document rather
   than from a committed flight JSON -- the same information, one pin closer
   to the machinery it governs, and machine-refused on drift by
   ``assert_binding_config_sha256()``.

The model fragment, the first two documented deltas and the hash formulas are
byte-for-byte the P-TRAP / P-KEY / P-SLU-Stage-2 precedent's own -- "A3-form
base so V1/V2/A3 are directly citable" (preregistration section 2) requires
the SAME decode config the consumed P-SLU flights used.

The two deltas from the committed model fragment, each with its reason
(unchanged from the P-TRAP precedent):

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory (env ``SAEA_FEAT_CACHE_DIR`` = /home/chao/feat-cache/slurp-q4km,
   the SAME directory the consumed P-SLU/P-KEY/P-TRAP flights warmed over these
   SAME 60 samples), resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()``.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel; the rails ``FrozenCoreClient`` path has no batch executor.

``server_args`` are the committed fragment's OWN argv, UNCHANGED (``-c 49152
-np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0``): W1/W2/W4 render the SAME A3-form
100-entry roster the consumed P-SLU A3 arm flew inside a 12288-token slot, plus
a handful of short appended ``type=value`` lines (measured mean 1.02 entries
for L1, 2.00 for L2b), and W3 renders strictly less than that. No A2T-style
full-registry prefill is involved, so the ``-np 1`` delta the Audio2Tool
flights need does not apply here and must NOT be introduced (it would change
the decode config the registration pins to the consumed P-SLU flights).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-pcorrf-240"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md"

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
    from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (
        ARM_N,
        CEILING_CALLS,
        CEILING_AUDIO_SECONDS,
        CEILING_GPU_HOURS,
        DEFAULT_PLANNED_GPU_HOURS,
        DEFAULT_PLANNED_MODEL_CALLS,
        DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
        PCORRF_ARMS,
        PROBE_ID,
        assert_binding_config_sha256,
        binding_config_sha256,
        build_binding_config_document,
    )

    # Fail-closed BEFORE the identity block is built: a drifted arm table,
    # seed, train-pool pin, L2b parameter or legality declaration must never
    # reach a config hash.
    assert_binding_config_sha256()
    binding_config = build_binding_config_document()

    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    values = dict(fragment)

    # Delta 1: campaign-own feature cache.
    server_env = dict(values.get("server_env", {}))
    server_env["LLAMA_MTMD_FEAT_CACHE_DIR"] = resolve_feat_cache_dir()
    values["server_env"] = server_env

    # Delta 2: drop the batch-executor-only id_slot sentinel.
    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    # Delta 3: probe identity, sourced from the machinery's OWN pinned binding
    # config document (module docstring). Keys disjoint from the fragment's own.
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_ID,
            "status": "REGISTERED",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": "slurp",
            "split_name": "devel",
            "sample_manifest": "configs/probes/g0-binding/pslu-sample-devel-n60.json",
            "roster_table": "configs/probes/g0-binding/pslu-rosters-train-only.json",
            "arms": list(PCORRF_ARMS),
            "arm_n": ARM_N,
            "binding_config": binding_config,
            "binding_config_sha256": binding_config_sha256(),
            "planned": {
                "model_calls": DEFAULT_PLANNED_MODEL_CALLS,
                "speech_audio_seconds": DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
                "gpu_hours": DEFAULT_PLANNED_GPU_HOURS,
            },
            "registered_ceilings": {
                "model_calls": CEILING_CALLS,
                "speech_audio_seconds": CEILING_AUDIO_SECONDS,
                "gpu_hours": CEILING_GPU_HOURS,
            },
            "orchestrator": "rails.probes.pcorrf_flight.run_pcorrf_flight",
            "launcher": "scratchpad pcorrf/launch_pcorrf_flight.py (archived with the flight receipt)",
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
