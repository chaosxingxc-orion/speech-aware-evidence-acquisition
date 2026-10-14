"""Shared identities of SUCCESSOR 3: the SLURP lock candidate v3.0 (the locked system on the Thinking core) on the signed test sample.

One module, imported by the derive, writer, mint, preflip, packets-fragment, reader and test scripts, so no id is spelled twice. Model-free. It EXTENDS
``thinking_system_dev_family`` (the P3.1 DEV-2000-ADDED family, which extends the 268-B Fold B family): the Thinking knobs, the model fragment, the
serving session, the packet root, the fit and context arithmetic and the measured-throughput planning rule are those families', imported by name.
What this module changes is the ROSTER side: the ids, the signed sample roster, the sealed comparator and the successor-3 allowance.

WHAT THE READ IS. Owner ruling 301 A (2026-10-13): the Thinking system flies ONCE on the signed 3,010-row test sample after P3.1 reads NOMINATED
(it did: ``SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1``). Only the lock arm flies; the comparator is the SEALED successor-2 run
(``SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1``, the Instruct NX R5 composed arm on this sample); there is NO in-chain replicate, so the
twin offset is DECLARED from the DEV twin (read.json ``contrast.slu_f1.o_twin_aa_vs_lock`` / ``contrast.intent.o_twin_aa_vs_lock``) and the limitation is
stated in every artifact. ONE attempt per id, aggregate-only, no smoke, no re-fly.

GPU PLANNING (the standing rule: every plan ceiling comes from a measured 4-slot throughput run): ``planned_gpu_hours(rows) = ceil_0.1(rows / 1.84 / 60 x 1.3)``,
the P3.1 rule (:func:`thinking_system_dev_family.planned_gpu_hours`), applied to 3,010 rows.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIRECT_DIR = HERE.parent / "direct"
TFRL_DIR = HERE.parent / "tfrl"
for _dir in (DIRECT_DIR, TFRL_DIR, HERE):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import thinking_system_dev_family as dev  # noqa: E402
import tfrl_family as tf  # noqa: E402

REPO_ROOT = dev.REPO_ROOT
ZERO = "0" * 64

DATE = "2026-10-14"
SLUG = "milestone-successor3-thinking-system"
PKG_NAME = f"slurp-{SLUG}-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
CELL = f"slurp-{SLUG}-v1"
BASELINE = f"slurp-{SLUG}-baseline-v1"
CAMPAIGN_PLAN = f"configs/campaign/{CELL}.json"
RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1"
ATTEMPT = "attempt-slurp-milestone-successor3-thinking-system-generation-v1"
FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-FIT-V1"
FIT_ATTEMPT = "attempt-slurp-milestone-successor3-thinking-system-fit-v1"
READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-PAIRED-ANALYSIS-V1"
RECIPE_ID = "slurp-milestone-successor3-thinking-system-paired-analysis-v1"
ANALYSIS_ROOT = f"analysis/{READ_RUN}"
DECISION_ID = "slurp-milestone-successor3-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READER = "scripts/analysis/slurp_successor3_thinking_read.py"
READ_DRIVER = "scripts/flights/nx/successor3_thinking_read.sh"
SHORT = "ms3"
LEDGER_MARK = "## Cell SUCCESSOR-3: the Thinking system (SLURP lock candidate v3.0) on the signed test sample (one attempt, no smoke)"
OWNER_RULINGS = "owner ruling 301 A (2026-10-13), decision 299 A, P3.1 read NOMINATED (2026-10-13)"

# ---- the signed allowance --------------------------------------------------------------------------------------------------------
ALLOWANCE = "docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json"
S2_ALLOWANCE = "docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json"

# ---- the packets pass over the sample (the Thinking mmproj packets; a final-report preparation) -----------------------------------
PACKETS_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1"
PACKETS_ATTEMPT = "attempt-packets-thinking-gpu-test-sample-3010-v1"
PACKETS_ROSTER_KIND = "thinking-test-sample-3010"
PACKETS_STAGE = "test-sample-3010"
PACKETS_SIDECAR_FRAGMENT = "q4km-thinking-feature-preprocess-gpu-np1-test-sample-3010-v1"
PACKETS_EXPERIMENT_FRAGMENT = "slurp-test-sample-3010-thinking-preprocess-gpu-v1"
PACKETS_LEGACY_CACHE = "/home/chao/feat-cache/slurp-thinking-gpu-q4km-test-sample-3010"
PACKETS_ROW_CALLS = 3010
PACKETS_ROW_SPEECH_SECONDS = 8207           # ceil(8206.436875), the form every roster row uses (the Instruct sample row said 8207)
PACKETS_ROW_GPU_HOURS = 1.0
PACKETS_ALLOWANCE = "docs/receipts/owner/2026-10-14-slurp-test-sample-successor-3-thinking-packets-allowance-v1.json"
THINK_PACKET_ROOT = dev.THINK_PACKET_ROOT
THINK_PROMOTION_RECEIPT = f"{THINK_PACKET_ROOT}/TEST-SAMPLE-3010-promotion.json"      # NEW receipt, produced in the coordinator's GPU window
UNPINNED_SHA = dev.UNPINNED_SHA

# ---- the signed sample ------------------------------------------------------------------------------------------------------------
ROWS = 3010
PROMPTS = 682
ROSTER_ID = "SLURP-TEST-SAMPLE-3010-V1"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
DATASET = "slurp-speech-native-test-sample-3010"
SPLIT_ID = "TEST-SAMPLE"
SPLIT_ROLE = "final-report"
SCORER = "slurp-slu-official-test"
SESSION = dev.THINK_SESSION
SWAP_TARGET = dev.THINK_SWAP_TARGET
MODEL = dev.THINK_MODEL
PROGRAM, LOCK, CONTACTS_PER_ROW = dev.PROGRAM, dev.LOCK, dev.CONTACTS_PER_ROW
FALLBACK_CONTACTS_PER_ROW_CEILING = dev.FALLBACK_CONTACTS_PER_ROW_CEILING

# ---- the source cell (the P3.1 lock arm on DEV) and the Instruct chain it parallels ---------------------------------------------------------
SRC = dev.CELLS["lock"]                      # cell / baseline / run / fit_run / attempt ... of the P3.1 lock arm
SRC_PACKAGE = dev.PACKAGE
SRC_READ_RUN = dev.READ_RUN_ID
SRC_READ_JSON_RELPATH = f"analysis/{dev.READ_RUN_ID}/read.json"        # on the data root
SRC_FLIGHT_COMMIT = "37b0ed0aa"             # the P3.1 flight commit (allowance first_contact_gate.basis)
R5_CELL = "slurp-native-stage3-nx-r5-composed-dev2000-added-v1"
R5_BASELINE = "slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1"
R5_FIT_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-FIT-V1"
R5_FIT_ATTEMPT = "attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-fit-v1"

# ---- the sealed comparator: successor 2 (the Instruct NX R5 composed arm on this sample) ------------------------------------------------------
S2_CELL = "slurp-milestone-successor2-composed-v1"
S2_BASELINE = "slurp-milestone-successor2-composed-baseline-v1"
S2_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1"
S2_ATTEMPT = "attempt-slurp-milestone-successor2-composed-generation-v1"
S2_FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1"
S2_PACKAGE = "docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1"
S2_READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1"
S1_PACKAGE = "docs/readiness/2026-10-01-slurp-milestone-successor1-v1"

# ---- seeds and declared numbers ------------------------------------------------------------------------------------------------------------
SEED = 20261014                  # a NEW fixed seed (the date of the registration); successor 2 used 20260915, P3.1 used 20261011
DRAWS = 10000
HARM_MARGIN = 2.5                # the cross-flight bar (read.json bar_pp 2.5), not tighter than the cross-flight sampling floor
INTENT_GUARD_PP = 0.65           # read.json intent_guard_pp (the P3.1 NOMINATED rule's intent guard)

# ---- GPU planning from the MEASURED throughput (one place; the P3.1 rule) -----------------------------------------------------------------
MEASURED_ROWS_PER_MINUTE = dev.MEASURED_ROWS_PER_MINUTE
GPU_MARGIN, GPU_ROUND_H = dev.GPU_MARGIN, dev.GPU_ROUND_H


def expected_wall_hours(rows: int) -> float:
    return rows / MEASURED_ROWS_PER_MINUTE / 60.0


def planned_gpu_hours(rows: int = ROWS) -> float:
    """``ceil_0.1( rows / 1.84 / 60 x 1.3 )``: 3,010 rows -> 27.26 h expected -> 35.5 (P3.1: 1,000 rows -> 11.8)."""

    hours = expected_wall_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def fit_contact_cap(rows: int = ROWS) -> int:
    """rows x program contacts x endpoints per contact (never run-cumulative): 24,080 (also the allowance's fit_endpoint_cap_total)."""

    return tf.fit_contact_cap(rows, CONTACTS_PER_ROW)


def generation_calls(rows: int = ROWS) -> int:
    """The plan ceiling: rows x (program contacts + answer-only fallback contacts per row), the P3.1 rule (core.reasoning_knobs): 3,010 x 4 = 12,040."""

    return rows * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING)


def program_calls(rows: int = ROWS) -> int:
    return rows * CONTACTS_PER_ROW


def roster_doc() -> dict:
    return json.loads((REPO_ROOT / ROSTER_RECEIPT).read_text(encoding="utf-8"))


def view_doc() -> dict:
    return json.loads((REPO_ROOT / f"configs/dataset/{DATASET}.json").read_text(encoding="utf-8"))


def roster_audio() -> float:
    return sum(float(item["audio_seconds"]) for item in view_doc()["items"])


def audio_cap() -> int:
    """Every contact re-sends the row's speech packet, a fallback re-ask included: ceil(sample audio seconds x (contacts + fallback contacts per row))."""

    return math.ceil(roster_audio() * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING) - 1e-9)


def eligible_run_ids() -> list[str]:
    return [RUN, FIT_RUN]


def eligible_attempt_ids() -> list[str]:
    return [ATTEMPT, FIT_ATTEMPT]


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(plan_kind: str) -> str:
    return f"{plan_kind}-plan-registered-v1.json"


# ---- the packet receipt: strict accessor + state (fail closed when absent) --------------------------------------------------------------------
def receipt_state(receipt_path: str | Path | None = None) -> dict:
    """``{"present": bool, "path": str, "sha256": str | None}`` of the sample promotion receipt (a file read; no model contact)."""

    path = Path(receipt_path or THINK_PROMOTION_RECEIPT)
    if not path.is_file():
        return {"present": False, "path": str(path), "sha256": None}
    return {"present": True, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def thinking_promotion_sha256(receipt_path: str | Path | None = None) -> str:
    """STRICT: the sha256 of the sample promotion receipt, or a SystemExit when the receipt is absent (the family fails closed)."""

    state = receipt_state(receipt_path)
    if not state["present"]:
        raise SystemExit(
            f"REFUSED: the Thinking promotion receipt for the test sample is absent ({state['path']}); produce it with "
            "bash scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage test-sample-3010 (the coordinator's GPU swap window), then re-derive")
    return str(state["sha256"])


def pinned_promotion_sha256(receipt_path: str | Path | None = None, *, require: bool = False) -> str:
    """What the baseline pins: the real sha256 when the receipt exists, else the zero sentinel (never a fabricated hash); ``require`` is strict."""

    if require:
        return thinking_promotion_sha256(receipt_path)
    state = receipt_state(receipt_path)
    return str(state["sha256"]) if state["present"] else UNPINNED_SHA


def sha_file(relpath: str, root: Path | None = None) -> str:
    return hashlib.sha256(((root or REPO_ROOT) / relpath).read_bytes()).hexdigest()


__all__ = [name for name in globals() if not name.startswith("_")]
