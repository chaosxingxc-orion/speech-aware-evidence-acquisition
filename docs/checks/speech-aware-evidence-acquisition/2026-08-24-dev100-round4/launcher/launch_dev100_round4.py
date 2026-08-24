"""DEV-100 campaign **ROUND 4** launcher — exposure row
``SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN`` (bounded-discovery-probe).

ROUND-4 VARIABLE (single knob): **alpha 0.55 -> 0.45** — the FIRST alpha
move since the ``f1060078`` label-identity binding repair made the
``(1 - alpha)`` protect-direct term live (round 3). At alpha 0.45 the
direct term (0.55) out-scores even a fully-concentrated fused mass
(alpha * 1.0 = 0.45), so retain-primary fires on EVERY sample whose
direct label the repaired normalizer recovers. ALL OTHER KNOBS ARE
UNCHANGED from the sealed round-3 cell (tau 0.65, rrf rank weighting,
evidence = rank + prior + agreement, top-k 5, fusion m=5/c=2/l=3, rank
weights 0.5/0.3/0.2, TRAIN priors, M11 pair-boundary stage OFF, value
vectors SEALED, facet-side admission; the f1060078 repair remains live
and is asserted present at preflight as an INVARIANT, not a variable) —
single-variable attribution: any movement vs round 3 belongs to the alpha
move (or to the documented direct-decode byte-variance channel,
attributed per sample).

REGISTERED FALSIFIABLE PROJECTION (damage-channel analysis
``docs/readiness/2026-08-24-dev100-damage-channel-analysis.md`` section 7
row ``label-identity-repair-alpha-045`` / section 9 closing paragraph, an
EXACT offline replay over the sealed ROUND-2 trajectories, zero unknowns
GIVEN the logged responses; per-sample membership re-derived model-free
pre-registration from the same sealed bytes, derivation receipt
``alpha045-projection-derivation.json`` sha256 ``250a7034…3dc0a``):
BLEND-r4 = 74/100 over round-2 bytes (round 2: 65); heals ALL 11 of the
old damage set; loses exactly 4 repairs (001569, 002814, 010037, 011819);
gains exactly 2 samples outside both groups (004899, 015265);
still-damaged EMPTY; retain-primary fires on 64/100 trajectories (so ~136
core contacts instead of 200). DOCUMENTED VARIANCE CAVEAT, registered
with the projection: the projection is exact only GIVEN round-2's logged
responses — round 3 QUANTIFIED the direct-byte-variance channel at ~+/-4
samples (vs-r2 direct agreement 79/100; all 4 round-3 projection misses
attributed to that channel), and at alpha .45 the retain-primary finals
are 64 FRESH direct decodes (vs 54 in round 3), so the credible flown
band is ~70-74. Deviations inside that channel are expected and are
attributed per-sample in the report's projection-reconciliation section.

This launcher is the flight-proven ROUND-3 launcher
(``../2026-08-24-dev100-round3/launcher/launch_dev100_round3.py``, landed
exit 0, 1-contact trajectories exercised in flight: retain-primary 52/100)
with exactly these changes: round index / attempt naming / output paths;
the SINGLE knob change alpha 0.55 -> 0.45; the fresh run-cumulative
successor plan declaration (1,600 calls / 4,300 audio-s over the 1,274 /
3,408.0633749999993 durable for rounds 0-3, re-summed from the
AttemptStore at registration); the ROUND-3 sealed per-sample scoring
artifact + round-3 report added as byte-pinned scoring-side authorities
(the primary round-over-round comparison is vs round 3; the projection
reconciliation stays r2-based because the alpha-.45 projection's given
inputs are round-2's logged responses, with the round-2 query-vectors log
the direct-hash attribution authority, carried); and the round-4 stopping
rule evaluation (round 3's +2 delta left the streak EMPTY — a qualifying
round 4 BANKS the first of two needed rounds; convergence CANNOT fire at
this seal; round 4 is the 5th of the hard cap 6). The serving session is
the SAME attempt-6 BASE-build resident service (receipt hash re-verified
before attach; the R6 prompt-fit row binds this session and STANDS — the
alpha knob is blend-decision-side only, it changes no prompt shape and
can only SUPPRESS the evidence contact, so the fit's worst-case m/c/l
envelope remains the upper bound).

Gold discipline: devel gold and every gold-derived artifact (the round-0
through round-3 per-sample scores) open SCORING-SIDE ONLY, after all
round-4 arms seal. Before the seal this launcher touches them as opaque bytes
(sha256 pins) only.

Encode-only scope note, recorded honestly: the source-level guards 1/2 of
``rails.encode_only_check`` are scoped to embedding-only runners and are NOT
run over this launcher's own source — this launcher legitimately constructs
``FrozenCoreClient`` (a generation client) for the frozen-core arms, which is
what those guards exist to refuse in an embedding-only context. The embedding
CHANNEL keeps its full protection: the pinned-module structural sweep
(guard set a), the live-client surface check (guard 3), and the per-request
payload sweep (guard 4) all run.

Run in WSL2 (systemd-run --user unit, immune to agent-session reaping;
PATH must include /usr/lib/wsl/lib for the in-script nvidia-smi — the
round-3 wrapper lesson)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python docs/checks/.../launcher/launch_dev100_round4.py

Self-test (offline: stubbed timings, zero contacts, no service, no gate)::

    ... launch_dev100_round4.py --self-test
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
# below except the round-4 plan/authority/projection block is byte-identical
# to the flight-proven round-3 launcher).
# --------------------------------------------------------------------------

RUN_ID = "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
ROUND_INDEX = 4
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
# comparison + resend response A). Round 4 never parses its response TEXTS —
# the M0 arm's scoring authority is round-0's sealed per-sample artifact.
A1_ATTEMPT_ID = "attempt-20260824T073337Z-dev100r0"
A1_TRACE_SHA256 = "d1f376bbacaa189f6583abe639d072567c4001fe63c52dab34e113b59ce4d8a2"

# ROUND-0, ROUND-1, ROUND-2 AND ROUND-3 SEALED AUTHORITIES (gold-derived;
# opened content-wise ONLY at the post-seal scoring step; before that,
# opaque byte pins).
A6_ATTEMPT_ID = "attempt-20260824T122641Z-dev100r0a6"
ROUND0_REPORT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round0/"
    "round0-report.json"
)
ROUND0_REPORT_SHA256 = "26f05488bb7031d1ae85710faffd2b414644729af1adc476a1002a55612fb0b6"
ROUND0_SCORES_SHA256 = "88922466d0463169547f0fcfae20bbdf98a6dd94a8ad7d89b68956a8bd343bed"
R1_ATTEMPT_ID = "attempt-20260824T144230Z-dev100r1"
R1_DUPLICATE_ATTEMPT_ID = "attempt-20260824T145246Z-dev100r1"  # refused takeoff, dead spend disclosed
ROUND1_REPORT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round1/"
    "round1-report.json"
)
ROUND1_REPORT_SHA256 = "559559d239103f2905d8e86e643741990ceb1023070095d1d797d8e66de4cd8d"
ROUND1_SCORES_SHA256 = "c70947e5c89203ce68eb40ca2fa62da13a3bde53ebbdf00882adee944b08ee78"
R2_ATTEMPT_ID = "attempt-20260824T153842Z-dev100r2"
ROUND2_REPORT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round2/"
    "round2-report.json"
)
ROUND2_REPORT_SHA256 = "c69cf3fef49a3bafb86818383953c9c0e37880518750073c6ba857f47e7b00f6"
ROUND2_SCORES_SHA256 = "6f9d65ac173f5304c0c58baadb1abe4b66cd5c0960e003e6acc817f3befa7191"
# Round-2 query-vectors log: NOT gold-derived (direct-decode response text
# sha256 per sample + embedding vectors), but opened content-wise only at
# the post-seal attribution step for cleanliness; byte pin verified at
# preflight. It stays the direct-hash attribution authority for the alpha-
# .45 projection, whose given inputs are round-2's logged responses.
ROUND2_QUERY_VECTORS_SHA256 = (
    "3b146c2fde28169bec2dce77fa37e1daf9aafd0153cab77c05884757be155c1e"
)
R3_ATTEMPT_ID = "attempt-20260824T173555Z-dev100r3"
ROUND3_REPORT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev100-round3/"
    "round3-report.json"
)
ROUND3_REPORT_SHA256 = "ac5a884febb43ede69b6401deb6e1e67e1e543c8e8082e50ad552b8358c47965"
ROUND3_SCORES_SHA256 = "90a27ea18a3773950948be8d21072dcb336cd0393eedb6ed23c166a42aa461a7"

# Prior-round durable cumulative spend (rounds 0-3 including the disclosed
# round-1 duplicate takeoff; re-summed from the durable AttemptStore
# attempts/<run_id>/*.json at round-4 registration — the FIRST authority
# per the round-1 duplicate lesson: 1,274 calls / 3,408.0633749999993
# audio-s across 12 records with NO round-4 attempt present; 623 tool
# contacts from the ledger row accounting, the store does not meter the
# tool channel).
PRIOR_CORE_CONTACTS = 1274
PRIOR_TOOL_CONTACTS = 623
PRIOR_AUDIO_SECONDS = 3408.0633749999993

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

# Hosting (INHERITED from attempt 6 through rounds 1-3, verified at
# registration): the BASE-build resident service has served rounds 0-3 and
# serves round 4 unchanged; the session receipt hash below binds the same
# session the R6 prompt-fit row measured, so the fit STANDS for this round.
HOSTING = {
    "mode": "systemd-run --user unit saea-np8-dev100-r6-base -p KillMode=mixed (WSL Ubuntu-24.04, systemd PID 1)",
    "keepalive": "detached Windows wsl.exe client, PID 23864, started 2026-08-24T10:52:39Z (verified alive at round-4 registration; holds the VM)",
    "linger": "enabled (loginctl enable-linger chao, 2026-08-24T08:06Z)",
    "service_inheritance": (
        "round 4 flies on the SAME resident BASE-build service the attempt-6 "
        "round-0 landing left up and rounds 1-3 landed on (unit "
        "saea-np8-dev100-r6-base, llama-server pid 2768, port 8080, BASE "
        "build llama.cpp-featcache, 8 slots at n_ctx 8192): at round-4 "
        "registration the unit was active, /health ok, 8/8 slots idle, the "
        "server log shows exactly one launch (8 slot-init lines), and the "
        "session receipt re-hashed byte-identical to the attempt-6 binding "
        "— no respawn, no restart, no binary change"
    ),
    "prompt_fit_standing": (
        "session-bound R6 prompt-fit row SAEA-SN-MF-DEV100-C3-PROMPT-FIT-NP8-R6 "
        "STANDS for round 4: the session receipt sha256 re-measured equal to "
        "the R6 binding at registration, and the round-4 variable (alpha "
        "0.55 -> 0.45) is blend-DECISION-side only — it changes which "
        "contact is dispatched (it can only SUPPRESS the evidence contact "
        "via retain-primary), never a prompt shape — the worst-case "
        "evidence-decode envelope the fit measured (6,174 tokens vs 8,192, "
        "margin +1,954) is an upper bound at the unchanged fusion knobs "
        "m=5/c=2/l=3"
    ),
    "clock_lock_note": (
        "the Windows-side GPU clock lock nvidia-smi -lgc 1200,2500 REMAINS "
        "applied (harmless and explicitly NOT a remedy - the attempt-5 "
        "mid-flight samples falsified the clock hypothesis; the attempt-6 "
        "base-binary landing confirmed the pathology was build-bound); "
        "mid-flight Windows-side clock sampling continues into "
        "clock-samples-round4.jsonl"
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
# ROUND-4 knobs: the SINGLE registered variable is alpha 0.55 -> 0.45 —
# the first alpha move since the f1060078 repair made the protect-direct
# term live. Every other knob below is byte-identical to the sealed
# round-3 cell (which was itself byte-identical to round 2). The repair
# remains an INVARIANT (asserted present at preflight by a behavior probe
# + the last commit touching rails/kb_policy.py). Provenance ids
# rank_weight_id=rrf / evidence_variant=rank+prior+agreement name the
# sweep cell; the flown machinery is the FROZEN registered C3 chain.
# --------------------------------------------------------------------------
ROUND4_ALPHA = 0.45
ROUND4_TAU = 0.65
ROUND4_TOP_K = 5
ROUND4_FUSE = FuseKnobs(tau=ROUND4_TAU, m=5, c=2, top_l=3)
ROUND4_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

# REGISTERED FALSIFIABLE PROJECTION (damage-channel analysis section 7 row
# label-identity-repair-alpha-045 / section 9 closing paragraph: exact
# offline replay over the sealed ROUND-2 trajectories at alpha 0.45 with
# the repair live; aggregate 74/100 published in the landed analysis, the
# per-sample membership re-derived model-free pre-registration from the
# same sealed bytes — derivation receipt alpha045-projection-derivation
# .json, sha256 250a7034059925917fe8f098766be38c56e7fb05406e200c3976d66f
# 9c83dc0a, socket-guarded, supply-fidelity gate passed, zero contacts;
# registered in the campaign row BEFORE takeoff). The report's
# projection-reconciliation section compares the flown round 4 against
# this, per sample, with variance-channel attribution. NOTE the projection
# base is ROUND-2 bytes (the analysis' given inputs), not round 3.
_P = "slurp:devel:"
PROJECTION = {
    "projected_correct_total": 74,
    "damage_healed": (
        f"{_P}000090:audio-1498567209",
        f"{_P}001227:audio-1490104218",
        f"{_P}001791:audio-1502195360",
        f"{_P}003202:audio-1495733953-headset",
        f"{_P}003443:audio-1501776590",
        f"{_P}003705:audio-1490194357",
        f"{_P}007738:audio-1489153308",
        f"{_P}012185:audio-1499244805",
        f"{_P}012625:audio-1494417974",
        f"{_P}015630:audio-1490967842",
        f"{_P}016699:audio-1499688493-headset",
    ),
    "still_damaged": (),
    "repairs_lost": (
        f"{_P}001569:audio-1490198849-headset",
        f"{_P}002814:audio-1490194699",
        f"{_P}010037:audio-1500386970-headset",
        f"{_P}011819:audio--1505404383-headset",
    ),
    "gains_outside_both_groups": (
        f"{_P}004899:audio-1495377050",
        f"{_P}015265:audio-1499689293-headset",
    ),
    "retain_primary_projected_count": 64,
    "expected_core_contacts_blend": "~136 (100 direct + ~36 evidence)",
    "variance_source": (
        "the retain-primary finals are FRESH direct decodes carrying the "
        "documented 75-81/100 cross-attempt direct byte instability; the "
        "projection is exact only GIVEN the round-2 logged responses. "
        "Round 3 QUANTIFIED this channel at ~+/-4 samples (vs-r2 direct "
        "agreement 79/100; all 4 round-3 projection misses attributed to "
        "it), and alpha .45 makes 64 finals fresh directs (vs 54 in round "
        "3) — the registered credible flown band is ~70-74"
    ),
}

# Round-4 attempt ceilings (campaign-row round-4 registration, carried
# unchanged from round 3): <= 210 frozen-core contacts (4 canary allowance —
# the registered pair plus a one-time re-run pair ONLY if bytes differ from
# attempt-1's M0 hashes — + 200 BLEND per-loop worst case + 1 resend +
# margin; the PROJECTED spend is ~139 because retain-primary trajectories
# are 1-contact, but the ceiling prices the worst case where retain-primary
# never fires), <= 130 embedding tool contacts. Both enforced fail-closed by
# caller-side meters.
#
# PLANNED_MODEL_CALLS and PLANNED_AUDIO_SECONDS are RUN-CUMULATIVE
# (core.model.adapter enforces both across every attempt of the run id via a
# fresh sibling read of durable attempt actuals per request). This is the
# FRESH SUCCESSOR PLAN (the round-3 1,400 / 3,700 plan is nearly exhausted
# at 1,274 / 3,408.06 durable): 1,600 = 1,274 durable (AttemptStore re-sum
# across 12 records) + 210 attempt worst case + 116 margin; 4,300 audio-s =
# 3,408.06 durable + ~575 worst case this round (556.4 full-dispatch BLEND
# pass + canary/resend/rerun allowance) + ~317 margin. Both are inside the
# AMENDED campaign cells (2,500 core / 5,500 audio-s).
# rails.runner's per-loop worst-case check sees 200 <= 1,600.
ATTEMPT_CORE_CEILING = 210
ATTEMPT_TOOL_CEILING = 130
PLANNED_MODEL_CALLS = 1600
PLANNED_AUDIO_SECONDS = 4300
PLANNED_GPU_HOURS = 1.0
REFUSED_TAKEOFFS: list[dict[str, object]] = []

# Decode-speed canary (attempt-3 registration, carried unchanged): 2 direct-
# decode contacts on the FIRST TWO attempt-1 M0 sample ids (sorted order),
# single-slot, timing only. PASS: every canary generation rate < 300
# ms/token (round-3 canary measured 9.93/6.89 on this very service). The
# byte comparison vs attempt-1 M0 is a RECORDED FACT; round 4 flies the
# SAME BASE build attempt 6 proved byte-identical to M0 (rounds 1-3 and the
# refused duplicate takeoff reconfirmed it repeatedly — most recently the
# round-3 canary AND resend, byte-identical), so a mismatch is unexpected —
# if bytes differ the pair is re-run ONCE and within-build byte-identity is
# REQUIRED (a mismatch stops fail-closed). The alpha knob cannot touch the
# canary: the M0 controller runs snapshot=None single-contact, so the blend
# decision is never consulted.
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
        "2026-08-24 round-4 preflight (host PowerShell WMI GetSmartFanMode=3 "
        "+ Windows nvidia-smi enforced 100.00 W, idle 1192 MHz / 0 % util / "
        "39 C / 21,264 MiB resident; service /health ok with 8/8 slots idle "
        "and exactly one launch in the server log (8 slot-init lines); "
        "keepalive PID 23864 alive; llama-server pid 2768 up; session "
        "receipt re-hashed equal to the attempt-6/R6 binding; durable "
        "AttemptStore re-summed to 1,274 calls / 3,408.0633749999993 audio-s "
        "across 12 records with NO round-4 attempt present)"
    ),
}

OUT_CHECK_DIR = REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-24-dev100-round4"

# Mid-flight clock sampling (attempt-5 semantics, CONTINUED): the coordinator
# samples the GPU from the WINDOWS side every ~10 s into this run-level JSONL
# file; the launcher embeds whatever samples exist into the sentinel abort
# record and the round report.
CLOCK_SAMPLES_NAME = "clock-samples-round4.jsonl"


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
                    f"round-4 core ceiling: <= {self._ceiling} frozen-core "
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
        # Launcher-side observability (introduced in round 3, never consulted by policy):
        # the label facet the REPAIRED normalizer recovered from the flown
        # direct response, captured after the registered controller advanced.
        self.direct_label_recovered: str | None = None

    def initial_contact(self, context):
        return self._inner.initial_contact(context)

    def advance(self, context, contact, response_text):
        is_direct = (
            contact.contact_id == "direct-decode"
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
            self.direct_label_recovered = getattr(self._inner, "_direct_label", None)
        return advance

    @property
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


# --------------------------------------------------------------------------
# Embedding contact meter (round-4 tool sub-ceiling, fail-closed).
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
                    f"embedding tool ceiling: round 4 registers <= {self.ceiling} "
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


def parse_slot_requests(log_bytes: bytes) -> list[dict[str, int]]:
    """Per-request serving records from raw llama-server log bytes —
    content-free COUNTS only (owner directive: prompt-reuse is a first-class
    metric). For every completed task: server slot id, task id, EVALUATED
    prompt tokens (the print_timing prompt-eval row — tokens actually
    processed after the slot prompt-cache prefix hit), generation tokens,
    and the release-time ``n_tokens`` (total tokens resident in the slot =
    declared prompt + generated, up to a fixed per-request offset that the
    flight calibrates against the client-side declared total). Only tasks
    with all three rows present are returned (sorted by task id)."""

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

    base = Path(tempfile.mkdtemp(prefix="saea-dev100-r4-selftest-"))
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

    # ---- prompt-reuse parser (owner directive: prefix-cache metric) ------
    stub_requests = (
        "165.41.712.384 I slot launch_slot_: id  4 | task 10 | processing task, is_child = 0\n"
        "165.41.748.510 I slot print_timing: id  4 | task 10 | prompt eval time =     233.21 ms /    75 tokens (    3.11 ms per token,   321.60 tokens per second)\n"
        "165.41.748.517 I slot print_timing: id  4 | task 10 |        eval time =    1714.68 ms /    48 tokens (   35.72 ms per token,    27.99 tokens per second)\n"
        "165.41.748.606 I slot      release: id  4 | task 10 | stop processing: n_tokens = 1817, truncated = 0\n"
        "165.57.331.776 I slot launch_slot_: id  1 | task 11 | processing task, is_child = 0\n"
        "165.58.552.171 I slot print_timing: id  1 | task 11 | prompt eval time =     634.41 ms /   529 tokens (    1.20 ms per token,   833.84 tokens per second)\n"
        "165.58.552.178 I slot print_timing: id  1 | task 11 |        eval time =     585.96 ms /    18 tokens (   32.55 ms per token,    30.72 tokens per second)\n"
        "165.58.552.276 I slot      release: id  1 | task 11 | stop processing: n_tokens = 2280, truncated = 0\n"
        "165.59.000.000 I slot launch_slot_: id  2 | task 12 | processing task, is_child = 0\n"
        "165.59.000.001 I slot print_timing: id  2 | task 12 | prompt eval time =       1.00 ms /     1 tokens (    1.00 ms per token,  1000.00 tokens per second)\n"
    )
    parsed_requests = parse_slot_requests(stub_requests.encode("utf-8"))
    if len(parsed_requests) != 2:  # task 12 lacks generation + release rows
        raise SystemExit(f"self-test FAIL: parser returned {len(parsed_requests)} complete requests")
    first, second = parsed_requests
    if (first["slot"], first["task"], first["prompt_eval_tokens"], first["generation_tokens"], first["release_n_tokens"]) != (4, 10, 75, 48, 1817):
        raise SystemExit(f"self-test FAIL: parser row 1 wrong: {first}")
    if second["release_n_tokens"] - second["generation_tokens"] != 2262:
        raise SystemExit(f"self-test FAIL: declared arithmetic wrong: {second}")
    dist = token_count_distribution([5, 1, 9])
    if (dist["count"], dist["min"], dist["median"], dist["max"], dist["sum"]) != (3, 1, 5, 9, 15):
        raise SystemExit(f"self-test FAIL: token distribution wrong: {dist}")
    if token_count_distribution([]) != {"count": 0}:
        raise SystemExit("self-test FAIL: empty distribution wrong")
    log("self-test prompt-reuse parser PASS: per-request records + declared arithmetic + distribution")

    # ---- round-4 knob sanity: alpha is THE single registered variable
    # (0.55 -> 0.45); every OTHER knob must equal the sealed round-3 cell ---
    if ROUND4_ALPHA != 0.45:
        raise SystemExit(f"self-test FAIL: round-4 alpha is not the registered 0.45: {ROUND4_ALPHA}")
    if ROUND4_FUSE.tau != 0.65 or (ROUND4_FUSE.m, ROUND4_FUSE.c, ROUND4_FUSE.top_l) != (5, 2, 3):
        raise SystemExit(f"self-test FAIL: fuse knobs drifted from the round-3 cell: {ROUND4_FUSE}")
    if ROUND4_TOP_K != 5:
        raise SystemExit("self-test FAIL: top-k drifted from the round-3 cell")
    if (ROUND4_WEIGHTS.w_cos, ROUND4_WEIGHTS.w_prior, ROUND4_WEIGHTS.w_agree) != (0.5, 0.3, 0.2):
        raise SystemExit("self-test FAIL: rank weights drifted from the round-3 cell")
    log("self-test knob sanity PASS: alpha 0.45 is the single variable; every other knob byte-equal to the round-3 cell")

    # ---- round-4 invariant: the f1060078 REPAIRED normalizer must be the
    # flown one (offline behavior probe, no snapshot, no contact) -----------
    probe_targets = {"facet:a": "alarm_query", "facet:b": "alarm_set"}
    flown_json = '{"scenario": "alarm", "action": "query", "entities": []}'
    if default_label_normalizer(flown_json, probe_targets) != "facet:a":
        raise SystemExit(
            "self-test FAIL: the flown default_label_normalizer does NOT "
            "recover the label from parsed scenario/action — the f1060078 "
            "repair is not present in the imported rails.kb_policy"
        )
    swapped_json = '{"scenario": "query", "action": "alarm", "entities": []}'
    if default_label_normalizer(swapped_json, probe_targets) is not None:
        raise SystemExit(
            "self-test FAIL: the normalizer matched a scenario/action SWAP — "
            "the repair must be exact-match only"
        )
    prose_map = {
        "facet:a": "Intent 'alarm_query' (scenario='alarm', action='query'); 130 TRAIN utterances in this snapshot."
    }
    if default_label_normalizer("Intent 'alarm_query' (scenario='alarm', action='query'); 130 TRAIN utterances in this snapshot.", prose_map) is not None:
        raise SystemExit(
            "self-test FAIL: the normalizer still matches prose facet "
            "representations as substrings — the PRE-repair behavior is live"
        )
    log(
        "self-test repair-presence probe PASS: identity exact-match live, "
        "swap refused, prose-substring path dead"
    )

    # ---- one-contact-trajectory accounting (retain-primary rounds) --------
    stub_scores = {
        "s1": {"contacts": 1},
        "s2": {"contacts": 2},
        "s3": {"contacts": 1},
    }
    stub_retained = sorted(sid for sid, row in stub_scores.items() if row["contacts"] == 1)
    stub_dispatched = sum(1 for row in stub_scores.values() if row["contacts"] == 2)
    if stub_retained != ["s1", "s3"] or stub_dispatched != 1:
        raise SystemExit("self-test FAIL: 1-contact trajectory accounting wrong")
    if sum(row["contacts"] for row in stub_scores.values()) != 4:
        raise SystemExit("self-test FAIL: mixed-contact total wrong")
    if int(PROJECTION["projected_correct_total"]) != 65 + len(
        PROJECTION["damage_healed"]
    ) - len(PROJECTION["repairs_lost"]) + len(PROJECTION["gains_outside_both_groups"]):
        raise SystemExit("self-test FAIL: registered projection arithmetic inconsistent")
    if len(PROJECTION["still_damaged"]) != 0 or len(PROJECTION["damage_healed"]) != 11:
        raise SystemExit(
            "self-test FAIL: the alpha-.45 projection heals ALL 11 damaged "
            "samples (still_damaged must be empty)"
        )
    log(
        "self-test 1-contact accounting + projection arithmetic PASS "
        "(65 + 11 - 4 + 2 = 74)"
    )
    log("SELF-TEST PASS (retained mechanisms + knob sanity + repair probe + accounting; zero contacts)")
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
    attempt_id = f"attempt-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-dev100r4"
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"ROUND 4 launcher — {RUN_ID} / {attempt_id}")
    log(f"run dir: {run_dir}")

    flight: dict[str, object] = {
        "schema": "saea-dev100-round4-flight-v1",
        "run_id": RUN_ID,
        "round_index": ROUND_INDEX,
        "attempt_id": attempt_id,
        "prior_attempt_ids_disclosed": [
            "attempt-20260824T073337Z-dev100r0",
            "attempt-20260824T084302Z-dev100r0a2",
            "attempt-20260824T093833Z-dev100r0a3",
            "attempt-20260824T111833Z-dev100r0a4",
            "attempt-20260824T114704Z-dev100r0a5",
            A6_ATTEMPT_ID,
            R1_ATTEMPT_ID,
            R1_DUPLICATE_ATTEMPT_ID,
            R2_ATTEMPT_ID,
            R3_ATTEMPT_ID,
        ],
        "registered_projection": dict(PROJECTION),
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

    # ---- ROUND-0/ROUND-1 sealed authorities: OPAQUE BYTE PINS pre-seal ----
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
    round1_report_path = REPO / ROUND1_REPORT_RELPATH
    measured_r1_report = sha256_file(round1_report_path)
    if measured_r1_report != ROUND1_REPORT_SHA256:
        raise SystemExit(
            f"round-1 sealed report hashes to {measured_r1_report}, not the "
            f"registered {ROUND1_REPORT_SHA256}"
        )
    round1_scores_path = root / "runs" / RUN_ID / R1_ATTEMPT_ID / "round1-scores.json"
    measured_r1_scores = sha256_file(round1_scores_path)
    if measured_r1_scores != ROUND1_SCORES_SHA256:
        raise SystemExit(
            f"round-1 per-sample scores hash to {measured_r1_scores}, not the "
            f"registered {ROUND1_SCORES_SHA256}"
        )
    round2_report_path = REPO / ROUND2_REPORT_RELPATH
    measured_r2_report = sha256_file(round2_report_path)
    if measured_r2_report != ROUND2_REPORT_SHA256:
        raise SystemExit(
            f"round-2 sealed report hashes to {measured_r2_report}, not the "
            f"registered {ROUND2_REPORT_SHA256}"
        )
    round2_scores_path = root / "runs" / RUN_ID / R2_ATTEMPT_ID / "round2-scores.json"
    measured_r2_scores = sha256_file(round2_scores_path)
    if measured_r2_scores != ROUND2_SCORES_SHA256:
        raise SystemExit(
            f"round-2 per-sample scores hash to {measured_r2_scores}, not the "
            f"registered {ROUND2_SCORES_SHA256}"
        )
    round2_qvec_path = root / "runs" / RUN_ID / R2_ATTEMPT_ID / "query-vectors.jsonl"
    measured_r2_qvec = sha256_file(round2_qvec_path)
    if measured_r2_qvec != ROUND2_QUERY_VECTORS_SHA256:
        raise SystemExit(
            f"round-2 query-vectors log hashes to {measured_r2_qvec}, not the "
            f"registered {ROUND2_QUERY_VECTORS_SHA256}; the direct-response "
            "attribution authority cannot be identified"
        )
    round3_report_path = REPO / ROUND3_REPORT_RELPATH
    measured_r3_report = sha256_file(round3_report_path)
    if measured_r3_report != ROUND3_REPORT_SHA256:
        raise SystemExit(
            f"round-3 sealed report hashes to {measured_r3_report}, not the "
            f"registered {ROUND3_REPORT_SHA256}"
        )
    round3_scores_path = root / "runs" / RUN_ID / R3_ATTEMPT_ID / "round3-scores.json"
    measured_r3_scores = sha256_file(round3_scores_path)
    if measured_r3_scores != ROUND3_SCORES_SHA256:
        raise SystemExit(
            f"round-3 per-sample scores hash to {measured_r3_scores}, not the "
            f"registered {ROUND3_SCORES_SHA256}"
        )
    log(
        "round-0/1/2/3 sealed authorities pinned byte-wise (r0 report "
        f"{measured_r0_report[:12]}…, r0 scores {measured_r0_scores[:12]}…, "
        f"r1 report {measured_r1_report[:12]}…, r1 scores "
        f"{measured_r1_scores[:12]}…, r2 report {measured_r2_report[:12]}…, "
        f"r2 scores {measured_r2_scores[:12]}…, r2 query-vectors "
        f"{measured_r2_qvec[:12]}…, r3 report {measured_r3_report[:12]}…, "
        f"r3 scores {measured_r3_scores[:12]}…); content stays sealed until "
        "the post-seal scoring step"
    )
    flight["sealed_authorities"] = {
        "round0_report_path": str(round0_report_path),
        "round0_report_sha256": measured_r0_report,
        "round0_scores_path": str(round0_scores_path),
        "round0_scores_sha256": measured_r0_scores,
        "round1_report_path": str(round1_report_path),
        "round1_report_sha256": measured_r1_report,
        "round1_scores_path": str(round1_scores_path),
        "round1_scores_sha256": measured_r1_scores,
        "round2_report_path": str(round2_report_path),
        "round2_report_sha256": measured_r2_report,
        "round2_scores_path": str(round2_scores_path),
        "round2_scores_sha256": measured_r2_scores,
        "round2_query_vectors_path": str(round2_qvec_path),
        "round2_query_vectors_sha256": measured_r2_qvec,
        "round3_report_path": str(round3_report_path),
        "round3_report_sha256": measured_r3_report,
        "round3_scores_path": str(round3_scores_path),
        "round3_scores_sha256": measured_r3_scores,
    }

    # ---- ROUND-4 INVARIANT assertion (the f1060078 repair stays live) -----
    # The round-4 variable is the alpha KNOB (0.55 -> 0.45); the repair is
    # an inherited invariant. (a) behavior probe: the flown
    # default_label_normalizer recovers the label facet from the answer's
    # OWN parsed scenario/action, exact-match only; (b) provenance: the
    # last commit touching rails/kb_policy.py is STILL the repair commit —
    # any later touch would break single-variable attribution.
    import subprocess as _subprocess

    if default_label_normalizer(
        '{"scenario": "alarm", "action": "query", "entities": []}',
        {"facet:a": "alarm_query"},
    ) != "facet:a" or default_label_normalizer(
        '{"scenario": "query", "action": "alarm", "entities": []}',
        {"facet:a": "alarm_query"},
    ) is not None:
        raise SystemExit(
            "round-4 invariant MISSING: the imported rails.kb_policy does not "
            "carry the f1060078 label-identity binding repair; refusing"
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
            "rails/kb_policy.py's last commit is "
            f"{kb_policy_last_commit[:12]}, not the repair commit f1060078 — "
            "rails/ was touched since round 3; single-variable attribution "
            "would be broken — refusing"
        )
    repo_head_commit = _subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    flight["round4_variable"] = {
        "kind": "knob (alpha 0.55 -> 0.45; the first alpha move since the f1060078 repair made the protect-direct term live)",
        "alpha_flown": ROUND4_ALPHA,
        "alpha_round3": 0.55,
        "repair_invariant_commit": kb_policy_last_commit,
        "repo_head_at_flight": repo_head_commit,
        "behavior_probe": "PASS (identity exact-match live, swap refused)",
        "knobs_changed": "alpha ONLY",
    }
    log(
        f"round-4 variable: alpha {ROUND4_ALPHA} (was 0.55); repair invariant "
        f"asserted (kb_policy last commit {kb_policy_last_commit[:12]}, repo "
        f"HEAD {repo_head_commit[:12]}, behavior probe PASS)"
    )

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
        request_id_prefix="dev100r4",
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
    # ROUND-2 FIX (carried through rounds 3-4): the WSL bridge binary
    # /usr/lib/wsl/lib/nvidia-smi timed out (5 s) under decode load and the
    # sampler self-disabled for the whole round-1 flight. The Windows-side
    # binary answered reliably every ~10 s all flight (clock-samples JSONL),
    # so round 4 points the SAME fail-tolerant sampler at it through WSL
    # interop, at a gentler 5 s cadence. Telemetry plumbing only — never a
    # science knob; on any failure the sampler still degrades to
    # NOT_AVAILABLE without touching the flight.
    sampler = resolve_resource_sampler(
        binary="/mnt/c/Windows/System32/nvidia-smi.exe",
        interval_seconds=5.0,
        slots_url=f"http://127.0.0.1:{DECODER_PORT}/slots",
    )
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
        canary_registry = Registry("dev100 round4 canary controller")
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
                "semantics (attempt-3 registration, carried to round 4; the "
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
                "canary bytes MATCH attempt-1 M0 (yet another cross-instance "
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
            rerun_registry = Registry("dev100 round4 canary rerun controller")
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
                "round4_response_sha256": dict(sorted(first_run_sha.items())),
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

        # ---- Arm BLEND (alpha 0.45 — THE round-4 knob; all else round-3 cell) ----
        cells = {sample.sample_id: LazyQueryVector() for sample in samples}
        kb_factory = make_kb_alpha_blend_controller_factory(
            snapshot=snapshot,
            query_vectors_by_sample={
                sample_id: {"content": cell} for sample_id, cell in cells.items()
            },
            facet_vectors=facet_vectors,
            normalizer=default_label_normalizer,
            rank_weights=ROUND4_WEIGHTS,
            fuse_knobs=ROUND4_FUSE,
            alpha=ROUND4_ALPHA,
            top_k_per_dimension=ROUND4_TOP_K,
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

        blend_registry = Registry("dev100 round4 BLEND controller")
        blend_registry.register(CONTROLLER_POLICY_ID, blend_factory)
        log(
            f"ARM BLEND START (alpha={ROUND4_ALPHA} — THE round-4 knob, tau={ROUND4_TAU}, f1060078 repair live): <= {ATTEMPT_CORE_CEILING} core "
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
        # Round-4 form (per-round discipline): response A is attempt-1's M0
        # recorded hash for the first sample (hash read, no text); response B
        # is a fresh single-slot re-issue of the byte-identical prompt on the
        # SAME BASE-build service instance attempt 6 flew.
        resend_record: dict[str, object]
        resend_log_offset = server_log_path.stat().st_size
        if contact_total + 1 <= ATTEMPT_CORE_CEILING:
            first_sample = samples[0]
            resend_registry = Registry("dev100 round4 resend controller")
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
            "schema": "saea-dev100-round4-canary-stop-v1",
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
                "round4_core_contacts": contact_total,
                "round4_tool_contacts": meter.count,
                "core_client": flight["core_client"],
            },
            "boundary": (
                "gold never opened; no response read semantically; round 4 is "
                "NOT sealed and NOT scored; the resident service and keepalive "
                "are left up for the coordinator's decision"
            ),
        }
        stop_path = OUT_CHECK_DIR / "round4-canary-stop.json"
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
            "schema": "saea-dev100-round4-sentinel-abort-v1",
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
                "round4_core_contacts": contact_total,
                "round4_tool_contacts": meter.count,
                "core_client": flight["core_client"],
            },
            "boundary": (
                "gold never opened; no response read semantically; round 4 is "
                "NOT sealed and NOT scored; everything durable was flushed at "
                "the trip (partial BLEND buffer into the main sink, canary in "
                "its own sink); the resident service and keepalive are left up "
                "for the coordinator's decision. NOTE: a sentinel trip on the "
                "BASE build would REOPEN the serving question the attempt-6 "
                "landing closed — report verbatim"
            ),
        }
        sentinel_path = OUT_CHECK_DIR / "round4-sentinel-abort.json"
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

    # ---- POST-SEAL scoring: gold + round-0/1/2/3 sealed artifacts open HERE
    # ONE gold opening for the whole round: round-4 BLEND is scored fresh;
    # arm M0 and the BLEND-round-0/1/2/3 per-sample correctness are consumed
    # from the SEALED scoring artifacts (re-hashed against the registration
    # pins immediately before parsing).
    log("ALL ROUND-4 ARMS SEALED — opening devel gold + round-0/1/2/3 sealed scores scoring-side")
    if sha256_file(round0_scores_path) != ROUND0_SCORES_SHA256:
        raise SystemExit("round-0 scores mutated between preflight and scoring; refusing")
    if sha256_file(round0_report_path) != ROUND0_REPORT_SHA256:
        raise SystemExit("round-0 report mutated between preflight and scoring; refusing")
    if sha256_file(round1_scores_path) != ROUND1_SCORES_SHA256:
        raise SystemExit("round-1 scores mutated between preflight and scoring; refusing")
    if sha256_file(round1_report_path) != ROUND1_REPORT_SHA256:
        raise SystemExit("round-1 report mutated between preflight and scoring; refusing")
    if sha256_file(round2_scores_path) != ROUND2_SCORES_SHA256:
        raise SystemExit("round-2 scores mutated between preflight and scoring; refusing")
    if sha256_file(round2_report_path) != ROUND2_REPORT_SHA256:
        raise SystemExit("round-2 report mutated between preflight and scoring; refusing")
    if sha256_file(round2_qvec_path) != ROUND2_QUERY_VECTORS_SHA256:
        raise SystemExit("round-2 query-vectors log mutated between preflight and scoring; refusing")
    if sha256_file(round3_scores_path) != ROUND3_SCORES_SHA256:
        raise SystemExit("round-3 scores mutated between preflight and scoring; refusing")
    if sha256_file(round3_report_path) != ROUND3_REPORT_SHA256:
        raise SystemExit("round-3 report mutated between preflight and scoring; refusing")
    round0_report = json.loads(round0_report_path.read_text(encoding="utf-8"))
    round0_scores = json.loads(round0_scores_path.read_text(encoding="utf-8"))
    round1_report = json.loads(round1_report_path.read_text(encoding="utf-8"))
    round1_scores = json.loads(round1_scores_path.read_text(encoding="utf-8"))
    round2_report = json.loads(round2_report_path.read_text(encoding="utf-8"))
    round2_scores = json.loads(round2_scores_path.read_text(encoding="utf-8"))
    round3_report = json.loads(round3_report_path.read_text(encoding="utf-8"))
    round3_scores = json.loads(round3_scores_path.read_text(encoding="utf-8"))
    sample_ids = {s.sample_id for s in samples}
    m0_rows = round0_scores["M0"]
    r0_blend_rows = round0_scores["BLEND"]
    r1_blend_rows = round1_scores["BLEND_ROUND1"]
    r2_blend_rows = round2_scores["BLEND_ROUND2"]
    r3_blend_rows = round3_scores["BLEND_ROUND3"]
    if set(m0_rows) != sample_ids or set(r0_blend_rows) != sample_ids:
        raise SystemExit("round-0 sealed scores do not cover the DEV-100 split exactly")
    if set(r1_blend_rows) != sample_ids:
        raise SystemExit("round-1 sealed scores do not cover the DEV-100 split exactly")
    if set(r2_blend_rows) != sample_ids:
        raise SystemExit("round-2 sealed scores do not cover the DEV-100 split exactly")
    if set(r3_blend_rows) != sample_ids:
        raise SystemExit("round-3 sealed scores do not cover the DEV-100 split exactly")
    m0_correct = {sid for sid, row in m0_rows.items() if row["correct"]}
    r0_blend_correct = {sid for sid, row in r0_blend_rows.items() if row["correct"]}
    r1_blend_correct = {sid for sid, row in r1_blend_rows.items() if row["correct"]}
    r2_blend_correct = {sid for sid, row in r2_blend_rows.items() if row["correct"]}
    r3_blend_correct = {sid for sid, row in r3_blend_rows.items() if row["correct"]}
    if len(m0_correct) != round0_report["arms"]["M0"]["correct_count"]:
        raise SystemExit("round-0 M0 correct count disagrees with the sealed report")
    if len(r0_blend_correct) != round0_report["arms"]["BLEND"]["correct_count"]:
        raise SystemExit("round-0 BLEND correct count disagrees with the sealed report")
    if sorted(r0_blend_correct - m0_correct) != round0_report["wrong_to_correct_sample_ids"]:
        raise SystemExit("round-0 W->C list disagrees with the sealed report")
    if sorted(m0_correct - r0_blend_correct) != round0_report["correct_to_wrong_sample_ids"]:
        raise SystemExit("round-0 C->W list disagrees with the sealed report")
    if len(r1_blend_correct) != round1_report["arms"]["BLEND_ROUND1"]["correct_count"]:
        raise SystemExit("round-1 BLEND correct count disagrees with the sealed report")
    if sorted(r1_blend_correct - m0_correct) != round1_report["wrong_to_correct_sample_ids"]:
        raise SystemExit("round-1 W->C list disagrees with the sealed report")
    if sorted(m0_correct - r1_blend_correct) != round1_report["correct_to_wrong_sample_ids"]:
        raise SystemExit("round-1 C->W list disagrees with the sealed report")
    if len(r2_blend_correct) != round2_report["arms"]["BLEND_ROUND2"]["correct_count"]:
        raise SystemExit("round-2 BLEND correct count disagrees with the sealed report")
    if sorted(r2_blend_correct - m0_correct) != round2_report["wrong_to_correct_sample_ids"]:
        raise SystemExit("round-2 W->C list disagrees with the sealed report")
    if sorted(m0_correct - r2_blend_correct) != round2_report["correct_to_wrong_sample_ids"]:
        raise SystemExit("round-2 C->W list disagrees with the sealed report")
    if len(r3_blend_correct) != round3_report["arms"]["BLEND_ROUND3"]["correct_count"]:
        raise SystemExit("round-3 BLEND correct count disagrees with the sealed report")
    if sorted(r3_blend_correct - m0_correct) != round3_report["wrong_to_correct_sample_ids"]:
        raise SystemExit("round-3 W->C list disagrees with the sealed report")
    if sorted(m0_correct - r3_blend_correct) != round3_report["correct_to_wrong_sample_ids"]:
        raise SystemExit("round-3 C->W list disagrees with the sealed report")
    # Round-2 per-sample DIRECT-decode response hashes (attribution
    # authority for the projection reconciliation: the alpha-.45 projection
    # is exact GIVEN round-2's logged responses). query-vectors.jsonl
    # records the sha256 of each embedded direct-answer text under
    # contact_id "query:<sid>".
    r2_direct_sha: dict[str, str] = {}
    with round2_qvec_path.open(encoding="utf-8") as qvec_handle:
        for line in qvec_handle:
            record = json.loads(line)
            contact_id = str(record.get("contact_id", ""))
            if contact_id.startswith("query:"):
                r2_direct_sha[contact_id[len("query:"):]] = str(record["text_sha256"])
    if set(r2_direct_sha) != sample_ids:
        raise SystemExit("round-2 query-vectors log does not cover the split exactly")
    # Round-3 per-sample DIRECT-decode response hashes (round-over-round
    # serving descriptive; recorded in the sealed round-3 scoring artifact).
    r3_direct_sha: dict[str, str] = {
        sid: str(row.get("direct_response_sha256"))
        for sid, row in r3_blend_rows.items()
    }
    r3_final_sha: dict[str, str] = {
        sid: str(row.get("response_sha256")) for sid, row in r3_blend_rows.items()
    }
    log(
        "round-0/1/2/3 sealed authorities parsed and cross-checked: M0 "
        f"{len(m0_correct)}/100, BLEND-r0 {len(r0_blend_correct)}/100, "
        f"BLEND-r1 {len(r1_blend_correct)}/100, BLEND-r2 "
        f"{len(r2_blend_correct)}/100, BLEND-r3 {len(r3_blend_correct)}/100, "
        "movement lists equal, r2 + r3 direct hashes indexed for attribution"
    )

    scorer = SlurpAdapter(lock, root, repo_root=REPO)
    sample_by_id = {sample.sample_id: sample for sample in samples}
    scores: dict[str, dict[str, dict[str, object]]] = {}

    blend_summary = arm_results["BLEND"]
    blend_scores: dict[str, dict[str, object]] = {}
    for result in blend_summary.results:
        metrics = dict(scorer.score(sample_by_id[result.sample_id], result.final_response_text))
        controller = blend_controllers.get(result.sample_id)
        blend_scores[result.sample_id] = {
            "correct": bool(metrics.get("scenario_action_exact")),
            "scenario_exact": bool(metrics.get("scenario_exact")),
            "action_exact": bool(metrics.get("action_exact")),
            "parsed": metrics.get("parsed"),
            "slot_f1_exact_f1": metrics.get("slot_f1_exact_f1"),
            "contacts": len(result.contacts),
            "response_sha256": sha256_text(result.final_response_text),
            "winner_label_present": winner_labels.get(result.sample_id) is not None,
            "direct_response_sha256": (
                controller.direct_response_sha256 if controller is not None else None
            ),
            "direct_label_recovered": (
                controller.direct_label_recovered if controller is not None else None
            ),
        }
    if set(blend_scores) != sample_ids:
        raise SystemExit("round-4 BLEND results do not cover the split")
    scores["BLEND_ROUND4"] = blend_scores
    scores["M0_SEALED_ROUND0"] = {
        sid: dict(row) for sid, row in sorted(m0_rows.items())
    }
    scores["BLEND_ROUND3_SEALED"] = {
        sid: dict(row) for sid, row in sorted(r3_blend_rows.items())
    }
    scores["BLEND_ROUND2_SEALED"] = {
        sid: dict(row) for sid, row in sorted(r2_blend_rows.items())
    }

    # Cross-attempt direct-contact byte agreement (serving descriptive) —
    # vs attempt-1's M0 hashes (the campaign-long series), vs round-2's
    # flown directs (the projection's given responses; the attribution
    # channel for the reconciliation below) AND vs round-3's flown directs
    # (the round-over-round channel).
    direct_agreement = {
        sample_id: (
            controller.direct_response_sha256 is not None
            and controller.direct_response_sha256 == a1_m0_response_sha[sample_id]
        )
        for sample_id, controller in blend_controllers.items()
    }
    direct_agree_count = sum(1 for same in direct_agreement.values() if same)
    direct_agreement_vs_r2 = {
        sample_id: (
            controller.direct_response_sha256 is not None
            and controller.direct_response_sha256 == r2_direct_sha[sample_id]
        )
        for sample_id, controller in blend_controllers.items()
    }
    direct_agree_vs_r2_count = sum(1 for same in direct_agreement_vs_r2.values() if same)
    direct_changed_vs_r2 = sorted(
        sid for sid, same in direct_agreement_vs_r2.items() if not same
    )
    direct_agreement_vs_r3 = {
        sample_id: (
            controller.direct_response_sha256 is not None
            and controller.direct_response_sha256 == r3_direct_sha[sample_id]
        )
        for sample_id, controller in blend_controllers.items()
    }
    direct_agree_vs_r3_count = sum(1 for same in direct_agreement_vs_r3.values() if same)
    direct_changed_vs_r3 = sorted(
        sid for sid, same in direct_agreement_vs_r3.items() if not same
    )
    direct_label_recovered_count = sum(
        1
        for controller in blend_controllers.values()
        if controller.direct_label_recovered is not None
    )

    outputs_path = run_dir / "round4-outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as sink:
        for result in blend_summary.results:
            sink.write(
                json.dumps(
                    {
                        "arm": "BLEND_ROUND4",
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
    r4_correct = {sid for sid, row in blend_scores.items() if row["correct"]}
    wrong_to_correct = sorted(r4_correct - m0_correct)
    correct_to_wrong = sorted(m0_correct - r4_correct)
    r3_w2c = set(round3_report["wrong_to_correct_sample_ids"])
    r3_c2w = set(round3_report["correct_to_wrong_sample_ids"])
    r2_w2c = set(round2_report["wrong_to_correct_sample_ids"])
    r2_c2w = set(round2_report["correct_to_wrong_sample_ids"])
    retained_primary_ids = sorted(
        sid for sid, row in blend_scores.items() if row["contacts"] == 1
    )
    dispatched_count = sum(1 for row in blend_scores.values() if row["contacts"] == 2)
    response_changed_vs_r2 = sorted(
        sid
        for sid in sample_ids
        if blend_scores[sid]["response_sha256"] != r2_blend_rows[sid]["response_sha256"]
    )
    response_changed_vs_r3 = sorted(
        sid
        for sid in sample_ids
        if blend_scores[sid]["response_sha256"] != r3_final_sha[sid]
    )
    audio_seconds_metered = None
    cost = flight["core_client"]["cost"]
    if isinstance(cost, Mapping):
        audio_seconds_metered = cost.get("audio_seconds_used")

    # ---- PROJECTION RECONCILIATION (the registered falsifiable prediction)
    # The registered alpha-.45 projection is ROUND-2-based (its given inputs
    # are round-2's logged responses) and defines a full per-sample expected
    # outcome: every sample keeps its round-2 outcome EXCEPT the 11
    # projected heals (wrong -> correct), the 4 projected lost repairs
    # (correct -> wrong) and the 2 projected gains (wrong -> correct).
    # Deviations are attributed per sample: a sample whose FLOWN
    # direct-decode response differs byte-wise from round-2's logged direct
    # (the projection's given input) sits in the DOCUMENTED
    # direct-byte-variance channel; a dispatched sample with an unchanged
    # direct but a changed evidence-decode final sits in the
    # evidence-decode-byte-variance channel; anything else is a
    # mechanism-level miss (would falsify the projection's arithmetic).
    projected_correct = (
        (r2_blend_correct - set(PROJECTION["repairs_lost"]))
        | set(PROJECTION["damage_healed"])
        | set(PROJECTION["gains_outside_both_groups"])
    )
    if len(projected_correct) != int(PROJECTION["projected_correct_total"]):
        raise SystemExit(
            f"registered projection reconstructs to {len(projected_correct)} "
            f"correct, not the registered {PROJECTION['projected_correct_total']}"
        )
    projection_named = {
        "damage_healed": PROJECTION["damage_healed"],
        "still_damaged": PROJECTION["still_damaged"],
        "repairs_lost": PROJECTION["repairs_lost"],
        "gains_outside_both_groups": PROJECTION["gains_outside_both_groups"],
    }
    named_outcomes: dict[str, dict[str, object]] = {}
    for group, members in projection_named.items():
        for sid in members:
            expected_correct = group in ("damage_healed", "gains_outside_both_groups")
            named_outcomes[sid] = {
                "projected_group": group,
                "projected_correct": expected_correct,
                "flown_correct": sid in r4_correct,
                "hit": (sid in r4_correct) == expected_correct,
                "retain_primary_flown": sid in retained_primary_ids,
                "direct_changed_vs_r2": sid in direct_changed_vs_r2,
            }
    per_sample_misses: dict[str, dict[str, object]] = {}
    for sid in sorted(sample_ids):
        flown = sid in r4_correct
        projected = sid in projected_correct
        if flown == projected:
            continue
        if sid in direct_changed_vs_r2:
            attribution = (
                "direct-byte-variance channel (the flown direct decode "
                "differs byte-wise from round-2's logged direct — the "
                "projection's given input; DOCUMENTED variance source)"
            )
        elif (
            blend_scores[sid]["contacts"] == 2
            and blend_scores[sid]["response_sha256"]
            != r2_blend_rows[sid]["response_sha256"]
        ):
            attribution = (
                "evidence-decode-byte-variance channel (direct unchanged, "
                "evidence-decode final differs byte-wise from round-2's)"
            )
        else:
            attribution = (
                "MECHANISM-LEVEL MISS (unexplained by the documented "
                "variance channels — falsifies the projection arithmetic "
                "for this sample)"
            )
        per_sample_misses[sid] = {
            "projected_correct": projected,
            "flown_correct": flown,
            "retain_primary_flown": sid in retained_primary_ids,
            "direct_changed_vs_r2": sid in direct_changed_vs_r2,
            "attribution": attribution,
        }
    mechanism_miss_count = sum(
        1
        for row in per_sample_misses.values()
        if str(row["attribution"]).startswith("MECHANISM")
    )
    retained_unchanged_direct = sum(
        1 for sid in retained_primary_ids if sid not in direct_changed_vs_r2
    )
    retained_changed_direct = len(retained_primary_ids) - retained_unchanged_direct
    projection_reconciliation = {
        "registered_projection": dict(PROJECTION),
        "projection_source": (
            "docs/readiness/2026-08-24-dev100-damage-channel-analysis.md "
            "section 7 row label-identity-repair-alpha-045 / section 9 "
            "closing paragraph (exact offline replay over the sealed "
            "round-2 trajectories at alpha .45; per-sample membership "
            "re-derived model-free pre-registration, derivation receipt "
            "alpha045-projection-derivation.json sha256 250a7034…3dc0a; "
            "registered verbatim in the campaign row BEFORE takeoff WITH "
            "the round-3-quantified ~+/-4-sample direct-byte-variance "
            "caveat: credible flown band ~70-74)"
        ),
        "projected_correct_total": len(projected_correct),
        "flown_correct_total": len(r4_correct),
        "aggregate_hit": len(r4_correct) == len(projected_correct),
        "per_sample_hits": sum(
            1 for sid in sample_ids if (sid in r4_correct) == (sid in projected_correct)
        ),
        "per_sample_misses": {sid: per_sample_misses[sid] for sid in sorted(per_sample_misses)},
        "mechanism_level_miss_count": mechanism_miss_count,
        "named_sample_outcomes": {sid: named_outcomes[sid] for sid in sorted(named_outcomes)},
        "retain_primary": {
            "projected_count": int(PROJECTION["retain_primary_projected_count"]),
            "realized_count": len(retained_primary_ids),
            "realized_with_unchanged_direct": retained_unchanged_direct,
            "realized_with_changed_direct": retained_changed_direct,
            "note": (
                "on a sample whose flown direct response is byte-identical "
                "to round-2's, the retain decision is the exact offline "
                "replay decision (deterministic normalizer + bit-identical "
                "embedding of identical text) — so any realized-vs-projected "
                "membership deviation must live entirely inside the "
                "changed-direct set"
            ),
        },
        "direct_agreement_vs_round2": {
            "agree_count": direct_agree_vs_r2_count,
            "changed_sample_ids": direct_changed_vs_r2,
        },
        "direct_agreement_vs_round3": {
            "agree_count": direct_agree_vs_r3_count,
            "changed_sample_ids": direct_changed_vs_r3,
        },
    }

    # ---- preregistered stopping rule, evaluated AT THE SEAL ---------------
    # Rule (preregistration section 3): CONVERGED when the best arm's
    # accuracy changes < 1 sample across two consecutive rounds with zero
    # correct->wrong regression growth; FALSIFIED when no knob setting beats
    # M0 direct after 3 completed rounds; hard cap 6. Round 3's +2 delta
    # did NOT qualify, so the streak is EMPTY entering round 4: round 4 can
    # at most BANK the first of two needed qualifying rounds; CONVERGENCE
    # CANNOT FIRE AT THIS SEAL (it would additionally require round 5 to
    # qualify). Round 4 is the 5th of the hard cap 6. The formal statement
    # belongs to the coordinator; this launcher states the arithmetic fact.
    delta_r4_vs_r3 = len(r4_correct) - len(r3_blend_correct)
    c2w_growth_vs_r3 = len(correct_to_wrong) - len(r3_c2w)
    round4_qualifies = abs(delta_r4_vs_r3) < 1 and c2w_growth_vs_r3 <= 0
    convergence_fires = False  # structurally: the streak is empty entering round 4
    beats_direct = max(
        len(r4_correct),
        len(r3_blend_correct),
        len(r2_blend_correct),
        len(r1_blend_correct),
        len(r0_blend_correct),
    ) > len(m0_correct)

    # ---- prompt-reuse analysis (owner directive at round-2 registration:
    # prefix-cache optimality is a first-class metric) -----------------------
    # Computed from the durable server log's per-request records ONLY —
    # content-free token counts; no behavior change, no extra contact.
    # declared prompt tokens per request = release n_tokens - generation
    # tokens + a fixed per-request offset CALIBRATED against the client-side
    # declared total (cost.prompt_tokens_total covers exactly this attempt's
    # requests); evaluated prompt tokens = the print_timing prompt-eval row
    # (tokens actually processed after the slot prompt-cache prefix hit);
    # skipped = declared - evaluated.
    with server_log_path.open("rb") as log_handle:
        log_handle.seek(canary_log_offset)
        canary_window_bytes = log_handle.read(blend_log_offset - canary_log_offset)
        blend_window_bytes = log_handle.read(resend_log_offset - blend_log_offset)
        resend_window_bytes = log_handle.read()
    canary_requests = parse_slot_requests(canary_window_bytes)
    blend_requests = parse_slot_requests(blend_window_bytes)
    resend_requests = parse_slot_requests(resend_window_bytes)
    all_requests = canary_requests + blend_requests + resend_requests
    prompt_tokens_total_client = (
        cost.get("prompt_tokens_total") if isinstance(cost, Mapping) else None
    )
    sum_release_minus_gen = sum(
        row["release_n_tokens"] - row["generation_tokens"] for row in all_requests
    )
    per_request_offset: object = "UNDETERMINED"
    if isinstance(prompt_tokens_total_client, int) and all_requests:
        offset_delta = prompt_tokens_total_client - sum_release_minus_gen
        if (
            offset_delta % len(all_requests) == 0
            and abs(offset_delta) <= 2 * len(all_requests)
        ):
            per_request_offset = offset_delta // len(all_requests)
    offset_int = per_request_offset if isinstance(per_request_offset, int) else 0

    def declared_tokens(row: Mapping[str, int]) -> int:
        return row["release_n_tokens"] - row["generation_tokens"] + offset_int

    def reuse_stats(
        rows: Sequence[Mapping[str, int]],
    ) -> tuple[dict[str, object], list[int]]:
        declared = [declared_tokens(row) for row in rows]
        evaluated = [row["prompt_eval_tokens"] for row in rows]
        skipped = [d - e for d, e in zip(declared, evaluated)]
        total_declared = sum(declared)
        total_evaluated = sum(evaluated)
        stats: dict[str, object] = {
            "requests": len(rows),
            "declared_prompt_tokens": total_declared,
            "evaluated_prompt_tokens": total_evaluated,
            "skipped_prompt_tokens": total_declared - total_evaluated,
            "evaluation_ratio": (
                round(total_evaluated / total_declared, 6) if total_declared else None
            ),
            "reuse_ratio": (
                round(1.0 - total_evaluated / total_declared, 6)
                if total_declared
                else None
            ),
            "skipped_tokens_distribution": token_count_distribution(skipped),
            "evaluated_tokens_distribution": token_count_distribution(evaluated),
            "declared_tokens_distribution": token_count_distribution(declared),
        }
        return stats, skipped

    DIRECT_CLASS_MAX_DECLARED = 2000  # direct-decode envelope is 1,819 worst case
    blend_direct_rows = [
        row for row in blend_requests if declared_tokens(row) <= DIRECT_CLASS_MAX_DECLARED
    ]
    blend_evidence_rows = [
        row for row in blend_requests if declared_tokens(row) > DIRECT_CLASS_MAX_DECLARED
    ]
    classification_clean = (
        len(blend_direct_rows) == 100 and len(blend_evidence_rows) == dispatched_count
    )
    if not classification_clean and len(blend_requests) == 100 + dispatched_count:
        ordered_by_declared = sorted(blend_requests, key=declared_tokens)
        blend_direct_rows = ordered_by_declared[:100]
        blend_evidence_rows = ordered_by_declared[100:]
    overall_reuse, _ = reuse_stats(all_requests)
    blend_direct_reuse, _ = reuse_stats(blend_direct_rows)
    blend_evidence_reuse, evidence_skipped = reuse_stats(blend_evidence_rows)
    canary_reuse, _ = reuse_stats(canary_requests)
    resend_reuse, _ = reuse_stats(resend_requests)
    two_contact_results = [
        result for result in blend_summary.results if len(result.contacts) == 2
    ]
    same_slot_trajectories = sum(
        1
        for result in two_contact_results
        if result.contacts[0].slot_id == result.contacts[1].slot_id
    )
    evidence_skipped_ge_1700 = sum(1 for s in evidence_skipped if s >= 1700)
    evidence_skipped_ge_1000 = sum(1 for s in evidence_skipped if s >= 1000)
    evidence_skipped_lt_100 = sum(1 for s in evidence_skipped if s < 100)
    evidence_reuse_ratio = blend_evidence_reuse.get("reuse_ratio")
    if isinstance(evidence_reuse_ratio, float) and evidence_reuse_ratio >= 0.5:
        reuse_verdict = (
            "ACTIVE: the slot prompt cache is doing real work on the evidence "
            "contact class (reuse ratio >= 0.5)"
        )
    elif isinstance(evidence_reuse_ratio, float) and evidence_reuse_ratio <= 0.05:
        reuse_verdict = (
            "NEAR-ZERO: the evidence contacts re-evaluate essentially their "
            "full prompts — this becomes a later-round optimization target per "
            "the owner directive"
        )
    else:
        reuse_verdict = (
            "PARTIAL: some prefix reuse on the evidence contact class, well "
            "short of the common-prefix ceiling"
        )
    prompt_reuse_section = {
        "directive": (
            "owner directive at round-2 registration: prefix-cache optimality "
            "is a first-class metric; measured from durable server-log "
            "per-request records only (content-free token counts), no "
            "behavior change"
        ),
        "method": (
            "per request: declared = release n_tokens - generation tokens + "
            "calibrated fixed offset; evaluated = print_timing prompt-eval "
            "tokens (post-prefix-cache); skipped = declared - evaluated. "
            "Windows split by the tracked server-log offsets: canary / BLEND "
            "/ resend. BLEND contact classes split at declared <= "
            f"{DIRECT_CLASS_MAX_DECLARED} (direct envelope 1,819)"
        ),
        "declared_offset_calibration": {
            "client_prompt_tokens_total": prompt_tokens_total_client,
            "sum_release_n_tokens_minus_generation": sum_release_minus_gen,
            "request_count_parsed": len(all_requests),
            "per_request_offset": per_request_offset,
        },
        "classification_clean_by_threshold": classification_clean,
        "overall": overall_reuse,
        "by_class": {
            "blend_direct_contact0": blend_direct_reuse,
            "blend_evidence_contact1": blend_evidence_reuse,
            "canary_direct_single_slot": canary_reuse,
            "resend_direct_single_slot": resend_reuse,
        },
        "within_trajectory": {
            "two_contact_trajectories": len(two_contact_results),
            "evidence_contact_same_server_slot_as_direct": same_slot_trajectories,
            "evidence_contact_different_server_slot": (
                len(two_contact_results) - same_slot_trajectories
            ),
            "expected_common_prefix_tokens": (
                "~1,700+ (system + task contract + speech packet + query)"
            ),
            "evidence_skipped_ge_1700_tokens": evidence_skipped_ge_1700,
            "evidence_skipped_ge_1000_tokens": evidence_skipped_ge_1000,
            "evidence_skipped_lt_100_tokens": evidence_skipped_lt_100,
            "note": (
                "the slot prompt cache holds the LAST prompt per server slot, "
                "so an evidence contact reaching the slot that just served a "
                "prompt sharing its prefix (its own trajectory's direct "
                "contact, or any request sharing the system+contract prefix) "
                "skips that prefix; slot ids per contact come from the "
                "client-side contact records (the runner pins id_slot)"
            ),
        },
        "verdict": reuse_verdict,
    }

    round_report = {
        "schema": "saea-dev100-round4-report-v1",
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
            "ROUND-4 registration (registered variable: the SINGLE knob alpha "
            "0.55 -> 0.45, the first alpha move since the f1060078 repair made "
            "the protect-direct term live; every other knob byte-equal to the "
            "round-3 cell and the repair asserted as an invariant; the alpha-"
            ".45 damage-channel projection registered verbatim as the "
            "falsifiable prediction WITH the round-3-quantified direct-byte-"
            "variance caveat, credible flown band ~70-74; FRESH run-cumulative "
            "successor plan 1,600 calls / 4,300 audio-s over the 1,274 / "
            "3,408.06 AttemptStore-verified durable spend; sealed round-0 "
            "through round-3 authorities pinned byte-wise; sentinel + micro-run "
            "trace isolation + Windows-side GPU sampling + clock sampling "
            "carried flight-proven from rounds 1-3)"
        ),
        "refused_takeoffs": REFUSED_TAKEOFFS,
        "round4_variable": flight.get("round4_variable"),
        "round0_citation": {
            "report_path": ROUND0_REPORT_RELPATH,
            "report_sha256": ROUND0_REPORT_SHA256,
            "scores_sha256": ROUND0_SCORES_SHA256,
            "sealed_results": "M0 48/100; BLEND(alpha .60, tau .5) 63/100; W->C 26; C->W 11; evidence fired 100/100",
        },
        "round1_citation": {
            "report_path": ROUND1_REPORT_RELPATH,
            "report_sha256": ROUND1_REPORT_SHA256,
            "scores_sha256": ROUND1_SCORES_SHA256,
            "sealed_results": (
                "BLEND(alpha .60, tau .65) 63/100; W->C 26; C->W 11; evidence "
                "fired 100/100; tau proven INERT on [0.5, 0.65]; plus the "
                "disclosed duplicate-takeoff addendum (29 core / 17 tool / "
                "68.03 audio-s dead spend, never read)"
            ),
        },
        "round2_citation": {
            "report_path": ROUND2_REPORT_RELPATH,
            "report_sha256": ROUND2_REPORT_SHA256,
            "scores_sha256": ROUND2_SCORES_SHA256,
            "query_vectors_sha256": ROUND2_QUERY_VECTORS_SHA256,
            "sealed_results": (
                "BLEND(alpha .55, tau .65) 65/100; W->C 28; C->W 11 "
                "(byte-equal list to round 1); evidence fired 100/100; "
                "retain-primary 0 (the direct term was structurally dead "
                "pre-repair); direct byte-agreement vs attempt-1 M0 75/100"
            ),
        },
        "round3_citation": {
            "report_path": ROUND3_REPORT_RELPATH,
            "report_sha256": ROUND3_REPORT_SHA256,
            "scores_sha256": ROUND3_SCORES_SHA256,
            "sealed_results": (
                "BLEND(alpha .55, tau .65, f1060078 repair) 67/100; W->C 24; "
                "C->W 5 (collapsed from 11); retain-primary 52/100 (first "
                "nonzero); direct-label recovered 61/100; projection "
                "reconciliation 96/100 per-sample hits, all 4 misses in the "
                "direct-byte-variance channel; direct byte-agreement vs "
                "attempt-1 M0 81/100, vs round-2 79/100"
            ),
        },
        "hosting": dict(HOSTING),
        "config_hash": composed.config_hash,
        "server_np": server_np,
        "decoder_session_receipt_sha256": measured_receipt,
        "gpu_preflight": flight["gpu_preflight"],
        "round4_knobs": {
            "alpha": ROUND4_ALPHA,
            "rank_weight_id": "rrf",
            "evidence_variant": "rank+prior+agreement",
            "tau": ROUND4_TAU,
            "top_k_per_dimension": ROUND4_TOP_K,
            "fusion": {"m": ROUND4_FUSE.m, "c": ROUND4_FUSE.c, "l": ROUND4_FUSE.top_l},
            "rank_weights": {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2},
            "prior_source": "train",
            "m11_pair_boundary_stage": False,
            "value_vectors": "SEALED (never loaded)",
            "percept_admission": "facet-side",
            "knob_change_vs_round3": {
                "single_variable": True,
                "knobs_changed": "alpha ONLY: 0.55 -> 0.45; every other knob is byte-equal to the sealed round-3 cell and the f1060078 repair is asserted as an invariant",
                "variable": (
                    "KNOB: alpha 0.55 -> 0.45 — the first alpha move since "
                    "the f1060078 label-identity binding repair made the "
                    "(1 - alpha) protect-direct term live. At alpha .45 the "
                    "direct term (0.55) out-scores even a fully-concentrated "
                    "fused mass (alpha * 1.0 = 0.45), so retain-primary "
                    "fires on EVERY direct-label-recovered sample — the "
                    "damage-channel analysis proved alpha inert pre-repair "
                    "(round 2) and live post-repair"
                ),
                "rationale": (
                    "the standing round-4 candidate from the round-3 seal "
                    "(the live-alpha re-sweep): the alpha-.45 cell of the "
                    "damage-channel analysis heals ALL 11 of the old damage "
                    "set (vs 6 at .55) at the cost of 4 repairs, projecting "
                    "74/100 over round-2 bytes with zero offline unknowns; "
                    "round 3 quantified the direct-byte-variance channel at "
                    "~+/-4 samples, so the credible flown band is ~70-74"
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
            "BLEND_ROUND4": {
                "accuracy_scenario_action_exact": len(r4_correct) / 100.0,
                "correct_count": len(r4_correct),
                "contacts": sum(row["contacts"] for row in blend_scores.values()),
                "evidence_contact_dispatched_samples": dispatched_count,
                "retain_primary_samples": len(retained_primary_ids),
                "direct_label_recovered_samples": direct_label_recovered_count,
                "parsed_count": sum(1 for row in blend_scores.values() if row["parsed"]),
                "embedding_tool_contacts": flight["embedding_accounting"].get("tool_contacts"),
            },
            "BLEND_ROUND3_FOR_REFERENCE": {
                "accuracy_scenario_action_exact": len(r3_blend_correct) / 100.0,
                "correct_count": len(r3_blend_correct),
                "source": "ROUND-3 SEALED per-sample scores",
            },
            "BLEND_ROUND2_FOR_REFERENCE": {
                "accuracy_scenario_action_exact": len(r2_blend_correct) / 100.0,
                "correct_count": len(r2_blend_correct),
                "source": "ROUND-2 SEALED per-sample scores",
            },
            "BLEND_ROUND1_FOR_REFERENCE": {
                "accuracy_scenario_action_exact": len(r1_blend_correct) / 100.0,
                "correct_count": len(r1_blend_correct),
                "source": "ROUND-1 SEALED per-sample scores",
            },
            "BLEND_ROUND0_FOR_REFERENCE": {
                "accuracy_scenario_action_exact": len(r0_blend_correct) / 100.0,
                "correct_count": len(r0_blend_correct),
                "source": "ROUND-0 SEALED per-sample scores",
            },
        },
        "wrong_to_correct_sample_ids": wrong_to_correct,
        "correct_to_wrong_sample_ids": correct_to_wrong,
        "vs_round3_blend": {
            "net_delta_correct_samples": delta_r4_vs_r3,
            "round3_correct_now_wrong": sorted(r3_blend_correct - r4_correct),
            "round3_wrong_now_correct": sorted(r4_correct - r3_blend_correct),
            "round3_w2c_retained": sorted(r3_w2c & r4_correct),
            "round3_w2c_lost": sorted(r3_w2c - r4_correct),
            "round3_c2w_repaired": sorted(r3_c2w & r4_correct),
            "round3_c2w_still_wrong": sorted(r3_c2w - r4_correct),
            "final_response_sha_changed_sample_ids": response_changed_vs_r3,
            "final_response_sha_changed_count": len(response_changed_vs_r3),
            "note": (
                "per-sample vs the round-3 sealed BLEND arm (alpha .55, tau "
                ".65, repair live) — the PRIMARY round-over-round comparison "
                "and the stopping-rule baseline. round3_c2w_repaired counts "
                "round-3 damage samples correct at alpha .45 (the alpha-.45 "
                "projection expects all 5 of round-3's C->W to heal); "
                "round3_w2c_lost counts round-3 repairs lost to the stronger "
                "protect-direct term"
            ),
        },
        "vs_round2_blend": {
            "net_delta_correct_samples": len(r4_correct) - len(r2_blend_correct),
            "round2_correct_now_wrong": sorted(r2_blend_correct - r4_correct),
            "round2_wrong_now_correct": sorted(r4_correct - r2_blend_correct),
            "round2_w2c_retained": sorted(r2_w2c & r4_correct),
            "round2_w2c_lost": sorted(r2_w2c - r4_correct),
            "round2_c2w_repaired": sorted(r2_c2w & r4_correct),
            "round2_c2w_still_wrong": sorted(r2_c2w - r4_correct),
            "final_response_sha_changed_sample_ids": response_changed_vs_r2,
            "final_response_sha_changed_count": len(response_changed_vs_r2),
            "note": (
                "per-sample vs the round-2 sealed BLEND arm (alpha .55, tau "
                ".65, pre-repair) — the alpha-.45 PROJECTION's baseline "
                "(secondary; the stopping rule reads vs_round3_blend). "
                "round2_c2w_repaired counts round-2 damage samples correct "
                "at alpha .45 with the repair (projected: 11 of 11); "
                "round2_w2c_lost counts round-2 repairs lost (projected: 4)"
            ),
        },
        "projection_reconciliation": projection_reconciliation,
        "blend_decisions": {
            "evidence_contact_dispatched_samples": dispatched_count,
            "retain_primary_samples": len(retained_primary_ids),
            "retained_primary_sample_ids": retained_primary_ids,
            "direct_label_recovered_samples": direct_label_recovered_count,
            "winner_label_present_samples": sum(
                1 for label in winner_labels.values() if label is not None
            ),
            "note": (
                "winner_label is set only on trajectories that dispatched "
                "the evidence contact; a retain-primary trajectory stops at "
                "1 contact with the direct response as final and no winner "
                "label (rails.kb_policy retain path). direct_label_recovered "
                "counts samples where the REPAIRED normalizer recovered a "
                "label facet from the flown direct answer (analysis "
                "expectation over the round-2 responses: 64/100; round 3 "
                "flew 61/100). At alpha .45 EVERY direct-label-recovered "
                "sample retains primary, so retain-primary should equal "
                "direct_label_recovered exactly"
            ),
        },
        "cross_attempt_direct_agreement": {
            "detail": (
                "per-sample sha256 equality between this round's BLEND "
                "direct-decode responses and attempt-1's reused M0 responses "
                "(byte-identical prompts; 8-slot concurrent serving "
                "descriptive, computed hash-to-hash; r0a6 measured 78/100, "
                "r1 79/100, r2 75/100, r3 81/100 on the same service)"
            ),
            "agree_count": direct_agree_count,
            "disagree_sample_ids": sorted(
                sample_id for sample_id, same in direct_agreement.items() if not same
            ),
            "vs_round2_agree_count": direct_agree_vs_r2_count,
            "vs_round2_changed_sample_ids": direct_changed_vs_r2,
            "vs_round3_agree_count": direct_agree_vs_r3_count,
            "vs_round3_changed_sample_ids": direct_changed_vs_r3,
        },
        "deviations": [
            {
                "id": "m0-arm-consumed-from-round0-seal",
                "kind": "successor semantics, registered pre-takeoff in the campaign row",
                "detail": (
                    "Arm M0 was not re-flown in round 4: its per-sample "
                    "correctness comes from round-0's sealed scoring artifact "
                    f"(round0-scores.json, sha256 {ROUND0_SCORES_SHA256}), "
                    "cross-checked against the sealed round-0 report "
                    f"({ROUND0_REPORT_SHA256}) at the single scoring-side "
                    "opening. Zero new spend for the arm; the same M0 baseline "
                    "serves every round per the campaign design."
                ),
            },
            {
                "id": "blend-r3-and-r2-arms-consumed-from-their-seals",
                "kind": "successor semantics, registered pre-takeoff in the campaign row",
                "detail": (
                    "The BLEND-round-3 reference arm (the round-over-round "
                    "and stopping-rule baseline) was not re-flown: its "
                    "per-sample correctness comes from round-3's sealed "
                    "scoring artifact (round3-scores.json, sha256 "
                    f"{ROUND3_SCORES_SHA256}), cross-checked against the "
                    f"sealed round-3 report ({ROUND3_REPORT_SHA256}) at the "
                    "single scoring-side opening; the BLEND-round-2 "
                    "reference arm (the alpha-.45 projection's baseline) "
                    "likewise from round-2's sealed artifacts "
                    f"(scores {ROUND2_SCORES_SHA256}, report "
                    f"{ROUND2_REPORT_SHA256}); round-1/round-0 reference "
                    "aggregates likewise from their sealed artifacts. Zero "
                    "new spend for these arms."
                ),
            },
            {
                "id": "gpu-sampler-windows-binary",
                "kind": "telemetry plumbing fix, carried flight-proven from round 2",
                "detail": (
                    "The in-flight GPU/VRAM sampler polls the Windows-side "
                    "/mnt/c/Windows/System32/nvidia-smi.exe (5 s cadence) "
                    "instead of the WSL bridge binary that timed out under "
                    "decode load in round 1 and self-disabled. Round 2 proved "
                    "it in flight (64 samples, zero probe failures). "
                    "Fail-tolerant semantics unchanged (degrades to "
                    "NOT_AVAILABLE); no science knob touched."
                ),
            },
        ],
        "spend_vs_ceilings": {
            "round4": {
                "core_contacts": {"used": contact_total, "attempt_ceiling": ATTEMPT_CORE_CEILING},
                "embedding_tool_contacts": {"used": meter.count, "attempt_ceiling": ATTEMPT_TOOL_CEILING},
                "metered_audio_seconds": {"used": audio_seconds_metered},
                "gpu_active_hours_contact_basis": flight["gpu_active_hours_contact_basis"],
            },
            "cumulative_plan_declaration": {
                "planned_model_calls_run_cumulative": PLANNED_MODEL_CALLS,
                "planned_speech_audio_seconds_run_cumulative": PLANNED_AUDIO_SECONDS,
                "note": (
                    "FRESH successor plan (the round-2 1,200 / 3,100 plan is "
                    "nearly exhausted at 1,123 / 3,005.33 durable); "
                    "run-cumulative per core.model.adapter's enforcement "
                    "across all attempts of the run id (fresh sibling read "
                    "per request); covers the 1,123 calls / "
                    "3,005.330937499999 audio-s AttemptStore-verified durable "
                    "for rounds 0-2 plus this round's worst case"
                ),
            },
            "campaign_cumulative_incl_prior_rounds": {
                "core_contacts": PRIOR_CORE_CONTACTS + contact_total,
                "embedding_tool_contacts": PRIOR_TOOL_CONTACTS + meter.count,
                "metered_audio_seconds": (
                    PRIOR_AUDIO_SECONDS + audio_seconds_metered
                    if isinstance(audio_seconds_metered, (int, float))
                    else None
                ),
                "note": (
                    "rounds 0-3 durable cumulative incl. the disclosed "
                    "round-1 duplicate (AttemptStore re-sum: 1,274 core, 623 "
                    "tool, 3,408.0633749999993 audio-s) plus this round-4 "
                    "attempt"
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
            "completed_rounds_after_this": 5,
            "streak_state_entering_round4": (
                "EMPTY — round 3's +2 delta did not qualify, so no qualifying "
                "round is banked; two fresh consecutive qualifying rounds are "
                "required"
            ),
            "round4_delta_vs_round3": delta_r4_vs_r3,
            "round4_c2w_vs_m0": len(correct_to_wrong),
            "round3_c2w_vs_m0": len(r3_c2w),
            "c2w_growth_vs_round3": c2w_growth_vs_r3,
            "round4_qualifies": round4_qualifies,
            "banks_first_qualifying_round": round4_qualifies,
            "convergence_fires": convergence_fires,
            "beats_direct": beats_direct,
            "note": (
                "evaluated AT THIS SEAL per the flight brief: with the "
                "streak EMPTY entering round 4, a qualifying round 4 (|delta "
                "vs r3| < 1 sample AND zero C->W growth) BANKS the first of "
                "two needed qualifying rounds — CONVERGENCE CANNOT FIRE at "
                "this seal regardless; it would require round 5 to also "
                "qualify. The coordinator states the streak formally and "
                "reports to the owner; falsification cannot apply while "
                "beats_direct is true; 5 completed rounds of the hard cap 6 "
                "(at most one round remains)."
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
        "prompt_reuse": prompt_reuse_section,
        "serving_descriptives": flight["serving_descriptives"],
        "embedding_jitter_pair": flight.get("embedding_jitter_pair"),
        "core_client": flight["core_client"],
        "run_dir": str(run_dir),
        "hard_stop": (
            "Round 4 lands and STOPS. No round-5 flight, no knob change: the "
            "coordinator reconciles the projection verdict and the "
            "stopping-rule facts above (streak empty entering round 4; round "
            "4 can only BANK the first qualifying round; 5 of the hard cap 6 "
            "rounds are complete) and reports to the owner (per-arm accuracy, "
            "W->C/C->W, per-sample deltas vs round 3 AND vs the alpha-.45 "
            "projection with mechanism-vs-variance attribution, "
            "retain-primary realized rate vs the projected 64, spend vs the "
            "amended ceilings, stopping-rule statement) before anything "
            "flies. The coordinator decides round 5 / convergence / freeze."
        ),
    }
    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_CHECK_DIR / "round4-report.json"
    report_path.write_text(
        json.dumps(round_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (run_dir / "round4-scores.json").write_text(
        json.dumps(scores, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    flight["outcome_status"] = "ROUND4_LANDED"
    flight["report_path"] = str(report_path)
    save_flight()
    log(f"round-4 report written: {report_path}")
    log(f"report sha256: {sha256_file(report_path)}")
    log(
        f"SUMMARY: M0 {len(m0_correct)}/100 (sealed), BLEND-r4(alpha "
        f"{ROUND4_ALPHA}, tau {ROUND4_TAU}, f1060078 repair) "
        f"{len(r4_correct)}/100 (projected 74, credible band 70-74; r3 was "
        f"{len(r3_blend_correct)}, r2 {len(r2_blend_correct)}, r1 "
        f"{len(r1_blend_correct)}, r0 {len(r0_blend_correct)}), W->C "
        f"{len(wrong_to_correct)} (r3 24), C->W {len(correct_to_wrong)} "
        f"(r3 5), evidence dispatched {dispatched_count}/100, retain-primary "
        f"{len(retained_primary_ids)} (projected 64), direct-label recovered "
        f"{direct_label_recovered_count}/100, core contacts {contact_total}/"
        f"{ATTEMPT_CORE_CEILING} (attempt), tool {meter.count}/{ATTEMPT_TOOL_CEILING}, "
        f"direct byte-agreement vs a1-M0 {direct_agree_count}/100, vs r2 "
        f"{direct_agree_vs_r2_count}/100, vs r3 {direct_agree_vs_r3_count}/100"
    )
    log(
        "PROJECTION RECONCILIATION: "
        f"aggregate {'HIT' if len(r4_correct) == len(projected_correct) else 'MISS'} "
        f"({len(r4_correct)} vs projected {len(projected_correct)}); "
        f"per-sample hits {projection_reconciliation['per_sample_hits']}/100, "
        f"misses {len(per_sample_misses)} "
        f"(mechanism-level {mechanism_miss_count}, rest attributed to the "
        "documented byte-variance channels)"
    )
    log(
        f"STOPPING RULE AT SEAL: round4_delta_vs_round3={delta_r4_vs_r3}, "
        f"C->W growth vs r3={c2w_growth_vs_r3}, round4_qualifies="
        f"{round4_qualifies} (BANKS the first qualifying round if true), "
        f"CONVERGENCE FIRES={convergence_fires} (structurally False — the "
        "streak is empty entering round 4); 5 of hard cap 6 rounds complete"
    )
    log(
        "PROMPT REUSE: overall evaluated/declared "
        f"{overall_reuse.get('evaluated_prompt_tokens')}/"
        f"{overall_reuse.get('declared_prompt_tokens')} "
        f"(reuse ratio {overall_reuse.get('reuse_ratio')}); evidence-class "
        f"reuse ratio {blend_evidence_reuse.get('reuse_ratio')}, skipped>=1700 "
        f"on {evidence_skipped_ge_1700}/{len(evidence_skipped)} evidence "
        f"contacts, same-slot trajectories {same_slot_trajectories}/"
        f"{len(two_contact_results)}; offset calibration "
        f"{per_request_offset}; verdict: {reuse_verdict}"
    )
    log("RESIDENT DECODER LEFT UP after round 4 (never stopped by this launcher)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
