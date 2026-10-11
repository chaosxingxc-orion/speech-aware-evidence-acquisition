"""Shared identities of the 266-E bare-core read: direct-only, TRAIN Fold B, Thinking versus Instruct.

One module, imported by the derive, writer, mint, reader and test scripts, so no id is spelled twice. Model-free.

WHAT THE READ IS. Owner decision 266-E (2026-10-11): is the CORE capability, not the system, the binding constraint? The same bare-core
form -- the direct-only phase program of the shared controller (``phase-direct-only-v1``) through ``FlightRuntime`` and the OpenJiuwen
executor, the sealed ``slurp-direct-max512`` task instruction -- flies on TRAIN Fold B (``SLURP-EVO-FOLD-B-V2``, 1,080 rows) on the
Instruct core (the resident session) and on the Thinking core (its own session). The comparison is cross-session by necessity, so the
Instruct arm flies twice in the same chain (the in-chain A/A replicate) and the Thinking delta is read against the mean of the two
Instruct passes at the cross-flight bar (about 2.5 pp at n = 1,080).

Four cells, all HELD: the Instruct arm (a), its request-identical replicate (b), the Thinking arm (c) and a four-row Thinking smoke (d)
that seals and reports decode cost BEFORE (c) is queued.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-11"
SLUG = "direct-only-fold-b-thinking-vs-instruct"
PKG_NAME = f"slurp-{SLUG}-v1"                      # coordination dir, package suffix, campaign stem
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1"
RECIPE_ID = f"slurp-{SLUG}-read-v1"
SERVING_ROW_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-SERVING-V1"
PACKETS_ROW_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1"
LEDGER_MARK = "## Cell 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct"

ROWS = 1080
SMOKE_ROWS = 4
CONTACTS_PER_ROW = 1                                # phase-direct-only-v1: one phase, max_contacts 1
FIT_ENDPOINTS = lambda rows: 1 + 3 * rows           # noqa: E731  core.preparation_fit.complete_phase_endpoint_count(1, rows, media_count=1)

SCORER = "slurp-slu-official-train"
POLICY = "phase-direct-only-v1"
DATASET = "slurp-speech-native-evo-fold-b-1080"
BOOTSTRAP_SEED = 20261011
BOOTSTRAP_DRAWS = 10000
#: The cross-flight bar the read resolves above (instrument note section 2d: about 2.5 pp at n = 1,080).
CROSS_FLIGHT_BAR_PP = 2.5

INSTRUCT_SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
THINK_SESSION = "serving-slurp-thinking-direct-fold-b-np4-v1"
INSTRUCT_MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
THINK_MODEL = "q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max2048-v1"
PARENT_BASELINE = "slurp-direct-max512-train-fold-a-v1"            # the sealed Fold A direct form, re-pointed at Fold B
PARENT_EXPERIMENT = "slurp-native-stage3-ver1a-samples-fold-b-v1"   # a committed Fold B experiment: roster, populations, skeleton
THINK_PACKET_ROOT = "/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6"
THINK_PROMOTION_RECEIPT = f"{THINK_PACKET_ROOT}/EVO-FOLD-B-V2-promotion.json"
UNPINNED_SHA = "0" * 64                              # sentinel: the Thinking packets are not prepared yet; the flip refuses it

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": f"{PACKAGE}/smoke-roster-receipt-v1.json",       # inside the package: a prefix of the parent roster, not a new draw
}
SMOKE_ROSTER_ID = "SLURP-DIRECT-FOLD-B-THINKING-SMOKE-4-V1"
TUNING_ROSTER, READ_ROSTER = "none", "SLURP-EVO-FOLD-B-V2"

#: The coordinator's decode-cost sign-off marker: the chain's Thinking arm segment refuses to start until it exists.
SIGNOFF_MARKER = "/home/chao/direct-fb-decode-signoff.marker"
FLIGHT_COMMIT_FILE = "/home/chao/direct-fb-flight-commit.txt"


def _spec(key, stem, role, core, rows, gpu, scoring, roster):
    upper = stem.upper()
    return {
        "key": key, "role": role, "core": core, "rows": rows, "gpu_hours": gpu, "scoring_jobs": scoring, "roster": roster,
        "cell": f"slurp-direct-only-fold-b-{stem}-v1",
        "baseline": f"slurp-direct-only-fold-b-{stem}-baseline-v1",
        "run": f"SAEA-SLURP-DIRECT-ONLY-FOLD-B-{upper}-V1",
        "fit_run": f"SAEA-SLURP-DIRECT-ONLY-FOLD-B-{upper}-FIT-V1",
        "attempt": f"attempt-slurp-direct-only-fold-b-{stem}-generation-v1",
        "fit_attempt": f"attempt-slurp-direct-only-fold-b-{stem}-fit-v1",
        "model": INSTRUCT_MODEL if core == "instruct" else THINK_MODEL,
        "session": INSTRUCT_SESSION if core == "instruct" else THINK_SESSION,
    }


#: Ordered by the registered chain: the smoke first, then the Thinking arm, then the Instruct arm and its replicate.
CELLS = {
    "smoke": _spec("smoke", "thinking-smoke-4", "four-row Thinking decode-cost smoke", "thinking", SMOKE_ROWS, 0.5, 0, "smoke"),
    "thinking": _spec("thinking", "thinking", "Thinking arm", "thinking", ROWS, 3.0, 1, "arm"),
    "instruct": _spec("instruct", "instruct", "Instruct arm", "instruct", ROWS, 0.5, 1, "arm"),
    "replicate": _spec("replicate", "instruct-replicate", "Instruct in-chain replicate", "instruct", ROWS, 0.5, 1, "arm"),
}
ARM_KEYS = ("instruct", "replicate", "thinking")
ALL_KEYS = ("smoke", "thinking", "instruct", "replicate")
#: The replicate each arm's stage3_measurement block names (rule 3: the in-chain A/A of the Instruct comparator).
REPLICATE_OF = {"instruct": "replicate", "replicate": "instruct", "thinking": "replicate"}


def fit_contact_cap(rows: int) -> int:
    return FIT_ENDPOINTS(rows)


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def roster_doc(kind: str) -> dict:
    return json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))


def roster_audio(kind: str) -> float:
    return sum(float(item["audio_seconds"]) for item in roster_doc(kind)["items"])


def audio_cap(kind: str) -> int:
    """One contact per row re-sends the row's speech packet once: ceil(roster audio seconds x 1)."""

    return math.ceil(roster_audio(kind) * CONTACTS_PER_ROW - 1e-9)
