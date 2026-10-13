"""Shared identities of the P3.1 replicate: the locked SLURP system on the Thinking core, flown on DEV-2000-ADDED, with its request-identical twin.

One module, imported by the DEV derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It EXTENDS
``thinking_system_family`` (the 268-B Fold B family, unchanged) instead of restating it: the Thinking knobs, the model fragment, the serving
session, the packet root, the fit and context arithmetic are the Fold B family's, imported by name. What this module changes is the ROSTER side
of the package: the ids, the DEV-2000-ADDED roster, the Instruct parent cells, the comparators and the GPU plan.

WHAT THE READ IS. Registry "P3 programme under decision 299 A" (coordinator, 2026-10-13 16:20Z), step P3.1: the 268-B read found the locked
system on the Thinking core TRANSFERS-ABOVE-BAR on TRAIN Fold B (SLU +7.15 pp, intent +2.31 pp over the Instruct system). Fold B numbers are
development numbers (decision 28), so a DEV-2000-ADDED replicate of the Thinking system precedes any lock. The cell is the plain lock (lock v2.2
plus the v4g post-processing, review-off COMP-1b module graph, program ``phase-native-module-v1-c2``, Perception 1 + Solver 1) on DEV-2000-ADDED
with the Instruct core swapped for the Thinking core, with an in-chain request-identical twin ``aa``. NOMINATED iff the SLU CI95 lower bound of
the contrast with the Instruct lock column on the same roster exceeds the twin offset AND the intent guard holds.

THE INSTRUCT PARENT (verified from the ledger and the sealed run manifests, 2026-10-13). The cells the brief names, ``module-comp1b-dev2000-added``
(+ ``-aa`` and ``-smoke-4``), are NOT the Fold B lock graph: they carry lock ``v2.1``, program ``phase-native-candidates-review-revise-v1``
(Reviewer loop ON, up to 11 contacts per row) and every module component off; only the ``-aa`` twin sealed (run
``SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1``, study commit 9a0a3384b) and the main cell stays held with no run directory. The cell that
IS request-identical to the 268-B Thinking cells apart from the roster and the core is NX R5 composed on DEV-2000-ADDED
(``SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1``, sealed COMPLETED at study commit 9a0a3384b, 2026-10-10T06:36:45Z; smoke
``...-SMOKE-4-V1`` sealed at the same commit): lock ``v2.2`` with ``saea-deliver-normalise-v4g``, ``review_loop`` off, ``columns`` empty, program
``phase-native-module-v1-c2``, 2 contacts per row. It is both the DERIVATION parent and the COMPARATOR column. Its module block reproduces
under the same compiler call as the Fold B parent (the derive script proves the reproduction before it writes anything).

GPU PLANNING (owner standing rule: "every plan ceiling comes from a measured 4-slot throughput run"). Source: the sealed 268-B arms ran
1.84 rows per minute at np4 x 24,576 with budget 3,072 (1,080 rows in 9 h 46 min; summed latency 37.65 h = 9.4 slot-normalised GPU-h), against
the 8.4 GPU-h ceiling the per-contact smoke seconds had set. The ceiling here is therefore a WALL-CLOCK bound at the measured rate:

    planned_gpu_hours(rows) = ceil_0.1( rows / 1.84 / 60 x 1.3 )          (1.3 = the loop's planning margin, ``tfrl_family.GPU_PLAN_MARGIN``)

1,000 rows -> 9.06 h expected -> 11.8 per arm; the four-row smoke keeps its 0.5. The card is exclusive during a flight, so wall hours are the
GPU hours the ceiling bounds.

THE PACKETS. The DEV rows need Thinking speech packets from a NEW promotion receipt ``DEV-2000-ADDED-promotion.json`` under the existing Thinking
packet root. The coordinator produces it in a GPU swap window (``scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage dev2000-added``).
The cells pin the receipt's sha256; while the receipt is absent the baselines carry the zero sentinel and EVERY consumer that matters (mint,
flip, chain, the strict accessor :func:`thinking_promotion_sha256`) fails closed.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TFRL_DIR = HERE.parent / "tfrl"
for _dir in (HERE, TFRL_DIR):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import direct_fb_family as dfb  # noqa: E402
import tfrl_family as tf  # noqa: E402
import thinking_system_family as base  # noqa: E402

REPO_ROOT = base.REPO_ROOT

DATE = "2026-10-13"
SHORT = "tsysd"
SLUG = "thinking-system-dev2000-added"
PKG_NAME = "slurp-system-thinking-core-dev2000-added-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = "slurp-system-thinking-core-dev2000-added-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1"
RECIPE_ID = "slurp-system-thinking-core-dev2000-added-read-v1"
READER = "scripts/analysis/slurp_system_thinking_core_dev_read.py"
LEDGER_MARK = "## Cell P3.1: the locked system on the Thinking core, DEV-2000-ADDED (lock + twin; smoke then 1,000 rows each)"
PACKETS_ROW_ID = "SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1"
PACKETS_ROSTER_KIND = "thinking-dev2000-added"
PACKETS_STAGE = "dev2000-added"

# ---- the system: exactly the loop's plain lock (the Fold B family's constants, re-exported) ----------------------------------------
ROWS, SMOKE_ROWS = 1000, base.SMOKE_ROWS
LOCK, PROGRAM, CONTACTS_PER_ROW, POLICY = base.LOCK, base.PROGRAM, base.CONTACTS_PER_ROW, base.POLICY
assert (ROWS, SMOKE_ROWS) == (1000, 4) and CONTACTS_PER_ROW == 2
SCORER = "slurp-slu-official"                          # the DEV runs' official scorer id (Fold B's is slurp-slu-official-train)
DATASET = "slurp-speech-native-dev2000-added"
SPLIT_ID = "DEV-2000-ADDED"
SPLIT_ROLE = "dev"
TUNING_ROSTER, READ_ROSTER = "none", "SLURP-DEV-2000-ADDED-V1"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
RUNTIME_VIEW = "configs/dataset/slurp-speech-native-dev2000-added.json"        # the roster = the dev2000-added runtime view (1,000 rows)
ROSTER = {"arm": RUNTIME_VIEW, "smoke": RUNTIME_VIEW}  # the smoke is the view's first four rows (the parent smoke cell's own four)

# ---- the Instruct parent and the comparators --------------------------------------------------------------------------------------
PARENT_SLUG = "nx-r5-composed-dev2000-added"
PARENT_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1"
PARENT_ATTEMPT = "attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-generation-v1"
PARENT_SMOKE_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-V1"
PARENT_STUDY_COMMIT = "9a0a3384b0eea234ef612bc6d44d7e1a6bb2e123"
PARENT_SMOKE_SPLIT_IDENTITY = "fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0"
#: The Instruct lock column the Thinking system arm is read against: the parent cell itself, same roster, same system, a different core.
COMPARATOR_COLUMN, COMPARATOR_ATTEMPT = PARENT_RUN, PARENT_ATTEMPT
COMPARATOR_ARM = "composed"
#: The bare Instruct core on this roster (cell B6 direct arm, sealed COMPLETED at study commit 54f569c62ba1; its split identity hash equals
#: the roster's, verified in the ledger row and by the test). There is NO bare Thinking core on DEV-2000-ADDED (P3.3 flies carrier baselines).
BARE_RUN = "SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1"
BARE_ATTEMPT = "attempt-slurp-direct-max512-dev2000-added-generation-v1"
BARE_KIND = "bare Instruct core (direct-only form, max512)"
#: The declared prior: the 268-B Fold B read (Thinking system minus Instruct lock column), SLU-F1 [+5.08, +9.26], intent +2.31 [+0.56, +4.07].
FOLD_B_DELTA_SLU_PP, FOLD_B_DELTA_INTENT_PP = 7.15, 2.31
EXPECTED_EFFECT_PP = FOLD_B_DELTA_SLU_PP
FOLD_B_INSTRUCT_LOCK_SLU, FOLD_B_INSTRUCT_LOCK_INTENT = 64.45, 82.69

# ---- the Thinking core: the Fold B family's pins, imported by name -------------------------------------------------------------------
THINK_BUDGET_TOKENS, THINK_ANSWER_RESERVE_TOKENS, THINK_MAX_TOKENS = base.THINK_BUDGET_TOKENS, base.THINK_ANSWER_RESERVE_TOKENS, base.THINK_MAX_TOKENS
THINK_BUDGET_MESSAGE, REASONING_CONTEXT_POLICY = base.THINK_BUDGET_MESSAGE, base.REASONING_CONTEXT_POLICY
NODE_MODES, ANSWER_FALLBACK = base.NODE_MODES, base.ANSWER_FALLBACK
FALLBACK_CONTACTS_PER_ROW_CEILING = base.FALLBACK_CONTACTS_PER_ROW_CEILING
THINKING_KNOBS, FRAGMENT_KNOBS = base.THINKING_KNOBS, base.FRAGMENT_KNOBS
#: The merged budget fragment and its session pin only the packet ROOT (``speech_feature_root``), never a receipt, and the packet root is
#: additive (the DEV promotion adds ``slurp/devel/...`` packets and one receipt), so the Fold B model fragment and session are reused unchanged.
THINK_MODEL, THINK_SESSION, THINK_SWAP_TARGET = base.THINK_MODEL, base.THINK_SESSION, base.THINK_SWAP_TARGET
INSTRUCT_SESSION = base.INSTRUCT_SESSION
THINK_PACKET_ROOT = base.THINK_PACKET_ROOT
THINK_PROMOTION_RECEIPT = f"{THINK_PACKET_ROOT}/DEV-2000-ADDED-promotion.json"       # NEW receipt, produced in the coordinator's GPU window
FOLD_B_PROMOTION_RECEIPT = base.THINK_PROMOTION_RECEIPT
UNPINNED_SHA = dfb.UNPINNED_SHA
SLOT_TOKENS, RESERVE_TOKENS, SPECIAL_RESERVE = base.SLOT_TOKENS, base.RESERVE_TOKENS, base.SPECIAL_RESERVE
PROMPT_LIMIT_THINKING, SOLVER_PROMPT_TOKENS_MAX = base.PROMPT_LIMIT_THINKING, base.SOLVER_PROMPT_TOKENS_MAX
THINK_SLOTS = base.THINK_SLOTS
SUPERSEDED_THINK_MODEL, SUPERSEDED_THINK_SESSION = base.SUPERSEDED_THINK_MODEL, base.SUPERSEDED_THINK_SESSION

# ---- GPU planning from the MEASURED throughput (one place) --------------------------------------------------------------------------
MEASURED_ROWS_PER_MINUTE = 1.84                         # 268-B arms: 1,080 rows in 9 h 46 min at np4 x 24,576, budget 3,072 (registry 15:50Z)
MEASURED_SOURCE = ("268-B READ (registry 15:50Z, 2026-10-13): lock and twin, 1,080 rows each in 9 h 46 min = 1.84 rows per minute at np4 x 24,576 "
                   "with budget 3,072; summed latency 37.65 / 37.82 h = about 9.4 slot-normalised GPU-h against the 8.4 ceiling the per-contact "
                   "smoke seconds had set (the overrun that retired per-contact planning)")
GPU_MARGIN = base.GPU_MARGIN                            # 1.3
GPU_ROUND_H = base.GPU_ROUND_H                          # 0.1
SMOKE_GPU_HOURS = 0.5


def expected_wall_hours(rows: int) -> float:
    """Wall-clock hours of a pass at the measured rate: rows / 1.84 / 60 (unrounded)."""

    return rows / MEASURED_ROWS_PER_MINUTE / 60.0


def planned_gpu_hours(rows: int) -> float:
    """The registered ceiling: ``ceil_0.1( rows / 1.84 / 60 x 1.3 )``. The only place a GPU ceiling of this package is computed."""

    hours = expected_wall_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def _spec(key: str, role: str, rows: int, roster: str, scoring_jobs: int, gpu: float, *, slug: str, ids_stem: str, parent_kind: str) -> dict:
    up = ids_stem.upper()
    return {
        "key": key, "role": role, "rows": rows, "roster": roster, "gpu_hours": gpu, "scoring_jobs": scoring_jobs, "parent_kind": parent_kind,
        "slug": slug, "cell": f"slurp-native-stage3-{ids_stem}-v1", "baseline": f"slurp-native-stage3-{ids_stem}-baseline-v1",
        "run": f"SAEA-SLURP-STAGE3-{up}-V1", "fit_run": f"SAEA-SLURP-STAGE3-{up}-FIT-V1",
        "attempt": f"attempt-slurp-native-stage3-{ids_stem}-generation-v1", "fit_attempt": f"attempt-slurp-native-stage3-{ids_stem}-fit-v1",
        "model": THINK_MODEL, "session": THINK_SESSION, "prefix": "smoke-" if key == "smoke" else f"{key}-",
        "campaign": f"configs/campaign/slurp-native-stage3-{ids_stem}-v1.json",
    }


CELLS = {
    "smoke": _spec("smoke", "four-row form smoke of the Thinking system", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   slug=SLUG, ids_stem=f"{SLUG}-smoke-4", parent_kind="smoke"),
    "lock": _spec("lock", "Thinking system arm (lock)", ROWS, "arm", 1, planned_gpu_hours(ROWS), slug=f"{SLUG}-lock", ids_stem=f"{SLUG}-lock", parent_kind="arm"),
    "aa": _spec("aa", "Thinking system in-chain twin (aa)", ROWS, "arm", 1, planned_gpu_hours(ROWS), slug=f"{SLUG}-aa", ids_stem=f"{SLUG}-aa", parent_kind="arm"),
}
ARM_KEYS = ("lock", "aa")
ALL_KEYS = ("smoke", "lock", "aa")
TWIN_SHAPE = base.TWIN_SHAPE
REPLICATE_OF = {"lock": "aa", "aa": "lock"}


def parent_names(parent_kind: str) -> dict:
    lo = "-smoke-4" if parent_kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{PARENT_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{PARENT_SLUG}{lo}-baseline-v1"}


def eligible_run_ids() -> list[str]:
    out: list[str] = []
    for key in ALL_KEYS:
        out += [CELLS[key]["run"], CELLS[key]["fit_run"]]
    return out


def eligible_attempt_ids() -> list[str]:
    out: list[str] = []
    for key in ALL_KEYS:
        out += [CELLS[key]["attempt"], CELLS[key]["fit_attempt"]]
    return out


def fit_contact_cap(rows: int) -> int:
    """rows x max_contacts x endpoints per contact (never run-cumulative): 8,000 for a 1,000-row cell (the parent's own cap)."""

    return tf.fit_contact_cap(rows, CONTACTS_PER_ROW)


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(key: str, plan_kind: str) -> str:
    return f"{CELLS[key]['prefix']}{plan_kind}-plan-registered-v1.json"


def roster_doc(kind: str) -> dict:
    """The roster document of ``kind``: the runtime view (1,000 items); the smoke is its first :data:`SMOKE_ROWS` items."""

    doc = json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))
    if kind == "smoke":
        doc = dict(doc, items=list(doc["items"])[:SMOKE_ROWS], count=SMOKE_ROWS, split_identity_hash=PARENT_SMOKE_SPLIT_IDENTITY)
    return doc


def roster_audio(kind: str) -> float:
    return sum(float(item["audio_seconds"]) for item in roster_doc(kind)["items"])


def audio_cap(kind: str) -> int:
    """Every contact re-sends the row's speech packet, a fallback re-ask included: ceil(roster audio seconds x (contacts + fallback contacts per row))."""

    return math.ceil(roster_audio(kind) * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING) - 1e-9)


def generation_calls(key: str) -> int:
    """The plan ceiling: rows x (program contacts + fallback contacts per row), the rule rails.runner applies (core.reasoning_knobs)."""

    return CELLS[key]["rows"] * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING)


def program_calls(key: str) -> int:
    return CELLS[key]["rows"] * CONTACTS_PER_ROW


# ---- the packet receipt: strict accessor + state (fail closed when absent) --------------------------------------------------------------


def receipt_state(receipt_path: str | Path | None = None) -> dict:
    """``{"present": bool, "path": str, "sha256": str | None}`` of the DEV promotion receipt (a file read; no model contact)."""

    path = Path(receipt_path or THINK_PROMOTION_RECEIPT)
    if not path.is_file():
        return {"present": False, "path": str(path), "sha256": None}
    return {"present": True, "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def thinking_promotion_sha256(receipt_path: str | Path | None = None) -> str:
    """STRICT: the sha256 of the DEV promotion receipt, or a SystemExit when the receipt is absent (the family fails closed)."""

    state = receipt_state(receipt_path)
    if not state["present"]:
        raise SystemExit(
            f"REFUSED: the Thinking promotion receipt for DEV-2000-ADDED is absent ({state['path']}); produce it with "
            "bash scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage dev2000-added (the coordinator's GPU swap window), then re-derive")
    return str(state["sha256"])


def pinned_promotion_sha256(receipt_path: str | Path | None = None, *, require: bool = False) -> str:
    """What the baselines pin: the real sha256 when the receipt exists, else the zero sentinel (never a fabricated hash); ``require`` is strict."""

    if require:
        return thinking_promotion_sha256(receipt_path)
    state = receipt_state(receipt_path)
    return str(state["sha256"]) if state["present"] else UNPINNED_SHA


__all__ = [name for name in globals() if not name.startswith("_")]
