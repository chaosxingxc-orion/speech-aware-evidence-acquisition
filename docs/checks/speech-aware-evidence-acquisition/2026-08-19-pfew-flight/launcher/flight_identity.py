"""Shared run identity for the P-FEW routing few-shot flight launcher, its
demo-binding step and its pre-flight check (exposure row
``SAEA-PROBE-pfew-180``).

Structurally the archived P-TRAP flight's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/
launcher/flight_identity.py``), with ONE documented difference, identical to
the archived P-A2T whole-population launcher's own
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-a2t-pop-flight/
launcher/flight_identity.py`` module docstring): this probe has NO committed
``configs/probes/g0-binding`` flight config. The 2026-08-19 second-arc
registration wave landed the preregistration
(``docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md``), the
machinery (``rails.probes.pfew_flight``) and the pinned read suite
(``analysis.pfew_read``) without one, and a flying agent must not create one
mid-session -- it would dirty the tree for the whole flight.

Every probe-identity and budget value below is therefore sourced from one of
exactly three places that are ALREADY COMMITTED:

  * the committed machinery's own module constants
    (``rails.probes.pfew_flight.PFEW_ARMS`` / ``FS_BAL_K`` / ``FS_SKEW_K`` /
    ``DEFAULT_DEMO_SEED`` / ``EXPECTED_SPLIT_IDENTITY_HASH``);
  * the committed frozen binding artifacts
    (``configs/probes/g0-binding/pslu-sample-devel-n60.json`` and
    ``pslu-rosters-train-only.json``, reused byte-identically from the
    consumed P-SLU/P-TRAP/P-KEY probes -- the registration's own opening line:
    "the SAME frozen 60 SLURP devel samples (seed 20260807)");
  * the committed exposure-ledger row ``SAEA-PROBE-pfew-180``'s own
    registered ceilings (200 calls / 700 speech-audio-seconds / 0.25 GPU-h),
    transcribed into :data:`REGISTERED_CEILINGS` and re-checked against the
    live ledger by ``preflight.py`` rather than trusted from here.

``values`` is the COMMITTED model fragment ``configs/model/q4km-featcache.json``
read verbatim with the SAME THREE documented deltas the P-SLU-Stage-2 / P-KEY /
P-TRAP flights used ("decode config identical to the consumed P-SLU flights" is
this registration's own section-1 requirement):

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> this campaign's own feature-cache
   directory (env ``SAEA_FEAT_CACHE_DIR`` = /home/chao/feat-cache/slurp-q4km,
   the SAME directory the consumed P-SLU/P-KEY/P-TRAP flights warmed over these
   SAME 60 samples), resolved through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()``.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel; the rails ``FrozenCoreClient`` path has no batch executor.
3. A probe-identity block is merged in so this run's config hash actually names
   the probe, its three arms, its frozen sample manifest, its roster table and
   its demo-sourcing provenance -- keys disjoint from the model fragment's own.

``server_args`` are the committed fragment's OWN argv, UNCHANGED (``-c 49152
-np 4 -fa on -ngl 999 -ctk q8_0 -ctv q8_0``) -- the s2/P-TRAP precedent. All
three arms render the SAME closed-set instruction over 18 short labels plus at
most four one-line demo pairs; nothing here approaches the 12288-token
per-slot budget, so the ``-np 1`` delta the Audio2Tool full-registry flights
need does not apply and must NOT be introduced (it would change the decode
config the registration pins to the consumed P-SLU flights).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

# The exposure-ledger row this flight is pre-registered under. FrozenCoreGate
# matches the ledger row by plan.run_id verbatim, so this string IS the row id.
RUN_ID = "SAEA-PROBE-pfew-180"

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md"
SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

PROBE_ID = "P-FEW"
CARRIER_LOCK_KEY = "slurp"
SPLIT_ROLE = "discovery"
EXECUTION_PROFILE = "bounded-discovery-probe"

# Every arm carries the sample's own real audio behind a TEXT supply block --
# identical D2 arm to the consumed P-SLU/P-TRAP flights.
D2_ARM = "fixed-legal-context"

# Registered ceilings, transcribed from the committed exposure-ledger row
# SAEA-PROBE-pfew-180 (preregistration section 4: "180 requests; <=200 core
# calls; <=700 metered audio-seconds; <=0.25 GPU-h"). preflight.py re-reads the
# LIVE ledger row and refuses if these disagree -- never trusted from here.
REGISTERED_CEILINGS = {
    "model_calls": 200,
    "speech_audio_seconds": 700,
    "gpu_hours": 0.25,
}

# The plan's own declared budgets. planned_model_calls is the EXACT total
# run_pfew_flight issues (3 arms x 60 samples; the machinery's own fail-closed
# validate_pfew_flight_summary enforces this precisely, never more, never
# fewer). The audio/GPU declarations are the registered ceilings themselves:
# the flight meters ~547 audio-seconds (182.26s x 3 passes) and spent ~0.07
# GPU-h on the structurally identical 120-request P-TRAP flight.
PLANNED_BUDGETS = {
    "model_calls": 180,
    "speech_audio_seconds": 700,
    "gpu_hours": 0.25,
}


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
    from speech_aware_evidence_acquisition.rails.probes.pfew_flight import (
        DEFAULT_DEMO_SEED,
        EXPECTED_SPLIT_IDENTITY_HASH,
        FS_BAL_K,
        FS_SKEW_K,
        PFEW_ARMS,
    )

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

    # Delta 3: probe identity, sourced only from committed machinery constants
    # and committed binding artifacts (module docstring).
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_ID,
            "stage": "2026-08-19 second-arc design order, routing-tier x filling-tier program probe 1",
            "status": "REGISTERED",
            "flight_config_version": "pfew-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "split_name": "devel",
            "split_role": SPLIT_ROLE,
            "sample_manifest": SAMPLE_MANIFEST_RELPATH,
            "roster_table": ROSTER_TABLE_RELPATH,
            "split_identity_hash": EXPECTED_SPLIT_IDENTITY_HASH,
            "arms": list(PFEW_ARMS),
            "demo_seed": DEFAULT_DEMO_SEED,
            "fs_bal_k": FS_BAL_K,
            "fs_skew_k": FS_SKEW_K,
            "demo_source": (
                "TRAIN-split (utterance text -> scenario label) pairs, read from the raw governed "
                "train.jsonl via rails.probes.pfew_flight.load_train_demo_pool (text-only, no audio "
                "opened, never devel/test) -- legal supply per the program split philosophy"
            ),
            "closed_set_construction": (
                "rails.probes.pslu_s2_flight.closed_set_phase1_supply_packet over "
                "canonical_scenario_labels(rosters), reused verbatim from the consumed A1'r phase 1"
            ),
            "orchestrator": "rails.probes.pfew_flight.run_pfew_flight",
            "launcher": "scratchpad tri2/pfew/launch_pfew_flight.py (archived with the flight receipt)",
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
