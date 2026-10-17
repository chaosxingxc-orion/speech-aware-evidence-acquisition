"""Shared identities of NX-T R2b: the Solver REASONING-BUDGET RAISE on the Thinking core, TRAIN Fold B (one candidate arm, per-node completion caps).

One module, imported by the derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It follows the NX-T R2 package form
(``nxt_r2_family``) and reuses what R2 reused: ``thinking_system_family`` (the Thinking model fragment family, packet root and its pinned promotion receipt, the
lock v2.2 + v4g plain-lock program, the Fold B roster), ``tfrl_family`` (the FIT arithmetic and the derive helpers) and ``recovery`` (the generic rec1 mechanism).
R2's own files are not changed.

WHAT THE CELL IS. NX-T R1 (which nodes need thinking at all) read the Solver NEEDS-THINKING and showed that 19 of its 51 smoke contacts hit the forced close at the
3,072-token budget (completion p90 3,128): the Solver's reasoning is truncated. Owner rulings 323 and 325 A (2026-10-17): raise the Solver's reasoning budget and its
completion cap so that Solver reasoning is no longer truncated, in ONE candidate arm, as a same-flight COLUMN beside the delivering arm. Every arm contacts Perception
and the Solver; the arms differ ONLY in the reasoning budget and completion cap of their own Solver contact (``roles.perception.thinking_variants``, receipt schema v5,
unchanged). The arm set is DATA (``nxt_r2b_arms.json``), now with a completion cap per node setting:

  ``solver-6144``   Perception at the lock form (budget 3,072 / reserve 1,024 / cap 4,096); the Solver at reasoning_budget_tokens 6,144, answer reserve 1,024, cap 7,168
  ``budget-3072``   the delivering arm = the 268-B lock form on BOTH nodes (budget 3,072 / reserve 1,024 / cap 4,096): its requests are the lock's, byte for byte

THE FRAGMENT AND THE PER-NODE POLICY. The serving fragment named after the largest cap (``...-budget3072-max7168-v1``) has decoding max_tokens 7,168 (the geometry cap that
admits the Solver's 7,168-token request). Its fragment defaults (budget 3,072, reserve 4,096) are NOT the delivering form, so the baseline carries a CELL-LEVEL
``thinking_policy`` that states the lock form (3,072 + 1,024 = 4,096) on both nodes; the candidate arm's policy overrides only its Solver node. ``max_tokens`` is a request
parameter: the GPU geometry (``-c 98304 -np 4``, four 24,576-token slots) and its receipt are the np4 session's, unchanged.

NO TWIN (owner decision 313 A): the in-flight A/A offset on this core is measured twice (268-B SLU +1.15 / intent -0.09; P3.1 SLU -0.61 / intent +1.60), so the column reads
against the DECLARED offset |o| = 1.15 pp SLU and the paired floor 0.7 pp; exactly one candidate arm (owner ruling 325 A).

GPU CEILING. The cost of an arm is its predicted seconds per row relative to the delivering arm, from the NX-T R1 measured per-node contact seconds of the both-on arm
(``nxt_r2b_cost_inputs.json``: Perception 47.82 s, Solver 62.21 s per contact, 110.03 s per row, 8.25 GPU-h per 1,080-row pass at 4 slots) with every RAISED node's contact
seconds scaled by its budget ratio (conservative: only the contacts that hit the forced close can grow), registered ROUNDED UP to 0.01. The arm mix is their sum with the
delivering arm's 1.0:
    expected GPU-h = rows x arm mix / rows-per-minute / 60            (rows per minute = 4 slots x 60 / 110.03 s, registered rounded DOWN to 0.01)
    ceiling        = ceil_0.1( expected x 1.3 )
Ceilings are bounds, never targets. The four-row smoke keeps the 0.5 GPU-h form allowance.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIRECT_DIR = HERE.parent / "direct"
TFRL_DIR = HERE.parent / "tfrl"
LIB_DIR = HERE.parent / "lib"
for _dir in (HERE, DIRECT_DIR, TFRL_DIR, LIB_DIR):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import thinking_system_family as tsf  # noqa: E402
import tfrl_family as tf  # noqa: E402
import recovery as rcv  # noqa: E402

REPO_ROOT = tf.REPO_ROOT

DATE = "2026-10-17"
SLUG = "nxt-r2b-solver-budget-fold-b"
SHORT = "nxt2b"
PKG_NAME = "slurp-nxt-r2b-solver-budget-fold-b-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
SIGNOFF_CONDITIONS = f"{PACKAGE}/signoff-conditions-v1.json"      # emitted by the derive, INSIDE the package (R2's sat beside it and went stale)
DECISION_ID = "slurp-nxt-r2b-solver-budget-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1"
RECIPE_ID = "slurp-nxt-r2b-solver-budget-fold-b-read-v1"
READER = "scripts/analysis/slurp_nxt_r2b_solver_budget_column_read.py"
READER_IMPL = "scripts/analysis/slurp_nxt_thinking_budget_column_read.py"      # the R2 reader, parameterised by this family
ANALYSIS_ROOT = f"analysis/{READ_RUN_ID}"
LEDGER_MARK = ("## Cell NXT-R2B: the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B (one flight, one candidate arm plus the delivering arm; "
               "smoke then 1,080 rows)")
OWNER_RULINGS = "owner rulings 323 and 325 A (2026-10-17), 313 A (2026-10-14) and 304/307 (2026-10-13), coordinator approval of the NX-T R2b design"
SMOKE_SCHEMA = "saea-nxt-r2b-solver-budget-column-smoke-v1"
READ_SCHEMA = "saea-nxt-r2b-solver-budget-column-read-v1"
READ_TITLE = "NX-T R2b read -- the Solver reasoning-budget raise"
WORD_MODE = "raise"                                         # the reader's word set for a budget ABOVE the delivering one (see the reader)

# ---- the system and the roster: exactly the 268-B lock, one flight --------------------------------------------------------------
ROWS, SMOKE_ROWS = tsf.ROWS, tsf.SMOKE_ROWS
LOCK, PROGRAM_BASE = tsf.LOCK, tsf.PROGRAM                 # v2.2; the plain lock program phase-native-module-v1-c2 (the base the column adds to)
SCORER = tsf.SCORER
DATASET, SPLIT_ID = tsf.DATASET, tsf.SPLIT_ID
TUNING_ROSTER, READ_ROSTER = "none", tsf.READ_ROSTER
ROSTER = dict(tsf.ROSTER)
PARENT = tsf.CELLS                                          # the 268-B cells the baselines/experiments are derived from (lock + smoke)
PARENT_SMOKE_KEY, PARENT_ARM_KEY = "smoke", "lock"

# ---- the arm table (DATA: nxt_r2b_arms.json) ----------------------------------------------------------------------------------------
ARMS_PATH = HERE / "nxt_r2b_arms.json"
ARM_TABLE_SCHEMA = "saea-nxt-r2b-arm-table-v1"
NODES = ("perception", "solver")
OFF = "off"                                                 # reader compatibility only: R2b has no no-think node
MAX_CANDIDATE_ARMS = 1                                      # owner ruling 325 A: ONE candidate arm
MIN_BUDGET_TOKENS = 128
DELIVERING_BUDGET = tsf.THINK_BUDGET_TOKENS                 # 3,072: the lock form
COMPLETION_CAP = tsf.THINK_MAX_TOKENS                       # 4,096: the delivering cap (never moves for a node at or below the delivering budget)
ANSWER_RESERVE_FLOOR = tsf.THINK_ANSWER_RESERVE_TOKENS      # 1,024: no node's answer reserve shrinks below the lock's
DELIVERING = f"budget-{DELIVERING_BUDGET}"                  # the delivering arm's id (thinking_frame.delivering_arm_id)
DELIVERING_SETTING = {"budget_tokens": DELIVERING_BUDGET, "completion_cap": COMPLETION_CAP}
TWIN = None                                                 # owner decision 313 A: no twin arm
_ARM_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ArmTableError(ValueError):
    """The arm table is malformed or breaks a registered rule (fail closed, by name)."""


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_node_setting(value: object, where: str, fragment_cap: int) -> dict:
    """One node's setting: exactly ``{budget_tokens, completion_cap}``. A budget above the delivering one is accepted only with a cap that leaves the 1,024-token
    answer reserve above it; a node at or below the delivering budget keeps the delivering cap; no cap exceeds the fragment's geometry cap."""

    if not isinstance(value, dict) or set(value) != {"budget_tokens", "completion_cap"}:
        raise ArmTableError(f"{where} must be exactly {{budget_tokens, completion_cap}}")
    budget, cap = value["budget_tokens"], value["completion_cap"]
    if not _int(budget) or not _int(cap):
        raise ArmTableError(f"{where}: budget_tokens and completion_cap must be integers, got {budget!r} / {cap!r}")
    if budget < MIN_BUDGET_TOKENS:
        raise ArmTableError(f"{where}.budget_tokens {budget} is below {MIN_BUDGET_TOKENS}: a budget that small measures a different thing (the forced close fires almost at once)")
    if cap < budget + ANSWER_RESERVE_FLOOR:
        raise ArmTableError(f"{where}: completion_cap {cap} must be >= budget_tokens + {ANSWER_RESERVE_FLOOR} = {budget + ANSWER_RESERVE_FLOOR} (the answer reserve never shrinks below the lock's)")
    if budget <= DELIVERING_BUDGET and cap != COMPLETION_CAP:
        raise ArmTableError(f"{where}: a node at or below the delivering budget {DELIVERING_BUDGET} keeps the delivering completion cap {COMPLETION_CAP}, got {cap}")
    if cap > fragment_cap:
        raise ArmTableError(f"{where}: completion_cap {cap} exceeds the serving fragment's geometry cap {fragment_cap}")
    return {"budget_tokens": budget, "completion_cap": cap}


def validate_arm_table(table: object) -> tuple[list[dict], int]:
    """Validate the arm-table document; return ``(candidate arms in declared order, fragment completion cap)``. Every refusal names the rule."""

    keys = {"_note", "answer_reserve_floor_tokens", "arms", "delivering", "fragment_completion_cap", "schema"}
    if not isinstance(table, dict) or set(table) != keys:
        raise ArmTableError(f"the arm table must be exactly {sorted(keys)}")
    if table["schema"] != ARM_TABLE_SCHEMA:
        raise ArmTableError(f"schema must be {ARM_TABLE_SCHEMA!r}")
    if table["delivering"] != DELIVERING_SETTING:
        raise ArmTableError(f"the decoding knobs of the delivering arm never move: {DELIVERING_SETTING}")
    if table["answer_reserve_floor_tokens"] != ANSWER_RESERVE_FLOOR:
        raise ArmTableError(f"answer_reserve_floor_tokens must be {ANSWER_RESERVE_FLOOR}")
    fragment_cap = table["fragment_completion_cap"]
    if not _int(fragment_cap) or fragment_cap < COMPLETION_CAP:
        raise ArmTableError(f"fragment_completion_cap must be an integer >= {COMPLETION_CAP}")
    arms = table["arms"]
    if not isinstance(arms, list) or not 1 <= len(arms) <= MAX_CANDIDATE_ARMS:
        raise ArmTableError(f"between 1 and {MAX_CANDIDATE_ARMS} candidate arm per round (owner ruling 325 A; no twin)")
    seen_ids: set[str] = set()
    seen_settings: set[str] = set()
    out = []
    for position, arm in enumerate(arms):
        where = f"arms[{position}]"
        if not isinstance(arm, dict) or set(arm) != {"arm_id", *NODES}:
            raise ArmTableError(f"{where} must be exactly {{arm_id, perception, solver}}")
        arm_id = arm["arm_id"]
        if not isinstance(arm_id, str) or not _ARM_ID.match(arm_id) or arm_id == DELIVERING or arm_id in seen_ids:
            raise ArmTableError(f"{where}.arm_id {arm_id!r} must be a distinct lower-case id other than the delivering arm {DELIVERING!r}")
        seen_ids.add(arm_id)
        settings = {node: validate_node_setting(arm[node], f"{where}.{node}", fragment_cap) for node in NODES}
        if all(settings[node] == DELIVERING_SETTING for node in NODES):
            raise ArmTableError(f"{where} sets both nodes to the delivering setting: it would duplicate the delivering arm")
        key = json.dumps([settings[node] for node in NODES], sort_keys=True)
        if key in seen_settings:
            raise ArmTableError(f"{where} repeats the setting of an earlier arm: two spellings of one configuration spend a contact per row and measure nothing")
        seen_settings.add(key)
        out.append({"arm_id": arm_id, **settings})
    largest = max(arm[node]["completion_cap"] for arm in out for node in NODES)
    if fragment_cap != max(largest, COMPLETION_CAP):
        raise ArmTableError(f"fragment_completion_cap {fragment_cap} must equal the largest node cap of the table ({max(largest, COMPLETION_CAP)}): the serving fragment is named after it")
    return out, fragment_cap


def node_policy(setting: dict) -> dict | None:
    """The per-node ``thinking_policy`` entry of one node setting (``None`` = the locked form, no override). Both the budget and the reserve are stated, so the
    node's ``max_tokens`` is budget + reserve = its own cap whatever the fragment defaults are."""

    if setting == DELIVERING_SETTING:
        return None
    return {"reasoning_budget_tokens": int(setting["budget_tokens"]), "answer_reserve_tokens": int(setting["completion_cap"]) - int(setting["budget_tokens"])}


def policy_of(arm: dict) -> dict:
    return {node: entry for node in NODES if (entry := node_policy(arm[node])) is not None}


def load_arm_table(path: Path = ARMS_PATH) -> tuple[list[dict], int]:
    return validate_arm_table(json.loads(Path(path).read_text(encoding="utf-8")))


ARM_SPECS, FRAGMENT_CAP = load_arm_table()
#: arm id -> its per-node override map (``core.reasoning_knobs.NODE_POLICY_KEYS`` per role kind); the delivering arm declares none (its form is the cell-level policy).
POLICIES = {arm["arm_id"]: policy_of(arm) for arm in ARM_SPECS}
#: arm id -> (Perception setting, Solver setting); the delivering arm is the lock form on both nodes.
SETTINGS = {arm["arm_id"]: (arm["perception"], arm["solver"]) for arm in ARM_SPECS}
SETTINGS[DELIVERING] = (dict(DELIVERING_SETTING), dict(DELIVERING_SETTING))
#: reader tables: arm -> node -> reasoning budget / completion cap
NODE_BUDGETS = {arm: {node: s["budget_tokens"] for node, s in zip(NODES, settings)} for arm, settings in SETTINGS.items()}
NODE_CAPS = {arm: {node: s["completion_cap"] for node, s in zip(NODES, settings)} for arm, settings in SETTINGS.items()}
CANDIDATE_ARMS = tuple(POLICIES)
ARM_ORDER = (*CANDIDATE_ARMS, DELIVERING)                   # declared order; the delivering arm LAST
K = len(ARM_ORDER)
CONTACTS_PER_ROW = 2 + 2 * (K - 1)                          # review-off base 2 + one Perception and one Solver contact per non-delivering arm (c4 for one candidate)
PROGRAM = f"phase-native-module-v1-c{CONTACTS_PER_ROW}"
#: The CELL-LEVEL thinking_policy of the baseline: the lock form (budget 3,072 + reserve 1,024 = cap 4,096) stated for BOTH nodes, because the fragment's own defaults
#: carry the geometry cap (budget 3,072, reserve 4,096, max_tokens 7,168). An arm's policy is composed on top of it.
DELIVERING_NODE_POLICY = {node: {"reasoning_budget_tokens": DELIVERING_BUDGET, "answer_reserve_tokens": COMPLETION_CAP - DELIVERING_BUDGET} for node in NODES}
#: Budgeted-thinking contacts per row (an answer-only fallback re-ask is possible only for a budgeted thinking request): the delivering arm's 2 plus every candidate
#: node (every node of an R2b arm still thinks).
THINKING_CONTACTS_PER_ROW = 2 + len(ARM_SPECS) * len(NODES)
FALLBACK_CONTACTS_PER_ROW_CEILING = THINKING_CONTACTS_PER_ROW   # the runner requires >= 2 for the module family, a larger plan is legal

# ---- the Thinking serving geometry: a NEW session id for the raised cap, the np4 x 24,576 server geometry unchanged -------------------------------
FRAGMENT_NAME = f"q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget{DELIVERING_BUDGET}-max{FRAGMENT_CAP}-v1"
SESSION_NAME = f"serving-slurp-thinking-module-fold-b-np4-budget{DELIVERING_BUDGET}-max{FRAGMENT_CAP}-v1"
SWAP_TARGET = f"think-budget{FRAGMENT_CAP}-np4"
SERVING_LIB = "scripts/flights/batch/serving_lib.sh"
GEOMETRY_LEAVES = ("decoding_params.max_tokens", "answer_reserve_tokens", "geometry_basis")    # the ONLY fragment leaves that differ from the resident np4 fragment
CONTROL_FRAGMENT = tsf.THINK_MODEL                          # the resident np4 session's fragment (budget3072-max4096): the geometry reference of the receipt


def _serving_lib_row(target: str, root: Path) -> dict | None:
    path = Path(root) / SERVING_LIB
    if not path.is_file():
        return None
    match = re.search(rf"^\s*{re.escape(target)}\)\s*\n(.*?);;", path.read_text(encoding="utf-8"), re.M | re.S)
    if not match:
        return None
    sid, fragment = re.search(r"G_SID=(\S+)", match.group(1)), re.search(r"G_FRAGMENT=(\S+)", match.group(1))
    return {"session": sid.group(1), "model_fragment": fragment.group(1)} if sid and fragment else None


def resolve_geometry(target: str = SWAP_TARGET, root: Path | str | None = None) -> dict:
    """Resolve a serving target to its session, model fragment and slot geometry from the serving_lib row and the fragment on disk. Raises ``ValueError``."""

    root = Path(root) if root else REPO_ROOT
    row = _serving_lib_row(target, root)
    if row is None:
        raise ValueError(f"unknown serving geometry target {target!r}: no row in {SERVING_LIB}")
    fragment_path = root / "configs" / "model" / f"{row['model_fragment']}.json"
    if not fragment_path.is_file():
        raise ValueError(f"geometry {target!r}: model fragment {fragment_path} is not on disk")
    args = json.loads(fragment_path.read_text(encoding="utf-8"))["server_args"]
    total, slots = int(args[args.index("-c") + 1]), int(args[args.index("-np") + 1])
    return {"target": target, "session": row["session"], "model_fragment": row["model_fragment"], "source": f"{SERVING_LIB} geometry row", "fragment_present": True,
            "fragment_path": f"configs/model/{row['model_fragment']}.json", "slots": slots, "slot_tokens": total // slots, "provisional": False}


ACTIVE_GEOMETRY = resolve_geometry()
THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET, THINK_SLOTS = (ACTIVE_GEOMETRY["session"], ACTIVE_GEOMETRY["model_fragment"], ACTIVE_GEOMETRY["target"],
                                                              ACTIVE_GEOMETRY["slots"])
if (THINK_MODEL, THINK_SESSION, THINK_SWAP_TARGET) != (FRAGMENT_NAME, SESSION_NAME, SWAP_TARGET):
    raise ValueError("serving_lib.sh row of the R2b target does not match the names derived from the arm table")
#: R2b has ONE geometry: the smoke and the column flight run on the same (new) session, so the chain's smoke / arm segments share it.
CONTROL_SESSION, CONTROL_MODEL, CONTROL_SWAP_TARGET = THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET
CONTROL_SLOTS, CONTROL_SLOT_TOKENS = THINK_SLOTS, ACTIVE_GEOMETRY["slot_tokens"]
DEFAULT_GEOMETRY = THINK_SWAP_TARGET


def geometry_of(key: str) -> dict:
    return ACTIVE_GEOMETRY


def think_model_text(key: str) -> str:
    """The ledger model/tool text of a cell (the np4 server geometry, the raised fragment cap, the per-node working caps)."""

    g = ACTIVE_GEOMETRY
    return ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, "
            f"c{g['slots'] * g['slot_tokens']} np{g['slots']} x {g['slot_tokens']:,} max{FRAGMENT_CAP} geometry cap (delivering form: reasoning budget {DELIVERING_BUDGET}, cap "
            f"{COMPLETION_CAP}; candidate Solver: budget {max(a['solver']['budget_tokens'] for a in ARM_SPECS)}, cap {FRAGMENT_CAP}), q8_0 KV, "
            f"--reasoning-format deepseek (model fragment {g['model_fragment']}); its own promoted speech packets; module program {PROGRAM}; "
            "per-arm reasoning budget and completion cap at the named node; no tool authority")


THINK_PACKET_ROOT, THINK_PROMOTION_RECEIPT = tsf.THINK_PACKET_ROOT, tsf.THINK_PROMOTION_RECEIPT
THINKING_KNOBS = json.loads(json.dumps(tsf.THINKING_KNOBS))
#: A raised or budget node's wire form: ``thinking_budget_tokens`` b, ``max_tokens`` the node's own cap, so the answer reserve is cap - b (never below 1,024).
BUDGET_NODE_KNOBS = {"thinking_budget_tokens": "b (the arm's setting)", "answer_reserve_tokens": "cap - b (>= 1024)", "max_tokens": "the node's own completion_cap",
                     "chat_template_kwargs": {"enable_thinking": True}}
NO_THINK_KNOBS = None                                       # R2b has no no-think node

# ---- external references (the 268-B and P3.1 reads; development numbers) ---------------------------------------------------------
THINKING_SYSTEM_SLU, THINKING_SYSTEM_INTENT = 71.61, 85.00                  # 268-B lock arm
TWIN_OFFSET_268B_SLU_PP, TWIN_OFFSET_268B_INTENT_PP = 1.15, -0.09            # 268-B cross-flight twin offset
TWIN_OFFSET_P31_SLU_PP, TWIN_OFFSET_P31_INTENT_PP = -0.61, 1.60              # P3.1 (DEV-2000-ADDED) cross-flight twin offset
DECLARED_OFFSET_SLU_PP = 1.15                                               # |o|: the larger of the two measured same-core A/A offsets, declared (decision 313 A)
PAIRED_FLOOR_PP = 0.7                                                       # the same-flight paired half-width (decisions 172/231/313)
FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65                                  # decision 190 node-column floors at n = 1,080 (the no-resolved-effect margins)
EXPECTED_EFFECT_PP = 0.0                                                    # the question is whether untruncated Solver reasoning moves the score at all; no effect is assumed

# ---- budget arithmetic (one place) ---------------------------------------------------------------------------------------------------
COST_INPUTS_PATH = HERE / "nxt_r2b_cost_inputs.json"
COST_INPUTS = json.loads(COST_INPUTS_PATH.read_text(encoding="utf-8"))
R1 = COST_INPUTS["r1_measured"]
NODE_SECONDS = {"perception": float(R1["perception_seconds_per_contact_mean"]), "solver": float(R1["solver_seconds_per_contact_mean"])}
SECONDS_PER_ROW_BOTH_ON = float(R1["seconds_per_row_both_on"])
R1_SLOTS = int(R1["slots"])


def ceil_hundredth(value: float) -> float:
    return math.ceil(round(value * 100.0, 9)) / 100.0


def floor_hundredth(value: float) -> float:
    return math.floor(round(value * 100.0, 9)) / 100.0


def relative_cost(arm: str, *, exact: bool = True) -> float:
    """An arm's predicted seconds per row over the delivering arm's measured seconds per row: each node's contact seconds, scaled by the node's budget over the
    delivering budget when the node is RAISED. A node below the delivering budget is outside this cost model (refused by name)."""

    seconds = 0.0
    for node in NODES:
        budget = NODE_BUDGETS[arm][node]
        if budget < DELIVERING_BUDGET:
            raise ValueError(f"the R2b cost model covers only raised budgets (budget >= {DELIVERING_BUDGET}); {arm} {node} is at {budget}")
        seconds += NODE_SECONDS[node] * (budget / DELIVERING_BUDGET)
    return seconds / (NODE_SECONDS["perception"] + NODE_SECONDS["solver"])


#: arm id -> registered cost in full delivering rows per row (the model's predicted seconds per row relative to the delivering arm, rounded UP to 0.01).
ROW_COST = {arm: ceil_hundredth(relative_cost(arm)) for arm in CANDIDATE_ARMS}
ROW_COST[DELIVERING] = 1.0
LINEAR_REFERENCE = {arm: round(relative_cost(arm), 4) for arm in CANDIDATE_ARMS}      # the model IS linear in the budget ratio; the unrounded cost
ARM_MIX_ROWS = round(sum(ROW_COST.values()), 2)
#: rows per minute of a delivering-only pass at the R1-measured seconds per row and 4 slots, registered rounded DOWN to 0.01 (a lower rate means more GPU-hours).
ROWS_PER_MINUTE_FULL = floor_hundredth(R1_SLOTS * 60.0 / SECONDS_PER_ROW_BOTH_ON)
GPU_MARGIN, GPU_ROUND_H = tf.GPU_PLAN_MARGIN, tf.GPU_PLAN_ROUND_H
SMOKE_GPU_HOURS = tsf.SMOKE_GPU_HOURS


def expected_gpu_hours(rows: int) -> float:
    """rows x arm mix / rows per minute / 60 (unrounded)."""

    return rows * ARM_MIX_ROWS / ROWS_PER_MINUTE_FULL / 60.0


def planned_gpu_hours(rows: int) -> float:
    """The registered ceiling: ``ceil_0.1( expected x 1.3 )``."""

    hours = expected_gpu_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def arm_row_equivalent_rows_per_minute(arm: str) -> float:
    return ROWS_PER_MINUTE_FULL / ROW_COST[arm]


def lock_flight_gpu_hours(arm: str, rows: int = ROWS) -> float:
    """The projected GPU-h of a ``rows``-row LOCK flight that ran only this arm's setting on both nodes, at the registered rate."""

    return rows / arm_row_equivalent_rows_per_minute(arm) / 60.0


# ---- the context fit of the raised cap (the registered FIT_ESTIMATE form) -----------------------------------------------------------------
#: The live prompt limit of one request is slot - operational reserve - completion ceiling - special reserve, and the ceiling of the fit gate is the cell's
#: geometry cap (the FRAGMENT's max_tokens, 7,168), so the gate holds EVERY contact of the cell to it (``FlightRuntime._completion_token_ceiling``).
SLOT_TOKENS, RESERVE_TOKENS, SPECIAL_RESERVE = tsf.SLOT_TOKENS, tsf.RESERVE_TOKENS, tsf.SPECIAL_RESERVE
PROMPT_LIMIT = SLOT_TOKENS - RESERVE_TOKENS - FRAGMENT_CAP - SPECIAL_RESERVE                # 14,334 at the 7,168 cap
PROMPT_LIMIT_THINKING = tsf.PROMPT_LIMIT_THINKING                                           # 17,406 at the 4,096 cap (the 268-B lock's)
SOLVER_PROMPT_TOKENS_MAX = tsf.SOLVER_PROMPT_TOKENS_MAX                                     # 14,641: the Instruct-lock maximum (fit-measure-v1)
FIT_ESTIMATE = {"base_prompt_tokens": 2000, "completion_ceiling": FRAGMENT_CAP, "slot_tokens": SLOT_TOKENS, "tokens_per_supplied_item": 235}
LOCK_MAX_SUPPLIED_ITEMS = tf.DELIVERING_MAX_SUPPLIED_ITEMS                                  # 55: the 268-B lock's own bound (fits at 4,096, NOT at 7,168)
OBSERVATIONS = {item["id"]: item for item in COST_INPUTS["fit_observations"]["sets"]}
OBSERVED_SOLVER_PROMPT_MAX = max(item["solver_prompt_tokens_max"] for item in OBSERVATIONS.values())
OBSERVED_SUPPLIED_COUNT_MAX = max(item.get("supplied_count_max", 0) for item in OBSERVATIONS.values())


def estimated_prompt_tokens(items: int) -> int:
    return FIT_ESTIMATE["base_prompt_tokens"] + items * FIT_ESTIMATE["tokens_per_supplied_item"]


#: The thinking_variants fit estimate (``rails.supply_variants.parse_perception_thinking_variants``) refuses an arm whose estimated prompt exceeds the limit, so the bound is the
#: largest item count the registered estimate admits at the 7,168 ceiling, never more than the lock's 55.
MAX_SUPPLIED_ITEMS = min(LOCK_MAX_SUPPLIED_ITEMS, (PROMPT_LIMIT - FIT_ESTIMATE["base_prompt_tokens"]) // FIT_ESTIMATE["tokens_per_supplied_item"])


def fit_proof() -> dict:
    """The context-fit proof of the raised cap, registered in the fit plan; ``ok`` is False (and the derive REFUSES) when the live slot cannot hold the Solver prompt plus
    the 7,168-token cap: the registered estimate at the chosen item bound, the measured Solver prompt maxima of the sealed Fold B flights, and the observed supplied count
    against the bound."""

    estimate = estimated_prompt_tokens(MAX_SUPPLIED_ITEMS)
    checks = {
        "estimate_at_bound_fits": estimate <= PROMPT_LIMIT,
        "observed_solver_prompt_max_fits": OBSERVED_SOLVER_PROMPT_MAX <= PROMPT_LIMIT,
        "observed_supplied_count_within_bound": OBSERVED_SUPPLIED_COUNT_MAX <= MAX_SUPPLIED_ITEMS,
        "slot_holds_prompt_plus_cap": OBSERVED_SOLVER_PROMPT_MAX + FRAGMENT_CAP <= SLOT_TOKENS,
        "bound_is_positive": MAX_SUPPLIED_ITEMS >= 1,
    }
    return {
        "slot_tokens": SLOT_TOKENS, "slots": ACTIVE_GEOMETRY["slots"], "reserve_tokens": RESERVE_TOKENS, "special_reserve_tokens": SPECIAL_RESERVE,
        "completion_cap": FRAGMENT_CAP, "prompt_limit_tokens": PROMPT_LIMIT, "control_prompt_limit_tokens_at_4096": PROMPT_LIMIT_THINKING,
        "fit_estimate": dict(FIT_ESTIMATE), "lock_max_supplied_items": LOCK_MAX_SUPPLIED_ITEMS,
        "lock_bound_estimate_tokens": estimated_prompt_tokens(LOCK_MAX_SUPPLIED_ITEMS), "lock_bound_fits_at_cap": estimated_prompt_tokens(LOCK_MAX_SUPPLIED_ITEMS) <= PROMPT_LIMIT,
        "max_supplied_items": MAX_SUPPLIED_ITEMS, "estimate_at_bound_tokens": estimate, "estimate_headroom_tokens": PROMPT_LIMIT - estimate,
        "observed_solver_prompt_tokens_max": OBSERVED_SOLVER_PROMPT_MAX, "observed_headroom_tokens": PROMPT_LIMIT - OBSERVED_SOLVER_PROMPT_MAX,
        "instruct_lock_solver_prompt_max_fit_measure_v1": SOLVER_PROMPT_TOKENS_MAX, "observed_supplied_count_max": OBSERVED_SUPPLIED_COUNT_MAX,
        "observations": json.loads(json.dumps(OBSERVATIONS)), "checks": checks, "ok": all(checks.values()),
        "note": ("The registered estimate (base 2,000 + 235 per supplied item) at the lock's bound of 55 items is 14,925 tokens, ABOVE the 14,334-token limit of the 7,168 cap, so the "
                 "thinking_variants parser would refuse the block; the bound is therefore the largest count the estimate admits (52). The bound only parameterises that estimate and a "
                 "runtime refusal of a branch that supplies more items than it; the request bytes of the delivering arm are unchanged, and the sealed Fold B flights supplied at most "
                 f"{OBSERVED_SUPPLIED_COUNT_MAX} items on {OBSERVATIONS['nxt-r1-fold-b-all-five-arms']['supplied_count_rows']} branch rows. The context-fit policy is compact-or-abstain, and the "
                 "measured Solver prompt maximum of the sealed Fold B flights is below the limit."),
    }


# ---- the single recovery (rec1) of a cell --------------------------------------------------------------------------------------------
#: A (run_id, attempt_id) pair is a one-time key, so a cell whose attempt stopped is re-flown WHOLE under the ``-rec1`` attempt ids (generation AND the live
#: phase fit) with a plan that carries the original plan plus the failed attempt's realised spend (run-cumulative). Generic mechanism:
#: ``scripts/flights/lib/recovery.py``. ``RECOVERIES`` is EMPTY on the first registration; the rec1 path is data-driven: the coordinator commits
#: ``<package>/predecessor-snapshot-arm-rec1-v1.json`` (``recovery.py snapshot``) and ``<package>/recovery-input-arm-v1.json`` (the diagnosis text, below) and the
#: family builds ``RECOVERIES["arm"]`` from them. The failed attempt's spend is the snapshot's, never typed here.
REC = rcv.REC
PREDECESSOR_SNAPSHOT = {"arm": f"{PACKAGE}/predecessor-snapshot-arm-rec1-v1.json"}
RECOVERY_INPUT = {"arm": f"{PACKAGE}/recovery-input-arm-v1.json"}
RECOVERY_INPUT_KEYS = ("recovered_at", "ledger_title", "agent", "reason", "root_cause", "fix", "decision")


def build_arm_recovery(inputs: dict, snap: dict) -> dict:
    """The arm cell's recovery record from the committed diagnosis ``inputs`` and the predecessor ``snap`` receipt."""

    missing = [k for k in RECOVERY_INPUT_KEYS if not inputs.get(k)]
    if missing:
        raise ValueError(f"the recovery input misses {missing}")
    fit = snap.get("fit") or {}
    calls, audio = snap["actual_calls"], snap["actual_audio_seconds"]
    return {
        "recovery_index": 1,
        "recovered_at": inputs["recovered_at"],
        "ledger_title": inputs["ledger_title"],
        "agent": inputs["agent"],
        "registered_at_utc": None,                      # the writer's --recovery-registered-at
        "base_commit": None,                            # the writer's --recovery-base-commit
        "worktree": None,
        "branch": None,
        "predecessor_attempt_id": snap["attempt_id"],
        "predecessor_fit_run_id": fit["run_id"],
        "predecessor_fit_attempt_id": fit["attempt_id"],
        "fit_predecessor_phrase": (f"no attempt record was opened for it, its prepared directory holds {fit.get('prepared_request_fit_envelopes', 0):,} "
                                   "request-fit envelopes preserved unread on the data root"),
        "predecessor_state": (f"{snap['state']}; {calls:,} calls / {audio:.2f} speech-seconds realised per its attempt record (reserved "
                              f"{snap['reserved_calls']:,} / {snap['reserved_audio_seconds']:,.0f}); preserved unread."),
        "predecessors": [rcv.predecessor_from_snapshot(snap)],
        "reason": inputs["reason"],
        "root_cause": inputs["root_cause"],
        "amendment": (f"RECOVERY {inputs['recovered_at']} (the cell's single one; {inputs['decision']}). The generation budget is run-cumulative across the "
                      "attempts of the run id (core/model/adapter.py; every attempt state counts, an OPENED one included), so the rec1 plan carries the original plan "
                      f"plus the failed attempt's recorded spend ({calls:,} calls, {audio:g} speech-seconds, read from the attempt record into "
                      f"{PREDECESSOR_SNAPSHOT['arm']}). The FIT cap is structural and unchanged (rows x program contacts x endpoints per contact). The FIT run id "
                      "and the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the "
                      "generation run id is unchanged. The registered GPU-hour ceiling does not change."),
        "fix": inputs["fix"],
        "unchanged": ("Unchanged: the smoke cell (sealed, signed off, not re-flown) and every registered knob, arm, policy, roster, prompt, geometry, cap and the "
                      "GPU-hour ceiling of the arm cell."),
        "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
        "fit_cap_rule": "The FIT cap is structural: rows x program contacts x endpoints per contact.",
    }


def _load_recoveries(root: Path = REPO_ROOT) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, rel in RECOVERY_INPUT.items():
        path = Path(root) / rel
        if path.is_file():
            out[key] = build_arm_recovery(json.loads(path.read_text(encoding="utf-8")), rcv.load_snapshot(Path(root) / PREDECESSOR_SNAPSHOT[key]))
    return out


RECOVERIES: dict[str, dict] = _load_recoveries()
for _rec in RECOVERIES.values():
    rcv.validate_recovery(_rec)


def recovery(key: str) -> dict | None:
    """The cell's recovery record, or ``None`` when the cell is on its first attempt."""

    return RECOVERIES.get(key)


def rec_suffix(key: str) -> str:
    return rcv.rec_suffix(RECOVERIES, key)


def predecessor_spend(key: str) -> tuple[int, float]:
    return rcv.predecessor_spend(RECOVERIES, key)


def cumulative_budget(key: str, original_calls: int, original_audio: float) -> tuple[int, int]:
    return rcv.cumulative_budget(RECOVERIES, key, original_calls, original_audio)


def _spec(key: str, role: str, rows: int, roster: str, scoring_jobs: int, gpu: float, *, ids_stem: str, parent_key: str) -> dict:
    up = ids_stem.upper()
    rec, rec_up = rec_suffix(key), rec_suffix(key).upper()
    parent = PARENT[parent_key]
    return {
        "key": key, "role": role, "rows": rows, "roster": roster, "gpu_hours": gpu, "scoring_jobs": scoring_jobs,
        "parent": parent_key, "parent_cell": parent["cell"], "parent_baseline": parent["baseline"], "slug": parent["slug"],
        "cell": f"slurp-native-stage3-{ids_stem}-v1",
        "baseline": f"slurp-native-stage3-{ids_stem}-baseline-v1",
        "run": f"SAEA-SLURP-STAGE3-{up}-V1",
        "fit_run": f"SAEA-SLURP-STAGE3-{up}-FIT{rec_up}-V1",
        "attempt": f"attempt-slurp-native-stage3-{ids_stem}-generation{rec}-v1",
        "fit_attempt": f"attempt-slurp-native-stage3-{ids_stem}-fit{rec}-v1",
        "model": THINK_MODEL, "session": THINK_SESSION,
        "prefix": "smoke-" if key == "smoke" else "",
        "campaign": f"configs/campaign/slurp-native-stage3-{ids_stem}-v1.json",
    }


CELLS = {
    "smoke": _spec("smoke", "four-row form smoke of the Solver reasoning-budget raise", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   ids_stem=f"{SLUG}-smoke-4", parent_key="smoke"),
    "arm": _spec("arm", f"Solver reasoning-budget raise column flight ({K} arms in one flight)", ROWS, "arm", 1, planned_gpu_hours(ROWS),
                 ids_stem=SLUG, parent_key="lock"),
}
ARM_KEYS = ("arm",)
ALL_KEYS = ("smoke", "arm")


def eligible_run_ids() -> list[str]:
    """The decision receipt's eligible run ids: each cell's generation run id then its first-registration FIT run id, in chain order, then the rec1 FIT run
    id of each recovered cell (the minted receipt of the first registration lists exactly the first four; the rec1 receipt appends the new FIT run id)."""

    out: list[str] = []
    for key in ALL_KEYS:
        rec = recovery(key)
        out += [CELLS[key]["run"], rec["predecessor_fit_run_id"] if rec else CELLS[key]["fit_run"]]
    out += [CELLS[key]["fit_run"] for key in ALL_KEYS if recovery(key)]
    return out


def eligible_attempt_ids() -> list[str]:
    """Each cell's attempt ids, in chain order; a recovered cell lists its first-attempt ids (superseded, spent) then its rec1 ids."""

    out: list[str] = []
    for key in ALL_KEYS:
        rec = recovery(key)
        if rec:
            out += [rec["predecessor_attempt_id"], rec["predecessor_fit_attempt_id"]]
        out += [CELLS[key]["attempt"], CELLS[key]["fit_attempt"]]
    return out


def fit_contact_cap(rows: int) -> int:
    """rows x program contacts x endpoints per contact (never run-cumulative)."""

    return tf.fit_contact_cap(rows, CONTACTS_PER_ROW)


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(key: str, plan_kind: str) -> str:
    """Package file name of a cell's registered plan; a recovered cell's plans carry the ``-rec1`` marker."""

    return rcv.plan_file_name(CELLS[key]["prefix"], plan_kind, key in RECOVERIES)


def superseded_plan_file_names(key: str) -> list[str]:
    """First-attempt plan names a recovery supersedes (removed from the package; the failed attempt stays on the data root)."""

    return rcv.superseded_plan_file_names(CELLS[key]["prefix"], key in RECOVERIES)


def roster_doc(kind: str) -> dict:
    return json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))


def roster_audio(kind: str) -> float:
    return sum(float(item["audio_seconds"]) for item in roster_doc(kind)["items"])


def audio_cap(kind: str) -> int:
    """Every contact re-sends the row's speech packet, a fallback re-ask included: ceil(roster audio seconds x (contacts + fallback contacts per row))."""

    return math.ceil(roster_audio(kind) * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING) - 1e-9)


def original_generation_calls(key: str) -> int:
    """The first-attempt plan ceiling: rows x (program contacts + fallback contacts per row)."""

    return CELLS[key]["rows"] * (CONTACTS_PER_ROW + FALLBACK_CONTACTS_PER_ROW_CEILING)


def generation_calls(key: str) -> int:
    """The plan ceiling: the original ceiling, plus the failed attempts' realised calls for a recovered cell (run-cumulative budget)."""

    return cumulative_budget(key, original_generation_calls(key), 0)[0]


def cell_audio_cap(key: str) -> int:
    """The cell's speech-second ceiling: the original cap, plus the failed attempts' realised seconds for a recovered cell (rounded up)."""

    return cumulative_budget(key, 0, audio_cap(CELLS[key]["roster"]))[1]


def program_calls(key: str) -> int:
    return CELLS[key]["rows"] * CONTACTS_PER_ROW


def extra_audio_seconds(kind: str) -> float:
    """The audio the K - 1 extra arms re-send: every extra arm adds one Perception and one Solver contact (2 (K - 1) extra contacts per row)."""

    return roster_audio(kind) * (CONTACTS_PER_ROW - 2)


def thinking_promotion_sha256() -> str:
    return tsf.thinking_promotion_sha256()


def signoff_conditions() -> dict:
    """The machine sign-off conditions (owner ruling 314 A; ``scripts/flights/batch/smoke_signoff.py``) FOR THIS ARM TABLE. The derive emits them inside the package, so
    a change of the table regenerates them (R2's sat beside its package and went stale)."""

    return {
        "schema": "saea-smoke-signoff-conditions-v1",
        "_note": (f"NX-T R2b machine sign-off conditions (owner ruling 314 A), emitted by nxt_r2b_derive_cells.py from {ARMS_PATH.name}; regenerated whenever the arm table changes. "
                  "The smoke's job is to show that every node closes within its own cap (no cap hit, no empty answer, no malformed JSON, no length finish), that the cost is no "
                  "more than 1.3x the registered arm mix, and that no column is absent or unattributed. No node is no-think in this round."),
        "package": PKG_NAME,
        "ruling": "owner ruling 314 A of 2026-10-14",
        "table_schema": SMOKE_SCHEMA,
        "table_relpath": f"{ANALYSIS_ROOT}/smoke-decode-cost.json",
        "expected_arms": sorted(ARM_ORDER),
        "min_contacts_per_node": 1,
        "no_think_nodes": {},
        "no_think_max": {"contacts_with_reasoning_chars": 0, "marker_in_content": 0, "reasoning_chars_mean": 0},
        "every_node_max": {"cap_hits": 0, "empty_content": 0, "no_json_object": 0, "finish_reason_length": 0},
        "arm_mix": {"max_ratio": 1.3, "measured_key": "arm_mix_measured_rows", "registered_key": "arm_mix_registered_rows"},
        "extras": [
            {"id": "unattributed-contacts", "path": "unattributed_contacts", "op": "==", "value": 0},
            {"id": "absent-columns", "path": "absent_columns", "op": "==", "value": 0},
        ],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
