"""Shared run identity for the P-A2T Stage-2b follow-up flight launcher and its
pre-flight check.

Same construction the archived P-A2T Stage-2 supply-probe launcher used
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2-flight/
launcher/flight_identity.py``) and for the same reason: ``core.config.compose``
needs four COMMITTED fragments (model/dataset/baseline/experiment) and this
repository ships no Audio2Tool dataset/baseline/experiment fragment -- creating
three config files just to name a flight that already has its own committed
binding (``configs/probes/g0-binding/a2t-s2b-flight.json``) would dirty the tree
for the whole flight. That config's own ``execution_plan`` note sanctions
exactly this: "protocol_hash and run_id/attempt_id are assigned by the flying
agent's own launcher at flight time, never frozen here."

``values`` is the COMMITTED model fragment ``configs/model/q4km-featcache.json``
read verbatim with FOUR documented deltas (identical to the Stage-2 flight's own
four), plus a probe-identity block read verbatim from the committed Stage-2b
flight config. ``config_hash_of`` is byte-for-byte ``core.config._canonical_hash``'s
formula and ``protocol_hash`` is computed by ``core.config.protocol_hash``
itself, so the identity stays reproducible.

The four deltas, each with its reason:

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory, resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()`` (env ``SAEA_FEAT_CACHE_DIR``).
   The fragment hand-types the LEGACY ``/home/chao/feat-cache/q4km`` (26 GB,
   warm for earnings21/22); ``docs/featcache-directories.md`` requires a NEW
   dataset campaign to use ``/home/chao/feat-cache/<dataset>-<encoder>/``. This
   flight re-uses the SAME ``audio2tool-q4km`` directory the A0 flight warmed and
   the Stage-2 flight re-hit (480 entries over the frozen 400-item split), so
   every one of this flight's 240 requests should hit an already-encoded audio
   feature and the cache entry count should not move.

2. ``decoding_params.id_slot`` ("per-sample") is REMOVED. That value is a
   sentinel the BATCH EXECUTOR resolves to an allocated integer slot; the
   rails ``FrozenCoreClient`` path has no batch executor, and
   ``core.model.adapter.request`` refuses an unresolved sentinel so it can
   never reach the server as a string.

3. A probe-identity block is merged in so this run's config hash actually names
   the flight, its two arms, its seed, its frozen split receipt, the Stage-2
   arm-plan it reuses verbatim and its pre-registration -- keys disjoint from
   the model fragment's own, exactly the disjointness ``compose`` enforces
   across fragments.

4. ``server_args``: ``-np 4`` becomes ``-np 1``. llama-server divides ``-c``
   across ``--parallel`` slots, so the committed ``-c 49152 -np 4`` yields
   12288 tokens PER SLOT. THIS FLIGHT STILL NEEDS ``-np 1``: B1 carries a
   nodefaults roster of 1-9 registry rows (small), but B2 is the FULL 152-row
   registry PLUS the pinned header PLUS one appended wrong row -- marginally
   ABOVE A0's own ~12.6k-token prefill -- which would overflow a 12288-token
   slot and make B2 unflyable. ``-np 1`` gives the single sequence the whole
   49152 and is memory-neutral (total ``n_ctx``, hence total KV cache, is
   unchanged). It costs no throughput either: ``FrozenCoreClient`` issues
   requests strictly sequentially, so slots 2-4 were never usable.

``-c``, ``-fa``, ``-ngl``, ``-ctk`` and ``-ctv`` are the committed fragment's
own values, unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-a2t-s2b-120"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
FLIGHT_CONFIG_RELPATH = "configs/probes/g0-binding/a2t-s2b-flight.json"
PREREGISTRATION_RELPATH = (
    "docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md"
)

# Both arms ride the SAME D2 arm: the supply manipulation lives inside the
# SYSTEM message text, never in a rails 'text' content part, so
# supplied_evidence stays empty for B1/B2 exactly as it did for every Stage-2
# arm and the zero-supply A0 request.
D2_ARM = "fixed-legal-context"

# Delta 4: see the module docstring.
SERVER_ARGS_DELTA = ("-np", "4", "-np", "1")


def resolve_feat_cache_dir() -> str:
    """The campaign feature-cache directory, via the sanctioned named parameter
    (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km directory
    silently: an unset env var is a hard error here, because this campaign must
    not write into the warm earnings21/22 cache."""

    from speech_aware_evidence_acquisition.core.session import (
        FEAT_CACHE_DIR_DEFAULT,
        feat_cache_dir,
    )

    resolved = feat_cache_dir()
    if resolved == FEAT_CACHE_DIR_DEFAULT:
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is unset (or set to the legacy q4km directory); "
            "this Audio2Tool campaign must never write into the warm earnings21/22 "
            f"cache ({FEAT_CACHE_DIR_DEFAULT}) -- see docs/featcache-directories.md"
        )
    if not resolved.rstrip("/").endswith("audio2tool-q4km"):
        raise RuntimeError(
            f"SAEA_FEAT_CACHE_DIR resolved to {resolved!r}; this flight writes only to "
            "/home/chao/feat-cache/audio2tool-q4km (never slurp-q4km, never q4km)"
        )
    return resolved


def _apply_np_delta(argv: list[str]) -> list[str]:
    """Replace the single ``-np 4`` pair with ``-np 1``. Fails closed if the
    committed fragment ever stops carrying exactly that pair, so this delta can
    never silently become a no-op (or clobber a different value)."""

    old_flag, old_value, new_flag, new_value = SERVER_ARGS_DELTA
    positions = [i for i, token in enumerate(argv) if token == old_flag]
    if len(positions) != 1:
        raise RuntimeError(
            f"expected exactly one {old_flag!r} in the committed server_args, found "
            f"{len(positions)} in {argv!r}"
        )
    index = positions[0]
    if argv[index + 1] != old_value:
        raise RuntimeError(
            f"expected {old_flag} {old_value} in the committed server_args, found "
            f"{old_flag} {argv[index + 1]!r}; refusing to rewrite an unexpected value"
        )
    patched = list(argv)
    patched[index] = new_flag
    patched[index + 1] = new_value
    return patched


def stage2_arm_plan_path(flight: Mapping[str, object]) -> Path:
    """Expand the committed ``stage2_arm_plan_path.path`` placeholder against the
    runtime ``SPEECHRL_DATA_DIR`` (the config stores the literal
    ``$SPEECHRL_DATA_DIR/...`` string; "a real launcher expands it at flight
    time"). Fails closed rather than silently resolving a relative path."""

    import os

    raw = str(flight["stage2_arm_plan_path"]["path"])  # type: ignore[index]
    token = "$SPEECHRL_DATA_DIR"
    if token not in raw:
        raise RuntimeError(f"stage2_arm_plan_path.path lost its {token} placeholder: {raw!r}")
    data_dir = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_dir:
        raise RuntimeError("SPEECHRL_DATA_DIR is unset; cannot expand the Stage-2 arm-plan path")
    return Path(raw.replace(token, data_dir.rstrip("/")))


def build_values(repo: Path) -> dict[str, object]:
    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    flight = json.loads((repo / FLIGHT_CONFIG_RELPATH).read_text(encoding="utf-8"))

    values = dict(fragment)

    # Delta 1: campaign-own feature cache.
    env = dict(values.get("server_env", {}))
    env["LLAMA_MTMD_FEAT_CACHE_DIR"] = resolve_feat_cache_dir()
    values["server_env"] = env

    # Delta 2: drop the batch-executor-only id_slot sentinel.
    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    # Delta 4: one sequence gets the whole context (docstring).
    values["server_args"] = _apply_np_delta([str(t) for t in values.get("server_args", [])])

    # Delta 3: probe identity, read verbatim from the committed flight config.
    # (Stage-2's own block carried an ``a0_verdict`` key; the Stage-2b config
    # declares no such key -- its provenance is the Stage-2 arm plan it reuses,
    # named here instead.)
    values.update(
        {
            "arm": D2_ARM,
            "probe": flight["probe"],
            "stage": flight["stage"],
            "status": flight["status"],
            "flight_config_version": flight["flight_config_version"],
            "flight_config": FLIGHT_CONFIG_RELPATH,
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": flight["carrier_lock_key"],
            "split_name": flight["execution_plan"]["split_role"],
            "headroom_manifest": flight["headroom_manifest"],
            "stage2_arm_plan": str(flight["stage2_arm_plan_path"]["path"]),
            "seed": flight["seed"],
            "arms": list(flight["arms"]),
            "orchestrator": "rails.probes.a2t_s2b_flight.run_a2t_s2b_flight",
            "launcher": "scratchpad s2bfly/launch_pa2t_s2b.py (archived with the flight receipt)",
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
