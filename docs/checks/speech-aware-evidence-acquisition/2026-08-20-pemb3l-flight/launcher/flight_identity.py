"""Shared run identity for the P-EMB-3L flight launcher and its pre-flight
check (exposure row ``SAEA-PROBE-pemb3l-234``).

Structurally the archived P-EMB launcher's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb1-flight/
launcher/flight_identity.py``) -- including its documented "no committed
g0-binding flight config" difference, which applies here for the same reason:
the 2026-08-20 registration wave landed the preregistration
(``docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md``) and the
machinery delta (``rails.probes.pemb3l_flight`` + the
``rails.embedding_client`` prefix seam + ``analysis.pemb3l_read``) without one,
and a flying agent must not create one mid-session -- it would dirty the tree
for the whole flight.

Every probe-identity and budget value below is sourced from one of exactly
three places that are ALREADY COMMITTED at ``339e8ce``:

  * the committed machinery's own module constants
    (``rails.probes.pemb3l_flight.PROBE_ID`` / ``ARMS`` / ``ARM_IDS`` /
    ``ARM_AUDIO_N`` / ``ARM_LABEL_N`` / ``ARM_TOTAL_N`` /
    ``EXPECTED_TOTAL_CONTACTS`` / ``BINDING_CONFIG_SHA256`` /
    ``AUDIO_INSTRUCT_PREFIX`` / ``TEXT_INSTRUCT_PREFIX`` /
    ``EXPECTED_RUN_A_SPLIT_IDENTITY_HASH``, plus
    ``rails.embedding_client.EMBEDDING_DIM``);
  * the committed frozen binding artifacts
    (``configs/probes/g0-binding/pslu-sample-devel-n60.json`` and
    ``pslu-rosters-train-only.json`` -- the SAME P-EMB-1 surface, reused
    verbatim);
  * the committed exposure-ledger row's own registered ceilings, transcribed
    into :data:`REGISTERED_CEILINGS` and re-checked against the LIVE ledger by
    ``preflight.py`` rather than trusted from here.

THE SERVER IS NOT THE GENERATION SERVER. ``values`` starts from the COMMITTED
model fragment ``configs/model/q4km-featcache.json`` (so the pinned q4km GGUF
+ mmproj identity, the runtime receipt and the transport all stay the frozen
core's own), with the P-EMB precedent's own deltas plus ONE this probe adds:

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> ``slurp-q4km``
   (``docs/featcache-directories.md``'s ``<dataset>-<encoder>`` rule) -- the
   SAME directory the consumed P-SLU/P-KEY/P-TRAP and P-EMB-1 flights already
   warmed over these SAME 60 clips, resolved through the sanctioned named
   parameter ``core.session.lifecycle.feat_cache_dir()``.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel. (The embedding client accepts no decoding params at all; the
   surviving block is carried only so this run's ``config_hash`` still records
   what the committed fragment declared.)
3. A probe-identity block is merged in so this run's config hash actually names
   the probe, its three arms, their EXACT instruct prefixes, the pinned binding
   config sha256, the split, the contact counts and the embedding dimension --
   keys disjoint from the model fragment's own.
4. ``server_args``: ``--embedding`` is APPENDED (E-0 binding decision).
   ``-ngl 999`` (also E-0-pinned) is already the committed fragment's own value
   and is left untouched, as are ``-c``, ``-fa``, ``-ctk`` and ``-ctv``.
5. ``server_args``: ``-np 4`` becomes ``-np 1``. Embedding mode pools ONE
   sequence per request and this launcher issues its contacts strictly
   sequentially, so slots 2-4 could never be used; ``-np 1`` also gives that
   single sequence the whole ``-c`` budget instead of a quarter of it, and is
   memory-neutral.
6. ``base_url``: port 8080 -> :data:`EMBEDDING_PORT` (8093).

7. NEW FOR THIS PROBE -- ``sessions``. A resident llama-server's pooling mode
   is a STARTUP FLAG, never a per-request parameter
   (``rails.probes.pemb3l_flight`` module docstring), so the registered sweep
   needs TWO sequential server sessions: ``--pooling last`` for L1+L2 and
   ``--pooling mean`` for L3. ``values["server_args"]`` therefore carries the
   argv tokens COMMON to both sessions and deliberately carries NO
   ``--pooling`` pair; :data:`SESSIONS` (mirrored into ``values["sessions"]``)
   carries each session's own COMPLETE argv, and those are the ONLY argv ever
   spawned. Both live inside the SAME ``config_hash``, so the protocol hash
   this run carries names the whole registered two-session protocol rather
   than either half of it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md"
SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

PROBE_LABEL = "P-EMB-3L"
EXECUTION_PROFILE = "bounded-discovery-probe"
SPLIT_ROLE = "discovery"
CARRIER_LOCK_KEY = "slurp"
FEAT_CACHE_SUFFIX = "slurp-q4km"

# Zero generation: every contact is an encode+pool with no sampling anywhere in
# the request path. The D2 arm label is still recorded so the protocol hash
# names a legal arm.
D2_ARM = "fixed-legal-context"

GENERATION_PORT = 8080
EMBEDDING_PORT = 8093

# Delta 4 / delta 5 (module docstring).
EMBEDDING_SERVER_ARGS_APPEND = ("--embedding",)
SERVER_ARGS_NP_DELTA = ("-np", "4", "-np", "1")

# Delta 7 (module docstring): one session PER POOLING MODE, in flight order.
# ``arm_ids`` is filled from the committed machinery's own arm table by
# :func:`session_plan` -- never hand-listed here.
SESSION_KEYS = ("last", "mean")

# A text contact spends a CALL but meters ZERO speech audio. The durable
# attempt store's own record_usage API refuses a non-positive audio figure
# (core.attempts.errors._positive_finite), so a text contact is charged this
# documented, deliberately negligible sentinel instead: 54 of them (18 labels x
# 3 arms) sum to 5.4e-8 seconds, orders of magnitude below any reporting
# resolution and below every registered ceiling's own integer granularity. The
# AUDIO contacts carry their sample's real ``audio_seconds``, exactly as a
# generation flight does -- and because each arm re-embeds the SAME 60 clips,
# the sweep meters that one-pass total THREE times.
TEXT_CONTACT_AUDIO_SECONDS = 1e-9

# Registered ceilings transcribed from the committed exposure-ledger row
# (preregistration section 4: "234 contacts; <=260 calls; <=600 metered
# audio-seconds; <=0.3 GPU-h"). preflight.py re-reads the LIVE ledger row and
# refuses if these disagree -- never trusted from here.
REGISTERED_CEILINGS: dict[str, object] = {
    "model_calls": 260,
    "speech_audio_seconds": 600,
    "gpu_hours": 0.3,
}

# planned_model_calls is the EXACT total the sweep issues (234; the machinery's
# own fail-closed run_pemb3l_sweep_flight enforces this precisely).
PLANNED_BUDGETS: dict[str, object] = {
    "model_calls": 234,
    "speech_audio_seconds": 600,
    "gpu_hours": 0.3,
}


def run_id() -> str:
    from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import PROBE_ID

    return PROBE_ID


def split_identity_hash() -> str:
    """The machinery's own pin, cross-checked against the SAME frozen
    60-sample manifest the consumed P-SLU/P-KEY/P-TRAP/P-EMB-1 probes used.
    Never a fresh derivation -- ``rails.probes.pemb3l_flight`` re-exports
    ``pemb_flight.EXPECTED_RUN_A_SPLIT_IDENTITY_HASH`` verbatim and this
    function runs the parent's own fail-closed assertion on it."""

    from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (
        EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
        assert_run_a_split_identity_hash,
    )

    assert_run_a_split_identity_hash(EXPECTED_RUN_A_SPLIT_IDENTITY_HASH)
    return EXPECTED_RUN_A_SPLIT_IDENTITY_HASH


def resolve_feat_cache_dir() -> str:
    """This sweep's dataset-scoped feature-cache directory, via the sanctioned
    named parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory silently."""

    from speech_aware_evidence_acquisition.core.session import (
        FEAT_CACHE_DIR_DEFAULT,
        feat_cache_dir,
    )

    resolved = feat_cache_dir()
    if resolved == FEAT_CACHE_DIR_DEFAULT:
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is unset (or set to the legacy q4km directory); this campaign "
            f"must never write into the warm earnings21/22 cache ({FEAT_CACHE_DIR_DEFAULT}) -- "
            "see docs/featcache-directories.md"
        )
    if not resolved.rstrip("/").endswith(FEAT_CACHE_SUFFIX):
        raise RuntimeError(
            f"SAEA_FEAT_CACHE_DIR resolved to {resolved!r}; P-EMB-3L writes only to "
            f"/home/chao/feat-cache/{FEAT_CACHE_SUFFIX}"
        )
    return resolved


def _apply_np_delta(argv: list[str]) -> list[str]:
    """Replace the single ``-np 4`` pair with ``-np 1``. Fails closed if the
    committed fragment ever stops carrying exactly that pair, so this delta can
    never silently become a no-op (or clobber a different value). Byte-for-byte
    the archived P-EMB launcher's own helper."""

    old_flag, old_value, new_flag, new_value = SERVER_ARGS_NP_DELTA
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


def session_plan() -> list[dict[str, object]]:
    """The two sessions, in flight order, each carrying the arm ids it flies.
    ``arm_ids`` is READ OFF the committed machinery's own arm table
    (``ARMS``/``pooling_mode``), never hand-listed -- so if a future edit ever
    moved an arm between pooling modes, this routing would follow it (and the
    binding-config sha256 guard would refuse the flight anyway)."""

    from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import ARMS

    plan: list[dict[str, object]] = []
    for key in SESSION_KEYS:
        arm_ids = [arm.arm_id for arm in ARMS if arm.pooling_mode == key]
        if not arm_ids:
            raise RuntimeError(f"no committed arm declares pooling_mode {key!r}")
        plan.append({"session_key": key, "pooling_mode": key, "arm_ids": arm_ids})
    covered = [arm_id for block in plan for arm_id in block["arm_ids"]]  # type: ignore[union-attr]
    if sorted(covered) != sorted(arm.arm_id for arm in ARMS):
        raise RuntimeError(
            f"session routing covers {sorted(covered)} but the committed arm table declares "
            f"{sorted(arm.arm_id for arm in ARMS)} -- every arm must be routed exactly once"
        )
    return plan


def build_values(repo: Path) -> dict[str, object]:
    from speech_aware_evidence_acquisition.rails.embedding_client import (
        EMBEDDING_DIM,
        EMBEDDING_ENDPOINT_PATH,
        LLAMA_MEDIA_MARKER_ENV,
        PROPS_MEDIA_MARKER_FIELD,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (
        ARM_AUDIO_N,
        ARM_LABEL_N,
        ARM_TOTAL_N,
        ARMS,
        AUDIO_INSTRUCT_PREFIX,
        BINDING_CONFIG_SCHEMA,
        BINDING_CONFIG_SHA256,
        CITED_MEAN_BARE_ACCURACY,
        EXPECTED_TOTAL_CONTACTS,
        TEXT_INSTRUCT_PREFIX,
        assert_binding_config_sha256,
        binding_config_sha256,
    )

    # Fail-closed BEFORE any value is composed: the live arm table's own digest
    # must equal the pinned one, so the two EXACT instruct-prefix strings this
    # config hash is about to record can never have drifted.
    assert_binding_config_sha256()

    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    values = dict(fragment)

    # Delta 1: dataset-scoped feature cache.
    server_env = dict(values.get("server_env", {}))
    server_env["LLAMA_MTMD_FEAT_CACHE_DIR"] = resolve_feat_cache_dir()
    values["server_env"] = server_env

    # Delta 2: drop the batch-executor-only id_slot sentinel.
    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    # Deltas 4 + 5: embedding mode, one sequence gets the whole context. NO
    # --pooling pair here: that flag is per-session (delta 7).
    argv = _apply_np_delta([str(token) for token in values.get("server_args", [])])
    common_argv = argv + list(EMBEDDING_SERVER_ARGS_APPEND)
    values["server_args"] = common_argv

    # Delta 6: the embedding tier's own port.
    values["base_url"] = f"http://127.0.0.1:{EMBEDDING_PORT}"

    # Delta 7: the two sessions' own COMPLETE argv -- the only argv spawned.
    sessions = []
    for block in session_plan():
        sessions.append(
            {
                "session_key": block["session_key"],
                "pooling_mode": block["pooling_mode"],
                "arm_ids": list(block["arm_ids"]),  # type: ignore[arg-type]
                "server_args": common_argv + ["--pooling", str(block["pooling_mode"])],
            }
        )
    values["sessions"] = sessions

    # Delta 3: probe identity, sourced only from committed machinery constants
    # and committed binding artifacts (module docstring).
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_LABEL,
            "stage": "2026-08-20 owner order: try the LOCAL omni model first, before the external-embedder survey concludes",
            "status": "REGISTERED",
            "flight_config_version": "pemb3l-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "split_name": "devel",
            "split_role": SPLIT_ROLE,
            "split_identity_hash": split_identity_hash(),
            "sample_manifest": SAMPLE_MANIFEST_RELPATH,
            "roster_table": ROSTER_TABLE_RELPATH,
            "tier": "embedding (encode+pool, ZERO generation)",
            "embedding_dim": EMBEDDING_DIM,
            "embedding_endpoint": EMBEDDING_ENDPOINT_PATH,
            "media_marker_env": LLAMA_MEDIA_MARKER_ENV,
            "media_marker_props_field": PROPS_MEDIA_MARKER_FIELD,
            "binding_config_schema": BINDING_CONFIG_SCHEMA,
            "binding_config_sha256": BINDING_CONFIG_SHA256,
            "binding_config_sha256_recomputed": binding_config_sha256(),
            "audio_instruct_prefix": AUDIO_INSTRUCT_PREFIX,
            "text_instruct_prefix": TEXT_INSTRUCT_PREFIX,
            "arms": [
                {
                    "arm_id": arm.arm_id,
                    "pooling_mode": arm.pooling_mode,
                    "audio_prefix": arm.audio_prefix,
                    "text_prefix": arm.text_prefix,
                }
                for arm in ARMS
            ],
            "audio_contacts_per_arm": ARM_AUDIO_N,
            "text_contacts_per_arm": ARM_LABEL_N,
            "contacts_per_arm": ARM_TOTAL_N,
            "total_contacts": EXPECTED_TOTAL_CONTACTS,
            "text_contact_kind": "the 18 canonical SLURP scenario labels (bare in L1; instruct-prefixed in L2/L3)",
            "cited_mean_bare_accuracy": CITED_MEAN_BARE_ACCURACY,
            "cited_mean_bare_provenance": "docs/readiness/2026-08-19-pemb1-verdict.md section 1 (consumed P-EMB-1, EMB-WEAK) -- NOT re-flown here",
            "orchestrator": "rails.probes.pemb3l_flight.run_pemb3l_sweep_flight",
            "launcher": "scratchpad pemb3l/launch_pemb3l_flight.py (archived with the flight receipt)",
        }
    )
    return values


def config_hash_of(values: Mapping[str, object]) -> str:
    """Byte-identical to ``core.config._canonical_hash``."""

    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def session_argv(values: Mapping[str, object], session_key: str) -> list[str]:
    raw = values.get("sessions", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("sessions must be a list")
    for block in raw:
        if isinstance(block, Mapping) and block.get("session_key") == session_key:
            argv = block.get("server_args", [])
            if not isinstance(argv, (list, tuple)):
                raise ValueError(f"session {session_key!r} server_args must be a list")
            return [str(token) for token in argv]
    raise ValueError(f"no session block for {session_key!r}")


def server_env(values: Mapping[str, object]) -> dict[str, str]:
    raw = values.get("server_env", {})
    if not isinstance(raw, Mapping):
        raise ValueError("server_env must be a mapping")
    return {str(k): str(v) for k, v in raw.items()}
