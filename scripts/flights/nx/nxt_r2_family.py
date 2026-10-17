"""Shared identities of NX-T R2: the per-node REASONING-BUDGET column on the Thinking core, TRAIN Fold B.

One module, imported by the derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It reuses the 268-B family it
extends instead of restating it: ``thinking_system_family`` (the Thinking model fragment, session, packet root and its pinned promotion receipt, the lock
v2.2 + v4g plain-lock program, the Fold B roster), ``tfrl_family`` (the FIT arithmetic and the derive helpers) and ``recovery`` (the generic rec1 mechanism).

WHAT THE CELL IS. Owner rulings 304/307 (2026-10-13), 313 A and 318 A (2026-10-14): NX-T R1 asked which nodes need thinking at all; NX-T R2 asks how MUCH
reasoning each node needs. ONE flight of the locked system (the 268-B lock) on TRAIN Fold B (1,080 rows) with a same-flight COLUMN over the per-node
reasoning BUDGET (``roles.perception.thinking_variants``, receipt schema v5, unchanged). Every arm contacts Perception and the Solver; the arms differ ONLY in
the reasoning budget of their own two contacts (the completion cap stays 4,096 and ``drop-reasoning-v1`` stays). The arm set is DATA:
``nxt_r2_arms.json`` (default ``budget-1536`` and ``budget-2048``, both nodes; the delivering arm ``budget-3072`` = the 268-B lock form, LAST):

  ``budget-1536``   Perception and Solver at reasoning_budget_tokens 1,536 (answer reserve 2,560, cap 4,096)
  ``budget-2048``   Perception and Solver at reasoning_budget_tokens 2,048 (answer reserve 2,048, cap 4,096)
  ``budget-3072``   the delivering arm = the 268-B lock form (budget 3,072, reserve 1,024, cap 4,096): its requests are the lock's, byte for byte

NO TWIN (owner decision 313 A): the in-flight A/A offset on this core is measured twice (268-B SLU +1.15 / intent -0.09; P3.1 SLU -0.61 / intent +1.60), so
the column reads against the DECLARED offset |o| = 1.15 pp SLU and the paired floor 0.7 pp; at most two candidate arms per round.

GPU CEILING. Each arm's cost is its predicted seconds per row relative to the delivering arm, from ``nxt_r2_cost`` (a clipped-reasoning model fitted on the 40
per-contact records of the NX-T R1 smoke), registered ROUNDED UP to 0.01. The arm mix is their sum with the delivering arm's 1.0:
    expected GPU-h = rows x arm mix / 1.84 rows per minute / 60            (1.84 rows/min = measured full Thinking row throughput, np4 x 24,576)
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
import nxt_r2_cost as cost  # noqa: E402

REPO_ROOT = tf.REPO_ROOT

DATE = "2026-10-15"
SLUG = "nxt-r2-thinking-budget-fold-b"
SHORT = "nxt2"
PKG_NAME = "slurp-nxt-r2-thinking-budget-fold-b-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = "slurp-nxt-r2-thinking-budget-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-NXT-R2-THINKING-BUDGET-FOLD-B-READ-V1"
RECIPE_ID = "slurp-nxt-r2-thinking-budget-fold-b-read-v1"
READER = "scripts/analysis/slurp_nxt_thinking_budget_column_read.py"
ANALYSIS_ROOT = f"analysis/{READ_RUN_ID}"
LEDGER_MARK = "## Cell NXT-R2: the per-node reasoning-budget column on the Thinking core, TRAIN Fold B (one flight, two candidate budgets plus the delivering arm; smoke then 1,080 rows)"
OWNER_RULINGS = "owner rulings 304/307 (2026-10-13), 313 A and 318 A (2026-10-14), coordinator approval of the NX-T R2 design"

# ---- the system and the roster: exactly the 268-B lock, one flight --------------------------------------------------------------
ROWS, SMOKE_ROWS = tsf.ROWS, tsf.SMOKE_ROWS
LOCK, PROGRAM_BASE = tsf.LOCK, tsf.PROGRAM                 # v2.2; the plain lock program phase-native-module-v1-c2 (the base the column adds to)
SCORER = tsf.SCORER
DATASET, SPLIT_ID = tsf.DATASET, tsf.SPLIT_ID
TUNING_ROSTER, READ_ROSTER = "none", tsf.READ_ROSTER
ROSTER = dict(tsf.ROSTER)
PARENT = tsf.CELLS                                          # the 268-B cells the baselines/experiments are derived from (lock + smoke)
PARENT_SMOKE_KEY, PARENT_ARM_KEY = "smoke", "lock"

# ---- the arm table (DATA: nxt_r2_arms.json) -----------------------------------------------------------------------------------------
ARMS_PATH = HERE / "nxt_r2_arms.json"
ARM_TABLE_SCHEMA = "saea-nxt-r2-arm-table-v1"
NODES = ("perception", "solver")
OFF = "off"
MAX_CANDIDATE_ARMS = 2                                      # owner decision 313 A: at most two candidate arms per round
MIN_BUDGET_TOKENS = 128                                     # a budget below this measures a different thing (the forced close fires almost at once)
DELIVERING_BUDGET = tsf.THINK_BUDGET_TOKENS                 # 3,072: the lock form
COMPLETION_CAP = tsf.THINK_MAX_TOKENS                       # 4,096: never moves
DELIVERING = f"budget-{DELIVERING_BUDGET}"                  # the delivering arm's id (thinking_frame.delivering_arm_id)
TWIN = None                                                 # owner decision 313 A: no twin arm
_ARM_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ArmTableError(ValueError):
    """The arm table is malformed or breaks a registered rule (fail closed, by name)."""


def validate_arm_table(table: object) -> list[dict]:
    """Validate the arm-table document and return its candidate arms (declared order). Every refusal names the rule."""

    if not isinstance(table, dict) or set(table) != {"_note", "arms", "completion_cap", "delivering_budget_tokens", "schema"}:
        raise ArmTableError("the arm table must be exactly {_note, arms, completion_cap, delivering_budget_tokens, schema}")
    if table["schema"] != ARM_TABLE_SCHEMA:
        raise ArmTableError(f"schema must be {ARM_TABLE_SCHEMA!r}")
    if table["completion_cap"] != COMPLETION_CAP or table["delivering_budget_tokens"] != DELIVERING_BUDGET:
        raise ArmTableError(f"the decoding knobs of the delivering arm never move: budget {DELIVERING_BUDGET}, cap {COMPLETION_CAP}")
    arms = table["arms"]
    if not isinstance(arms, list) or not 1 <= len(arms) <= MAX_CANDIDATE_ARMS:
        raise ArmTableError(f"between 1 and {MAX_CANDIDATE_ARMS} candidate arms per round (owner decision 313 A; no twin)")
    seen_ids: set[str] = set()
    seen_policies: set[str] = set()
    out = []
    for position, arm in enumerate(arms):
        where = f"arms[{position}]"
        if not isinstance(arm, dict) or set(arm) != {"arm_id", *NODES}:
            raise ArmTableError(f"{where} must be exactly {{arm_id, perception, solver}}")
        arm_id = arm["arm_id"]
        if not isinstance(arm_id, str) or not _ARM_ID.match(arm_id) or arm_id == DELIVERING or arm_id in seen_ids:
            raise ArmTableError(f"{where}.arm_id {arm_id!r} must be a distinct lower-case id other than the delivering arm {DELIVERING!r}")
        seen_ids.add(arm_id)
        for node in NODES:
            value = arm[node]
            if value == OFF:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or not MIN_BUDGET_TOKENS <= value <= DELIVERING_BUDGET:
                raise ArmTableError(
                    f"{where}.{node} must be 'off' or an integer reasoning budget in [{MIN_BUDGET_TOKENS}, {DELIVERING_BUDGET}] (the cost model and the clip "
                    f"read are defined up to the R1 budget): got {value!r}")
        if all(arm[node] == DELIVERING_BUDGET for node in NODES):
            raise ArmTableError(f"{where} sets both nodes to the delivering budget: it would duplicate the delivering arm")
        key = json.dumps([arm["perception"], arm["solver"]])
        if key in seen_policies:
            raise ArmTableError(f"{where} repeats the setting of an earlier arm: two spellings of one configuration spend a contact per row and measure nothing")
        seen_policies.add(key)
        out.append({"arm_id": arm_id, "perception": arm["perception"], "solver": arm["solver"]})
    return out


def node_policy(setting: int | str) -> dict | None:
    """The per-node ``thinking_policy`` entry of one node setting (``None`` = the locked form, no override). A budget ``b`` keeps the 4,096 cap by stating the
    reserve ``cap - b``; OFF is NX-T R1's no-think form (the answer reserve defaults to the lock's 1,024)."""

    if setting == OFF:
        return {"enable_thinking": False}
    if setting == DELIVERING_BUDGET:
        return None
    return {"reasoning_budget_tokens": int(setting), "answer_reserve_tokens": COMPLETION_CAP - int(setting)}


def policy_of(arm: dict) -> dict:
    return {node: entry for node in NODES if (entry := node_policy(arm[node])) is not None}


def load_arm_table(path: Path = ARMS_PATH) -> list[dict]:
    return validate_arm_table(json.loads(Path(path).read_text(encoding="utf-8")))


ARM_SPECS = load_arm_table()
#: arm id -> its per-node override map (``core.reasoning_knobs.NODE_POLICY_KEYS`` per role kind); the delivering arm declares none.
POLICIES = {arm["arm_id"]: policy_of(arm) for arm in ARM_SPECS}
SETTINGS = {arm["arm_id"]: (arm["perception"], arm["solver"]) for arm in ARM_SPECS}
SETTINGS[DELIVERING] = (DELIVERING_BUDGET, DELIVERING_BUDGET)
CANDIDATE_ARMS = tuple(POLICIES)
ARM_ORDER = (*CANDIDATE_ARMS, DELIVERING)                   # declared order; the delivering arm LAST
K = len(ARM_ORDER)
CONTACTS_PER_ROW = 2 + 2 * (K - 1)                          # review-off base 2 + one Perception and one Solver contact per non-delivering arm (c6 for two candidates)
PROGRAM = f"phase-native-module-v1-c{CONTACTS_PER_ROW}"
#: Budgeted-thinking contacts per row (an answer-only fallback re-ask is possible only for a budgeted thinking request): the delivering arm's 2 plus every
#: candidate node that still thinks.
THINKING_CONTACTS_PER_ROW = 2 + sum(1 for arm in ARM_SPECS for node in NODES if arm[node] != OFF)
FALLBACK_CONTACTS_PER_ROW_CEILING = THINKING_CONTACTS_PER_ROW   # the runner requires >= 2 for the module family, a larger plan is legal

# ---- the Thinking serving geometry (owner decision 315 A, VOID on this 24 GB card: the control is the only geometry that fits) ------------------
#: Kept for parity with NX-T R1 (the derive and the writer still accept ``--geometry``); the table is NX-T R1's file, reused. ONLY the geometry leaves move;
#: the decoding knobs never move with geometry. The committed choice is ``<package>/geometry-selection-v1.json`` (absent = the control).
CONTROL_SESSION, CONTROL_MODEL, CONTROL_SWAP_TARGET = tsf.THINK_SESSION, tsf.THINK_MODEL, tsf.THINK_SWAP_TARGET
CONTROL_SLOTS, CONTROL_SLOT_TOKENS = tsf.THINK_SLOTS, tsf.SLOT_TOKENS
DEFAULT_GEOMETRY = CONTROL_SWAP_TARGET                      # think-budget-np4
GEOMETRY_TABLE_PATH = HERE / "nxt_r1_geometry_targets.json"
GEOMETRY_SELECTION = f"{PACKAGE}/geometry-selection-v1.json"
SERVING_LIB = "scripts/flights/batch/serving_lib.sh"
GEOMETRY_LEAVES = ("server_args", "geometry_basis", "profile_slot_count")
GEOMETRY_EXPERIMENT_KEYS = ("service_session", "cells.0.model_fragment")


def _serving_lib_row(target: str, root: Path) -> dict | None:
    path = Path(root) / SERVING_LIB
    if not path.is_file():
        return None
    match = re.search(rf"^\s*{re.escape(target)}\)\s*\n(.*?);;", path.read_text(encoding="utf-8"), re.M | re.S)
    if not match:
        return None
    sid, fragment = re.search(r"G_SID=(\S+)", match.group(1)), re.search(r"G_FRAGMENT=(\S+)", match.group(1))
    return {"session": sid.group(1), "model_fragment": fragment.group(1)} if sid and fragment else None


def resolve_geometry(target: str, root: Path | str | None = None) -> dict:
    """Resolve a serving target to its session, model fragment and slot geometry. Raises ``ValueError`` for an unknown target."""

    root = Path(root) if root else REPO_ROOT
    table = json.loads(GEOMETRY_TABLE_PATH.read_text(encoding="utf-8"))["targets"]
    row, hint = _serving_lib_row(target, root), table.get(target)
    if row is None and hint is None:
        raise ValueError(f"unknown serving geometry target {target!r}: no row in {SERVING_LIB} and none in {GEOMETRY_TABLE_PATH.name}")
    chosen = row or hint
    source = f"{SERVING_LIB} geometry row" if row else f"{GEOMETRY_TABLE_PATH.name} (provisional: {SERVING_LIB} has no row for it yet)"
    fragment_path = root / "configs" / "model" / f"{chosen['model_fragment']}.json"
    present = fragment_path.is_file()
    slots, slot_tokens = (hint or {}).get("slots"), (hint or {}).get("slot_tokens")
    if present:
        args = json.loads(fragment_path.read_text(encoding="utf-8"))["server_args"]
        total, slots = int(args[args.index("-c") + 1]), int(args[args.index("-np") + 1])
        slot_tokens = total // slots
    if not slots or not slot_tokens:
        raise ValueError(f"geometry {target!r}: no slot geometry (fragment absent and no table hint)")
    return {"target": target, "session": chosen["session"], "model_fragment": chosen["model_fragment"], "source": source, "fragment_present": present,
            "fragment_path": f"configs/model/{chosen['model_fragment']}.json", "slots": int(slots), "slot_tokens": int(slot_tokens),
            "provisional": row is None and bool((hint or {}).get("provisional"))}


def _read_selection(root: Path) -> str:
    path = Path(root) / GEOMETRY_SELECTION
    return json.loads(path.read_text(encoding="utf-8"))["target"] if path.is_file() else DEFAULT_GEOMETRY


ACTIVE_GEOMETRY = resolve_geometry(_read_selection(REPO_ROOT))
THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET = ACTIVE_GEOMETRY["session"], ACTIVE_GEOMETRY["model_fragment"], ACTIVE_GEOMETRY["target"]


def geometry_of(key: str) -> dict:
    """The serving geometry a cell runs on: the smoke always uses the control; the arm follows the selection."""

    return resolve_geometry(CONTROL_SWAP_TARGET) if key == "smoke" else ACTIVE_GEOMETRY


def select_geometry(target: str, root: Path | str | None = None, *, write: bool = True) -> dict:
    """Select the arm's serving geometry: refuses a non-control target whose model fragment is not on disk, writes (or, for the control, removes) the
    committed selection file, and updates this module's identities in place."""

    global ACTIVE_GEOMETRY, THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET, THINK_SLOTS
    root = Path(root) if root else REPO_ROOT
    geometry = resolve_geometry(target, root)
    if target != DEFAULT_GEOMETRY and not geometry["fragment_present"]:
        raise ValueError(f"geometry {target!r}: model fragment {geometry['fragment_path']} is not present in this tree; the np6/np8 path waits for its fragment")
    path = root / GEOMETRY_SELECTION
    if write:
        if target == DEFAULT_GEOMETRY:
            if path.is_file():
                path.unlink()
        else:
            path.write_bytes((json.dumps({"schema": "saea-nxt-r2-geometry-selection-v1", "target": target, "decision": "coordinator selection",
                                          "session": geometry["session"], "model_fragment": geometry["model_fragment"]}, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    ACTIVE_GEOMETRY = geometry
    THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET, THINK_SLOTS = geometry["session"], geometry["model_fragment"], geometry["target"], geometry["slots"]
    if "CELLS" in globals():
        CELLS["arm"]["model"], CELLS["arm"]["session"] = THINK_MODEL, THINK_SESSION
    return geometry


def think_model_text(key: str) -> str:
    """The ledger model/tool text of a cell, geometry-aware (the control reads ``c98304 np4 x 24,576``)."""

    g = geometry_of(key)
    return ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, "
            f"c{g['slots'] * g['slot_tokens']} np{g['slots']} x {g['slot_tokens']:,} max{tsf.THINK_MAX_TOKENS} (reasoning budget {tsf.THINK_BUDGET_TOKENS}), q8_0 KV, "
            f"--reasoning-format deepseek (model fragment {g['model_fragment']}); its own promoted speech packets; module program {PROGRAM}; "
            "per-arm reasoning budget at the named nodes; no tool authority")


THINK_PACKET_ROOT, THINK_PROMOTION_RECEIPT = tsf.THINK_PACKET_ROOT, tsf.THINK_PROMOTION_RECEIPT
THINKING_KNOBS = json.loads(json.dumps(tsf.THINKING_KNOBS))
#: The no-think form of a node an arm table turns OFF (NX-T R1's, unchanged): the answer reserve is the lock's 1,024.
NO_THINK_KNOBS = {"enable_thinking": False, "answer_reserve_tokens": tsf.THINK_ANSWER_RESERVE_TOKENS, "max_tokens": tsf.THINK_ANSWER_RESERVE_TOKENS,
                  "budget_field": "absent (no thinking_budget_tokens)", "chat_template_kwargs": {"enable_thinking": False}}
#: A budget node's wire form: ``thinking_budget_tokens`` b, ``max_tokens`` the unchanged cap, so the answer reserve is cap - b.
BUDGET_NODE_KNOBS = {"thinking_budget_tokens": "b (the arm's setting)", "answer_reserve_tokens": "cap - b", "max_tokens": COMPLETION_CAP if "COMPLETION_CAP" in globals() else tsf.THINK_MAX_TOKENS,
                     "chat_template_kwargs": {"enable_thinking": True}}

# ---- external references (the 268-B and P3.1 reads; development numbers) ---------------------------------------------------------
THINKING_SYSTEM_SLU, THINKING_SYSTEM_INTENT = 71.61, 85.00                  # 268-B lock arm
TWIN_OFFSET_268B_SLU_PP, TWIN_OFFSET_268B_INTENT_PP = 1.15, -0.09            # 268-B cross-flight twin offset
TWIN_OFFSET_P31_SLU_PP, TWIN_OFFSET_P31_INTENT_PP = -0.61, 1.60              # P3.1 (DEV-2000-ADDED) cross-flight twin offset
DECLARED_OFFSET_SLU_PP = 1.15                                               # |o|: the larger of the two measured same-core A/A offsets, declared (decision 313 A)
PAIRED_FLOOR_PP = 0.7                                                       # the same-flight paired half-width (decisions 172/231/313)
FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65                                  # decision 190 node-column floors at n = 1,080 (the no-resolved-loss margins)
EXPECTED_EFFECT_PP = 0.0                                                    # a budget cut is expected to cost nothing resolvable (the question is the saving)

# ---- budget arithmetic (one place) ---------------------------------------------------------------------------------------------------
COST_MODEL = cost.fit(cost.load_inputs())
#: arm id -> registered cost in full delivering rows per row (the model's predicted seconds per row relative to the delivering arm, rounded UP to 0.01).
ROW_COST = {arm: cost.ceil_hundredth(cost.relative_cost(COST_MODEL, *SETTINGS[arm], delivering=DELIVERING_BUDGET)) for arm in CANDIDATE_ARMS}
ROW_COST[DELIVERING] = 1.0
LINEAR_REFERENCE = {arm: round(cost.linear_reference(COST_MODEL, *SETTINGS[arm], delivering=DELIVERING_BUDGET), 4) for arm in CANDIDATE_ARMS}
ARM_MIX_ROWS = round(sum(ROW_COST.values()), 2)
ROWS_PER_MINUTE_FULL = 1.84                                                 # measured, np4 x 24,576 (P3 programme)
GPU_MARGIN, GPU_ROUND_H = tf.GPU_PLAN_MARGIN, tf.GPU_PLAN_ROUND_H
SMOKE_GPU_HOURS = tsf.SMOKE_GPU_HOURS
THINK_SLOTS = ACTIVE_GEOMETRY["slots"]


def expected_gpu_hours(rows: int) -> float:
    """rows x arm mix / 1.84 rows per minute / 60 (unrounded)."""

    return rows * ARM_MIX_ROWS / ROWS_PER_MINUTE_FULL / 60.0


def planned_gpu_hours(rows: int) -> float:
    """The registered ceiling: ``ceil_0.1( expected x 1.3 )``."""

    hours = expected_gpu_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def arm_row_equivalent_rows_per_minute(arm: str) -> float:
    """The rows per minute an arm alone would run at, from its cost in full rows: ``1.84 / cost``."""

    return ROWS_PER_MINUTE_FULL / ROW_COST[arm]


def lock_flight_gpu_hours(arm: str, rows: int = ROWS) -> float:
    """The projected GPU-h of a ``rows``-row LOCK flight that runs only this arm's setting on both nodes, at the registered 1.84 rows/min reference."""

    return rows / arm_row_equivalent_rows_per_minute(arm) / 60.0


# ---- the recoveries of a cell ----------------------------------------------------------------------------------------------------------
#: A (run_id, attempt_id) pair is a one-time key, so a cell whose attempt stopped is re-registered under the ``-recN`` attempt ids (generation AND the live
#: phase fit) with a plan that carries the original plan plus every earlier attempt's realised spend (run-cumulative). Generic mechanism:
#: ``scripts/flights/lib/recovery.py``. ``RECOVERIES`` is EMPTY on the first registration; every recovery is data-driven: the coordinator commits a predecessor
#: snapshot (``recovery.py snapshot``) and a diagnosis input per recovery and the family builds ``RECOVERY_HISTORY["arm"]`` from them. A predecessor's spend is the
#: snapshot's, never typed here.
#:
#: * ``rec1`` (coordinator decision under owner rulings 318 A / 327 A, 2026-10-17): the column flight re-flown WHOLE after a host reboot killed the first attempt.
#:   Files: ``predecessor-snapshot-arm-rec1-v1.json`` (the FIRST attempt) and ``recovery-input-arm-v1.json``.
#: * ``rec2`` (owner ruling 328, 2026-10-17): the rec1 attempt was ABORTED by a serving-task incident; rec2 is a RESUME of it (the default recovery form: a stopped
#:   attempt is resumed, never re-flown whole, whenever a checkpoint or trace exists), under an explicit owner exception to the one-recovery rule. Files:
#:   ``predecessor-snapshot-arm-rec2-v1.json`` (the rec1 attempt, with its trace and checkpoint pins and both replay classifications; written by
#:   ``nxt_r2_rec2_snapshot.py``) and ``recovery-input-arm-rec2-v1.json`` (the diagnosis plus ``owner_exception`` and the COMPUTED ``resume_mode``;
#:   ``nxt_r2_rec2_mode.py``).
#:
#: ``RECOVERY_HISTORY[key]`` lists the records in order; ``RECOVERIES[key]`` is the LATEST one, the state the ids, plans and caps follow.
REC = rcv.REC
PREDECESSOR_SNAPSHOT = {"arm": f"{PACKAGE}/predecessor-snapshot-arm-rec1-v1.json"}      # the rec1 record's snapshot (the first attempt)
RECOVERY_INPUT = {"arm": f"{PACKAGE}/recovery-input-arm-v1.json"}                       # the rec1 record's diagnosis
PREDECESSOR_SNAPSHOTS = {"arm": [PREDECESSOR_SNAPSHOT["arm"], f"{PACKAGE}/predecessor-snapshot-arm-rec2-v1.json"]}
RECOVERY_INPUTS = {"arm": [RECOVERY_INPUT["arm"], f"{PACKAGE}/recovery-input-arm-rec2-v1.json"]}
RECOVERY_INPUT_KEYS = ("recovered_at", "ledger_title", "agent", "reason", "root_cause", "fix", "decision")
RECOVERY_INPUT_KEYS_REC2 = RECOVERY_INPUT_KEYS + ("owner_exception", "resume_mode", "resume_mode_basis")
RESUME_MODES = {"checkpoint": "B", "trace": "A"}                                        # resume mode -> the owner-decision-309 letter


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


def resume_declaration(mode: str, stopped: dict) -> dict:
    """The ``resume_from`` object of the stopped attempt in ``mode`` (``checkpoint``: mode B, ``trace``: mode A); the pins come from the snapshot's data-root reads."""

    pins = stopped["trace"]
    if mode == "checkpoint":
        return {"attempt_id": stopped["attempt_id"], "checkpoint_sha256": pins["checkpoint_sha256"]}
    if mode == "trace":
        return {"attempt_id": stopped["attempt_id"], "trace_sha256": pins["trace_sha256"]}
    raise ValueError(f"resume_mode must be 'checkpoint' or 'trace', got {mode!r}")


def build_arm_rec2(inputs: dict, first: dict, stopped: dict) -> dict:
    """The arm cell's rec2 recovery record (owner ruling 328): a RESUME of the stopped rec1 attempt. ``first`` = the first attempt's snapshot, ``stopped`` = the rec1
    attempt's snapshot (trace and checkpoint pins, both replay classifications, the code-identity comparison); ``inputs`` = the committed diagnosis and the
    computed ``resume_mode``."""

    missing = [k for k in RECOVERY_INPUT_KEYS_REC2 if not inputs.get(k)]
    if missing:
        raise ValueError(f"the rec2 recovery input misses {missing}")
    mode = inputs["resume_mode"]
    letter = RESUME_MODES.get(mode)
    if letter is None:
        raise ValueError(f"resume_mode must be one of {sorted(RESUME_MODES)}, got {mode!r}")
    if mode == "checkpoint" and (stopped.get("mode_inputs") or {}).get("implementation_differing_modules") != []:
        raise ValueError("mode B (checkpoint) is refused: the snapshot does not show a byte-identical runtime / runner / row_checkpoint")
    resume = stopped["resume"][mode]
    counts = dict(resume["counts"])
    kept, flown = counts["kept"], counts["flown"]
    if kept + flown != counts["roster"]:
        raise ValueError(f"the rec2 resume counts do not add up: {counts}")
    if stopped["resume"]["trace"]["kept_sample_ids_sha256"] != stopped["resume"]["checkpoint"]["kept_sample_ids_sha256"] and mode == "checkpoint":
        raise ValueError("the trace and the checkpoint disagree on the kept rows; the mode choice must be re-examined")
    fit, trace = stopped.get("fit") or {}, stopped["trace"]
    predecessors = [rcv.predecessor_from_snapshot(first), rcv.predecessor_from_snapshot(stopped)]
    calls, audio = sum(p["contacts_spent"] for p in predecessors), sum(p["speech_seconds_spent"] for p in predecessors)
    contacts = flown * CONTACTS_PER_ROW
    gpu = expected_gpu_hours(flown)
    exception = inputs["owner_exception"]
    exception_cap = exception[:1].upper() + exception[1:]
    snaps = " and ".join(PREDECESSOR_SNAPSHOTS["arm"])
    pin_name, pin_sha = ("checkpoint", trace["checkpoint_sha256"]) if mode == "checkpoint" else ("trace", trace["trace_sha256"])
    pin_bytes = trace["checkpoint_bytes"] if mode == "checkpoint" else trace["trace_bytes"]
    if mode == "checkpoint":
        why_mode = (f"MODE {letter} (row checkpoint): {inputs['resume_mode_basis']} `resume_from` names the rec1 attempt and the sha256 of its row checkpoint, "
                    f"{pin_sha} ({pin_bytes:,} bytes), read from the data root into {PREDECESSOR_SNAPSHOTS['arm'][1]}.")
        phrase = f"resumed in mode B (row checkpoint) from `{stopped['attempt_id']}`: the {kept:,} complete rows are kept and the {flown:,} remaining rows are flown"
    else:
        why_mode = (f"MODE {letter} (trace replay), not mode B: {inputs['resume_mode_basis']} `resume_from` names the rec1 attempt and the sha256 of its trace, "
                    f"{pin_sha} ({pin_bytes:,} bytes), read from the data root into {PREDECESSOR_SNAPSHOTS['arm'][1]}.")
        phrase = f"resumed in mode A (trace replay) from `{stopped['attempt_id']}`: the {kept:,} complete rows are kept and the {flown:,} remaining rows are flown"
    return {
        "recovery_index": 2,
        "recovered_at": inputs["recovered_at"],
        "ledger_title": inputs["ledger_title"],
        "agent": inputs["agent"],
        "registered_at_utc": None,
        "base_commit": None,
        "worktree": None,
        "branch": None,
        "owner_exception": exception,
        "predecessor_attempt_id": stopped["attempt_id"],
        "predecessor_fit_run_id": fit["run_id"],
        "predecessor_fit_attempt_id": fit["attempt_id"],
        "fit_predecessor_phrase": (f"{'its attempt record is present, ' if fit.get('attempt_record_present') else 'no attempt record was opened for it, '}its prepared "
                                   f"directory holds {fit.get('prepared_request_fit_envelopes', 0):,} request-fit envelopes preserved unread on the data root"),
        "predecessor_state": (f"{stopped['state']} (its attempt record); {stopped['actual_calls']:,} calls / {stopped['actual_audio_seconds']:.2f} "
                              f"speech-seconds realised per its attempt record (reserved {stopped['reserved_calls']:,} / {stopped['reserved_audio_seconds']:,.0f}); "
                              f"{kept:,} complete rows in its row checkpoint (sha256 {trace['checkpoint_sha256'][:8]}...) and its trace (sha256 "
                              f"{trace['trace_sha256'][:8]}...); {counts['partial']} partial row(s) in the trace were never completed; preserved unread."),
        "predecessors": predecessors,
        "reason": (f"{inputs['reason']} {exception_cap} grants an EXPLICIT exception to the package rule of one recovery re-registration per run id and rules that "
                   f"a stopped attempt is RESUMED, never re-flown whole, whenever a checkpoint or trace exists: this rec2 keeps the {kept:,} complete rows of the stopped "
                   f"rec1 attempt by a mode-{letter} resume and flies the {flown:,} remaining rows."),
        "root_cause": inputs["root_cause"],
        "amendment": (
            f"RECOVERY {inputs['recovered_at']} (rec2; {exception}, {inputs['decision']}). {why_mode} The attempt keeps the {kept:,} complete rows (each is proven by "
            f"the offline replay recorded as a block of the generation plan) and flies the {flown:,} remaining rows: {flown:,} x {CONTACTS_PER_ROW} = {contacts:,} "
            f"program contacts and nothing else. The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py): the registered "
            f"plan plus both earlier attempts' recorded spend ({calls:,} calls, {audio:g} speech-seconds, read from the attempt records into {snaps}). The FIT cap is "
            "structural and unchanged. The FIT run id and the FIT attempt id take the rec2 marker because a (run_id, attempt_id) pair is a one-time key; the "
            f"generation run id is unchanged. The registered GPU-hour ceiling ({planned_gpu_hours(ROWS)} GPU-h) stands; the resume is expected to spend about "
            f"{gpu:.1f} GPU-h ({flown:,} rows x {ARM_MIX_ROWS} full-row equivalents / {ROWS_PER_MINUTE_FULL} rows per minute). `--allow-output-change` is never "
            f"passed: the rebuilt supply, the roster ({ROWS:,} rows) and the read (n = {ROWS:,}) are the registered ones."),
        "fix": inputs["fix"],
        "unchanged": (f"Unchanged: the smoke cell `slurp-native-stage3-{SLUG}-smoke-4-v1` (sealed, not re-flown) and every registered knob, arm, policy, roster ({ROWS:,} rows), "
                      f"prompt, geometry, cap, the program {PROGRAM} and the {planned_gpu_hours(ROWS)} GPU-hour ceiling of the arm cell."),
        "extra_note": (f"Resume accounting: kept {kept:,} rows (from `{stopped['attempt_id']}`, kept-row id hash {resume['kept_sample_ids_sha256']}); flown {flown:,} rows "
                       f"({counts['partial']} partial, {counts['unstarted']:,} never started), {contacts:,} program contacts. The read reports kept / flown counts "
                       f"beside the arm columns. {exception_cap} covers this one re-registration only."),
        "rule": "A third recovery is not covered by the owner exception; a second failure of rec2 closes the cell, and the fix is proven on a four-row dry run.",
        "fit_cap_rule": "The FIT cap is structural: rows x program contacts x endpoints per contact.",
        "resume_mode": f"resume-mode-{letter}-keep-{kept}-fly-{flown}",
        "resume_from": resume_declaration(mode, stopped),
        "resume_counts": counts,
        "flown_phrase": phrase,
    }


def _load_history(root: Path = REPO_ROOT) -> dict[str, list[dict]]:
    """Each recovered cell's records in order: rec1 from its two files, rec2 from its two files once they are committed."""

    out: dict[str, list[dict]] = {}
    for key, inputs in RECOVERY_INPUTS.items():
        path = Path(root) / inputs[0]
        if not path.is_file():
            continue
        snaps = [Path(root) / rel for rel in PREDECESSOR_SNAPSHOTS[key]]
        first = rcv.load_snapshot(snaps[0])
        history = [build_arm_recovery(json.loads(path.read_text(encoding="utf-8")), first)]
        second = Path(root) / inputs[1]
        if second.is_file() and snaps[1].is_file():
            history.append(build_arm_rec2(json.loads(second.read_text(encoding="utf-8")), first, rcv.load_snapshot(snaps[1])))
        out[key] = history
    return out


def _load_recoveries(root: Path = REPO_ROOT) -> dict[str, dict]:
    """The LATEST record of each recovered cell (the state the ids, plans and caps follow)."""

    return {key: records[-1] for key, records in _load_history(root).items()}


RECOVERY_HISTORY: dict[str, list[dict]] = _load_history()
RECOVERIES: dict[str, dict] = {key: records[-1] for key, records in RECOVERY_HISTORY.items()}
for _records in RECOVERY_HISTORY.values():
    for _position, _rec in enumerate(_records, 1):
        rcv.validate_recovery(_rec)
        if _rec["recovery_index"] != _position:
            raise ValueError("the recovery history is out of order")


def recovery_index(key: str) -> int:
    """0 for a cell on its first attempt, else the index of its latest recovery."""

    rec = RECOVERIES.get(key)
    return int(rec["recovery_index"]) if rec else 0


def history_caps(key: str, index: int, caps: dict) -> dict:
    """The run-cumulative caps AS OF recovery ``index`` (the original plan plus the spend of the attempts that recovery names); used to print an earlier
    recovery section of the README with its own cumulative numbers."""

    calls, audio = rcv.cumulative_budget({key: RECOVERY_HISTORY[key][index - 1]}, key, original_generation_calls(key), audio_cap(CELLS[key]["roster"]))
    return {**caps, "generation_calls_cap": calls, "repeated_speech_audio_seconds_cap": audio}


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
        "model": CONTROL_MODEL if key == "smoke" else THINK_MODEL, "session": CONTROL_SESSION if key == "smoke" else THINK_SESSION,
        "prefix": "smoke-" if key == "smoke" else "",
        "campaign": f"configs/campaign/slurp-native-stage3-{ids_stem}-v1.json",
    }


CELLS = {
    "smoke": _spec("smoke", "four-row form smoke of the reasoning-budget column", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   ids_stem=f"{SLUG}-smoke-4", parent_key="smoke"),
    "arm": _spec("arm", f"reasoning-budget column flight ({K} arms in one flight)", ROWS, "arm", 1, planned_gpu_hours(ROWS),
                 ids_stem=SLUG, parent_key="lock"),
}
ARM_KEYS = ("arm",)
ALL_KEYS = ("smoke", "arm")


def eligible_run_ids() -> list[str]:
    """The decision receipt's eligible run ids: each cell's generation run id then its first-registration FIT run id, in chain order, then the FIT run id of every
    recovery, oldest first (each receipt's list is a strict prefix of the next: the first registration lists exactly the first four, rec1 appends its FIT run id, rec2
    appends its own)."""

    out: list[str] = []
    for key in ALL_KEYS:
        history = RECOVERY_HISTORY.get(key, [])
        out += [CELLS[key]["run"], history[0]["predecessor_fit_run_id"] if history else CELLS[key]["fit_run"]]
    for key in ALL_KEYS:
        history = RECOVERY_HISTORY.get(key, [])
        out += [rec["predecessor_fit_run_id"] for rec in history[1:]] + ([CELLS[key]["fit_run"]] if history else [])
    return out


def eligible_attempt_ids() -> list[str]:
    """Each cell's attempt ids, in chain order; a recovered cell lists the ids of every earlier attempt (superseded, spent) then its latest ids."""

    out: list[str] = []
    for key in ALL_KEYS:
        for rec in RECOVERY_HISTORY.get(key, []):
            out += [rec["predecessor_attempt_id"], rec["predecessor_fit_attempt_id"]]
        out += [CELLS[key]["attempt"], CELLS[key]["fit_attempt"]]
    return out


def fit_contact_cap(rows: int) -> int:
    """rows x program contacts x endpoints per contact (never run-cumulative)."""

    return tf.fit_contact_cap(rows, CONTACTS_PER_ROW)


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def plan_file_name(key: str, plan_kind: str) -> str:
    """Package file name of a cell's registered plan; a recovered cell's plans carry its latest ``-recN`` marker."""

    return rcv.plan_file_name(CELLS[key]["prefix"], plan_kind, recovery_index(key))


def superseded_plan_file_names(key: str) -> list[str]:
    """First-attempt plan names a recovery supersedes (removed from the package; the failed attempt stays on the data root)."""

    return rcv.superseded_plan_file_names(CELLS[key]["prefix"], recovery_index(key))


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


#: Context fit at the 4,096-token cap is the 268-B lock's (every arm's request is at most that long): live prompt limit 17,406 against the measured Solver prompt
#: maximum 14,641. The per-contact exact gate runs on every arm's REAL request. A lower budget never lengthens a prompt, but an arm's Solver prompt carries THAT
#: arm's own Perception note.
PROMPT_LIMIT_THINKING, SOLVER_PROMPT_TOKENS_MAX = tsf.PROMPT_LIMIT_THINKING, tsf.SOLVER_PROMPT_TOKENS_MAX
FIT_ESTIMATE = {"base_prompt_tokens": 2000, "completion_ceiling": tsf.THINK_MAX_TOKENS, "slot_tokens": 24576, "tokens_per_supplied_item": 235}
MAX_SUPPLIED_ITEMS = tf.DELIVERING_MAX_SUPPLIED_ITEMS      # 55: the lock's own supply bound; every arm renders the delivering arm's evidence


__all__ = [name for name in globals() if not name.startswith("_")]
