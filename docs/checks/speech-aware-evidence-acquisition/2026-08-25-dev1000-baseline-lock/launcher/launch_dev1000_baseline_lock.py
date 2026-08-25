"""DEV-1000 BASELINE-LOCK two-arm launcher — exposure row
``SAEA-DEV1000-BASELINE-LOCK`` (bounded-discovery-probe), MECHANICAL FLIGHT
ONLY. The ladder's TERMINAL DEV TIER.

One parameterized launcher, one ARM per invocation (``--arm M0 | BLEND``),
each invocation minting its OWN attempt id with one-shot semantics per arm.

Lineage: the machinery is the flight-proven DEV-500 confirmatory launcher
(``../2026-08-24-dev500-confirmatory/launcher/launch_dev500_confirmatory.py``,
landed exit 0 on all four arms) — the parameterized multi-arm skeleton at
scale — with the delta retain-override grafted in from the flight-proven A4
launcher (``../2026-08-25-dev100-retain-override/launcher/
launch_dev100_retain_override.py``, landed exit 0 at commit 890adefc). The two
ABL control arms are EXCISED: the lock tier does not re-run ablations
(preregistration §3 — the DEV-500 confirmatory already established attribution
on an unexposed 400 with the same form; this tier tests SCALE-STABILITY).

Authority: ``docs/readiness/2026-08-24-dev1000-baseline-lock-preregistration.md``
and ``docs/readiness/2026-08-25-lock-candidate-selection.md``; machine-readable
contract ``configs/experiment/slurp-dev1000-baseline-lock-v1.json``.

* ARM M0 — prompt-matched direct decode, 1 contact per sample over the FULL
  DEV-1000 (1,000 loop contacts; in-session, removing the cross-build
  confound).
* ARM BLEND — the FROZEN v2 LOCK CANDIDATE over the FULL DEV-1000: the v1
  alpha-.45 cell PLUS the registered delta >= 0.14 retain-override on the
  dispatch rule (2-contact worst 2,000, expected ~1,400 at the projected ~40 %
  dispatch rate; content-dim query embedding of the trajectory's own direct
  answer via the CPU sidecar on 8082, <= 1,020 tool contacts; the
  identical-prompt resend pair flies on this arm).

SCOPE OF THE FLOWN POPULATION — read this before touching the arm tables. BOTH
arms fly ALL 1,000 samples. The LOCK STATISTIC covers only the 500 samples
UNEXPOSED at this tier (DEV-1000 minus DEV-500, receipt
``docs/receipts/probe-samples/DEV-1000-NEW500.json``); the exposed 500 are
scored separately as a secondary reading, exactly as the DEV-500 campaign did
with its nested 100. NO SUB-SELECTION HAPPENS AT FLIGHT TIME — the separately
registered one-touch read performs the partition over a sealed, already-flown
set. This launcher asserts the partition's integrity (NEW500 subset of the
flown ids, disjoint from DEV-500, union exact) and then flies everything.

MECHANICAL LANDING ONLY: this launcher NEVER opens gold, NEVER scores, and
computes NO accuracy. Response texts land opaque in the run dir for the
later, separately registered one-touch read. The lock candidate's knob table
(``configs/policy/kb-policy-v2-lock-candidate.json``) is byte-frozen: alpha
.45, tau .65, top-k 5, rrf .5/.3/.2, fusion m5/c2/l3, TRAIN priors, value
vectors SEALED, facet-side admission, f1060078 repair asserted as an
invariant, plus the delta >= 0.14 retain-override with its MANDATORY
disagreement condition. The override is implemented ENTIRELY LAUNCHER-SIDE
through ``rails.kb_policy``'s own pure functions and the ``normalizer``
keyword the REGISTERED controller factory already exposes; nothing under
``rails/`` or ``core/`` is modified, monkeypatched, or subclassed.

REGISTERED HONESTY: the delta bar was FIT on EXPOSED data (DEV-100 r4/r5 +
DEV-500 NEW400) and frozen 2026-08-25. The unexposed-500 read therefore
validates the bar AND confirms the cell in one touch — legitimate only because
the bar is frozen before the read and the fit is declared. Any post-freeze
change to the bar voids the lock registration.

Mandatory rails (all flight-proven, registered in the row): GPU preflight,
AttemptStore pre-takeoff inspection with a fail-closed prior+worst<=plan
guard, decode-speed canary per arm (byte compare vs the attempt-1 M0 hash
authority; one re-run on mismatch with required within-build identity),
in-flight decode-rate sentinel per arm (rolling median of 8 > 1,000 ms/token
aborts durable-first and STOPS THE MISSION), micro-run trace-sink isolation,
identical-prompt resend pair on BLEND, per-request prompt-reuse measurement,
Windows-side clock/VRAM sampling.

Run in WSL2 (systemd-run --user unit, immune to agent-session reaping;
PATH must include /usr/lib/wsl/lib for the in-script nvidia-smi)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python .../launch_dev1000_baseline_lock.py --arm M0 \
        --gpu-preflight <preflight.json>

Self-test (offline: stubbed timings, zero contacts, no service, no gate)::

    ... launch_dev1000_baseline_lock.py --self-test
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
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
    _DIRECT_CONTACT_ID,
    _EVIDENCE_CONTACT_ID,
    PRIOR_MASS_DIMENSIONS,
    FuseKnobs,
    KbAlphaBlendController,
    RankWeights,
    _cosine,
    _fused_label_scores,
    _label_identities,
    default_label_normalizer,
    fuse_supplyfilter_factory,
    make_kb_alpha_blend_controller_factory,
    multidim_recall,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    AgentStepTransition,
    FusionDecision,
    KnowledgeSnapshot,
    QueryState,
    RankResult,
    RankedFacet,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    AgentContactPlan,
    AgentLoopAdvance,
    run_speech_native_agent_loop,
)

# --------------------------------------------------------------------------
# Pinned identity (campaign row SAEA-DEV1000-BASELINE-LOCK; the serving pins
# are INHERITED unchanged from the sealed DEV-100 campaign / DEV-500
# confirmatory / K-WIDEN K1 / A4, all of which flew this same resident BASE
# service; the dataset pins are the landed DEV-1000 prep artifacts).
# --------------------------------------------------------------------------

RUN_ID = "SAEA-DEV1000-BASELINE-LOCK"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-dev1000"
BASELINE_FRAGMENT = "slurp-dev1000-kb-alpha-blend"
EXPERIMENT_FRAGMENT = "slurp-dev1000-baseline-lock-v1"
COMPOSED_CONFIG_SHA256 = "b94f81a6140467e861885167fa4f5ff0832e79d4fe5830d3e9fa9a0eb6986ab5"
SPLIT_ID = "DEV-1000"
NEW500_SPLIT_ID = "DEV-1000-NEW500"
# The load_split / ExecutionPlan convention (the receipt's ``run_identity_hash``
# field, equal to the runtime view's ``split_identity_hash`` field).
#
# ERRATUM, disclosed in the flight row and the experiment fragment: the
# preregistration §2 quotes "identity e9a7b7fe…d853 load-split" for DEV-1000.
# That value is DEV-100's run_identity_hash, carried over by a copy error when
# the preregistration was drafted. The correct DEV-1000 load-split identity is
# the one below. The preregistration's OTHER quoted value (9fb44e33…243b,
# receipt-integrity) is correct and is pinned below unchanged. The erratum
# moves NO sample: the flown population is the same 1,000 ids either way, and
# both hashes are asserted in-script before takeoff.
SPLIT_IDENTITY_HASH = "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
SPLIT_RECEIPT_RELPATH = "docs/receipts/probe-samples/DEV-1000.json"
SPLIT_RECEIPT_INTEGRITY_HASH = (
    "9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b"
)
RUNTIME_VIEW_SHA256 = "e148dbbcbda5b5145de9d3270f8bf7d6fb83fd00c7533f5ffa0fea1735fa0e87"
PROMOTION_RECEIPT_SHA256 = "2accbdc5a2f39fa650218928f92ab7b304717e108646c78051f8c203426a8fe6"
SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-mmproj-free.json"
FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
SESSION_DIR = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP8-BASE-DEV100-20260824T120910Z"
)
SESSION_RECEIPT_SHA256 = "6c8bab4d67432b4a3b88679483f0d6db41e28620ab8ee973f442a97200861b10"
DECODER_PORT = 8080
EMB_PORT = 8082

SPLIT_COUNT = 1000
SPLIT_AUDIO_SECONDS_TOTAL = 2884.7936875

# DEV-500 receipt (the nested EXPOSED subset at this tier; read ONLY to prove
# the NEW500 partition is exactly the set difference. Never a flown split).
DEV500_RECEIPT_RELPATH = "docs/receipts/probe-samples/DEV-500.json"
DEV500_RUN_IDENTITY = "a00f8c8615ea9508a812f93117b9838f2a1a84ec2b3f06c07edc28b04da6acf4"
DEV500_COUNT = 500

# NEW500 receipt pins (docs/receipts/probe-samples/DEV-1000-NEW500.json) —
# the LOCK STATISTIC's population. Pinned and integrity-checked here, but
# NEVER used to sub-select at flight time: both arms fly all 1,000 and the
# separately registered one-touch read does the partition.
#
# ID-FORMAT NOTE (the A4 lesson, applied): each receipt item carries BOTH an
# ``id`` field (``slurp:devel:NNNNNN:audio-NNNNNNNNNN`` — equal to the runtime
# view's ``sample_id``) and a ``key`` field (carrier-prefixed,
# ``slurp:slurp:devel:…``). Set comparisons against the flown population MUST
# use ``id``; comparing on ``key`` silently yields an EMPTY intersection.
NEW500_RECEIPT_RELPATH = "docs/receipts/probe-samples/DEV-1000-NEW500.json"
NEW500_RECEIPT_SHA256 = "1feefb8c327c0234160e96906bd5344cfef25ac665ddbb4db957fab067a234a3"
NEW500_RECEIPT_SPLIT_IDENTITY = (
    "1d6d4ba61028c36f22f03de87d48afebeda1b53bd3b32b1a001e117068ddc66d"
)
NEW500_RUN_IDENTITY = "48a96f6fcb9cc391dd776aededa9c27ec4e89195b06a656ae68e814948416ecd"
NEW500_COUNT = 500
NEW500_AUDIO_SECONDS_TOTAL = 1462.712

# The frozen v2 LOCK CANDIDATE, hash-pinned at the flight row.
LOCK_CANDIDATE_RELPATH = "configs/policy/kb-policy-v2-lock-candidate.json"
LOCK_CANDIDATE_SHA256 = (
    "0c34ebe7be636b8e432bffe504b0175d1a122000a74051b183e09615de69033e"
)
LOCK_CANDIDATE_SUPERSEDES_RELPATH = "configs/policy/kb-policy-v1-dev100.json"
LOCK_CANDIDATE_SUPERSEDES_SHA256 = (
    "0d36273eb2a5f4411ba9ca378ad820392e97c8759222087cf562e7f19442e2b0"
)

# Attempt-1 durable M0 trace: HASH AUTHORITY ONLY (canary byte comparison +
# resend response A). Never parsed for response TEXTS.
A1_ATTEMPT_ID = "attempt-20260824T073337Z-dev100r0"
A1_RUN_ID = "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
A1_TRACE_SHA256 = "d1f376bbacaa189f6583abe639d072567c4001fe63c52dab34e113b59ce4d8a2"

# Canary pair: the FIRST TWO attempt-1 M0 sample ids in sorted order (the
# registered pair every DEV-100 round, the DEV-500 campaign, K-WIDEN K1 and A4
# flew); the resend sample is the first. Both are DEV-100 ids, hence inside
# DEV-500, hence inside DEV-1000 — asserted in-script.
CANARY_SAMPLE_IDS = (
    "slurp:devel:000090:audio-1498567209",
    "slurp:devel:000109:audio-1497882612",
)
RESEND_SAMPLE_ID = CANARY_SAMPLE_IDS[0]
CANARY_SPLIT_ID = "DEV-1000-CANARY-2"
RESEND_SPLIT_ID = "DEV-1000-RESEND-1"

# Campaign ceilings (preregistration section 4; ledger row cells).
#
# Worst-case accounting, computed from the pinned view (NOT estimated):
#   M0     worst = 1,004 core / 2,891.9608 audio-s
#                  (4 canary contacts + 1,000 loop contacts)
#   BLEND  worst = 2,005 core / 5,778.1623 audio-s
#                  (4 canary + 2,000 loop + 1 resend)
#   RUN-CUMULATIVE worst = 3,009 core / 8,670.1231 audio-s
#   tool   worst = 1,001 (1,000 query embeddings + 1 jitter), BLEND only
# All four are inside the cells below with margin.
CAMPAIGN_CEILING_CORE = 3400
CAMPAIGN_CEILING_TOOL = 1200
CAMPAIGN_CEILING_AUDIO = 9000
CAMPAIGN_CEILING_GPU_HOURS = 3.0

# Embedder pins (BLEND arm only; umbrella lock qwen3-embedding-0.6b-gguf).
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_DIM = 1024
EMBEDDER_RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
EMB_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
)

# --------------------------------------------------------------------------
# The byte-frozen v2 LOCK CANDIDATE
# (configs/policy/kb-policy-v2-lock-candidate.json). Every knob below is
# BYTE-IDENTICAL to the v1 frozen cell it supersedes; the SINGLE addition is
# the DELTA RETAIN-OVERRIDE dispatch rule, which changes no knob at all -- it
# changes which branch of ``_advance_after_direct`` a live-direct trajectory
# takes. Any change here voids the lock registration.
# --------------------------------------------------------------------------
FROZEN_ALPHA = 0.45
FROZEN_TAU = 0.65
FROZEN_TOP_K = 5
FROZEN_FUSE = FuseKnobs(tau=FROZEN_TAU, m=5, c=2, top_l=3)
FROZEN_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

# THE v2 ADDITION. delta = cos_top1 - cos_direct; the override fires on a
# trajectory that WOULD have retained (the repaired normalizer recovered a
# direct label) when delta >= the bar AND the direct answer's own task target
# is not the fused top-1 target. 0.14 is the smallest bar that disturbs ZERO
# already-correct retains on all three sealed populations simultaneously.
#
# REGISTERED HONESTY: this bar was FIT on EXPOSED data (DEV-100 r4/r5 +
# DEV-500 NEW400) and frozen 2026-08-25. Its OUT-OF-SAMPLE validation IS the
# unexposed-500 lock read this campaign feeds. Declared here, in the flight
# row, and in every report that cites the lock.
DELTA_BAR = 0.14
DELTA_EPS = 1e-12

M0_POLICY_ID = "saea-direct-decode-only-m0"
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 64}

# --------------------------------------------------------------------------
# Per-arm registration table (campaign row PLAN DECLARATIONS, byte-matching
# the registered ledger segments; run-cumulative plan semantics).
#
# ``plan_calls`` and ``plan_audio`` are RUN-CUMULATIVE across every attempt of
# the run id (core.model.adapter enforces both against a fresh sibling read of
# durable attempt actuals), so BLEND's plan covers M0's durable actual PLUS
# BLEND's own worst case. ``plan_gpu`` is per-attempt, matching the DEV-500
# confirmatory convention; the two arms sum to the 3.0 campaign cell.
#
# BOTH arms fly ``split_id = SPLIT_ID`` -- all 1,000. There is deliberately no
# arm whose split is NEW500: the lock statistic's partition is performed by
# the separately registered one-touch read, never at flight time.
# --------------------------------------------------------------------------
ARMS: dict[str, dict[str, object]] = {
    "M0": {
        "slug": "m0",
        "arm_index": 1,
        "split_id": SPLIT_ID,
        "max_contacts": 1,
        "attempt_core_ceiling": 1010,
        "attempt_tool_ceiling": 0,
        "plan_calls": 1060,
        "plan_audio": 2950,
        "plan_gpu": 1.2,
        "resend": False,
        "sidecar": False,
        "report_stub": "arm1-m0",
    },
    "BLEND": {
        "slug": "blend",
        "arm_index": 2,
        "split_id": SPLIT_ID,
        "max_contacts": 2,
        "attempt_core_ceiling": 2010,
        "attempt_tool_ceiling": 1020,
        "plan_calls": 3100,
        "plan_audio": 8800,
        "plan_gpu": 1.8,
        "resend": True,
        "sidecar": True,
        "report_stub": "arm2-blend",
    },
}

# Decode-speed canary (registered semantics carried from the DEV-100 rounds).
CANARY_SAMPLE_COUNT = 2
CANARY_MS_PER_TOKEN_PASS = 300.0

# In-flight decode-rate sentinel (armed on EVERY arm's main loop).
SENTINEL_WINDOW_CONTACTS = 8
SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT = 1000.0

OUT_CHECK_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition"
    / "2026-08-25-dev1000-baseline-lock"
)


def read_clock_samples(root: Path, slug: str) -> list[dict[str, object]] | None:
    """Parse the Windows-side mid-flight clock samples if present."""

    path = root / "runs" / RUN_ID / f"clock-samples-{slug}.jsonl"
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
# DEV-1000 adapter: runtime-view-filtered SLURP samples, scoring PERMANENTLY
# deferred (mechanical flight: gold never opens under this row).
# --------------------------------------------------------------------------


class Dev1000Adapter(SlurpAdapter):
    """SlurpAdapter filtered to the DEV-1000 runtime view. ``load_split``
    serves ``DEV-1000`` (all 1,000 -- what BOTH arms fly),
    ``DEV-1000-NEW500`` (the unexposed 500 = DEV-1000 minus DEV-500, id set
    supplied at construction), ``DEV-1000-CANARY-2`` (the registered attempt-1
    M0 canary pair) and ``DEV-1000-RESEND-1`` (the first canary sample).

    ``DEV-1000-NEW500`` is served so the launcher can PROVE the partition
    (subset / disjointness / exact-difference) before takeoff. NO ARM FLIES
    IT: the lock statistic's partition belongs to the separately registered
    one-touch read, over a sealed and already-flown set.

    ``score`` returns a deferral marker: this campaign lands MECHANICALLY."""

    def __init__(self, lock, root, *, repo_root, view_items, new500_ids) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._view_by_id = {item["sample_id"]: item for item in view_items}
        self._new500_ids = frozenset(new500_ids)
        self._cache: dict[str, tuple[SlurpSample, ...]] = {}

    def load_split(self, split_id, **kwargs):  # noqa: D102
        if split_id not in (SPLIT_ID, NEW500_SPLIT_ID, CANARY_SPLIT_ID, RESEND_SPLIT_ID):
            raise ValueError(f"Dev1000Adapter serves only DEV-1000 views, not {split_id!r}")
        if SPLIT_ID not in self._cache:
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
            self._cache[SPLIT_ID] = tuple(sorted(samples, key=lambda s: s.sample_id))
        full = self._cache[SPLIT_ID]
        if split_id == SPLIT_ID:
            return full
        if split_id == NEW500_SPLIT_ID:
            subset = tuple(s for s in full if s.sample_id in self._new500_ids)
            if len(subset) != NEW500_COUNT:
                raise ValueError(f"NEW500 subset resolved to {len(subset)} samples")
            return subset
        by_id = {s.sample_id: s for s in full}
        if split_id == CANARY_SPLIT_ID:
            return tuple(by_id[sid] for sid in CANARY_SAMPLE_IDS)
        return (by_id[RESEND_SAMPLE_ID],)

    def score(self, sample, response):  # noqa: D102 — gold stays sealed under this row
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
    core-contact ceiling FAIL-CLOSED, with an optional armed
    :class:`DecodeRateSentinel` consulted AFTER every completed contact."""

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
                    f"arm core ceiling: <= {self._ceiling} frozen-core contacts "
                    f"registered and {self._count} are already spent; refusing "
                    "the next contact fail-closed"
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
    embedding of the trajectory's own direct answer text (BLEND arm)."""

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


# --------------------------------------------------------------------------
# THE REGISTERED v2 VARIABLE: the delta-override dispatch rule, implemented
# ENTIRELY LAUNCHER-SIDE through kb_policy's OWN pure functions. Nothing
# under rails/ or core/ is modified, imported-and-monkeypatched, or
# subclassed; the only injection point is the ``normalizer`` keyword the
# REGISTERED controller factory already exposes.
# --------------------------------------------------------------------------


def _fused_ranked_targets(
    fused: Mapping[str, float], label_targets: Mapping[str, str]
) -> tuple[tuple[str, float], ...]:
    """Collapse ``_fused_label_scores``'s label-FACET-keyed scores onto task
    TARGETS, taking the max (which is what ``_argmax_labels`` would see) and
    dropping non-positive scores, then rank by (-score, target).

    Byte-for-byte the same collapse the landed pre-analysis uses
    (``analysis.contrast_fewshot_preanalysis._fused_ranked_targets``);
    reproduced here rather than imported so this launcher pulls in no
    analysis module at flight time."""

    by_target: dict[str, float] = {}
    for facet_id, score in fused.items():
        if score <= 0.0:
            continue
        target = label_targets[facet_id]
        by_target[target] = max(by_target.get(target, 0.0), score)
    return tuple(sorted(by_target.items(), key=lambda item: (-item[1], item[0])))


class DeltaSignalTable:
    """Frozen-snapshot lookups the delta signal needs, built ONCE per flight.

    ``content_facet_target`` maps a content facet id to the task target of
    the first value that associates it -- the same first-wins convention the
    landed pre-analysis's ``SnapshotBundle`` uses. ``facets_by_target``
    restricts that to facets the landed content-facet NPZ actually carries a
    vector for, which is the population ``cos_direct`` maximizes over."""

    def __init__(self, snapshot: KnowledgeSnapshot, facet_vector_table: Mapping[str, Mapping[str, tuple[float, ...]]]) -> None:
        self.label_targets: dict[str, str] = dict(_label_identities(snapshot))
        self.values_by_id = {value.value_id: value for value in snapshot.values}
        content_facet_target: dict[str, str] = {}
        for value in snapshot.values:
            if value.task_target is None:
                continue
            for facet_id in value.associated_facet_ids:
                content_facet_target.setdefault(facet_id, value.task_target)
        self.content_facet_target = content_facet_target
        by_target: dict[str, list[str]] = {}
        for facet_id, target in content_facet_target.items():
            if facet_id in facet_vector_table:
                by_target.setdefault(target, []).append(facet_id)
        self.facets_by_target = {
            target: tuple(sorted(facet_ids)) for target, facet_ids in by_target.items()
        }
        self.facet_vector_table = facet_vector_table


def compute_delta_signal(
    *,
    snapshot: KnowledgeSnapshot,
    table: DeltaSignalTable,
    facet_vectors,
    query_vector: tuple[float, ...],
    direct_label: str | None,
    query_state: QueryState,
    ranker,
    fuser,
    top_k: int,
    tau: float,
    fusion_m: int,
) -> dict[str, object]:
    """The v2 trigger signal for ONE trajectory, at ZERO contacts.

    Replays recall -> rank -> fuse through ``rails.kb_policy``'s own pure
    functions at the frozen knobs on this trajectory's own already-embedded
    query vector, then computes

        delta = cos_top1 - cos_direct

    where ``cos_top1`` is the fused top-1 TARGET's best PERCEPT-ADMITTED
    supporting content-facet cosine (admitted = inside
    ``rank_result.candidates[:fusion_m]`` AND max non-prior-dimension recall
    cosine >= tau -- exactly the fuser's own admission predicate) and
    ``cos_direct`` is the direct answer's OWN target's best content-facet
    cosine ANYWHERE in the frozen snapshot.

    Returns a fully populated record whether or not the override fires, so
    the round can report the delta distribution over every retain candidate
    and not merely over the triggered set. Gold is never touched."""

    record: dict[str, object] = {
        "direct_label": direct_label,
        "direct_target": None,
        "fused_top1_target": None,
        "cos_top1": None,
        "cos_direct": None,
        "delta": None,
        "disagrees": False,
        "override_fires": False,
        "replay_selected_value_ids": None,
        "reason": None,
        "delta_bar": DELTA_BAR,
    }
    if direct_label is None:
        # Dead-direct: the FROZEN cell already dispatches this trajectory
        # (the protect-direct term is inert), so the override is irrelevant
        # and the expensive replay is skipped by design.
        record["reason"] = "dead-direct (the frozen cell dispatches it anyway)"
        return record
    if len(query_vector) == 0:
        record["reason"] = "query vector empty (no cosine dimension)"
        return record

    direct_target = table.label_targets.get(direct_label)
    record["direct_target"] = direct_target

    recall_scores = multidim_recall(
        snapshot, {"content": query_vector}, facet_vectors, top_k
    )
    if not recall_scores:
        record["reason"] = "nothing recalled (the frozen cell stops at one contact)"
        return record
    rank_result = ranker(
        snapshot_sha256=snapshot.content_hash(),
        query_state=query_state,
        recall_scores=recall_scores,
    )
    fusion_decision = fuser(
        snapshot=snapshot,
        snapshot_sha256=snapshot.content_hash(),
        query_state=query_state,
        rank_result=rank_result,
        recall_scores=recall_scores,
    )
    record["replay_selected_value_ids"] = tuple(fusion_decision.selected_value_ids)
    if not fusion_decision.selected_value_ids:
        record["reason"] = "empty supply (the frozen cell stops at one contact)"
        return record

    fused = _fused_label_scores(
        table.label_targets,
        table.values_by_id,
        fusion_decision.selected_value_ids,
        rank_result,
    )
    fused_ranked = _fused_ranked_targets(fused, table.label_targets)
    if not fused_ranked:
        record["reason"] = "no positively-scored fused target"
        return record
    fused_top1_target = fused_ranked[0][0]
    record["fused_top1_target"] = fused_top1_target

    # cos_top1: the fuser's OWN percept-admission predicate, per target.
    top_m_ids = [
        candidate.facet_id for candidate in rank_result.candidates[:fusion_m]
    ]
    best_cos_by_target: dict[str, float] = {}
    for facet_id in top_m_ids:
        dim_scores = recall_scores.get(facet_id, {})
        cosine_scores = [
            score
            for dim, score in dim_scores.items()
            if dim not in PRIOR_MASS_DIMENSIONS
        ]
        if not cosine_scores or max(cosine_scores) < tau:
            continue
        target = table.content_facet_target.get(facet_id)
        content_score = dim_scores.get("content")
        if target is None or content_score is None:
            continue
        best_cos_by_target[target] = max(
            best_cos_by_target.get(target, 0.0), float(content_score)
        )
    cos_top1 = best_cos_by_target.get(fused_top1_target)
    record["cos_top1"] = None if cos_top1 is None else float(cos_top1)

    # cos_direct: a masked maximum over the FULL content-facet population
    # carrying the direct answer's own target -- the conservative handicap.
    cos_direct: float | None = None
    if direct_target is not None:
        facet_ids = table.facets_by_target.get(direct_target, ())
        if facet_ids:
            cos_direct = max(
                _cosine(query_vector, table.facet_vector_table[facet_id]["content"])
                for facet_id in facet_ids
            )
    record["cos_direct"] = None if cos_direct is None else float(cos_direct)

    disagrees = direct_target is not None and direct_target != fused_top1_target
    record["disagrees"] = bool(disagrees)
    if cos_top1 is None or cos_direct is None:
        record["reason"] = (
            "delta undefined (the fused top-1 admitted no supporting facet, "
            "or the direct answer's target carries no vectored content facet)"
        )
        return record
    delta = float(cos_top1) - float(cos_direct)
    record["delta"] = delta
    if not disagrees:
        record["reason"] = (
            "direct target IS the fused top-1: the mandatory disagreement "
            "condition refuses the override"
        )
        return record
    if delta >= DELTA_BAR - DELTA_EPS:
        record["override_fires"] = True
        record["reason"] = f"OVERRIDE: delta {delta:.4f} >= bar {DELTA_BAR}"
    else:
        record["reason"] = f"delta {delta:.4f} below bar {DELTA_BAR}"
    return record


class DeltaOverrideNormalizer:
    """The REGISTERED v2 variable, as a per-sample ``Normalizer``.

    ``KbAlphaBlendController`` calls its injected normalizer exactly twice
    per trajectory: once at the top of ``_advance_after_direct`` and once at
    the top of ``_advance_after_evidence``. Call 1 computes the delta signal
    and, when the override fires, returns ``None`` INSTEAD of the recovered
    label -- which removes the protect-direct constant from
    ``_blend_scores``, makes ``best_labels == (direct_label,)`` False, and so
    routes the trajectory down the evidence-dispatch branch. Call 2 always
    returns the true normalization, so ``_advance_after_evidence``'s
    ``last_winner_label`` bookkeeping is exactly what the frozen cell does.

    The suppression is confined to the retain/dispatch BRANCH: recall, rank
    and fuse all run BEFORE ``_blend_scores``, so the SUPPLY of an overridden
    trajectory is byte-identical to what the frozen cell would have computed.
    The launcher proves that per sample rather than asserting it."""

    def __init__(
        self,
        *,
        sample_id: str,
        snapshot: KnowledgeSnapshot,
        table: DeltaSignalTable,
        facet_vectors,
        cell: LazyQueryVector,
        query_state: QueryState,
        ranker,
        fuser,
        sink: dict[str, dict[str, object]],
        lock: threading.Lock,
    ) -> None:
        self._sample_id = sample_id
        self._snapshot = snapshot
        self._table = table
        self._facet_vectors = facet_vectors
        self._cell = cell
        self._query_state = query_state
        self._ranker = ranker
        self._fuser = fuser
        self._sink = sink
        self._lock = lock
        self.calls = 0
        self.true_direct_label: str | None = None
        self.record: dict[str, object] | None = None

    def __call__(self, response_text, label_targets):
        true_label = default_label_normalizer(response_text, label_targets)
        self.calls += 1
        if self.calls != 1:
            # The evidence contact: never suppressed.
            return true_label
        self.true_direct_label = true_label
        if dict(label_targets) != self._table.label_targets:
            raise SystemExit(
                "v2 override: the controller's label_targets differ from the "
                "launcher's frozen-snapshot identities; refusing"
            )
        record = compute_delta_signal(
            snapshot=self._snapshot,
            table=self._table,
            facet_vectors=self._facet_vectors,
            query_vector=tuple(float(value) for value in self._cell),
            direct_label=true_label,
            query_state=self._query_state,
            ranker=self._ranker,
            fuser=self._fuser,
            top_k=FROZEN_TOP_K,
            tau=FROZEN_TAU,
            fusion_m=FROZEN_FUSE.m,
        )
        record["sample_id"] = self._sample_id
        record["true_direct_label"] = true_label
        self.record = record
        with self._lock:
            self._sink[self._sample_id] = record
        return None if record["override_fires"] else true_label


class RuntimeEmbeddedBlendController:
    """BLEND wrapper: on the direct-decode response, embeds that text (ONE
    pinned-tool contact) into the injected content-dimension cell, then lets
    the REGISTERED controller advance. Adds no policy behaviour beyond the
    injected v2 override normalizer. The sha256 of the direct-decode response
    text is recorded for the cross-attempt byte-agreement descriptive."""

    def __init__(
        self,
        inner,
        *,
        sample_id: str,
        cell: LazyQueryVector,
        embed,
        override_normalizer: "DeltaOverrideNormalizer",
    ) -> None:
        self._inner = inner
        self._sample_id = sample_id
        self._cell = cell
        self._embed = embed
        self._override = override_normalizer
        self._filled = False
        self.direct_response_sha256: str | None = None
        # Launcher-side observability (never consulted by policy): the label
        # facet the REPAIRED normalizer recovered from the flown direct
        # response. Under v2 this is read from the override normalizer's TRUE
        # recovery, not from the controller's (possibly suppressed)
        # ``_direct_label``.
        self.direct_label_recovered: str | None = None
        self.direct_label_suppressed_by_override: bool = False
        # Observability (never consulted by policy): the flown fusion
        # decision's supply, captured from the registered controller's own
        # advance for the branch-only (supply-identity) proof.
        self.fusion_selected_value_ids: tuple[str, ...] | None = None
        self.fusion_supporting_facet_ids: tuple[str, ...] | None = None

    def initial_contact(self, context):
        return self._inner.initial_contact(context)

    def advance(self, context, contact, response_text):
        is_direct = (
            contact.contact_id == _DIRECT_CONTACT_ID
            and isinstance(response_text, str)
            and not self._filled
        )
        if is_direct:
            self.direct_response_sha256 = sha256_text(response_text)
            vector = self._embed(self._sample_id, response_text)
            self._cell.fill(vector)
            self._filled = True
        advance = self._inner.advance(context, contact, response_text)
        if is_direct:
            self.direct_label_recovered = self._override.true_direct_label
            record = self._override.record
            self.direct_label_suppressed_by_override = bool(
                record is not None and record.get("override_fires")
            )
            fusion_decision = getattr(advance, "fusion_decision", None)
            if fusion_decision is not None:
                self.fusion_selected_value_ids = tuple(
                    fusion_decision.selected_value_ids
                )
                self.fusion_supporting_facet_ids = tuple(
                    fusion_decision.supporting_facet_ids
                )
        return advance

    @property
    def delta_record(self) -> dict[str, object] | None:
        return self._override.record

    @property
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


# --------------------------------------------------------------------------
# Embedding contact meter (BLEND arm tool sub-ceiling, fail-closed).
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
                    f"embedding tool ceiling: the BLEND arm registers <= "
                    f"{self.ceiling} contacts and {self.count} are already spent; refusing"
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
    """Decode-speed canary failed: the arm stops BEFORE its main loop."""


def parse_print_timing(log_bytes: bytes) -> dict[str, list[dict[str, float]]]:
    """Extract llama-server per-request print_timing rates from raw server-log
    bytes: content-free serving descriptives only."""

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


def parse_slot_requests(log_bytes: bytes) -> list[dict[str, int]]:
    """Per-request serving records from raw llama-server log bytes —
    content-free COUNTS only (prompt-reuse is a first-class metric)."""

    import re

    launch = re.compile(
        r"slot launch_slot_: id\s+(\d+) \| task (\d+) \| processing task"
    )
    peval = re.compile(
        r"slot print_timing: id\s+(\d+) \| task (\d+) \| prompt eval time =\s*"
        r"[0-9.]+ ms /\s*(\d+) tokens"
    )
    geval = re.compile(
        r"slot print_timing: id\s+(\d+) \| task (\d+) \|\s+eval time =\s*"
        r"[0-9.]+ ms /\s*(\d+) tokens"
    )
    release = re.compile(
        r"slot\s+release: id\s+(\d+) \| task (\d+) \| stop processing: "
        r"n_tokens = (\d+)"
    )
    by_task: dict[int, dict[str, int]] = {}

    def rec(slot: str, task: str) -> dict[str, int]:
        return by_task.setdefault(int(task), {"slot": int(slot), "task": int(task)})

    for line in log_bytes.decode("utf-8", errors="replace").splitlines():
        match = launch.search(line)
        if match is not None:
            rec(match.group(1), match.group(2))
            continue
        match = peval.search(line)
        if match is not None:
            rec(match.group(1), match.group(2))["prompt_eval_tokens"] = int(match.group(3))
            continue
        match = geval.search(line)
        if match is not None:
            rec(match.group(1), match.group(2))["generation_tokens"] = int(match.group(3))
            continue
        match = release.search(line)
        if match is not None:
            rec(match.group(1), match.group(2))["release_n_tokens"] = int(match.group(3))
    complete = [
        row
        for _, row in sorted(by_task.items())
        if {"prompt_eval_tokens", "generation_tokens", "release_n_tokens"} <= set(row)
    ]
    return complete


def token_count_distribution(values: Sequence[int]) -> dict[str, object]:
    """Descriptive distribution of a token-count list (content-free)."""

    if not values:
        return {"count": 0}
    ordered = sorted(int(v) for v in values)
    n = len(ordered)
    return {
        "count": n,
        "min": ordered[0],
        "p10": ordered[max(0, int(0.1 * n) - (1 if int(0.1 * n) == n else 0))],
        "median": ordered[n // 2],
        "p90": ordered[min(n - 1, int(0.9 * n))],
        "max": ordered[-1],
        "sum": sum(ordered),
    }


def rate_distribution(rates: Sequence[float]) -> dict[str, object]:
    """Descriptive distribution of generation ms/token rates."""

    if not rates:
        return {"count": 0}
    ordered = sorted(float(r) for r in rates)
    n = len(ordered)
    return {
        "count": n,
        "min": ordered[0],
        "p10": ordered[max(0, int(0.1 * n) - (1 if int(0.1 * n) == n else 0))],
        "median": ordered[n // 2],
        "p90": ordered[min(n - 1, int(0.9 * n))],
        "max": ordered[-1],
    }


class DecodeRateSentinelTrip(Exception):
    """The in-flight decode-rate sentinel tripped: flush everything durable
    immediately and stop the flight cleanly (service left up)."""


class DecodeRateSentinel:
    """Rolling-median in-flight decode-rate guard (flight-proven in the
    DEV-100 campaign)."""

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
    """Flush a micro-run's TraceBuffer into its OWN TraceSink, applying a
    record-id namespace prefix at flush time."""

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
                    f"sinks: {sorted(overlap)[:5]!r}; refusing"
                )


def self_test() -> int:
    """Offline exercise: zero contacts, no service, no gate, no data root."""

    base = Path(tempfile.mkdtemp(prefix="saea-dev1000-selftest-"))
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
    main_buffer = duplicate_heavy_buffer()
    main_ids = [record_id for _, record_id, _ in main_buffer.records]
    main_buffer.flush_into(main_sink)
    assert_zero_record_id_overlap(
        {"main": frozenset(main_ids), "canary": frozenset(canary_ids)}
    )
    canary_sink.close()
    try:
        duplicate_heavy_buffer().flush_into(main_sink)
    except TraceSinkError as error:
        log(f"self-test: shared-sink collision correctly refused ({error})")
    else:
        raise SystemExit("self-test FAIL: duplicate flush into one sink did not raise")
    try:
        assert_zero_record_id_overlap(
            {"main": frozenset(main_ids), "canary": frozenset(main_ids)}
        )
    except SystemExit as error:
        log(f"self-test: overlap assertion correctly fired ({error})")
    else:
        raise SystemExit("self-test FAIL: record-id overlap not detected")
    log("self-test mechanism a PASS: micro-run sink isolation + negative controls")

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
        raise SystemExit("self-test FAIL: sentinel tripped AT the threshold (strict >)")
    stub_rows([5137.0] * SENTINEL_WINDOW_CONTACTS)
    try:
        for _ in range(SENTINEL_WINDOW_CONTACTS):
            sentinel.observe_after_contact()
    except DecodeRateSentinelTrip as error:
        log(f"self-test: sentinel correctly tripped ({error})")
    if sentinel.tripped is None:
        raise SystemExit("self-test FAIL: sentinel did not trip on degraded rates")
    log(f"self-test mechanism b PASS: {sentinel.summary()}")

    # ---- prompt-reuse parser ---------------------------------------------
    stub_requests = (
        "165.41.712.384 I slot launch_slot_: id  4 | task 10 | processing task, is_child = 0\n"
        "165.41.748.510 I slot print_timing: id  4 | task 10 | prompt eval time =     233.21 ms /    75 tokens (    3.11 ms per token,   321.60 tokens per second)\n"
        "165.41.748.517 I slot print_timing: id  4 | task 10 |        eval time =    1714.68 ms /    48 tokens (   35.72 ms per token,    27.99 tokens per second)\n"
        "165.41.748.606 I slot      release: id  4 | task 10 | stop processing: n_tokens = 1817, truncated = 0\n"
        "165.59.000.000 I slot launch_slot_: id  2 | task 12 | processing task, is_child = 0\n"
        "165.59.000.001 I slot print_timing: id  2 | task 12 | prompt eval time =       1.00 ms /     1 tokens (    1.00 ms per token,  1000.00 tokens per second)\n"
    )
    parsed_requests = parse_slot_requests(stub_requests.encode("utf-8"))
    if len(parsed_requests) != 1:
        raise SystemExit(f"self-test FAIL: parser returned {len(parsed_requests)} complete requests")
    first = parsed_requests[0]
    if (first["slot"], first["task"], first["prompt_eval_tokens"], first["generation_tokens"], first["release_n_tokens"]) != (4, 10, 75, 48, 1817):
        raise SystemExit(f"self-test FAIL: parser row wrong: {first}")
    dist = token_count_distribution([5, 1, 9])
    if (dist["count"], dist["min"], dist["median"], dist["max"], dist["sum"]) != (3, 1, 5, 9, 15):
        raise SystemExit(f"self-test FAIL: token distribution wrong: {dist}")
    log("self-test prompt-reuse parser PASS")

    # ---- lock-candidate knob sanity (byte-frozen v2 cell) -----------------
    if FROZEN_ALPHA != 0.45 or FROZEN_TAU != 0.65 or FROZEN_TOP_K != 5:
        raise SystemExit("self-test FAIL: frozen cell knobs drifted")
    if (FROZEN_FUSE.m, FROZEN_FUSE.c, FROZEN_FUSE.top_l) != (5, 2, 3):
        raise SystemExit("self-test FAIL: fuse knobs drifted from the frozen cell")
    if (FROZEN_WEIGHTS.w_cos, FROZEN_WEIGHTS.w_prior, FROZEN_WEIGHTS.w_agree) != (0.5, 0.3, 0.2):
        raise SystemExit("self-test FAIL: rank weights drifted from the frozen cell")
    if DELTA_BAR != 0.14:
        raise SystemExit("self-test FAIL: the v2 delta bar drifted from 0.14")
    if not (0.0 < DELTA_EPS < 1e-9):
        raise SystemExit("self-test FAIL: the v2 delta epsilon drifted")
    log(
        "self-test knob sanity PASS: byte-frozen v1 cell knobs plus the v2 "
        f"delta retain-override at bar {DELTA_BAR}"
    )

    # ---- f1060078 repair-presence probe ----------------------------------
    probe_targets = {"facet:a": "alarm_query", "facet:b": "alarm_set"}
    flown_json = '{"scenario": "alarm", "action": "query", "entities": []}'
    if default_label_normalizer(flown_json, probe_targets) != "facet:a":
        raise SystemExit("self-test FAIL: the f1060078 repair is not present")
    swapped_json = '{"scenario": "query", "action": "alarm", "entities": []}'
    if default_label_normalizer(swapped_json, probe_targets) is not None:
        raise SystemExit("self-test FAIL: the normalizer matched a scenario/action SWAP")
    prose = "Intent 'alarm_query' (scenario='alarm', action='query'); 130 TRAIN utterances in this snapshot."
    if default_label_normalizer(prose, {"facet:a": prose}) is not None:
        raise SystemExit("self-test FAIL: prose-substring path is live (pre-repair behavior)")
    log("self-test repair-presence probe PASS")

    # ---- the v2 delta override: pure-signal behaviour, zero contacts ------
    # The override's decision surface is exercised without any model, service
    # or snapshot: compute_delta_signal's own guard clauses plus the
    # bar/disagreement predicate, which is the whole of the registered
    # variable. A dead-direct trajectory must be REFUSED by the override (the
    # frozen cell already dispatches it); a fired override must return None
    # from the normalizer so the controller takes the dispatch branch.
    dead = compute_delta_signal(
        snapshot=None,
        table=None,
        facet_vectors=None,
        query_vector=(1.0, 0.0),
        direct_label=None,
        query_state=None,
        ranker=None,
        fuser=None,
        top_k=FROZEN_TOP_K,
        tau=FROZEN_TAU,
        fusion_m=FROZEN_FUSE.m,
    )
    if dead["override_fires"] or dead["delta"] is not None:
        raise SystemExit("self-test FAIL: the override fired on a dead-direct trajectory")
    if "dead-direct" not in str(dead["reason"]):
        raise SystemExit("self-test FAIL: dead-direct reason string drifted")
    if dead["delta_bar"] != DELTA_BAR:
        raise SystemExit("self-test FAIL: the record does not carry the registered bar")
    novec = compute_delta_signal(
        snapshot=None,
        table=None,
        facet_vectors=None,
        query_vector=(),
        direct_label="facet:a",
        query_state=None,
        ranker=None,
        fuser=None,
        top_k=FROZEN_TOP_K,
        tau=FROZEN_TAU,
        fusion_m=FROZEN_FUSE.m,
    )
    if novec["override_fires"] or "query vector empty" not in str(novec["reason"]):
        raise SystemExit("self-test FAIL: empty-query-vector guard drifted")
    # The bar predicate itself, at the registered epsilon.
    for delta_value, expected in (
        (DELTA_BAR + 0.01, True),
        (DELTA_BAR, True),
        (DELTA_BAR - 1e-13, True),
        (DELTA_BAR - 0.01, False),
        (0.1282, False),
        (0.0039, False),
    ):
        fires = delta_value >= DELTA_BAR - DELTA_EPS
        if fires is not expected:
            raise SystemExit(
                f"self-test FAIL: bar predicate wrong at delta {delta_value}: "
                f"{fires} != {expected}"
            )
    log(
        "self-test v2 override PASS: dead-direct refused, empty-vector "
        f"refused, bar predicate exact at {DELTA_BAR} (the two known "
        "out-of-reach DEV-100 members 0.1282 and 0.0039 stay below)"
    )

    # ---- plan arithmetic: worst-case prior chain fits every plan + row ----
    # Worst cases computed from the pinned DEV-1000 view (1,000 samples,
    # 2,884.7936875 audio-s; canary pair 3.5835625 s; resend 1.4078125 s):
    #   M0    = 4 canary + 1,000 loop            = 1,004 core / 2,891.9608 s
    #   BLEND = 4 canary + 2,000 loop + 1 resend = 2,005 core / 5,778.1623 s
    chain = [
        ("M0", 1004, 2891.9608),
        ("BLEND", 2005, 5778.1623),
    ]
    if list(ARMS) != [arm_id for arm_id, _, _ in chain]:
        raise SystemExit(
            f"self-test FAIL: the arm table {list(ARMS)} does not match the "
            f"registered flight chain {[a for a, _, _ in chain]}"
        )
    prior_calls, prior_audio = 0, 0.0
    for arm_id, worst_calls, worst_audio in chain:
        arm = ARMS[arm_id]
        if worst_calls > int(arm["attempt_core_ceiling"]):
            raise SystemExit(f"self-test FAIL: {arm_id} attempt core ceiling too small")
        if prior_calls + worst_calls > int(arm["plan_calls"]):
            raise SystemExit(f"self-test FAIL: {arm_id} plan calls too small")
        if prior_audio + worst_audio > float(arm["plan_audio"]):
            raise SystemExit(f"self-test FAIL: {arm_id} plan audio too small")
        if int(arm["plan_calls"]) > CAMPAIGN_CEILING_CORE:
            raise SystemExit(f"self-test FAIL: {arm_id} plan calls exceed the row cell")
        if float(arm["plan_audio"]) > CAMPAIGN_CEILING_AUDIO:
            raise SystemExit(f"self-test FAIL: {arm_id} plan audio exceeds the row cell")
        if int(arm["attempt_tool_ceiling"]) > CAMPAIGN_CEILING_TOOL:
            raise SystemExit(f"self-test FAIL: {arm_id} tool ceiling exceeds the row cell")
        if float(arm["plan_gpu"]) > CAMPAIGN_CEILING_GPU_HOURS:
            raise SystemExit(f"self-test FAIL: {arm_id} plan gpu exceeds the row cell")
        prior_calls += worst_calls
        prior_audio += worst_audio
    if prior_calls > CAMPAIGN_CEILING_CORE:
        raise SystemExit("self-test FAIL: the campaign core worst case exceeds the row cell")
    if prior_audio > CAMPAIGN_CEILING_AUDIO:
        raise SystemExit("self-test FAIL: the campaign audio worst case exceeds the row cell")
    if sum(float(a["plan_gpu"]) for a in ARMS.values()) > CAMPAIGN_CEILING_GPU_HOURS:
        raise SystemExit("self-test FAIL: the summed per-arm GPU plans exceed the row cell")
    log(
        "self-test plan arithmetic PASS: the worst-case prior chain "
        f"({prior_calls} core / {prior_audio:.1f} audio-s) fits every arm plan "
        f"and the row cells ({CAMPAIGN_CEILING_CORE} / "
        f"{CAMPAIGN_CEILING_AUDIO})"
    )

    # ---- the NEW500 partition is a READ-ONLY pin, never a flown split -----
    for arm_id, arm in ARMS.items():
        if arm["split_id"] != SPLIT_ID:
            raise SystemExit(
                f"self-test FAIL: arm {arm_id} flies {arm['split_id']!r}; both lock "
                "arms MUST fly the full DEV-1000 -- the statistic's partition "
                "belongs to the separately registered one-touch read"
            )
    log(
        "self-test population PASS: both arms fly the full DEV-1000; no arm "
        "sub-selects the unexposed 500"
    )
    log("SELF-TEST PASS (zero contacts)")
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
    if "--arm" not in sys.argv:
        raise SystemExit("usage: --arm M0|BLEND [--gpu-preflight <json>] [--preflight-only]")
    arm_id = sys.argv[sys.argv.index("--arm") + 1]
    if arm_id not in ARMS:
        raise SystemExit(f"unknown arm {arm_id!r}; registered arms: {sorted(ARMS)}")
    arm = ARMS[arm_id]
    slug = str(arm["slug"])
    split_id = str(arm["split_id"])
    max_contacts = int(arm["max_contacts"])
    attempt_core_ceiling = int(arm["attempt_core_ceiling"])
    attempt_tool_ceiling = int(arm["attempt_tool_ceiling"])
    plan_calls = int(arm["plan_calls"])
    plan_audio = int(arm["plan_audio"])
    plan_gpu = float(arm["plan_gpu"])
    with_resend = bool(arm["resend"])
    with_sidecar = bool(arm["sidecar"])
    report_stub = str(arm["report_stub"])

    gpu_preflight: dict[str, object] = {"coordinator_record": "NOT_PROVIDED"}
    if "--gpu-preflight" in sys.argv:
        gpu_preflight_path = Path(sys.argv[sys.argv.index("--gpu-preflight") + 1])
        gpu_preflight = json.loads(gpu_preflight_path.read_text(encoding="utf-8"))

    attempt_id = (
        f"attempt-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-dev1000{slug}"
    )
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"DEV-1000 BASELINE-LOCK ARM {arm_id} — {RUN_ID} / {attempt_id}")
    log(f"run dir: {run_dir}")

    flight: dict[str, object] = {
        "schema": "saea-dev1000-baseline-lock-arm-flight-v1",
        "run_id": RUN_ID,
        "arm_id": arm_id,
        "arm_index": arm["arm_index"],
        "attempt_id": attempt_id,
        "mechanical_only": True,
        "started_at": iso_now(),
        "gpu_preflight": dict(gpu_preflight),
        "plan": {
            "calls": plan_calls,
            "audio_seconds": plan_audio,
            "gpu_hours": plan_gpu,
            "attempt_core_ceiling": attempt_core_ceiling,
            "attempt_tool_ceiling": attempt_tool_ceiling,
        },
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
    log(f"GPU preflight: enforced power limit {enforced_w} W (>= 95)")

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
    candidate = values["dev1000_lock_candidate"]
    frozen_cell = candidate["knobs"]
    if (
        frozen_cell["alpha"] != FROZEN_ALPHA
        or frozen_cell["tau"] != FROZEN_TAU
        or frozen_cell["recall_top_k_per_dimension"] != FROZEN_TOP_K
        or frozen_cell["fusion"] != {"m": 5, "c": 2, "l": 3}
        or frozen_cell["rank_weights"] != {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}
    ):
        raise SystemExit("composed frozen-cell knobs disagree with this launcher's constants")
    if frozen_cell["retain_override"]["bar"] != DELTA_BAR:
        raise SystemExit(
            f"composed retain-override bar {frozen_cell['retain_override']['bar']} "
            f"!= this launcher's registered {DELTA_BAR}"
        )
    log(f"composed config hash verified: {composed.config_hash} (-np {server_np}; v2 cell knobs equal)")
    flight["config_hash"] = composed.config_hash
    flight["server_np"] = server_np

    # ---- the v2 LOCK CANDIDATE, hash-pinned at the flight row -------------
    # The candidate file is the registration's object of study; it is pinned
    # by hash so a post-freeze edit cannot fly silently. The knob table above
    # was already proved equal via the composed fragment; this proves the
    # SOURCE file itself has not moved since the flight row was written.
    candidate_path = REPO / LOCK_CANDIDATE_RELPATH
    measured_candidate = sha256_file(candidate_path)
    if measured_candidate != LOCK_CANDIDATE_SHA256:
        raise SystemExit(
            f"the v2 lock candidate hashes to {measured_candidate}, not the "
            f"registered {LOCK_CANDIDATE_SHA256}; a post-freeze change voids "
            "the lock registration"
        )
    candidate_file = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate_file["knobs"]["retain_override"]["bar"] != DELTA_BAR:
        raise SystemExit("the v2 candidate file's delta bar disagrees with this launcher")
    if candidate_file["supersedes"] != LOCK_CANDIDATE_SUPERSEDES_RELPATH:
        raise SystemExit("the v2 candidate no longer supersedes the v1 frozen cell")
    measured_v1 = sha256_file(REPO / LOCK_CANDIDATE_SUPERSEDES_RELPATH)
    if measured_v1 != LOCK_CANDIDATE_SUPERSEDES_SHA256:
        raise SystemExit(
            f"the superseded v1 frozen cell hashes to {measured_v1}, not the pin"
        )
    log(
        f"v2 lock candidate pinned ({measured_candidate[:12]}…), superseding the "
        f"v1 frozen cell ({measured_v1[:12]}…); delta bar {DELTA_BAR} agreed by "
        "the candidate file, the composed fragment and this launcher"
    )
    flight["lock_candidate"] = {
        "relpath": LOCK_CANDIDATE_RELPATH,
        "sha256": measured_candidate,
        "supersedes_relpath": LOCK_CANDIDATE_SUPERSEDES_RELPATH,
        "supersedes_sha256": measured_v1,
        "delta_bar": DELTA_BAR,
        "delta_bar_fit_on_exposed_data": (
            "the bar was FIT on exposed data (DEV-100 r4/r5 + DEV-500 NEW400) "
            "and frozen 2026-08-25; its out-of-sample validation IS the "
            "unexposed-500 read this campaign feeds"
        ),
    }

    # ---- prompt-fit: the STANDING session-bound R6 row --------------------
    # The delta override changes only WHICH trajectories dispatch; the prompt
    # SHAPES are unchanged from the standing envelope. BLEND(v2) flies the v1
    # cell's m=5 material with the supplied-value ceiling fusion_c 2 *
    # fusion_top_l 3 = 6 and renders ZERO facet representations, so the
    # evidence-prompt WORST CASE is byte-identical to the one row
    # SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6 measured (6,174 tokens vs 8,192,
    # margin +1,954). M0 carries no evidence slot at all. The takeoff
    # precondition is therefore exactly that the resident session receipt
    # still hashes to the value that row bound -- asserted below, before
    # attach. If it does not, the mission STOPS here and an MF row is
    # registered to re-measure.
    PROMPT_FIT_STANDING_ROW = "SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6"
    session_receipt_path = SESSION_DIR / "session-receipt.json"
    measured_session = sha256_file(session_receipt_path)
    if measured_session != SESSION_RECEIPT_SHA256:
        raise SystemExit(
            f"the resident session receipt hashes to {measured_session}, not the "
            f"{SESSION_RECEIPT_SHA256} that the standing prompt-fit row "
            f"{PROMPT_FIT_STANDING_ROW} bound. The fit standing CANNOT be "
            "inherited across a session or binary change: STOP, register an MF "
            "row, and re-measure the prompt fit before any contact."
        )
    log(
        f"prompt-fit standing VERIFIED: session receipt {measured_session[:12]}… "
        f"is byte-equal to the binding of {PROMPT_FIT_STANDING_ROW} "
        "(6,174/8,192 tokens, margin +1,954); no re-measurement required"
    )
    flight["prompt_fit"] = {
        "standing_row": PROMPT_FIT_STANDING_ROW,
        "session_receipt_sha256": measured_session,
        "declared_tokens": 6174,
        "context_per_slot": 8192,
        "margin_tokens": 1954,
        "basis": (
            "the override changes only WHICH trajectories dispatch, never the "
            "prompt shape; supplied-value ceiling stays c*top_l = 6 and the "
            "runner renders zero facet representations"
        ),
    }

    # ---- runtime view + promotion receipt ---------------------------------
    view = json.loads(
        (REPO / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(encoding="utf-8")
    )
    if view["runtime_view_sha256"] != RUNTIME_VIEW_SHA256:
        raise SystemExit("runtime view sha256 drifted")
    if view["split_identity_hash"] != SPLIT_IDENTITY_HASH or view["count"] != SPLIT_COUNT:
        raise SystemExit("runtime view identity drifted")
    if abs(float(view["audio_seconds_total"]) - SPLIT_AUDIO_SECONDS_TOTAL) > 1e-6:
        raise SystemExit("runtime view audio total drifted")
    # The DEV-1000 receipt, by BOTH hash conventions (the preregistration §2
    # load-split erratum is documented at SPLIT_IDENTITY_HASH above).
    split_receipt = json.loads(
        (REPO / SPLIT_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    if split_receipt.get("run_identity_hash") != SPLIT_IDENTITY_HASH:
        raise SystemExit("DEV-1000 receipt run identity (load-split convention) drifted")
    if split_receipt.get("split_identity_hash") != SPLIT_RECEIPT_INTEGRITY_HASH:
        raise SystemExit("DEV-1000 receipt integrity hash drifted")
    promotion_path = FEATURE_ROOT / "DEV-1000-promotion.json"
    measured_promotion = sha256_file(promotion_path)
    if measured_promotion != PROMOTION_RECEIPT_SHA256:
        raise SystemExit(f"promotion receipt hashes to {measured_promotion}, not the pin")
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    if promotion.get("dataset_runtime_view_sha256") != RUNTIME_VIEW_SHA256:
        raise SystemExit("promotion receipt binds a different runtime view")
    if int(promotion.get("count", -1)) != SPLIT_COUNT:
        raise SystemExit(
            f"promotion receipt carries {promotion.get('count')} packets, not "
            f"{SPLIT_COUNT}: the DEV-1000 preprocess is incomplete"
        )
    log(f"DEV-1000 promotion receipt verified ({measured_promotion[:12]}…, 1,000 packets)")

    # ---- NEW500 partition: deterministic derivation + receipt cross-check --
    # PROOF ONLY. No arm flies this subset -- both arms fly all 1,000 and the
    # separately registered one-touch read performs the partition over the
    # sealed result. Verifying it here means the read can never be handed a
    # population that disagrees with what actually flew.
    #
    # THE A4 LESSON, APPLIED: the receipt's items carry BOTH ``id`` (equal to
    # the view's ``sample_id``) and ``key`` (carrier-prefixed,
    # ``slurp:slurp:devel:…``). This comparison uses ``id``. Comparing on
    # ``key`` yields a SILENTLY EMPTY intersection, which is exactly the class
    # of bug the A4 landing surfaced.
    dev1000_ids = sorted(item["sample_id"] for item in view["items"])
    if len(dev1000_ids) != SPLIT_COUNT:
        raise SystemExit("DEV-1000 view drifted")
    dev500_receipt = json.loads(
        (REPO / DEV500_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    if dev500_receipt.get("run_identity_hash") != DEV500_RUN_IDENTITY:
        raise SystemExit("DEV-500 receipt run identity drifted")
    dev500_ids = sorted(item["id"] for item in dev500_receipt["items"])
    if len(dev500_ids) != DEV500_COUNT:
        raise SystemExit(f"DEV-500 receipt carries {len(dev500_ids)} ids")
    if not set(dev500_ids) <= set(dev1000_ids):
        raise SystemExit("DEV-500 is not nested inside DEV-1000")
    new500_ids = sorted(set(dev1000_ids) - set(dev500_ids))
    if len(new500_ids) != NEW500_COUNT:
        raise SystemExit(f"NEW500 derivation yields {len(new500_ids)} ids")
    new500_receipt_path = REPO / NEW500_RECEIPT_RELPATH
    measured_new500 = sha256_file(new500_receipt_path)
    if measured_new500 != NEW500_RECEIPT_SHA256:
        raise SystemExit(
            f"NEW500 receipt hashes to {measured_new500}, not the registered "
            f"{NEW500_RECEIPT_SHA256}"
        )
    new500_receipt = json.loads(new500_receipt_path.read_text(encoding="utf-8"))
    if new500_receipt.get("split_identity_hash") != NEW500_RECEIPT_SPLIT_IDENTITY:
        raise SystemExit("NEW500 receipt split identity drifted")
    if new500_receipt.get("run_identity_hash") != NEW500_RUN_IDENTITY:
        raise SystemExit("NEW500 receipt run identity drifted")
    receipt_ids = sorted(item["id"] for item in new500_receipt["items"])
    if receipt_ids != new500_ids:
        raise SystemExit(
            "NEW500 receipt items disagree with the DEV-1000 minus DEV-500 "
            "derivation (if the intersection is EMPTY, the comparison is "
            "reading the receipt's 'key' field instead of 'id')"
        )
    if set(receipt_ids) & set(dev500_ids):
        raise SystemExit("NEW500 is not disjoint from the exposed DEV-500")
    if sorted(set(receipt_ids) | set(dev500_ids)) != dev1000_ids:
        raise SystemExit("NEW500 union DEV-500 is not exactly DEV-1000")
    view_seconds = {item["sample_id"]: float(item["audio_seconds"]) for item in view["items"]}
    new500_audio = sum(view_seconds[sid] for sid in new500_ids)
    if abs(new500_audio - NEW500_AUDIO_SECONDS_TOTAL) > 1e-3:
        raise SystemExit(
            f"NEW500 audio total {new500_audio:.4f} != pinned "
            f"{NEW500_AUDIO_SECONDS_TOTAL}"
        )
    # The canary/resend pair must live in the EXPOSED half, so the rail's own
    # contacts can never add exposure to the lock statistic's population.
    if not set(CANARY_SAMPLE_IDS) <= set(dev500_ids):
        raise SystemExit(
            "the canary pair is not inside the exposed DEV-500: a rail contact "
            "would touch the unexposed statistic population"
        )
    if set(CANARY_SAMPLE_IDS) & set(new500_ids):
        raise SystemExit("the canary pair intersects the unexposed 500")
    log(
        f"NEW500 partition PROVED: {len(new500_ids)} ids = DEV-1000 minus "
        f"DEV-500, receipt-equal (compared on 'id'), disjoint from the exposed "
        f"500, union exact, {new500_audio:.3f} audio-s; canary pair "
        f"{CANARY_SAMPLE_IDS} lies inside the EXPOSED half"
    )
    flight["new500_partition"] = {
        "count": len(new500_ids),
        "audio_seconds_total": round(new500_audio, 4),
        "receipt_split_identity": NEW500_RECEIPT_SPLIT_IDENTITY,
        "receipt_run_identity": NEW500_RUN_IDENTITY,
        "receipt_sha256": measured_new500,
        "flown_by_any_arm": False,
        "note": (
            "PROOF ONLY -- both arms fly the full DEV-1000; the lock "
            "statistic's partition belongs to the separately registered "
            "one-touch read"
        ),
        "canary_inside_exposed_half": True,
    }

    # ---- knowledge snapshot + SEALED-value discipline ---------------------
    snapshot_path = root / "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise SystemExit("knowledge snapshot content hash mismatch")
    log(f"TRAIN snapshot verified: {len(snapshot.facets)} facets / {len(snapshot.values)} values")

    facet_vector_table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    if arm_id == "BLEND":
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
        for index, facet_id in enumerate(facet_ids):
            facet_vector_table[facet_id] = {"content": tuple(facet_matrix[index].tolist())}
        log(
            f"content-facet vectors loaded: {facet_matrix.shape} ({measured_npz[:12]}…). "
            "VALUE VECTORS SEALED: vectors-values.npz is NOT loaded by this flight."
        )
        flight["knowledge"] = {
            "snapshot_sha256": SNAPSHOT_SHA256,
            "facet_vectors_npz_sha256": measured_npz,
            "value_vectors_loaded": False,
            "percept_admission": "facet-side (fuser construction)",
        }
    else:
        log(
            "content-facet embedding vectors NOT loaded for this arm (M0/ablation); "
            "VALUE VECTORS SEALED as always"
        )
        flight["knowledge"] = {
            "snapshot_sha256": SNAPSHOT_SHA256,
            "facet_vectors_npz_loaded": False,
            "value_vectors_loaded": False,
        }

    content_facet_ids = sorted(
        facet.facet_id for facet in snapshot.facets if facet.dimension == "content"
    )
    if not content_facet_ids:
        raise SystemExit("snapshot has no content-dimension facets")

    save_flight()

    # ---- samples (model-free; hashes only the view files) ------------------
    adapter = Dev1000Adapter(
        lock, root, repo_root=REPO, view_items=view["items"], new500_ids=new500_ids
    )
    log(f"loading the DEV-1000 view (per-file sha256 against the view), arm split {split_id}")
    all_samples = adapter.load_split(SPLIT_ID)
    if len(all_samples) != SPLIT_COUNT:
        raise SystemExit(f"{len(all_samples)} samples, expected {SPLIT_COUNT}")
    samples = adapter.load_split(split_id)
    if split_id != SPLIT_ID or len(samples) != SPLIT_COUNT:
        raise SystemExit(
            f"arm {arm_id} resolved {len(samples)} samples of split {split_id!r}; both "
            f"lock arms MUST fly the full {SPLIT_ID} ({SPLIT_COUNT} samples)"
        )
    loop_audio = sum(float(s.audio_seconds) for s in samples)
    log(f"arm split {split_id}: {len(samples)} samples, one metered pass = {loop_audio:.6f}s")

    packet_bindings: dict[str, dict[str, str]] = {}
    for item in view["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        packet_bindings[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    if set(packet_bindings) != {s.sample_id for s in all_samples}:
        raise SystemExit("packet bindings do not cover the DEV-1000 view")
    log(f"speech packet bindings materialized for all {SPLIT_COUNT} samples")

    payload_binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=all_samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    log("payload binding built (inputs complete, still pre-gate)")

    # ---- attempt-1 durable M0 trace: byte identity + HASH INDEX ONLY ------
    a1_run_dir = root / "runs" / A1_RUN_ID / A1_ATTEMPT_ID
    a1_trace_path = a1_run_dir / f"{A1_RUN_ID}.trace.jsonl"
    measured_a1_trace = sha256_file(a1_trace_path)
    if measured_a1_trace != A1_TRACE_SHA256:
        raise SystemExit(
            f"attempt-1 trace hashes to {measured_a1_trace}, not the registered "
            f"{A1_TRACE_SHA256}; the canary hash authority cannot be identified"
        )
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
    for canary_sid in CANARY_SAMPLE_IDS:
        if canary_sid not in a1_m0_response_sha:
            raise SystemExit(f"attempt-1 M0 hash index lacks canary sample {canary_sid}")
    log(
        f"attempt-1 M0 trace verified ({measured_a1_trace[:12]}…, hash-index "
        f"authority over {len(a1_m0_response_sha)} samples)"
    )

    # ---- rails invariants: the f1060078 repair stays live ------------------
    import subprocess as _subprocess

    if default_label_normalizer(
        '{"scenario": "alarm", "action": "query", "entities": []}',
        {"facet:a": "alarm_query"},
    ) != "facet:a" or default_label_normalizer(
        '{"scenario": "query", "action": "alarm", "entities": []}',
        {"facet:a": "alarm_query"},
    ) is not None:
        raise SystemExit(
            "invariant MISSING: the imported rails.kb_policy does not carry the "
            "f1060078 label-identity binding repair; refusing"
        )
    kb_policy_last_commit = _subprocess.run(
        [
            "git", "-C", str(REPO), "log", "-1", "--format=%H", "--",
            "src/speech_aware_evidence_acquisition/rails/kb_policy.py",
        ],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    if not kb_policy_last_commit.startswith("f1060078"):
        raise SystemExit(
            f"rails/kb_policy.py's last commit is {kb_policy_last_commit[:12]}, not "
            "the repair commit f1060078 — rails/ was touched; refusing"
        )
    repo_head_commit = _subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    flight["invariants"] = {
        "kb_policy_last_commit": kb_policy_last_commit,
        "repo_head_at_flight": repo_head_commit,
        "behavior_probe": "PASS (identity exact-match live, swap refused)",
        "frozen_cell": "byte-frozen DEV-100 cell (no knob change this campaign)",
    }
    log(
        f"invariants: kb_policy last commit {kb_policy_last_commit[:12]}, repo HEAD "
        f"{repo_head_commit[:12]}, behavior probe PASS"
    )

    # ---- model-free dry check: registered chain vs the runner's guard ------
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
    dry_contract = adapter.build_task_contract(dry_sample, default_obs_packet(dry_sample))
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
        ranker=rank_wcos_prior_agree_factory(RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)),
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
    dry_plan_contact = dry_controller.initial_contact(dry_context)
    if dry_plan_contact.instruction != DIRECT_REFERENCE_INSTRUCTION:
        raise SystemExit(
            "rails-rendered direct instruction differs from the registered bytes; refusing"
        )
    _assert_agent_control_excludes_knowledge_payloads(dry_plan_contact, protected)
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
        "dry check PASS: rails-rendered direct instruction byte-identical to the "
        f"registered form; instructions clear all {len(protected)} protected payloads"
    )

    # ---- pre-takeoff AttemptStore inspection + fail-closed sizing guard ----
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(RUN_ID)
    prior_records = sorted(
        p.name for p in (root / "attempts" / RUN_ID).glob("*.json")
    ) if (root / "attempts" / RUN_ID).is_dir() else []
    canary_samples_audio = sum(
        float(s.audio_seconds) for s in adapter.load_split(CANARY_SPLIT_ID)
    )
    resend_audio = float(adapter.load_split(RESEND_SPLIT_ID)[0].audio_seconds) if with_resend else 0.0
    worst_core = CANARY_SAMPLE_COUNT * 2 + len(samples) * max_contacts + (1 if with_resend else 0)
    worst_audio = (
        canary_samples_audio * 2
        + loop_audio * max_contacts
        + resend_audio
    )
    if worst_core > attempt_core_ceiling:
        raise SystemExit(
            f"attempt worst case {worst_core} exceeds the registered attempt core "
            f"ceiling {attempt_core_ceiling}; refusing"
        )
    if prior_calls + worst_core > min(plan_calls, CAMPAIGN_CEILING_CORE):
        raise SystemExit(
            f"REFUSED TAKEOFF at zero spend: durable prior {prior_calls} calls + "
            f"worst case {worst_core} exceeds min(plan {plan_calls}, campaign "
            f"{CAMPAIGN_CEILING_CORE}); the campaign row's fail-closed sizing guard"
        )
    if prior_audio + worst_audio > min(plan_audio, CAMPAIGN_CEILING_AUDIO):
        raise SystemExit(
            f"REFUSED TAKEOFF at zero spend: durable prior {prior_audio:.2f} audio-s "
            f"+ worst case {worst_audio:.2f} exceeds min(plan {plan_audio}, campaign "
            f"{CAMPAIGN_CEILING_AUDIO}); the campaign row's fail-closed sizing guard"
        )
    flight["pre_takeoff_attempt_store"] = {
        "prior_records": prior_records,
        "prior_calls": prior_calls,
        "prior_audio_seconds": prior_audio,
        "worst_case_core_this_attempt": worst_core,
        "worst_case_audio_this_attempt": round(worst_audio, 6),
    }
    log(
        f"AttemptStore pre-takeoff: {len(prior_records)} prior records, "
        f"{prior_calls} calls / {prior_audio:.2f} audio-s durable; this attempt "
        f"worst case {worst_core} calls / {worst_audio:.2f} audio-s fits plan "
        f"{plan_calls}/{plan_audio} and campaign {CAMPAIGN_CEILING_CORE}/"
        f"{CAMPAIGN_CEILING_AUDIO}"
    )
    save_flight()

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
        planned_model_calls=plan_calls,
        planned_gpu_hours=plan_gpu,
        planned_speech_audio_seconds=plan_audio,
        protocol_hash=composed.config_hash,
        attempt_id=attempt_id,
    ).validate()
    (run_dir / "execution-plan.json").write_text(
        json.dumps(
            {
                "attempt_id": plan.attempt_id,
                "arm_id": arm_id,
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
            "four-arm prompt-fit no longer stands; STOP and respawn per the attempt-6 "
            "recipe plus a FRESH prompt-fit row"
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
        request_id_prefix=f"dev1000{slug}",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    log(f"FrozenCoreClient constructed (arm {client.arm})")

    # ---- embedding sidecar (BLEND arm only; own session + stop receipt) ----
    meter: EmbeddingMeter | None = None
    emb_session = None
    emb_client = None
    emb_runtime_receipt = None
    jitter_start = None
    jitter_text = None
    embed_lock = threading.Lock()
    if with_sidecar:
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

        meter = EmbeddingMeter(attempt_tool_ceiling, run_dir / "embedding-contacts.jsonl")
        emb_client = EmbeddingClient(
            base_url=f"http://127.0.0.1:{EMB_PORT}",
            post=guarded_post(600.0),
            timeout_seconds=600.0,
            expected_dim=EMBEDDER_DIM,
            require_marker_verification=False,
        )
        assert_client_surface_is_encode_only(emb_client)
        emb_client.verify_media_marker()

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

    # ---- serving telemetry (NOT_AVAILABLE-tolerant; Windows-side binary) --
    sampler = resolve_resource_sampler(
        binary="/mnt/c/Windows/System32/nvidia-smi.exe",
        interval_seconds=5.0,
        slots_url=f"http://127.0.0.1:{DECODER_PORT}/slots",
    )
    sampler.start()
    sampler.begin_request_window()

    main_summary = None
    controllers_by_sample: dict[str, object] = {}
    # v2 override state. Populated ONLY on the BLEND arm; initialized here so
    # the report block and every abort path can read it unconditionally
    # (the A4 lesson: a name defined only inside one arm's branch is a
    # NameError waiting for the other arm's report).
    delta_records: dict[str, dict[str, object]] = {}
    override_normalizers: dict[str, "DeltaOverrideNormalizer"] = {}
    outcome_status = "ABORTED"
    contact_total = 0
    canary_fail_message: str | None = None
    sentinel_trip_message: str | None = None
    main_sentinel: DecodeRateSentinel | None = None
    main_buffer: TraceBuffer | None = None
    micro_run_sink_ids: dict[str, frozenset] = {}
    main_sink_ids: frozenset = frozenset()
    flight_started = time.time()
    metered_client = CoreCeilingClient(client, attempt_core_ceiling)
    server_log_path = SESSION_DIR / "server.log"
    canary_log_offset = 0
    main_log_offset = 0
    resend_log_offset = 0
    resend_record: dict[str, object] = {"flown": False, "reason": "not a BLEND-arm rail"}

    def flush_partial_main() -> None:
        """Durable-first discipline on an abort path."""

        nonlocal main_sink_ids
        if main_buffer is None or not main_buffer.records:
            return
        partial_ids = [record_id for _, record_id, _ in main_buffer.records]
        try:
            client.flush_trace_buffer(main_buffer)
            main_sink_ids = main_sink_ids | frozenset(partial_ids)
            flight["main_partial_flush"] = {"flushed_records": len(partial_ids)}
            log(
                f"durable-first: {len(partial_ids)} partial main-loop trace records "
                "flushed into the main sink"
            )
        except Exception as flush_error:  # noqa: BLE001 — report, never mask
            flight["main_partial_flush"] = {"error": repr(flush_error)}
            log(f"durable-first partial flush FAILED: {flush_error!r}")

    try:
        # ---------------- M0 controller factory (canary/resend + M0 arm) ---
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

        # ---------------- Decode-speed CANARY (before the main loop) -------
        canary_samples = adapter.load_split(CANARY_SPLIT_ID)
        canary_ids = [sample.sample_id for sample in canary_samples]
        canary_log_offset = server_log_path.stat().st_size
        canary_registry = Registry(f"dev1000 {slug} canary controller")
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
            split_id=CANARY_SPLIT_ID,
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
        canary_contacts = sum(len(result.contacts) for result in canary_summary.results)
        contact_total += canary_contacts
        canary_wall = time.time() - canary_started
        time.sleep(1.0)
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
                    "byte_identical_to_attempt1": sha256_text(result.final_response_text)
                    == a1_m0_response_sha[result.sample_id],
                }
                for result in canary_summary.results
            },
            "note": (
                "responses never read semantically: sha256 + server print_timing "
                "descriptives only (registered canary semantics; SAME BASE-build "
                "service instance the DEV-100 campaign proved byte-identical to "
                "attempt-1 M0)"
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
                f"canary timing lines incomplete: {len(generation_rows)} generation "
                f"rows for {canary_contacts} contacts; refusing to fly the main "
                "loop without a decode-speed verdict"
            )
        worst_rate = max(row["ms_per_token"] for row in generation_rows)
        canary_record["worst_generation_ms_per_token"] = worst_rate
        canary_record["passed"] = worst_rate < CANARY_MS_PER_TOKEN_PASS
        save_flight()
        if not canary_record["passed"]:
            raise CanaryFail(
                "decode-speed canary FAILED: generation rates "
                f"{[row['ms_per_token'] for row in generation_rows]} ms/token vs "
                f"the registered pass threshold {CANARY_MS_PER_TOKEN_PASS}; the "
                "main loop is NOT flown; the service is left up"
            )
        log(
            "CANARY PASS: generation "
            f"{[row['ms_per_token'] for row in generation_rows]} ms/token "
            f"(worst {worst_rate})"
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
            log("canary bytes MATCH attempt-1 M0 (continuity confirmed)")
        else:
            log(
                "canary bytes DIFFER from attempt-1 M0 (UNEXPECTED on this build): "
                "re-running the pair once — within-build determinism is REQUIRED"
            )
            rerun_buffer = TraceBuffer(plan.run_id)
            rerun_registry = Registry(f"dev1000 {slug} canary rerun controller")
            rerun_registry.register(M0_POLICY_ID, m0_factory)
            rerun_log_offset = server_log_path.stat().st_size
            rerun_summary = run_speech_native_agent_loop(
                data_root=root,
                plan=plan,
                adapter=adapter,
                core_client=metered_client,
                split_id=CANARY_SPLIT_ID,
                knowledge_snapshot=snapshot,
                speech_packet_bindings={
                    sample_id: packet_bindings[sample_id] for sample_id in canary_ids
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
            rerun_record_ids = flush_micro_run_buffer(rerun_buffer, rerun_sink, "canary-rerun")
            rerun_manifest_hash = rerun_sink.close()
            micro_run_sink_ids["canary_rerun"] = frozenset(rerun_record_ids)
            rerun_contacts = sum(len(result.contacts) for result in rerun_summary.results)
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
                "response_sha256": dict(sorted(rerun_sha.items())),
                "within_build_byte_identical_to_first_run": within_build_identical,
                "trace": {
                    "sink_dir": str(run_dir / "canary-rerun-trace"),
                    "record_ids": len(rerun_record_ids),
                    "namespace": "canary-rerun/",
                    "manifest_hash": rerun_manifest_hash,
                },
            }
            canary_record["decode_divergence"] = {
                "attempt1_m0_response_sha256": {
                    sample_id: a1_m0_response_sha[sample_id] for sample_id in canary_ids
                },
                "flown_response_sha256": dict(sorted(first_run_sha.items())),
                "note": "recorded as a caveat traveling with the arm report",
            }
            save_flight()
            if len(rerun_rows) != rerun_contacts:
                raise CanaryFail(
                    f"canary re-run timing lines incomplete: {len(rerun_rows)} rows "
                    f"for {rerun_contacts} contacts; refusing"
                )
            rerun_worst = max(row["ms_per_token"] for row in rerun_rows)
            if rerun_worst >= CANARY_MS_PER_TOKEN_PASS:
                raise CanaryFail(
                    f"canary re-run FAILED the timing gate: worst {rerun_worst} "
                    "ms/token; the main loop is NOT flown; the service is left up"
                )
            if not within_build_identical:
                raise CanaryFail(
                    "WITHIN-build determinism FAILED: canary re-run responses are "
                    "not byte-identical to the first run on the SAME binary; "
                    "stopping fail-closed before the main loop"
                )
            log("canary re-run PASS: within-build determinism confirmed; caveat recorded")
        save_flight()

        # ---------------- ARM main loop ------------------------------------
        main_registry = Registry(f"dev1000 {slug} main controller")
        if arm_id == "M0":
            controller_policy_id = M0_POLICY_ID

            def main_factory(sample_id: str):
                controller = m0_factory(sample_id)
                controllers_by_sample[sample_id] = controller
                return controller

            main_registry.register(M0_POLICY_ID, main_factory)
        else:  # BLEND — the FROZEN v2 cell (v1 knobs + the delta override)
            controller_policy_id = CONTROLLER_POLICY_ID
            cells = {sample.sample_id: LazyQueryVector() for sample in samples}
            delta_table = DeltaSignalTable(snapshot, facet_vector_table)
            if len(delta_table.label_targets) != 60:
                raise SystemExit(
                    "v2 delta table: expected the 60-way TRAIN label vocabulary, "
                    f"got {len(delta_table.label_targets)} label identities"
                )
            log(
                "v2 delta table built from the frozen snapshot: "
                f"{len(delta_table.label_targets)} label identities, "
                f"{len(delta_table.content_facet_target)} content facets carrying "
                f"a task target, {len(delta_table.facets_by_target)} targets with "
                "vectored facets (the cos_direct population)"
            )
            delta_lock = threading.Lock()
            # The ranker/fuser the override replay uses are constructed from
            # the SAME frozen knobs the registered controller is built with,
            # through the SAME kb_policy factories -- not a reimplementation.
            override_ranker = rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
            override_fuser = fuse_supplyfilter_factory(FROZEN_FUSE)

            def override_normalizer_for(sample_id: str) -> DeltaOverrideNormalizer:
                normalizer = DeltaOverrideNormalizer(
                    sample_id=sample_id,
                    snapshot=snapshot,
                    table=delta_table,
                    facet_vectors=lambda facet_id: facet_vector_table.get(facet_id, {}),
                    cell=cells[sample_id],
                    query_state=QueryState(
                        query_id=f"v2delta:{sample_id}",
                        query_sample_id=sample_id,
                        speech_packet_id=packet_bindings[sample_id]["packet_id"],
                        speech_packet_sha256=packet_bindings[sample_id]["sha256"],
                        use_split_identity_hash=SPLIT_IDENTITY_HASH,
                        use_partition_role="dev",
                    ).validate(),
                    ranker=override_ranker,
                    fuser=override_fuser,
                    sink=delta_records,
                    lock=delta_lock,
                )
                override_normalizers[sample_id] = normalizer
                return normalizer

            # One controller factory PER SAMPLE, because the injected
            # normalizer is per-sample state. Every other keyword is the
            # frozen v1 cell, byte-unchanged.
            def kb_factory(sample_id: str):
                per_sample = make_kb_alpha_blend_controller_factory(
                    snapshot=snapshot,
                    query_vectors_by_sample={
                        sample_id: {"content": cells[sample_id]}
                    },
                    facet_vectors=lambda facet_id: facet_vector_table.get(facet_id, {}),
                    normalizer=override_normalizer_for(sample_id),
                    rank_weights=FROZEN_WEIGHTS,
                    fuse_knobs=FROZEN_FUSE,
                    alpha=FROZEN_ALPHA,
                    top_k_per_dimension=FROZEN_TOP_K,
                )
                return per_sample(sample_id)

            def main_factory(sample_id: str):
                controller = RuntimeEmbeddedBlendController(
                    kb_factory(sample_id),
                    sample_id=sample_id,
                    cell=cells[sample_id],
                    embed=embed_query_text,
                    override_normalizer=override_normalizers[sample_id],
                )
                controllers_by_sample[sample_id] = controller
                return controller

            main_registry.register(CONTROLLER_POLICY_ID, main_factory)
            log(
                f"ARM BLEND controller = the FROZEN v2 LOCK CANDIDATE (alpha="
                f"{FROZEN_ALPHA}, tau={FROZEN_TAU}, top_k={FROZEN_TOP_K}, fusion "
                f"m={FROZEN_FUSE.m}/c={FROZEN_FUSE.c}/l={FROZEN_FUSE.top_l}, "
                f"f1060078 repair live) PLUS the registered RETAIN-OVERRIDE at "
                f"delta >= {DELTA_BAR} with the mandatory disagreement condition"
            )

        log(
            f"ARM {arm_id} MAIN LOOP START ({len(samples)} samples x max "
            f"{max_contacts} contacts, policy {controller_policy_id}): <= "
            f"{attempt_core_ceiling} core contacts (hard meter); sentinel ARMED "
            f"(rolling median over {SENTINEL_WINDOW_CONTACTS} > "
            f"{SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT:.0f} ms/token aborts)"
        )
        main_buffer = TraceBuffer(plan.run_id)
        main_log_offset = server_log_path.stat().st_size
        main_sentinel = DecodeRateSentinel(server_log_path, main_log_offset)
        metered_client.arm_sentinel(main_sentinel)
        main_started = time.time()
        main_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=metered_client,
            split_id=split_id,
            knowledge_snapshot=snapshot,
            speech_packet_bindings={
                sample.sample_id: packet_bindings[sample.sample_id] for sample in samples
            },
            controller_policy_id=controller_policy_id,
            max_contacts=max_contacts,
            slot_count=server_np,
            queue_depth=server_np,
            trace_sink=main_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=main_registry,
        )
        metered_client.arm_sentinel(None)
        main_contacts = sum(len(result.contacts) for result in main_summary.results)
        contact_total += main_contacts
        main_record_ids = [record_id for _, record_id, _ in main_buffer.records]
        flight["core_contacts_total_pre_flush"] = contact_total
        save_flight()
        client.flush_trace_buffer(main_buffer)
        main_sink_ids = frozenset(main_record_ids)
        main_buffer = None
        log(
            f"ARM {arm_id} main loop flushed FIRST into the main sink: "
            f"{len(main_record_ids)} records"
        )
        log(f"ARM {arm_id} MAIN LOOP DONE in {time.time() - main_started:.1f}s: {main_contacts} contacts")
        time.sleep(1.0)
        with server_log_path.open("rb") as log_handle:
            log_handle.seek(main_log_offset)
            main_timing = parse_print_timing(log_handle.read())
        gen_rates = sorted(row["ms_per_token"] for row in main_timing["generation"])
        flight["main_print_timing"] = {
            "generation_rows": len(gen_rates),
            "ms_per_token_min": gen_rates[0] if gen_rates else None,
            "ms_per_token_median": gen_rates[len(gen_rates) // 2] if gen_rates else None,
            "ms_per_token_max": gen_rates[-1] if gen_rates else None,
        }
        save_flight()

        # ---------------- identical-prompt resend pair (BLEND arm only) ----
        resend_log_offset = server_log_path.stat().st_size
        if with_resend:
            if contact_total + 1 <= attempt_core_ceiling:
                resend_sample = adapter.load_split(RESEND_SPLIT_ID)[0]
                resend_registry = Registry(f"dev1000 {slug} resend controller")
                resend_registry.register(M0_POLICY_ID, m0_factory)
                resend_buffer = TraceBuffer(plan.run_id)
                resend_summary = run_speech_native_agent_loop(
                    data_root=root,
                    plan=plan,
                    adapter=adapter,
                    core_client=metered_client,
                    split_id=RESEND_SPLIT_ID,
                    knowledge_snapshot=snapshot,
                    speech_packet_bindings={
                        resend_sample.sample_id: packet_bindings[resend_sample.sample_id]
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
                resend_record_ids = flush_micro_run_buffer(resend_buffer, resend_sink, "resend")
                resend_manifest_hash = resend_sink.close()
                micro_run_sink_ids["resend"] = frozenset(resend_record_ids)
                contact_total += 1
                base_sha = a1_m0_response_sha[resend_sample.sample_id]
                resend_text = resend_summary.results[0].final_response_text
                resend_record = {
                    "flown": True,
                    "sample_id": resend_sample.sample_id,
                    "server_np": server_np,
                    "response_a_sha256": base_sha,
                    "response_b_sha256": sha256_text(resend_text),
                    "byte_identical": base_sha == sha256_text(resend_text),
                    "note": (
                        "byte-identical direct-decode PROMPT by construction; response "
                        "A is attempt-1's recorded M0 hash (zero-copy), response B a "
                        "fresh single-slot decode on the SAME BASE-build instance; "
                        "sha256 equality only"
                    ),
                    "trace": {
                        "sink_dir": str(run_dir / "resend-trace"),
                        "record_ids": len(resend_record_ids),
                        "namespace": "resend/",
                        "manifest_hash": resend_manifest_hash,
                    },
                }
                log(
                    f"resend pair (sample {resend_sample.sample_id}, -np {server_np}): "
                    f"byte_identical={resend_record['byte_identical']}"
                )
            else:
                resend_record = {
                    "flown": False,
                    "reason": (
                        f"attempt core ceiling {attempt_core_ceiling} fully consumed "
                        f"({contact_total} contacts); resend skipped and disclosed"
                    ),
                }
                log("resend SKIPPED: no core-contact headroom (disclosed)")
        flight["resend_pair"] = resend_record

        assert_zero_record_id_overlap({"main": main_sink_ids, **micro_run_sink_ids})
        flight["trace_isolation"] = {
            "main_sink_records": len(main_sink_ids),
            "canary_sink_records": len(micro_run_sink_ids.get("canary", frozenset())),
            "canary_rerun_sink_records": len(micro_run_sink_ids.get("canary_rerun", frozenset())),
            "resend_sink_records": len(micro_run_sink_ids.get("resend", frozenset())),
            "zero_record_id_overlap_asserted": True,
            "flush_order": "canary (own sink) -> main loop (main sink FIRST) -> resend (own sink)",
        }
        log(
            "trace isolation verified: zero record-id overlap across "
            f"main ({len(main_sink_ids)}) and micro-run sinks"
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
        flush_partial_main()
    except Exception as error:
        if main_sentinel is not None and main_sentinel.tripped is not None:
            sentinel_trip_message = f"{main_sentinel.tripped} (surfaced wrapped as: {error!r})"
            outcome_status = "SENTINEL_ABORT_STOP"
            log(f"SENTINEL TRIP (wrapped): {sentinel_trip_message}")
            flush_partial_main()
        else:
            flush_partial_main()
            raise
    finally:
        sampler.end_request_window()
        sampler.stop()
        telemetry = dict(sampler.summary())
        flight["serving_descriptives"] = telemetry
        flight["core_contacts_total"] = contact_total
        flight["sentinel"] = main_sentinel.summary() if main_sentinel is not None else None
        flight["outcome_status"] = outcome_status
        save_flight()

        if with_sidecar and emb_client is not None:
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
                    "ceiling": attempt_tool_ceiling,
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
        else:
            flight["embedding_accounting"] = {"tool_contacts": 0, "ceiling": attempt_tool_ceiling}
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

    tool_contacts_used = meter.count if meter is not None else 0
    cost = flight["core_client"]["cost"]
    audio_seconds_metered = cost.get("audio_seconds_used") if isinstance(cost, Mapping) else None

    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)

    # ---- canary-fail / sentinel-trip hard stops (no scoring, no gold) -----
    if canary_fail_message is not None or sentinel_trip_message is not None:
        stop_kind = "canary-stop" if canary_fail_message is not None else "sentinel-abort"
        stop_record = {
            "schema": f"saea-dev1000-baseline-lock-{report_stub}-{stop_kind}-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": RUN_ID,
            "arm_id": arm_id,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "outcome": outcome_status,
            "verbatim": canary_fail_message or sentinel_trip_message,
            "canary": flight.get("canary"),
            "sentinel": flight.get("sentinel"),
            "mid_flight_clock_samples_windows_side": read_clock_samples(root, slug),
            "durable_flush": {
                "canary_sink": flight.get("canary", {}).get("trace")
                if isinstance(flight.get("canary"), dict)
                else None,
                "main_partial_flush": flight.get("main_partial_flush"),
            },
            "spend": {
                "arm_core_contacts": contact_total,
                "arm_tool_contacts": tool_contacts_used,
                "core_client": flight["core_client"],
            },
            "boundary": (
                "gold never opened; no response read semantically; the arm is NOT "
                "mechanically landed as complete; everything durable was flushed; "
                "the resident service and keepalive are left up. A sentinel trip "
                "STOPS THE MISSION — no later arm flies on a sick GPU (registered "
                "campaign-row rail)."
            ),
        }
        stop_path = OUT_CHECK_DIR / f"{report_stub}-{stop_kind}.json"
        stop_path.write_text(
            json.dumps(stop_record, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        flight["stop_record_path"] = str(stop_path)
        save_flight()
        log(f"STOP RECORD written: {stop_path}")
        log(f"VERBATIM: {stop_record['verbatim']}")
        return 4 if canary_fail_message is not None else 5

    # ---- MECHANICAL landing: gold-free per-sample records + arm report ----
    # (NO adapter gold access; response texts land OPAQUE in the run dir for
    # the later, separately registered one-touch read.)
    mech_rows: dict[str, dict[str, object]] = {}
    for result in main_summary.results:
        controller = controllers_by_sample.get(result.sample_id)
        mech_rows[result.sample_id] = {
            "contacts": len(result.contacts),
            "slot_ids": [record.slot_id for record in result.contacts],
            "response_sha256": sha256_text(result.final_response_text),
            "direct_response_sha256": (
                getattr(controller, "direct_response_sha256", None)
                if max_contacts > 1
                else sha256_text(result.final_response_text)
            ),
            "retained_primary": len(result.contacts) == 1,
            "direct_label_recovered": (
                getattr(
                    controller,
                    "direct_label_recovered",
                    getattr(controller, "_direct_label", None),
                )
                is not None
                if controller is not None
                else None
            ),
            "winner_label_present": (
                getattr(controller, "last_winner_label", None) is not None
                if controller is not None
                else None
            ),
            # v2 override observability (BLEND only; None on M0). Gold-free:
            # these are cosines over the trajectory's own query vector and the
            # frozen TRAIN snapshot.
            "override_fires": delta_records.get(result.sample_id, {}).get("override_fires"),
            "delta": delta_records.get(result.sample_id, {}).get("delta"),
            "cos_top1": delta_records.get(result.sample_id, {}).get("cos_top1"),
            "cos_direct": delta_records.get(result.sample_id, {}).get("cos_direct"),
            "direct_target": delta_records.get(result.sample_id, {}).get("direct_target"),
            "fused_top1_target": delta_records.get(result.sample_id, {}).get(
                "fused_top1_target"
            ),
            "disagrees": delta_records.get(result.sample_id, {}).get("disagrees"),
            "override_reason": delta_records.get(result.sample_id, {}).get("reason"),
            "direct_label_suppressed_by_override": (
                getattr(controller, "direct_label_suppressed_by_override", None)
                if controller is not None
                else None
            ),
            # The branch-only proof material: the controller's OWN flown
            # supply, recorded so the post-seal read can compare it against
            # the launcher-side replay without re-running anything.
            "fusion_selected_value_ids": (
                getattr(controller, "fusion_selected_value_ids", None)
                if controller is not None
                else None
            ),
            "replay_selected_value_ids": delta_records.get(result.sample_id, {}).get(
                "replay_selected_value_ids"
            ),
        }
    if {s.sample_id for s in samples} != set(mech_rows):
        raise SystemExit("main-loop results do not cover the arm split exactly")
    if arm_id == "BLEND" and set(delta_records) != {s.sample_id for s in samples}:
        raise SystemExit(
            f"the v2 override normalizer produced a delta record for "
            f"{len(delta_records)} of {len(samples)} samples; the override did "
            "not run on every trajectory"
        )

    outputs_path = run_dir / f"{report_stub}-outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as sink:
        for result in main_summary.results:
            controller = controllers_by_sample.get(result.sample_id)
            sink.write(
                json.dumps(
                    {
                        "arm": arm_id,
                        "sample_id": result.sample_id,
                        "final_response_text": result.final_response_text,
                        "contacts": len(result.contacts),
                        "slot_ids": [record.slot_id for record in result.contacts],
                        "winner_label": getattr(controller, "last_winner_label", None),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    (run_dir / f"{report_stub}-mechanical.json").write_text(
        json.dumps(mech_rows, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log(f"opaque outputs written: {outputs_path} (never read semantically this mission)")

    retained_count = sum(1 for row in mech_rows.values() if row["retained_primary"])
    dispatched_count = sum(1 for row in mech_rows.values() if row["contacts"] == 2)
    label_recovered_count = sum(
        1 for row in mech_rows.values() if row["direct_label_recovered"] is True
    )
    # Dispatch decomposition (BLEND only). A dead-direct dispatch is the v1
    # predicate firing (the direct answer named no TRAIN intent); an override
    # dispatch is the registered v2 addition. The two are disjoint by
    # construction: the override only inspects live-direct trajectories.
    override_fired_count = sum(
        1 for row in mech_rows.values() if row["override_fires"] is True
    )
    override_dispatched_count = sum(
        1
        for row in mech_rows.values()
        if row["override_fires"] is True and row["contacts"] == 2
    )
    dead_direct_dispatched_count = sum(
        1
        for row in mech_rows.values()
        if row["contacts"] == 2
        and row["direct_label_recovered"] is not True
    )
    delta_defined = [
        float(row["delta"]) for row in mech_rows.values() if row["delta"] is not None
    ]
    delta_distribution = (
        {
            "n": len(delta_defined),
            "min": min(delta_defined),
            "p50": statistics.median(delta_defined),
            "max": max(delta_defined),
            "at_or_above_bar": sum(
                1 for d in delta_defined if d >= DELTA_BAR - DELTA_EPS
            ),
        }
        if delta_defined
        else None
    )
    # Branch-only (supply-identity) check, computed HERE so a violation is
    # visible at landing rather than at the read: on every trajectory that
    # dispatched, the launcher-side replay's supply must equal the
    # controller's own flown FusionDecision supply.
    supply_mismatches = sorted(
        sid
        for sid, row in mech_rows.items()
        if row["replay_selected_value_ids"] is not None
        and row["fusion_selected_value_ids"] is not None
        and tuple(row["replay_selected_value_ids"]) != tuple(row["fusion_selected_value_ids"])
    )

    # ---- prompt-reuse analysis (content-free token counts) ----------------
    with server_log_path.open("rb") as log_handle:
        log_handle.seek(canary_log_offset)
        canary_window_bytes = log_handle.read(main_log_offset - canary_log_offset)
        main_window_bytes = log_handle.read(resend_log_offset - main_log_offset)
        resend_window_bytes = log_handle.read()
    canary_requests = parse_slot_requests(canary_window_bytes)
    main_requests = parse_slot_requests(main_window_bytes)
    resend_requests = parse_slot_requests(resend_window_bytes)
    all_requests = canary_requests + main_requests + resend_requests
    prompt_tokens_total_client = (
        cost.get("prompt_tokens_total") if isinstance(cost, Mapping) else None
    )
    sum_release_minus_gen = sum(
        row["release_n_tokens"] - row["generation_tokens"] for row in all_requests
    )
    per_request_offset: object = "UNDETERMINED"
    if isinstance(prompt_tokens_total_client, int) and all_requests:
        offset_delta = prompt_tokens_total_client - sum_release_minus_gen
        if offset_delta % len(all_requests) == 0 and abs(offset_delta) <= 2 * len(all_requests):
            per_request_offset = offset_delta // len(all_requests)
    offset_int = per_request_offset if isinstance(per_request_offset, int) else 0

    def declared_tokens(row: Mapping[str, int]) -> int:
        return row["release_n_tokens"] - row["generation_tokens"] + offset_int

    def reuse_stats(rows: Sequence[Mapping[str, int]]) -> dict[str, object]:
        declared = [declared_tokens(row) for row in rows]
        evaluated = [row["prompt_eval_tokens"] for row in rows]
        total_declared = sum(declared)
        total_evaluated = sum(evaluated)
        return {
            "requests": len(rows),
            "declared_prompt_tokens": total_declared,
            "evaluated_prompt_tokens": total_evaluated,
            "skipped_prompt_tokens": total_declared - total_evaluated,
            "evaluation_ratio": (
                round(total_evaluated / total_declared, 6) if total_declared else None
            ),
            "reuse_ratio": (
                round(1.0 - total_evaluated / total_declared, 6) if total_declared else None
            ),
            "evaluated_tokens_distribution": token_count_distribution(evaluated),
            "declared_tokens_distribution": token_count_distribution(declared),
        }

    DIRECT_CLASS_MAX_DECLARED = 2000  # direct envelope 1,832 + margin
    main_direct_rows = [
        row for row in main_requests if declared_tokens(row) <= DIRECT_CLASS_MAX_DECLARED
    ]
    main_evidence_rows = [
        row for row in main_requests if declared_tokens(row) > DIRECT_CLASS_MAX_DECLARED
    ]
    classification_clean = (
        len(main_direct_rows) == len(samples)
        and len(main_evidence_rows) == dispatched_count
    )
    if not classification_clean and len(main_requests) == len(samples) + dispatched_count:
        ordered_by_declared = sorted(main_requests, key=declared_tokens)
        main_direct_rows = ordered_by_declared[: len(samples)]
        main_evidence_rows = ordered_by_declared[len(samples):]
    prompt_reuse_section = {
        "method": (
            "per request: declared = release n_tokens - generation tokens + "
            "calibrated fixed offset; evaluated = print_timing prompt-eval tokens "
            "(post-prefix-cache); windows split by tracked server-log offsets "
            "(canary / main / resend); main contact classes split at declared <= "
            f"{DIRECT_CLASS_MAX_DECLARED}"
        ),
        "declared_offset_calibration": {
            "client_prompt_tokens_total": prompt_tokens_total_client,
            "sum_release_n_tokens_minus_generation": sum_release_minus_gen,
            "request_count_parsed": len(all_requests),
            "per_request_offset": per_request_offset,
        },
        "classification_clean_by_threshold": classification_clean,
        "overall": reuse_stats(all_requests),
        "by_class": {
            "main_direct_contact0": reuse_stats(main_direct_rows),
            "main_evidence_contact1": reuse_stats(main_evidence_rows),
            "canary_direct_single_slot": reuse_stats(canary_requests),
            "resend_direct_single_slot": reuse_stats(resend_requests),
        },
    }

    sentinel_summary = main_sentinel.summary() if main_sentinel is not None else None
    arm_report = {
        "schema": f"saea-dev1000-baseline-lock-{report_stub}-mechanical-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "arm_id": arm_id,
        "arm_index": arm["arm_index"],
        "attempt_id": attempt_id,
        "generated_at": iso_now(),
        "mechanical_only": True,
        "authority": (
            "campaign row SAEA-DEV1000-BASELINE-LOCK under "
            "docs/readiness/2026-08-24-dev1000-baseline-lock-preregistration.md "
            "and docs/readiness/2026-08-25-lock-candidate-selection.md; "
            "machine-readable contract "
            "configs/experiment/slurp-dev1000-baseline-lock-v1.json. MECHANICAL "
            "landing only — gold never opened, no accuracy computed; the "
            "one-touch lock read is a separately registered later mission"
        ),
        "config_hash": composed.config_hash,
        "server_np": server_np,
        "decoder_session_receipt_sha256": measured_receipt,
        "gpu_preflight": flight["gpu_preflight"],
        "prompt_fit": flight.get("prompt_fit"),
        "lock_candidate": flight.get("lock_candidate"),
        "frozen_cell": {
            "policy_config": LOCK_CANDIDATE_RELPATH,
            "policy_config_sha256": LOCK_CANDIDATE_SHA256,
            "supersedes": LOCK_CANDIDATE_SUPERSEDES_RELPATH,
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_TAU,
            "top_k_per_dimension": FROZEN_TOP_K,
            "fusion": {"m": FROZEN_FUSE.m, "c": FROZEN_FUSE.c, "l": FROZEN_FUSE.top_l},
            "rank_weights": {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2},
            "retain_override_bar": DELTA_BAR if arm_id == "BLEND" else None,
            "value_vectors": "SEALED (never loaded)",
            "kb_policy_last_commit": flight["invariants"]["kb_policy_last_commit"],
        },
        "arm_construction": {
            "split_id": split_id,
            "sample_count": len(samples),
            "max_contacts": max_contacts,
            "controller_policy_id": controller_policy_id,
            "flies_full_dev1000": split_id == SPLIT_ID and len(samples) == SPLIT_COUNT,
            "retain_override": (
                {
                    "bar": DELTA_BAR,
                    "epsilon": DELTA_EPS,
                    "disagreement_condition": "MANDATORY",
                    "implementation": (
                        "launcher-side, through the registered controller "
                        "factory's own normalizer keyword; rails/ and core/ "
                        "untouched"
                    ),
                    "fit_on_exposed_data": (
                        "the bar was FIT on DEV-100 r4/r5 + DEV-500 NEW400 and "
                        "frozen 2026-08-25; the unexposed-500 read validates it"
                    ),
                }
                if arm_id == "BLEND"
                else None
            ),
        },
        "lock_statistic_population": {
            "note": (
                "NOT flown as a separate arm. Both arms fly the full DEV-1000; "
                "the lock statistic covers only the unexposed 500 and the "
                "exposed 500 are read separately. The partition is performed by "
                "the separately registered one-touch read over this sealed "
                "result."
            ),
            **({} if flight.get("new500_partition") is None else flight["new500_partition"]),
        },
        "mechanical": {
            "loop_contacts": sum(row["contacts"] for row in mech_rows.values()),
            "one_contact_trajectories_retained_primary": retained_count,
            "two_contact_trajectories_dispatched": dispatched_count,
            "dispatch_rate": (
                round(dispatched_count / len(samples), 6) if samples else None
            ),
            "retain_rate": (
                round(retained_count / len(samples), 6) if samples else None
            ),
            "direct_label_recovered_samples": label_recovered_count,
            "retain_override": {
                "bar": DELTA_BAR if arm_id == "BLEND" else None,
                "fired": override_fired_count,
                "override_dispatched": override_dispatched_count,
                "dead_direct_dispatched": dead_direct_dispatched_count,
                "dispatch_decomposition_exact": (
                    override_dispatched_count + dead_direct_dispatched_count
                    == dispatched_count
                ),
                "delta_distribution_over_defined": delta_distribution,
                "branch_only_supply_mismatches": supply_mismatches,
                "branch_only_holds": not supply_mismatches,
            },
            "winner_label_present_samples": sum(
                1 for row in mech_rows.values() if row["winner_label_present"] is True
            ),
            "per_sample_records": f"{report_stub}-mechanical.json (run dir)",
            "opaque_outputs": str(outputs_path),
        },
        "canary": flight.get("canary"),
        "resend_pair": flight.get("resend_pair"),
        "sentinel": sentinel_summary,
        "decode_rate_distribution_ms_per_token": rate_distribution(
            main_sentinel.observed_rates if main_sentinel is not None else []
        ),
        "main_print_timing": flight.get("main_print_timing"),
        "prompt_reuse": prompt_reuse_section,
        "trace_isolation": flight.get("trace_isolation"),
        "serving_descriptives": flight.get("serving_descriptives"),
        "embedding_accounting": flight.get("embedding_accounting"),
        "embedding_jitter_pair": flight.get("embedding_jitter_pair"),
        "mid_flight_clock_samples_windows_side": read_clock_samples(root, slug),
        "core_client": flight["core_client"],
        "spend_vs_ceilings": {
            "this_attempt": {
                "core_contacts": {"used": contact_total, "attempt_ceiling": attempt_core_ceiling},
                "embedding_tool_contacts": {"used": tool_contacts_used, "attempt_ceiling": attempt_tool_ceiling},
                "metered_audio_seconds": {"used": audio_seconds_metered},
                "gpu_active_hours_contact_basis": flight["gpu_active_hours_contact_basis"],
            },
            "plan_declaration_run_cumulative": {
                "planned_model_calls": plan_calls,
                "planned_speech_audio_seconds": plan_audio,
                "planned_gpu_hours": plan_gpu,
            },
            "campaign_cumulative_incl_prior_arms": {
                "core_contacts": prior_calls + contact_total,
                "metered_audio_seconds": (
                    prior_audio + audio_seconds_metered
                    if isinstance(audio_seconds_metered, (int, float))
                    else None
                ),
                "prior_durable_at_registration": {
                    "calls": prior_calls,
                    "audio_seconds": prior_audio,
                    "records": prior_records,
                },
            },
            "campaign_ceilings": {
                "core_contacts": CAMPAIGN_CEILING_CORE,
                "embedding_tool_contacts": CAMPAIGN_CEILING_TOOL,
                "metered_audio_seconds": CAMPAIGN_CEILING_AUDIO,
                "gpu_hours": CAMPAIGN_CEILING_GPU_HOURS,
            },
        },
        "run_dir": str(run_dir),
        "hard_stop": (
            "MECHANICAL LANDING ONLY: gold stays sealed under this campaign row; "
            "no accuracy, no W->C/C->W, no per-scenario read, and NO LOCK "
            "VERDICT exists in this artifact. After ARM 2 (BLEND) lands "
            "mechanically the mission STOPS. The one-touch lock read -- which "
            "partitions this sealed result into the unexposed 500 (the "
            "statistic) and the exposed 500 (reported separately), computes the "
            "paired bootstrap and McNemar, and evaluates the preregistered "
            "90-percent-CI-lower-bound >= +10 pp lock condition -- requires its "
            "own registered row after coordinator review (preregistration "
            "sections 1 and 2)."
        ),
    }
    report_path = OUT_CHECK_DIR / f"{report_stub}-mechanical-report.json"
    report_path.write_text(
        json.dumps(arm_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    flight["outcome_status"] = "ARM_LANDED_MECHANICAL"
    flight["report_path"] = str(report_path)
    save_flight()
    log(f"arm mechanical report written: {report_path}")
    log(f"report sha256: {sha256_file(report_path)}")
    log(
        f"MECHANICAL SUMMARY ARM {arm_id}: {len(samples)} samples, "
        f"{sum(row['contacts'] for row in mech_rows.values())} loop contacts "
        f"(+{contact_total - sum(row['contacts'] for row in mech_rows.values())} "
        f"canary/resend), retain-primary {retained_count}, dispatched "
        f"{dispatched_count}, direct-label recovered {label_recovered_count}, "
        f"core {contact_total}/{attempt_core_ceiling} (attempt), tool "
        f"{tool_contacts_used}/{attempt_tool_ceiling}, audio "
        f"{audio_seconds_metered}, cumulative core "
        f"{prior_calls + contact_total}/{CAMPAIGN_CEILING_CORE}"
    )
    log("RESIDENT DECODER LEFT UP (never stopped by this launcher); GOLD NEVER OPENED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
