"""Shared identities of the 268-B read: the locked SLURP system on the Thinking core, TRAIN Fold B, with its request-identical twin.

One module, imported by the derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It reuses the two
families it extends instead of restating them: ``direct_fb_family`` (the Thinking core's model fragment, session, packet root and its pinned
promotion receipt, all frozen by the 266-E read) and ``tfrl_family`` (the Fold B roster, the plain-lock program ``phase-native-module-v1-c2``,
the FIT arithmetic and the derive helpers). A cell here adds ONLY the core swap and the ids.

WHAT THE READ IS. Owner decision 268 B (2026-10-12): the 266-E read found the bare Thinking core +11.90 pp SLU-F1 over the bare Instruct core.
Does that stack on the locked system? The cell is the plain lock (lock v2.2 + the v4g post-processing, the COMP-1b review-off module graph,
program ``phase-native-module-v1-c2``: Perception 1 + Solver 1) on TRAIN Fold B with the Instruct core swapped for the Thinking core. It is
read cross-flight against the loop's Instruct lock arm on the same roster (the iteration-3 column), with an in-chain request-identical twin
``aa`` as the A/A replicate.

WHY THE TWIN IS A SEPARATE CELL, NOT A SUPPLY ARM. In the loop columns the twin ``aa`` is an in-flight Solver arm of a ``supply_variants`` group
beside at least one real candidate column. ``rails.consumption_module`` refuses a supply frame with no candidate column ("supply_frame is
declared but no supply column is"), so a lock-plus-twin flight cannot be compiled; and the twin of a cross-flight contrast is stronger as a
whole-pipeline replicate anyway (Perception re-contacted, not shared). The twin is therefore a second cell flown in the same chain, exactly as
the 266-E Instruct replicate and the cell1/gepacell twins are. Arms: ``lock`` (the Thinking system arm) and ``aa`` (its twin).

Three cells, all HELD: the four-row smoke, ``lock`` and ``aa``.
"""

from __future__ import annotations

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

REPO_ROOT = tf.REPO_ROOT

DATE = "2026-10-12"
SLUG = "thinking-system-fold-b"
PKG_NAME = "slurp-system-thinking-core-fold-b-v1"          # coordination dir, package suffix
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = "slurp-system-thinking-core-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1"
RECIPE_ID = "slurp-system-thinking-core-fold-b-read-v1"
READER = "scripts/analysis/slurp_system_thinking_core_read.py"
LEDGER_MARK = "## Cell 268-B: the locked system on the Thinking core, TRAIN Fold B (lock + twin; smoke then 1,080 rows each)"

# ---- the system: exactly the loop's plain lock -----------------------------------------------------------------------------------
ROWS, SMOKE_ROWS = tf.ROWS, tf.SMOKE_ROWS
LOCK = tf.CONST_LOCK                                   # v2.2 (requests byte-identical to the loop's v2.3, proof P-ACE-0)
PROGRAM = tf.CONST_PROGRAM                             # phase-native-module-v1-c2
CONTACTS_PER_ROW = tf.CONST_CONTACTS                   # Perception 1 + Solver 1
SCORER = tf.SCORER
POLICY = PROGRAM
DATASET = "slurp-speech-native-evo-fold-b-1080"
SPLIT_ID = "SLURP-EVO-FOLD-B-V2"
TUNING_ROSTER, READ_ROSTER = "none", "SLURP-EVO-FOLD-B-V2"
ROSTER = dict(tf.ROSTER)                               # arm: the Fold B v2 roster; smoke: the loop's own four Fold B rows
PARENT_SLUG = tf.PARENT_SLUG                           # nx-r6-perception-fold-b: the committed module-graph parent the loop derives from
#: The Instruct lock arm this read is contrasted with: the loop's iteration-3 column (arm ``lock``), same roster, same system.
COMPARATOR_COLUMN = "SAEA-SLURP-STAGE3-TFRL-LOOP-I3-FOLD-B-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-tfrl-loop-i3-fold-b-generation-v1"
COMPARATOR_ARM = tf.DELIVERING
#: The bare Thinking core of the 266-E read (direct-only form) the system is read against as well.
BARE_THINKING_RUN = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-V1"
BARE_THINKING_ATTEMPT = "attempt-slurp-direct-only-fold-b-thinking-generation-rec1-v1"
BARE_DELTA_SLU_PP = 11.90                              # 266-E: bare Thinking minus bare Instruct, SLU-F1 [+9.34, +14.52]
BARE_DELTA_INTENT_PP = 4.35                            # 266-E intent guard [+2.08, +6.62]
INSTRUCT_LOCK_SLU, INSTRUCT_LOCK_INTENT = 64.34, 82.41   # the Instruct-core lock column of record (decision 268 text)

# ---- the Thinking core: the 266-E pins re-used, the no-truncation knobs of the engineering design added -----------------------------
#: ONE place for every Thinking-control knob (coordinator update of 2026-10-12; design docs/superpowers/specs/2026-10-12-thinking-core-engineering-
#: base-design.md on branch opus/thinking-core-engineering-design, decisions 274-282). The harness that PASSES ``thinking_budget_tokens`` and the
#: per-role reasoning block through the transport is built separately (decision 282); the package is re-derived from THESE constants when it lands.
THINK_BUDGET_TOKENS = 3072                              # B: per-request reasoning budget; the budget sampler forces the think block closed
THINK_ANSWER_RESERVE_TOKENS = 1024                      # R: answer reserve after the forced close (largest Instruct module answer: 158 tokens)
THINK_MAX_TOKENS = THINK_BUDGET_TOKENS + THINK_ANSWER_RESERVE_TOKENS    # 4,096: the fragment's geometry cap, replaces 8,192
#: The forced-close message the server flag ``--reasoning-budget-message`` carries (spec decision 276 A; the Qwen3 technical report's stop
#: sentence, wording from memory in the spec: verify verbatim against arXiv:2505.09388 before the fragment is pinned by a flight).
THINK_BUDGET_MESSAGE = "Considering the limited time by the user, I have to give the solution based on the thinking directly now."
REASONING_CONTEXT_POLICY = "drop-reasoning-v1"          # decision 278 A: no reasoning byte is carried across nodes (a registered, hashed knob)
NODE_MODES = {"perception": "think", "solver": "think"}   # decision 279 A: every node thinks, budgeted, for the transfer read
ANSWER_FALLBACK = {"id": "saea-thinking-answer-fallback-v1", "mode": "answer-only re-ask", "enable_thinking": False,
                   "max_tokens": THINK_ANSWER_RESERVE_TOKENS, "per_node": 1}        # decision 277 A; the contact ceiling rises by 1 per node
FALLBACK_CONTACTS_PER_ROW_CEILING = 2                   # core.reasoning_knobs.FALLBACK_CONTACTS_PER_ROW_MODULE: one answer-only re-ask per node (merged, decision 283 A)
BUDGET_MESSAGE_SHA256 = __import__("hashlib").sha256(THINK_BUDGET_MESSAGE.encode("utf-8")).hexdigest()
#: The registered knobs as one mapping, so the baseline, the plans, the facts and the tests all read the same bytes.
#: The REAL fragment keys of the merged harness (core.reasoning_knobs.FRAGMENT_KNOB_KEYS); the wire fields fold into decoding_params at composition.
FRAGMENT_KNOBS = {"reasoning_budget_tokens": THINK_BUDGET_TOKENS, "answer_reserve_tokens": THINK_ANSWER_RESERVE_TOKENS, "enable_thinking": True,
                  "reasoning_context_policy": REASONING_CONTEXT_POLICY, "forced_close_message_sha256": BUDGET_MESSAGE_SHA256}
THINKING_KNOBS = {
    "thinking_budget_tokens": THINK_BUDGET_TOKENS, "answer_reserve_tokens": THINK_ANSWER_RESERVE_TOKENS, "completion_cap": THINK_MAX_TOKENS,
    "budget_message": THINK_BUDGET_MESSAGE, "reasoning_context_policy": REASONING_CONTEXT_POLICY, "node_modes": dict(NODE_MODES),
    "answer_fallback": dict(ANSWER_FALLBACK), "decoding": {"temperature": 0, "seed": 20260913}, "reasoning_format": "deepseek",
}
#: The model fragment and the serving session, derived from the 266-E max8192 definitions (``direct_fb_family.THINK_MODEL`` /
#: ``THINK_SESSION``) by the swap budget{B}-max{cap}; the 8,192 fragment and session stay on disk unedited as the record. No session is started here.
SUPERSEDED_THINK_MODEL, SUPERSEDED_THINK_SESSION = dfb.THINK_MODEL, dfb.THINK_SESSION
THINK_MODEL = "q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget%d-max%d-v1" % (THINK_BUDGET_TOKENS, THINK_MAX_TOKENS)
THINK_SESSION = "serving-slurp-thinking-module-fold-b-np4-budget%d-max%d-v1" % (THINK_BUDGET_TOKENS, THINK_MAX_TOKENS)
THINK_SWAP_TARGET = "think-budget-np4"                  # scripts/flights/batch/serving_lib.sh geometry row
INSTRUCT_SESSION = tf.SESSION
THINK_PACKET_ROOT = dfb.THINK_PACKET_ROOT
THINK_PROMOTION_RECEIPT = dfb.THINK_PROMOTION_RECEIPT
BASELINE_FOR_PINS = "slurp-direct-only-fold-b-thinking-baseline-v1"   # the 266-E Thinking baseline whose promotion-receipt sha is the pin
#: The fold-excluded knowledge view of the 266-E baselines. A module cell pins its stores through ``knowledge_stores`` (the loop's Fold B
#: pools, which exclude Fold A and Fold B by construction), not through ``knowledge_snapshot_*``; the view is recorded here so the test can
#: prove the module cell does not carry the full-TRAIN view that aborted the first 266-E Instruct attempt.
KNOWLEDGE_SNAPSHOT_SHA256 = dfb.KNOWLEDGE_SNAPSHOT_SHA256
FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256 = dfb.FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256

# ---- budget arithmetic (one place) ---------------------------------------------------------------------------------------------
#: The engineering design's throughput model (section 2.5 / 4.3): thinking contact latency = Instruct-module latency of that role
#: + DECODE_S_PER_TOKEN x E[min(reasoning, B)]. Measured inputs: Instruct module column (i2, 4,320 contacts) Perception 5.48 s and Solver 7.45 s
#: per contact; 266-E least-squares decode increment 0.02298 s per generated token per slot; E[min(x, B)] from the 266-E COST channel.
INSTRUCT_MODULE_S = {"perception": 5.48, "solver": 7.45}
DECODE_S_PER_TOKEN = 0.02298
E_MIN_REASONING_TOKENS = {1024: 638, 2048: 782, 3072: 848, 4096: 892, None: 1032}
THINK_SLOTS = 4
GPU_MARGIN = tf.GPU_PLAN_MARGIN                         # 1.3, the loop's planning margin
GPU_ROUND_H = tf.GPU_PLAN_ROUND_H
SMOKE_GPU_HOURS = 0.5
#: Wall-clock idle factors measured by the design (section 4.3): 1.11 on a direct-only Thinking arm, about 1.44 on the Instruct module column.
WALL_FACTOR_RANGE = (1.11, 1.44)


#: Sign-off amendment (coordinator, 2026-10-12 20:05Z, smoke SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1 at flight commit
#: c112da11b, 4 rows / 8 contacts, 0 cap hits, 0 empty, 2 forced closes): the measured per-contact seconds on the SYSTEM prompts
#: (Perception 50.32 s mean, Solver 35.31 s mean at np4; reasoning means 1,985 / 1,768 tokens against the 848 the bare-core COST
#: channel predicted) replace the modelled Instruct-latency-plus-decode-increment estimate above. Projection 6.42 GPU-h per
#: 1,080-row pass versus the 3.89 modelled; the registered ceiling moves from 5.1 to 8.4 per arm (x1.3 margin, ceil 0.1).
SMOKE_MEASURED_S_PER_CONTACT = {"perception": 50.32, "solver": 35.31}


def row_seconds(solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS) -> float:
    """Slot-seconds of one row: Perception + ``solver_contacts`` Solvers, from the smoke's measured per-contact seconds (sign-off
    amendment above); the modelled form (Instruct latency plus the budgeted decode increment) is kept in ``modelled_row_seconds``."""

    return SMOKE_MEASURED_S_PER_CONTACT["perception"] + solver_contacts * SMOKE_MEASURED_S_PER_CONTACT["solver"]


def modelled_row_seconds(solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS) -> float:
    """The pre-smoke model: each role's Instruct latency plus the budgeted decode increment (kept for the design record)."""

    think = DECODE_S_PER_TOKEN * E_MIN_REASONING_TOKENS[budget]
    return (INSTRUCT_MODULE_S["perception"] + think) + solver_contacts * (INSTRUCT_MODULE_S["solver"] + think)


def expected_gpu_hours(rows: int, solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS) -> float:
    """Slot-normalised GPU hours of a pass: rows x row_seconds / slots / 3600 (unrounded)."""

    return rows * row_seconds(solver_contacts, budget=budget) / THINK_SLOTS / 3600.0


def planned_gpu_hours(rows: int, solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS) -> float:
    """The registered ceiling: ``ceil_0.1( expected x margin )``."""

    hours = expected_gpu_hours(rows, solver_contacts, budget=budget) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def wall_hours(rows: int, solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS, modelled: bool = False) -> tuple[float, float]:
    low, high = WALL_FACTOR_RANGE
    base = (modelled_expected_gpu_hours if modelled else expected_gpu_hours)(rows, solver_contacts, budget=budget)
    return round(base * low, 1), round(base * high, 1)


#: Context fit at the 4,096-token cap: the live prompt limit is the slot minus the 3,072-token reserve, the cap and the 2-token special
#: reserve. The Instruct column's cap is 512. The measured Solver prompt maximum on the Instruct lock is 14,641 tokens (fit-measure-v1).
SLOT_TOKENS, RESERVE_TOKENS, SPECIAL_RESERVE = 24576, 3072, 2
PROMPT_LIMIT_THINKING = SLOT_TOKENS - RESERVE_TOKENS - THINK_MAX_TOKENS - SPECIAL_RESERVE      # 17,406
PROMPT_LIMIT_INSTRUCT = SLOT_TOKENS - RESERVE_TOKENS - 512 - SPECIAL_RESERVE                   # 20,990
PROMPT_LIMIT_SUPERSEDED_8192 = SLOT_TOKENS - RESERVE_TOKENS - 8192 - SPECIAL_RESERVE           # 13,310
SOLVER_PROMPT_TOKENS_MAX = 14641


def _spec(key: str, role: str, rows: int, roster: str, scoring_jobs: int, gpu: float, *, slug: str, ids_stem: str, parent_kind: str) -> dict:
    up = ids_stem.upper()
    return {
        "key": key, "role": role, "rows": rows, "roster": roster, "gpu_hours": gpu, "scoring_jobs": scoring_jobs,
        "parent_kind": parent_kind,                                            # the committed module parent this cell derives from
        "slug": slug,                                                           # replaces the parent's slug in every inherited id
        "cell": f"slurp-native-stage3-{ids_stem}-v1",
        "baseline": f"slurp-native-stage3-{ids_stem}-baseline-v1",
        "run": f"SAEA-SLURP-STAGE3-{up}-V1",
        "fit_run": f"SAEA-SLURP-STAGE3-{up}-FIT-V1",
        "attempt": f"attempt-slurp-native-stage3-{ids_stem}-generation-v1",
        "fit_attempt": f"attempt-slurp-native-stage3-{ids_stem}-fit-v1",
        "model": THINK_MODEL, "session": THINK_SESSION,
        "prefix": "smoke-" if key == "smoke" else f"{key}-",
        "campaign": f"configs/campaign/slurp-native-stage3-{ids_stem}-v1.json",
    }


def _arm_gpu() -> float:
    return planned_gpu_hours(ROWS, 1)


#: Ordered by the registered chain: the smoke, the Thinking system arm ``lock``, then its twin ``aa``.
CELLS = {
    "smoke": _spec("smoke", "four-row form smoke of the Thinking system", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   slug=SLUG, ids_stem=f"{SLUG}-smoke-4", parent_kind="smoke"),
    "lock": _spec("lock", "Thinking system arm (lock)", ROWS, "arm", 1, _arm_gpu(), slug=f"{SLUG}-lock", ids_stem=f"{SLUG}-lock", parent_kind="arm"),
    "aa": _spec("aa", "Thinking system in-chain twin (aa)", ROWS, "arm", 1, _arm_gpu(), slug=f"{SLUG}-aa", ids_stem=f"{SLUG}-aa", parent_kind="arm"),
}
ARM_KEYS = ("lock", "aa")
ALL_KEYS = ("smoke", "lock", "aa")
#: How the twin is carried. "separate-cell" (registered today): the module compiler and rails.supply_variants refuse a supply-variant group
#: with no candidate column, so lock + in-row twin (c3) cannot be compiled; the twin is a second whole-pipeline flight. "in-row": the engineering
#: design's c3 shape (Perception + lock + twin in one flight), registrable when the harness admits a candidate-less twin group (decision 282).
TWIN_SHAPE = "separate-cell"
#: Reference figures of the design's c3 shape under the same formula (1 Perception + 2 Solver contacts per row): about 5.9 GPU-h, 6.6-8.5 h wall.
def modelled_expected_gpu_hours(rows: int, solver_contacts: int, *, budget: int | None = THINK_BUDGET_TOKENS) -> float:
    """The design's reference figure under the pre-smoke model (kept for the design record; never a registered ceiling)."""

    return rows * modelled_row_seconds(solver_contacts, budget=budget) / THINK_SLOTS / 3600.0


C3_EXPECTED_GPU_H = modelled_expected_gpu_hours(ROWS, 2)
C3_PLANNED_GPU_H = round(math.ceil(round(C3_EXPECTED_GPU_H * GPU_MARGIN / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)
#: The replicate each arm's ``stage3_measurement`` block names (instrument rule 3: the in-chain A/A of the cross-flight contrast).
REPLICATE_OF = {"lock": "aa", "aa": "lock"}


def eligible_run_ids() -> list[str]:
    """The decision receipt's eligible run ids: each cell's generation run id then its FIT run id, in chain order."""

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
    """rows x max_contacts x endpoints per contact (never run-cumulative): 8,640 for a 1,080-row cell."""

    return tf.fit_contact_cap(rows, CONTACTS_PER_ROW)


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(key: str, plan_kind: str) -> str:
    return f"{CELLS[key]['prefix']}{plan_kind}-plan-registered-v1.json"


def roster_doc(kind: str) -> dict:
    return json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))


def roster_audio(kind: str) -> float:
    return sum(float(item["audio_seconds"]) for item in roster_doc(kind)["items"])


def audio_cap(kind: str) -> int:
    """Every contact re-sends the row's speech packet, a fallback re-ask included: ceil(roster audio seconds x (contacts + fallback contacts per row))."""

    return math.ceil(roster_audio(kind) * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING) - 1e-9)


def generation_calls(key: str) -> int:
    """The plan ceiling: rows x (program contacts + fallback contacts per row), the rule rails.runner applies (core.reasoning_knobs)."""

    return CELLS[key]["rows"] * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING)


def program_calls(key: str) -> int:
    """The program maximum without fallbacks."""

    return CELLS[key]["rows"] * CONTACTS_PER_ROW


def thinking_promotion_sha256() -> str:
    """The sha256 of the Thinking packet root's promotion receipt, as pinned by the 266-E Thinking baseline (a committed config; no data read)."""

    path = REPO_ROOT / "configs" / "baseline" / f"{BASELINE_FOR_PINS}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("speech_packet_promotion_receipt") != THINK_PROMOTION_RECEIPT:
        raise SystemExit(f"{BASELINE_FOR_PINS} pins {doc.get('speech_packet_promotion_receipt')!r}, expected {THINK_PROMOTION_RECEIPT!r}")
    sha = doc.get("speech_packet_promotion_receipt_sha256", "")
    if len(sha) != 64 or sha == dfb.UNPINNED_SHA:
        raise SystemExit(f"{BASELINE_FOR_PINS} does not carry a real promotion-receipt sha256")
    return sha


__all__ = [name for name in globals() if not name.startswith("_")]
