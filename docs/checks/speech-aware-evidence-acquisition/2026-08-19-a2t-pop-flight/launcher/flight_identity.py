"""Shared run identity for the P-A2T whole-population regression-arm flight
launcher and its pre-flight check (exposure row ``SAEA-PROBE-a2t-pop-194``).

Same construction the archived P-A2T Stage-2/2b/2c launchers used
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-flight/
launcher/flight_identity.py``) and for the same reason: ``core.config.compose``
needs four COMMITTED fragments (model/dataset/baseline/experiment) and this
repository ships no Audio2Tool dataset/baseline/experiment fragment.

ONE DOCUMENTED DIFFERENCE FROM THE STAGE-2c PRECEDENT, identical to the sibling
abstention probe's: this probe has NO committed g0-binding flight config (the
2026-08-19 registration wave landed the machinery
``rails.probes.a2t_pop_flight`` and the preregistration
``docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md`` without
one, and a flying agent must not create one mid-session -- it would dirty the
tree for the whole flight). Every probe-identity value below is therefore
sourced from one of exactly three PLACES THAT ARE ALREADY COMMITTED OR ALREADY
FROZEN:

  * the committed machinery's own module constants
    (``rails.probes.a2t_pop_flight.A2T_POP_ARMS`` / ``EM_CORRECT_N`` /
    ``SPLIT_IDENTITY_HASH`` / ``DEFAULT_SEED``);
  * the consumed A0 read's own published, hash-manifested artifact
    ``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/
    headroom.json``, loaded through the machinery's OWN
    ``load_headroom_source`` -- the preregistration's section 2 sourcing rule
    ("via the consumed read archive's published artifacts, never re-scoring")
    made executable;
  * the machinery's own fail-closed ``assert_split_identity_hash_pinned``,
    which refuses a drifted artifact rather than silently redefining the split.

The 97-id EM-correct roster itself is NOT recorded in this module: it is derived
at flight time by ``rails.probes.a2t_pop_flight.derive_em_correct_ids``
(fail-closed at exactly 97) and written into the attempt directory's own
arm-plan artifact.

``values`` is the COMMITTED model fragment ``configs/model/q4km-featcache.json``
read verbatim with the SAME FOUR documented deltas the Stage-2/2b/2c flights
used, plus the probe-identity block. The four deltas, each with its reason:

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory, resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()`` (env ``SAEA_FEAT_CACHE_DIR``).
   This flight re-uses the SAME ``audio2tool-q4km`` directory the A0 flight
   warmed over the frozen 400-item split, and every one of its 194 requests
   sends REAL audio from that split (no derived media anywhere), so the cache
   entry count should not move.

2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel; the rails ``FrozenCoreClient`` path has no batch executor.

3. The probe-identity block described above is merged in, keys disjoint from the
   model fragment's own.

4. ``server_args``: ``-np 4`` becomes ``-np 1``. llama-server divides ``-c``
   across ``--parallel`` slots, so the committed ``-c 49152 -np 4`` yields
   12288 tokens PER SLOT. R0 IS A0's own request BYTE-IDENTICALLY -- the FULL
   152-row registry, ~12.6k tokens of prefill, already ABOVE a 12288-token slot
   -- so ``-np 4`` would make the comparator arm unflyable, exactly as it would
   have for A0 itself and for Stage-2c's C3. (R1's B1-form stripped roster is
   tiny, but a single session serves both arms.) ``-np 1`` gives the single
   sequence the whole 49152 and is memory-neutral (total ``n_ctx``, hence total
   KV cache, is unchanged); it costs no throughput either, because
   ``FrozenCoreClient`` issues requests strictly sequentially, so slots 2-4 were
   never usable.

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
RUN_ID = "SAEA-PROBE-a2t-pop-194"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md"
HEADROOM_MANIFEST_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-18-pa2t-a0-read/headroom.json"
)

PROBE_ID = "P-A2T-POP"

# Both arms ride the SAME D2 arm: R0 is A0's own zero-supply request and R1's
# supply lives inside the SYSTEM message text, never in a rails 'text' content
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
    """Load the consumed A0 read's own published headroom artifact through the
    machinery's OWN loader and run the machinery's OWN fail-closed pinned-hash
    guard against it."""

    from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (
        assert_split_identity_hash_pinned,
        load_headroom_source,
    )

    source = load_headroom_source(repo / HEADROOM_MANIFEST_RELPATH)
    assert_split_identity_hash_pinned(source.split_identity_hash)
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
    from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (
        A2T_POP_ARMS,
        DEFAULT_SEED,
        EM_CORRECT_N,
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
    # and the frozen headroom artifact (docstring). The 97-id roster itself is
    # derived at flight time, never frozen here.
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_ID,
            "stage": "2026-08-19 registration wave, adversarial-panel Finding 3 (V4)",
            "status": "REGISTERED",
            "flight_config_version": "a2t-pop-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": "audio2tool",
            "split_name": "discovery",
            "headroom_manifest": HEADROOM_MANIFEST_RELPATH,
            "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
            "split_identity_hash": split.split_identity_hash,
            "seed": DEFAULT_SEED,
            "population": "EM-correct ids of the frozen A2T 400 (tool_accuracy==1 AND exact_match==1)",
            "population_n": EM_CORRECT_N,
            "arms": list(A2T_POP_ARMS),
            "orchestrator": "rails.probes.a2t_pop_flight.run_a2t_pop_flight",
            "launcher": "scratchpad tri/pop/launch_a2t_pop.py (archived with the flight receipt)",
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
