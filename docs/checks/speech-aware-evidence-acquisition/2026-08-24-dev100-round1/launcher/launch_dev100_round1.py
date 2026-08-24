"""DEV-100 campaign **ROUND 1** launcher — exposure row
``SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN`` (bounded-discovery-probe).

ROUND-1 KNOB (coordinator decision after the round-0 owner sync,
single-variable for attribution): **tau 0.5 -> 0.65** — tighten percept
admission. Everything else is byte-identical to the sealed round-0 cell
(alpha 0.60, rrf rank weighting, evidence = rank + prior + agreement,
top-k 5, fusion m=5/c=2/l=3, rank weights 0.5/0.3/0.2, TRAIN priors, M11
pair-boundary stage OFF, value vectors SEALED, facet-side admission).
Mechanism (verified against ``rails.kb_policy._fuse_supply_filter``): tau
is the max-cosine admission threshold on content-facet recall — raising it
admits fewer facets, so fewer (possibly zero) values are selected and the
retain-primary path (``_advance_after_direct`` stop) fires for the first
time. Targets the round-0 damage channel (11 correct->wrong samples);
expected cost is some of the 26 wrong->correct repairs. The round-1 vs
round-0 comparison is per-sample.

This launcher is the flight-proven ROUND-0 ATTEMPT-6 launcher
(``../2026-08-24-dev100-round0/launcher/launch_dev100_round0_attempt6.py``,
landed exit 0 on the healthy BASE binary) with exactly these changes:
round index / attempt naming / output paths; the tau constant; the
run-cumulative plan declaration (950 calls / 2,450 audio-s over the 688 /
1,824.52 already durable for round 0); the M0 arm consumed from ROUND-0's
SEALED per-sample scoring artifact instead of re-parsing attempt-1 texts
(round 0 is scored and sealed — M0 is never re-flown and never re-opened
sample-by-sample from raw traces); and the round-1 report adding the
per-sample movement analysis vs both M0 and BLEND-round-0. The serving
session is the SAME attempt-6 BASE-build resident service (receipt hash
re-verified before attach; the R6 prompt-fit row binds this session and
STANDS — tau changes only WHICH values render, bounded by the same
worst-case m/c/l envelope the fit measured).

Gold discipline: devel gold and every gold-derived artifact (the round-0
per-sample scores) open SCORING-SIDE ONLY, after all round-1 arms seal.
Before the seal this launcher touches them as opaque bytes (sha256 pins)
only.

Encode-only scope note, recorded honestly: the source-level guards 1/2 of
``rails.encode_only_check`` are scoped to embedding-only runners and are NOT
run over this launcher's own source — this launcher legitimately constructs
``FrozenCoreClient`` (a generation client) for the frozen-core arms, which is
what those guards exist to refuse in an embedding-only context. The embedding
CHANNEL keeps its full protection: the pinned-module structural sweep
(guard set a), the live-client surface check (guard 3), and the per-request
payload sweep (guard 4) all run.

Run in WSL2 (systemd-run --user unit, immune to agent-session reaping)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python docs/checks/.../launcher/launch_dev100_round1.py

Self-test (offline: stubbed timings, zero contacts, no service, no gate)::

    ... launch_dev100_round1.py --self-test
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import statistics
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Sequence as AbcSequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit(f"PYTHONPATH must contain the literal {REPO / 'src'}")

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(f"package resolves to {_pkg.__file__}, not the main checkout")

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import TRANSPORTS, Registry  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.resources import (  # noqa: E402
    resolve_resource_sampler,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    attach_session,
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.tracing import (  # noqa: E402
    TraceBuffer,
    TraceSink,
    TraceSinkError,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SLURP_LOCK_KEY,
    SlurpAdapter,
    SlurpSample,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EmbeddingClient,
)
from speech_aware_evidence_acquisition.rails.encode_only_check import (  # noqa: E402
    assert_client_surface_is_encode_only,
    assert_payload_has_no_forbidden_keys,
    run_encode_only_machine_check,
)
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    CONTROLLER_POLICY_ID,
    FuseKnobs,
    KbAlphaBlendController,
    RankWeights,
    default_label_normalizer,
    fuse_supplyfilter_factory,
    make_kb_alpha_blend_controller_factory,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    run_speech_native_agent_loop,
)

# --------------------------------------------------------------------------
# Pinned identity (campaign row + amendment 5b + landed receipts; every pin
# below except the round-1 knob/plan block is byte-identical to attempt 6).
# --------------------------------------------------------------------------

RUN_ID = "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
ROUND_INDEX = 1
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-dev100"
BASELINE_FRAGMENT = "slurp-dev100-kb-alpha-blend"
EXPERIMENT_FRAGMENT = "slurp-dev100-kb-alpha-blend-campaign-v1"
COMPOSED_CONFIG_SHA256 = "7fff75d1ed8642a9e948d86e8d6c5bf9cfd669f7342d9da009167dfd62655ca5"
SPLIT_ID = "DEV-100"
SPLIT_IDENTITY_HASH = "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
RUNTIME_VIEW_SHA256 = "9c7fe959ab0a258de97094a5edeb17da88de95965a093ea076deabe7a47220f7"
PROMOTION_RECEIPT_SHA256 = "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-mmproj-free.json"
FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
SESSION_DIR = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP8-BASE-DEV100-20260824T120910Z"
)
SESSION_RECEIPT_SHA256 = "6c8bab4d67432b4a3b88679483f0d6db41e28620ab8ee973f442a97200861b10"
DECODER_PORT = 8080
EMB_PORT = 8082

# Attempt-1 durable M0 trace: HASH AUTHORITY ONLY this round (canary byte
# comparison + resend response A). Round 1 never parses its response TEXTS —
# the M0 arm's scoring authority is round-0's sealed per-sample artifact.
A1_ATTEMPT_ID = "attempt-20260824T073337Z-dev100r0"
A1_TRACE_SHA256 = "d1f376bbacaa189f6583abe639d072567c4001fe63c52dab34e113b59ce4d8a2"

# ROUND-0 SEALED AUTHORITIES (gold-derived; opened content-wise ONLY at the
# post-seal scoring step; before that, opaque byte pins).
A6_ATTEMPT_ID = "attempt-20260824T122641Z-dev100r0a6"
ROUND0_REPORT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round0/"
    "round0-report.json"
)
ROUND0_REPORT_SHA256 = "26f05488bb7031d1ae85710faffd2b414644729af1adc476a1002a55612fb0b6"
ROUND0_SCORES_SHA256 = "88922466d0463169547f0fcfae20bbdf98a6dd94a8ad7d89b68956a8bd343bed"

# Round-0 durable cumulative spend (attempts 1-6, ledger landing entry +
# durable attempt store, re-summed at registration: 688 calls /
# 1,824.5204999999996 audio-s / 300 tool contacts).
ROUND0_CORE_CONTACTS = 688
ROUND0_TOOL_CONTACTS = 300
ROUND0_AUDIO_SECONDS = 1824.5204999999996

# Campaign ceilings AS AMENDED by the owner at the round-0 sync
# (preregistration section 4 amendment, commit 121bdc08): audio-seconds
# 2,400 -> 5,500 and frozen-core contacts 1,800 -> 2,500; tool and GPU-h
# cells unchanged. The campaign experiment fragment stays byte-frozen (its
# ceilings block is the historical round-0 registration; the preregistration
# and the campaign exposure row carry the amendment).
CAMPAIGN_CEILING_CORE = 2500
CAMPAIGN_CEILING_TOOL = 1500
CAMPAIGN_CEILING_AUDIO = 5500
CAMPAIGN_CEILING_GPU_HOURS = 2.0

# Hosting (INHERITED from attempt 6, verified at registration): the BASE-build
# resident service was left up by the attempt-6 landing and serves round 1
# unchanged; the session receipt hash below binds the same session the R6
# prompt-fit row measured, so the fit STANDS for this round.
HOSTING = {
    "mode": "systemd-run --user unit saea-np8-dev100-r6-base -p KillMode=mixed (WSL Ubuntu-24.04, systemd PID 1)",
    "keepalive": "detached Windows wsl.exe client, PID 23864, started 2026-08-24T10:52:39Z (verified alive at round-1 registration; holds the VM)",
    "linger": "enabled (loginctl enable-linger chao, 2026-08-24T08:06Z)",
    "service_inheritance": (
        "round 1 flies on the SAME resident BASE-build service the attempt-6 "
        "round-0 landing left up (unit saea-np8-dev100-r6-base, llama-server "
        "pid 2768, port 8080, BASE build llama.cpp-featcache, 8 slots at "
        "n_ctx 8192): at round-1 registration the unit was active, /health "
        "ok, 8/8 slots idle, and the session receipt re-hashed byte-identical "
        "to the attempt-6 binding — no respawn, no restart, no binary change"
    ),
    "prompt_fit_standing": (
        "session-bound R6 prompt-fit row SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6 "
        "STANDS for round 1: the session receipt sha256 re-measured equal to "
        "the R6 binding at registration, and the tau knob changes only WHICH "
        "values are admitted for rendering — the worst-case evidence-decode "
        "envelope the fit measured (6,174 tokens vs 8,192, margin +1,954) is "
        "an upper bound at the unchanged fusion knobs m=5/c=2/l=3"
    ),
    "clock_lock_note": (
        "the Windows-side GPU clock lock nvidia-smi -lgc 1200,2500 REMAINS "
        "applied (harmless and explicitly NOT a remedy - the attempt-5 "
        "mid-flight samples falsified the clock hypothesis; the attempt-6 "
        "base-binary landing confirmed the pathology was build-bound); "
        "mid-flight Windows-side clock sampling continues into "
        "clock-samples-round1.jsonl"
    ),
}

# Embedder pins (umbrella lock qwen3-embedding-0.6b-gguf; the KB pass pins).
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_DIM = 1024
EMBEDDER_RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
EMB_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
)

# --------------------------------------------------------------------------
# ROUND-1 knobs: tau 0.5 -> 0.65 is the ONLY change vs the sealed round-0
# cell (single-variable attribution). Provenance ids rank_weight_id=rrf /
# evidence_variant=rank+prior+agreement name the sweep cell; the flown
# machinery is the FROZEN registered C3 chain.
# --------------------------------------------------------------------------
ROUND1_ALPHA = 0.6
ROUND1_TAU = 0.65
ROUND0_TAU_FOR_RECORD = 0.5
ROUND1_TOP_K = 5
ROUND1_FUSE = FuseKnobs(tau=ROUND1_TAU, m=5, c=2, top_l=3)
ROUND1_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

# Round-1 attempt ceilings (campaign-row round-1 registration): <= 210
# frozen-core contacts (4 canary allowance — the registered pair plus a
# one-time re-run pair ONLY if bytes differ from attempt-1's M0 hashes — +
# 200 BLEND per-loop worst case + 1 resend + margin), <= 130 embedding tool
# contacts. Both enforced fail-closed by caller-side meters.
#
# PLANNED_MODEL_CALLS and PLANNED_AUDIO_SECONDS are RUN-CUMULATIVE
# (core.model.adapter enforces both across every attempt of the run id via a
# fresh sibling read of durable attempt actuals per request). 950 = 688
# round-0 durable + 4 canary allowance + 200 BLEND worst case + 1 resend +
# 57 margin; 2,450 audio-s = 1,824.52 round-0 durable + ~560 worst case this
# round + margin. Both are inside the AMENDED campaign cells (2,500 core /
# 5,500 audio-s). rails.runner's per-loop worst-case check sees 200 <= 950.
ATTEMPT_CORE_CEILING = 210
ATTEMPT_TOOL_CEILING = 130
PLANNED_MODEL_CALLS = 950
PLANNED_AUDIO_SECONDS = 2450
PLANNED_GPU_HOURS = 1.0
REFUSED_TAKEOFFS: list[dict[str, object]] = []

# Decode-speed canary (attempt-3 registration, carried unchanged): 2 direct-
# decode contacts on the FIRST TWO attempt-1 M0 sample ids (sorted order),
# single-slot, timing only. PASS: every canary generation rate < 300
# ms/token (attempt-6 fresh-session canary measured 7.28/7.02 on this very
# service). The byte comparison vs attempt-1 M0 is a RECORDED FACT; round 1
# flies the SAME BASE build attempt 6 proved byte-identical to M0, so a
# mismatch is unexpected — if bytes differ the pair is re-run ONCE and
# within-build byte-identity is REQUIRED (a mismatch stops fail-closed).
CANARY_SAMPLE_COUNT = 2
CANARY_MS_PER_TOKEN_PASS = 300.0

# In-flight decode-rate sentinel (attempt-4 mechanism b, flight-proven):
# after EVERY completed frozen-core contact of arm BLEND, read the server's
# NEW print_timing generation rows from the tracked server-log offset; a
# rolling median over the last SENTINEL_WINDOW_CONTACTS observed rates
# STRICTLY ABOVE the abort threshold flushes everything durable and aborts
# cleanly (service left up).
SENTINEL_WINDOW_CONTACTS = 8
SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT = 1000.0

M0_POLICY_ID = "saea-direct-decode-only-m0"
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 64}

# GPU preflight facts (preregistration section 5.4), measured by the flight
# coordinator immediately before this launcher was started; the power limit
# is re-verified below in-script.
GPU_PREFLIGHT = {
    "lenovo_smart_fan_mode": 3,
    "enforced_power_limit_w_at_preflight": 100.0,
    "clock_lock": {
        "command": "nvidia-smi -lgc 1200,2500 (Windows side)",
        "status": (
            "REMAINS APPLIED (harmless; NOT a remedy — attempt 5 falsified "
            "the clock hypothesis, attempt 6 confirmed the pathology was "
            "build-bound; left in place and disclosed)"
        ),
    },
    "measured_at": (
        "2026-08-24 round-1 preflight (host PowerShell WMI GetSmartFanMode=3 "
        "+ Windows nvidia-smi enforced 100.00 W, idle 10.07 W / 42 C / "
        "1192 MHz / 0 % util; service /health ok with 8/8 slots idle; "
        "keepalive PID 23864 alive; session receipt re-hashed equal to the "
        "attempt-6/R6 binding)"
    ),
}

OUT_CHECK_DIR = REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-24-dev100-round1"

# Mid-flight clock sampling (attempt-5 semantics, CONTINUED): the coordinator
# samples the GPU from the WINDOWS side every ~10 s into this run-level JSONL
# file; the launcher embeds whatever samples exist into the sentinel abort
# record and the round report.
CLOCK_SAMPLES_NAME = "clock-samples-round1.jsonl"


def read_clock_samples(root: Path) -> list[dict[str, object]] | None:
    """Parse the Windows-side mid-flight clock samples if present."""

    path = root / "runs" / RUN_ID / CLOCK_SAMPLES_NAME
    if not path.exists():
        return None
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"raw": line})
    return rows


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Round adapter: DEV-100 runtime-view-filtered SLURP samples, scoring
# DEFERRED past the whole round (gold opens only after all arms seal).
# --------------------------------------------------------------------------


class RoundAdapter(SlurpAdapter):
    """SlurpAdapter filtered to the DEV-100 runtime view, with score()
    replaced by a gold-free deferral marker. ``load_split`` supports
    ``DEV-100`` (all 100), ``DEV-100-CANARY-2`` (the first two samples in
    sorted order, for the decode-speed canary micro-run), and
    ``DEV-100-RESEND-1`` (the first sample only, for the identical-prompt
    resend micro-run)."""

    def __init__(self, lock, root, *, repo_root, view_items) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._view_by_id = {item["sample_id"]: item for item in view_items}
        self._cache: dict[str, tuple[SlurpSample, ...]] = {}

    def load_split(self, split_id, **kwargs):  # noqa: D102
        if split_id not in ("DEV-100", "DEV-100-CANARY-2", "DEV-100-RESEND-1"):
            raise ValueError(f"RoundAdapter serves only DEV-100 views, not {split_id!r}")
        if "DEV-100" not in self._cache:
            records = load_slurp_split(self._lock, self._root, "devel")
            wanted = self._view_by_id
            picked = [record for record in records if record.sample_id in wanted]
            if len(picked) != len(wanted):
                missing = set(wanted) - {record.sample_id for record in picked}
                raise ValueError(f"devel split lacks view samples: {sorted(missing)[:5]}")
            samples = []
            for record in picked:
                item = wanted[record.sample_id]
                if record.media_relpath != item["media_relpath"]:
                    raise ValueError(f"media_relpath drift for {record.sample_id}")
                audio_ref = self._audio_ref(record.media_relpath)
                if audio_ref.sha256 != item["audio_sha256"]:
                    raise ValueError(f"audio bytes drift for {record.sample_id}")
                samples.append(
                    SlurpSample(
                        sample_id=record.sample_id,
                        audio_ref=audio_ref,
                        audio_seconds=record.audio_seconds,
                        utterance_id=record.utterance_id,
                        media_relpath=record.media_relpath,
                        scenario=record.scenario,
                        action=record.action,
                        intent=record.intent,
                        entities=record.entities,
                    )
                )
            self._cache["DEV-100"] = tuple(sorted(samples, key=lambda s: s.sample_id))
        full = self._cache["DEV-100"]
        if split_id == "DEV-100":
            return full
        if split_id == "DEV-100-CANARY-2":
            return full[:CANARY_SAMPLE_COUNT]
        return (full[0],)

    def score(self, sample, response):  # noqa: D102 — gold stays sealed in-round
        return {"scoring_deferred": True}


# --------------------------------------------------------------------------
# Reference-form instructions (byte-identity oracle; unchanged since
# b3d29658 landed the rendering rails-side).
# --------------------------------------------------------------------------

DIRECT_DIRECTIVE = (
    "Answer using only the speech query; no external knowledge has been "
    "supplied yet."
)
DIRECT_REFERENCE_INSTRUCTION = (
    "Decide under the task contract already given above. " + DIRECT_DIRECTIVE
)
EVIDENCE_REFERENCE_INSTRUCTION = (
    "Decide under the task contract already given above, now "
    "considering the retrieved evidence. Answer using the speech "
    "query together with the supplied knowledge evidence."
)


class CoreCeilingClient:
    """Delegating frozen-core client wrapper enforcing the attempt-level
    core-contact ceiling FAIL-CLOSED: the contact that would exceed the
    registered ceiling raises BEFORE reaching the transport (zero spend for
    the refused contact). An optional armed :class:`DecodeRateSentinel` is
    consulted AFTER every completed contact — armed only for arm BLEND."""

    def __init__(self, inner, ceiling: int) -> None:
        self._inner = inner
        self._ceiling = ceiling
        self._count = 0
        self._lock = threading.Lock()
        self._sentinel: "DecodeRateSentinel | None" = None

    @property
    def contact_count(self) -> int:
        return self._count

    def arm_sentinel(self, sentinel: "DecodeRateSentinel | None") -> None:
        self._sentinel = sentinel

    def complete(self, *args, **kwargs):
        with self._lock:
            if self._count + 1 > self._ceiling:
                raise RuntimeError(
                    f"round-1 core ceiling: <= {self._ceiling} frozen-core "
                    f"contacts registered and {self._count} are already spent; "
                    "refusing the next contact fail-closed"
                )
            self._count += 1
        result = self._inner.complete(*args, **kwargs)
        sentinel = self._sentinel
        if sentinel is not None:
            sentinel.observe_after_contact()
        return result

    def __getattr__(self, name):
        return getattr(self._inner, name)


class LazyQueryVector(AbcSequence):
    """Empty (len 0 -> cosine recall inert) until filled with the runtime
    embedding of the trajectory's own direct answer text."""

    def __init__(self) -> None:
        self._values: tuple[float, ...] | None = None

    def fill(self, values: Sequence[float]) -> None:
        if self._values is not None:
            raise RuntimeError("query vector already filled")
        self._values = tuple(float(v) for v in values)

    def __len__(self) -> int:
        return 0 if self._values is None else len(self._values)

    def __getitem__(self, index):
        if self._values is None:
            raise IndexError(index)
        return self._values[index]


class RuntimeEmbeddedBlendController:
    """Delegating wrapper: on the direct-decode response, embeds that text
    (ONE pinned-tool contact) into the injected content-dimension cell, then
    lets the REGISTERED controller advance. Adds no policy behaviour. The
    sha256 of the direct-decode response text is recorded for the
    cross-attempt byte-agreement descriptive."""

    def __init__(self, inner, *, sample_id: str, cell: LazyQueryVector, embed) -> None:
        self._inner = inner
        self._sample_id = sample_id
        self._cell = cell
        self._embed = embed
        self._filled = False
        self.direct_response_sha256: str | None = None

    def initial_contact(self, context):
        return self._inner.initial_contact(context)

    def advance(self, context, contact, response_text):
        if (
            contact.contact_id == "direct-decode"
            and isinstance(response_text, str)
            and not self._filled
        ):
            self.direct_response_sha256 = sha256_text(response_text)
            vector = self._embed(self._sample_id, response_text)
            self._cell.fill(vector)
            self._filled = True
        return self._inner.advance(context, contact, response_text)

    @property
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


# --------------------------------------------------------------------------
# Embedding contact meter (round-1 tool sub-ceiling, fail-closed).
# --------------------------------------------------------------------------


class EmbeddingMeter:
    def __init__(self, ceiling: int, contact_log: Path) -> None:
        self.ceiling = ceiling
        self.count = 0
        self.latency_total = 0.0
        self._log = contact_log
        self._lock = threading.Lock()

    def charge(self, contact_id: str) -> None:
        with self._lock:
            if self.count + 1 > self.ceiling:
                raise RuntimeError(
                    f"embedding tool ceiling: round 1 registers <= {self.ceiling} "
                    f"contacts and {self.count} are already spent; refusing"
                )
            self.count += 1

    def record(self, contact_id: str, latency: float, dims: int, text_sha256: str) -> None:
        with self._lock:
            self.latency_total += latency
            with self._log.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "index": self.count,
                            "contact_id": contact_id,
                            "latency_seconds": round(latency, 4),
                            "dims": dims,
                            "text_sha256": text_sha256,
                        }
                    )
                    + "\n"
                )


class CanaryFail(Exception):
    """Decode-speed canary failed: the flight stops BEFORE arm BLEND."""


def parse_print_timing(log_bytes: bytes) -> dict[str, list[dict[str, float]]]:
    """Extract llama-server per-request print_timing rates from raw server-log
    bytes: content-free serving descriptives only (ms totals, token counts,
    ms/token). Generation rows carry '|        eval time'; prompt rows carry
    '| prompt eval time'."""

    import re

    pattern = re.compile(
        r"\|\s*(prompt eval|eval) time =\s*([0-9.]+) ms /\s*([0-9]+) tokens "
        r"\(\s*([0-9.]+) ms per token"
    )
    rows: dict[str, list[dict[str, float]]] = {"prompt_eval": [], "generation": []}
    for line in log_bytes.decode("utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match is None:
            continue
        kind = "prompt_eval" if match.group(1) == "prompt eval" else "generation"
        rows[kind].append(
            {
                "total_ms": float(match.group(2)),
                "tokens": int(match.group(3)),
                "ms_per_token": float(match.group(4)),
            }
        )
    return rows


class DecodeRateSentinelTrip(Exception):
    """The in-flight decode-rate sentinel tripped: flush everything durable
    immediately and stop the flight cleanly (service left up)."""


class DecodeRateSentinel:
    """Rolling-median in-flight decode-rate guard (attempt-4 mechanism b,
    flight-proven in attempts 4/5/6)."""

    def __init__(
        self,
        server_log_path: Path,
        start_offset: int,
        *,
        window: int = SENTINEL_WINDOW_CONTACTS,
        threshold_ms_per_token: float = SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT,
    ) -> None:
        self._path = Path(server_log_path)
        self._offset = int(start_offset)
        self._window: deque[float] = deque(maxlen=int(window))
        self._threshold = float(threshold_ms_per_token)
        self.observed_rates: list[float] = []
        self.contacts_observed = 0
        self.tripped: dict[str, object] | None = None
        self._lock = threading.Lock()

    def observe_after_contact(self) -> None:
        with self._lock:
            self.contacts_observed += 1
            with self._path.open("rb") as handle:
                handle.seek(self._offset)
                data = handle.read()
            self._offset += len(data)
            for row in parse_print_timing(data)["generation"]:
                self._window.append(float(row["ms_per_token"]))
                self.observed_rates.append(float(row["ms_per_token"]))
            if len(self._window) == self._window.maxlen:
                rolling_median = float(statistics.median(self._window))
                if rolling_median > self._threshold:
                    self.tripped = {
                        "rolling_median_ms_per_token": rolling_median,
                        "window_ms_per_token": [round(r, 2) for r in self._window],
                        "threshold_ms_per_token": self._threshold,
                        "window_contacts": self._window.maxlen,
                        "contacts_observed": self.contacts_observed,
                        "rates_observed": len(self.observed_rates),
                    }
                    raise DecodeRateSentinelTrip(
                        "in-flight decode-rate sentinel TRIPPED: rolling median "
                        f"{rolling_median:.2f} ms/token over the last "
                        f"{self._window.maxlen} observed generation rows exceeds "
                        f"the registered abort threshold {self._threshold:.0f} "
                        f"ms/token; window "
                        f"{[round(rate, 2) for rate in self._window]}"
                    )

    def summary(self) -> dict[str, object]:
        rates = sorted(self.observed_rates)
        descript: dict[str, object] = {
            "contacts_observed": self.contacts_observed,
            "rates_observed": len(rates),
            "window_contacts": self._window.maxlen,
            "threshold_ms_per_token": self._threshold,
            "tripped": self.tripped,
        }
        if rates:
            descript.update(
                {
                    "ms_per_token_min": rates[0],
                    "ms_per_token_median": rates[len(rates) // 2],
                    "ms_per_token_p90": rates[min(len(rates) - 1, int(0.9 * len(rates)))],
                    "ms_per_token_max": rates[-1],
                }
            )
        return descript


def flush_micro_run_buffer(
    buffer: TraceBuffer, sink: TraceSink, namespace: str
) -> list[str]:
    """Flush a micro-run's TraceBuffer into its OWN TraceSink (attempt-4
    mechanism a), applying a record-id namespace prefix at flush time so
    record ids stay globally unique across every sink of the attempt."""

    flushed: list[str] = []
    for channel, record_id, payload in buffer.records:
        namespaced = f"{namespace}/{record_id}"
        sink.emit(channel, namespaced, payload)
        flushed.append(namespaced)
    buffer.records = []
    return flushed


def assert_zero_record_id_overlap(sink_ids: Mapping[str, frozenset]) -> None:
    """Assert the record-id sets of every pair of trace sinks are disjoint."""

    names = sorted(sink_ids)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = sink_ids[left] & sink_ids[right]
            if overlap:
                raise SystemExit(
                    f"record-id overlap between the {left!r} and {right!r} trace "
                    f"sinks: {sorted(overlap)[:5]!r}; the attempt-3 collision "
                    "class is present — refusing"
                )


def self_test() -> int:
    """Offline exercise of BOTH retained attempt-4 mechanisms: stubbed timings,
    zero model contacts, no service, no gate, no data root."""

    base = Path(tempfile.mkdtemp(prefix="saea-dev100-r1-selftest-"))
    log(f"SELF-TEST in {base} (zero contacts, no service, no data root)")

    # ---- mechanism a: micro-run trace isolation --------------------------
    def duplicate_heavy_buffer() -> TraceBuffer:
        buffer = TraceBuffer(RUN_ID)
        for sample_id in ("stub:000090", "stub:000109"):
            buffer.emit("ORG", f"{sample_id}/agent-loop/org", {"org_stub": sample_id})
            buffer.emit("USE", f"{sample_id}/agent-loop/use", {"use_stub": sample_id})
        return buffer

    main_sink = TraceSink(base / "main", RUN_ID)
    canary_sink = TraceSink(base / "canary-trace", RUN_ID)
    canary_ids = flush_micro_run_buffer(duplicate_heavy_buffer(), canary_sink, "canary")
    blend_buffer = duplicate_heavy_buffer()  # regenerates the SAME record ids
    blend_ids = [record_id for _, record_id, _ in blend_buffer.records]
    blend_buffer.flush_into(main_sink)
    assert_zero_record_id_overlap(
        {"main": frozenset(blend_ids), "canary": frozenset(canary_ids)}
    )
    canary_sink.close()
    try:
        duplicate_heavy_buffer().flush_into(main_sink)
    except TraceSinkError as error:
        log(f"self-test: shared-sink collision correctly refused ({error})")
    else:
        raise SystemExit(
            "self-test FAIL: duplicate flush into one sink did not raise"
        )
    try:
        assert_zero_record_id_overlap(
            {"main": frozenset(blend_ids), "canary": frozenset(blend_ids)}
        )
    except SystemExit as error:
        log(f"self-test: overlap assertion correctly fired ({error})")
    else:
        raise SystemExit("self-test FAIL: record-id overlap not detected")
    log("self-test mechanism a PASS: micro-run sink isolation + both negative controls")

    # ---- mechanism b: in-flight decode-rate sentinel ---------------------
    stub_log = base / "server.log"
    stub_log.write_text("", encoding="utf-8")

    def stub_rows(rates: Sequence[float]) -> None:
        with stub_log.open("a", encoding="utf-8") as handle:
            for rate in rates:
                tokens = 32
                handle.write(
                    f"srv  log_server_r: |        eval time =    {rate * tokens:.2f} ms "
                    f"/    {tokens} tokens (   {rate:.2f} ms per token, "
                    f"{1000.0 / rate:.2f} tokens per second)\n"
                )

    sentinel = DecodeRateSentinel(stub_log, 0)
    stub_rows([30.0] * SENTINEL_WINDOW_CONTACTS)
    for _ in range(SENTINEL_WINDOW_CONTACTS):
        sentinel.observe_after_contact()
    if sentinel.tripped is not None:
        raise SystemExit("self-test FAIL: sentinel tripped on healthy rates")
    stub_rows([SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT] * SENTINEL_WINDOW_CONTACTS)
    for _ in range(SENTINEL_WINDOW_CONTACTS):
        sentinel.observe_after_contact()
    if sentinel.tripped is not None:
        raise SystemExit(
            "self-test FAIL: sentinel tripped AT the threshold (must be strict >)"
        )
    stub_rows([5137.0] * SENTINEL_WINDOW_CONTACTS)
    try:
        for _ in range(SENTINEL_WINDOW_CONTACTS):
            sentinel.observe_after_contact()
    except DecodeRateSentinelTrip as error:
        log(f"self-test: sentinel correctly tripped ({error})")
    if sentinel.tripped is None:
        raise SystemExit("self-test FAIL: sentinel did not trip on degraded rates")
    summary = sentinel.summary()
    if summary["rates_observed"] != 3 * SENTINEL_WINDOW_CONTACTS:
        raise SystemExit(f"self-test FAIL: unexpected observation count: {summary}")
    log(f"self-test mechanism b PASS: {summary}")

    # ---- round-1 knob sanity: tau is the ONLY divergence from round 0 ----
    if ROUND1_FUSE.tau != 0.65 or (ROUND1_FUSE.m, ROUND1_FUSE.c, ROUND1_FUSE.top_l) != (5, 2, 3):
        raise SystemExit(f"self-test FAIL: round-1 fuse knobs drifted: {ROUND1_FUSE}")
    if (ROUND1_ALPHA, ROUND1_TOP_K) != (0.6, 5):
        raise SystemExit("self-test FAIL: non-tau knobs drifted from the round-0 cell")
    if (ROUND1_WEIGHTS.w_cos, ROUND1_WEIGHTS.w_prior, ROUND1_WEIGHTS.w_agree) != (0.5, 0.3, 0.2):
        raise SystemExit("self-test FAIL: rank weights drifted from the round-0 cell")
    log("self-test knob sanity PASS: tau=0.65 single-variable vs the round-0 cell")
    log("SELF-TEST PASS (both retained mechanisms + knob sanity; zero contacts)")
    return 0


def guarded_post(timeout_seconds: float):
    import urllib.request

    def post(url: str, body: bytes) -> bytes:
        assert_payload_has_no_forbidden_keys(json.loads(body.decode("utf-8")), context="emb-request")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    attempt_id = f"attempt-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-dev100r1"
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"ROUND 1 launcher — {RUN_ID} / {attempt_id}")
    log(f"run dir: {run_dir}")

    flight: dict[str, object] = {
        "schema": "saea-dev100-round1-flight-v1",
        "run_id": RUN_ID,
        "round_index": ROUND_INDEX,
        "attempt_id": attempt_id,
        "round0_attempt_ids_disclosed": [
            "attempt-20260824T073337Z-dev100r0",
            "attempt-20260824T084302Z-dev100r0a2",
            "attempt-20260824T093833Z-dev100r0a3",
            "attempt-20260824T111833Z-dev100r0a4",
            "attempt-20260824T114704Z-dev100r0a5",
            A6_ATTEMPT_ID,
        ],
        "started_at": iso_now(),
        "gpu_preflight": dict(GPU_PREFLIGHT),
        "hosting": dict(HOSTING),
    }

    def save_flight() -> None:
        (run_dir / "flight-state.json").write_text(
            json.dumps(flight, indent=1, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    save_flight()

    # ---- GPU preflight re-verification (power limit; fan mode is Windows) --
    import subprocess

    smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=enforced.power.limit", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    enforced_w = float(smi.stdout.strip().split()[0])
    if enforced_w < 95.0:
        raise SystemExit(f"GPU preflight: enforced power limit {enforced_w} W < 95 W")
    flight["gpu_preflight"]["enforced_power_limit_w_in_wsl"] = enforced_w
    log(f"GPU preflight: enforced power limit {enforced_w} W (>= 95), SmartFanMode 3 (host-recorded)")

    # ---- composition ------------------------------------------------------
    composed = compose(REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    values = composed.values
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise SystemExit(
            f"composed config hash {composed.config_hash} != registered {COMPOSED_CONFIG_SHA256}"
        )
    server_args = list(values["server_args"])
    server_np = int(server_args[server_args.index("-np") + 1])
    if server_np != 8:
        raise SystemExit(f"composed -np is {server_np}, expected 8")
    log(f"composed config hash verified: {composed.config_hash} (-np {server_np})")
    flight["config_hash"] = composed.config_hash
    flight["server_np"] = server_np

    # ---- runtime view + promotion receipt ---------------------------------
    view = json.loads(
        (REPO / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(encoding="utf-8")
    )
    if view["runtime_view_sha256"] != RUNTIME_VIEW_SHA256:
        raise SystemExit("runtime view sha256 drifted")
    if view["split_identity_hash"] != SPLIT_IDENTITY_HASH or view["count"] != 100:
        raise SystemExit("runtime view identity drifted")
    promotion_path = FEATURE_ROOT / "DEV-100-promotion.json"
    measured_promotion = sha256_file(promotion_path)
    if measured_promotion != PROMOTION_RECEIPT_SHA256:
        raise SystemExit(f"promotion receipt hashes to {measured_promotion}, not the pin")
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    if promotion.get("dataset_runtime_view_sha256") != RUNTIME_VIEW_SHA256:
        raise SystemExit("promotion receipt binds a different runtime view")
    log(f"DEV-100 promotion receipt verified ({measured_promotion[:12]}…)")

    # ---- knowledge snapshot + SEALED-value discipline ---------------------
    snapshot_path = root / "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise SystemExit("knowledge snapshot content hash mismatch")
    log(f"TRAIN snapshot verified: {len(snapshot.facets)} facets / {len(snapshot.values)} values")

    emb_receipt = json.loads(
        (REPO / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full-embeddings.json").read_text(
            encoding="utf-8"
        )
    )
    facet_block = emb_receipt["vectors"]["content_facets"]
    facet_npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = sha256_file(facet_npz_path)
    if measured_npz != facet_block["sha256"]:
        raise SystemExit("content-facet npz hash mismatch vs the landed receipt")
    npz = np.load(facet_npz_path)
    facet_ids = [str(v) for v in npz["ids"]]
    facet_matrix = npz["vectors"]
    if facet_matrix.shape != (len(facet_ids), EMBEDDER_DIM):
        raise SystemExit(f"unexpected facet vector shape {facet_matrix.shape}")
    log(
        f"content-facet vectors loaded: {facet_matrix.shape} ({measured_npz[:12]}…). "
        "VALUE VECTORS SEALED: vectors-values.npz is NOT loaded by this flight."
    )
    facet_vector_table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    for index, facet_id in enumerate(facet_ids):
        facet_vector_table[facet_id] = {"content": tuple(facet_matrix[index].tolist())}

    def facet_vectors(facet_id: str) -> Mapping[str, tuple[float, ...]]:
        return facet_vector_table.get(facet_id, {})

    flight["knowledge"] = {
        "snapshot_sha256": SNAPSHOT_SHA256,
        "facet_vectors_npz_sha256": measured_npz,
        "value_vectors_loaded": False,
        "percept_admission": "facet-side (fuser construction)",
    }
    save_flight()

    # ---- samples (model-free; hashes only the 100 view files) -------------
    adapter = RoundAdapter(lock, root, repo_root=REPO, view_items=view["items"])
    log("loading the 100 DEV-100 samples (per-file sha256 against the view)")
    samples = adapter.load_split(SPLIT_ID)
    if len(samples) != 100:
        raise SystemExit(f"{len(samples)} samples, expected 100")
    one_pass_audio = sum(float(s.audio_seconds) for s in samples)
    log(f"samples verified: 100 ids, one metered pass = {one_pass_audio:.6f}s")

    packet_bindings: dict[str, dict[str, str]] = {}
    for item in view["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        packet_bindings[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    if set(packet_bindings) != {s.sample_id for s in samples}:
        raise SystemExit("packet bindings do not cover the split")
    log("speech packet bindings materialized for all 100 samples")

    payload_binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    log("payload binding built (inputs complete, still pre-gate)")

    # ---- attempt-1 durable M0 trace: byte identity + HASH INDEX ONLY ------
    a1_run_dir = root / "runs" / RUN_ID / A1_ATTEMPT_ID
    a1_trace_path = a1_run_dir / f"{RUN_ID}.trace.jsonl"
    measured_a1_trace = sha256_file(a1_trace_path)
    if measured_a1_trace != A1_TRACE_SHA256:
        raise SystemExit(
            f"attempt-1 trace hashes to {measured_a1_trace}, not the registered "
            f"{A1_TRACE_SHA256}; the canary/resend hash authority cannot be identified"
        )
    log(f"attempt-1 M0 trace verified ({measured_a1_trace[:12]}…, hash-index authority)")
    a1_request_sample: dict[str, str] = {}
    a1_response_sha_by_request: dict[str, str] = {}
    with a1_trace_path.open(encoding="utf-8") as trace_handle:
        for line in trace_handle:
            record = json.loads(line)
            channel = record.get("channel")
            record_id = str(record.get("record_id", ""))
            if channel == "MODEL_REQUEST":
                base = record_id.rsplit("/", 1)[0]
                a1_request_sample[base] = str(record["payload"]["payload"]["sample_id"])
            elif channel == "MODEL_RESPONSE":
                base = record_id.rsplit("/", 1)[0]
                a1_response_sha_by_request[base] = str(
                    record["payload"]["response_text_sha256"]
                )
    if set(a1_request_sample) != set(a1_response_sha_by_request):
        raise SystemExit("attempt-1 trace: request/response pairing incomplete")
    a1_m0_response_sha: dict[str, str] = {
        sample_id: a1_response_sha_by_request[base]
        for base, sample_id in a1_request_sample.items()
    }
    if set(a1_m0_response_sha) != {s.sample_id for s in samples} or len(
        a1_request_sample
    ) != 100:
        raise SystemExit(
            "attempt-1 M0 trace does not cover the DEV-100 split exactly once"
        )
    log("attempt-1 M0 hash index built: 100 request/response pairs cover the split")

    # ---- ROUND-0 sealed authorities: OPAQUE BYTE PINS pre-seal ------------
    # Content (gold-derived per-sample correctness) is parsed ONLY at the
    # post-seal scoring step below.
    round0_report_path = REPO / ROUND0_REPORT_RELPATH
    measured_r0_report = sha256_file(round0_report_path)
    if measured_r0_report != ROUND0_REPORT_SHA256:
        raise SystemExit(
            f"round-0 sealed report hashes to {measured_r0_report}, not the "
            f"ledger-pinned {ROUND0_REPORT_SHA256}"
        )
    round0_scores_path = root / "runs" / RUN_ID / A6_ATTEMPT_ID / "round0-scores.json"
    measured_r0_scores = sha256_file(round0_scores_path)
    if measured_r0_scores != ROUND0_SCORES_SHA256:
        raise SystemExit(
            f"round-0 per-sample scores hash to {measured_r0_scores}, not the "
            f"registered {ROUND0_SCORES_SHA256}"
        )
    log(
        "round-0 sealed authorities pinned byte-wise (report "
        f"{measured_r0_report[:12]}…, scores {measured_r0_scores[:12]}…); "
        "content stays sealed until the post-seal scoring step"
    )
    flight["round0_sealed_authorities"] = {
        "report_path": str(round0_report_path),
        "report_sha256": measured_r0_report,
        "scores_path": str(round0_scores_path),
        "scores_sha256": measured_r0_scores,
    }

    # ---- model-free dry check: the REGISTERED chain vs the runner's guard --
    from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: PLC0415
        QueryState,
    )
    from speech_aware_evidence_acquisition.rails.obs import (  # noqa: PLC0415
        default_obs_packet,
    )
    from speech_aware_evidence_acquisition.rails.runner import (  # noqa: PLC0415
        AgentRuntimeContext,
        _assert_agent_control_excludes_knowledge_payloads,
        _protected_knowledge_material,
    )

    protected = _protected_knowledge_material(snapshot)
    dry_sample = samples[0]
    dry_contract = adapter.build_task_contract(
        dry_sample, default_obs_packet(dry_sample)
    )
    dry_state = QueryState(
        query_id=f"dry:{dry_sample.sample_id}",
        query_sample_id=dry_sample.sample_id,
        speech_packet_id=packet_bindings[dry_sample.sample_id]["packet_id"],
        speech_packet_sha256=packet_bindings[dry_sample.sample_id]["sha256"],
        use_split_identity_hash=SPLIT_IDENTITY_HASH,
        use_partition_role="dev",
    ).validate()
    dry_controller = KbAlphaBlendController(
        snapshot=None,
        query_vectors={},
        facet_vectors=lambda facet_id: {},
        normalizer=default_label_normalizer,
        ranker=rank_wcos_prior_agree_factory(
            RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)
        ),
        fuser=fuse_supplyfilter_factory(FuseKnobs(tau=1.0, m=1, c=1, top_l=1)),
        alpha=0.5,
        top_k_per_dimension=1,
    )
    dry_context = AgentRuntimeContext(
        sample_id=dry_sample.sample_id,
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(facet.facet_id for facet in snapshot.facets),
        catalog_value_ids=(),
        query_state=dry_state,
        task_contract=dry_contract,
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )
    dry_plan = dry_controller.initial_contact(dry_context)
    if dry_plan.instruction != DIRECT_REFERENCE_INSTRUCTION:
        raise SystemExit(
            "rails-rendered direct instruction differs from the registered "
            f"bytes; refusing (rendered: {dry_plan.instruction[:120]!r})"
        )
    _assert_agent_control_excludes_knowledge_payloads(dry_plan, protected)
    for name, text in (
        ("direct-reference", DIRECT_REFERENCE_INSTRUCTION),
        ("evidence-reference", EVIDENCE_REFERENCE_INSTRUCTION),
    ):
        hits = [m for m in protected if m in text.casefold()]
        if hits:
            raise SystemExit(
                f"guard simulation: {name} instruction embeds protected knowledge "
                f"payloads {hits[:3]!r}; refusing before takeoff"
            )
    log(
        "dry check PASS: rails-rendered direct instruction is byte-identical to "
        "the registered form and clears the runner's protected-knowledge "
        f"guard against all {len(protected)} protected payloads"
    )

    if "--preflight-only" in sys.argv:
        flight["outcome_status"] = "PREFLIGHT_ONLY_PASS"
        save_flight()
        log("PREFLIGHT-ONLY PASS: every input verified; zero contacts, no gate, no attach")
        return 0

    # ---- execution plan + FULL frozen-core gate ---------------------------
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY,
        split_role="dev",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLANNED_MODEL_CALLS,
        planned_gpu_hours=PLANNED_GPU_HOURS,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=composed.config_hash,
        attempt_id=attempt_id,
    ).validate()
    (run_dir / "execution-plan.json").write_text(
        json.dumps(
            {
                "attempt_id": plan.attempt_id,
                "carrier_lock_key": plan.carrier_lock_key,
                "execution_profile": plan.execution_profile,
                "planned_gpu_hours": plan.planned_gpu_hours,
                "planned_model_calls": plan.planned_model_calls,
                "planned_speech_audio_seconds": plan.planned_speech_audio_seconds,
                "protocol_hash": plan.protocol_hash,
                "run_id": plan.run_id,
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": plan.split_identity_hash,
                "split_role": plan.split_role,
                "study": "speech-aware-evidence-acquisition",
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path("/home/chao"),
        runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
    )
    log("running the FULL frozen-core gate (q4km GGUF attestation; minutes of I/O)")
    gate_started = time.time()
    lock_sha256 = gate.assert_model_touch_allowed(plan, full_hash=True)
    log(f"frozen-core gate PASS in {time.time() - gate_started:.1f}s (lock {lock_sha256[:12]}…)")
    flight["gate"] = {"umbrella_lock_sha256": lock_sha256, "seconds": round(time.time() - gate_started, 1)}
    save_flight()

    # ---- attach to the resident np8 BASE-build service --------------------
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    receipt_path = SESSION_DIR / "session-receipt.json"
    measured_receipt = sha256_file(receipt_path)
    if measured_receipt != SESSION_RECEIPT_SHA256:
        raise SystemExit(
            f"resident session receipt hashes to {measured_receipt}, not the registered "
            f"{SESSION_RECEIPT_SHA256}; the service was restarted or mutated — the "
            "R6 prompt-fit no longer stands; STOP and respawn per the attempt-6 recipe"
        )
    session = attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao"))
    if list(session.argv) != [session.argv[0], "--host", "127.0.0.1", "--port", str(DECODER_PORT)] + [
        "-m", session.argv[6], "--no-mmproj"] + server_args:
        raise SystemExit("resident session argv does not match the np8 composition")
    log(f"attached to resident np8 session pid={session.pid} (receipt {measured_receipt[:12]}…)")
    flight["decoder_session"] = {
        "session_id": session.session_id,
        "pid": session.pid,
        "port": session.port,
        "receipt_sha256": measured_receipt,
        "np": server_np,
    }
    save_flight()

    transport = TRANSPORTS.resolve(str(values["transport"]))(
        values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao")
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=payload_binding,
        arm="speech-feature-query",
        request_id_prefix="dev100r1",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    log(f"FrozenCoreClient constructed (arm {client.arm})")

    # ---- embedding sidecar (own session + stop receipt) -------------------
    emb_report = run_encode_only_machine_check()
    log(f"encode-only structural sweep PASS: {list(emb_report.checked_modules)}")
    embedder_path = root / EMBEDDER_RELPATH
    measured_embedder = sha256_file(embedder_path)
    if measured_embedder != EMBEDDER_SHA256:
        raise SystemExit("embedder GGUF hash mismatch vs the umbrella lock pin")
    committed_pre = load_runtime_receipt(REPO / "docs" / EMBEDDER_RUNTIME_RECEIPT_RELPATH)
    emb_runtime_receipt = {
        "llama_cpp": dict(committed_pre["llama_cpp"]),
        "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured_embedder}],
    }
    if _port_reachable("127.0.0.1", EMB_PORT):
        raise SystemExit(f"something already listens on {EMB_PORT}")
    log(f"spawning CPU-only embedder sidecar on {EMB_PORT}: {list(EMB_SERVER_ARGS)}")
    emb_session = start_session(
        runtime_root=Path("/home/chao"),
        data_root=root,
        runtime_receipt=emb_runtime_receipt,
        host="127.0.0.1",
        port=EMB_PORT,
        session_id=f"{RUN_ID}-{attempt_id}-qwen3-emb-cpu",
        extra_argv=list(EMB_SERVER_ARGS),
        receipt_path=run_dir / "session-qwen3-emb-cpu.receipt.json",
        server_log_path=run_dir / "session-qwen3-emb-cpu.server.log",
        ready_timeout_seconds=900.0,
    )
    log(f"embedder sidecar up: pid={emb_session.pid} port={emb_session.port}")

    meter = EmbeddingMeter(ATTEMPT_TOOL_CEILING, run_dir / "embedding-contacts.jsonl")
    emb_client = EmbeddingClient(
        base_url=f"http://127.0.0.1:{EMB_PORT}",
        post=guarded_post(600.0),
        timeout_seconds=600.0,
        expected_dim=EMBEDDER_DIM,
        require_marker_verification=False,
    )
    assert_client_surface_is_encode_only(emb_client)
    emb_client.verify_media_marker()
    embed_lock = threading.Lock()
    query_vector_log = run_dir / "query-vectors.jsonl"

    def embed_query_text(sample_id: str, text: str) -> tuple[float, ...]:
        contact_id = f"query:{sample_id}"
        with embed_lock:
            meter.charge(contact_id)
            started = time.time()
            vector = emb_client.embed_text(contact_id=contact_id, text=text)
            elapsed = time.time() - started
            meter.record(contact_id, elapsed, vector.dims, sha256_text(text))
            with query_vector_log.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "contact_id": contact_id,
                            "text_sha256": sha256_text(text),
                            "dims": vector.dims,
                            "values": list(vector.values),
                        }
                    )
                    + "\n"
                )
            return tuple(vector.values)

    facet_repr_by_id = {
        facet.facet_id: facet.representation for facet in snapshot.facets
    }
    jitter_text = facet_repr_by_id[sorted(facet_vector_table)[0]]
    with embed_lock:
        meter.charge("jitter:start")
        t0 = time.time()
        jitter_start = emb_client.embed_text(contact_id="jitter:start", text=jitter_text)
        meter.record("jitter:start", time.time() - t0, jitter_start.dims, sha256_text(jitter_text))
    log("embedding sidecar verified (surface encode-only; jitter start embedded)")

    # ---- serving telemetry (NOT_AVAILABLE-tolerant) -----------------------
    sampler = resolve_resource_sampler(slots_url=f"http://127.0.0.1:{DECODER_PORT}/slots")
    sampler.start()
    sampler.begin_request_window()

    arm_results: dict[str, object] = {}
    winner_labels: dict[str, str | None] = {}
    outcome_status = "ABORTED"
    contact_total = 0
    canary_fail_message: str | None = None
    sentinel_trip_message: str | None = None
    blend_sentinel: DecodeRateSentinel | None = None
    blend_buffer: TraceBuffer | None = None
    micro_run_sink_ids: dict[str, frozenset] = {}
    main_sink_ids: frozenset = frozenset()
    flight_started = time.time()
    metered_client = CoreCeilingClient(client, ATTEMPT_CORE_CEILING)

    def flush_partial_blend() -> None:
        """Durable-first discipline: push whatever the BLEND buffer holds into
        the main client sink BEFORE anything else on an abort path."""

        nonlocal main_sink_ids
        if blend_buffer is None or not blend_buffer.records:
            return
        partial_ids = [record_id for _, record_id, _ in blend_buffer.records]
        try:
            client.flush_trace_buffer(blend_buffer)
            main_sink_ids = main_sink_ids | frozenset(partial_ids)
            flight["blend_partial_flush"] = {"flushed_records": len(partial_ids)}
            log(
                f"durable-first: {len(partial_ids)} partial BLEND trace records "
                "flushed into the main sink"
            )
        except Exception as flush_error:  # noqa: BLE001 — report, never mask
            flight["blend_partial_flush"] = {"error": repr(flush_error)}
            log(f"durable-first partial flush FAILED: {flush_error!r}")

    try:
        # ---------------- M0 controller factory (canary/resend micro-runs) --
        def m0_factory(sample_id: str):
            return KbAlphaBlendController(
                snapshot=None,
                query_vectors={},
                facet_vectors=lambda facet_id: {},
                normalizer=default_label_normalizer,
                ranker=rank_wcos_prior_agree_factory(
                    RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)
                ),
                fuser=fuse_supplyfilter_factory(FuseKnobs(tau=1.0, m=1, c=1, top_l=1)),
                alpha=0.5,
                top_k_per_dimension=1,
            )

        log(
            "ARM M0 CONSUMED from ROUND-0 SEALED SCORES "
            f"({ROUND0_SCORES_SHA256[:12]}…): zero new contacts, never re-flown"
        )

        # ---------------- Decode-speed CANARY (before arm BLEND) ----------
        canary_samples = adapter.load_split("DEV-100-CANARY-2")
        canary_ids = [sample.sample_id for sample in canary_samples]
        server_log_path = SESSION_DIR / "server.log"
        canary_log_offset = server_log_path.stat().st_size
        canary_registry = Registry("dev100 round1 canary controller")
        canary_registry.register(M0_POLICY_ID, m0_factory)
        canary_buffer = TraceBuffer(plan.run_id)
        log(
            f"CANARY START: {len(canary_samples)} single-slot direct-decode "
            f"contacts on {canary_ids} (timing only; PASS < "
            f"{CANARY_MS_PER_TOKEN_PASS} ms/token generation)"
        )
        canary_started = time.time()
        canary_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=metered_client,
            split_id="DEV-100-CANARY-2",
            knowledge_snapshot=snapshot,
            speech_packet_bindings={
                sample_id: packet_bindings[sample_id] for sample_id in canary_ids
            },
            controller_policy_id=M0_POLICY_ID,
            max_contacts=1,
            slot_count=1,
            queue_depth=1,
            trace_sink=canary_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=canary_registry,
        )
        canary_sink = TraceSink(run_dir / "canary-trace", plan.run_id)
        canary_record_ids = flush_micro_run_buffer(canary_buffer, canary_sink, "canary")
        canary_manifest_hash = canary_sink.close()
        micro_run_sink_ids["canary"] = frozenset(canary_record_ids)
        log(
            f"canary trace flushed into its OWN sink: {len(canary_record_ids)} "
            f"records at {run_dir / 'canary-trace'} (manifest {canary_manifest_hash[:12]}...)"
        )
        canary_contacts = sum(
            len(result.contacts) for result in canary_summary.results
        )
        contact_total += canary_contacts
        canary_wall = time.time() - canary_started
        time.sleep(1.0)  # let the server flush its print_timing lines
        with server_log_path.open("rb") as log_handle:
            log_handle.seek(canary_log_offset)
            canary_timing = parse_print_timing(log_handle.read())
        generation_rows = canary_timing["generation"]
        canary_record: dict[str, object] = {
            "sample_ids": canary_ids,
            "contacts": canary_contacts,
            "wall_seconds": round(canary_wall, 3),
            "pass_threshold_ms_per_token": CANARY_MS_PER_TOKEN_PASS,
            "generation": generation_rows,
            "prompt_eval": canary_timing["prompt_eval"],
            "response_sha256_vs_attempt1_m0": {
                result.sample_id: {
                    "response_sha256": sha256_text(result.final_response_text),
                    "byte_identical_to_attempt1": sha256_text(
                        result.final_response_text
                    )
                    == a1_m0_response_sha[result.sample_id],
                }
                for result in canary_summary.results
            },
            "note": (
                "responses never read semantically: sha256 + server "
                "print_timing descriptives only, per the registered canary "
                "semantics (attempt-3 registration, carried to round 1; the "
                "service is the SAME BASE-build instance attempt 6 proved "
                "byte-identical to attempt-1 M0)"
            ),
            "trace": {
                "sink_dir": str(run_dir / "canary-trace"),
                "record_ids": len(canary_record_ids),
                "namespace": "canary/",
                "manifest_hash": canary_manifest_hash,
            },
        }
        flight["canary"] = canary_record
        save_flight()
        if len(generation_rows) != canary_contacts:
            raise CanaryFail(
                f"canary timing lines incomplete: {len(generation_rows)} "
                f"generation print_timing rows for {canary_contacts} contacts; "
                "refusing to fly BLEND without a decode-speed verdict"
            )
        worst_rate = max(row["ms_per_token"] for row in generation_rows)
        canary_record["worst_generation_ms_per_token"] = worst_rate
        canary_record["passed"] = worst_rate < CANARY_MS_PER_TOKEN_PASS
        save_flight()
        if not canary_record["passed"]:
            raise CanaryFail(
                "decode-speed canary FAILED: generation rates "
                f"{[row['ms_per_token'] for row in generation_rows]} ms/token "
                f"vs the registered pass threshold {CANARY_MS_PER_TOKEN_PASS}; "
                "arm BLEND is NOT flown; the service is left up"
            )
        log(
            "CANARY PASS: generation "
            f"{[row['ms_per_token'] for row in generation_rows]} ms/token "
            f"(worst {worst_rate}), prompt-eval "
            f"{[row['ms_per_token'] for row in canary_timing['prompt_eval']]} "
            "ms/token"
        )

        first_run_sha = {
            result.sample_id: sha256_text(result.final_response_text)
            for result in canary_summary.results
        }
        same_build_identical = all(
            row["byte_identical_to_attempt1"]
            for row in canary_record["response_sha256_vs_attempt1_m0"].values()
        )
        canary_record["byte_identical_to_attempt1_m0"] = same_build_identical
        if same_build_identical:
            canary_record["decode_divergence"] = None
            log(
                "canary bytes MATCH attempt-1 M0 (sixth cross-instance "
                "confirmation, same build as the attempt-6 proof): the "
                "M0/BLEND pairing is unconditionally sound"
            )
        else:
            log(
                "canary bytes DIFFER from attempt-1 M0 (UNEXPECTED on the "
                "same build attempt 6 proved identical): re-running the pair "
                "once — within-build determinism is REQUIRED"
            )
            rerun_buffer = TraceBuffer(plan.run_id)
            rerun_registry = Registry("dev100 round1 canary rerun controller")
            rerun_registry.register(M0_POLICY_ID, m0_factory)
            rerun_log_offset = server_log_path.stat().st_size
            rerun_summary = run_speech_native_agent_loop(
                data_root=root,
                plan=plan,
                adapter=adapter,
                core_client=metered_client,
                split_id="DEV-100-CANARY-2",
                knowledge_snapshot=snapshot,
                speech_packet_bindings={
                    sample_id: packet_bindings[sample_id]
                    for sample_id in canary_ids
                },
                controller_policy_id=M0_POLICY_ID,
                max_contacts=1,
                slot_count=1,
                queue_depth=1,
                trace_sink=rerun_buffer,
                agent_executor_id="openjiuwen-workflow-v1",
                decoding_params=DECODING_PARAMS,
                controller_registry=rerun_registry,
            )
            rerun_sink = TraceSink(run_dir / "canary-rerun-trace", plan.run_id)
            rerun_record_ids = flush_micro_run_buffer(
                rerun_buffer, rerun_sink, "canary-rerun"
            )
            rerun_manifest_hash = rerun_sink.close()
            micro_run_sink_ids["canary_rerun"] = frozenset(rerun_record_ids)
            rerun_contacts = sum(
                len(result.contacts) for result in rerun_summary.results
            )
            contact_total += rerun_contacts
            time.sleep(1.0)
            with server_log_path.open("rb") as log_handle:
                log_handle.seek(rerun_log_offset)
                rerun_timing = parse_print_timing(log_handle.read())
            rerun_rows = rerun_timing["generation"]
            rerun_sha = {
                result.sample_id: sha256_text(result.final_response_text)
                for result in rerun_summary.results
            }
            within_build_identical = rerun_sha == first_run_sha
            canary_record["rerun"] = {
                "contacts": rerun_contacts,
                "generation": rerun_rows,
                "prompt_eval": rerun_timing["prompt_eval"],
                "response_sha256": dict(sorted(rerun_sha.items())),
                "within_build_byte_identical_to_first_run": (
                    within_build_identical
                ),
                "trace": {
                    "sink_dir": str(run_dir / "canary-rerun-trace"),
                    "record_ids": len(rerun_record_ids),
                    "namespace": "canary-rerun/",
                    "manifest_hash": rerun_manifest_hash,
                },
            }
            canary_record["decode_divergence"] = {
                "attempt1_m0_response_sha256": {
                    sample_id: a1_m0_response_sha[sample_id]
                    for sample_id in canary_ids
                },
                "round1_response_sha256": dict(sorted(first_run_sha.items())),
                "note": (
                    "bytes differ from attempt-1 M0 on the SAME build that "
                    "matched in attempt 6 — recorded as a caveat traveling "
                    "with the round report; per-build determinism is "
                    "confirmed by the re-run"
                ),
            }
            save_flight()
            if len(rerun_rows) != rerun_contacts:
                raise CanaryFail(
                    "canary re-run timing lines incomplete: "
                    f"{len(rerun_rows)} generation rows for {rerun_contacts} "
                    "contacts; refusing to fly BLEND without a verdict"
                )
            rerun_worst = max(row["ms_per_token"] for row in rerun_rows)
            if rerun_worst >= CANARY_MS_PER_TOKEN_PASS:
                raise CanaryFail(
                    "canary re-run FAILED the timing gate: "
                    f"{[row['ms_per_token'] for row in rerun_rows]} ms/token "
                    f"vs the registered threshold {CANARY_MS_PER_TOKEN_PASS}; "
                    "arm BLEND is NOT flown; the service is left up"
                )
            if not within_build_identical:
                raise CanaryFail(
                    "WITHIN-build determinism FAILED: the canary re-run "
                    "responses are not byte-identical to the first run on "
                    "the SAME binary; per-build determinism is a registered "
                    "requirement — stopping fail-closed before arm BLEND"
                )
            log(
                "canary re-run PASS: within-build determinism confirmed "
                f"(worst {rerun_worst} ms/token); decode-divergence recorded "
                "as a caveat"
            )
        save_flight()

        # ---------------- Arm BLEND (ROUND-1 knobs: tau 0.65) --------------
        cells = {sample.sample_id: LazyQueryVector() for sample in samples}
        kb_factory = make_kb_alpha_blend_controller_factory(
            snapshot=snapshot,
            query_vectors_by_sample={
                sample_id: {"content": cell} for sample_id, cell in cells.items()
            },
            facet_vectors=facet_vectors,
            normalizer=default_label_normalizer,
            rank_weights=ROUND1_WEIGHTS,
            fuse_knobs=ROUND1_FUSE,
            alpha=ROUND1_ALPHA,
            top_k_per_dimension=ROUND1_TOP_K,
        )
        blend_controllers: dict[str, RuntimeEmbeddedBlendController] = {}

        def blend_factory(sample_id: str):
            controller = RuntimeEmbeddedBlendController(
                kb_factory(sample_id),
                sample_id=sample_id,
                cell=cells[sample_id],
                embed=embed_query_text,
            )
            blend_controllers[sample_id] = controller
            return controller

        blend_registry = Registry("dev100 round1 BLEND controller")
        blend_registry.register(CONTROLLER_POLICY_ID, blend_factory)
        log(
            f"ARM BLEND START (tau={ROUND1_TAU}): <= {ATTEMPT_CORE_CEILING} core "
            f"contacts (hard meter) + <= {ATTEMPT_TOOL_CEILING} embedding tool "
            f"contacts; decode-rate sentinel ARMED (rolling median over "
            f"{SENTINEL_WINDOW_CONTACTS} contacts > "
            f"{SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT:.0f} ms/token aborts)"
        )
        blend_buffer = TraceBuffer(plan.run_id)
        blend_log_offset = server_log_path.stat().st_size
        blend_sentinel = DecodeRateSentinel(server_log_path, blend_log_offset)
        metered_client.arm_sentinel(blend_sentinel)
        blend_started = time.time()
        blend_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=metered_client,
            split_id=SPLIT_ID,
            knowledge_snapshot=snapshot,
            speech_packet_bindings=packet_bindings,
            controller_policy_id=CONTROLLER_POLICY_ID,
            max_contacts=2,
            slot_count=server_np,
            queue_depth=server_np,
            trace_sink=blend_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=blend_registry,
        )
        metered_client.arm_sentinel(None)
        blend_contacts = sum(len(result.contacts) for result in blend_summary.results)
        contact_total += blend_contacts
        blend_record_ids = [record_id for _, record_id, _ in blend_buffer.records]
        flight["core_contacts_total_pre_flush"] = contact_total
        save_flight()
        client.flush_trace_buffer(blend_buffer)
        main_sink_ids = frozenset(blend_record_ids)
        log(
            f"ARM BLEND flushed FIRST into the main sink: {len(blend_record_ids)} "
            "records"
        )
        log(f"ARM BLEND DONE in {time.time() - blend_started:.1f}s: {blend_contacts} contacts")
        arm_results["BLEND"] = blend_summary
        winner_labels = {
            sample_id: controller.last_winner_label
            for sample_id, controller in blend_controllers.items()
        }
        time.sleep(1.0)
        with server_log_path.open("rb") as log_handle:
            log_handle.seek(blend_log_offset)
            blend_timing = parse_print_timing(log_handle.read())
        gen_rates = sorted(row["ms_per_token"] for row in blend_timing["generation"])
        flight["blend_print_timing"] = {
            "generation_rows": len(gen_rates),
            "ms_per_token_min": gen_rates[0] if gen_rates else None,
            "ms_per_token_median": gen_rates[len(gen_rates) // 2] if gen_rates else None,
            "ms_per_token_max": gen_rates[-1] if gen_rates else None,
        }
        save_flight()

        # ---------------- identical-prompt resend pair ----------------
        # Round-1 form (per-round discipline): response A is attempt-1's M0
        # recorded hash for the first sample (hash read, no text); response B
        # is a fresh single-slot re-issue of the byte-identical prompt on the
        # SAME BASE-build service instance attempt 6 flew.
        resend_record: dict[str, object]
        if contact_total + 1 <= ATTEMPT_CORE_CEILING:
            first_sample = samples[0]
            resend_registry = Registry("dev100 round1 resend controller")
            resend_registry.register(M0_POLICY_ID, m0_factory)
            resend_buffer = TraceBuffer(plan.run_id)
            resend_summary = run_speech_native_agent_loop(
                data_root=root,
                plan=plan,
                adapter=adapter,
                core_client=metered_client,
                split_id="DEV-100-RESEND-1",
                knowledge_snapshot=snapshot,
                speech_packet_bindings={
                    first_sample.sample_id: packet_bindings[first_sample.sample_id]
                },
                controller_policy_id=M0_POLICY_ID,
                max_contacts=1,
                slot_count=1,
                queue_depth=1,
                trace_sink=resend_buffer,
                agent_executor_id="openjiuwen-workflow-v1",
                decoding_params=DECODING_PARAMS,
                controller_registry=resend_registry,
            )
            resend_sink = TraceSink(run_dir / "resend-trace", plan.run_id)
            resend_record_ids = flush_micro_run_buffer(
                resend_buffer, resend_sink, "resend"
            )
            resend_manifest_hash = resend_sink.close()
            micro_run_sink_ids["resend"] = frozenset(resend_record_ids)
            log(
                f"resend trace flushed into its OWN sink: {len(resend_record_ids)} "
                f"records at {run_dir / 'resend-trace'} "
                f"(manifest {resend_manifest_hash[:12]}...)"
            )
            contact_total += 1
            base_sha = a1_m0_response_sha[first_sample.sample_id]
            resend_text = resend_summary.results[0].final_response_text
            resend_record = {
                "flown": True,
                "sample_id": first_sample.sample_id,
                "server_np": server_np,
                "response_a_sha256": base_sha,
                "response_b_sha256": sha256_text(resend_text),
                "byte_identical": base_sha == sha256_text(resend_text),
                "note": (
                    "byte-identical direct-decode PROMPT by construction: the SAME "
                    "assembly path (rails.runner._agent_messages over the same frozen "
                    "adapter/contract/packet/instruction inputs). Response A is "
                    "attempt-1's recorded M0 hash (ZERO-COPY build); response B is a "
                    "fresh single-slot decode on the SAME BASE-build service instance "
                    "attempt 6 flew — cross-build byte-determinism was proven at the "
                    "attempt-6 canary/resend, so byte identity is expected here. "
                    "sha256 equality only."
                ),
                "trace": {
                    "sink_dir": str(run_dir / "resend-trace"),
                    "record_ids": len(resend_record_ids),
                    "namespace": "resend/",
                    "manifest_hash": resend_manifest_hash,
                },
            }
            log(
                f"resend pair (sample {first_sample.sample_id}, -np {server_np}, "
                f"cross-instance): byte_identical={resend_record['byte_identical']}"
            )
        else:
            resend_record = {
                "flown": False,
                "reason": (
                    f"attempt core ceiling {ATTEMPT_CORE_CEILING} fully consumed by "
                    f"arm BLEND ({contact_total} contacts); the resend is skipped and "
                    "disclosed rather than breaching the registered ceiling"
                ),
            }
            log("resend SKIPPED: no core-contact headroom (disclosed)")
        flight["resend_pair"] = resend_record

        assert_zero_record_id_overlap({"main": main_sink_ids, **micro_run_sink_ids})
        flight["trace_isolation"] = {
            "main_sink_records": len(main_sink_ids),
            "canary_sink_records": len(micro_run_sink_ids.get("canary", frozenset())),
            "resend_sink_records": len(micro_run_sink_ids.get("resend", frozenset())),
            "zero_record_id_overlap_asserted": True,
            "flush_order": "canary (own sink) -> BLEND (main sink FIRST) -> resend (own sink)",
        }
        log(
            "trace isolation verified: zero record-id overlap across the "
            f"main ({len(main_sink_ids)}), canary "
            f"({len(micro_run_sink_ids.get('canary', frozenset()))}) and resend "
            f"({len(micro_run_sink_ids.get('resend', frozenset()))}) sinks"
        )
        outcome_status = "CONTACTS_COMPLETE"
    except CanaryFail as error:
        canary_fail_message = str(error)
        outcome_status = "CANARY_FAIL_STOP"
        log(f"CANARY FAIL: {canary_fail_message}")
    except DecodeRateSentinelTrip as error:
        sentinel_trip_message = str(error)
        outcome_status = "SENTINEL_ABORT_STOP"
        log(f"SENTINEL TRIP: {sentinel_trip_message}")
        flush_partial_blend()
    except Exception as error:
        if blend_sentinel is not None and blend_sentinel.tripped is not None:
            sentinel_trip_message = (
                f"{blend_sentinel.tripped} (surfaced wrapped as: {error!r})"
            )
            outcome_status = "SENTINEL_ABORT_STOP"
            log(f"SENTINEL TRIP (wrapped): {sentinel_trip_message}")
            flush_partial_blend()
        else:
            flush_partial_blend()
            raise
    finally:
        sampler.end_request_window()
        sampler.stop()
        telemetry = dict(sampler.summary())
        flight["serving_descriptives"] = telemetry
        flight["core_contacts_total"] = contact_total
        flight["sentinel"] = (
            blend_sentinel.summary() if blend_sentinel is not None else None
        )
        flight["outcome_status"] = outcome_status
        save_flight()

        # jitter end + embedding accounting + sidecar stop (always) ----------
        try:
            with embed_lock:
                meter.charge("jitter:end")
                t0 = time.time()
                jitter_end = emb_client.embed_text(contact_id="jitter:end", text=jitter_text)
                meter.record("jitter:end", time.time() - t0, jitter_end.dims, sha256_text(jitter_text))
            dot = sum(a * b for a, b in zip(jitter_start.values, jitter_end.values))
            na = sum(a * a for a in jitter_start.values) ** 0.5
            nb = sum(b * b for b in jitter_end.values) ** 0.5
            flight["embedding_jitter_pair"] = {
                "cosine": dot / (na * nb),
                "bit_identical": tuple(jitter_start.values) == tuple(jitter_end.values),
                "text_sha256": sha256_text(jitter_text),
            }
        except Exception as error:  # noqa: BLE001 — teardown reports, never masks
            flight["embedding_jitter_pair"] = {"error": repr(error)}
        try:
            emb_contacts = emb_client.close()
            flight["embedding_accounting"] = {
                "tool_contacts": meter.count,
                "client_contact_count": emb_contacts.get("contact_count"),
                "ceiling": ATTEMPT_TOOL_CEILING,
                "latency_seconds_total": round(meter.latency_total, 3),
            }
        except Exception as error:  # noqa: BLE001
            flight["embedding_accounting"] = {"error": repr(error), "tool_contacts": meter.count}
        try:
            stop = stop_session(
                emb_session,
                runtime_receipt=emb_runtime_receipt,
                runtime_root=Path("/home/chao"),
                receipt_path=run_dir / "session-qwen3-emb-cpu.stop-receipt.json",
                force_after_timeout=True,
            )
            flight["embedding_session_stop"] = {
                "termination_signal": stop.get("termination_signal"),
                "forced": stop.get("forced"),
            }
            log(f"embedder sidecar stopped ({stop.get('termination_signal')}, forced={stop.get('forced')})")
        except Exception as error:  # noqa: BLE001
            flight["embedding_session_stop"] = {"error": repr(error)}
            log(f"embedder sidecar stop FAILED: {error!r}")
        save_flight()

    # ---- core client receipt (trace manifest + cost) ----------------------
    timings = client.timings
    contact_latency_total = sum(t.latency_seconds for t in timings) if timings else 0.0
    core_receipt = client.close()
    flight["core_client"] = {
        "trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
        "cost": core_receipt.get("cost"),
        "request_count": len(timings),
        "contact_latency_seconds_total": round(contact_latency_total, 3),
    }
    flight["gpu_active_hours_contact_basis"] = round(contact_latency_total / 3600.0, 6)
    flight["wall_seconds"] = round(time.time() - flight_started, 1)
    save_flight()
    log(
        f"core client closed: {len(timings)} requests, contact latency "
        f"{contact_latency_total:.1f}s, wall {flight['wall_seconds']}s"
    )

    # ---- canary-fail hard stop: NO scoring, NO gold, service left up ------
    if canary_fail_message is not None:
        OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
        stop_record = {
            "schema": "saea-dev100-round1-canary-stop-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": RUN_ID,
            "round_index": ROUND_INDEX,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "outcome": "CANARY_FAIL_STOP",
            "verbatim": canary_fail_message,
            "canary": flight.get("canary"),
            "mid_flight_clock_samples_windows_side": read_clock_samples(root),
            "spend": {
                "round1_core_contacts": contact_total,
                "round1_tool_contacts": meter.count,
                "core_client": flight["core_client"],
            },
            "boundary": (
                "gold never opened; no response read semantically; round 1 is "
                "NOT sealed and NOT scored; the resident service and keepalive "
                "are left up for the coordinator's decision"
            ),
        }
        stop_path = OUT_CHECK_DIR / "round1-canary-stop.json"
        stop_path.write_text(
            json.dumps(stop_record, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        flight["outcome_status"] = "CANARY_FAIL_STOP"
        flight["canary_stop_path"] = str(stop_path)
        save_flight()
        log(f"CANARY-FAIL STOP RECORD written: {stop_path}")
        log(f"VERBATIM: {canary_fail_message}")
        return 4

    # ---- sentinel-trip hard stop: durable data flushed, NO scoring --------
    if sentinel_trip_message is not None:
        OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
        sentinel_record = {
            "schema": "saea-dev100-round1-sentinel-abort-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": RUN_ID,
            "round_index": ROUND_INDEX,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "outcome": "SENTINEL_ABORT_STOP",
            "verbatim": sentinel_trip_message,
            "sentinel": flight.get("sentinel"),
            "mid_flight_clock_samples_windows_side": read_clock_samples(root),
            "registered_semantics": {
                "window_contacts": SENTINEL_WINDOW_CONTACTS,
                "abort_threshold_ms_per_token": SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT,
                "metric": (
                    "server print_timing generation ms/token (content-free), "
                    "read per completed BLEND contact from the tracked "
                    "server-log offset; rolling median, strict >"
                ),
            },
            "canary": flight.get("canary"),
            "durable_flush": {
                "canary_sink": flight.get("canary", {}).get("trace")
                if isinstance(flight.get("canary"), dict)
                else None,
                "blend_partial_flush": flight.get("blend_partial_flush"),
            },
            "spend": {
                "round1_core_contacts": contact_total,
                "round1_tool_contacts": meter.count,
                "core_client": flight["core_client"],
            },
            "boundary": (
                "gold never opened; no response read semantically; round 1 is "
                "NOT sealed and NOT scored; everything durable was flushed at "
                "the trip (partial BLEND buffer into the main sink, canary in "
                "its own sink); the resident service and keepalive are left up "
                "for the coordinator's decision. NOTE: a sentinel trip on the "
                "BASE build would REOPEN the serving question the attempt-6 "
                "landing closed — report verbatim"
            ),
        }
        sentinel_path = OUT_CHECK_DIR / "round1-sentinel-abort.json"
        sentinel_path.write_text(
            json.dumps(sentinel_record, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        flight["outcome_status"] = "SENTINEL_ABORT_STOP"
        flight["sentinel_abort_path"] = str(sentinel_path)
        save_flight()
        log(f"SENTINEL ABORT RECORD written: {sentinel_path}")
        log(f"VERBATIM: {sentinel_trip_message}")
        return 5

    # ---- POST-SEAL scoring: gold + round-0 sealed artifacts open HERE -----
    # ONE gold opening for the whole round: round-1 BLEND is scored fresh;
    # arm M0 and BLEND-round-0 per-sample correctness are consumed from
    # round-0's SEALED scoring artifact (re-hashed against the registration
    # pins immediately before parsing).
    log("ALL ROUND-1 ARMS SEALED — opening devel gold + round-0 sealed scores scoring-side")
    if sha256_file(round0_scores_path) != ROUND0_SCORES_SHA256:
        raise SystemExit("round-0 scores mutated between preflight and scoring; refusing")
    if sha256_file(round0_report_path) != ROUND0_REPORT_SHA256:
        raise SystemExit("round-0 report mutated between preflight and scoring; refusing")
    round0_report = json.loads(round0_report_path.read_text(encoding="utf-8"))
    round0_scores = json.loads(round0_scores_path.read_text(encoding="utf-8"))
    sample_ids = {s.sample_id for s in samples}
    m0_rows = round0_scores["M0"]
    r0_blend_rows = round0_scores["BLEND"]
    if set(m0_rows) != sample_ids or set(r0_blend_rows) != sample_ids:
        raise SystemExit("round-0 sealed scores do not cover the DEV-100 split exactly")
    m0_correct = {sid for sid, row in m0_rows.items() if row["correct"]}
    r0_blend_correct = {sid for sid, row in r0_blend_rows.items() if row["correct"]}
    if len(m0_correct) != round0_report["arms"]["M0"]["correct_count"]:
        raise SystemExit("round-0 M0 correct count disagrees with the sealed report")
    if len(r0_blend_correct) != round0_report["arms"]["BLEND"]["correct_count"]:
        raise SystemExit("round-0 BLEND correct count disagrees with the sealed report")
    if sorted(r0_blend_correct - m0_correct) != round0_report["wrong_to_correct_sample_ids"]:
        raise SystemExit("round-0 W->C list disagrees with the sealed report")
    if sorted(m0_correct - r0_blend_correct) != round0_report["correct_to_wrong_sample_ids"]:
        raise SystemExit("round-0 C->W list disagrees with the sealed report")
    log(
        "round-0 sealed authorities parsed and cross-checked: M0 "
        f"{len(m0_correct)}/100, BLEND-r0 {len(r0_blend_correct)}/100, lists equal"
    )

    scorer = SlurpAdapter(lock, root, repo_root=REPO)
    sample_by_id = {sample.sample_id: sample for sample in samples}
    scores: dict[str, dict[str, dict[str, object]]] = {}

    blend_summary = arm_results["BLEND"]
    blend_scores: dict[str, dict[str, object]] = {}
    for result in blend_summary.results:
        metrics = dict(scorer.score(sample_by_id[result.sample_id], result.final_response_text))
        blend_scores[result.sample_id] = {
            "correct": bool(metrics.get("scenario_action_exact")),
            "scenario_exact": bool(metrics.get("scenario_exact")),
            "action_exact": bool(metrics.get("action_exact")),
            "parsed": metrics.get("parsed"),
            "slot_f1_exact_f1": metrics.get("slot_f1_exact_f1"),
            "contacts": len(result.contacts),
            "response_sha256": sha256_text(result.final_response_text),
            "winner_label_present": winner_labels.get(result.sample_id) is not None,
        }
    if set(blend_scores) != sample_ids:
        raise SystemExit("round-1 BLEND results do not cover the split")
    scores["BLEND_ROUND1"] = blend_scores
    scores["M0_SEALED_ROUND0"] = {
        sid: dict(row) for sid, row in sorted(m0_rows.items())
    }

    # Cross-attempt direct-contact byte agreement (serving descriptive).
    direct_agreement = {
        sample_id: (
            controller.direct_response_sha256 is not None
            and controller.direct_response_sha256 == a1_m0_response_sha[sample_id]
        )
        for sample_id, controller in blend_controllers.items()
    }
    direct_agree_count = sum(1 for same in direct_agreement.values() if same)

    outputs_path = run_dir / "round1-outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as sink:
        for result in blend_summary.results:
            sink.write(
                json.dumps(
                    {
                        "arm": "BLEND_ROUND1",
                        "sample_id": result.sample_id,
                        "final_response_text": result.final_response_text,
                        "contacts": len(result.contacts),
                        "slot_ids": [record.slot_id for record in result.contacts],
                        "winner_label": winner_labels.get(result.sample_id),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    log(f"outputs written: {outputs_path}")

    # ---- per-sample movement analysis ------------------------------------
    r1_correct = {sid for sid, row in blend_scores.items() if row["correct"]}
    wrong_to_correct = sorted(r1_correct - m0_correct)
    correct_to_wrong = sorted(m0_correct - r1_correct)
    r0_w2c = set(round0_report["wrong_to_correct_sample_ids"])
    r0_c2w = set(round0_report["correct_to_wrong_sample_ids"])
    retained_primary_ids = sorted(
        sid for sid, row in blend_scores.items() if row["contacts"] == 1
    )
    dispatched_count = sum(1 for row in blend_scores.values() if row["contacts"] == 2)
    response_changed_vs_r0 = sorted(
        sid
        for sid in sample_ids
        if blend_scores[sid]["response_sha256"] != r0_blend_rows[sid]["response_sha256"]
    )
    audio_seconds_metered = None
    cost = flight["core_client"]["cost"]
    if isinstance(cost, Mapping):
        audio_seconds_metered = cost.get("audio_seconds_used")

    round_report = {
        "schema": "saea-dev100-round1-report-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "round_index": ROUND_INDEX,
        "attempt_id": attempt_id,
        "generated_at": iso_now(),
        "authority": (
            "docs/readiness/2026-08-23-dev100-campaign-preregistration.md including "
            "amendment 5b and the owner-approved section-4 ceiling amendment "
            "(2026-08-24, commit 121bdc08: core 1,800 -> 2,500, audio-s 2,400 -> "
            "5,500); campaign exposure row SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN "
            "ROUND-1 registration (single-variable tau knob; run-cumulative plan "
            "950 calls / 2,450 audio-s; sealed round-0 authorities pinned "
            "byte-wise; sentinel + micro-run trace isolation + clock sampling "
            "carried flight-proven from attempt 6)"
        ),
        "refused_takeoffs": REFUSED_TAKEOFFS,
        "round0_citation": {
            "report_path": ROUND0_REPORT_RELPATH,
            "report_sha256": ROUND0_REPORT_SHA256,
            "scores_sha256": ROUND0_SCORES_SHA256,
            "sealed_results": "M0 48/100; BLEND(tau .5) 63/100; W->C 26; C->W 11; evidence fired 100/100",
        },
        "hosting": dict(HOSTING),
        "config_hash": composed.config_hash,
        "server_np": server_np,
        "decoder_session_receipt_sha256": measured_receipt,
        "gpu_preflight": flight["gpu_preflight"],
        "round1_knobs": {
            "alpha": ROUND1_ALPHA,
            "rank_weight_id": "rrf",
            "evidence_variant": "rank+prior+agreement",
            "tau": ROUND1_TAU,
            "top_k_per_dimension": ROUND1_TOP_K,
            "fusion": {"m": ROUND1_FUSE.m, "c": ROUND1_FUSE.c, "l": ROUND1_FUSE.top_l},
            "rank_weights": {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2},
            "prior_source": "train",
            "m11_pair_boundary_stage": False,
            "value_vectors": "SEALED (never loaded)",
            "percept_admission": "facet-side",
            "knob_change_vs_round0": {
                "tau": {"from": ROUND0_TAU_FOR_RECORD, "to": ROUND1_TAU},
                "single_variable": True,
                "rationale": (
                    "tighten percept admission to attack the round-0 damage "
                    "channel (11 C->W); expected trade: retain-primary fires "
                    "for the first time, some W->C repairs lost"
                ),
            },
        },
        "arms": {
            "M0": {
                "accuracy_scenario_action_exact": len(m0_correct) / 100.0,
                "correct_count": len(m0_correct),
                "contacts": 0,
                "source": (
                    "ROUND-0 SEALED per-sample scores (never re-flown; "
                    f"scores sha256 {ROUND0_SCORES_SHA256})"
                ),
            },
            "BLEND_ROUND1": {
                "accuracy_scenario_action_exact": len(r1_correct) / 100.0,
                "correct_count": len(r1_correct),
                "contacts": sum(row["contacts"] for row in blend_scores.values()),
                "evidence_contact_dispatched_samples": dispatched_count,
                "retain_primary_samples": len(retained_primary_ids),
                "parsed_count": sum(1 for row in blend_scores.values() if row["parsed"]),
                "embedding_tool_contacts": flight["embedding_accounting"].get("tool_contacts"),
            },
            "BLEND_ROUND0_FOR_REFERENCE": {
                "accuracy_scenario_action_exact": len(r0_blend_correct) / 100.0,
                "correct_count": len(r0_blend_correct),
                "source": "ROUND-0 SEALED per-sample scores",
            },
        },
        "wrong_to_correct_sample_ids": wrong_to_correct,
        "correct_to_wrong_sample_ids": correct_to_wrong,
        "vs_round0_blend": {
            "net_delta_correct_samples": len(r1_correct) - len(r0_blend_correct),
            "round0_correct_now_wrong": sorted(r0_blend_correct - r1_correct),
            "round0_wrong_now_correct": sorted(r1_correct - r0_blend_correct),
            "round0_w2c_retained": sorted(r0_w2c & r1_correct),
            "round0_w2c_lost": sorted(r0_w2c - r1_correct),
            "round0_c2w_repaired": sorted(r0_c2w & r1_correct),
            "round0_c2w_still_wrong": sorted(r0_c2w - r1_correct),
            "final_response_sha_changed_sample_ids": response_changed_vs_r0,
            "final_response_sha_changed_count": len(response_changed_vs_r0),
            "note": (
                "per-sample vs the round-0 sealed BLEND arm (tau .5). "
                "round0_c2w_repaired counts round-0 damage samples that are "
                "correct under tau .65; round0_w2c_lost counts round-0 repairs "
                "lost to the tighter admission"
            ),
        },
        "blend_decisions": {
            "evidence_contact_dispatched_samples": dispatched_count,
            "retain_primary_samples": len(retained_primary_ids),
            "retained_primary_sample_ids": retained_primary_ids,
            "winner_label_present_samples": sum(
                1 for label in winner_labels.values() if label is not None
            ),
        },
        "cross_attempt_direct_agreement": {
            "detail": (
                "per-sample sha256 equality between this round's BLEND "
                "direct-decode responses and attempt-1's reused M0 responses "
                "(byte-identical prompts; 8-slot concurrent serving "
                "descriptive, computed hash-to-hash; attempt-6 measured "
                "78/100 on the same service)"
            ),
            "agree_count": direct_agree_count,
            "disagree_sample_ids": sorted(
                sample_id for sample_id, same in direct_agreement.items() if not same
            ),
        },
        "deviations": [
            {
                "id": "m0-arm-consumed-from-round0-seal",
                "kind": "successor semantics, registered pre-takeoff in the campaign row",
                "detail": (
                    "Arm M0 was not re-flown in round 1: its per-sample "
                    "correctness comes from round-0's sealed scoring artifact "
                    f"(round0-scores.json, sha256 {ROUND0_SCORES_SHA256}), "
                    "cross-checked against the sealed round-0 report "
                    f"({ROUND0_REPORT_SHA256}) at the single scoring-side "
                    "opening. Zero new spend for the arm; the same M0 baseline "
                    "serves every round per the campaign design."
                ),
            }
        ],
        "spend_vs_ceilings": {
            "round1": {
                "core_contacts": {"used": contact_total, "attempt_ceiling": ATTEMPT_CORE_CEILING},
                "embedding_tool_contacts": {"used": meter.count, "attempt_ceiling": ATTEMPT_TOOL_CEILING},
                "metered_audio_seconds": {"used": audio_seconds_metered},
                "gpu_active_hours_contact_basis": flight["gpu_active_hours_contact_basis"],
            },
            "cumulative_plan_declaration": {
                "planned_model_calls_run_cumulative": PLANNED_MODEL_CALLS,
                "planned_speech_audio_seconds_run_cumulative": PLANNED_AUDIO_SECONDS,
                "note": (
                    "run-cumulative per core.model.adapter's enforcement across "
                    "all attempts of the run id (fresh sibling read per request); "
                    "covers the 688 calls / 1,824.52 audio-s durable for round 0 "
                    "plus this round's worst case"
                ),
            },
            "campaign_cumulative_incl_round0": {
                "core_contacts": ROUND0_CORE_CONTACTS + contact_total,
                "embedding_tool_contacts": ROUND0_TOOL_CONTACTS + meter.count,
                "metered_audio_seconds": (
                    ROUND0_AUDIO_SECONDS + audio_seconds_metered
                    if isinstance(audio_seconds_metered, (int, float))
                    else None
                ),
                "note": (
                    "round-0 durable cumulative (attempts 1-6: 688 core, 300 "
                    "tool, 1,824.5204999999996 audio-s) plus this round-1 attempt"
                ),
            },
            "campaign_ceilings_as_amended": {
                "core_contacts": CAMPAIGN_CEILING_CORE,
                "embedding_tool_contacts": CAMPAIGN_CEILING_TOOL,
                "metered_audio_seconds": CAMPAIGN_CEILING_AUDIO,
                "gpu_hours": CAMPAIGN_CEILING_GPU_HOURS,
                "amendment": (
                    "owner-approved at the round-0 sync (preregistration "
                    "section 4, commit 121bdc08): audio 2,400 -> 5,500, core "
                    "1,800 -> 2,500; tool and GPU-h unchanged"
                ),
            },
        },
        "stopping_rule_status": {
            "rule": (
                "converged: best-arm delta < 1 sample across 2 consecutive "
                "rounds with zero C->W growth; falsified: no arm beats direct "
                "after 3 completed rounds; hard cap 6"
            ),
            "completed_rounds_after_this": 2,
            "best_arm_delta_vs_prior_round": len(r1_correct) - len(r0_blend_correct),
            "beats_direct": max(len(r1_correct), len(r0_blend_correct)) > len(m0_correct),
            "note": (
                "evaluated by the coordinator between rounds; convergence "
                "needs TWO consecutive sub-1-sample rounds, so no trigger "
                "can fire before round 2's seal unless falsification applies"
            ),
        },
        "canary": flight.get("canary"),
        "blend_print_timing": flight.get("blend_print_timing"),
        "sentinel": flight.get("sentinel"),
        "blend_generation_rates_ms_per_token_in_observation_order": (
            list(blend_sentinel.observed_rates) if blend_sentinel is not None else None
        ),
        "mid_flight_clock_samples_windows_side": read_clock_samples(root),
        "trace_isolation": flight.get("trace_isolation"),
        "resend_pair": flight["resend_pair"],
        "serving_descriptives": flight["serving_descriptives"],
        "embedding_jitter_pair": flight.get("embedding_jitter_pair"),
        "core_client": flight["core_client"],
        "run_dir": str(run_dir),
        "hard_stop": (
            "Round 1 lands and STOPS. No round-2 flight, no knob change: the "
            "coordinator reports to the owner (per-arm accuracy, W->C/C->W, "
            "delta vs round 0, spend vs the amended ceilings, proposed "
            "next-round knobs) before anything flies."
        ),
    }
    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_CHECK_DIR / "round1-report.json"
    report_path.write_text(
        json.dumps(round_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (run_dir / "round1-scores.json").write_text(
        json.dumps(scores, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    flight["outcome_status"] = "ROUND1_LANDED"
    flight["report_path"] = str(report_path)
    save_flight()
    log(f"round-1 report written: {report_path}")
    log(f"report sha256: {sha256_file(report_path)}")
    log(
        f"SUMMARY: M0 {len(m0_correct)}/100 (sealed), BLEND-r1(tau {ROUND1_TAU}) "
        f"{len(r1_correct)}/100 (r0 was {len(r0_blend_correct)}), "
        f"W->C {len(wrong_to_correct)} (r0 26), C->W {len(correct_to_wrong)} (r0 11), "
        f"evidence dispatched {dispatched_count}/100, retain-primary "
        f"{len(retained_primary_ids)}, core contacts {contact_total}/"
        f"{ATTEMPT_CORE_CEILING} (attempt), tool {meter.count}/{ATTEMPT_TOOL_CEILING}, "
        f"direct byte-agreement {direct_agree_count}/100"
    )
    log("RESIDENT DECODER LEFT UP for round 2 (never stopped by this launcher)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
