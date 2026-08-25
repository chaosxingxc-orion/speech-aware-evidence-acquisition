"""AUDIO2TOOL STAGE G1 launcher, THIRD BLEND ATTEMPT -- THE TWO-PASS FLIGHT
-- exposure row ``SAEA-A2T-G1`` (bounded-discovery-probe), MECHANICAL FLIGHT
ONLY.

SUCCESSOR-ATTEMPT PROVENANCE. Attempt 1
(``attempt-20260825T101057Z-a2tg1blend``) tripped the registered in-flight
decode-rate sentinel at loop contact 26 of 208. Attempt 2
(``attempt-20260825T114856Z-a2tg1blend``) tripped it again at loop contact 60
of 208, and this time its own FIX-1 telemetry ATTRIBUTED it: a MEMORY-PATH
STALL UNDER VRAM OVERSUBSCRIPTION, with throttling refuted. With the CPU
embedder sidecar resident, ``memory.used`` stepped 21,288 -> 24,125 MiB (98.6
percent of 24,463) and decode collapsed from a 19.54 ms/token median to 997.25
(about 51x) while prefill moved only 1.56 -> 3.76 (about 2.4x); the SM clock
sat at a 2,482 MHz median against the 2,500 MHz lock, drawing 45 W of a 100 W
cap at 55 C and 100 percent utilization. Full clocks, half the power budget,
cool, busy, one token per second is a device spinning on memory transfers.

ATTEMPT 2's DEFECT, NAMED EXACTLY: its offline precompute worked (hit rate
0.9138, 53 in-loop tool contacts avoided) but the MISS PATH SPAWNED THE
SIDECAR AND NEVER STOPPED IT, so one miss at loop contact about 12 restored
the bad VRAM condition for the whole remaining loop. The precompute removed 91
percent of the in-loop tool contacts and 0 percent of the contention, because
contention is a function of whether the process is RESIDENT, not of how many
contacts it serves.

THIS ATTEMPT REMOVES THE CONTENTION STRUCTURALLY RATHER THAN PROBABILISTICALLY.
The sidecar is NEVER co-resident with a decode contact, and that is asserted
fail-closed on every single contact rather than hoped for:

* **PASS A (GPU busy, sidecar DOWN).** All 104 contact-0 direct decodes of the
  BLEND arm fly through the DEGENERATE direct-decode-only controller
  (``snapshot=None``), whose ``initial_contact`` is byte-identical to the
  blend controller's own. No embedding happens, no evidence contact is
  scheduled, and -- decisively -- THE POLICY IS NEVER RUN AGAINST AN INERT
  QUERY VECTOR. Flying with an empty cell would change what the policy reads;
  the correct shape is DEFERRAL, NEVER OMISSION, so the policy simply does not
  decide yet.
* **OFFLINE BRIDGE (GPU idle, sidecar UP ALONE).** Every Pass-A text not
  already covered by an already-durable vector is embedded in ONE batched
  sidecar session; the sidecar is then STOPPED with its own receipt and VRAM is
  verified to have returned to the no-sidecar baseline before Pass B starts.
  The already-durable table is attempt 2's own offline precompute over the
  landed M0 texts plus its five live-embedded divergent texts -- reused at ZERO
  new tool contacts, because an embedding is a deterministic function of its
  text and every spawn proved bit-identical jitter numerics.
* **PASS B (GPU busy, sidecar DOWN).** The REAL frozen v1 blend controller runs
  recall -> rank -> fuse on the vector of THAT trajectory's OWN flown Pass-A
  text, and flies the evidence contact wherever the policy dispatches. The
  trajectory's contact 0 is not re-flown: it is RESUMED from Pass A's durable
  record through :class:`ReplayDirectClient`, which serves the direct contact
  from Pass A's text after proving the sha256 of the messages the runner just
  built equals the sha256 Pass A recorded for the same sample. A retain-primary
  trajectory therefore costs ZERO Pass-B contacts.

WHAT IS KEPT FROM ATTEMPT 2, UNCHANGED: FIX 1's telemetry (it is what made the
diagnosis possible and it stays armed through every phase) and FIX 4's
run-cumulative fail-closed sizing guards. FIX 3 (cold start) is DROPPED as a
remedy -- attempt 2 had a genuine cold start and stalled anyway, so the
hypothesis is dead; the preflight recording of host state is kept.

WHAT IS ADDED: :class:`SidecarCoResidencyGuard`, consulted before EVERY frozen-
core contact and at every phase boundary. If the embedder port is reachable or
a sidecar handle is live while a decode is in flight, the flight stops fail-
closed. It is the invariant this whole redesign exists to hold.

NOT ONE POLICY KNOB MOVES. ``rails/`` and ``core/`` are byte-untouched, the v1
cell is byte-identical, and the section 8.1 derived serving geometry is the
geometry the M0 arm flew. Every change here is SERVING or HARNESS.

One parameterized launcher, one ARM per invocation (``--arm M0 | BLEND``),
each invocation minting its OWN attempt id with one-shot semantics per arm. The
M0 arm is NOT re-flown by this file: it landed complete at
``attempt-20260825T100735Z-a2tg1m0`` and is scored.

Lineage: the machinery is the flight-proven DEV-1000 baseline-lock launcher
(``../../2026-08-25-dev1000-baseline-lock/launcher/launch_dev1000_baseline_lock.py``,
landed exit 0 on both arms) with three structural changes and nothing else:

* the v2 DELTA RETAIN-OVERRIDE is EXCISED. G1 carries the locked **v1** cell,
  byte-identical. The override's bar was fit on SLURP exposed data and its own
  out-of-sample read damaged 3 of the 3 unexposed trajectories it touched.
* the carrier is Audio2Tool, so the adapter, the label vocabulary and the
  direct-label recovery function are the carrier ANALOGUES documented in
  ``configs/experiment/a2t-g1-v1.json`` -- not knob changes.
* the canary has no inherited hash authority. No prior A2T flight ran this
  geometry, so the **M0 arm establishes this campaign's own** canary hashes
  and the BLEND arm compares against them.

Authority: ``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md``
sections 3.3 / 3.4 / 3.5 / 3.6, section 7 (Amendment 1) and section 8 (owner
Amendment 2, commit ``bb6d22ef``); machine-readable contract
``configs/experiment/a2t-g1-v1.json``.

THE CLAIM THIS FLIGHT CARRIES, stated in Amendment 2's terms: the locked
POLICY CELL transfers BYTE-IDENTICAL; SERVING GEOMETRY is DERIVED per carrier
by the fixed section 8.1 rule from the measured task contract, applied
uniformly to every arm and fixed before any result was seen. It is not a
deviation and there is no exception to disclose.

SCOPE OF THE FLOWN POPULATION. Both arms fly all 104 items of ``A2T-G1-104``,
a 13-per-tier draw from the frozen EXPOSED 400. Plan section 3.3: the exposed
tier's numbers are SECONDARY readings and can never be the campaign claim.

MECHANICAL LANDING ONLY: this launcher NEVER opens gold, NEVER scores, and
computes NO accuracy. Response texts land opaque in the run dir for the
separately invoked seal-and-score step.

Run in WSL2 (systemd-run --user unit; PATH must include /usr/lib/wsl/lib for
the in-script nvidia-smi)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python .../launch_a2t_g1.py --arm M0 --gpu-preflight <preflight.json>

Self-test (offline: stubbed timings, zero contacts, no service, no gate)::

    ... launch_a2t_g1.py --self-test
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import statistics
import subprocess
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
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

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
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
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
    FuseKnobs,
    KbAlphaBlendController,
    RankWeights,
    _label_identities,
    default_label_normalizer,
    fuse_supplyfilter_factory,
    make_kb_alpha_blend_controller_factory,
    multidim_recall,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
)

# --------------------------------------------------------------------------
# Pinned identity (campaign row SAEA-A2T-G1).
# --------------------------------------------------------------------------

RUN_ID = "SAEA-A2T-G1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-g1-kb-alpha-blend"
EXPERIMENT_FRAGMENT = "a2t-g1-v1"
COMPOSED_CONFIG_SHA256 = (
    "df6bf4d4e5ac3ae5a3fe9d52dc8933b81bec70f7dbff05a2984635b8badc38f9"
)

SPLIT_ID = "A2T-G1-104"
CANARY_SPLIT_ID = "A2T-G1-CANARY-2"
RESEND_SPLIT_ID = "A2T-G1-RESEND-1"
SPLIT_COUNT = 104
SPLIT_AUDIO_SECONDS_TOTAL = 587.017
SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
# Both hash conventions. ``SPLIT_IDENTITY_HASH`` is the load-split convention
# (``audio2tool/tier:NNNNNN``) the ExecutionPlan carries;
# ``SPLIT_RECEIPT_INTEGRITY_HASH`` is the key convention
# (``audio2tool:tier:NNNNNN``) the receipt signs itself with.
SPLIT_IDENTITY_HASH = (
    "f5a030189cf80dcbc52899e2fa5f819bac03874f2ad3f9645fdc60c432a9bf3a"
)
SPLIT_RECEIPT_INTEGRITY_HASH = (
    "516f92d9b919640969676eb10b776d9c479169fb0a387497e943c726b2191326"
)
PARENT_RECEIPT_RELPATH = "docs/receipts/probe-samples/r1-audio2tool-sample.json"
PARENT_SPLIT_IDENTITY_HASH = (
    "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
)

SNAPSHOT_RELPATH = "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
SNAPSHOT_SHA256 = "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
EMBEDDINGS_RECEIPT_RELPATH = "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json"
LABEL_VOCABULARY_SIZE = 151

RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-mmproj-free.json"
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT_PATH = FEATURE_ROOT / "A2T-G1-104-promotion.json"
PROMOTION_RECEIPT_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)
SESSION_DIR = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP2-BASE-A2T-G1-20260825T092000Z"
)
SESSION_RECEIPT_SHA256 = (
    "ee9a4849a90a86b8759474a66db214037628a9872ed1d433df0165385f16c79e"
)
DECODER_PORT = 8090
EMB_PORT = 8082

# The v1 FROZEN CELL, hash-pinned at the flight row.
#
# NOTE ON THE HASH, recorded rather than silently re-pinned: the DEV-1000 lock
# launcher pinned this file at 0d36273e..., its PRE-LOCK bytes. The lock commit
# d9fef537 then added two ANNOTATION keys to the same file -- ``STATUS`` and
# ``locked_at`` -- and changed nothing else; ``git log -p`` on the path shows a
# two-line addition and no edit inside ``knobs``. The knob table is therefore
# byte-identical to the cell the DEV-1000 lock flew, and this launcher proves
# that independently by comparing the knob dict key for key below. Pinning the
# current bytes is the honest choice: pinning the stale hash would refuse a
# file whose only change was the lock's own annotation.
POLICY_CELL_RELPATH = "configs/policy/kb-policy-v1-dev100.json"
POLICY_CELL_SHA256 = (
    "d68afd2cfb6e12d9cbd9d3fbcf0daf3f81f6ed8be9b2a75c4f8ffb234011a919"
)
POLICY_CELL_PRELOCK_SHA256 = (
    "0d36273eb2a5f4411ba9ca378ad820392e97c8759222087cf562e7f19442e2b0"
)

# Campaign ceilings (experiment fragment section a2t_g1_ceilings).
CAMPAIGN_CEILING_CORE = 400
CAMPAIGN_CEILING_TOOL = 200
CAMPAIGN_CEILING_AUDIO = 2000
CAMPAIGN_CEILING_GPU_HOURS = 0.6

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
# THE BYTE-FROZEN v1 POLICY CELL (configs/policy/kb-policy-v1-dev100.json).
# Every knob below is BYTE-IDENTICAL to the locked cell. Nothing about this
# carrier changes any of them; see the experiment fragment's a2t_g1_claim.
# --------------------------------------------------------------------------
FROZEN_ALPHA = 0.45
FROZEN_TAU = 0.65
FROZEN_TOP_K = 5
FROZEN_FUSE = FuseKnobs(tau=FROZEN_TAU, m=5, c=2, top_l=3)
FROZEN_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

M0_POLICY_ID = "saea-direct-decode-only-m0"
# The section 8.1 DERIVED output ceiling for this carrier: a JSON call list,
# not a single label. Equal to the value A0 registered here.
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1024}

ARMS: dict[str, dict[str, object]] = {
    "M0": {
        "slug": "m0",
        "arm_index": 1,
        "split_id": SPLIT_ID,
        "max_contacts": 1,
        "attempt_core_ceiling": 120,
        "attempt_tool_ceiling": 0,
        "plan_calls": 150,
        "plan_audio": 700,
        "plan_gpu": 0.25,
        "resend": False,
        "sidecar": False,
        "report_stub": "arm1-m0",
    },
    "BLEND": {
        "slug": "blend",
        "arm_index": 2,
        "split_id": SPLIT_ID,
        "max_contacts": 2,
        # ------------------------------------------------------------------
        # THE ATTEMPT CEILING, LOWERED WITH ITS BASIS STATED.
        #
        # The budget BINDS: 196 of the campaign's 400 core contacts are already
        # durable, so 204 remain, while the two-pass WORST case (2 canary x 2
        # for a re-run + 104 Pass A + 104 Pass B + 1 resend = 213) exceeds it.
        # The predecessor's section 9 item 4 allows exactly two remedies: an
        # OWNER decision raising the campaign cell, or a LOWER ATTEMPT CEILING
        # REGISTERED WITH ITS BASIS STATED. This launcher takes the second and
        # never the first.
        #
        # THE BASIS, registered as row SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION at
        # ZERO contacts BEFORE it was computed: the v1 cell's own dispatch
        # predicate, evaluated through rails.kb_policy's own pure functions over
        # the landed M0 texts and their already-durable embeddings, dispatches
        # 0 of 104. The mechanism is structural, not marginal -- content-facet
        # cosines are healthy (min 0.759, max 0.957, all 104 above tau 0.65) but
        # the ranker's prior-mass dimensions score 1.2 to 4.1 unnormalized, so
        # ALL 104 trajectories have ZERO content facets in the top-m=5 window the
        # fuser admits over, and percept admission reads only NON-prior-mass
        # dimensions. Nothing is ever admitted, so nothing is ever selected.
        # CORROBORATED BY THE FLOWN RECORD: attempts 1 and 2 together flew 86
        # BLEND trajectories and produced 86 direct-decode contacts and ZERO
        # evidence-decode contacts.
        #
        # PASS_B_CONTACT_CEILING = 26 is therefore a 25-percent-of-population
        # margin over a projection of 0 -- it tolerates every one of the roughly
        # 9 percent divergent Pass-A texts flipping to dispatch, three times
        # over. Worst case: 4 canary + 104 Pass A + 26 Pass B + 1 resend = 135;
        # 196 + 135 = 331 <= 400. Asserted fail-closed at takeoff.
        "attempt_core_ceiling": 135,
        # Tool contacts: 126 of 200 are durable, so 74 remain. The bridge embeds
        # ONLY Pass-A texts absent from the already-durable table (expected
        # about 9 at the measured 8.6 percent divergence) plus 2 jitter probes
        # per sidecar spawn/stop cycle. 50 leaves room for about 48 live embeds
        # -- five times any plausible value -- and 126 + 50 = 176 <= 200.
        "attempt_tool_ceiling": 50,
        "plan_calls": 400,
        "plan_audio": 2000,
        "plan_gpu": 0.35,
        "resend": True,
        "sidecar": True,
        "report_stub": "arm2-blend",
    },
}

CANARY_SAMPLE_COUNT = 2
# THE GATE IS THE PER-TOKEN GENERATION RATE, never wall time: at the derived
# output ceiling of 1,024 tokens a healthy canary decode legitimately runs far
# longer than a 64-token SLURP canary did.
CANARY_MS_PER_TOKEN_PASS = 300.0

SENTINEL_WINDOW_CONTACTS = 8
SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT = 1000.0

OUT_CHECK_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-25-a2t-g1"
)
CANARY_AUTHORITY_PATH = OUT_CHECK_DIR / "canary-hashes.json"


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


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


def messages_digest(messages) -> str:
    """Content hash of a rails ``messages`` document, stable under dict order.

    Pass B's replay proves the contact it resumes is the contact Pass A flew by
    comparing THIS digest, so it must be computed over the whole document and
    never over a summary of it."""

    return sha256_text(
        json.dumps(
            [dict(message) for message in messages],
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    )


def read_clock_samples(root: Path, slug: str) -> list[dict[str, object]] | None:
    """Parse the Windows-side mid-flight clock samples if present."""

    path = root / "runs" / RUN_ID / ("clock-samples-%s.jsonl" % slug)
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


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# FIX 1 -- the sentinel's telemetry blind spot.
#
# ``core.resources``' sampler records utilization and memory only, and it is
# core code this launcher must not touch. So the launcher samples the missing
# series ITSELF, on the Windows-side binary, into the very file the arm report
# and the abort record already read (``read_clock_samples``). One query line;
# no policy surface, no core edit.
# --------------------------------------------------------------------------

NVIDIA_SMI_WINDOWS = "/mnt/c/Windows/System32/nvidia-smi.exe"
GPU_TELEMETRY_FIELDS: tuple[str, ...] = (
    "timestamp",
    "memory.used",
    "memory.total",
    "utilization.gpu",
    "utilization.memory",
    "clocks.sm",
    "clocks.max.sm",
    "clocks.mem",
    "power.draw",
    "enforced.power.limit",
    "temperature.gpu",
    "pstate",
    "clocks_throttle_reasons.active",
    "clocks_throttle_reasons.sw_power_cap",
    "clocks_throttle_reasons.hw_slowdown",
    "clocks_throttle_reasons.sw_thermal_slowdown",
    "clocks_throttle_reasons.hw_thermal_slowdown",
)
_NUMERIC_TELEMETRY_FIELDS = frozenset(
    {
        "memory.used",
        "memory.total",
        "utilization.gpu",
        "utilization.memory",
        "clocks.sm",
        "clocks.max.sm",
        "clocks.mem",
        "power.draw",
        "enforced.power.limit",
        "temperature.gpu",
    }
)
_THROTTLE_FLAG_FIELDS: tuple[str, ...] = (
    "clocks_throttle_reasons.sw_power_cap",
    "clocks_throttle_reasons.hw_slowdown",
    "clocks_throttle_reasons.sw_thermal_slowdown",
    "clocks_throttle_reasons.hw_thermal_slowdown",
)


class ClockThrottleSampler:
    """Launcher-local clock/power/throttle sampler.

    Never raises out of :meth:`start`, :meth:`stop`, :meth:`sample_once` or
    :meth:`summary`: a broken binary degrades to a recorded reason exactly the
    way the core sampler degrades, because a telemetry failure must never take
    down a flight."""

    def __init__(
        self,
        path: Path,
        *,
        binary: str = NVIDIA_SMI_WINDOWS,
        interval_seconds: float = 3.0,
        phase: str = "preflight",
    ) -> None:
        self._path = path
        self._binary = binary
        self._interval_seconds = float(interval_seconds)
        self._phase = phase
        self._rows: list[dict[str, object]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._reason: str | None = None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Truncate: the file is per-attempt evidence, never an append-across-
        # attempts log.
        self._path.write_text("", encoding="utf-8", newline="\n")

    @property
    def phase(self) -> str:
        return self._phase

    def set_phase(self, phase: str) -> None:
        with self._lock:
            self._phase = phase

    def _poll(self) -> dict[str, object] | None:
        try:
            completed = subprocess.run(
                [
                    self._binary,
                    "--query-gpu=%s" % ",".join(GPU_TELEMETRY_FIELDS),
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            line = next(
                candidate
                for candidate in completed.stdout.strip().splitlines()
                if candidate.strip()
            )
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != len(GPU_TELEMETRY_FIELDS):
                raise ValueError(
                    "nvidia-smi returned %d fields, expected %d"
                    % (len(parts), len(GPU_TELEMETRY_FIELDS))
                )
        except Exception as error:  # noqa: BLE001 -- telemetry never kills a flight
            with self._lock:
                if self._reason is None:
                    self._reason = "clock/throttle sampling failed: %r" % (error,)
            return None
        row: dict[str, object] = {}
        for field, value in zip(GPU_TELEMETRY_FIELDS, parts):
            if field in _NUMERIC_TELEMETRY_FIELDS:
                try:
                    row[field] = float(value)
                except ValueError:
                    row[field] = value
            else:
                row[field] = value
        with self._lock:
            row["phase"] = self._phase
        row["sampled_at_unix_seconds"] = time.time()
        return row

    def sample_once(self, phase: str | None = None) -> dict[str, object] | None:
        if phase is not None:
            self.set_phase(phase)
        row = self._poll()
        if row is None:
            return None
        self._append(row)
        return row

    def _append(self, row: Mapping[str, object]) -> None:
        with self._lock:
            self._rows.append(dict(row))
            try:
                with self._path.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            except OSError as error:
                if self._reason is None:
                    self._reason = "clock sample write failed: %r" % (error,)

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            row = self._poll()
            if row is not None:
                self._append(row)

    def start(self) -> None:
        if self._thread is not None:
            return
        self.sample_once()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds * 2 + 25.0)
            self._thread = None

    def summary(self) -> dict[str, object]:
        with self._lock:
            rows = [dict(row) for row in self._rows]
            reason = self._reason

        def _stats(field: str, subset: Sequence[Mapping[str, object]]) -> dict[str, object]:
            values = [
                float(row[field])
                for row in subset
                if isinstance(row.get(field), (int, float))
            ]
            if not values:
                return {"count": 0}
            ordered = sorted(values)
            return {
                "count": len(ordered),
                "min": ordered[0],
                "median": float(statistics.median(ordered)),
                "max": ordered[-1],
            }

        by_phase: dict[str, object] = {}
        for phase in sorted({str(row.get("phase")) for row in rows}):
            subset = [row for row in rows if str(row.get("phase")) == phase]
            phase_block: dict[str, object] = {"samples": len(subset)}
            for field in (
                "clocks.sm",
                "power.draw",
                "memory.used",
                "utilization.gpu",
                "temperature.gpu",
            ):
                phase_block[field] = _stats(field, subset)
            phase_block["throttle_reasons_active_values"] = sorted(
                {
                    str(row.get("clocks_throttle_reasons.active"))
                    for row in subset
                    if row.get("clocks_throttle_reasons.active") is not None
                }
            )
            phase_block["throttle_flags_ever_active"] = {
                field: any(
                    str(row.get(field)).strip().lower() == "active" for row in subset
                )
                for field in _THROTTLE_FLAG_FIELDS
            }
            by_phase[phase] = phase_block
        overall_flags = {
            field: any(str(row.get(field)).strip().lower() == "active" for row in rows)
            for field in _THROTTLE_FLAG_FIELDS
        }
        return {
            "path": str(self._path),
            "interval_seconds": self._interval_seconds,
            "query_fields": list(GPU_TELEMETRY_FIELDS),
            "sample_count": len(rows),
            "sampling_reason": reason,
            "throttle_flags_ever_active": overall_flags,
            "any_throttling_observed": any(overall_flags.values()),
            "by_phase": by_phase,
            "fix": (
                "FIX 1 of the successor attempt: clocks.sm / clocks.max.sm / "
                "power.draw / clocks_throttle_reasons.* were NOT sampled by "
                "attempt 1, so its sentinel trip could not be attributed. They are"
            ),
        }


# --------------------------------------------------------------------------
# FIX 2 -- the OFFLINE query-vector precompute source: the LANDED M0 arm.
#
# The M0 arm flew the identical bare direct decode over the identical 104
# samples under the identical derived geometry on the identical service
# instance, and its per-sample texts landed with their own sha256 records.
# BLEND's contact 0 IS that decode, so its query text is knowable before
# takeoff for every sample whose flown text reproduces -- which the
# predecessor measured at 22 of 26.
# --------------------------------------------------------------------------

M0_ARM_REPORT_RELNAME = "arm1-m0-mechanical-report.json"
M0_ARM_REPORT_SHA256 = (
    "7e5e9223c48b1bc457b2b02cb54050d208d717b376326ab5061da8847366ab37"
)
M0_ATTEMPT_ID = "attempt-20260825T100735Z-a2tg1m0"
# Registered expectation, from attempt 2's MEASURED hit rate of 0.9138 (53 hits
# / 5 misses / 58 lookups) against attempt 1's 22 of 26. Recorded so the landed
# bridge miss count is read against a number fixed BEFORE the flight.
PRECOMPUTE_EXPECTED_HIT_RATE = 0.9138
# Durable embedding tool spend already on the row when this attempt registers
# (27 from attempt 1 plus 99 from attempt 2).
PRIOR_TOOL_CONTACTS_DURABLE = 126

# ---- the ALREADY-DURABLE query-vector tables (zero new tool contacts) -----
#
# An embedding is a deterministic function of its text, and every attempt-2
# spawn and stop proved bit-identical jitter numerics against the first spawn,
# so a vector already computed for a text on this row is the SAME vector the
# bridge would recompute. Reusing them is a serving cache, not a result read.
ATTEMPT2_ID = "attempt-20260825T114856Z-a2tg1blend"
ATTEMPT2_PRECOMPUTED_RELNAME = "query-vectors-precomputed.jsonl"
ATTEMPT2_PRECOMPUTED_SHA256 = (
    "4fceb9488a5d0245837dfde85cb9d918115d8e6c7f720b2e1e9eccdfeaf46657"
)
ATTEMPT2_LANDED_RELNAME = "query-vectors.jsonl"

# ---- the registered Pass-B contact ceiling and its basis ------------------
PASS_B_CONTACT_CEILING = 26
DISPATCH_PROJECTION_RELNAME = "dispatch-projection.json"
DISPATCH_PROJECTION_RUN_ID = "SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION"
DISPATCH_PROJECTION_COUNT = 0
# Worst-case Pass-B metered audio: the PASS_B_CONTACT_CEILING largest sample
# durations in the subset, so the audio guard is conservative whichever samples
# actually dispatch. Verified live against the subset receipt at takeoff.
PASS_B_WORST_AUDIO_SECONDS = 291.548

# After the bridge stops the sidecar, VRAM must return to the no-sidecar
# baseline before Pass B is allowed to start. Attempt 2 measured the sidecar's
# device allocation at about 2,837 MiB against a 21,288 MiB no-sidecar
# occupancy, so a return to at most this many MiB proves the allocation is gone.
VRAM_NO_SIDECAR_CEILING_MIB = 22500.0
VRAM_RETURN_TIMEOUT_SECONDS = 120.0


def load_m0_direct_texts(
    out_check_dir: Path, expected_sample_ids: Sequence[str]
) -> tuple[dict[str, str], dict[str, object]]:
    """Return ``{sample_id: direct decode text}`` from the LANDED M0 arm, each
    text verified against that arm's OWN per-sample ``direct_response_sha256``
    record. Fail-closed on any mismatch: a silently wrong precompute would
    corrupt BLEND's recall with a vector for a text that never flew."""

    report_path = out_check_dir / M0_ARM_REPORT_RELNAME
    measured_report = sha256_file(report_path)
    if measured_report != M0_ARM_REPORT_SHA256:
        raise SystemExit(
            "the landed M0 arm report hashes to %s, not the registered %s; refusing "
            "to precompute query vectors from unpinned bytes"
            % (measured_report, M0_ARM_REPORT_SHA256)
        )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("arm_id") != "M0" or report.get("attempt_id") != M0_ATTEMPT_ID:
        raise SystemExit("the pinned M0 report is not the landed M0 attempt")
    m0_run_dir = Path(str(report["run_dir"]))
    if m0_run_dir.name != M0_ATTEMPT_ID:
        raise SystemExit("the pinned M0 report names an unexpected run dir")
    mech_path = m0_run_dir / "arm1-m0-mechanical.json"
    outputs_path = m0_run_dir / "arm1-m0-outputs.jsonl"
    mech = json.loads(mech_path.read_text(encoding="utf-8"))
    texts: dict[str, str] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("arm") != "M0":
                raise SystemExit("an M0 outputs row is not an M0 row")
            sample_id = str(row["sample_id"])
            text = row["direct_response_text"]
            if not isinstance(text, str):
                raise SystemExit("M0 outputs row %r has no direct text" % sample_id)
            recorded = mech.get(sample_id, {}).get("direct_response_sha256")
            if sha256_text(text) != recorded:
                raise SystemExit(
                    "M0 direct text for %r does not hash to its landed record; refusing"
                    % sample_id
                )
            texts[sample_id] = text
    if set(texts) != set(expected_sample_ids):
        raise SystemExit(
            "the landed M0 texts cover %d samples, not this arm's %d"
            % (len(texts), len(expected_sample_ids))
        )
    integrity = {
        "source_arm": "M0 (landed, scored, hash-pinned)",
        "m0_report": M0_ARM_REPORT_RELNAME,
        "m0_report_sha256": measured_report,
        "m0_attempt_id": M0_ATTEMPT_ID,
        "m0_run_dir": str(m0_run_dir),
        "m0_mechanical_sha256": sha256_file(mech_path),
        "m0_outputs_sha256": sha256_file(outputs_path),
        "texts_verified_against": "per-sample direct_response_sha256 in the M0 arm's own mechanical records",
        "sample_count": len(texts),
    }
    return texts, integrity


# --------------------------------------------------------------------------
# THE A2T CARRIER ANALOGUE of the SLURP direct-label recovery function.
#
# SLURP: parse the answer's OWN scenario/action fields, join as
# ``scenario_action``, match EXACTLY against the label vocabulary (the
# f1060078 repair), ties broken by facet_id ascending.
#
# A2T: parse the answer's OWN call list with the FROZEN SCORER'S parser, take
# the PRIMARY tool name (the first call's name), match EXACTLY against the
# label vocabulary, ties broken by facet_id ascending. Same rule, same
# never-from-gold and never-from-prose discipline, re-expressed for an answer
# that is a JSON call list rather than a single label.
#
# WHY THE PRIMARY NAME: the knowledge base indexes one construction unit per
# value and each value's ``task_target`` is that unit's PRIMARY gold tool, so
# the primary name is the projection the label vocabulary is actually built
# on. The SCORER never uses this projection -- tool accuracy is equality of
# the full tool-name MULTISET -- and this function governs only which branch
# of the dispatch rule a trajectory takes.
# --------------------------------------------------------------------------


def a2t_primary_tool_normalizer(
    response_text: str, label_targets: Mapping[str, str]
) -> str | None:
    if not isinstance(response_text, str):
        return None
    try:
        calls, parsed = parse_tool_calls_text(response_text)
    except Exception:  # noqa: BLE001 -- an unparseable answer is dead-direct
        return None
    if not parsed or not calls:
        return None
    identity = calls[0].name
    if not isinstance(identity, str) or not identity:
        return None
    matches = sorted(
        facet_id for facet_id, target in label_targets.items() if target == identity
    )
    return matches[0] if matches else None


def tool_name_multiset(response_text: str) -> tuple[str, ...] | None:
    """The scorer-side projection, recorded for observability only: the sorted
    tool-name multiset of a parsed answer, or ``None`` when it does not parse.
    NEVER consulted by policy."""

    if not isinstance(response_text, str):
        return None
    try:
        calls, parsed = parse_tool_calls_text(response_text)
    except Exception:  # noqa: BLE001
        return None
    if not parsed:
        return None
    return tuple(sorted(call.name for call in calls))


# --------------------------------------------------------------------------
# A2T G1 adapter: subset-filtered Audio2Tool samples, scoring PERMANENTLY
# deferred (mechanical flight: gold never opens under this launcher).
# --------------------------------------------------------------------------


class A2TG1Adapter(Audio2ToolAdapter):
    """``Audio2ToolAdapter`` filtered to the frozen G1 subset. ``load_split``
    serves ``A2T-G1-104`` (all 104 -- what BOTH arms fly),
    ``A2T-G1-CANARY-2`` (the registered canary pair) and ``A2T-G1-RESEND-1``
    (the first canary sample).

    ``score`` returns a deferral marker: this campaign lands MECHANICALLY and
    the seal-and-score step is a separate invocation."""

    def __init__(self, lock, root, *, repo_root, receipt_items) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._by_id = {item["sample_id"]: item for item in receipt_items}
        self._cache: dict[str, tuple] = {}

    def load_split(self, split_id):  # noqa: D102
        if split_id not in (SPLIT_ID, CANARY_SPLIT_ID, RESEND_SPLIT_ID):
            raise ValueError(
                "A2TG1Adapter serves only the G1 views, not %r" % (split_id,)
            )
        if SPLIT_ID not in self._cache:
            exposed = super().load_split("discovery")
            wanted = self._by_id
            picked = [s for s in exposed if s.sample_id in wanted]
            if len(picked) != len(wanted):
                missing = set(wanted) - {s.sample_id for s in picked}
                raise ValueError(
                    "the discovery split lacks subset samples: %r" % (sorted(missing)[:5],)
                )
            for sample in picked:
                item = wanted[sample.sample_id]
                if sample.media_relpath != item["media_relpath"]:
                    raise ValueError("media_relpath drift for %s" % sample.sample_id)
                if sample.audio_ref.sha256 != item["audio_sha256"]:
                    raise ValueError("audio bytes drift for %s" % sample.sample_id)
            self._cache[SPLIT_ID] = tuple(
                sorted(picked, key=lambda s: s.sample_id)
            )
        full = self._cache[SPLIT_ID]
        if split_id == SPLIT_ID:
            return full
        ordered = [s.sample_id for s in full]
        canary_ids = ordered[:CANARY_SAMPLE_COUNT]
        by_id = {s.sample_id: s for s in full}
        if split_id == CANARY_SPLIT_ID:
            return tuple(by_id[sid] for sid in canary_ids)
        return (by_id[canary_ids[0]],)

    def score(self, sample, response):  # noqa: D102 -- gold stays sealed here
        return {"scoring_deferred": True}


# --------------------------------------------------------------------------
# Reference-form instructions (byte-identity oracle; rendered rails-side and
# carrier-independent -- kb_policy owns these strings).
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


class CoResidencyViolation(Exception):
    """THE invariant this redesign exists to hold was violated: the CPU
    embedder sidecar was resident while a frozen-core decode contact was in
    flight. Attempt 2 proved that state costs about 2,837 MiB of a 24,463 MiB
    card and collapses decode by about 51x, so the flight stops fail-closed."""


class SidecarCoResidencyGuard:
    """Fail-closed assertion that NO embedder sidecar is resident while a decode
    contact is in flight.

    Two independent probes, because either alone can lie: the launcher's own
    live sidecar handle (authoritative for a sidecar THIS process started) and a
    TCP reachability probe of the embedder port (catches a stray listener this
    process does not own). Armed for the canary, Pass A, Pass B and the resend;
    DISARMED only for the offline bridge, which is precisely the window in which
    the sidecar is supposed to be up and the GPU is supposed to be idle."""

    def __init__(self, port: int, sidecar_is_live) -> None:
        self._port = port
        self._sidecar_is_live = sidecar_is_live
        self._armed = False
        self._phase = "unarmed"
        self._lock = threading.Lock()
        self.checks = 0
        self.contact_checks = 0
        self.phase_checks: list[dict[str, object]] = []

    @property
    def armed(self) -> bool:
        return self._armed

    def arm(self, phase: str) -> None:
        self._armed = True
        self._phase = phase
        self.assert_clear("phase-boundary:%s" % phase, phase_boundary=True)

    def disarm(self, phase: str) -> None:
        self._armed = False
        self._phase = phase

    def assert_clear(self, where: str, *, phase_boundary: bool = False) -> None:
        if not self._armed:
            return
        with self._lock:
            self.checks += 1
            if not phase_boundary:
                self.contact_checks += 1
        live = bool(self._sidecar_is_live())
        reachable = _port_reachable("127.0.0.1", self._port, timeout=0.25)
        if phase_boundary:
            self.phase_checks.append(
                {
                    "where": where,
                    "at_utc": iso_now(),
                    "sidecar_handle_live": live,
                    "embedder_port_reachable": reachable,
                }
            )
        if live or reachable:
            raise CoResidencyViolation(
                "CO-RESIDENCY INVARIANT VIOLATED at %s during phase %r: embedder "
                "sidecar handle live=%s, port %d reachable=%s. Attempt 2 measured "
                "this exact state at 24,125 MiB of 24,463 with decode at 997 "
                "ms/token; refusing to fly a contact into it"
                % (where, self._phase, live, self._port, reachable)
            )

    def summary(self) -> dict[str, object]:
        return {
            "invariant": (
                "the CPU embedder sidecar is NEVER resident while a frozen-core "
                "decode contact is in flight"
            ),
            "enforcement": (
                "two independent probes -- the launcher's own live sidecar handle "
                "and a TCP reachability probe of the embedder port -- asserted "
                "before EVERY frozen-core contact and at every phase boundary, "
                "fail-closed"
            ),
            "total_checks": self.checks,
            "per_contact_checks": self.contact_checks,
            "phase_boundary_checks": self.phase_checks,
            "violations": 0,
            "held": True,
        }


class CoreCeilingClient:
    """Delegating frozen-core client wrapper enforcing the attempt-level
    core-contact ceiling FAIL-CLOSED, with an optional armed
    :class:`DecodeRateSentinel` consulted AFTER every completed contact and an
    optional :class:`SidecarCoResidencyGuard` consulted BEFORE every one.

    It also records the sha256 of the exact ``messages`` document each contact
    was built from, keyed by (contact id, sample id). Pass B's
    :class:`ReplayDirectClient` proves against those digests that the direct
    contact it resumes is the one Pass A actually flew."""

    def __init__(self, inner, ceiling: int) -> None:
        self._inner = inner
        self._ceiling = ceiling
        self._count = 0
        self._lock = threading.Lock()
        self._sentinel: "DecodeRateSentinel | None" = None
        self._guard: "SidecarCoResidencyGuard | None" = None
        self.message_digests: dict[tuple[str, str], str] = {}

    @property
    def contact_count(self) -> int:
        return self._count

    def arm_sentinel(self, sentinel: "DecodeRateSentinel | None") -> None:
        self._sentinel = sentinel

    def arm_coresidency_guard(self, guard: "SidecarCoResidencyGuard | None") -> None:
        self._guard = guard

    def complete(self, *args, **kwargs):
        guard = self._guard
        contact_id = kwargs.get("agent_contact_id")
        sample_id = kwargs.get("speech_feature_sample_id")
        if guard is not None:
            guard.assert_clear(
                "core contact %s/%s" % (contact_id, sample_id)
            )
        with self._lock:
            if self._count + 1 > self._ceiling:
                raise RuntimeError(
                    "arm core ceiling: <= %d frozen-core contacts registered and "
                    "%d are already spent; refusing the next contact fail-closed"
                    % (self._ceiling, self._count)
                )
            self._count += 1
        if isinstance(contact_id, str) and isinstance(sample_id, str) and args:
            digest = messages_digest(args[0])
            with self._lock:
                self.message_digests[(contact_id, sample_id)] = digest
        result = self._inner.complete(*args, **kwargs)
        sentinel = self._sentinel
        if sentinel is not None:
            sentinel.observe_after_contact()
        return result

    def __getattr__(self, name):
        return getattr(self._inner, name)


class ReplayDirectClient:
    """PASS B's core client: it RESUMES each trajectory's contact 0 from Pass
    A's durable record instead of re-flying it, and passes every other contact
    straight through to the metered client.

    This is not a shortcut around the measurement: Pass A flew exactly this
    contact, on this service instance, under this geometry, and its response is
    durable. What the replay must prove is that the contact the runner just
    built IS that contact, and it proves it the only way that cannot be argued
    with -- the sha256 of the ``messages`` document must equal the sha256 Pass A
    recorded for the same (contact id, sample id). A mismatch raises; NOTHING is
    substituted and nothing is skipped.

    A replayed contact spends no core contact, meters no audio and reaches no
    transport, which is exactly why the two-pass shape fits a budget the
    single-pass shape does not."""

    def __init__(self, inner, *, texts_by_sample, digests_by_sample, log_path) -> None:
        self._inner = inner
        self._texts = dict(texts_by_sample)
        self._digests = dict(digests_by_sample)
        self._log_path = log_path
        self._lock = threading.Lock()
        self.replayed = 0
        self.passed_through = 0
        self.replayed_sample_ids: list[str] = []

    def complete(
        self,
        messages,
        *,
        decoding_params=None,
        text_only_sample_id=None,
        speech_feature_sample_id=None,
        key_representation_id=None,
        matcher_policy_id=None,
        agent_state=None,
        agent_contact_id=None,
        contact_instruction=None,
    ):
        if agent_contact_id != _DIRECT_CONTACT_ID:
            with self._lock:
                self.passed_through += 1
            return self._inner.complete(
                messages,
                decoding_params=decoding_params,
                text_only_sample_id=text_only_sample_id,
                speech_feature_sample_id=speech_feature_sample_id,
                key_representation_id=key_representation_id,
                matcher_policy_id=matcher_policy_id,
                agent_state=agent_state,
                agent_contact_id=agent_contact_id,
                contact_instruction=contact_instruction,
            )
        sample_id = speech_feature_sample_id
        if not isinstance(sample_id, str) or sample_id not in self._texts:
            raise RuntimeError(
                "PASS B replay: no Pass-A direct response for sample %r; refusing "
                "to substitute anything for a contact that must be the flown one"
                % (sample_id,)
            )
        expected = self._digests.get(sample_id)
        measured = messages_digest(messages)
        if expected is None or measured != expected:
            raise RuntimeError(
                "PASS B replay REFUSED for %s: the messages document the runner "
                "built hashes to %s but Pass A flew %s. The replayed contact must "
                "be the flown contact; deferral is legitimate, substitution is not"
                % (sample_id, measured, expected)
            )
        if agent_state:
            raise RuntimeError(
                "PASS B replay: contact 0 must carry no prior agent state (%d given)"
                % len(agent_state)
            )
        text = self._texts[sample_id]
        with self._lock:
            self.replayed += 1
            self.replayed_sample_ids.append(sample_id)
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "sample_id": sample_id,
                            "agent_contact_id": agent_contact_id,
                            "key_representation_id": key_representation_id,
                            "matcher_policy_id": matcher_policy_id,
                            "messages_sha256": measured,
                            "pass_a_messages_sha256": expected,
                            "messages_byte_identical_to_pass_a": True,
                            "response_sha256": sha256_text(text),
                            "core_contacts_spent": 0,
                            "metered_audio_seconds": 0.0,
                        }
                    )
                    + "\n"
                )
        return text

    def summary(self) -> dict[str, object]:
        return {
            "semantics": (
                "PASS B resumes each trajectory's contact 0 from Pass A's durable "
                "record rather than re-flying it; the sha256 of the messages "
                "document is proved equal to Pass A's on every single replay"
            ),
            "replayed_contacts": self.replayed,
            "passed_through_contacts": self.passed_through,
            "core_contacts_saved": self.replayed,
            "log": str(self._log_path),
        }

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


class RuntimeEmbeddedBlendController:
    """BLEND wrapper: on the direct-decode response, embeds that text (ONE
    pinned-tool contact) into the injected content-dimension cell, then lets
    the REGISTERED controller advance. It adds NO policy behaviour."""

    def __init__(self, inner, *, sample_id: str, cell: LazyQueryVector, embed) -> None:
        self._inner = inner
        self._sample_id = sample_id
        self._cell = cell
        self._embed = embed
        self._filled = False
        self.direct_response_sha256: str | None = None
        self.direct_response_text: str | None = None
        # Launcher-side observability (never consulted by policy).
        self.direct_label_recovered: str | None = None
        self.direct_tool_multiset: tuple[str, ...] | None = None
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
            self.direct_response_text = response_text
            self.direct_tool_multiset = tool_name_multiset(response_text)
            vector = self._embed(self._sample_id, response_text)
            self._cell.fill(vector)
            self._filled = True
        advance = self._inner.advance(context, contact, response_text)
        if is_direct:
            self.direct_label_recovered = getattr(self._inner, "_direct_label", None)
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
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


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
                    "embedding tool ceiling: the BLEND arm registers <= %d contacts "
                    "and %d are already spent; refusing" % (self.ceiling, self.count)
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
    """Per-request serving records from raw llama-server log bytes --
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
    """Rolling-median in-flight decode-rate guard (flight-proven)."""

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
                        "%.2f ms/token over the last %d observed generation rows "
                        "exceeds the registered abort threshold %.0f ms/token; "
                        "window %r"
                        % (
                            rolling_median,
                            self._window.maxlen,
                            self._threshold,
                            [round(rate, 2) for rate in self._window],
                        )
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
        namespaced = "%s/%s" % (namespace, record_id)
        sink.emit(channel, namespaced, payload)
        flushed.append(namespaced)
    buffer.records = []
    return flushed


def assert_zero_record_id_overlap(sink_ids: Mapping[str, frozenset]) -> None:
    names = sorted(sink_ids)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = sink_ids[left] & sink_ids[right]
            if overlap:
                raise SystemExit(
                    "record-id overlap between the %r and %r trace sinks: %r; refusing"
                    % (left, right, sorted(overlap)[:5])
                )


def self_test() -> int:
    """Offline exercise: zero contacts, no service, no gate, no data root."""

    base = Path(tempfile.mkdtemp(prefix="saea-a2t-g1-selftest-"))
    log("SELF-TEST in %s (zero contacts, no service, no data root)" % base)

    # ---- mechanism a: micro-run trace isolation --------------------------
    def duplicate_heavy_buffer() -> TraceBuffer:
        buffer = TraceBuffer(RUN_ID)
        for sample_id in ("stub:000001", "stub:000002"):
            buffer.emit("ORG", "%s/agent-loop/org" % sample_id, {"org_stub": sample_id})
            buffer.emit("USE", "%s/agent-loop/use" % sample_id, {"use_stub": sample_id})
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
        log("self-test: shared-sink collision correctly refused (%s)" % error)
    else:
        raise SystemExit("self-test FAIL: duplicate flush into one sink did not raise")
    try:
        assert_zero_record_id_overlap(
            {"main": frozenset(main_ids), "canary": frozenset(main_ids)}
        )
    except SystemExit as error:
        log("self-test: overlap assertion correctly fired (%s)" % error)
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
                    "srv  log_server_r: |        eval time =    %.2f ms /    %d tokens "
                    "(   %.2f ms per token, %.2f tokens per second)\n"
                    % (rate * tokens, tokens, rate, 1000.0 / rate)
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
        log("self-test: sentinel correctly tripped (%s)" % error)
    if sentinel.tripped is None:
        raise SystemExit("self-test FAIL: sentinel did not trip on degraded rates")
    log("self-test mechanism b PASS: %r" % (sentinel.summary(),))

    # ---- prompt-reuse parser ---------------------------------------------
    stub_requests = (
        "165.41.712.384 I slot launch_slot_: id  1 | task 10 | processing task, is_child = 0\n"
        "165.41.748.510 I slot print_timing: id  1 | task 10 | prompt eval time =     233.21 ms /    75 tokens (    3.11 ms per token,   321.60 tokens per second)\n"
        "165.41.748.517 I slot print_timing: id  1 | task 10 |        eval time =    1714.68 ms /    48 tokens (   35.72 ms per token,    27.99 tokens per second)\n"
        "165.41.748.606 I slot      release: id  1 | task 10 | stop processing: n_tokens = 1817, truncated = 0\n"
        "165.59.000.000 I slot launch_slot_: id  0 | task 12 | processing task, is_child = 0\n"
    )
    parsed_requests = parse_slot_requests(stub_requests.encode("utf-8"))
    if len(parsed_requests) != 1:
        raise SystemExit(
            "self-test FAIL: parser returned %d complete requests" % len(parsed_requests)
        )
    first = parsed_requests[0]
    if (
        first["slot"],
        first["task"],
        first["prompt_eval_tokens"],
        first["generation_tokens"],
        first["release_n_tokens"],
    ) != (1, 10, 75, 48, 1817):
        raise SystemExit("self-test FAIL: parser row wrong: %r" % (first,))
    dist = token_count_distribution([5, 1, 9])
    if (dist["count"], dist["min"], dist["median"], dist["max"], dist["sum"]) != (3, 1, 5, 9, 15):
        raise SystemExit("self-test FAIL: token distribution wrong: %r" % (dist,))
    log("self-test prompt-reuse parser PASS")

    # ---- v1 frozen-cell knob sanity --------------------------------------
    if FROZEN_ALPHA != 0.45 or FROZEN_TAU != 0.65 or FROZEN_TOP_K != 5:
        raise SystemExit("self-test FAIL: frozen cell knobs drifted")
    if (FROZEN_FUSE.m, FROZEN_FUSE.c, FROZEN_FUSE.top_l) != (5, 2, 3):
        raise SystemExit("self-test FAIL: fuse knobs drifted from the frozen cell")
    if (FROZEN_WEIGHTS.w_cos, FROZEN_WEIGHTS.w_prior, FROZEN_WEIGHTS.w_agree) != (0.5, 0.3, 0.2):
        raise SystemExit("self-test FAIL: rank weights drifted from the frozen cell")
    if DECODING_PARAMS["max_tokens"] != 1024:
        raise SystemExit("self-test FAIL: the derived output ceiling drifted from 1024")
    log("self-test knob sanity PASS: byte-frozen v1 cell + derived output ceiling 1024")

    # ---- f1060078 repair-presence probe (the SLURP form, unchanged) -------
    probe_targets = {"facet:a": "alarm_query", "facet:b": "alarm_set"}
    flown_json = '{"scenario": "alarm", "action": "query", "entities": []}'
    if default_label_normalizer(flown_json, probe_targets) != "facet:a":
        raise SystemExit("self-test FAIL: the f1060078 repair is not present")
    swapped_json = '{"scenario": "query", "action": "alarm", "entities": []}'
    if default_label_normalizer(swapped_json, probe_targets) is not None:
        raise SystemExit("self-test FAIL: the normalizer matched a scenario/action SWAP")
    prose = "Intent 'alarm_query' (scenario='alarm', action='query'); 130 TRAIN utterances."
    if default_label_normalizer(prose, {"facet:a": prose}) is not None:
        raise SystemExit("self-test FAIL: prose-substring path is live (pre-repair behavior)")
    log("self-test repair-presence probe PASS")

    # ---- the A2T carrier analogue: exact-match only, never prose ----------
    a2t_targets = {
        "facet:label:tool:setBrightness": "setBrightness",
        "facet:label:tool:setLighting": "setLighting",
    }
    single = '[{"name": "setBrightness", "arguments": {"level": 40}}]'
    if a2t_primary_tool_normalizer(single, a2t_targets) != "facet:label:tool:setBrightness":
        raise SystemExit("self-test FAIL: A2T normalizer missed a single-call answer")
    multi = (
        '[{"name": "setLighting", "arguments": {}}, '
        '{"name": "setBrightness", "arguments": {"level": 10}}]'
    )
    if a2t_primary_tool_normalizer(multi, a2t_targets) != "facet:label:tool:setLighting":
        raise SystemExit("self-test FAIL: A2T normalizer did not take the PRIMARY call")
    if tool_name_multiset(multi) != ("setBrightness", "setLighting"):
        raise SystemExit("self-test FAIL: tool-name multiset projection wrong")
    unknown = '[{"name": "notARegisteredTool", "arguments": {}}]'
    if a2t_primary_tool_normalizer(unknown, a2t_targets) is not None:
        raise SystemExit("self-test FAIL: A2T normalizer matched a tool outside the vocabulary")
    prose_answer = "I would call setBrightness with level 40."
    if a2t_primary_tool_normalizer(prose_answer, a2t_targets) is not None:
        raise SystemExit(
            "self-test FAIL: the A2T normalizer matched PROSE -- the f1060078 class of "
            "defect, re-introduced on this carrier"
        )
    if a2t_primary_tool_normalizer("[]", a2t_targets) is not None:
        raise SystemExit("self-test FAIL: an empty call list is not dead-direct")
    if a2t_primary_tool_normalizer(None, a2t_targets) is not None:
        raise SystemExit("self-test FAIL: a non-string answer is not dead-direct")
    log(
        "self-test A2T carrier analogue PASS: primary-call exact match, multiset "
        "projection, unknown tool refused, prose refused, empty list dead-direct"
    )

    # ---- plan arithmetic: the TWO-PASS worst case against the REAL prior --
    #
    # This is the arithmetic that decides whether the attempt may take off at
    # all, so the self-test checks it offline before a single contact.
    #   PASS A  = 104 direct contacts, one per sample
    #   PASS B  = one contact per DISPATCHED trajectory, zero for a retained one
    #             (its contact 0 is resumed from Pass A, not re-flown)
    #   worst   = 2x2 canary + 104 + 26 + 1 resend = 135 core
    # Durable prior on the row at this attempt's registration: 196 core calls
    # and 941.061 audio seconds across the landed M0 arm and the two aborted
    # BLEND attempts. 196 + 135 = 331 <= 400.
    PRIOR_CORE_DURABLE = 196
    PRIOR_AUDIO_DURABLE = 941.061
    blend = ARMS["BLEND"]
    worst_core_self = (
        CANARY_SAMPLE_COUNT * 2 + SPLIT_COUNT + PASS_B_CONTACT_CEILING + 1
    )
    worst_audio_self = (
        2 * 3.234 + SPLIT_AUDIO_SECONDS_TOTAL + PASS_B_WORST_AUDIO_SECONDS + 1.097
    )
    if worst_core_self != 135:
        raise SystemExit(
            "self-test FAIL: the two-pass worst case is %d, not the registered 135"
            % worst_core_self
        )
    if worst_core_self > int(blend["attempt_core_ceiling"]):
        raise SystemExit("self-test FAIL: BLEND attempt core ceiling too small")
    if PRIOR_CORE_DURABLE + worst_core_self > min(
        int(blend["plan_calls"]), CAMPAIGN_CEILING_CORE
    ):
        raise SystemExit(
            "self-test FAIL: durable prior %d + worst case %d exceeds the cell"
            % (PRIOR_CORE_DURABLE, worst_core_self)
        )
    if PRIOR_AUDIO_DURABLE + worst_audio_self > min(
        float(blend["plan_audio"]), float(CAMPAIGN_CEILING_AUDIO)
    ):
        raise SystemExit(
            "self-test FAIL: durable prior %.3f audio-s + worst case %.3f exceeds "
            "the cell" % (PRIOR_AUDIO_DURABLE, worst_audio_self)
        )
    if PRIOR_TOOL_CONTACTS_DURABLE + int(blend["attempt_tool_ceiling"]) > (
        CAMPAIGN_CEILING_TOOL
    ):
        raise SystemExit("self-test FAIL: the tool ceiling does not fit the campaign")
    single_pass_worst = CANARY_SAMPLE_COUNT * 2 + SPLIT_COUNT * 2 + 1
    if PRIOR_CORE_DURABLE + single_pass_worst <= CAMPAIGN_CEILING_CORE:
        raise SystemExit(
            "self-test FAIL: the single-pass worst case would still fit, so the "
            "two-pass justification stated in this launcher is wrong"
        )
    log(
        "self-test plan arithmetic PASS: two-pass worst case %d core / %.3f audio-s "
        "on a durable prior of %d / %.3f fits 400 / 2000, while the single-pass "
        "worst case %d would NOT (196 + %d = %d > 400)"
        % (
            worst_core_self,
            worst_audio_self,
            PRIOR_CORE_DURABLE,
            PRIOR_AUDIO_DURABLE,
            single_pass_worst,
            single_pass_worst,
            PRIOR_CORE_DURABLE + single_pass_worst,
        )
    )

    # ---- mechanism c: the co-residency guard is fail-closed ---------------
    fake_sidecar = {"live": False}
    guard = SidecarCoResidencyGuard(1, lambda: fake_sidecar["live"])
    guard.assert_clear("unarmed")  # unarmed is a no-op, never a false alarm
    guard.arm("self-test")
    guard.assert_clear("clear host")
    fake_sidecar["live"] = True
    try:
        guard.assert_clear("sidecar resident")
    except CoResidencyViolation as error:
        log("self-test: co-residency guard correctly refused (%s)" % str(error)[:80])
    else:
        raise SystemExit("self-test FAIL: the guard admitted a resident sidecar")
    fake_sidecar["live"] = False
    guard.assert_clear("clear again")
    guard.disarm("self-test")
    fake_sidecar["live"] = True
    guard.assert_clear("disarmed during the bridge")  # the bridge window
    log("self-test mechanism c PASS: %r" % (guard.summary()["total_checks"],))

    # ---- mechanism d: the replay client refuses a substituted contact -----
    replay_log = base / "replay.jsonl"
    flown_messages = [{"role": "user", "content": "flown"}]
    other_messages = [{"role": "user", "content": "different"}]
    replay_inner_calls: list[str] = []

    class _StubInner:
        def complete(self, messages, **kwargs):
            replay_inner_calls.append(str(kwargs.get("agent_contact_id")))
            return "evidence answer"

    replay = ReplayDirectClient(
        _StubInner(),
        texts_by_sample={"stub:000001": "the flown direct answer"},
        digests_by_sample={"stub:000001": messages_digest(flown_messages)},
        log_path=replay_log,
    )
    replayed = replay.complete(
        flown_messages,
        speech_feature_sample_id="stub:000001",
        agent_contact_id=_DIRECT_CONTACT_ID,
    )
    if replayed != "the flown direct answer" or replay_inner_calls:
        raise SystemExit("self-test FAIL: the replay did not serve Pass A's own text")
    try:
        replay.complete(
            other_messages,
            speech_feature_sample_id="stub:000001",
            agent_contact_id=_DIRECT_CONTACT_ID,
        )
    except RuntimeError as error:
        log("self-test: replay correctly refused a drifted prompt (%s)" % str(error)[:80])
    else:
        raise SystemExit("self-test FAIL: the replay served a contact it never flew")
    try:
        replay.complete(
            flown_messages,
            speech_feature_sample_id="stub:999999",
            agent_contact_id=_DIRECT_CONTACT_ID,
        )
    except RuntimeError:
        log("self-test: replay correctly refused an unknown sample")
    else:
        raise SystemExit("self-test FAIL: the replay invented a response")
    evidence = replay.complete(
        flown_messages,
        speech_feature_sample_id="stub:000001",
        agent_contact_id="evidence-decode",
    )
    if evidence != "evidence answer" or replay_inner_calls != ["evidence-decode"]:
        raise SystemExit("self-test FAIL: the evidence contact was not passed through")
    if replay.replayed != 1 or replay.passed_through != 1:
        raise SystemExit("self-test FAIL: replay accounting is wrong")
    log("self-test mechanism d PASS: %r" % (replay.summary(),))

    for arm_id, arm in ARMS.items():
        if float(arm["plan_audio"]) > CAMPAIGN_CEILING_AUDIO:
            raise SystemExit("self-test FAIL: %s plan audio exceeds the row cell" % arm_id)
        if int(arm["attempt_tool_ceiling"]) > CAMPAIGN_CEILING_TOOL:
            raise SystemExit("self-test FAIL: %s tool ceiling exceeds the row cell" % arm_id)
        if float(arm["plan_gpu"]) > CAMPAIGN_CEILING_GPU_HOURS:
            raise SystemExit("self-test FAIL: %s plan gpu exceeds the row cell" % arm_id)
        if int(arm["plan_calls"]) > CAMPAIGN_CEILING_CORE:
            raise SystemExit("self-test FAIL: %s plan calls exceed the row cell" % arm_id)
    if sum(float(a["plan_gpu"]) for a in ARMS.values()) > CAMPAIGN_CEILING_GPU_HOURS:
        raise SystemExit("self-test FAIL: the summed per-arm GPU plans exceed the row cell")

    # ---- both arms fly the SAME derived geometry and the SAME population --
    for arm_id, arm in ARMS.items():
        if arm["split_id"] != SPLIT_ID:
            raise SystemExit(
                "self-test FAIL: arm %s flies %r; both G1 arms MUST fly the full "
                "%s" % (arm_id, arm["split_id"], SPLIT_ID)
            )
    log("self-test population PASS: both arms fly the full %s" % SPLIT_ID)
    log("SELF-TEST PASS (zero contacts)")
    return 0


def guarded_post(timeout_seconds: float):
    import urllib.request

    def post(url: str, body: bytes) -> bytes:
        assert_payload_has_no_forbidden_keys(
            json.loads(body.decode("utf-8")), context="emb-request"
        )
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
        raise SystemExit("unknown arm %r; registered arms: %r" % (arm_id, sorted(ARMS)))
    if arm_id != "BLEND":
        raise SystemExit(
            "this is the THIRD BLEND ATTEMPT launcher and it flies the BLEND arm "
            "only. The M0 arm landed complete at attempt-20260825T100735Z-a2tg1m0 "
            "and is scored; re-flying it would spend contacts on a settled result "
            "and would break the paired comparison's population identity"
        )
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

    attempt_id = "attempt-%s-a2tg1%s" % (
        datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        slug,
    )
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log("A2T STAGE G1 ARM %s -- %s / %s" % (arm_id, RUN_ID, attempt_id))
    log("run dir: %s" % run_dir)

    flight: dict[str, object] = {
        "schema": "saea-a2t-g1-arm-flight-v1",
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
        raise SystemExit("GPU preflight: enforced power limit %s W < 95 W" % enforced_w)
    flight["gpu_preflight"]["enforced_power_limit_w_in_wsl"] = enforced_w
    log("GPU preflight: enforced power limit %s W (>= 95)" % enforced_w)

    # ---- composition ------------------------------------------------------
    composed = compose(
        REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT
    )
    values = composed.values
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise SystemExit(
            "composed config hash %s != registered %s"
            % (composed.config_hash, COMPOSED_CONFIG_SHA256)
        )
    server_args = list(values["server_args"])
    server_np = int(server_args[server_args.index("-np") + 1])
    server_ctx = int(server_args[server_args.index("-c") + 1])
    if server_np != 2 or server_ctx != 65536:
        raise SystemExit(
            "composed geometry is -c %d -np %d, not the section 8.1 derived -c 65536 -np 2"
            % (server_ctx, server_np)
        )
    if int(values["decoding_params"]["max_tokens"]) != DECODING_PARAMS["max_tokens"]:
        raise SystemExit("composed max_tokens disagrees with the derived output ceiling")
    cell = values["a2t_g1_policy_cell"]["knobs"]
    if (
        cell["alpha"] != FROZEN_ALPHA
        or cell["tau"] != FROZEN_TAU
        or cell["recall_top_k_per_dimension"] != FROZEN_TOP_K
        or cell["fusion"] != {"m": 5, "c": 2, "l": 3}
        or cell["rank_weights"] != {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}
    ):
        raise SystemExit("composed frozen-cell knobs disagree with this launcher's constants")
    log(
        "composed config hash %s (-c %d -np %d, %d tokens per slot; v1 cell knobs equal)"
        % (composed.config_hash, server_ctx, server_np, server_ctx // server_np)
    )
    flight["config_hash"] = composed.config_hash
    flight["server_np"] = server_np
    flight["tokens_per_slot"] = server_ctx // server_np

    # ---- the v1 POLICY CELL, hash-pinned ---------------------------------
    policy_path = REPO / POLICY_CELL_RELPATH
    measured_policy = sha256_file(policy_path)
    if measured_policy != POLICY_CELL_SHA256:
        raise SystemExit(
            "the v1 policy cell hashes to %s, not the registered %s; the "
            "byte-identical transfer claim would be false"
            % (measured_policy, POLICY_CELL_SHA256)
        )
    policy_file = json.loads(policy_path.read_text(encoding="utf-8"))
    file_knobs = policy_file["knobs"]
    if (
        file_knobs["alpha"] != FROZEN_ALPHA
        or file_knobs["tau"] != FROZEN_TAU
        or file_knobs["recall_top_k_per_dimension"] != FROZEN_TOP_K
        or file_knobs["fusion"] != {"m": 5, "c": 2, "l": 3}
        or file_knobs["rank_weights"] != {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2}
        or file_knobs["prior_source"] != "train"
        or file_knobs["percept_admission"] != "facet-side (value vectors sealed)"
    ):
        raise SystemExit("the v1 policy cell file's knobs disagree with this launcher")
    log(
        "v1 policy cell pinned (%s), knobs agreed by the cell file, the composed "
        "fragment and this launcher -- BYTE-IDENTICAL TRANSFER" % measured_policy[:12]
    )
    flight["policy_cell"] = {
        "relpath": POLICY_CELL_RELPATH,
        "sha256": measured_policy,
        "prelock_sha256": POLICY_CELL_PRELOCK_SHA256,
        "file_hash_note": (
            "the DEV-1000 lock launcher pinned this file's PRE-LOCK bytes "
            "(0d36273e...). The lock commit d9fef537 added two ANNOTATION keys, "
            "STATUS and locked_at, and edited nothing inside knobs; the knob table "
            "this flight carries is proved equal key for key against the file, the "
            "composed fragment and this launcher's own constants."
        ),
        "transfer": "BYTE-IDENTICAL (campaign plan section 8.2)",
        "delta_retain_override": "NOT CARRIED (v1, not the v2 lock candidate)",
    }

    # ---- serving geometry: DERIVED, and verified live --------------------
    derivation = values["a2t_g1_serving_geometry_derivation"]
    required = int(derivation["step_3_slot_width"]["requirement_worst_case"])
    per_slot = server_ctx // server_np
    if per_slot <= required:
        raise SystemExit(
            "derived geometry does not clear its own requirement: %d tokens per slot "
            "against %d required" % (per_slot, required)
        )
    log(
        "section 8.1 derivation verified: %d tokens per slot against %d required, "
        "margin +%d" % (per_slot, required, per_slot - required)
    )
    flight["serving_geometry"] = {
        "rule": "campaign plan section 8.1",
        "context_total": server_ctx,
        "parallel_slots": server_np,
        "tokens_per_slot": per_slot,
        "requirement_worst_case": required,
        "margin_tokens": per_slot - required,
        "output_ceiling": DECODING_PARAMS["max_tokens"],
        "status": "DERIVED per carrier by the fixed rule, applied identically to every arm",
    }

    # ---- subset receipt + packet promotion receipt ------------------------
    receipt_path = REPO / SUBSET_RECEIPT_RELPATH
    measured_receipt = sha256_file(receipt_path)
    if measured_receipt != SUBSET_RECEIPT_SHA256:
        raise SystemExit("subset receipt hashes to %s, not the pin" % measured_receipt)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt["split_name"] != SPLIT_ID
        or receipt["count"] != SPLIT_COUNT
        or receipt["run_identity_hash"] != SPLIT_IDENTITY_HASH
        or receipt["split_identity_hash"] != SPLIT_RECEIPT_INTEGRITY_HASH
        or receipt["parent_split_identity_hash"] != PARENT_SPLIT_IDENTITY_HASH
    ):
        raise SystemExit("subset receipt identity drifted")
    if abs(float(receipt["audio_seconds_total"]) - SPLIT_AUDIO_SECONDS_TOTAL) > 1e-6:
        raise SystemExit("subset receipt audio total drifted")
    # The subset must still be a subset of the frozen exposed 400. Compared on
    # sample_id: the parent receipt's items carry a carrier-prefixed ``key``
    # and comparing on THAT yields a silently empty intersection.
    parent = json.loads((REPO / PARENT_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    parent_ids = {
        "%s:%06d" % (item["tier"], int(item["id"])) for item in parent["items"]
    }
    subset_ids = {item["sample_id"] for item in receipt["items"]}
    if len(parent_ids) != 400 or not subset_ids <= parent_ids:
        raise SystemExit("the G1 subset is not inside the frozen exposed 400")
    log(
        "subset receipt verified (%s): %d of the frozen exposed 400, %.3f audio-s"
        % (measured_receipt[:12], len(subset_ids), float(receipt["audio_seconds_total"]))
    )

    measured_promotion = sha256_file(PROMOTION_RECEIPT_PATH)
    if measured_promotion != PROMOTION_RECEIPT_SHA256:
        raise SystemExit(
            "packet promotion receipt hashes to %s, not the pin" % measured_promotion
        )
    promotion = json.loads(PROMOTION_RECEIPT_PATH.read_text(encoding="utf-8"))
    if (
        promotion["subset_receipt_sha256"] != SUBSET_RECEIPT_SHA256
        or int(promotion["count"]) != SPLIT_COUNT
        or promotion["split_identity_hash"] != SPLIT_IDENTITY_HASH
    ):
        raise SystemExit("promotion receipt binds a different subset")
    log(
        "packet promotion receipt verified (%s, %d packets, build %s)"
        % (
            measured_promotion[:12],
            int(promotion["count"]),
            promotion["llama_cpp_build_commit"][:8],
        )
    )
    flight["packet_promotion"] = {
        "receipt": str(PROMOTION_RECEIPT_PATH),
        "sha256": measured_promotion,
        "count": int(promotion["count"]),
        "build_commit": promotion["llama_cpp_build_commit"],
    }

    # ---- knowledge snapshot + SEALED-value discipline ---------------------
    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise SystemExit("A2T knowledge snapshot content hash mismatch")
    label_targets = dict(_label_identities(snapshot))
    if len(label_targets) != LABEL_VOCABULARY_SIZE:
        raise SystemExit(
            "A2T label vocabulary is %d identities, not the registered %d"
            % (len(label_targets), LABEL_VOCABULARY_SIZE)
        )
    log(
        "A2T snapshot verified: %d facets / %d values / %d label identities"
        % (len(snapshot.facets), len(snapshot.values), len(label_targets))
    )
    # Decontamination, re-proved here rather than inherited: no flown sample
    # may be in the snapshot's own construction roster.
    contaminated = subset_ids & set(snapshot.source_sample_ids)
    if contaminated:
        raise SystemExit(
            "DECONTAMINATION FAILURE: %d flown samples are in the KB construction "
            "roster: %r" % (len(contaminated), sorted(contaminated)[:5])
        )
    if snapshot.source_split_identity_hash == SPLIT_IDENTITY_HASH:
        raise SystemExit("knowledge BUILD and AgentLoop USE share a split identity")

    facet_vector_table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    if arm_id == "BLEND":
        emb_receipt = json.loads(
            (REPO / EMBEDDINGS_RECEIPT_RELPATH).read_text(encoding="utf-8")
        )
        facet_block = emb_receipt["vectors"]["content_facets"]
        facet_npz_path = snapshot_path.parent / facet_block["file"]
        measured_npz = sha256_file(facet_npz_path)
        if measured_npz != facet_block["sha256"]:
            raise SystemExit("content-facet npz hash mismatch vs the landed receipt")
        if emb_receipt["snapshot"]["content_sha256"] != SNAPSHOT_SHA256:
            raise SystemExit("the embeddings receipt names a different snapshot")
        npz = np.load(facet_npz_path)
        facet_ids = [str(v) for v in npz["ids"]]
        facet_matrix = npz["vectors"]
        if facet_matrix.shape != (len(facet_ids), EMBEDDER_DIM):
            raise SystemExit("unexpected facet vector shape %r" % (facet_matrix.shape,))
        for index, facet_id in enumerate(facet_ids):
            facet_vector_table[facet_id] = {"content": tuple(facet_matrix[index].tolist())}
        log(
            "content-facet vectors loaded: %r (%s). VALUE VECTORS SEALED: no value "
            "vector file exists and none is loaded." % (facet_matrix.shape, measured_npz[:12])
        )
        flight["knowledge"] = {
            "snapshot_sha256": SNAPSHOT_SHA256,
            "facet_vectors_npz_sha256": measured_npz,
            "value_vectors_loaded": False,
            "percept_admission": "facet-side (fuser construction)",
            "label_identities": len(label_targets),
        }
    else:
        log("content-facet vectors NOT loaded for this arm (M0); VALUE VECTORS SEALED")
        flight["knowledge"] = {
            "snapshot_sha256": SNAPSHOT_SHA256,
            "facet_vectors_npz_loaded": False,
            "value_vectors_loaded": False,
            "label_identities": len(label_targets),
        }

    save_flight()

    # ---- samples ----------------------------------------------------------
    adapter = A2TG1Adapter(lock, root, repo_root=REPO, receipt_items=receipt["items"])
    all_samples = adapter.load_split(SPLIT_ID)
    if len(all_samples) != SPLIT_COUNT:
        raise SystemExit("%d samples, expected %d" % (len(all_samples), SPLIT_COUNT))
    samples = adapter.load_split(split_id)
    if split_id != SPLIT_ID or len(samples) != SPLIT_COUNT:
        raise SystemExit(
            "arm %s resolved %d samples of split %r; both G1 arms MUST fly the full "
            "%s (%d samples)" % (arm_id, len(samples), split_id, SPLIT_ID, SPLIT_COUNT)
        )
    loop_audio = sum(float(s.audio_seconds) for s in samples)
    log(
        "arm split %s: %d samples, one metered pass = %.6fs"
        % (split_id, len(samples), loop_audio)
    )

    packet_bindings: dict[str, dict[str, str]] = {}
    for item in receipt["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        if packet.audio_sha256 != item["audio_sha256"]:
            raise SystemExit("packet %s carries a different audio sha256" % item["packet_id"])
        packet_bindings[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    if set(packet_bindings) != {s.sample_id for s in all_samples}:
        raise SystemExit("packet bindings do not cover the G1 subset")
    log("speech packet bindings materialized for all %d samples" % SPLIT_COUNT)

    payload_binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=all_samples,
        data_root=root,
        carrier_root=asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
    )
    log("payload binding built (inputs complete, still pre-gate)")

    # ---- canary hash authority -------------------------------------------
    canary_samples = adapter.load_split(CANARY_SPLIT_ID)
    canary_ids = [sample.sample_id for sample in canary_samples]
    resend_sample_id = canary_ids[0]
    canary_authority: dict[str, str] | None = None
    if arm_id == "BLEND":
        if not CANARY_AUTHORITY_PATH.exists():
            raise SystemExit(
                "no canary hash authority at %s: the M0 arm must land first, because "
                "this campaign establishes its OWN authority (no prior A2T flight ran "
                "this geometry)" % CANARY_AUTHORITY_PATH
            )
        authority_doc = json.loads(CANARY_AUTHORITY_PATH.read_text(encoding="utf-8"))
        if authority_doc["run_id"] != RUN_ID or authority_doc["sample_ids"] != canary_ids:
            raise SystemExit("the landed canary authority names a different pair")
        canary_authority = dict(authority_doc["response_sha256"])
        log(
            "canary hash authority loaded from the M0 arm (%s, attempt %s)"
            % (CANARY_AUTHORITY_PATH.name, authority_doc["attempt_id"])
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
    probe_targets = {
        "facet:label:tool:setBrightness": "setBrightness",
        "facet:label:tool:setLighting": "setLighting",
    }
    if (
        a2t_primary_tool_normalizer(
            '[{"name": "setBrightness", "arguments": {}}]', probe_targets
        )
        != "facet:label:tool:setBrightness"
        or a2t_primary_tool_normalizer(
            "I would call setBrightness.", probe_targets
        )
        is not None
        or a2t_primary_tool_normalizer('[{"name": "nope", "arguments": {}}]', probe_targets)
        is not None
    ):
        raise SystemExit(
            "invariant MISSING: the A2T carrier analogue of the f1060078 repair is "
            "not behaving (exact primary-name match only, prose refused); refusing"
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
            "rails/kb_policy.py's last commit is %s, not the repair commit f1060078 "
            "-- rails/ was touched; refusing" % kb_policy_last_commit[:12]
        )
    repo_head_commit = _subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    flight["invariants"] = {
        "kb_policy_last_commit": kb_policy_last_commit,
        "repo_head_at_flight": repo_head_commit,
        "slurp_repair_probe": "PASS (identity exact-match live, swap refused)",
        "a2t_analogue_probe": "PASS (primary-name exact match, prose refused, unknown tool refused)",
        "frozen_cell": "byte-frozen v1 cell (no knob change on this carrier)",
    }
    log(
        "invariants: kb_policy last commit %s, repo HEAD %s, both repair probes PASS"
        % (kb_policy_last_commit[:12], repo_head_commit[:12])
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
        query_id="dry:%s" % dry_sample.sample_id,
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
        normalizer=a2t_primary_tool_normalizer,
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
                "guard simulation: %s instruction embeds protected knowledge payloads "
                "%r; refusing before takeoff" % (name, hits[:3])
            )
    log(
        "dry check PASS: rails-rendered direct instruction byte-identical to the "
        "registered form; instructions clear all %d protected payloads" % len(protected)
    )

    # ---- pre-takeoff AttemptStore inspection + fail-closed sizing guard ----
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(RUN_ID)
    prior_records = (
        sorted(p.name for p in (root / "attempts" / RUN_ID).glob("*.json"))
        if (root / "attempts" / RUN_ID).is_dir()
        else []
    )
    canary_samples_audio = sum(float(s.audio_seconds) for s in canary_samples)
    resend_audio = (
        float(adapter.load_split(RESEND_SPLIT_ID)[0].audio_seconds) if with_resend else 0.0
    )
    # ---- the registered dispatch projection, pinned before it is used ----
    #
    # The Pass-B ceiling is BELOW the arithmetic worst case, which is admissible
    # only with its basis stated. The basis is a separately registered model-free
    # row, and this launcher refuses to fly if that artifact is absent or says
    # something other than what the ceiling was derived from.
    projection_path = OUT_CHECK_DIR / DISPATCH_PROJECTION_RELNAME
    if not projection_path.exists():
        raise SystemExit(
            "the registered dispatch projection %s is missing; the lowered Pass-B "
            "ceiling has no basis and this launcher refuses to fly"
            % DISPATCH_PROJECTION_RELNAME
        )
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    if (
        projection.get("run_id") != DISPATCH_PROJECTION_RUN_ID
        or projection.get("about_run_id") != RUN_ID
        or projection.get("population", {}).get("count") != SPLIT_COUNT
        or projection.get("population", {}).get("split_identity_hash")
        != SPLIT_IDENTITY_HASH
    ):
        raise SystemExit("the dispatch projection is about a different population")
    projected_dispatch = int(projection["projection"]["dispatch_count"])
    if projected_dispatch != DISPATCH_PROJECTION_COUNT:
        raise SystemExit(
            "the dispatch projection reports %d dispatches, not the %d this "
            "attempt's ceiling was derived from; re-derive the ceiling rather than "
            "flying against a stale basis"
            % (projected_dispatch, DISPATCH_PROJECTION_COUNT)
        )
    if PASS_B_CONTACT_CEILING < projected_dispatch:
        raise SystemExit("the Pass-B ceiling is below its own projection")
    flight["dispatch_projection"] = {
        "row": DISPATCH_PROJECTION_RUN_ID,
        "artifact": DISPATCH_PROJECTION_RELNAME,
        "artifact_sha256": sha256_file(projection_path),
        "projected_dispatch_count": projected_dispatch,
        "projected_dispatch_rate": projection["projection"]["dispatch_rate"],
        "registered_pass_b_ceiling": PASS_B_CONTACT_CEILING,
        "margin_over_projection": PASS_B_CONTACT_CEILING - projected_dispatch,
        "mechanism": (
            "content-facet cosines are healthy (all 104 above tau) but ALL 104 "
            "trajectories have ZERO content facets in the top-m rank window the "
            "fuser admits over, because the ranker's prior-mass dimensions score "
            "well above any cosine; percept admission reads only NON-prior-mass "
            "dimensions, so nothing is admitted and nothing is selected"
        ),
        "flown_corroboration": (
            "attempts 1 and 2 together flew 86 BLEND trajectories and produced 86 "
            "direct-decode contacts and ZERO evidence-decode contacts"
        ),
        "limitation": projection.get("limitation"),
    }

    # ---- the TWO-PASS worst case, which is what actually binds -----------
    #
    # Pass A is exactly one contact per sample. Pass B costs one contact per
    # DISPATCHED trajectory and zero for a retained one, because its contact 0 is
    # resumed from Pass A rather than re-flown. The audio bound uses the
    # PASS_B_CONTACT_CEILING LARGEST sample durations, so it holds whichever
    # trajectories dispatch.
    sample_audio_desc = sorted(
        (float(sample.audio_seconds) for sample in samples), reverse=True
    )
    pass_b_worst_audio = sum(sample_audio_desc[:PASS_B_CONTACT_CEILING])
    if abs(pass_b_worst_audio - PASS_B_WORST_AUDIO_SECONDS) > 0.01:
        raise SystemExit(
            "the %d largest sample durations sum to %.3f s, not the registered "
            "%.3f s; the audio guard's basis drifted"
            % (PASS_B_CONTACT_CEILING, pass_b_worst_audio, PASS_B_WORST_AUDIO_SECONDS)
        )
    worst_core = (
        CANARY_SAMPLE_COUNT * 2
        + len(samples)
        + PASS_B_CONTACT_CEILING
        + (1 if with_resend else 0)
    )
    worst_audio = (
        canary_samples_audio * 2 + loop_audio + pass_b_worst_audio + resend_audio
    )
    flight["two_pass_worst_case"] = {
        "canary_incl_one_rerun": CANARY_SAMPLE_COUNT * 2,
        "pass_a_contacts": len(samples),
        "pass_b_contacts_ceiling": PASS_B_CONTACT_CEILING,
        "resend": 1 if with_resend else 0,
        "worst_core": worst_core,
        "worst_audio_seconds": round(worst_audio, 6),
        "single_pass_worst_core_for_comparison": (
            CANARY_SAMPLE_COUNT * 2
            + len(samples) * max_contacts
            + (1 if with_resend else 0)
        ),
    }
    if worst_core > attempt_core_ceiling:
        raise SystemExit(
            "attempt worst case %d exceeds the registered attempt core ceiling %d; refusing"
            % (worst_core, attempt_core_ceiling)
        )
    if prior_calls + worst_core > min(plan_calls, CAMPAIGN_CEILING_CORE):
        raise SystemExit(
            "REFUSED TAKEOFF at zero spend: durable prior %d calls + worst case %d "
            "exceeds min(plan %d, campaign %d)"
            % (prior_calls, worst_core, plan_calls, CAMPAIGN_CEILING_CORE)
        )
    if prior_audio + worst_audio > min(plan_audio, CAMPAIGN_CEILING_AUDIO):
        raise SystemExit(
            "REFUSED TAKEOFF at zero spend: durable prior %.2f audio-s + worst case "
            "%.2f exceeds min(plan %d, campaign %d)"
            % (prior_audio, worst_audio, plan_audio, CAMPAIGN_CEILING_AUDIO)
        )
    if PRIOR_TOOL_CONTACTS_DURABLE + attempt_tool_ceiling > CAMPAIGN_CEILING_TOOL:
        raise SystemExit(
            "REFUSED TAKEOFF at zero spend: durable prior %d embedding tool contacts + "
            "this attempt's ceiling %d exceeds the campaign tool ceiling %d"
            % (PRIOR_TOOL_CONTACTS_DURABLE, attempt_tool_ceiling, CAMPAIGN_CEILING_TOOL)
        )
    flight["pre_takeoff_attempt_store"] = {
        "prior_records": prior_records,
        "prior_calls": prior_calls,
        "prior_audio_seconds": prior_audio,
        "worst_case_core_this_attempt": worst_core,
        "worst_case_audio_this_attempt": round(worst_audio, 6),
        "prior_tool_contacts_durable": PRIOR_TOOL_CONTACTS_DURABLE,
        "attempt_tool_ceiling": attempt_tool_ceiling,
        "campaign_tool_ceiling": CAMPAIGN_CEILING_TOOL,
    }
    log(
        "AttemptStore pre-takeoff: %d prior records, %d calls / %.2f audio-s durable; "
        "this attempt worst case %d calls / %.2f audio-s fits plan %d/%d and campaign %d/%d"
        % (
            len(prior_records),
            prior_calls,
            prior_audio,
            worst_core,
            worst_audio,
            plan_calls,
            plan_audio,
            CAMPAIGN_CEILING_CORE,
            CAMPAIGN_CEILING_AUDIO,
        )
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
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
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
    log("frozen-core gate PASS in %.1fs (lock %s)" % (time.time() - gate_started, lock_sha256[:12]))
    flight["gate"] = {
        "umbrella_lock_sha256": lock_sha256,
        "seconds": round(time.time() - gate_started, 1),
    }
    save_flight()

    # ---- attach to the resident np2 service ------------------------------
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    session_receipt_path = SESSION_DIR / "session-receipt.json"
    measured_session = sha256_file(session_receipt_path)
    if measured_session != SESSION_RECEIPT_SHA256:
        raise SystemExit(
            "resident session receipt hashes to %s, not the registered %s; the "
            "service was restarted or mutated -- the session-bound prompt fit no "
            "longer stands; STOP and re-measure" % (measured_session, SESSION_RECEIPT_SHA256)
        )
    session = attach_session(
        session_receipt_path, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao")
    )
    expected_argv = (
        [session.argv[0], "--host", "127.0.0.1", "--port", str(DECODER_PORT)]
        + ["-m", session.argv[6], "--no-mmproj"]
        + server_args
    )
    if list(session.argv) != expected_argv:
        raise SystemExit("resident session argv does not match the np2 composition")
    log(
        "attached to resident np2 session pid=%s (receipt %s)"
        % (session.pid, measured_session[:12])
    )
    flight["decoder_session"] = {
        "session_id": session.session_id,
        "pid": session.pid,
        "port": session.port,
        "receipt_sha256": measured_session,
        "np": server_np,
    }
    save_flight()

    transport = TRANSPORTS.resolve(str(values["transport"]))(
        values, root, session=session, runtime_receipt=runtime_receipt,
        runtime_root=Path("/home/chao"),
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=payload_binding,
        arm="speech-feature-query",
        request_id_prefix="a2tg1%s" % slug,
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    log("FrozenCoreClient constructed (arm %s)" % client.arm)

    # ---- FIX 1: launcher-local clock / power / throttle telemetry ---------
    clock_sampler = ClockThrottleSampler(
        root / "runs" / RUN_ID / ("clock-samples-%s.jsonl" % slug),
        interval_seconds=3.0,
        phase="pre-takeoff",
    )
    clock_sampler.start()
    log(
        "FIX 1 armed: clock/power/throttle sampler writing %s every 3.0 s "
        "(clocks.sm, clocks.max.sm, power.draw, clocks_throttle_reasons.*)"
        % (root / "runs" / RUN_ID / ("clock-samples-%s.jsonl" % slug))
    )

    # ---- embedding sidecar (BLEND arm only; own session + stop receipt) ---
    #
    # FIX 2 restructures this from "one sidecar up for the whole arm, one live
    # embed inside every trajectory" into "one OFFLINE precompute pass, sidecar
    # DOWN for the GPU loop, lazily re-spawned only if a flown text diverges".
    meter: EmbeddingMeter | None = None
    emb_session = None
    emb_client = None
    emb_runtime_receipt = None
    jitter_text = None
    jitter_authority: tuple[float, ...] | None = None
    embed_lock = threading.Lock()
    emb_spawn_count = 0
    emb_spawn_records: list[dict[str, object]] = []
    emb_stop_records: list[dict[str, object]] = []
    precomputed_by_text_sha: dict[str, tuple[float, ...]] = {}
    lookup_stats: dict[str, object] = {"hits": 0, "misses": 0, "miss_sample_ids": []}
    query_vector_log = run_dir / "query-vectors.jsonl"

    def _spawn_sidecar(reason: str) -> None:
        """Spawn the pinned CPU-only embedder. Each spawn re-runs the
        encode-only surface assertion and the media-marker check, and probes
        the SAME jitter text so cross-spawn numerics are provable."""

        nonlocal emb_session, emb_client, emb_spawn_count, jitter_authority
        if emb_client is not None:
            return
        for _ in range(60):
            if not _port_reachable("127.0.0.1", EMB_PORT, timeout=0.5):
                break
            time.sleep(0.5)
        if _port_reachable("127.0.0.1", EMB_PORT, timeout=0.5):
            raise SystemExit("something already listens on %d" % EMB_PORT)
        emb_spawn_count += 1
        index = emb_spawn_count
        log(
            "spawning CPU-only embedder sidecar #%d (%s) on %d: %r"
            % (index, reason, EMB_PORT, list(EMB_SERVER_ARGS))
        )
        spawn_started = time.time()
        emb_session = start_session(
            runtime_root=Path("/home/chao"),
            data_root=root,
            runtime_receipt=emb_runtime_receipt,
            host="127.0.0.1",
            port=EMB_PORT,
            session_id="%s-%s-qwen3-emb-cpu-%d" % (RUN_ID, attempt_id, index),
            extra_argv=list(EMB_SERVER_ARGS),
            receipt_path=run_dir / ("session-qwen3-emb-cpu-%d.receipt.json" % index),
            server_log_path=run_dir / ("session-qwen3-emb-cpu-%d.server.log" % index),
            ready_timeout_seconds=900.0,
        )
        emb_client = EmbeddingClient(
            base_url="http://127.0.0.1:%d" % EMB_PORT,
            post=guarded_post(600.0),
            timeout_seconds=600.0,
            expected_dim=EMBEDDER_DIM,
            require_marker_verification=False,
        )
        assert_client_surface_is_encode_only(emb_client)
        emb_client.verify_media_marker()
        contact_id = "jitter:spawn%d" % index
        meter.charge(contact_id)
        probe_started = time.time()
        probe = emb_client.embed_text(contact_id=contact_id, text=jitter_text)
        meter.record(
            contact_id,
            time.time() - probe_started,
            probe.dims,
            sha256_text(jitter_text),
        )
        values = tuple(probe.values)
        if jitter_authority is None:
            jitter_authority = values
            identical = True
        else:
            identical = values == jitter_authority
        emb_spawn_records.append(
            {
                "spawn_index": index,
                "reason": reason,
                "pid": emb_session.pid,
                "ready_seconds": round(time.time() - spawn_started, 2),
                "jitter_bit_identical_to_first_spawn": identical,
                "at_utc": iso_now(),
            }
        )
        log(
            "embedder sidecar #%d up: pid=%s port=%s ready in %.1f s; encode-only "
            "surface asserted, media marker verified, jitter bit-identical to the "
            "first spawn = %s"
            % (
                index,
                emb_session.pid,
                emb_session.port,
                time.time() - spawn_started,
                identical,
            )
        )
        if not identical:
            log(
                "WARNING: sidecar #%d jitter vector is NOT bit-identical to the first "
                "spawn; live-embedded misses may not share the precomputed numerics" % index
            )

    def _stop_sidecar(reason: str) -> dict[str, object]:
        """Stop the sidecar with its own receipt, probing the jitter text once
        more first. Never raises: teardown reports, it does not mask."""

        nonlocal emb_session, emb_client
        record: dict[str, object] = {"reason": reason, "at_utc": iso_now()}
        if emb_client is None:
            record["skipped"] = "no sidecar was up"
            return record
        index = emb_spawn_count
        record["spawn_index"] = index
        try:
            contact_id = "jitter:stop%d" % index
            meter.charge(contact_id)
            probe_started = time.time()
            probe = emb_client.embed_text(contact_id=contact_id, text=jitter_text)
            meter.record(
                contact_id,
                time.time() - probe_started,
                probe.dims,
                sha256_text(jitter_text),
            )
            record["jitter_bit_identical_to_first_spawn"] = (
                tuple(probe.values) == jitter_authority
            )
        except Exception as error:  # noqa: BLE001 -- teardown reports, never masks
            record["jitter_error"] = repr(error)
        try:
            closed = emb_client.close()
            record["client_contact_count"] = closed.get("contact_count")
        except Exception as error:  # noqa: BLE001
            record["client_close_error"] = repr(error)
        try:
            stop = stop_session(
                emb_session,
                runtime_receipt=emb_runtime_receipt,
                runtime_root=Path("/home/chao"),
                receipt_path=run_dir
                / ("session-qwen3-emb-cpu-%d.stop-receipt.json" % index),
                force_after_timeout=True,
            )
            record["termination_signal"] = stop.get("termination_signal")
            record["forced"] = stop.get("forced")
        except Exception as error:  # noqa: BLE001
            record["stop_error"] = repr(error)
            log("embedder sidecar #%d stop FAILED: %r" % (index, error))
        emb_client = None
        emb_session = None
        for _ in range(60):
            if not _port_reachable("127.0.0.1", EMB_PORT, timeout=0.5):
                break
            time.sleep(0.5)
        record["port_free"] = not _port_reachable("127.0.0.1", EMB_PORT, timeout=0.5)
        emb_stop_records.append(record)
        log(
            "embedder sidecar #%d stopped (%s, forced=%s, port free=%s) -- %s"
            % (
                index,
                record.get("termination_signal"),
                record.get("forced"),
                record.get("port_free"),
                reason,
            )
        )
        return record

    if with_sidecar:
        emb_report = run_encode_only_machine_check()
        log("encode-only structural sweep PASS: %r" % (list(emb_report.checked_modules),))
        embedder_path = root / EMBEDDER_RELPATH
        measured_embedder = sha256_file(embedder_path)
        if measured_embedder != EMBEDDER_SHA256:
            raise SystemExit("embedder GGUF hash mismatch vs the umbrella lock pin")
        committed_pre = load_runtime_receipt(REPO / "docs" / EMBEDDER_RUNTIME_RECEIPT_RELPATH)
        emb_runtime_receipt = {
            "llama_cpp": dict(committed_pre["llama_cpp"]),
            "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured_embedder}],
        }
        meter = EmbeddingMeter(attempt_tool_ceiling, run_dir / "embedding-contacts.jsonl")
        facet_repr_by_id = {
            facet.facet_id: facet.representation for facet in snapshot.facets
        }
        jitter_text = facet_repr_by_id[sorted(facet_vector_table)[0]]

        # ---- the ALREADY-DURABLE query-vector table (ZERO tool contacts) --
        #
        # NOTHING is embedded before takeoff and NO sidecar is spawned here.
        # Attempt 2's offline precompute already embedded all 104 landed M0
        # texts, and its own miss path live-embedded five divergent ones. An
        # embedding is a deterministic function of its text and every attempt-2
        # spawn proved bit-identical jitter numerics, so those vectors ARE the
        # vectors the bridge would recompute. They are loaded, hash-pinned, and
        # the offline bridge after Pass A embeds only what they do not cover.
        m0_texts, m0_integrity = load_m0_direct_texts(
            OUT_CHECK_DIR, [sample.sample_id for sample in samples]
        )
        log(
            "%d landed M0 direct-decode texts loaded and verified against their "
            "OWN per-sample direct_response_sha256 records (M0 report %s)"
            % (len(m0_texts), M0_ARM_REPORT_SHA256[:12])
        )
        durable_vector_provenance: dict[str, str] = {}
        attempt2_dir = root / "runs" / RUN_ID / ATTEMPT2_ID
        attempt2_precomputed = attempt2_dir / ATTEMPT2_PRECOMPUTED_RELNAME
        measured_attempt2 = sha256_file(attempt2_precomputed)
        if measured_attempt2 != ATTEMPT2_PRECOMPUTED_SHA256:
            raise SystemExit(
                "attempt-2 precomputed query vectors hash to %s, not the landed "
                "record %s; refusing to reuse unpinned vectors"
                % (measured_attempt2, ATTEMPT2_PRECOMPUTED_SHA256)
            )
        with attempt2_precomputed.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                key = str(record["text_sha256"])
                if len(record["values"]) != EMBEDDER_DIM:
                    raise SystemExit("durable vector %s has the wrong dimension" % key)
                precomputed_by_text_sha[key] = tuple(
                    float(v) for v in record["values"]
                )
                durable_vector_provenance[key] = "attempt2-offline-precompute"
        attempt2_landed = attempt2_dir / ATTEMPT2_LANDED_RELNAME
        attempt2_landed_sha = None
        if attempt2_landed.exists():
            attempt2_landed_sha = sha256_file(attempt2_landed)
            with attempt2_landed.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    key = str(record["text_sha256"])
                    if key in precomputed_by_text_sha:
                        continue
                    if len(record["values"]) != EMBEDDER_DIM:
                        raise SystemExit(
                            "durable vector %s has the wrong dimension" % key
                        )
                    precomputed_by_text_sha[key] = tuple(
                        float(v) for v in record["values"]
                    )
                    durable_vector_provenance[key] = "attempt2-live-embed"
        m0_text_shas = {sha256_text(text) for text in m0_texts.values()}
        m0_covered = sum(1 for key in m0_text_shas if key in precomputed_by_text_sha)
        flight["durable_query_vector_table"] = {
            "semantics": (
                "an embedding is a deterministic function of its text and every "
                "attempt-2 spawn proved bit-identical jitter numerics against the "
                "first spawn, so a vector already computed for a text on this row "
                "IS the vector the bridge would recompute. Reusing them is a "
                "serving cache and spends ZERO tool contacts. NOTHING is embedded "
                "before takeoff and no sidecar is spawned before Pass A."
            ),
            "attempt2_precomputed_sha256": measured_attempt2,
            "attempt2_landed_query_vectors_sha256": attempt2_landed_sha,
            "distinct_vectors_loaded": len(precomputed_by_text_sha),
            "m0_landed_texts": len(m0_texts),
            "m0_distinct_text_shas": len(m0_text_shas),
            "m0_text_shas_covered": m0_covered,
            "tool_contacts_spent_here": 0,
            "m0_source": m0_integrity,
        }
        save_flight()
        log(
            "durable query-vector table loaded: %d distinct vectors, %d of %d "
            "distinct M0 text hashes covered, ZERO tool contacts, sidecar NOT "
            "spawned" % (len(precomputed_by_text_sha), m0_covered, len(m0_text_shas))
        )
        log(
            "FIX 3 (cold start) is DROPPED as a remedy: attempt 2 entered its "
            "canary genuinely cold at 10.18 W / 43 C / 0 percent and stalled "
            "anyway, so the hypothesis is dead. Host state stays recorded in the "
            "preflight and in the phase-tagged clock samples."
        )

    def embed_query_text(sample_id: str, text: str) -> tuple[float, ...]:
        """FIX 2 at flight time: hash the FLOWN contact-0 text and look it up.
        A hit returns the offline embedding of the byte-identical text; a miss
        lazily re-spawns the sidecar and embeds live, fail-closed."""

        contact_id = "query:%s" % sample_id
        key = sha256_text(text)
        with embed_lock:
            precomputed = precomputed_by_text_sha.get(key)
            if precomputed is not None:
                lookup_stats["hits"] = int(lookup_stats["hits"]) + 1
                source = "precomputed"
                values = precomputed
                dims = len(values)
            else:
                lookup_stats["misses"] = int(lookup_stats["misses"]) + 1
                lookup_stats["miss_sample_ids"].append(sample_id)  # type: ignore[union-attr]
                source = "live"
                if emb_client is None:
                    log(
                        "query-vector cache MISS on %s: the flown contact-0 text "
                        "diverges from the landed M0 text; re-spawning the sidecar"
                        % sample_id
                    )
                    _spawn_sidecar("cache miss on %s" % sample_id)
                meter.charge(contact_id)
                started = time.time()
                vector = emb_client.embed_text(contact_id=contact_id, text=text)
                meter.record(contact_id, time.time() - started, vector.dims, key)
                values = tuple(vector.values)
                dims = vector.dims
            with query_vector_log.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "contact_id": contact_id,
                            "text_sha256": key,
                            "dims": dims,
                            "source": source,
                            "values": list(values),
                        }
                    )
                    + "\n"
                )
            return tuple(values)

    # ---- serving telemetry (NOT_AVAILABLE-tolerant; Windows-side binary) --
    sampler = resolve_resource_sampler(
        binary="/mnt/c/Windows/System32/nvidia-smi.exe",
        interval_seconds=5.0,
        slots_url="http://127.0.0.1:%d/slots" % DECODER_PORT,
    )
    sampler.start()
    sampler.begin_request_window()

    main_summary = None
    pass_a_summary = None
    controllers_by_sample: dict[str, object] = {}
    outcome_status = "ABORTED"
    contact_total = 0
    canary_fail_message: str | None = None
    sentinel_trip_message: str | None = None
    coresidency_message: str | None = None
    main_sentinel: DecodeRateSentinel | None = None
    main_buffer: TraceBuffer | None = None
    pass_a_buffer: TraceBuffer | None = None
    pass_a_sink: TraceSink | None = None
    micro_run_sink_ids: dict[str, frozenset] = {}
    main_sink_ids: frozenset = frozenset()
    canary_record: dict[str, object] = {}
    first_run_sha: dict[str, str] = {}
    pass_a_texts: dict[str, str] = {}
    pass_a_digests: dict[str, str] = {}
    replay_client: "ReplayDirectClient | None" = None
    flight_started = time.time()
    metered_client = CoreCeilingClient(client, attempt_core_ceiling)
    coresidency_guard = SidecarCoResidencyGuard(
        EMB_PORT, lambda: emb_client is not None
    )
    metered_client.arm_coresidency_guard(coresidency_guard)
    server_log_path = SESSION_DIR / "server.log"
    canary_log_offset = 0
    main_log_offset = 0
    resend_log_offset = 0
    resend_record: dict[str, object] = {"flown": False, "reason": "not a BLEND-arm rail"}

    def flush_partial_main() -> None:
        """Durable-first discipline on an abort path, for BOTH passes.

        Pass A's records go to their own namespaced sink and Pass B's to the
        main sink, so an abort in either window still lands everything durable
        that window produced."""

        nonlocal main_sink_ids, pass_a_buffer
        if pass_a_buffer is not None and pass_a_buffer.records and pass_a_sink is not None:
            partial_a = [record_id for _, record_id, _ in pass_a_buffer.records]
            try:
                namespaced = flush_micro_run_buffer(pass_a_buffer, pass_a_sink, "pass-a")
                micro_run_sink_ids["pass_a"] = frozenset(
                    micro_run_sink_ids.get("pass_a", frozenset())
                ) | frozenset(namespaced)
                flight["pass_a_partial_flush"] = {
                    "flushed_records": len(namespaced),
                    "manifest_hash": pass_a_sink.close(),
                }
                log(
                    "durable-first: %d partial PASS A trace records flushed into the "
                    "pass-a sink and its manifest closed" % len(namespaced)
                )
            except Exception as flush_error:  # noqa: BLE001 -- report, never mask
                flight["pass_a_partial_flush"] = {
                    "error": repr(flush_error),
                    "records_at_risk": len(partial_a),
                }
                log("durable-first PASS A partial flush FAILED: %r" % (flush_error,))
        if main_buffer is None or not main_buffer.records:
            return
        partial_ids = [record_id for _, record_id, _ in main_buffer.records]
        try:
            client.flush_trace_buffer(main_buffer)
            main_sink_ids = main_sink_ids | frozenset(partial_ids)
            flight["main_partial_flush"] = {"flushed_records": len(partial_ids)}
            log(
                "durable-first: %d partial PASS B trace records flushed into the "
                "main sink" % len(partial_ids)
            )
        except Exception as flush_error:  # noqa: BLE001 -- report, never mask
            flight["main_partial_flush"] = {"error": repr(flush_error)}
            log("durable-first partial flush FAILED: %r" % (flush_error,))

    try:
        def m0_factory(sample_id: str):
            return KbAlphaBlendController(
                snapshot=None,
                query_vectors={},
                facet_vectors=lambda facet_id: {},
                normalizer=a2t_primary_tool_normalizer,
                ranker=rank_wcos_prior_agree_factory(
                    RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)
                ),
                fuser=fuse_supplyfilter_factory(FuseKnobs(tau=1.0, m=1, c=1, top_l=1)),
                alpha=0.5,
                top_k_per_dimension=1,
            )

        # ---------------- Decode-speed CANARY (before the main loop) -------
        canary_log_offset = server_log_path.stat().st_size
        canary_registry = Registry("a2t g1 %s canary controller" % slug)
        canary_registry.register(M0_POLICY_ID, m0_factory)
        canary_buffer = TraceBuffer(plan.run_id)
        log(
            "CANARY START: %d single-slot direct-decode contacts on %r (timing only; "
            "PASS < %.0f ms/token GENERATION RATE -- the gate is the per-token rate, "
            "not wall time, and at max_tokens 1024 a healthy decode runs long)"
            % (len(canary_samples), canary_ids, CANARY_MS_PER_TOKEN_PASS)
        )
        clock_sampler.set_phase("canary")
        coresidency_guard.arm("canary")
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
        first_run_sha = {
            result.sample_id: sha256_text(result.final_response_text)
            for result in canary_summary.results
        }
        canary_record = {
            "sample_ids": canary_ids,
            "contacts": canary_contacts,
            "wall_seconds": round(canary_wall, 3),
            "pass_threshold_ms_per_token": CANARY_MS_PER_TOKEN_PASS,
            "gate_semantics": (
                "PER-TOKEN generation rate, never wall time: the derived output "
                "ceiling is 1,024 tokens, so a healthy A2T canary decode legitimately "
                "runs far longer than a 64-token SLURP canary"
            ),
            "generation": generation_rows,
            "prompt_eval": canary_timing["prompt_eval"],
            "response_sha256": dict(sorted(first_run_sha.items())),
            "hash_authority": (
                "ESTABLISHED BY THIS CAMPAIGN. No prior A2T flight ran this geometry, "
                "so the M0 arm records these hashes and the BLEND arm compares against "
                "them; there is nothing older to inherit."
            ),
            "note": (
                "responses never read semantically: sha256 + server print_timing "
                "descriptives only"
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
                "canary timing lines incomplete: %d generation rows for %d contacts; "
                "refusing to fly the main loop without a decode-speed verdict"
                % (len(generation_rows), canary_contacts)
            )
        worst_rate = max(row["ms_per_token"] for row in generation_rows)
        canary_record["worst_generation_ms_per_token"] = worst_rate
        canary_record["passed"] = worst_rate < CANARY_MS_PER_TOKEN_PASS
        save_flight()
        if not canary_record["passed"]:
            raise CanaryFail(
                "decode-speed canary FAILED: generation rates %r ms/token vs the "
                "registered pass threshold %.0f; the main loop is NOT flown; the "
                "service is left up"
                % ([row["ms_per_token"] for row in generation_rows], CANARY_MS_PER_TOKEN_PASS)
            )
        log(
            "CANARY PASS: generation %r ms/token (worst %s)"
            % ([row["ms_per_token"] for row in generation_rows], worst_rate)
        )

        if arm_id == "M0":
            CANARY_AUTHORITY_PATH.parent.mkdir(parents=True, exist_ok=True)
            CANARY_AUTHORITY_PATH.write_text(
                json.dumps(
                    {
                        "schema": "saea-a2t-g1-canary-authority-v1",
                        "study": "speech-aware-evidence-acquisition",
                        "run_id": RUN_ID,
                        "arm_id": arm_id,
                        "attempt_id": attempt_id,
                        "generated_at": iso_now(),
                        "sample_ids": canary_ids,
                        "response_sha256": dict(sorted(first_run_sha.items())),
                        "decoding_params": dict(DECODING_PARAMS),
                        "server_np": server_np,
                        "session_receipt_sha256": measured_session,
                        "note": (
                            "this campaign's OWN canary hash authority. No prior "
                            "Audio2Tool flight ran the section 8.1 derived geometry, "
                            "so nothing older can be inherited."
                        ),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            log("canary hash authority ESTABLISHED: %s" % CANARY_AUTHORITY_PATH)
            canary_record["authority_written"] = str(CANARY_AUTHORITY_PATH)
        else:
            agreed = {
                sample_id: first_run_sha[sample_id] == canary_authority.get(sample_id)
                for sample_id in canary_ids
            }
            canary_record["byte_identical_to_m0_authority"] = agreed
            canary_record["all_byte_identical_to_m0_authority"] = all(agreed.values())
            if all(agreed.values()):
                log("canary bytes MATCH the M0 arm's authority (within-campaign continuity)")
            else:
                log(
                    "canary bytes DIFFER from the M0 authority (UNEXPECTED at "
                    "temperature 0 on one build): re-running the pair once -- "
                    "within-build determinism is REQUIRED"
                )
                rerun_buffer = TraceBuffer(plan.run_id)
                rerun_registry = Registry("a2t g1 %s canary rerun controller" % slug)
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
                rerun_record_ids = flush_micro_run_buffer(
                    rerun_buffer, rerun_sink, "canary-rerun"
                )
                rerun_manifest_hash = rerun_sink.close()
                micro_run_sink_ids["canary_rerun"] = frozenset(rerun_record_ids)
                rerun_contacts = sum(len(r.contacts) for r in rerun_summary.results)
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
                    "m0_authority_response_sha256": dict(sorted(canary_authority.items())),
                    "flown_response_sha256": dict(sorted(first_run_sha.items())),
                    "note": "recorded as a caveat traveling with the arm report",
                }
                save_flight()
                if len(rerun_rows) != rerun_contacts:
                    raise CanaryFail(
                        "canary re-run timing lines incomplete: %d rows for %d contacts"
                        % (len(rerun_rows), rerun_contacts)
                    )
                rerun_worst = max(row["ms_per_token"] for row in rerun_rows)
                if rerun_worst >= CANARY_MS_PER_TOKEN_PASS:
                    raise CanaryFail(
                        "canary re-run FAILED the timing gate: worst %s ms/token"
                        % rerun_worst
                    )
                if not within_build_identical:
                    raise CanaryFail(
                        "WITHIN-build determinism FAILED: canary re-run responses are "
                        "not byte-identical to the first run on the SAME binary; "
                        "stopping fail-closed before the main loop"
                    )
                log("canary re-run PASS: within-build determinism confirmed; caveat recorded")
        save_flight()

        # ================= PASS A: 104 direct decodes, sidecar DOWN =========
        #
        # Pass A flies the BLEND arm's OWN contact 0 through the DEGENERATE
        # direct-decode-only controller (snapshot=None), whose initial_contact is
        # byte-identical to the blend controller's. It records each trajectory's
        # flown text and the sha256 of the messages document that produced it,
        # and it NEVER runs the policy: an inert query vector would change what
        # the policy reads, so the decision is DEFERRED to Pass B, never omitted.
        main_registry = Registry("a2t g1 %s pass B controller" % slug)
        pass_a_registry = Registry("a2t g1 %s pass A controller" % slug)
        pass_a_controllers: dict[str, object] = {}

        def pass_a_factory(sample_id: str):
            controller = m0_factory(sample_id)
            pass_a_controllers[sample_id] = controller
            return controller

        pass_a_registry.register(M0_POLICY_ID, pass_a_factory)
        main_log_offset = server_log_path.stat().st_size
        main_sentinel = DecodeRateSentinel(server_log_path, main_log_offset)
        metered_client.arm_sentinel(main_sentinel)
        coresidency_guard.arm("pass-a")
        clock_sampler.set_phase("pass-a")
        log(
            "PASS A START (%d samples x 1 direct contact, sidecar DOWN, "
            "co-residency guard ARMED): <= %d core contacts (hard meter); sentinel "
            "ARMED (rolling median over %d > %.0f ms/token aborts)"
            % (
                len(samples),
                attempt_core_ceiling,
                SENTINEL_WINDOW_CONTACTS,
                SENTINEL_MEDIAN_MS_PER_TOKEN_ABORT,
            )
        )
        pass_a_buffer = TraceBuffer(plan.run_id)
        pass_a_sink = TraceSink(run_dir / "pass-a-trace", plan.run_id)
        pass_a_started = time.time()
        pass_a_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=metered_client,
            split_id=split_id,
            knowledge_snapshot=snapshot,
            speech_packet_bindings={
                sample.sample_id: packet_bindings[sample.sample_id] for sample in samples
            },
            controller_policy_id=M0_POLICY_ID,
            max_contacts=1,
            slot_count=server_np,
            queue_depth=server_np,
            trace_sink=pass_a_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=pass_a_registry,
        )
        pass_a_contacts = sum(len(result.contacts) for result in pass_a_summary.results)
        contact_total += pass_a_contacts
        flight["core_contacts_total_pre_flush"] = contact_total
        save_flight()
        pass_a_record_ids = flush_micro_run_buffer(pass_a_buffer, pass_a_sink, "pass-a")
        pass_a_manifest_hash = pass_a_sink.close()
        micro_run_sink_ids["pass_a"] = frozenset(pass_a_record_ids)
        pass_a_buffer = None
        pass_a_texts = {
            result.sample_id: result.final_response_text
            for result in pass_a_summary.results
        }
        if set(pass_a_texts) != {sample.sample_id for sample in samples}:
            raise SystemExit("PASS A did not cover the arm split exactly")
        missing_digests = [
            sample_id
            for sample_id in pass_a_texts
            if (_DIRECT_CONTACT_ID, sample_id) not in metered_client.message_digests
        ]
        if missing_digests:
            raise SystemExit(
                "PASS A recorded no messages digest for %d samples (%r); Pass B "
                "cannot prove its replay is the flown contact"
                % (len(missing_digests), missing_digests[:5])
            )
        pass_a_digests = {
            sample_id: metered_client.message_digests[(_DIRECT_CONTACT_ID, sample_id)]
            for sample_id in pass_a_texts
        }
        pass_a_outputs_path = run_dir / "pass-a-direct-outputs.jsonl"
        with pass_a_outputs_path.open("w", encoding="utf-8", newline="\n") as sink:
            for sample_id in sorted(pass_a_texts):
                sink.write(
                    json.dumps(
                        {
                            "sample_id": sample_id,
                            "pass": "A",
                            "direct_response_text": pass_a_texts[sample_id],
                            "direct_response_sha256": sha256_text(
                                pass_a_texts[sample_id]
                            ),
                            "messages_sha256": pass_a_digests[sample_id],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        pass_a_vs_m0 = {
            sample_id: sha256_text(pass_a_texts[sample_id])
            == sha256_text(m0_texts[sample_id])
            for sample_id in sorted(pass_a_texts)
        }
        flight["pass_a"] = {
            "design": (
                "the BLEND arm's OWN contact 0, flown with the embedder sidecar DOWN "
                "through the degenerate direct-decode-only controller whose "
                "initial_contact is byte-identical to the blend controller's. The "
                "policy is NOT run here: an inert query vector would change what the "
                "policy reads, so the decision is DEFERRED to Pass B, never omitted"
            ),
            "samples": len(pass_a_texts),
            "core_contacts": pass_a_contacts,
            "wall_seconds": round(time.time() - pass_a_started, 1),
            "outputs": str(pass_a_outputs_path),
            "outputs_sha256": sha256_file(pass_a_outputs_path),
            "byte_identical_to_landed_m0_text": sum(
                1 for agreed in pass_a_vs_m0.values() if agreed
            ),
            "divergent_from_landed_m0_text": sorted(
                sample_id for sample_id, agreed in pass_a_vs_m0.items() if not agreed
            ),
            "trace": {
                "sink_dir": str(run_dir / "pass-a-trace"),
                "record_ids": len(pass_a_record_ids),
                "namespace": "pass-a/",
                "manifest_hash": pass_a_manifest_hash,
            },
        }
        save_flight()
        log(
            "PASS A DONE in %.1fs: %d contacts, %d/%d texts byte-identical to the "
            "landed M0 text, %d divergent"
            % (
                time.time() - pass_a_started,
                pass_a_contacts,
                sum(1 for a in pass_a_vs_m0.values() if a),
                len(pass_a_vs_m0),
                sum(1 for a in pass_a_vs_m0.values() if not a),
            )
        )

        # ================= OFFLINE BRIDGE: sidecar UP ALONE =================
        #
        # The GPU decode loop is stopped. Only now may the sidecar exist, and it
        # is stopped again with its own receipt before Pass B is allowed to
        # start -- verified by BOTH the port probe and a VRAM return check, not
        # by assumption. This is the whole point of the redesign.
        metered_client.arm_sentinel(None)
        coresidency_guard.disarm("offline-bridge")
        clock_sampler.set_phase("offline-bridge")
        bridge_started = time.time()
        bridge_needed = sorted(
            {
                sha256_text(text)
                for text in pass_a_texts.values()
                if sha256_text(text) not in precomputed_by_text_sha
            }
        )
        text_by_sha = {sha256_text(text): text for text in pass_a_texts.values()}
        bridge_vram_before = clock_sampler.sample_once()
        bridge_spawn_stop: dict[str, object] | None = None
        if bridge_needed:
            log(
                "OFFLINE BRIDGE: %d Pass-A texts are not covered by the durable "
                "table; spawning the sidecar ALONE to embed them in ONE session"
                % len(bridge_needed)
            )
            _spawn_sidecar("offline bridge between Pass A and Pass B")
            bridge_path = run_dir / "query-vectors-bridge.jsonl"
            with bridge_path.open("w", encoding="utf-8", newline="\n") as handle:
                for key in bridge_needed:
                    contact_id = "bridge:%s" % key[:16]
                    with embed_lock:
                        meter.charge(contact_id)
                        started = time.time()
                        vector = emb_client.embed_text(
                            contact_id=contact_id, text=text_by_sha[key]
                        )
                        meter.record(contact_id, time.time() - started, vector.dims, key)
                    precomputed_by_text_sha[key] = tuple(vector.values)
                    durable_vector_provenance[key] = "attempt3-bridge"
                    handle.write(
                        json.dumps(
                            {
                                "contact_id": contact_id,
                                "text_sha256": key,
                                "dims": vector.dims,
                                "values": list(vector.values),
                            }
                        )
                        + "\n"
                    )
            bridge_spawn_stop = _stop_sidecar(
                "offline bridge complete -- Pass B flies with the sidecar DOWN"
            )
            bridge_sha = sha256_file(bridge_path)
        else:
            bridge_path = None
            bridge_sha = None
            log(
                "OFFLINE BRIDGE: every Pass-A text is already covered by the durable "
                "vector table; the sidecar is NOT spawned at all and zero tool "
                "contacts are spent"
            )
        uncovered = [
            sample_id
            for sample_id, text in pass_a_texts.items()
            if sha256_text(text) not in precomputed_by_text_sha
        ]
        if uncovered:
            raise SystemExit(
                "OFFLINE BRIDGE FAILED to cover %d Pass-A texts (%r); Pass B would "
                "have to read a vector for a text that never flew, and deferral -- "
                "not substitution -- is the only legitimate shape"
                % (len(uncovered), uncovered[:5])
            )

        # ---- the sidecar is DOWN and VRAM has returned, both PROVED --------
        vram_deadline = time.time() + VRAM_RETURN_TIMEOUT_SECONDS
        bridge_vram_after = clock_sampler.sample_once()
        while time.time() < vram_deadline:
            used = (bridge_vram_after or {}).get("memory.used")
            if isinstance(used, (int, float)) and used <= VRAM_NO_SIDECAR_CEILING_MIB:
                break
            time.sleep(3.0)
            bridge_vram_after = clock_sampler.sample_once()
        vram_used_after = (bridge_vram_after or {}).get("memory.used")
        vram_returned = isinstance(vram_used_after, (int, float)) and (
            vram_used_after <= VRAM_NO_SIDECAR_CEILING_MIB
        )
        port_free = not _port_reachable("127.0.0.1", EMB_PORT, timeout=0.5)
        flight["offline_bridge"] = {
            "design": (
                "the ONE window in which the sidecar may exist: the GPU decode loop "
                "is stopped, the sidecar is spawned ALONE, every Pass-A text not "
                "already covered by the durable table is embedded in one batched "
                "session, and the sidecar is stopped with its own receipt before "
                "Pass B is allowed to start"
            ),
            "pass_a_texts": len(pass_a_texts),
            "distinct_pass_a_text_shas": len(text_by_sha),
            "already_covered_by_durable_table": len(text_by_sha) - len(bridge_needed),
            "embedded_here": len(bridge_needed),
            "expected_hit_rate": PRECOMPUTE_EXPECTED_HIT_RATE,
            "measured_coverage_rate": (
                round((len(text_by_sha) - len(bridge_needed)) / len(text_by_sha), 6)
                if text_by_sha
                else None
            ),
            "sidecar_spawned": bool(bridge_needed),
            "sidecar_stop": bridge_spawn_stop,
            "bridge_vectors_path": str(bridge_path) if bridge_path else None,
            "bridge_vectors_sha256": bridge_sha,
            "seconds": round(time.time() - bridge_started, 2),
            "tool_contacts_after_bridge": meter.count if meter is not None else 0,
            "vram_before_mib": (bridge_vram_before or {}).get("memory.used"),
            "vram_after_mib": vram_used_after,
            "vram_no_sidecar_ceiling_mib": VRAM_NO_SIDECAR_CEILING_MIB,
            "vram_returned_to_baseline": vram_returned,
            "embedder_port_free": port_free,
            "coverage_complete": True,
        }
        save_flight()
        log(
            "OFFLINE BRIDGE DONE in %.1fs: %d embedded, sidecar %s, port free=%s, "
            "VRAM %s MiB (ceiling %s), returned=%s"
            % (
                time.time() - bridge_started,
                len(bridge_needed),
                "spawned and stopped" if bridge_needed else "never spawned",
                port_free,
                vram_used_after,
                VRAM_NO_SIDECAR_CEILING_MIB,
                vram_returned,
            )
        )
        if not port_free:
            raise CoResidencyViolation(
                "the embedder port is still reachable after the offline bridge; "
                "refusing to start Pass B into the exact condition that stalled "
                "attempts 1 and 2"
            )
        if not vram_returned:
            raise CoResidencyViolation(
                "VRAM did not return to the no-sidecar baseline after the offline "
                "bridge (%s MiB against a %s MiB ceiling) within %.0f s; refusing to "
                "start Pass B"
                % (
                    vram_used_after,
                    VRAM_NO_SIDECAR_CEILING_MIB,
                    VRAM_RETURN_TIMEOUT_SECONDS,
                )
            )

        # ================= PASS B: the policy decides, sidecar DOWN =========
        #
        # The REAL frozen v1 blend controller now runs over the vector of THAT
        # trajectory's OWN flown Pass-A text. Contact 0 is RESUMED from Pass A's
        # durable record through ReplayDirectClient, which proves the messages
        # digest matches before returning a byte; the evidence contact, wherever
        # the policy dispatches, is a real metered frozen-core contact.
        cells = {sample.sample_id: LazyQueryVector() for sample in samples}

        def bridge_lookup(sample_id: str, text: str) -> tuple[float, ...]:
            """Pass B's embedding callback is a PURE TABLE LOOKUP that cannot
            spawn anything. Every Pass-A text is covered by construction, and a
            miss raises rather than substituting a vector for a text that did
            not fly."""

            contact_id = "query:%s" % sample_id
            key = sha256_text(text)
            with embed_lock:
                values = precomputed_by_text_sha.get(key)
                if values is None:
                    lookup_stats["misses"] = int(lookup_stats["misses"]) + 1
                    lookup_stats["miss_sample_ids"].append(sample_id)  # type: ignore[union-attr]
                    raise RuntimeError(
                        "PASS B: no vector for the flown text of %s. The offline "
                        "bridge is the only place an embedding may happen and it "
                        "reported full coverage; refusing to embed inside the GPU "
                        "loop" % sample_id
                    )
                lookup_stats["hits"] = int(lookup_stats["hits"]) + 1
                with query_vector_log.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            {
                                "contact_id": contact_id,
                                "text_sha256": key,
                                "dims": len(values),
                                "source": durable_vector_provenance.get(key, "unknown"),
                                "values": list(values),
                            }
                        )
                        + "\n"
                    )
                return values

        def kb_factory(sample_id: str):
            per_sample = make_kb_alpha_blend_controller_factory(
                snapshot=snapshot,
                query_vectors_by_sample={sample_id: {"content": cells[sample_id]}},
                facet_vectors=lambda facet_id: facet_vector_table.get(facet_id, {}),
                normalizer=a2t_primary_tool_normalizer,
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
                embed=bridge_lookup,
            )
            controllers_by_sample[sample_id] = controller
            return controller

        controller_policy_id = CONTROLLER_POLICY_ID
        main_registry.register(CONTROLLER_POLICY_ID, main_factory)
        log(
            "PASS B controller = the FROZEN v1 CELL, BYTE-IDENTICAL (alpha=%s, "
            "tau=%s, top_k=%s, fusion m=%s/c=%s/l=%s, rrf %s/%s/%s, TRAIN priors, "
            "facet-side admission, f1060078 repair live) over the A2T tool-shaped "
            "knowledge base with the A2T primary-tool normalizer"
            % (
                FROZEN_ALPHA,
                FROZEN_TAU,
                FROZEN_TOP_K,
                FROZEN_FUSE.m,
                FROZEN_FUSE.c,
                FROZEN_FUSE.top_l,
                FROZEN_WEIGHTS.w_cos,
                FROZEN_WEIGHTS.w_prior,
                FROZEN_WEIGHTS.w_agree,
            )
        )
        replay_client = ReplayDirectClient(
            metered_client,
            texts_by_sample=pass_a_texts,
            digests_by_sample=pass_a_digests,
            log_path=run_dir / "pass-b-replay.jsonl",
        )
        coresidency_guard.arm("pass-b")
        metered_client.arm_sentinel(main_sentinel)
        clock_sampler.set_phase("pass-b")
        log(
            "PASS B START (%d trajectories, contact 0 RESUMED from Pass A at zero "
            "core contacts, evidence contacts real and metered; registered Pass-B "
            "ceiling %d against a projection of %d): sentinel ARMED, co-residency "
            "guard ARMED"
            % (
                len(samples),
                PASS_B_CONTACT_CEILING,
                DISPATCH_PROJECTION_COUNT,
            )
        )
        main_buffer = TraceBuffer(plan.run_id)
        main_started = time.time()
        main_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=replay_client,
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
        pass_b_evidence_contacts = replay_client.passed_through
        contact_total += pass_b_evidence_contacts
        main_contacts = sum(len(result.contacts) for result in main_summary.results)
        main_record_ids = [record_id for _, record_id, _ in main_buffer.records]
        flight["core_contacts_total_pre_flush"] = contact_total
        save_flight()
        client.flush_trace_buffer(main_buffer)
        main_sink_ids = frozenset(main_record_ids)
        main_buffer = None
        log(
            "PASS B flushed FIRST into the main sink: %d records" % len(main_record_ids)
        )
        if pass_b_evidence_contacts > PASS_B_CONTACT_CEILING:
            raise SystemExit(
                "PASS B spent %d evidence contacts against a registered ceiling of %d"
                % (pass_b_evidence_contacts, PASS_B_CONTACT_CEILING)
            )
        flight["pass_b"] = {
            "design": (
                "the REAL frozen v1 blend controller over the vector of THAT "
                "trajectory's OWN flown Pass-A text; contact 0 is RESUMED from Pass "
                "A's durable record and costs zero core contacts, the evidence "
                "contact wherever the policy dispatches is real and metered"
            ),
            "trajectories": len(main_summary.results),
            "trajectory_contacts_including_resumed": main_contacts,
            "evidence_contacts_flown": pass_b_evidence_contacts,
            "registered_pass_b_ceiling": PASS_B_CONTACT_CEILING,
            "dispatch_projection": DISPATCH_PROJECTION_COUNT,
            "replay": replay_client.summary(),
            "wall_seconds": round(time.time() - main_started, 1),
        }
        save_flight()
        log(
            "PASS B DONE in %.1fs: %d trajectory contacts, of which %d were REAL "
            "evidence contacts and %d were resumed from Pass A at zero cost"
            % (
                time.time() - main_started,
                main_contacts,
                pass_b_evidence_contacts,
                replay_client.replayed,
            )
        )
        time.sleep(1.0)
        with server_log_path.open("rb") as log_handle:
            log_handle.seek(main_log_offset)
            main_timing = parse_print_timing(log_handle.read())
        gen_rates = sorted(row["ms_per_token"] for row in main_timing["generation"])
        flight["main_print_timing"] = {
            "window": "PASS A + offline bridge + PASS B (the bridge writes no rows here)",
            "generation_rows": len(gen_rates),
            "ms_per_token_min": gen_rates[0] if gen_rates else None,
            "ms_per_token_median": gen_rates[len(gen_rates) // 2] if gen_rates else None,
            "ms_per_token_max": gen_rates[-1] if gen_rates else None,
        }
        save_flight()

        # ---------------- identical-prompt resend pair (BLEND arm only) ----
        clock_sampler.set_phase("resend")
        coresidency_guard.arm("resend")
        resend_log_offset = server_log_path.stat().st_size
        if with_resend:
            if contact_total + 1 <= attempt_core_ceiling:
                resend_sample = adapter.load_split(RESEND_SPLIT_ID)[0]
                resend_registry = Registry("a2t g1 %s resend controller" % slug)
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
                base_sha = (canary_authority or {}).get(resend_sample_id)
                resend_text = resend_summary.results[0].final_response_text
                resend_record = {
                    "flown": True,
                    "sample_id": resend_sample.sample_id,
                    "server_np": server_np,
                    "response_a_sha256": base_sha,
                    "response_a_source": (
                        "the M0 arm's landed canary hash authority for the same sample"
                    ),
                    "response_b_sha256": sha256_text(resend_text),
                    "byte_identical": base_sha == sha256_text(resend_text),
                    "note": (
                        "byte-identical direct-decode PROMPT by construction; response "
                        "A is the M0 arm's recorded hash, response B a fresh "
                        "single-slot decode on the SAME instance; sha256 equality only"
                    ),
                    "trace": {
                        "sink_dir": str(run_dir / "resend-trace"),
                        "record_ids": len(resend_record_ids),
                        "namespace": "resend/",
                        "manifest_hash": resend_manifest_hash,
                    },
                }
                log(
                    "resend pair (sample %s, -np %d): byte_identical=%s"
                    % (resend_sample.sample_id, server_np, resend_record["byte_identical"])
                )
            else:
                resend_record = {
                    "flown": False,
                    "reason": (
                        "attempt core ceiling %d fully consumed (%d contacts); resend "
                        "skipped and disclosed" % (attempt_core_ceiling, contact_total)
                    ),
                }
                log("resend SKIPPED: no core-contact headroom (disclosed)")
        flight["resend_pair"] = resend_record

        assert_zero_record_id_overlap({"main": main_sink_ids, **micro_run_sink_ids})
        flight["trace_isolation"] = {
            "main_sink_records": len(main_sink_ids),
            "canary_sink_records": len(micro_run_sink_ids.get("canary", frozenset())),
            "canary_rerun_sink_records": len(
                micro_run_sink_ids.get("canary_rerun", frozenset())
            ),
            "pass_a_sink_records": len(micro_run_sink_ids.get("pass_a", frozenset())),
            "resend_sink_records": len(micro_run_sink_ids.get("resend", frozenset())),
            "zero_record_id_overlap_asserted": True,
            "why_pass_a_is_namespaced": (
                "both passes emit an agent-loop runtime record per sample under the "
                "same record base, so Pass A flushes into its OWN namespaced sink and "
                "only Pass B -- the pass in which the policy actually decides -- lands "
                "in the main sink"
            ),
            "flush_order": (
                "canary (own sink) -> PASS A (own sink, flushed before the bridge) -> "
                "offline bridge (no decoder trace) -> PASS B (main sink FIRST) -> "
                "resend (own sink)"
            ),
        }
        log(
            "trace isolation verified: zero record-id overlap across main (%d) and "
            "micro-run sinks" % len(main_sink_ids)
        )
        outcome_status = "CONTACTS_COMPLETE"
    except CanaryFail as error:
        canary_fail_message = str(error)
        outcome_status = "CANARY_FAIL_STOP"
        log("CANARY FAIL: %s" % canary_fail_message)
    except CoResidencyViolation as error:
        coresidency_message = str(error)
        outcome_status = "CORESIDENCY_VIOLATION_STOP"
        log("CO-RESIDENCY VIOLATION: %s" % coresidency_message)
        flush_partial_main()
    except DecodeRateSentinelTrip as error:
        sentinel_trip_message = str(error)
        outcome_status = "SENTINEL_ABORT_STOP"
        log("SENTINEL TRIP: %s" % sentinel_trip_message)
        flush_partial_main()
    except Exception as error:
        if main_sentinel is not None and main_sentinel.tripped is not None:
            sentinel_trip_message = "%r (surfaced wrapped as: %r)" % (
                main_sentinel.tripped,
                error,
            )
            outcome_status = "SENTINEL_ABORT_STOP"
            log("SENTINEL TRIP (wrapped): %s" % sentinel_trip_message)
            flush_partial_main()
        else:
            flush_partial_main()
            raise
    finally:
        coresidency_guard.disarm("teardown")
        clock_sampler.set_phase("teardown")
        sampler.end_request_window()
        sampler.stop()
        flight["serving_descriptives"] = dict(sampler.summary())
        flight["core_contacts_total"] = contact_total
        flight["sentinel"] = main_sentinel.summary() if main_sentinel is not None else None
        flight["outcome_status"] = outcome_status
        save_flight()

        if with_sidecar and meter is not None:
            if emb_client is not None:
                _stop_sidecar("arm teardown")
            hits = int(lookup_stats["hits"])
            misses = int(lookup_stats["misses"])
            looked_up = hits + misses
            flight["query_vector_lookup"] = {
                "hits": hits,
                "misses": misses,
                "lookups": looked_up,
                "hit_rate": round(hits / looked_up, 6) if looked_up else None,
                "expected_hit_rate": PRECOMPUTE_EXPECTED_HIT_RATE,
                "miss_sample_ids": list(lookup_stats["miss_sample_ids"]),  # type: ignore[arg-type]
                "in_loop_tool_contacts_avoided": hits,
                "semantics": (
                    "in the two-pass design every lookup is a HIT by construction: "
                    "the offline bridge covers every Pass-A text before Pass B starts "
                    "and Pass B's callback is a pure table lookup. A MISS here would "
                    "mean the bridge's coverage assertion was wrong, and it raises "
                    "rather than embedding inside the GPU loop"
                ),
            }
            flight["embedding_sidecar_lifecycle"] = {
                "spawns": emb_spawn_records,
                "stops": emb_stop_records,
                "spawn_count": emb_spawn_count,
                "jitter_text_sha256": sha256_text(jitter_text) if jitter_text else None,
                "cross_spawn_numerics": (
                    "every spawn and stop embeds the SAME jitter text and compares "
                    "bit-for-bit against the first spawn, so live-embedded misses are "
                    "provably in the same numeric space as the precomputed vectors"
                ),
            }
            flight["embedding_accounting"] = {
                "tool_contacts": meter.count,
                "ceiling": attempt_tool_ceiling,
                "latency_seconds_total": round(meter.latency_total, 3),
                "bridge_contacts": int(
                    (flight.get("offline_bridge") or {}).get("embedded_here", 0)
                ),
                "in_loop_live_query_contacts": 0,
                "in_loop_embedding_is_structurally_impossible": (
                    "Pass B's embedding callback is a pure table lookup that raises "
                    "rather than spawning anything; the offline bridge is the only "
                    "place an embedding may happen"
                ),
                "durable_vectors_reused_at_zero_cost": int(
                    (flight.get("offline_bridge") or {}).get(
                        "already_covered_by_durable_table", 0
                    )
                ),
                "jitter_contacts": 2 * emb_spawn_count,
            }
        else:
            flight["embedding_accounting"] = {
                "tool_contacts": 0,
                "ceiling": attempt_tool_ceiling,
            }
        clock_sampler.stop()
        flight["gpu_clock_throttle_telemetry"] = clock_sampler.summary()
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
        "core client closed: %d requests, contact latency %.1fs, wall %ss"
        % (len(timings), contact_latency_total, flight["wall_seconds"])
    )

    tool_contacts_used = meter.count if meter is not None else 0
    cost = flight["core_client"]["cost"]
    audio_seconds_metered = cost.get("audio_seconds_used") if isinstance(cost, Mapping) else None

    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)

    # ---- canary-fail / sentinel-trip hard stops (no scoring, no gold) -----
    if (
        canary_fail_message is not None
        or sentinel_trip_message is not None
        or coresidency_message is not None
    ):
        if canary_fail_message is not None:
            stop_kind = "canary-stop"
        elif coresidency_message is not None:
            stop_kind = "coresidency-stop"
        else:
            stop_kind = "sentinel-abort"
        stop_record = {
            "schema": "saea-a2t-g1-%s-%s-v1" % (report_stub, stop_kind),
            "study": "speech-aware-evidence-acquisition",
            "run_id": RUN_ID,
            "arm_id": arm_id,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "outcome": outcome_status,
            "verbatim": (
                canary_fail_message or coresidency_message or sentinel_trip_message
            ),
            "canary": flight.get("canary"),
            "sentinel": flight.get("sentinel"),
            "gpu_clock_throttle_telemetry": flight.get("gpu_clock_throttle_telemetry"),
            "pass_a": flight.get("pass_a"),
            "offline_bridge": flight.get("offline_bridge"),
            "pass_b": flight.get("pass_b"),
            "coresidency_invariant": coresidency_guard.summary()
            if coresidency_message is None
            else {"held": False, "violation": coresidency_message},
            "durable_query_vector_table": flight.get("durable_query_vector_table"),
            "dispatch_projection": flight.get("dispatch_projection"),
            "query_vector_lookup": flight.get("query_vector_lookup"),
            "embedding_sidecar_lifecycle": flight.get("embedding_sidecar_lifecycle"),
            "serving_descriptives": flight.get("serving_descriptives"),
            "mid_flight_clock_samples_windows_side": read_clock_samples(root, slug),
            "durable_flush": {
                "canary_sink": flight.get("canary", {}).get("trace")
                if isinstance(flight.get("canary"), dict)
                else None,
                "pass_a_sink": flight.get("pass_a", {}).get("trace")
                if isinstance(flight.get("pass_a"), dict)
                else None,
                "pass_a_partial_flush": flight.get("pass_a_partial_flush"),
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
                "the resident service and its unit are left up. A sentinel trip STOPS "
                "THE MISSION -- no later arm flies on a sick GPU."
            ),
        }
        stop_path = OUT_CHECK_DIR / ("%s-%s-attempt3.json" % (report_stub, stop_kind))
        stop_path.write_text(
            json.dumps(stop_record, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        flight["stop_record_path"] = str(stop_path)
        save_flight()
        log("STOP RECORD written: %s" % stop_path)
        log("VERBATIM: %s" % stop_record["verbatim"])
        if canary_fail_message is not None:
            return 4
        return 6 if coresidency_message is not None else 5

    # ---- MECHANICAL landing: gold-free per-sample records + arm report ----
    mech_rows: dict[str, dict[str, object]] = {}
    for result in main_summary.results:
        controller = controllers_by_sample.get(result.sample_id)
        direct_label = (
            getattr(controller, "direct_label_recovered", None)
            if max_contacts > 1
            else getattr(controller, "_direct_label", None)
        )
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
            "direct_label_recovered": direct_label is not None if controller is not None else None,
            "direct_label_facet_id": direct_label,
            "direct_tool_multiset": (
                list(getattr(controller, "direct_tool_multiset", None) or [])
                if max_contacts > 1
                else list(tool_name_multiset(result.final_response_text) or [])
            ),
            "winner_label_present": (
                getattr(controller, "last_winner_label", None) is not None
                if controller is not None
                else None
            ),
            "fusion_selected_value_ids": (
                getattr(controller, "fusion_selected_value_ids", None)
                if controller is not None
                else None
            ),
        }
    if {s.sample_id for s in samples} != set(mech_rows):
        raise SystemExit("main-loop results do not cover the arm split exactly")

    # ---- branch-only replay proof (BLEND arm; launcher-side pure functions)
    replay_mismatches: list[str] = []
    replay_checked = 0
    if arm_id == "BLEND":
        replay_ranker = rank_wcos_prior_agree_factory(FROZEN_WEIGHTS)
        replay_fuser = fuse_supplyfilter_factory(FROZEN_FUSE)
        query_vectors_by_sample: dict[str, tuple[float, ...]] = {}
        with query_vector_log.open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                contact_id = str(record["contact_id"])
                if contact_id.startswith("query:"):
                    query_vectors_by_sample[contact_id[len("query:") :]] = tuple(
                        float(v) for v in record["values"]
                    )
        for sample_id, row in sorted(mech_rows.items()):
            flown = row["fusion_selected_value_ids"]
            if flown is None:
                continue
            vector = query_vectors_by_sample.get(sample_id)
            if vector is None:
                replay_mismatches.append("%s: no landed query vector" % sample_id)
                continue
            replay_state = QueryState(
                query_id="replay:%s" % sample_id,
                query_sample_id=sample_id,
                speech_packet_id=packet_bindings[sample_id]["packet_id"],
                speech_packet_sha256=packet_bindings[sample_id]["sha256"],
                use_split_identity_hash=SPLIT_IDENTITY_HASH,
                use_partition_role="dev",
            ).validate()
            recall_scores = multidim_recall(
                snapshot,
                {"content": vector},
                lambda facet_id: facet_vector_table.get(facet_id, {}),
                FROZEN_TOP_K,
            )
            if not recall_scores:
                replay_selected: tuple[str, ...] = ()
            else:
                rank_result = replay_ranker(
                    snapshot_sha256=snapshot.content_hash(),
                    query_state=replay_state,
                    recall_scores=recall_scores,
                )
                fusion_decision = replay_fuser(
                    snapshot=snapshot,
                    snapshot_sha256=snapshot.content_hash(),
                    query_state=replay_state,
                    rank_result=rank_result,
                    recall_scores=recall_scores,
                )
                replay_selected = tuple(fusion_decision.selected_value_ids)
            replay_checked += 1
            if replay_selected != tuple(flown):
                replay_mismatches.append(sample_id)
        log(
            "branch-only replay: %d trajectories replayed through kb_policy's own pure "
            "functions, %d supply mismatches" % (replay_checked, len(replay_mismatches))
        )

    outputs_path = run_dir / ("%s-outputs.jsonl" % report_stub)
    with outputs_path.open("w", encoding="utf-8") as sink:
        for result in main_summary.results:
            controller = controllers_by_sample.get(result.sample_id)
            sink.write(
                json.dumps(
                    {
                        "arm": arm_id,
                        "sample_id": result.sample_id,
                        "final_response_text": result.final_response_text,
                        "direct_response_text": getattr(
                            controller, "direct_response_text", None
                        )
                        if max_contacts > 1
                        else result.final_response_text,
                        "contacts": len(result.contacts),
                        "slot_ids": [record.slot_id for record in result.contacts],
                        "winner_label": getattr(controller, "last_winner_label", None),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    (run_dir / ("%s-mechanical.json" % report_stub)).write_text(
        json.dumps(mech_rows, indent=1, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log("opaque outputs written: %s (never read semantically this step)" % outputs_path)

    retained_count = sum(1 for row in mech_rows.values() if row["retained_primary"])
    dispatched_count = sum(1 for row in mech_rows.values() if row["contacts"] == 2)
    label_recovered_count = sum(
        1 for row in mech_rows.values() if row["direct_label_recovered"] is True
    )
    dead_direct_dispatched = sum(
        1
        for row in mech_rows.values()
        if row["contacts"] == 2 and row["direct_label_recovered"] is not True
    )
    empty_or_unparsed_direct = sum(
        1 for row in mech_rows.values() if not row["direct_tool_multiset"]
    )
    # THE MECHANISM INVARIANT, computed here so a violation is visible at
    # landing: under the v1 cell (no override) a trajectory dispatches EXACTLY
    # when the normalizer recovered no label, so retain == direct-label-recovered.
    retain_equals_recovered = (
        arm_id != "BLEND"
        or all(
            (row["contacts"] == 1) == (row["direct_label_recovered"] is True)
            for row in mech_rows.values()
        )
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

    # The A2T direct envelope is about 13,236 tokens plus speech; the evidence
    # envelope is up to about 19,047. Split the classes well above the direct
    # envelope and well below the evidence worst case.
    DIRECT_CLASS_MAX_DECLARED = 15000
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
        main_evidence_rows = ordered_by_declared[len(samples) :]
    prompt_reuse_section = {
        "method": (
            "per request: declared = release n_tokens - generation tokens + calibrated "
            "fixed offset; evaluated = print_timing prompt-eval tokens (post-prefix-"
            "cache); windows split by tracked server-log offsets (canary / main / "
            "resend); main contact classes split at declared <= %d"
            % DIRECT_CLASS_MAX_DECLARED
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
        "schema": "saea-a2t-g1-%s-mechanical-v1" % report_stub,
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "arm_id": arm_id,
        "arm_index": arm["arm_index"],
        "attempt_id": attempt_id,
        "generated_at": iso_now(),
        "mechanical_only": True,
        "authority": (
            "campaign row SAEA-A2T-G1 under "
            "docs/readiness/2026-08-25-a2t-generality-campaign-plan.md sections 3.3 to "
            "3.6, section 7 (Amendment 1) and section 8 (owner Amendment 2); "
            "machine-readable contract configs/experiment/a2t-g1-v1.json. MECHANICAL "
            "landing only -- gold never opened here, no accuracy computed; the seal "
            "and score step runs separately under the same registered row"
        ),
        "claim": {
            "policy_cell": "TRANSFERS BYTE-IDENTICAL (v1, hash-pinned)",
            "serving_geometry": (
                "DERIVED per carrier by the campaign plan section 8.1 rule from the "
                "measured task contract, applied identically to every arm and fixed "
                "before any result was seen"
            ),
        },
        "config_hash": composed.config_hash,
        "serving_geometry": flight.get("serving_geometry"),
        "server_np": server_np,
        "decoder_session_receipt_sha256": measured_session,
        "gpu_preflight": flight["gpu_preflight"],
        "policy_cell": flight.get("policy_cell"),
        "packet_promotion": flight.get("packet_promotion"),
        "knowledge": flight.get("knowledge"),
        "frozen_cell": {
            "policy_config": POLICY_CELL_RELPATH,
            "policy_config_sha256": POLICY_CELL_SHA256,
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_TAU,
            "top_k_per_dimension": FROZEN_TOP_K,
            "fusion": {"m": FROZEN_FUSE.m, "c": FROZEN_FUSE.c, "l": FROZEN_FUSE.top_l},
            "rank_weights": {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2},
            "value_vectors": "SEALED (never produced, never loaded)",
            "kb_policy_last_commit": flight["invariants"]["kb_policy_last_commit"],
            "retain_override": "NOT CARRIED (v1, not the v2 lock candidate)",
        },
        "carrier_analogue": {
            "label_vocabulary_size": LABEL_VOCABULARY_SIZE,
            "direct_label_recovery": (
                "the answer's OWN parsed call list, PRIMARY tool name, matched EXACTLY "
                "against the label vocabulary, ties by facet_id ascending -- the A2T "
                "form of the SLURP scenario_action rule and of the f1060078 repair"
            ),
            "scorer_projection_is_different": (
                "tool accuracy is equality of the full tool-name MULTISET; the primary-"
                "name projection governs only the dispatch branch and is never scored"
            ),
        },
        "arm_construction": {
            "split_id": split_id,
            "sample_count": len(samples),
            "max_contacts": max_contacts,
            "controller_policy_id": controller_policy_id,
            "flies_full_subset": split_id == SPLIT_ID and len(samples) == SPLIT_COUNT,
            "exposure": (
                "EXPOSED tier -- plan section 3.3 makes these numbers SECONDARY "
                "readings, never the campaign claim"
            ),
        },
        "mechanical": {
            "loop_contacts": sum(row["contacts"] for row in mech_rows.values()),
            "pass_a_direct_contacts_flown": pass_a_contacts,
            "pass_b_evidence_contacts_flown": pass_b_evidence_contacts,
            "pass_b_contacts_resumed_at_zero_cost": replay_client.replayed
            if replay_client is not None
            else 0,
            "registered_pass_b_ceiling": PASS_B_CONTACT_CEILING,
            "dispatch_projection_count": DISPATCH_PROJECTION_COUNT,
            "dispatch_matched_projection": dispatched_count == DISPATCH_PROJECTION_COUNT,
            "one_contact_trajectories_retained_primary": retained_count,
            "two_contact_trajectories_dispatched": dispatched_count,
            "dispatch_rate": round(dispatched_count / len(samples), 6) if samples else None,
            "retain_rate": round(retained_count / len(samples), 6) if samples else None,
            "direct_label_recovered_samples": label_recovered_count,
            "dead_direct_dispatched": dead_direct_dispatched,
            "dispatch_decomposition_exact": dead_direct_dispatched == dispatched_count,
            "retain_equals_direct_label_recovered": retain_equals_recovered,
            "direct_answers_empty_or_unparsed": empty_or_unparsed_direct,
            "branch_only_replay": {
                "trajectories_replayed": replay_checked,
                "supply_mismatches": replay_mismatches,
                "branch_only_holds": not replay_mismatches,
            },
            "winner_label_present_samples": sum(
                1 for row in mech_rows.values() if row["winner_label_present"] is True
            ),
            "per_sample_records": "%s-mechanical.json (run dir)" % report_stub,
            "opaque_outputs": str(outputs_path),
        },
        "canary": flight.get("canary"),
        "two_pass": {
            "design": (
                "PASS A flies all 104 contact-0 direct decodes with the embedder "
                "sidecar DOWN and runs NO policy; an OFFLINE BRIDGE embeds every "
                "uncovered Pass-A text with the sidecar UP ALONE and stops it with "
                "its own receipt; PASS B runs the frozen v1 cell over each "
                "trajectory's OWN flown text and flies only the evidence contacts "
                "the policy dispatches, resuming contact 0 from Pass A's durable "
                "record at zero core contacts. Deferral, never omission: the policy "
                "is never run against an inert or substituted query vector"
            ),
            "pass_a": flight.get("pass_a"),
            "offline_bridge": flight.get("offline_bridge"),
            "pass_b": flight.get("pass_b"),
            "coresidency_invariant": coresidency_guard.summary(),
            "durable_query_vector_table": flight.get("durable_query_vector_table"),
            "dispatch_projection": flight.get("dispatch_projection"),
            "two_pass_worst_case": flight.get("two_pass_worst_case"),
        },
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
        "embedding_sidecar_lifecycle": flight.get("embedding_sidecar_lifecycle"),
        "query_vector_lookup": flight.get("query_vector_lookup"),
        "gpu_clock_throttle_telemetry": flight.get("gpu_clock_throttle_telemetry"),
        "successor_attempt": {
            "attempt_index": 3,
            "row": RUN_ID,
            "predecessor_attempt_ids": [
                "attempt-20260825T101057Z-a2tg1blend",
                "attempt-20260825T114856Z-a2tg1blend",
            ],
            "predecessor_outcome": (
                "attempt 1 SENTINEL ABORT at loop contact 26 of 208; attempt 2 "
                "SENTINEL ABORT at loop contact 60 of 208, attributed by its own "
                "FIX-1 telemetry to a MEMORY-PATH STALL UNDER VRAM OVERSUBSCRIPTION "
                "with throttling refuted -- SM clock 2,482 MHz of a 2,500 MHz lock, "
                "45 W of 100 W, 55 C, 100 percent utilization, decode about 51x "
                "slower while prefill moved only about 2.4x"
            ),
            "dead_spend_disclosed": {
                "attempt_1": {
                    "core_contacts": 28,
                    "metered_audio_seconds": 73.633,
                    "embedding_tool_contacts": 27,
                },
                "attempt_2": {
                    "core_contacts": 62,
                    "metered_audio_seconds": 277.177,
                    "embedding_tool_contacts": 99,
                },
                "total_core_contacts": 90,
                "status": (
                    "DEAD SPEND -- durable, unusable, charged against the "
                    "run-cumulative plan and never re-read as results"
                ),
            },
            "changes": [
                "TWO-PASS: the embedder sidecar is never co-resident with a decode contact, by construction rather than by luck",
                "CO-RESIDENCY GUARD: asserted fail-closed before EVERY frozen-core contact and at every phase boundary",
                "REPLAY: Pass B resumes contact 0 from Pass A's durable record, proving the messages digest matches, which is what makes the budget fit",
                "KEPT: FIX 1 telemetry armed through every phase; FIX 4 run-cumulative fail-closed guards",
                "DROPPED: FIX 3 cold start -- attempt 2 had one and stalled anyway, so the hypothesis is dead",
                "LOWERED CEILING with its basis stated: row SAEA-SN-MF-A2T-G1-DISPATCH-PROJECTION",
            ],
            "policy_surface_untouched": (
                "every change is SERVING or HARNESS; rails/ and core/ are byte-"
                "unchanged, the v1 policy cell is byte-identical, and the section 8.1 "
                "derived geometry is the geometry the M0 arm flew"
            ),
            "predecessor_launcher_sha256": {
                "attempt_1": "f7181af0b75bbbfd38fe0de3c68b1074f4009da0fa75b3f0a85c7b478b9dbc90",
                "attempt_2": "17b7efd93a435cc07ecaa146e5af9bc873cbefb0e8a476888f6cf0109355efa2",
            },
        },
        "mid_flight_clock_samples_windows_side": read_clock_samples(root, slug),
        "core_client": flight["core_client"],
        "invariants": flight.get("invariants"),
        "spend_vs_ceilings": {
            "this_attempt": {
                "core_contacts": {
                    "used": contact_total,
                    "attempt_ceiling": attempt_core_ceiling,
                },
                "embedding_tool_contacts": {
                    "used": tool_contacts_used,
                    "attempt_ceiling": attempt_tool_ceiling,
                },
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
            "MECHANICAL LANDING ONLY: this artifact carries no accuracy, no tool "
            "accuracy, no exact match, no per-tier table and NO VERDICT. The seal and "
            "score step computes those under the same registered row. G1 authorizes "
            "MECHANICS on an EXPOSED tier; the generality claim belongs to G2 on the "
            "unexposed tier and cannot be reached from anything here."
        ),
    }
    report_path = OUT_CHECK_DIR / ("%s-mechanical-report-attempt3.json" % report_stub)
    report_path.write_text(
        json.dumps(arm_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    flight["outcome_status"] = "ARM_LANDED_MECHANICAL"
    flight["report_path"] = str(report_path)
    save_flight()
    log("arm mechanical report written: %s" % report_path)
    log("report sha256: %s" % sha256_file(report_path))
    log(
        "MECHANICAL SUMMARY ARM %s: %d samples, %d loop contacts (+%d canary/resend), "
        "retain-primary %d, dispatched %d, direct-label recovered %d, core %d/%d "
        "(attempt), tool %d/%d, audio %s, cumulative core %d/%d"
        % (
            arm_id,
            len(samples),
            sum(row["contacts"] for row in mech_rows.values()),
            contact_total - sum(row["contacts"] for row in mech_rows.values()),
            retained_count,
            dispatched_count,
            label_recovered_count,
            contact_total,
            attempt_core_ceiling,
            tool_contacts_used,
            attempt_tool_ceiling,
            audio_seconds_metered,
            prior_calls + contact_total,
            CAMPAIGN_CEILING_CORE,
        )
    )
    log("RESIDENT DECODER LEFT UP (never stopped by this launcher); GOLD NEVER OPENED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
