"""Shared run identity for the P-EMB embedding-tier flight launcher and its
pre-flight check (exposure rows ``SAEA-PROBE-pemb1-78`` / ``SAEA-PROBE-pemb2-552``).

Structurally the archived P-A2T whole-population launcher's own
``flight_identity.py`` (``docs/checks/speech-aware-evidence-acquisition/
2026-08-19-a2t-pop-flight/launcher/flight_identity.py``) -- including its
documented "no committed g0-binding flight config" difference, which applies
here for the same reason: the 2026-08-19 second-arc registration wave landed
the preregistration (``docs/readiness/2026-08-19-pemb-preregistration-
REGISTERED.md``), the machinery (``rails.embedding_client`` +
``rails.probes.pemb_flight``) and the pinned read suite
(``analysis.pemb_read``) without one, and a flying agent must not create one
mid-session -- it would dirty the tree for the whole flight.

Every probe-identity and budget value below is sourced from one of exactly
three places that are ALREADY COMMITTED:

  * the committed machinery's own module constants
    (``rails.probes.pemb_flight.RUN_A_ID`` / ``RUN_B_ID`` / ``RUN_A_AUDIO_N`` /
    ``RUN_A_LABEL_N`` / ``RUN_B_AUDIO_N`` / ``RUN_B_ROW_N`` /
    ``EXPECTED_RUN_A_SPLIT_IDENTITY_HASH`` / ``EXPECTED_RUN_B_SPLIT_IDENTITY_HASH``,
    plus ``rails.embedding_client.EMBEDDING_DIM``);
  * the committed frozen binding artifacts
    (``configs/probes/g0-binding/pslu-sample-devel-n60.json`` and
    ``pslu-rosters-train-only.json`` for Run A; the Audio2Tool receipt-scoped
    ``discovery`` split and ``tools_registry.csv`` for Run B, both reached
    through their own committed loaders);
  * the committed exposure-ledger rows' own registered ceilings, transcribed
    into :data:`RUNS` and re-checked against the LIVE ledger by ``preflight.py``
    rather than trusted from here.

THE SERVER IS NOT THE GENERATION SERVER. ``values`` starts from the COMMITTED
model fragment ``configs/model/q4km-featcache.json`` (so the pinned q4km GGUF
+ mmproj identity, the runtime receipt and the transport all stay the frozen
core's own), with FIVE documented deltas -- the first three are the P-SLU/
P-KEY/P-TRAP precedent's own, the last two are this probe's embedding-mode
binding decisions from E-0 (preregistration opening paragraph):

1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> the RUN's own dataset-scoped
   feature-cache directory (``docs/featcache-directories.md``'s
   ``<dataset>-<encoder>`` rule: ``slurp-q4km`` for Run A, ``audio2tool-q4km``
   for Run B -- the SAME directories the consumed P-SLU/P-KEY/P-TRAP and A0/
   Stage-2 flights already warmed over these SAME audio files), resolved
   through the sanctioned named parameter
   ``core.session.lifecycle.feat_cache_dir()``. Because ``server_env`` is
   fixed at spawn time, this is also why the two runs take two SEQUENTIAL
   sessions rather than one shared session.
2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- batch-executor-only
   sentinel. (The embedding client accepts no decoding params at all; the
   surviving block is carried only so this run's ``config_hash`` still records
   what the committed fragment declared.)
3. A probe-identity block is merged in so this run's config hash actually names
   the probe, its run, its split, its contact counts and its embedding
   dimension -- keys disjoint from the model fragment's own.
4. ``server_args``: ``--embedding --pooling mean`` are APPENDED. This is the
   E-0 binding decision, verbatim from the preregistration: "pooled audio
   embeddings work AS-BUILT on the pinned llama.cpp via a separate instance
   with ``--embedding --pooling mean``". ``-ngl 999`` (also E-0-pinned) is
   already the committed fragment's own value and is left untouched, as are
   ``-c``, ``-fa``, ``-ctk`` and ``-ctv``.
5. ``server_args``: ``-np 4`` becomes ``-np 1``. Embedding mode pools ONE
   sequence per request and this launcher issues its contacts strictly
   sequentially, so slots 2-4 could never be used; ``-np 1`` also gives that
   single sequence the whole ``-c`` budget instead of a quarter of it, and is
   memory-neutral (total ``n_ctx``, hence total KV cache, is unchanged). Same
   delta, same fail-closed rewrite helper, as the archived A2T launchers.
6. ``base_url``: port 8080 -> :data:`EMBEDDING_PORT` (8091). An embedding-mode
   server can never coexist with a generation-mode one
   (``rails.embedding_client.GENERATION_COEXISTENCE_NOTE``); giving it its own
   port makes an accidental overlap a bind failure rather than a silent
   mis-route, and the launcher additionally refuses to start while anything is
   still listening on the generation port
   (``rails.embedding_client.assert_no_conflicting_generation_server``).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md"
SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

PROBE_ID = "P-EMB"
EXECUTION_PROFILE = "bounded-discovery-probe"
SPLIT_ROLE = "discovery"

# Zero generation: every contact is an encode+pool with no sampling anywhere in
# the request path (rails.embedding_client module docstring: "this client
# accepts no decoding-params argument anywhere, so there is no seam through
# which a sampling parameter could leak into a request"). The D2 arm label is
# still recorded so the protocol hash names a legal arm.
D2_ARM = "fixed-legal-context"

GENERATION_PORT = 8080
EMBEDDING_PORT = 8091

# Delta 4 / delta 5: see the module docstring.
EMBEDDING_SERVER_ARGS_APPEND = ("--embedding", "--pooling", "mean")
SERVER_ARGS_NP_DELTA = ("-np", "4", "-np", "1")

# A text contact spends a CALL but meters ZERO speech audio. The durable
# attempt store's own record_usage API refuses a non-positive audio figure
# (core.attempts.errors._positive_finite), so a text contact is charged this
# documented, deliberately negligible sentinel instead: 552 of them sum to
# 5.5e-7 seconds, orders of magnitude below any reporting resolution and below
# every registered ceiling's own integer granularity. The AUDIO contacts carry
# their sample's real ``audio_seconds``, exactly as a generation flight does.
TEXT_CONTACT_AUDIO_SECONDS = 1e-9


def _run_block(
    *,
    run_key: str,
    carrier_lock_key: str,
    feat_cache_suffix: str,
    registered: Mapping[str, object],
    planned: Mapping[str, object],
) -> dict[str, object]:
    return {
        "run_key": run_key,
        "carrier_lock_key": carrier_lock_key,
        "feat_cache_suffix": feat_cache_suffix,
        "registered_ceilings": dict(registered),
        "planned_budgets": dict(planned),
    }


# Registered ceilings transcribed from the committed exposure-ledger rows
# (preregistration section 4: "Run A: <=90 embedding calls; <=400 metered
# audio-seconds; <=0.2 GPU-h. Run B: <=600 embedding calls; <=3,000 metered
# audio-seconds; <=0.5 GPU-h"). preflight.py re-reads the LIVE ledger rows and
# refuses if these disagree -- never trusted from here.
#
# planned_model_calls is the EXACT total each run issues (78 / 552; the
# machinery's own fail-closed _validate_run_summary enforces this precisely).
RUNS: dict[str, dict[str, object]] = {
    "A": _run_block(
        run_key="A",
        carrier_lock_key="slurp",
        feat_cache_suffix="slurp-q4km",
        registered={"model_calls": 90, "speech_audio_seconds": 400, "gpu_hours": 0.2},
        planned={"model_calls": 78, "speech_audio_seconds": 400, "gpu_hours": 0.2},
    ),
    "B": _run_block(
        run_key="B",
        carrier_lock_key="audio2tool",
        feat_cache_suffix="audio2tool-q4km",
        registered={"model_calls": 600, "speech_audio_seconds": 3000, "gpu_hours": 0.5},
        planned={"model_calls": 552, "speech_audio_seconds": 3000, "gpu_hours": 0.5},
    ),
}


def run_id_for(run_key: str) -> str:
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import RUN_A_ID, RUN_B_ID

    if run_key == "A":
        return RUN_A_ID
    if run_key == "B":
        return RUN_B_ID
    raise RuntimeError(f"unknown P-EMB run key {run_key!r}; known keys are 'A' and 'B'")


def split_identity_hash_for(run_key: str) -> str:
    """Run A: the machinery's own pin, cross-checked against the SAME frozen
    60-sample manifest the consumed P-SLU/P-KEY/P-TRAP probes used. Run B: the
    committed ``rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH`` (the frozen
    400 Audio2Tool discovery split), cross-checked against the machinery's own
    fail-closed Run B pin. Never a fresh derivation."""

    from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (
        SPLIT_IDENTITY_HASH as A2T_SPLIT_IDENTITY_HASH,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
        EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        EXPECTED_RUN_B_SPLIT_IDENTITY_HASH,
        assert_run_a_split_identity_hash,
        assert_run_b_split_identity_hash,
    )

    if run_key == "A":
        assert_run_a_split_identity_hash(EXPECTED_RUN_A_SPLIT_IDENTITY_HASH)
        return EXPECTED_RUN_A_SPLIT_IDENTITY_HASH
    if run_key == "B":
        if A2T_SPLIT_IDENTITY_HASH != EXPECTED_RUN_B_SPLIT_IDENTITY_HASH:
            raise RuntimeError(
                f"rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH {A2T_SPLIT_IDENTITY_HASH!r} "
                f"disagrees with rails.probes.pemb_flight's own Run B pin "
                f"{EXPECTED_RUN_B_SPLIT_IDENTITY_HASH!r} -- fail-closed"
            )
        assert_run_b_split_identity_hash(A2T_SPLIT_IDENTITY_HASH)
        return A2T_SPLIT_IDENTITY_HASH
    raise RuntimeError(f"unknown P-EMB run key {run_key!r}")


def resolve_feat_cache_dir(run_key: str) -> str:
    """The RUN's own dataset-scoped feature-cache directory, via the sanctioned
    named parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory silently, and never accepts the OTHER run's directory."""

    from speech_aware_evidence_acquisition.core.session import (
        FEAT_CACHE_DIR_DEFAULT,
        feat_cache_dir,
    )

    expected_suffix = str(RUNS[run_key]["feat_cache_suffix"])
    resolved = feat_cache_dir()
    if resolved == FEAT_CACHE_DIR_DEFAULT:
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is unset (or set to the legacy q4km directory); this campaign "
            f"must never write into the warm earnings21/22 cache ({FEAT_CACHE_DIR_DEFAULT}) -- "
            "see docs/featcache-directories.md"
        )
    if not resolved.rstrip("/").endswith(expected_suffix):
        raise RuntimeError(
            f"SAEA_FEAT_CACHE_DIR resolved to {resolved!r}; P-EMB Run {run_key} writes only to "
            f"/home/chao/feat-cache/{expected_suffix}"
        )
    return resolved


def _apply_np_delta(argv: list[str]) -> list[str]:
    """Replace the single ``-np 4`` pair with ``-np 1``. Fails closed if the
    committed fragment ever stops carrying exactly that pair, so this delta can
    never silently become a no-op (or clobber a different value). Byte-for-byte
    the archived A2T launchers' own helper."""

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


def build_values(repo: Path, run_key: str) -> dict[str, object]:
    from speech_aware_evidence_acquisition.rails.embedding_client import (
        EMBEDDING_DIM,
        EMBEDDING_ENDPOINT_PATH,
        LLAMA_MEDIA_MARKER_ENV,
        PROPS_MEDIA_MARKER_FIELD,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
        RUN_A_AUDIO_N,
        RUN_A_LABEL_N,
        RUN_A_TOTAL_N,
        RUN_B_AUDIO_N,
        RUN_B_ROW_N,
        RUN_B_TOTAL_N,
    )

    block = RUNS[run_key]
    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    values = dict(fragment)

    # Delta 1: run-own dataset-scoped feature cache.
    server_env = dict(values.get("server_env", {}))
    server_env["LLAMA_MTMD_FEAT_CACHE_DIR"] = resolve_feat_cache_dir(run_key)
    values["server_env"] = server_env

    # Delta 2: drop the batch-executor-only id_slot sentinel.
    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    # Deltas 4 + 5: embedding mode, one sequence gets the whole context.
    argv = _apply_np_delta([str(token) for token in values.get("server_args", [])])
    values["server_args"] = argv + list(EMBEDDING_SERVER_ARGS_APPEND)

    # Delta 6: the embedding tier's own port.
    values["base_url"] = f"http://127.0.0.1:{EMBEDDING_PORT}"

    if run_key == "A":
        audio_n, text_n, total_n = RUN_A_AUDIO_N, RUN_A_LABEL_N, RUN_A_TOTAL_N
        text_kind = "the 18 canonical SLURP scenario labels, bare label strings"
        split_name = "devel"
    else:
        audio_n, text_n, total_n = RUN_B_AUDIO_N, RUN_B_ROW_N, RUN_B_TOTAL_N
        text_kind = "the 152 tool registry rows, data.audio2tool.render_registry_row shipped form"
        split_name = "discovery"

    # Delta 3: probe identity, sourced only from committed machinery constants
    # and committed binding artifacts (module docstring).
    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_ID,
            "run_key": run_key,
            "stage": "2026-08-19 second-arc design order, routing-tier scheme scoreboard v1",
            "status": "REGISTERED",
            "flight_config_version": "pemb-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "carrier_lock_key": block["carrier_lock_key"],
            "split_name": split_name,
            "split_role": SPLIT_ROLE,
            "split_identity_hash": split_identity_hash_for(run_key),
            "tier": "embedding (encode+pool, ZERO generation)",
            "embedding_dim": EMBEDDING_DIM,
            "embedding_endpoint": EMBEDDING_ENDPOINT_PATH,
            "media_marker_env": LLAMA_MEDIA_MARKER_ENV,
            "media_marker_props_field": PROPS_MEDIA_MARKER_FIELD,
            "audio_contacts": audio_n,
            "text_contacts": text_n,
            "total_contacts": total_n,
            "text_contact_kind": text_kind,
            "instruct_prefix": "NONE on either side (E-0 binding decision: prefix dilution)",
            "orchestrator": (
                "rails.probes.pemb_flight.run_pemb1_flight"
                if run_key == "A"
                else "rails.probes.pemb_flight.run_pemb2_flight"
            ),
            "launcher": "scratchpad tri2/pemb/launch_pemb_flight.py (archived with the flight receipt)",
        }
    )
    if run_key == "A":
        values["sample_manifest"] = SAMPLE_MANIFEST_RELPATH
        values["roster_table"] = ROSTER_TABLE_RELPATH
    return values


def config_hash_of(values: Mapping[str, object]) -> str:
    """Byte-identical to ``core.config._canonical_hash``."""

    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


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
