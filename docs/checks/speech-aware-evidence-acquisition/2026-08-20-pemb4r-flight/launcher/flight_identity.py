"""Shared run identity for the P-EMB-4R flight launcher (exposure row
``SAEA-PROBE-pemb4r-4100``).

Structurally the archived P-EMB-3M launcher's own ``flight_identity.py``
(``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-flight/
launcher/flight_identity.py``), including its documented "no committed
g0-binding flight config" difference, which applies here for the same reason:
the 2026-08-20 registration wave landed the preregistration
(``docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md``) and the
machinery (``rails.probes.pemb4r_flight`` + ``analysis.pemb4r_read``) without
one, and a flying agent must not create one mid-session -- it would dirty the
tree for the whole flight.

FOUR EMBEDDER MODELS, ONE FROZEN CORE. Three embedder GGUFs are served, one at
a time, through the SAME pinned llama.cpp binary (per-model runtime receipts,
:func:`embedder_runtime_receipt`); GLAP runs in-process through transformers;
and -- unlike every prior P-EMB flight -- the pinned q4km Qwen3-Omni core IS
loaded, once, at the very end, for C-DECODE's 60 generation calls.

  * LCO-3B  ``lco-embedding-omni-3b-gguf``  dim 2048 (proven, P-EMB-3M M1)
  * LCO-7B  ``lco-embedding-omni-7b-gguf``  dim MEASURED at gate time; its own
    GGUF metadata declares ``qwen2vl.embedding_length = 3584``, read OFFLINE
    from the file header in the preflight stage (model-free, no server) purely
    so the pinned ``rails.embedding_client.EmbeddingClient`` can be constructed
    with a correct ``expected_dim``. The gate's own verdict still comes from a
    LIVE sanity embed's returned vector (``run_lco7_server_sanity_gate``'s
    ``measured_dim``): a disagreement between the declared and the served dim
    refuses through the client and lands as DROPPED-LCO7, disclosed.
  * QW      ``qwen3-embedding-0.6b-gguf``   dim 1024, TEXT-ONLY, no mmproj
  * GLAP    ``glap``                        dim 1024, in-process transformers
  * CORE    ``qwen3-omni-30b-a3b-instruct-gguf-q4km``  C-DECODE generation only

FEATURE CACHE, PER ENCODER. Cache entries are mmproj-encoder-specific
(``docs/featcache-directories.md``), and this flight runs TWO different audio
encoders over the SAME 60 clips, so each gets its own ``<dataset>-<encoder>``
directory: ``slurp-lco3b`` (already warm -- P-EMB-3M's own M1 arm encoded these
exact 60 clips through this exact encoder) and ``slurp-lco7b`` (cold). The
q4km core's C-DECODE session uses ``slurp-q4km``, the SAME directory the
consumed P-SLU/P-KEY/P-TRAP/P-FEW/P-CORR-F flights warmed over these SAME 60
samples. No process-wide ``SAEA_FEAT_CACHE_DIR`` is honored at all: the
launcher refuses to start if one is set, and each session is handed its own
``LLAMA_MTMD_FEAT_CACHE_DIR`` explicitly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

MODEL_FRAGMENT_RELPATH = "configs/model/q4km-featcache.json"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-featcache.json"
PREREGISTRATION_RELPATH = "docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md"
E1_IDENTITY_RELPATH = "docs/readiness/2026-08-20-e1-local-embedder-identity.md"
SAMPLE_MANIFEST_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

PROBE_LABEL = "P-EMB-4R"
EXECUTION_PROFILE = "bounded-discovery-probe"

# Coordinator ruling issued 2026-08-20, BEFORE any C-DECODE contact was made
# (the flight was mid-``lco7`` stage; zero generation contacts had been spent).
# Recorded VERBATIM, at the coordinator's instruction, so the flight receipt is
# the flight-side record that the ruling preceded the contacts. The coordinator
# lands the matching registration amendment pre-read if the fallback triggers.
COORDINATOR_PRE_CONTACT_RULING = (
    "Coordinator pre-contact ruling 2026-08-20: if budget_forced fires, the registration's "
    "C-DECODE HELPS/HURTS clauses are NOT evaluable at the read (modality confound against the "
    "audio-modality FS-NONE comparator); C-DECODE then reports descriptively only. If the winner "
    "is a text arm, clauses evaluate as registered."
)
COORDINATOR_PRE_CONTACT_RULING_KEY = "coordinator_pre_contact_ruling"
SPLIT_ROLE = "discovery"
CARRIER_LOCK_KEY = "slurp"

# The one D2 arm rails.core_client.FrozenCoreClient builds payloads for; also
# the arm label recorded in the config so the protocol hash names a legal arm.
D2_ARM = "fixed-legal-context"

GENERATION_PORT = 8080
LCO3_PORT = 8093
QW_PORT = 8094
LCO7_PORT = 8095

# A TEXT contact spends a CALL but meters ZERO speech audio. The durable
# attempt store's record_usage API refuses a non-positive audio figure
# (core.attempts.errors._positive_finite), so a text contact is charged this
# documented, deliberately negligible sentinel instead: the 3,840 text contacts
# across this whole flight sum to 3.84e-6 seconds, orders of magnitude below any
# reporting resolution and below every registered ceiling's integer
# granularity. Reused verbatim from the archived P-EMB-3L/3M launchers.
TEXT_CONTACT_AUDIO_SECONDS = 1e-9

# Registered ceilings transcribed from the committed exposure-ledger row
# (registration section 5: "<=4,500 calls; <=700 metered audio-seconds
# (3x182.26 planned); <=0.5 GPU-h"). The preflight stage re-reads the LIVE
# ledger row AND the committed machinery's own CEILING_* constants and refuses
# if any of the three sources disagree -- never trusted from here alone.
REGISTERED_CEILINGS: dict[str, object] = {
    "model_calls": 4500,
    "speech_audio_seconds": 700,
    "gpu_hours": 0.5,
}

# planned_model_calls is the registration's own plan (4,100 = 3,600 bank + 180
# audio queries + 240 text queries + 60 C-DECODE + <=20 gate contacts), the
# exposure row's own name.
#
# planned_speech_audio_seconds is declared at the REGISTERED CEILING (700), not
# at the machinery's own 547 default. Reason, recorded for audit: 547 is exactly
# three metered audio passes (3 x 182.26 = 546.78) and admits no fourth. Whether
# C-DECODE needs a fourth pass is not knowable until the retrieval winner is
# resolved -- and the winner is resolved by a GOLD-FREE proxy that this launcher
# must not pre-empt. Declaring the registered ceiling lets the fourth pass be
# decided on MEASURED remaining budget at C-DECODE entry (see
# ``c_decode_modality_decision`` in the launcher) instead of being foreclosed by
# a plan number, while the ceiling itself still refuses fail-closed. It never
# authorizes more than the registration already did: 700 IS the registered cell.
PLANNED_BUDGETS: dict[str, object] = {
    "model_calls": 4100,
    "speech_audio_seconds": 700,
    "gpu_hours": 0.5,
}

# ---------------------------------------------------------------------------
# Gate-contact budget (registration section 3; machinery GATE_CONTACTS_MAX=20).
#
#   1  LCO-7B server sanity            (text, gate (a); measures the served dim)
#   2  POOLING-DIFFER LCO-3B           (audio, synthetic non-corpus WAV, 2 boots)
#   1  LCO-3B repeat-call determinism  (audio, SAME WAV, SAME 'last' boot)
#   2  POOLING-DIFFER LCO-7B           (audio, synthetic WAV, 2 boots)
#   1  LCO-7B repeat-call determinism  (audio, SAME WAV, SAME 'last' boot)
#   1  GLAP text sanity                (gate (b), P-EMB-3M pattern)
#   1  GLAP audio sanity               (gate (b) AMENDMENT, synthetic WAV)
#   2  QW repeat-call determinism pair (text; E-1 Mission C: qwen3-emb is not
#                                       bit-exact across identical GPU calls)
#   1  C-DECODE determinism RESEND     (generation; the P-CORR-F resend-
#                                       divergence finding -- 6/20 identical-
#                                       prompt pairs diverged at -np 4 -- makes
#                                       the generation server's own parallelism
#                                       setting load-bearing, so one identical-
#                                       prompt resend is flown and recorded)
#  --
#  12  total, <= 20
#
# GLAP is in-process with no server session at all, so registration section 6's
# per-server-session determinism rule does not reach it (the P-EMB-3M
# precedent's own disclosure, carried). The two LCO 'mean' gate boots carry no
# determinism pair of their own: they exist solely to produce the one vector
# each byte-compare needs.
# ---------------------------------------------------------------------------
GATE_CONTACT_PLAN: dict[str, int] = {
    "lco7_server_sanity": 1,
    "pooling_differ_lco3": 2,
    "lco3_repeat_call_determinism": 1,
    "pooling_differ_lco7": 2,
    "lco7_repeat_call_determinism": 1,
    "glap_text_sanity": 1,
    "glap_audio_sanity": 1,
    "qw_repeat_call_determinism": 2,
    "c_decode_determinism_resend": 1,
}
PLANNED_GATE_CONTACTS = sum(GATE_CONTACT_PLAN.values())  # 12

# The synthetic, NON-CORPUS gate clip -- byte-identical to the archived
# P-EMB-3M launcher's own (stdlib only; ffmpeg is a PINNED ABSENCE on this host
# and is never installed, and nothing here decodes or resamples).
GATE_WAV_SAMPLE_RATE = 16000
GATE_WAV_SECONDS = 2.0
GATE_WAV_FREQ_HZ = 440.0
GATE_WAV_AMPLITUDE = 0.5


def build_gate_wav_bytes() -> bytes:
    """A 2 s, 16 kHz, mono, 16-bit PCM 440 Hz sine as a complete WAV container.

    SYNTHETIC and NON-CORPUS: no SLURP audio, no speaker, no linguistic content
    and no gold, so spending it on the two pooling-differ gates, the two LCO
    determinism pairs and the GLAP audio-path sanity contact adds zero corpus
    exposure. Its own sha256 is pinned into the flight receipt."""

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
# The served models.
# ---------------------------------------------------------------------------

LCO3_SUBDIR = "models/lco-embedding-omni-3b-gguf"
LCO3_PRIMARY = "LCO-Embedding-Omni-3B-Q8_0.gguf"
LCO3_MMPROJ = "mmproj-LCO-Embedding-Omni-3b-F16.gguf"

LCO7_SUBDIR = "models/lco-embedding-omni-7b-gguf"
LCO7_PRIMARY = "LCO-Embedding-Omni-7B-Q8_0.gguf"
LCO7_MMPROJ = "mmproj-LCO-Embedding-Omni-7b-F16.gguf"

QW_SUBDIR = "models/qwen3-embedding-0.6b-gguf"
QW_PRIMARY = "Qwen3-Embedding-0.6B-Q8_0.gguf"

GLAP_SUBDIR = "models/glap"
GLAP_WEIGHTS = "model.safetensors"

# E-1 Mission B's recipe plus the batch-geometry amendment the P-EMB-3M flight
# established LIVE on this host: a pooled embedding needs the WHOLE sequence in
# ONE physical batch, and LCO's qwen2.5o whisper-style projector pads any clip
# to a ~30 s chunk (~1500 audio tokens) regardless of utterance length, so
# ``-b``/``-ub`` are raised to the context size. ``-np 1``: embedding mode pools
# ONE sequence per request and this launcher issues contacts strictly
# sequentially, so extra slots would only split the context and the VRAM.
LCO_COMMON_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "-ngl", "999", "-c", "4096", "-b", "4096", "-ub", "4096", "-np", "1",
)
QW_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "999", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1",
)

POOLING_MODES: tuple[str, ...] = ("mean", "last")

FEAT_CACHE_ROOT = "/home/chao/feat-cache"
FEAT_CACHE_BY_MODEL: dict[str, str] = {
    "lco3": f"{FEAT_CACHE_ROOT}/slurp-lco3b",
    "lco7": f"{FEAT_CACHE_ROOT}/slurp-lco7b",
}
CORE_FEAT_CACHE_DIR = f"{FEAT_CACHE_ROOT}/slurp-q4km"

SERVER_PORT_BY_MODEL: dict[str, int] = {"lco3": LCO3_PORT, "lco7": LCO7_PORT, "qw": QW_PORT}


def lco_session_args(pooling_mode: str) -> list[str]:
    if pooling_mode not in POOLING_MODES:
        raise ValueError(f"unknown LCO pooling mode {pooling_mode!r}, expected one of {POOLING_MODES}")
    return [*LCO_COMMON_SERVER_ARGS, "--pooling", pooling_mode]


def gguf_relpaths(model: str) -> tuple[str, ...]:
    if model == "lco3":
        return (f"{LCO3_SUBDIR}/{LCO3_PRIMARY}", f"{LCO3_SUBDIR}/{LCO3_MMPROJ}")
    if model == "lco7":
        return (f"{LCO7_SUBDIR}/{LCO7_PRIMARY}", f"{LCO7_SUBDIR}/{LCO7_MMPROJ}")
    if model == "qw":
        return (f"{QW_SUBDIR}/{QW_PRIMARY}",)
    raise ValueError(f"gguf_relpaths: {model!r} is not a served GGUF model")


def all_hashed_relpaths() -> tuple[str, ...]:
    """Every embedder byte this flight will actually serve, plus GLAP's own
    weight file. The umbrella lock carries a per-file sha256 for
    ``qwen3-embedding-0.6b-gguf`` ONLY -- lco-3b / lco-7b / glap are all
    ``LOCAL_CANDIDATE`` entries with an aggregate ``size_bytes``/``files``
    count and no per-file hash at all -- so where the lock DOES carry a hash it
    is cross-checked fail-closed, and where it does not, this flight's own
    measured hash is recorded as a self-pin and disclosed as such. The q4km
    core is deliberately NOT in this list: its GGUF set is attested by
    ``contracts.FrozenCoreGate._validate_runtime``, which the C-DECODE stage
    runs explicitly BEFORE it spawns anything (the P-CORR-F section-8 forward
    rule)."""

    return (
        *gguf_relpaths("lco3"),
        *gguf_relpaths("lco7"),
        *gguf_relpaths("qw"),
        f"{GLAP_SUBDIR}/{GLAP_WEIGHTS}",
    )


def embedder_runtime_receipt(
    committed_runtime_receipt: Mapping[str, object],
    *,
    gguf_relpaths_: Sequence[str],
    sha256_by_relpath: Mapping[str, str],
) -> dict[str, object]:
    """One served embedder's own runtime receipt: the committed receipt's
    ``llama_cpp`` block VERBATIM (same pinned binary path + sha256 + build
    commit, which ``core.session.start_session`` re-hashes fail-closed against
    the real file before it spawns anything) plus THIS model's own
    ``gguf_files``. Never mutates the committed document, never invents a
    hash."""

    llama_cpp = committed_runtime_receipt.get("llama_cpp")
    if not isinstance(llama_cpp, Mapping):
        raise RuntimeError("committed runtime receipt lacks a llama_cpp mapping")
    files = []
    for relpath in gguf_relpaths_:
        sha256 = sha256_by_relpath.get(relpath)
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise RuntimeError(f"no measured sha256 for {relpath!r}; refusing to spawn (fail-closed)")
        files.append({"path": relpath, "sha256": sha256})
    return {"llama_cpp": dict(llama_cpp), "gguf_files": files}


# ---------------------------------------------------------------------------
# Identity helpers.
# ---------------------------------------------------------------------------


def run_id() -> str:
    from speech_aware_evidence_acquisition.rails.probes.pemb4r_flight import PROBE_ID

    return PROBE_ID


def split_identity_hash() -> str:
    """The machinery's own pin, cross-checked against the SAME frozen 60-sample
    manifest the consumed P-SLU/P-KEY/P-TRAP/P-EMB/P-FEW probes used."""

    from speech_aware_evidence_acquisition.rails.probes.pemb4r_flight import EXPECTED_SPLIT_IDENTITY_HASH
    from speech_aware_evidence_acquisition.rails.probes.pemb_flight import assert_run_a_split_identity_hash

    assert_run_a_split_identity_hash(EXPECTED_SPLIT_IDENTITY_HASH)
    return EXPECTED_SPLIT_IDENTITY_HASH


def gguf_declared_embedding_length(path: Path) -> int:
    """OFFLINE, model-free: the GGUF header's own ``<arch>.embedding_length``.

    Read only so the pinned ``EmbeddingClient`` can be constructed with a
    correct ``expected_dim`` for a model this codebase has no proven-dim probe
    for (LCO-7B). Never substitutes for the LIVE gate measurement: gate (a)
    still reports the dim the SERVER actually returned, and a disagreement
    refuses through the client's own fail-closed dim check."""

    from gguf import GGUFReader

    reader = GGUFReader(str(path))
    for name, field in reader.fields.items():
        if name.endswith(".embedding_length"):
            return int(field.parts[field.data[0]][0])
    raise RuntimeError(f"{path}: no <arch>.embedding_length key in the GGUF metadata")


def build_values(
    repo: Path,
    lock: Mapping[str, object],
    sha256_by_relpath: Mapping[str, str],
    declared_dims: Mapping[str, int],
) -> dict[str, object]:
    """This run's full config-values document -- the input to
    :func:`config_hash_of` and therefore to the protocol hash the ExecutionPlan
    carries.

    Starts from the COMMITTED model fragment ``configs/model/q4km-featcache.json``
    and keeps its transport/timeout/server_args/decoding_params for the C-DECODE
    generation session (which really does serve that exact frozen core), then
    ADDS the four embedder-model blocks this flight also serves. Two documented
    deltas from the fragment, both the established precedent:

      1. ``server_env.LLAMA_MTMD_FEAT_CACHE_DIR`` -> ``slurp-q4km``, the SAME
         directory every consumed SLURP flight warmed over these SAME 60
         samples (never the legacy earnings21/22 ``q4km`` cache).
      2. ``decoding_params.id_slot`` ("per-sample") is REMOVED -- a
         batch-executor-only sentinel; the rails ``FrozenCoreClient`` path has
         no batch executor.

    ``server_args`` are the fragment's OWN argv, UNCHANGED, including ``-np 4``.
    That number is load-bearing evidence for this flight (the P-CORR-F
    resend-divergence finding) and is recorded verbatim in the receipt; it is
    NOT altered here, because changing it would change the decode config every
    consumed P-SLU/P-FEW row this probe's own C-DECODE comparison is paired
    against."""

    from speech_aware_evidence_acquisition.rails.embedding_client import (
        EMBEDDING_ENDPOINT_PATH,
        LLAMA_MEDIA_MARKER_ENV,
        PROPS_MEDIA_MARKER_FIELD,
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb4r_flight import (
        ARMS,
        BANK_MANIFEST_SHA256,
        BANK_N_SCENARIOS,
        BANK_PER_SCENARIO_N,
        BANK_TOTAL_N,
        BINDING_CONFIG_SCHEMA,
        BINDING_CONFIG_SHA256,
        DEFAULT_BANK_SEED,
        GATE_CONTACTS_MAX,
        MODEL_LOCK_KEY,
        MODELS,
        PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH,
        PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
        PLANNED_BANK_CONTACTS,
        PLANNED_AUDIO_QUERY_CONTACTS,
        PLANNED_C_DECODE_CONTACTS,
        PLANNED_TEXT_QUERY_CONTACTS,
        QUERY_N,
        RETRIEVAL_K_PRIMARY,
        RETRIEVAL_K_REPORTED,
        WINNER_SELECTION_RULE,
        assert_binding_config_sha256,
        binding_config_sha256,
        resolve_model_binding,
    )

    # Fail-closed BEFORE any value is composed: the live arm table's own digest
    # must equal the pinned one, so the four model bindings this config hash is
    # about to record can never have drifted -- including the umbrella lock's
    # own content for those four keys.
    assert_binding_config_sha256(lock)

    fragment = json.loads((repo / MODEL_FRAGMENT_RELPATH).read_text(encoding="utf-8"))
    values: dict[str, object] = dict(fragment)

    server_env = dict(values.get("server_env", {}))
    server_env["LLAMA_MTMD_FEAT_CACHE_DIR"] = CORE_FEAT_CACHE_DIR
    values["server_env"] = server_env

    decoding = dict(values.get("decoding_params", {}))
    decoding.pop("id_slot", None)
    values["decoding_params"] = decoding

    values.update(
        {
            "arm": D2_ARM,
            "probe": PROBE_LABEL,
            "run_id": run_id(),
            "status": "REGISTERED",
            "flight_config_version": "pemb4r-launcher-v1 (no committed g0-binding config; see module docstring)",
            "preregistration": PREREGISTRATION_RELPATH,
            "e1_identity_record": E1_IDENTITY_RELPATH,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "split_name": "devel",
            "split_role": SPLIT_ROLE,
            "split_identity_hash": split_identity_hash(),
            "sample_manifest": SAMPLE_MANIFEST_RELPATH,
            "roster_table": ROSTER_TABLE_RELPATH,
            "tier": (
                "embedding (encode+pool, ZERO generation) for all seven kNN arms; "
                "generation ONLY for the registered C-DECODE arm on the pinned q4km core"
            ),
            "embedding_endpoint": EMBEDDING_ENDPOINT_PATH,
            "media_marker_env": LLAMA_MEDIA_MARKER_ENV,
            "media_marker_props_field": PROPS_MEDIA_MARKER_FIELD,
            "binding_config_schema": BINDING_CONFIG_SCHEMA,
            "binding_config_sha256": BINDING_CONFIG_SHA256,
            "binding_config_sha256_recomputed": binding_config_sha256(lock),
            "prefixes": {"audio_prefix": "", "text_prefix": ""},
            "prefix_note": (
                "bare content on both sides, per the registration's own register-alignment design "
                "and the P-EMB-1 precedent -- in explicit contrast to P-EMB-3L's refuted "
                "instruct-prefix arms"
            ),
            "bank": {
                "n_scenarios": BANK_N_SCENARIOS,
                "per_scenario_n": BANK_PER_SCENARIO_N,
                "total": BANK_TOTAL_N,
                "seed": DEFAULT_BANK_SEED,
                "manifest_sha256": BANK_MANIFEST_SHA256,
                "source": "SLURP train.jsonl TRAIN split via rails.probes.pfew_flight.load_train_demo_pool",
                "value_metadata_note": (
                    "each bank row's own gold_scenario is TRAIN-split VALUE metadata: never embedded, "
                    "never rendered into an embedding request; only 'text' is ever passed to embed_text"
                ),
            },
            "retrieval": {
                "k_primary": RETRIEVAL_K_PRIMARY,
                "k_reported": list(RETRIEVAL_K_REPORTED),
                "winner_selection_rule": WINNER_SELECTION_RULE,
            },
            "arms": [
                {
                    "arm_id": arm.arm_id,
                    "model": arm.model,
                    "query_kind": arm.query_kind,
                    "kind": arm.kind,
                    "model_lock_key": MODEL_LOCK_KEY[arm.model],
                    "model_binding": resolve_model_binding(lock, MODEL_LOCK_KEY[arm.model]),
                }
                for arm in sorted(ARMS, key=lambda a: a.arm_id)
            ],
            "declared_embedding_length_by_model": dict(sorted(declared_dims.items())),
            "query_n": QUERY_N,
            "planned_bank_contacts": PLANNED_BANK_CONTACTS,
            "planned_audio_query_contacts": PLANNED_AUDIO_QUERY_CONTACTS,
            "planned_text_query_contacts": PLANNED_TEXT_QUERY_CONTACTS,
            "planned_c_decode_contacts": PLANNED_C_DECODE_CONTACTS,
            "planned_gate_contacts": PLANNED_GATE_CONTACTS,
            "gate_contacts_max": GATE_CONTACTS_MAX,
            "gate_contact_plan": dict(GATE_CONTACT_PLAN),
            "t0_transcript_registry_relpath": PKEY2_338_TRANSCRIPT_REGISTRY_RELPATH,
            "t0_transcript_registry_sha256": PKEY2_338_TRANSCRIPT_REGISTRY_SHA256,
            "embedder_servers": [
                {
                    "server_key": f"lco3-{mode}",
                    "model": "lco3",
                    "model_lock_key": MODEL_LOCK_KEY["lco3"],
                    "port": LCO3_PORT,
                    "pooling_mode": mode,
                    "server_args": lco_session_args(mode),
                    "gguf_files": [
                        {"path": rel, "sha256": sha256_by_relpath.get(rel)} for rel in gguf_relpaths("lco3")
                    ],
                    "server_env": {
                        "LLAMA_MTMD_FEAT_CACHE_DIR": FEAT_CACHE_BY_MODEL["lco3"],
                        "LLAMA_MEDIA_MARKER": "<__media__>",
                    },
                    "recipe_source": f"{E1_IDENTITY_RELPATH} Mission B",
                }
                for mode in POOLING_MODES
            ]
            + [
                {
                    "server_key": f"lco7-{mode}",
                    "model": "lco7",
                    "model_lock_key": MODEL_LOCK_KEY["lco7"],
                    "port": LCO7_PORT,
                    "pooling_mode": mode,
                    "server_args": lco_session_args(mode),
                    "gguf_files": [
                        {"path": rel, "sha256": sha256_by_relpath.get(rel)} for rel in gguf_relpaths("lco7")
                    ],
                    "server_env": {
                        "LLAMA_MTMD_FEAT_CACHE_DIR": FEAT_CACHE_BY_MODEL["lco7"],
                        "LLAMA_MEDIA_MARKER": "<__media__>",
                    },
                    "recipe_source": f"{E1_IDENTITY_RELPATH} Mission B (same recipe, 7B weights)",
                }
                for mode in POOLING_MODES
            ]
            + [
                {
                    "server_key": "qw",
                    "model": "qw",
                    "model_lock_key": MODEL_LOCK_KEY["qw"],
                    "port": QW_PORT,
                    "pooling_mode": "last",
                    "server_args": list(QW_SERVER_ARGS),
                    "gguf_files": [
                        {"path": rel, "sha256": sha256_by_relpath.get(rel)} for rel in gguf_relpaths("qw")
                    ],
                    "server_env": {},
                    "recipe_source": f"{E1_IDENTITY_RELPATH} Mission C",
                }
            ],
            "in_process_models": [
                {
                    "model": "glap",
                    "model_lock_key": MODEL_LOCK_KEY["glap"],
                    "kind": "in-process-transformers",
                    "weights": {
                        "path": f"{GLAP_SUBDIR}/{GLAP_WEIGHTS}",
                        "sha256": sha256_by_relpath.get(f"{GLAP_SUBDIR}/{GLAP_WEIGHTS}"),
                    },
                    "device_placement_note": (
                        "GLAP's own encode_text builds its token tensors on CPU unconditionally and "
                        "only moves the ENCODER OUTPUT onto the projection's device -- upstream's own "
                        "split-device contract. The P-EMB-3M launcher's device-placement fix "
                        "(model.text_encoder.to('cpu')) is carried verbatim; not one byte of the "
                        "pinned remote code is edited."
                    ),
                }
            ],
            "generation_session": {
                "server_key": "q4km-core",
                "model_lock_key": fragment["model_lock_key"],
                "port": GENERATION_PORT,
                "server_args": list(fragment["server_args"]),
                "server_env": server_env,
                "decoding_params": decoding,
                "parallelism_np": _np_value(fragment["server_args"]),
                "parallelism_note": (
                    "-np is carried UNCHANGED from the committed fragment. The P-CORR-F pre-read "
                    "resend finding (6/20 identical-prompt pairs diverged at -np 4) makes this "
                    "number load-bearing evidence, so it is recorded rather than silently altered; "
                    "altering it would also change the decode config the consumed P-FEW FS-NONE "
                    "rows this flight's C-DECODE is paired against were produced under."
                ),
            },
            "feat_cache_dirs": {
                "lco3": FEAT_CACHE_BY_MODEL["lco3"],
                "lco7": FEAT_CACHE_BY_MODEL["lco7"],
                "core": CORE_FEAT_CACHE_DIR,
            },
            "gate_wav": {
                "synthetic": True,
                "corpus_audio": False,
                "sample_rate": GATE_WAV_SAMPLE_RATE,
                "seconds": GATE_WAV_SECONDS,
                "freq_hz": GATE_WAV_FREQ_HZ,
                "amplitude": GATE_WAV_AMPLITUDE,
                "sha256": hashlib.sha256(build_gate_wav_bytes()).hexdigest(),
            },
            "models": list(MODELS),
            "orchestrator": "rails.probes.pemb4r_flight",
            "launcher": "scratchpad pemb4r/launch_pemb4r_flight.py (archived with the flight receipt)",
        }
    )
    return values


def _np_value(server_args_: Sequence[str]) -> str | None:
    tokens = [str(token) for token in server_args_]
    for index, token in enumerate(tokens):
        if token == "-np" and index + 1 < len(tokens):
            return tokens[index + 1]
    return None


def config_hash_of(values: Mapping[str, object]) -> str:
    """Byte-identical to ``core.config._canonical_hash``."""

    blob = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def decoding_params(values: Mapping[str, object]) -> dict[str, object]:
    return dict(values.get("decoding_params", {}))


def core_server_args(values: Mapping[str, object]) -> list[str]:
    raw = values.get("server_args", [])
    if not isinstance(raw, (list, tuple)):
        raise ValueError("server_args must be a list")
    return [str(token) for token in raw]


def core_server_env(values: Mapping[str, object]) -> dict[str, str]:
    raw = values.get("server_env", {})
    if not isinstance(raw, Mapping):
        raise ValueError("server_env must be a mapping")
    return {str(k): str(v) for k, v in raw.items()}
