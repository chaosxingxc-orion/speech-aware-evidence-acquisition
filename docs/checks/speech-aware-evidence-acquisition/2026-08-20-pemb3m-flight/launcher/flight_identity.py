"""Shared run identity for the P-EMB-3M flight launcher (exposure row
``SAEA-PROBE-pemb3m-388``).

Structurally the archived P-EMB-3L launcher's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3l-flight/
launcher/flight_identity.py``), including its documented "no committed
g0-binding flight config" difference, which applies here for the same reason:
the 2026-08-20 registration wave landed the preregistration
(``docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md``) and the
machinery (``rails.probes.pemb3m_flight`` + ``rails.local_encoder_client`` +
``rails.encode_only_check`` + ``analysis.pemb3m_read``) without one, and a
flying agent must not create one mid-session -- it would dirty the tree for the
whole flight.

THE SERVER IS NOT THE FROZEN CORE. This is the ONE structural difference from
every prior P-EMB launcher, and it is the whole point of this registration: the
q4km/Q8_0 Qwen3-Omni chat core is NEVER loaded by this flight. Two DIFFERENT
pinned GGUF models are served, one at a time, through the SAME pinned llama.cpp
binary:

  * M1 PRIMARY -- ``lco-embedding-omni-3b-gguf`` (dim 2048, audio-capable via
    its own ``mmproj`` file), E-1 Mission-B recipe verbatim
    (``docs/readiness/2026-08-20-e1-local-embedder-identity.md``):
    ``LLAMA_MEDIA_MARKER=<__media__> llama-server -m <Q8_0> --mmproj <F16>
    --embedding --pooling last -ngl 999 -c 4096``.
  * M4 CASCADE -- ``qwen3-embedding-0.6b-gguf`` (dim 1024, TEXT-ONLY, no
    mmproj), E-1 Mission-C resolution: ``--embedding --pooling last``.

Because ``core.session.start_session`` builds its ``-m``/``--mmproj`` argv from
a RUNTIME RECEIPT's ``gguf_files`` list, this module composes one
EMBEDDER runtime receipt per served model: the committed
``docs/receipts/runtime-q4km-featcache.json``'s own ``llama_cpp`` block
(the SAME pinned binary + build commit, re-hashed fail-closed at spawn time by
``start_session`` itself) plus THAT model's own ``gguf_files``. The GGUF
sha256 values are NOT hardcoded here: they are measured by the preflight stage
against the real bytes under ``$SPEECHRL_DATA_DIR`` and passed in, because the
umbrella lock carries a per-file sha256 for ``qwen3-embedding-0.6b-gguf`` ONLY
-- ``lco-embedding-omni-3b-gguf`` is a ``LOCAL_CANDIDATE``/
``UNRESOLVED_LOCAL_SOURCE`` entry with an aggregate ``size_bytes``/``files``
count and no per-file hash at all (E-1 Mission A;
``rails.probes.pemb3m_flight.resolve_model_binding``'s own docstring). Where the
lock DOES carry a hash it is cross-checked fail-closed; where it does not, this
flight's own measured hash is recorded as a self-pin and disclosed as such.

Every probe-identity value below is sourced from one of exactly three places
that are ALREADY COMMITTED at ``d0ea848``:

  * the committed machinery's own module constants
    (``rails.probes.pemb3m_flight.PROBE_ID`` / ``ARMS`` / ``ARM_IDS`` /
    ``ARM_QUERY_N`` / ``ARM_LABEL_N`` / ``ARM_TOTAL_N`` /
    ``PLANNED_TOTAL_EMBEDDING_CONTACTS`` / ``GATE_CONTACTS_MAX`` /
    ``BINDING_CONFIG_SHA256`` / ``CEILING_*`` /
    ``PKEY2_338_TRANSCRIPT_REGISTRY_SHA256`` / ``EXPECTED_SPLIT_IDENTITY_HASH``,
    plus ``rails.local_encoder_client.GLAP_EMBEDDING_DIM``/
    ``CLSP_EMBEDDING_DIM``);
  * the committed frozen binding artifacts
    (``configs/probes/g0-binding/pslu-sample-devel-n60.json`` and
    ``pslu-rosters-train-only.json`` -- the SAME P-EMB-1 surface, verbatim);
  * the committed exposure-ledger row's own registered ceilings, transcribed
    into :data:`REGISTERED_CEILINGS` and re-checked against the LIVE ledger by
    the preflight stage rather than trusted from here.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md"
E1_IDENTITY_RELPATH = "docs/readiness/2026-08-20-e1-local-embedder-identity.md"
SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

PROBE_LABEL = "P-EMB-3M"
EXECUTION_PROFILE = "bounded-discovery-probe"
SPLIT_ROLE = "discovery"
CARRIER_LOCK_KEY = "slurp"

# Zero generation anywhere in this flight: every contact is an encode+pool with
# no sampling parameter reachable in the request path (structurally proven by
# rails.encode_only_check, pre-flight gate (d)). The D2 arm label is still
# recorded so the protocol hash names a legal arm.
D2_ARM = "fixed-legal-context"

GENERATION_PORT = 8080
LCO_PORT = 8093
QWEN3_EMB_PORT = 8094

# M1 re-embeds the SAME 60 SLURP devel clips the consumed P-SLU/P-KEY/P-TRAP and
# P-EMB-1/3L flights already warmed -- but through a DIFFERENT audio encoder
# (LCO-3B's own qwen2.5o projector, not q4km's). docs/featcache-directories.md's
# <dataset>-<encoder> rule therefore gives it its OWN directory: a q4km-warmed
# feature can never be replayed for an LCO encode, and this flight can never
# write into the warm q4km or slurp-q4km caches.
FEAT_CACHE_SUFFIX = "slurp-lco3b"

# A TEXT contact spends a CALL but meters ZERO speech audio. The durable attempt
# store's record_usage API refuses a non-positive audio figure
# (core.attempts.errors._positive_finite), so a text contact is charged this
# documented, deliberately negligible sentinel instead: the 72 text contacts
# across all four arms sum to 7.2e-8 seconds, orders of magnitude below any
# reporting resolution and below every registered ceiling's integer granularity.
# Reused verbatim from the archived P-EMB-3L launcher.
TEXT_CONTACT_AUDIO_SECONDS = 1e-9

# Registered ceilings transcribed from the committed exposure-ledger row
# (preregistration section 5: "<=440 calls; <=900 metered audio-seconds; <=0.5
# GPU-h"). The preflight stage re-reads the LIVE ledger row AND the committed
# machinery's own CEILING_* constants and refuses if any of the three sources
# disagree -- never trusted from here alone.
REGISTERED_CEILINGS: dict[str, object] = {
    "model_calls": 440,
    "speech_audio_seconds": 900,
    "gpu_hours": 0.5,
}

# planned_model_calls is the registration's own WORST CASE (312 scored + 66
# CASCADE-T0 contingency + 10 gate contacts = 388, the exposure row's own name),
# not this attempt's intended spend. The CASCADE-T0 supplement is not expected to
# fly (pre-flight gate (c) is pre-verified COMPLETE), so the intended spend is
# 312 scored + 9 gate = 321; both figures are recorded in the flight receipt and
# the durable attempt store carries the ACTUAL. Declaring the registered worst
# case keeps the plan's ceiling honest under one-shot attempt semantics: a
# resumed successor attempt charges its own spend against the SAME plan ceiling.
PLANNED_BUDGETS: dict[str, object] = {
    "model_calls": 388,
    "speech_audio_seconds": 900,
    "gpu_hours": 0.5,
}

# ---------------------------------------------------------------------------
# Gate-contact budget (registration section 3 + the 2026-08-20 coordinator
# amendment extending gate (b) to the controls' AUDIO path).
#
# rails.probes.pemb3m_flight.GATE_CONTACTS_MAX is 10 and its own module
# docstring accounts for three families (pooling-differ + control sanity + M4
# repeat-call determinism). This flight spends NINE, adding the amendment's two
# control AUDIO-path sanity contacts and one LCO repeat-call determinism contact
# that the machinery's own accounting left slack for:
#
#   1  pooling-differ, --pooling mean boot, synthetic non-corpus WAV
#   1  pooling-differ, --pooling last boot, SAME synthetic WAV  (byte-compared)
#   1  LCO repeat-call determinism, SAME synthetic WAV, SAME last boot
#      (pairs with the line above -> registration section 6's "repeat-call
#      determinism sample per server session", on the AUDIO path that M1
#      actually scores, at zero corpus-audio cost)
#   2  control TEXT sanity   (GLAP, CLSP) -- gate (b) as shipped
#   2  control AUDIO sanity  (GLAP, CLSP) -- the coordinator amendment
#   2  M4 repeat-call determinism pair (qwen3-emb, text; E-1 Mission C)
#
# The --pooling mean gate boot carries no separate determinism pair of its own:
# it exists solely to produce the one vector the byte-compare needs, and the ten-
# contact allowance is fully committed above. M2/M3 are in-process transformers
# with no server session at all, so section 6's per-server-session rule does not
# reach them. Both facts are disclosed in the flight receipt.
# ---------------------------------------------------------------------------
GATE_CONTACT_PLAN: dict[str, int] = {
    "pooling_differ_mean": 1,
    "pooling_differ_last": 1,
    "lco_repeat_call_determinism": 1,
    "control_text_sanity": 2,
    "control_audio_sanity": 2,
    "m4_repeat_call_determinism": 2,
}
PLANNED_GATE_CONTACTS = sum(GATE_CONTACT_PLAN.values())  # 9

# The synthetic, NON-CORPUS gate clip (E-1 used the same shape: "one synthetic
# 2 s sine WAV ... no dataset audio, no gold"). Generated byte-deterministically
# by build_gate_wav_bytes below from the stdlib alone -- ffmpeg is a pinned
# ABSENCE on this host and is never installed; nothing here decodes or resamples.
GATE_WAV_SAMPLE_RATE = 16000
GATE_WAV_SECONDS = 2.0
GATE_WAV_FREQ_HZ = 440.0
GATE_WAV_AMPLITUDE = 0.5


def build_gate_wav_bytes() -> bytes:
    """A 2 s, 16 kHz, mono, 16-bit PCM 440 Hz sine as a complete WAV container.

    Pure stdlib (``wave`` + ``struct`` + ``math``), so the bytes are identical
    on every host and no decoder, resampler or ffmpeg is involved. This clip is
    SYNTHETIC and NON-CORPUS: it carries no SLURP audio, no speaker, no
    linguistic content and no gold, so spending it on the pooling-differ gate,
    the LCO determinism pair and the two control AUDIO-path sanity contacts adds
    zero corpus exposure. Its own sha256 is pinned into the flight receipt."""

    import io
    import math
    import struct
    import wave

    n = int(GATE_WAV_SAMPLE_RATE * GATE_WAV_SECONDS)
    frames = bytearray()
    for i in range(n):
        value = GATE_WAV_AMPLITUDE * math.sin(2.0 * math.pi * GATE_WAV_FREQ_HZ * i / GATE_WAV_SAMPLE_RATE)
        frames += struct.pack("<h", int(round(value * 32767.0)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(GATE_WAV_SAMPLE_RATE)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# The two served embedder models.
# ---------------------------------------------------------------------------

LCO_LOCAL_SUBDIR = "models/lco-embedding-omni-3b-gguf"
LCO_PRIMARY_FILENAME = "LCO-Embedding-Omni-3B-Q8_0.gguf"
LCO_MMPROJ_FILENAME = "mmproj-LCO-Embedding-Omni-3b-F16.gguf"

QWEN3_EMB_LOCAL_SUBDIR = "models/qwen3-embedding-0.6b-gguf"
QWEN3_EMB_PRIMARY_FILENAME = "Qwen3-Embedding-0.6B-Q8_0.gguf"

# E-1 Mission B's recipe plus the batch-geometry amendment forced by a LIVE
# refusal on this host (attempt-20260820T110419Z-d6c576, 11:23:39Z). E-1's own
# verification ran ``-ngl 0 --no-mmproj-offload`` on CPU because the GPU was
# campaign-occupied, and never exercised an AUDIO contact under llama.cpp's own
# embedding-mode batch clamp. On GPU the server logs, at boot:
#
#   embeddings enabled with n_batch (2048) > n_ubatch (512)
#   setting n_batch = n_ubatch = 512 to avoid assertion failure
#
# and then refuses every audio contact:
#
#   input (1502 tokens) is too large to process.
#   increase the physical batch size (current batch size: 512)
#
# A pooled embedding needs the WHOLE sequence in ONE physical batch, and LCO's
# qwen2.5o whisper-style projector pads any clip to a ~30 s chunk -- ~1500 audio
# tokens regardless of how short the utterance is (the frozen 60 are ~3 s each).
# So ``-b``/``-ub`` are raised to the context size, 4096, which is >2.7x the
# observed token count and leaves room for the marker/prompt tokens beside it.
# ``-np 1`` follows the P-EMB-3L launcher's own delta-5 rationale: embedding mode
# pools ONE sequence per request and this launcher issues contacts strictly
# sequentially, so llama.cpp's ``n_parallel = auto`` -> 4 slots would only split
# the context and the VRAM four ways for slots that can never be used.
LCO_COMMON_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "-ngl", "999", "-c", "4096", "-b", "4096", "-ub", "4096", "-np", "1",
)
# E-1 Mission C: text-only, no mmproj, dim 1024. The same batch geometry is
# applied for the same structural reason (one pooled sequence per request must
# fit in one physical batch) even though the 60 T0 transcripts and 18 labels are
# far shorter than the clamp -- a text contact must never be able to trip the
# exact refusal that stopped the audio side.
QWEN3_EMB_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "999", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1",
)

LCO_SESSION_KEYS: tuple[str, ...] = ("mean", "last")


def lco_session_args(pooling_mode: str) -> list[str]:
    if pooling_mode not in LCO_SESSION_KEYS:
        raise ValueError(f"unknown LCO pooling mode {pooling_mode!r}, expected one of {LCO_SESSION_KEYS}")
    return [*LCO_COMMON_SERVER_ARGS, "--pooling", pooling_mode]


def lco_gguf_relpaths() -> tuple[str, str]:
    return (
        f"{LCO_LOCAL_SUBDIR}/{LCO_PRIMARY_FILENAME}",
        f"{LCO_LOCAL_SUBDIR}/{LCO_MMPROJ_FILENAME}",
    )


def qwen3_emb_gguf_relpaths() -> tuple[str, ...]:
    return (f"{QWEN3_EMB_LOCAL_SUBDIR}/{QWEN3_EMB_PRIMARY_FILENAME}",)


def embedder_runtime_receipt(
    committed_runtime_receipt: Mapping[str, object],
    *,
    gguf_relpaths: Sequence[str],
    sha256_by_relpath: Mapping[str, str],
) -> dict[str, object]:
    """One served embedder's own runtime receipt: the committed receipt's
    ``llama_cpp`` block VERBATIM (same pinned binary path + sha256 + build
    commit, which ``core.session.start_session`` re-hashes fail-closed against
    the real file before it spawns anything) plus THIS model's own
    ``gguf_files``.

    Never mutates the committed document, never invents a hash: every entry's
    sha256 comes from ``sha256_by_relpath``, which the preflight stage measured
    against the real bytes under the data root (module docstring)."""

    llama_cpp = committed_runtime_receipt.get("llama_cpp")
    if not isinstance(llama_cpp, Mapping):
        raise RuntimeError("committed runtime receipt lacks a llama_cpp mapping")
    files = []
    for relpath in gguf_relpaths:
        sha256 = sha256_by_relpath.get(relpath)
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise RuntimeError(f"no measured sha256 for {relpath!r}; refusing to spawn (fail-closed)")
        files.append({"path": relpath, "sha256": sha256})
    return {"llama_cpp": dict(llama_cpp), "gguf_files": files}


# ---------------------------------------------------------------------------
# Identity helpers.
# ---------------------------------------------------------------------------


def run_id() -> str:
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import PROBE_ID

    return PROBE_ID


def split_identity_hash() -> str:
    """The machinery's own pin, cross-checked against the SAME frozen 60-sample
    manifest the consumed P-SLU/P-KEY/P-TRAP/P-EMB probes used. Never a fresh
    derivation -- ``rails.probes.pemb3m_flight`` re-exports
    ``pemb_flight.EXPECTED_RUN_A_SPLIT_IDENTITY_HASH`` verbatim and this function
    runs the parent's own fail-closed assertion on it."""

    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (
        EXPECTED_SPLIT_IDENTITY_HASH,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
        assert_run_a_split_identity_hash,
    )

    assert_run_a_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)
    return EXPECTED_SPLIT_IDENTITY_HASH


def resolve_feat_cache_dir() -> str:
    """M1's dataset+encoder-scoped feature-cache directory, via the sanctioned
    named parameter (``SAEA_FEAT_CACHE_DIR``). Never returns the legacy q4km
    directory, and never the q4km-warmed slurp-q4km one either: a q4km audio
    feature must never be replayed for an LCO encode."""

    from speech_aware_evidence_acquisition.core.session import (
        FEAT_CACHE_DIR_DEFAULT,
        feat_cache_dir,
    )

    resolved = feat_cache_dir()
    if resolved == FEAT_CACHE_DIR_DEFAULT:
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is unset (or set to the legacy q4km directory); this flight "
            f"must never write into the warm earnings21/22 cache ({FEAT_CACHE_DIR_DEFAULT}) -- "
            "see docs/featcache-directories.md"
        )
    if not resolved.rstrip("/").endswith(FEAT_CACHE_SUFFIX):
        raise RuntimeError(
            f"SAEA_FEAT_CACHE_DIR resolved to {resolved!r}; P-EMB-3M's M1 arm writes only to "
            f"/home/chao/feat-cache/{FEAT_CACHE_SUFFIX} (a DIFFERENT audio encoder from every "
            "q4km-warmed cache on this host)"
        )
    return resolved


def build_values(repo: Path, lock: Mapping[str, object], sha256_by_relpath: Mapping[str, str]) -> dict[str, object]:
    """This run's full config-values document -- the input to ``config_hash_of``
    and therefore to the protocol hash the ExecutionPlan carries.

    Starts from the COMMITTED model fragment ``configs/model/q4km-featcache.json``
    ONLY for the transport/timeout shape it establishes, then replaces every
    model-identity field, because this flight serves two DIFFERENT models and
    never the frozen core (module docstring). The frozen core's own decoding
    params are dropped entirely rather than carried: there is no generation in
    this flight and the embedding client accepts no decoding-params argument
    anywhere, so carrying a sampling block would misdescribe the protocol."""

    from speech_aware_evidence_acquisition.rails.embedding_client import (
        EMBEDDING_ENDPOINT_PATH,
        LLAMA_MEDIA_MARKER_ENV,
        PROPS_MEDIA_MARKER_FIELD,
    )
    from speech_aware_evidence_acquisition.rails.local_encoder_client import (
        CLSP_EMBEDDING_DIM,
        GLAP_EMBEDDING_DIM,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (
        ARM_LABEL_N,
        ARM_QUERY_N,
        ARM_TOTAL_N,
        ARMS,
        BINDING_CONFIG_SCHEMA,
        BINDING_CONFIG_SHA256,
        CASCADE_T0_SUPPLEMENT_MAX_CONTACTS,
        GATE_CONTACTS_MAX,
        PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH,
        PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
        PLANNED_TOTAL_EMBEDDING_CONTACTS,
        assert_binding_config_sha256,
        binding_config_sha256,
        resolve_model_binding,
    )

    # Fail-closed BEFORE any value is composed: the live arm table's own digest
    # must equal the pinned one, so the four model bindings this config hash is
    # about to record can never have drifted -- including the umbrella lock's own
    # content for those four keys, which this digest also commits to.
    assert_binding_config_sha256(lock)

    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    values: dict[str, object] = {
        "transport": str(fragment["transport"]),
        "timeout_seconds": float(fragment["timeout_seconds"]),
        "runtime_receipt": RUNTIME_RECEIPT_RELPATH,
        "model_fragment_source": MODEL_FRAGMENT_RELPATH,
        "model_fragment_carried_fields": ["transport", "timeout_seconds"],
        "frozen_core_loaded": False,
        "frozen_core_note": (
            "the q4km/Q8_0 Qwen3-Omni chat core is NEVER loaded by this flight; only its "
            "pinned llama.cpp binary is reused, to serve two different embedder GGUFs"
        ),
        "decoding_params": {},
        "decoding_params_note": (
            "empty by construction: zero generation, and rails.embedding_client accepts no "
            "decoding-params argument anywhere in its request path (rails.encode_only_check "
            "guard 4 proves no sampling key is reachable)"
        ),
    }

    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_LABEL,
            "stage": (
                "2026-08-20 owner approval of the embedder-charter adjudication section 3 design, "
                "triggered by the P-EMB-3L LOCAL-EXHAUSTED verdict"
            ),
            "status": "REGISTERED",
            "flight_config_version": "pemb3m-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "e1_identity_record": E1_IDENTITY_RELPATH,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "split_name": "devel",
            "split_role": SPLIT_ROLE,
            "split_identity_hash": split_identity_hash(),
            "sample_manifest": SAMPLE_MANIFEST_RELPATH,
            "roster_table": ROSTER_TABLE_RELPATH,
            "tier": "embedding (encode+pool, ZERO generation, zero sampling seam)",
            "embedding_endpoint": EMBEDDING_ENDPOINT_PATH,
            "media_marker_env": LLAMA_MEDIA_MARKER_ENV,
            "media_marker_props_field": PROPS_MEDIA_MARKER_FIELD,
            "binding_config_schema": BINDING_CONFIG_SCHEMA,
            "binding_config_sha256": BINDING_CONFIG_SHA256,
            "binding_config_sha256_recomputed": binding_config_sha256(lock),
            "prefixes": {"audio_prefix": "", "text_prefix": ""},
            "prefix_note": (
                "bare content on both sides, per the preregistration's own opening paragraph and "
                "the P-EMB-1 precedent -- in explicit contrast to P-EMB-3L's refuted instruct-prefix arms"
            ),
            "arms": [
                {
                    "arm_id": arm.arm_id,
                    "model_lock_key": arm.model_lock_key,
                    "embedding_dim": arm.embedding_dim,
                    "uses_audio": arm.uses_audio,
                    "kind": arm.kind,
                    "model_binding": resolve_model_binding(lock, arm.model_lock_key),
                }
                for arm in ARMS
            ],
            "glap_embedding_dim": GLAP_EMBEDDING_DIM,
            "clsp_embedding_dim": CLSP_EMBEDDING_DIM,
            "query_contacts_per_arm": ARM_QUERY_N,
            "label_contacts_per_arm": ARM_LABEL_N,
            "contacts_per_arm": ARM_TOTAL_N,
            "planned_scored_contacts": PLANNED_TOTAL_EMBEDDING_CONTACTS,
            "planned_gate_contacts": PLANNED_GATE_CONTACTS,
            "gate_contacts_max": GATE_CONTACTS_MAX,
            "gate_contact_plan": dict(GATE_CONTACT_PLAN),
            "cascade_t0_supplement_max_contacts": CASCADE_T0_SUPPLEMENT_MAX_CONTACTS,
            "cascade_t0_supplement_expected": False,
            "t0_transcript_registry_relpath": PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH,
            "t0_transcript_registry_sha256": PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
            "label_contact_kind": "the 18 canonical SLURP scenario labels, bare, every arm",
            "servers": [
                {
                    "server_key": f"lco-{key}",
                    "model_lock_key": "lco-embedding-omni-3b-gguf",
                    "port": LCO_PORT,
                    "pooling_mode": key,
                    "server_args": lco_session_args(key),
                    "gguf_files": [
                        {"path": rel, "sha256": sha256_by_relpath.get(rel)} for rel in lco_gguf_relpaths()
                    ],
                    "server_env": {
                        "LLAMA_MTMD_FEAT_CACHE_DIR": resolve_feat_cache_dir(),
                        "LLAMA_MEDIA_MARKER": "<__media__>",
                    },
                    "recipe_source": f"{E1_IDENTITY_RELPATH} Mission B",
                }
                for key in LCO_SESSION_KEYS
            ]
            + [
                {
                    "server_key": "qwen3-emb",
                    "model_lock_key": "qwen3-embedding-0.6b-gguf",
                    "port": QWEN3_EMB_PORT,
                    "pooling_mode": "last",
                    "server_args": list(QWEN3_EMB_SERVER_ARGS),
                    "gguf_files": [
                        {"path": rel, "sha256": sha256_by_relpath.get(rel)} for rel in qwen3_emb_gguf_relpaths()
                    ],
                    "server_env": {},
                    "recipe_source": f"{E1_IDENTITY_RELPATH} Mission C",
                }
            ],
            "gate_wav": {
                "synthetic": True,
                "corpus_audio": False,
                "sample_rate": GATE_WAV_SAMPLE_RATE,
                "seconds": GATE_WAV_SECONDS,
                "freq_hz": GATE_WAV_FREQ_HZ,
                "amplitude": GATE_WAV_AMPLITUDE,
                "sha256": hashlib.sha256(build_gate_wav_bytes()).hexdigest(),
            },
            "orchestrator": "rails.probes.pemb3m_flight (run_m1_arm_flight / run_local_encoder_arm_flight / run_m4_arm_flight)",
            "launcher": "scratchpad pemb3m/launch_pemb3m_flight.py (archived with the flight receipt)",
        }
    )
    return values


def config_hash_of(values: Mapping[str, object]) -> str:
    """Byte-identical to ``core.config._canonical_hash``."""

    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
