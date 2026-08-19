"""Shared run identity for the P-A2T abstention-asymmetry 2x2 flight launcher
and its pre-flight check (exposure row ``SAEA-PROBE-a2t-abst-44``).

Same construction the archived P-A2T Stage-2/2b/2c launchers used
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-flight/
launcher/flight_identity.py``) and for the same reason: ``core.config.compose``
needs four COMMITTED fragments (model/dataset/baseline/experiment) and this
repository ships no Audio2Tool dataset/baseline/experiment fragment.

ONE DOCUMENTED DIFFERENCE FROM THE STAGE-2c PRECEDENT. That flight read its
probe-identity block "verbatim from the committed flight config"
(``configs/probes/g0-binding/a2t-s2c-flight.json``). This probe has NO committed
flight config: the 2026-08-19 registration wave landed the machinery
(``rails.probes.a2t_abst_flight``) and the preregistration
(``docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md``) without a
g0-binding JSON, and a flying agent must not create one mid-session (it would
dirty the tree for the whole flight -- the same reason the precedent gives for
not composing fragments). So every probe-identity value below is sourced from
one of exactly three PLACES THAT ARE ALREADY COMMITTED OR ALREADY FROZEN, never
hand-typed policy:

  * the committed machinery's own module constants
    (``rails.probes.a2t_abst_flight.A2T_ABST_CELLS`` / ``ABST_N`` /
    ``DEFAULT_SEED``) -- cells, draw size and seed;
  * the consumed A0 read's own published, hash-manifested artifact
    ``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/
    headroom.json`` -- the headroom id list, the consumed A0 ``attempt_dir``
    the tool-removal render derives its correct tools from, and the
    ``split_identity_hash``. That path is the SAME literal every committed A2T
    flight config carries under ``headroom_manifest``;
  * ``rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH`` -- the pinned constant
    the headroom artifact's own hash is cross-checked against (fail-closed in
    :func:`resolve_split`), so a drifted artifact cannot silently redefine this
    flight's split identity.

``values`` is the COMMITTED model fragment ``configs/model/q4km-featcache.json``
read verbatim with the SAME FOUR documented deltas the Stage-2/2b/2c flights
used, plus that probe-identity block. ``config_hash_of`` is byte-for-byte
``core.config._canonical_hash``'s formula and ``protocol_hash`` is computed by
``core.config.protocol_hash`` itself, so the identity stays reproducible.

The four deltas, each with its reason:

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory, resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()`` (env ``SAEA_FEAT_CACHE_DIR``).
   This flight re-uses the SAME ``audio2tool-q4km`` directory the A0 flight
   warmed over the frozen 400-item split, so the 22 real-audio requests should
   hit already-encoded features. The 22 SILENCE-SWAP requests are new derived
   media and WILL add cache entries -- expected, disclosed in the receipt.

2. ``decoding_params.id_slot`` ("per-sample") is REMOVED. That value is a
   sentinel the BATCH EXECUTOR resolves to an allocated integer slot; the rails
   ``FrozenCoreClient`` path has no batch executor.

3. The probe-identity block described above is merged in, keys disjoint from the
   model fragment's own.

4. ``server_args``: ``-np 4`` becomes ``-np 1``. llama-server divides ``-c``
   across ``--parallel`` slots, so the committed ``-c 49152 -np 4`` yields
   12288 tokens PER SLOT. ALL FOUR CELLS of this probe carry a registry-sized
   system prompt -- TP-A/TP-S the FULL 152-row registry (A0's own ~12.6k-token
   prefill, already ABOVE a 12288-token slot) and TW-A/TW-S that same registry
   minus one row -- so ``-np 4`` would make the probe unflyable, exactly as it
   would have for A0 and for Stage-2c's C3. ``-np 1`` gives the single sequence
   the whole 49152 and is memory-neutral (total ``n_ctx``, hence total KV cache,
   is unchanged); it costs no throughput either, because ``FrozenCoreClient``
   issues requests strictly sequentially, so slots 2-4 were never usable.

``-c``, ``-fa``, ``-ngl``, ``-ctk`` and ``-ctv`` are the committed fragment's own
values, unchanged.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-a2t-abst-44"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-19-a2t-abst-preregistration-REGISTERED.md"
HEADROOM_MANIFEST_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json"
)

PROBE_ID = "P-A2T-ABST"

# All four cells ride the SAME D2 arm: the supply manipulation lives inside the
# SYSTEM message text (TW's tool-removal render) or in the AUDIO payload (the
# silence swap, a registered derived slice), never in a rails 'text' content
# part, so supplied_evidence stays empty exactly as it did for A0 and for every
# Stage-2/2b/2c arm.
D2_ARM = "fixed-legal-context"

# Delta 4: see the module docstring.
SERVER_ARGS_DELTA = ("-np", "4", "-np", "1")


@dataclass(frozen=True)
class SplitBinding:
    headroom_ids: tuple[str, ...]
    consumed_a0_attempt_dir: str
    split_identity_hash: str


def resolve_split(repo: Path) -> SplitBinding:
    """Load the consumed A0 read's own published headroom artifact and
    fail-closed cross-check its split identity against the committed pinned
    constant ``rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH``."""

    from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (
        SPLIT_IDENTITY_HASH,
        load_headroom_source,
    )

    source = load_headroom_source(repo / HEADROOM_MANIFEST_RELPATH)
    if source.split_identity_hash != SPLIT_IDENTITY_HASH:
        raise RuntimeError(
            f"headroom artifact split_identity_hash {source.split_identity_hash!r} != the committed "
            f"pinned constant {SPLIT_IDENTITY_HASH!r}; refusing to fly against a drifted split"
        )
    return SplitBinding(
        headroom_ids=source.headroom_sample_ids,
        consumed_a0_attempt_dir=source.attempt_dir,
        split_identity_hash=source.split_identity_hash,
    )


def resolve_feat_cache_dir() -> str:
    """The campaign feature-cache directory, via the sanctioned named parameter
    (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km directory silently:
    an unset env var is a hard error here, because this campaign must not write
    into the warm earnings21/22 cache."""

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


def build_values(repo: Path) -> dict[str, object]:
    from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (
        A2T_ABST_CELLS,
        ABST_N,
        DEFAULT_SEED,
        seeded_abst_draw,
    )

    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    split = resolve_split(repo)

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

    # Delta 3: probe identity, sourced only from committed machinery constants
    # and the frozen headroom artifact (docstring).
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_ID,
            "stage": "2026-08-19 registration wave, panel value item V1",
            "status": "REGISTERED",
            "flight_config_version": "a2t-abst-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": "audio2tool",
            "split_name": "discovery",
            "headroom_manifest": HEADROOM_MANIFEST_RELPATH,
            "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
            "split_identity_hash": split.split_identity_hash,
            "seed": DEFAULT_SEED,
            "n_draw": ABST_N,
            "cells": list(A2T_ABST_CELLS),
            "drawn_sample_ids": list(
                seeded_abst_draw(split.headroom_ids, seed=DEFAULT_SEED, n=ABST_N)
            ),
            "orchestrator": "rails.probes.a2t_abst_flight.run_a2t_abst_flight",
            "launcher": "scratchpad tri/abst/launch_a2t_abst.py (archived with the flight receipt)",
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
