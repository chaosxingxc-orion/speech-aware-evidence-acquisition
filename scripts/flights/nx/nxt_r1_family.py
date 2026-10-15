"""Shared identities of NX-T R1: the per-node THINKING-POLICY column on the Thinking core, TRAIN Fold B.

One module, imported by the derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It reuses the 268-B
family it extends instead of restating it: ``thinking_system_family`` (the Thinking model fragment, session, packet root and its pinned
promotion receipt, the lock v2.2 + v4g plain-lock program, the Fold B roster) and ``tfrl_family`` (the FIT arithmetic and the derive helpers).

WHAT THE CELL IS. Owner rulings 304 and 306/307 (2026-10-13): "are there nodes that do not need thinking?" becomes the FIRST node-level round on
the Thinking base. ONE flight of the locked system (the 268-B lock) on TRAIN Fold B (1,080 rows) with a same-flight COLUMN over the per-node
thinking policy (``roles.perception.thinking_variants``, receipt schema v5; harness commit on this branch). Every arm contacts Perception and the
Solver; the arms differ ONLY in the thinking decoding of their own two contacts. Five arms, the delivering arm LAST:

  ``perception-off``  Perception enable_thinking false (max_tokens = the 1,024 reserve), Solver thinking at budget 3,072 / cap 4,096
  ``solver-off``      Perception thinking (the locked form), Solver enable_thinking false
  ``both-off``        no thinking anywhere: the no-think core on the same weights
  ``both-on-twin``    request-identical copy of the delivering arm: the column's own in-flight A/A null
  ``both-on``         the delivering arm = the 268-B lock form (budget 3,072, cap 4,096, ``drop-reasoning-v1``); its requests are the lock's, byte for byte

Ruling 2 of the coordinator: no note sharing. ``solver-off`` and the two Perception-off arms re-contact as INDEPENDENT chains, so the Solver prompt
of a non-delivering arm differs by the arm's OWN Perception note; the evidence, the template and the QueryState are identical in every arm.

GPU CEILING (coordinator ruling 4). Arm mix, in full 268-B rows per row (one 268-B row = one Thinking Perception contact + one Thinking Solver
contact; measured 50.32 s + 35.31 s at np4, so the Perception contact is 0.588 of a row and the Solver contact 0.412): both-on 1.0 + both-on-twin 1.0 +
perception-off 0.6 + solver-off 0.6 + both-off 0.05 = 3.25. The single-node-off arms are costed at 0.6 (the larger of 0.588 and 0.412, rounded up: a
no-think contact costs a few hundred tokens, not zero); both-off at 0.05.
    expected GPU-h = rows x 3.25 / 1.84 rows per minute / 60            (1.84 rows/min = measured full Thinking row throughput, np4 x 24,576)
    ceiling        = ceil_0.1( expected x 1.3 )
For 1,080 rows: expected 31.79 GPU-h, ceiling 41.4. The four-row smoke keeps the 0.5 GPU-h form allowance. Ceilings are bounds, never targets.
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

DATE = "2026-10-13"
SLUG = "nxt-r1-thinking-policy-fold-b"
SHORT = "nxt1"
PKG_NAME = "slurp-nxt-r1-thinking-policy-fold-b-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = "slurp-nxt-r1-thinking-policy-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1"
RECIPE_ID = "slurp-nxt-r1-thinking-policy-fold-b-read-v1"
READER = "scripts/analysis/slurp_nxt_thinking_policy_column_read.py"
ANALYSIS_ROOT = f"analysis/{READ_RUN_ID}"
COLUMN_DIR = "thinking-policy-columns"          # under the arm cell's run directory: the official per-arm column scores
LEDGER_MARK = "## Cell NXT-R1: the per-node thinking-policy column on the Thinking core, TRAIN Fold B (one flight, five arms; smoke then 1,080 rows)"
OWNER_RULINGS = "owner rulings 301-307 (2026-10-13), coordinator approval of the NX-T R1 design (rulings 1-5)"

# ---- the system and the roster: exactly the 268-B lock, one flight --------------------------------------------------------------
ROWS, SMOKE_ROWS = tsf.ROWS, tsf.SMOKE_ROWS
LOCK, PROGRAM_BASE = tsf.LOCK, tsf.PROGRAM                 # v2.2; the plain lock program phase-native-module-v1-c2 (the base the column adds to)
SCORER = tsf.SCORER
DATASET, SPLIT_ID = tsf.DATASET, tsf.SPLIT_ID
TUNING_ROSTER, READ_ROSTER = "none", tsf.READ_ROSTER
ROSTER = dict(tsf.ROSTER)
PARENT = tsf.CELLS                                          # the 268-B cells the baselines/experiments are derived from (lock + smoke)
PARENT_SMOKE_KEY, PARENT_ARM_KEY = "smoke", "lock"

# ---- the arms ----------------------------------------------------------------------------------------------------------------------
OFF = {"enable_thinking": False}
#: arm id -> its per-node override map (``core.reasoning_knobs.NODE_POLICY_KEYS`` per role kind); the delivering arm and the twin declare none.
POLICIES = {
    "perception-off": {"perception": dict(OFF)},
    "solver-off": {"solver": dict(OFF)},
    "both-off": {"perception": dict(OFF), "solver": dict(OFF)},
}
CANDIDATE_ARMS = tuple(POLICIES)
TWIN, DELIVERING = "both-on-twin", "both-on"
ARM_ORDER = (*CANDIDATE_ARMS, TWIN, DELIVERING)             # declared order; the delivering arm LAST
K = len(ARM_ORDER)                                          # 5
CONTACTS_PER_ROW = 2 + 2 * (K - 1)                          # review-off base 2 + one Perception and one Solver contact per non-delivering arm = 10
PROGRAM = f"phase-native-module-v1-c{CONTACTS_PER_ROW}"     # phase-native-module-v1-c10
#: Thinking contacts per row (an answer-only fallback re-ask is possible only for a budgeted thinking request): both-on 2 + twin 2 + perception-off
#: 1 (its Solver) + solver-off 1 (its Perception) + both-off 0.
THINKING_CONTACTS_PER_ROW = 2 + 2 + 1 + 1
FALLBACK_CONTACTS_PER_ROW_CEILING = THINKING_CONTACTS_PER_ROW   # 6; the runner requires >= 2 for the module family, a larger plan is legal
# ---- the Thinking serving geometry (owner decision 315 A, 2026-10-14) ----------------------------------------------------------------
#: The column flight (the ``arm`` cell) runs on whichever Thinking serving geometry a throughput receipt picks: the np4 x 24k control (default), np6 x 20k
#: or np8 x 16k. ONLY the geometry leaves move (the serving session, the model-fragment reference and, inside that fragment, ``server_args`` /
#: ``profile_slot_count`` / ``geometry_basis``); the decoding knobs (budget 3,072 / cap 4,096 / drop-reasoning-v1) never move with geometry. The smoke is sealed
#: on the control and always stays on it. The choice is committed state: ``<package>/geometry-selection-v1.json`` (absent = the control, byte-identical to the
#: first registration); ``--geometry`` on the derive / writer writes it through :func:`select_geometry`.
#: Resolution is data-driven: the geometry row of ``scripts/flights/batch/serving_lib.sh`` (``G_SID`` / ``G_FRAGMENT``) when it has one, else the provisional
#: table ``nxt_r1_geometry_targets.json``. The np6 / np8 path is UNTESTED until their fragments and serving rows land.
CONTROL_SESSION, CONTROL_MODEL, CONTROL_SWAP_TARGET = tsf.THINK_SESSION, tsf.THINK_MODEL, tsf.THINK_SWAP_TARGET
CONTROL_SLOTS, CONTROL_SLOT_TOKENS = tsf.THINK_SLOTS, tsf.SLOT_TOKENS
DEFAULT_GEOMETRY = CONTROL_SWAP_TARGET                      # think-budget-np4
GEOMETRY_TABLE_PATH = HERE / "nxt_r1_geometry_targets.json"
GEOMETRY_SELECTION = f"{PACKAGE}/geometry-selection-v1.json"
SERVING_LIB = "scripts/flights/batch/serving_lib.sh"
#: Composed-config leaves a geometry change may move (``compose`` values of the arm cell); the experiment's ``service_session`` and the cell's
#: ``model_fragment`` reference move with them. Anything else that moves refuses the derive.
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
    """The serving geometry a cell runs on: the smoke is sealed on the control; the arm follows the selection."""

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
            path.write_bytes((json.dumps({"schema": "saea-nxt-r1-geometry-selection-v1", "target": target, "decision": "owner decision 315 A (2026-10-14)",
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
            "per-arm enable_thinking false at the named node; no tool authority")


THINK_PACKET_ROOT, THINK_PROMOTION_RECEIPT = tsf.THINK_PACKET_ROOT, tsf.THINK_PROMOTION_RECEIPT
THINKING_KNOBS = json.loads(json.dumps(tsf.THINKING_KNOBS))
NO_THINK_KNOBS = {"enable_thinking": False, "answer_reserve_tokens": tsf.THINK_ANSWER_RESERVE_TOKENS, "max_tokens": tsf.THINK_ANSWER_RESERVE_TOKENS,
                  "budget_field": "absent (no thinking_budget_tokens)", "chat_template_kwargs": {"enable_thinking": False}}

# ---- external references (the 268-B read; development numbers) ------------------------------------------------------------------
THINKING_SYSTEM_SLU, THINKING_SYSTEM_INTENT = 71.61, 85.00                  # 268-B lock arm
INSTRUCT_SYSTEM_SLU, INSTRUCT_SYSTEM_INTENT = 64.45, 82.69                  # the Instruct lock column of loop iteration 3
TWIN_OFFSET_268B_SLU_PP, TWIN_OFFSET_268B_INTENT_PP = 1.15, -0.09            # 268-B cross-flight twin offset (external reference for the A/A)
SYSTEM_DELTA_SLU_PP = 7.15                                                  # d_system of 268-B: the largest contrast the column can show (both-off ~ Instruct)
FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65                                  # decision 190 node-column floors at n = 1,080

# ---- budget arithmetic (one place) ---------------------------------------------------------------------------------------------------
ROW_COST = {"both-on": 1.0, "both-on-twin": 1.0, "perception-off": 0.6, "solver-off": 0.6, "both-off": 0.05}     # full 268-B rows per row
ARM_MIX_ROWS = round(sum(ROW_COST.values()), 2)                                                             # 3.25
ROWS_PER_MINUTE_FULL = 1.84                                                                                 # measured, np4 x 24,576 (P3 programme)
GPU_MARGIN, GPU_ROUND_H = tf.GPU_PLAN_MARGIN, tf.GPU_PLAN_ROUND_H
SMOKE_GPU_HOURS = tsf.SMOKE_GPU_HOURS
PERCEPTION_SHARE_OF_ROW = tsf.SMOKE_MEASURED_S_PER_CONTACT["perception"] / (sum(tsf.SMOKE_MEASURED_S_PER_CONTACT.values()))
THINK_SLOTS = ACTIVE_GEOMETRY["slots"]


def expected_gpu_hours(rows: int) -> float:
    """rows x arm mix (3.25 full rows per row) / 1.84 rows per minute / 60 (unrounded)."""

    return rows * ARM_MIX_ROWS / ROWS_PER_MINUTE_FULL / 60.0


def planned_gpu_hours(rows: int) -> float:
    """The registered ceiling: ``ceil_0.1( expected x 1.3 )``."""

    hours = expected_gpu_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def arm_row_equivalent_rows_per_minute(arm: str) -> float:
    """The rows per minute an arm alone would run at, from its cost in full rows: ``1.84 / cost``."""

    return ROWS_PER_MINUTE_FULL / ROW_COST[arm]


# ---- the single recovery (rec1) of a cell --------------------------------------------------------------------------------------------
#: A (run_id, attempt_id) pair is a one-time key, so a cell whose attempt stopped is re-flown WHOLE under the ``-rec1`` attempt ids (generation AND the live
#: phase fit) with a plan that carries the original plan plus the failed attempt's realised spend (the adapter budget is run-cumulative across the attempts of
#: a run id). The package protocol fixes ONE root-diagnosed recovery per run id; a second failure closes the cell. Generic mechanism:
#: ``scripts/flights/lib/recovery.py``. The failed attempt's spend is the committed snapshot receipt's (read from the attempt record by the lib's CLI, never
#: typed here); the writer re-verifies it against the data root whenever the root is present.
REC = rcv.REC
PREDECESSOR_SNAPSHOT = {"arm": f"{PACKAGE}/predecessor-snapshot-arm-rec1-v1.json"}
_ARM_FIT_ATTEMPT_FIRST = "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-fit-v1"


def _arm_recovery() -> dict:
    snap = rcv.load_snapshot(REPO_ROOT / PREDECESSOR_SNAPSHOT["arm"])
    fit = snap.get("fit") or {}
    calls, audio = snap["actual_calls"], snap["actual_audio_seconds"]
    return {
        "recovery_index": 1,
        "recovered_at": "2026-10-14",
        "ledger_title": "the column flight re-registration (Windows Update forced restart)",
        "agent": "the NX-T R1 recovery agent (Sonnet)",
        "registered_at_utc": None,                      # the writer's --recovery-registered-at
        "base_commit": None,                            # the writer's --recovery-base-commit
        "worktree": None,
        "branch": None,
        "predecessor_attempt_id": snap["attempt_id"],
        "predecessor_fit_run_id": fit["run_id"],
        "predecessor_fit_attempt_id": fit["attempt_id"],
        "fit_predecessor_phrase": (f"no attempt record was opened for it, its prepared directory holds {fit['prepared_request_fit_envelopes']:,} "
                                   "request-fit envelopes preserved unread on the data root"),
        "predecessor_state": (
            f"{snap['state']} at flight commit 37e177e3e from 2026-10-14T12:18:45Z, killed by a host restart at 15:29Z; {calls:,} calls / {audio:.2f} "
            f"speech-seconds realised per its attempt record (reserved {snap['reserved_calls']:,} / {snap['reserved_audio_seconds']:,.0f}); no trace was "
            "written (the run directory holds only the session-attach receipt); preserved unread."),
        "predecessors": [rcv.predecessor_from_snapshot(snap)],
        "reason": (
            "The predecessor attempt was killed by a Windows Update forced restart of the host (System event log 1074: 15:29Z MoUsoCoreWorker \"operating "
            "system: Service Pack (planned)\", 15:33Z TrustedInstaller \"operating system: upgrade (planned)\"). The trace sink buffers until the seal, so "
            "the attempt left no trace and the E10 mode-A resume has nothing to replay; the column flight is re-flown WHOLE under the rec1 ids. The smoke "
            "cell sealed at 2026-10-14T12:16Z, was signed off at 12:18:33Z and is NOT re-flown."),
        "root_cause": ("infrastructure, not the cell: a Windows Update forced restart (System event log 1074) killed the host session; no defect in the "
                       "cell, the runtime or any registered knob"),
        "amendment": (
            "RECOVERY 2026-10-14 (the cell's single one; owner decision 309 A, coordinator brief, Fable 5.1). The generation budget is run-cumulative across "
            "the attempts of the run id (core/model/adapter.py; every attempt state counts, an OPENED one included), so the rec1 plan carries the original "
            f"plan plus the failed attempt's recorded spend ({calls:,} calls, {audio:g} speech-seconds, read from the attempt record into "
            f"{PREDECESSOR_SNAPSHOT['arm']}). The FIT cap is structural and unchanged (rows x program contacts x endpoints per contact). The FIT run id and "
            "the FIT attempt id both take the rec1 marker because the cell is re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation "
            "run id is unchanged. The registered GPU-hour ceiling does not change."),
        "fix": ("none in the cell; infrastructure: the Windows Update auto-restart policy is set (decision 310 A) and the data-disk mount task is fixed "
                "(decision 311)"),
        "unchanged": ("Unchanged: the smoke cell `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-smoke-4-v1` (sealed, signed off, not re-flown; its "
                      "baseline, experiment, ids and attempt are untouched) and every registered knob, arm, policy, roster, prompt, geometry, cap and the "
                      "41.4 GPU-hour ceiling of the arm cell."),
        "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
        "fit_cap_rule": "The FIT cap is structural: rows x program contacts x endpoints per contact.",
    }


RECOVERIES: dict[str, dict] = {"arm": _arm_recovery()}
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
        "model": CONTROL_MODEL if key == "smoke" else THINK_MODEL, "session": CONTROL_SESSION if key == "smoke" else THINK_SESSION,
        "prefix": "smoke-" if key == "smoke" else "",
        "campaign": f"configs/campaign/slurp-native-stage3-{ids_stem}-v1.json",
    }


CELLS = {
    "smoke": _spec("smoke", "four-row form smoke of the thinking-policy column", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   ids_stem=f"{SLUG}-smoke-4", parent_key="smoke"),
    "arm": _spec("arm", "thinking-policy column flight (five arms in one flight)", ROWS, "arm", 1, planned_gpu_hours(ROWS),
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
    """rows x program contacts x endpoints per contact (never run-cumulative): 43,200 for a 1,080-row cell."""

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
    """The first-attempt plan ceiling: rows x (program contacts + fallback contacts per row) = rows x 16."""

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


#: Context fit at the 4,096-token cap is the 268-B lock's (every arm's request is at most that long): live prompt limit 17,406 against the measured
#: Solver prompt maximum 14,641 (a non-delivering arm adds no evidence; its Perception note differs, which moves the Solver prompt by a few hundred
#: tokens at most). The per-contact exact gate runs on every arm's REAL request.
PROMPT_LIMIT_THINKING, SOLVER_PROMPT_TOKENS_MAX = tsf.PROMPT_LIMIT_THINKING, tsf.SOLVER_PROMPT_TOKENS_MAX
#: The group's fit estimate (``thinking_frame.fit_estimate``): measured inputs of the 268-B lock (Solver prompt max 14,641 at 55 supplied items).
#: base 2,000 + 55 x 235 = 14,925 -> the delivering arm's measured scale; completion ceiling = the geometry cap 4,096.
FIT_ESTIMATE = {"base_prompt_tokens": 2000, "completion_ceiling": tsf.THINK_MAX_TOKENS, "slot_tokens": 24576, "tokens_per_supplied_item": 235}
MAX_SUPPLIED_ITEMS = tf.DELIVERING_MAX_SUPPLIED_ITEMS      # 55: the lock's own supply bound; every arm renders the delivering arm's evidence


# ---- the SEAL-ONLY completion of the stopped column (2026-10-15) ----------------------------------------------------------------------
#: The rec1 column attempt stopped after 1,029 complete rows: row 1,030 (admission index 1,014) ended on a non-delivering ``both-off`` Solver contact that hit
#: its 1,024-token no-think cap, the harness raised ``RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column`` and the other 50 rows were
#: never started. The completion is a SEAL-ONLY registration of the 1,029 complete rows under the SAME run id (the precedent: P-SV-1 ``scripts/flights/psv/``):
#: a new attempt id, ``resume_from`` the stopped attempt by trace sha256 (mode A: the harness fix changes ``rails/runner.py``, which a mode-B checkpoint resume
#: refuses by its code-identity pin), the roster fixed to the complete rows (a strict subset of the Fold B roster, its own dataset fragment and split identity),
#: zero model contacts. Package ``docs/readiness/<date>-<package>-sealonly-v1/``; derived by ``nxt_r1_sealonly_derive_cell.py``.
SEALONLY_PKG_NAME = f"{PKG_NAME}-sealonly-v1"
SEALONLY_PACKAGE = f"docs/readiness/{DATE}-{SEALONLY_PKG_NAME}"
SEALONLY_PREREG = f"{SEALONLY_PACKAGE}-preregistration.md"
SEALONLY_DECISION_ID = "slurp-nxt-r1-thinking-policy-fold-b-sealonly-admission-v1"
SEALONLY_DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-sealonly-v1.json"       # beside the column's own receipt
SEALONLY_PROOF_RUN_ID = "SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-SEALONLY-REPLAY-PROOF-V1"
SEALONLY_COMPLETE_ROWS = f"{SEALONLY_PACKAGE}/complete-rows-v1.json"                           # roster-receipt shaped: items[].sample_id / stratum / utterance_id
SEALONLY_ANALYSIS_DIR = "sealonly"                                                              # under ``analysis/<READ_RUN_ID>/``
SEALONLY_FLIGHT_COMMIT_FILE = "/home/chao/nxt1seal-flight-commit.txt"


def sealonly_spec() -> dict:
    """The seal-only completion's identities, derived from the arm cell's rec1 identities (never typed twice)."""

    arm = CELLS["arm"]
    stem = f"slurp-native-stage3-{SLUG}"
    return {
        "package": SEALONLY_PACKAGE, "preregistration": SEALONLY_PREREG,
        "experiment": f"{stem}-v1-sealonly", "cell": f"{stem}-v1-sealonly", "baseline": f"{stem}-baseline-v1-sealonly",
        "parent_cell": arm["cell"], "parent_baseline": arm["baseline"],
        "run": arm["run"], "fit_run": arm["fit_run"],
        "predecessor_attempt": arm["attempt"],
        "attempt": arm["attempt"].replace("-rec1-v1", "-rec1-sealonly-v1"),
        "fit_attempt": arm["fit_attempt"].replace("-rec1-v1", "-rec1-sealonly-v1"),
        "decision_id": SEALONLY_DECISION_ID, "decision_relpath": SEALONLY_DECISION_RELPATH, "proof_run": SEALONLY_PROOF_RUN_ID,
        "read_run": READ_RUN_ID, "complete_rows": SEALONLY_COMPLETE_ROWS, "analysis_dir": SEALONLY_ANALYSIS_DIR,
        "session": arm["session"], "model": arm["model"],
    }


__all__ = [name for name in globals() if not name.startswith("_")]
