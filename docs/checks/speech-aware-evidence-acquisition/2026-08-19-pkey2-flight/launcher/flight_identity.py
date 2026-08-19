"""Shared run identity for the P-KEY flight launcher and its pre-flight check.

Structurally the P-SLU Stage-2 flight's own ``flight_identity.py`` (archived at
``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-s2-flight/launcher/``),
adapted only in run identity: RUN_ID names the P-KEY exposure row
``SAEA-PROBE-pkey2-338`` and the flight config is the committed
``configs/probes/g0-binding/pkey-flight.json``. The model fragment, the three
documented deltas and the hash formulas are byte-for-byte the s2 precedent's
own -- "decode config identical to the consumed P-SLU flights" is the
registration's own requirement
(docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md).

The three deltas from the committed model fragment, each with its reason
(unchanged from the s2 precedent):

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory (env ``SAEA_FEAT_CACHE_DIR`` = /home/chao/feat-cache/slurp-q4km,
   the SAME directory the P-SLU flights warmed), resolved through the
   sanctioned named parameter ``core.session.lifecycle.feat_cache_dir()``.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel; the rails ``FrozenCoreClient`` path has no batch executor.
3. A probe-identity block is merged in so this run's config hash actually
   names the probe, its five arms, its frozen sample manifest, its roster
   table and its pinned T0/TXT text hashes -- keys disjoint from the model
   fragment's own.

``server_args`` are the committed fragment's OWN argv, unchanged (the same
``-c 49152 -np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0`` the consumed P-SLU
flights' session receipts record).

SUCCESSOR-RUN NOTE (2026-08-19, preregistration section 8). This launcher is the
predecessor ``pkeyfly/`` launcher with exactly TWO string changes, both of them
run identity:

  a. ``RUN_ID`` ``SAEA-PROBE-pkey-303`` -> ``SAEA-PROBE-pkey2-338``. The
     predecessor run is CLOSED NOT-CONSUMED; its attempt store durably charges
     attempt-1's 183 calls forever, so no compliant attempt could fly under it.
     ``RUN_ID`` is the ONLY place run identity is bound: it flows into
     ``ExecutionPlan.run_id``, which is what ``FrozenCoreGate`` matches against
     the exposure row, what ``core.attempts.AttemptStore`` namespaces prior
     durable spend by, and what ``rails.core_client.build_slice_registry``
     namespaces the silence-swap slices by. The committed flight config binds
     NO run identity -- its own ``execution_plan.note`` says run_id/attempt_id
     "are assigned by the flying agent's own launcher at flight time, never
     frozen here", and its documentary ``exposure_ledger_row`` field is read by
     nothing in ``src/`` (it is pinned to the predecessor row by
     ``tests/unit/test_pkey_flight_config.py``, which must stay green).
  b. the ``launcher`` provenance value below now names ``pkey2fly/`` -- the
     directory that actually flies. That string is inside the hashed values
     bundle, so this run's ``config_hash``/``protocol_hash`` differ from the
     predecessor pre-flight's by exactly this one field. Nothing pins either
     hash; the DECODE config (decoding_params, server_args, server_env) is
     byte-identical to the s2 precedent, which is what the registration
     actually requires.

Everything else -- the flight config path, the frozen 60-sample manifest, the
roster table, the pinned T0/TXT text hashes, the plan ceilings, the model
fragment and its three deltas -- is unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-pkey2-338"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
FLIGHT_CONFIG_RELPATH = "configs/probes/g0-binding/pkey-flight.json"

D2_ARM = "fixed-legal-context"


def resolve_feat_cache_dir() -> str:
    """The campaign feature-cache directory, via the sanctioned named
    parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory silently: an unset env var is a hard error here, because this
    launcher's whole point is that a SLURP campaign must not write into
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
            "t0_instruction_sha256": flight["t0_instruction_sha256"],
            "txt_template_sha256": flight["txt_template_sha256"],
            "launcher": "scratchpad pkey2fly/launch_pkey_flight.py (archived with the flight receipt)",
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
