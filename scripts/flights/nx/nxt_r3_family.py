"""Shared identities of NX-T R3: the Solver INSTRUCTION-TEMPLATE column on the Thinking core, TRAIN Fold B (the USE-node round).

One module, imported by the derive, writer, mint, reader, chain and test scripts, so no id is spelled twice. Model-free. It follows the NX-T R2 / R2b package
form and reuses what they reused: ``thinking_system_family`` (the Thinking model fragment family, packet root and its pinned promotion receipt, the lock v2.2 + v4g
plain-lock program, the Fold B roster), ``tfrl_family`` (the FIT arithmetic and the derive helpers) and ``recovery`` (the generic rec1 / rec2 mechanism). R2's and
R2b's own files are not changed.

WHAT THE CELL IS. Owner ruling 326 A (2026-10-17) opens the USE node: ONE flight of the locked Thinking system (the 268-B lock: lock v2.2 + v4g, the review-off
COMP-1b module graph, Perception AND Solver both thinking at budget 3,072 / cap 4,096) on TRAIN Fold B (1,080 rows) with a same-flight COLUMN over the Solver's
INSTRUCTION TEMPLATE (``roles.solver.template_variants``, receipt ``saea-supply-variant-arms-v4``, the NX node-template instrument). The Solver is contacted K = 6 times
over the SAME Perception note, the SAME evidence and the SAME QueryState, once per template; every contact carries the lock's decoding and per-node thinking fields
(role-keyed at request composition, so an arm contact cannot differ: proved by ``tests/unit/test_nxt_r3_registration.py``). The arm set is DATA
(``nxt_r3_arms.json``): four hash-pinned candidate templates, each the locked Solver template plus one short paragraph (``configs/probes/nx/solver/thinking/``), the
twin ``aa`` (``replicate_of`` lock) and the delivering arm ``lock`` (the locked template, untemplated, LAST). ``arm_visits`` is ``first``.

  ``t1-decide-once``            reasoning termination: reason briefly, decide each slot once, stop thinking when every slot is decided
  ``t2-grounded-or-empty``      precision: output an entity only when its value is heard; an empty entities array is a correct answer
  ``t3-supply-focus``           supply focus: fix the intent first, consult only that intent's supplied items, ignore the other candidates' cards
  ``t4-decide-once-grounded``   t1 + t2 together
  ``aa``                        the in-flight A/A (the locked template again)
  ``lock``                      the delivering arm: the 268-B lock form; its requests are the lock's, byte for byte

The serving target is the RESIDENT ``think-budget-np4`` session (fragment ``...-budget3072-max4096-v1``, ``-c 98304 -np 4``, four 24,576-token slots): no new
fragment, no cell-level thinking policy (the fragment's defaults ARE the lock form). The swap call is kept and is a no-op when that session is resident.

GPU CEILING. From the NX-T R2b measured throughput of the delivering arm (``nxt_r3_cost_inputs.json``: 9.23 GPU-h per 1,080-row lock flight, Perception 59 s and Solver
64.07 s per contact at 4 slots): a row costs one Perception contact plus K Solver contacts, every Solver contact costed at the lock's Solver seconds (an upper
envelope). The arm mix is that row in lock-row equivalents, rounded UP to 0.01:
    expected GPU-h = rows x arm mix / rows-per-minute / 60            (rows per minute = 4 slots x 60 / the lock row seconds, registered rounded DOWN to 0.01)
    ceiling        = ceil_0.1( expected x 1.3 )
Ceilings are bounds, never targets (owner: runs of 24 GPU-h or more are intended). The four-row smoke keeps the 0.5 GPU-h form allowance.
"""

from __future__ import annotations

import hashlib
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

DATE = "2026-10-18"
SLUG = "nxt-r3-solver-template-fold-b"
SHORT = "nxt3"
PKG_NAME = "slurp-nxt-r3-solver-template-fold-b-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
SIGNOFF_CONDITIONS = f"{PACKAGE}/signoff-conditions-v1.json"      # emitted by the derive, INSIDE the package
DECISION_ID = "slurp-nxt-r3-solver-template-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1"
RECIPE_ID = "slurp-nxt-r3-solver-template-fold-b-read-v1"
READER = "scripts/analysis/slurp_nxt_r3_solver_template_column_read.py"
ANALYSIS_ROOT = f"analysis/{READ_RUN_ID}"
LEDGER_MARK = ("## Cell NXT-R3: the Solver instruction-template column on the Thinking core, TRAIN Fold B (one flight, four candidate templates plus the twin and the "
               "delivering arm; smoke then 1,080 rows)")
OWNER_RULINGS = "owner rulings 326 A and 327 A (2026-10-17), 313 A (2026-10-14) and 304/307 (2026-10-13), coordinator approval of the NX-T R3 design"
SMOKE_SCHEMA = "saea-nxt-r3-solver-template-column-smoke-v1"
READ_SCHEMA = "saea-nxt-r3-solver-template-column-read-v1"
READ_TITLE = "NX-T R3 read -- the Solver instruction-template column"
SPEC_DESIGN = "docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md"

# ---- the system and the roster: exactly the 268-B lock, one flight --------------------------------------------------------------
ROWS, SMOKE_ROWS = tsf.ROWS, tsf.SMOKE_ROWS
LOCK, PROGRAM_BASE = tsf.LOCK, tsf.PROGRAM                 # v2.2; the plain lock program phase-native-module-v1-c2 (the base the column adds to)
SCORER = tsf.SCORER
DATASET, SPLIT_ID = tsf.DATASET, tsf.SPLIT_ID
TUNING_ROSTER, READ_ROSTER = "none", tsf.READ_ROSTER
ROSTER = dict(tsf.ROSTER)
PARENT = tsf.CELLS                                          # the 268-B cells the baselines/experiments are derived from (lock + smoke)
PARENT_SMOKE_KEY, PARENT_ARM_KEY = "smoke", "lock"
NODE = "solver"
NODES = ("perception", "solver")

# ---- the arm table (DATA: nxt_r3_arms.json) -----------------------------------------------------------------------------------------
ARMS_PATH = HERE / "nxt_r3_arms.json"
ARM_TABLE_SCHEMA = "saea-nxt-r3-arm-table-v1"
MAX_CANDIDATE_ARMS = 6                                      # rails.supply_variants.MAX_TEMPLATE_CANDIDATE_ARMS
DELIVERING, TWIN = "lock", "aa"
LOCKED_TEMPLATE = "configs/probes/slurp_native_role_solver_v2.txt"
LOCKED_TEMPLATE_SHA = "18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd"
TEMPLATE_CHARS_PER_TOKEN = 3.5                              # the estimate method of the NX R1 packages (nx_r1_fit_measure.py); no tokenizer contact
CANDIDATE_DIR = "configs/probes/nx/solver/thinking/"
_ARM_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ArmTableError(ValueError):
    """The arm table is malformed or breaks a registered rule (fail closed, by name)."""


def sha256_file(relpath: str, root: Path | None = None) -> str:
    return hashlib.sha256(((Path(root) if root else REPO_ROOT) / relpath).read_bytes()).hexdigest()


def template_tokens(relpath: str, root: Path | None = None) -> int:
    """The template token ESTIMATE: ceil(bytes / 3.5), the method of the NX R1 packages (no tokenizer contact)."""

    return math.ceil(len(((Path(root) if root else REPO_ROOT) / relpath).read_bytes()) / TEMPLATE_CHARS_PER_TOKEN)


def validate_arm_table(table: object, root: Path | None = None) -> list[dict]:
    """Validate the arm-table document against the files on disk and return its candidate arms (declared order). Every refusal names the rule."""

    keys = {"_note", "arms", "delivering", "locked_template", "schema", "twin"}
    if not isinstance(table, dict) or set(table) != keys:
        raise ArmTableError(f"the arm table must be exactly {sorted(keys)}")
    if table["schema"] != ARM_TABLE_SCHEMA:
        raise ArmTableError(f"schema must be {ARM_TABLE_SCHEMA!r}")
    if (table["delivering"], table["twin"]) != (DELIVERING, TWIN):
        raise ArmTableError(f"the delivering arm is {DELIVERING!r} and the twin {TWIN!r}")
    if table["locked_template"] != {"relpath": LOCKED_TEMPLATE, "sha256": LOCKED_TEMPLATE_SHA}:
        raise ArmTableError("locked_template must be the Solver template the Thinking lock renders")
    if sha256_file(LOCKED_TEMPLATE, root) != LOCKED_TEMPLATE_SHA:
        raise ArmTableError("the locked Solver template bytes moved")
    arms = table["arms"]
    if not isinstance(arms, list) or not 1 <= len(arms) <= MAX_CANDIDATE_ARMS:
        raise ArmTableError(f"between 1 and {MAX_CANDIDATE_ARMS} candidate arms")
    locked = (Path(root) if root else REPO_ROOT).joinpath(LOCKED_TEMPLATE).read_bytes().decode("utf-8")
    seen: set[str] = set()
    digests: set[str] = set()
    out = []
    for position, arm in enumerate(arms):
        where = f"arms[{position}]"
        if not isinstance(arm, dict) or set(arm) != {"arm_id", "evidence", "relpath", "sha256"}:
            raise ArmTableError(f"{where} must be exactly {{arm_id, evidence, relpath, sha256}}")
        arm_id = arm["arm_id"]
        if not isinstance(arm_id, str) or not _ARM_ID.match(arm_id) or arm_id in (DELIVERING, TWIN) or arm_id in seen:
            raise ArmTableError(f"{where}.arm_id {arm_id!r} must be a distinct lower-case id other than {DELIVERING!r} and {TWIN!r}")
        seen.add(arm_id)
        if not str(arm["relpath"]).startswith(CANDIDATE_DIR):
            raise ArmTableError(f"{where}.relpath must sit under {CANDIDATE_DIR}")
        actual = sha256_file(arm["relpath"], root)
        if actual != arm["sha256"]:
            raise ArmTableError(f"{where}: {arm['relpath']} hashes to {actual}, not the pinned {arm['sha256']}")
        if arm["sha256"] in digests or arm["sha256"] == LOCKED_TEMPLATE_SHA:
            raise ArmTableError(f"{where}: two arms (or the lock) share one template")
        digests.add(arm["sha256"])
        text = (Path(root) if root else REPO_ROOT).joinpath(arm["relpath"]).read_bytes().decode("utf-8")
        marker = "On a revision, reconsider"
        head, tail = locked[:locked.index(marker)], locked[locked.index(marker):]
        if not (text.startswith(head) and text.endswith(tail) and len(text) > len(locked)):
            raise ArmTableError(f"{where}: a candidate template must be the locked template with paragraph(s) added before the revision paragraph, nothing else changed")
        out.append({"arm_id": arm_id, "evidence": arm["evidence"], "relpath": arm["relpath"], "sha256": arm["sha256"], "template_tokens": template_tokens(arm["relpath"], root),
                    "added_paragraphs": text[len(head):len(text) - len(tail)].strip("\n").split("\n\n")})
    return out


def load_arm_table(path: Path = ARMS_PATH) -> list[dict]:
    return validate_arm_table(json.loads(Path(path).read_text(encoding="utf-8")))


ARM_SPECS = load_arm_table()
CANDIDATE_ARMS = tuple(a["arm_id"] for a in ARM_SPECS)
ARM_ORDER = (*CANDIDATE_ARMS, TWIN, DELIVERING)             # declared order; the twin, then the delivering arm LAST
K = len(ARM_ORDER)
CONTACTS_PER_ROW = 2 + (K - 1)                              # review-off base 2 + (K - 1) extra Solver contacts (c7 for K = 6)
PROGRAM = f"phase-native-module-v1-c{CONTACTS_PER_ROW}"
DELIVERING_TEMPLATE_TOKENS = template_tokens(LOCKED_TEMPLATE)
TEMPLATE_TOKENS = {**{a["arm_id"]: a["template_tokens"] for a in ARM_SPECS}, DELIVERING: DELIVERING_TEMPLATE_TOKENS}
#: Budgeted-thinking contacts per row (an answer-only fallback re-ask is possible only for a budgeted thinking request): Perception 1 + K Solver contacts, all thinking.
THINKING_CONTACTS_PER_ROW = 1 + K
FALLBACK_CONTACTS_PER_ROW_CEILING = THINKING_CONTACTS_PER_ROW

# ---- the Thinking serving geometry: the RESIDENT np4 session, unchanged -------------------------------------------------------------------
SERVING_LIB = "scripts/flights/batch/serving_lib.sh"
SWAP_TARGET = tsf.THINK_SWAP_TARGET                         # think-budget-np4


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
if (THINK_MODEL, THINK_SESSION, THINK_SWAP_TARGET) != (tsf.THINK_MODEL, tsf.THINK_SESSION, tsf.THINK_SWAP_TARGET):
    raise ValueError("serving_lib.sh row of think-budget-np4 does not match the 268-B Thinking family's session and fragment")
CONTROL_SESSION, CONTROL_MODEL, CONTROL_SWAP_TARGET = THINK_SESSION, THINK_MODEL, THINK_SWAP_TARGET
CONTROL_SLOTS, CONTROL_SLOT_TOKENS = THINK_SLOTS, ACTIVE_GEOMETRY["slot_tokens"]
DEFAULT_GEOMETRY = THINK_SWAP_TARGET


def geometry_of(key: str) -> dict:
    return ACTIVE_GEOMETRY


def think_model_text(key: str) -> str:
    """The ledger model/tool text of a cell (the resident np4 server geometry, the lock's decoding, the per-arm Solver template)."""

    g = ACTIVE_GEOMETRY
    return ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, "
            f"c{g['slots'] * g['slot_tokens']} np{g['slots']} x {g['slot_tokens']:,} max{tsf.THINK_MAX_TOKENS} (reasoning budget {tsf.THINK_BUDGET_TOKENS} on both nodes), q8_0 KV, "
            f"--reasoning-format deepseek (model fragment {g['model_fragment']}); its own promoted speech packets; module program {PROGRAM}; "
            "per-arm Solver instruction template; no tool authority")


THINK_PACKET_ROOT, THINK_PROMOTION_RECEIPT = tsf.THINK_PACKET_ROOT, tsf.THINK_PROMOTION_RECEIPT
THINKING_KNOBS = json.loads(json.dumps(tsf.THINKING_KNOBS))
DELIVERING_BUDGET, COMPLETION_CAP = tsf.THINK_BUDGET_TOKENS, tsf.THINK_MAX_TOKENS

# ---- external references (the 268-B and P3.1 reads; development numbers) ---------------------------------------------------------
THINKING_SYSTEM_SLU, THINKING_SYSTEM_INTENT = 71.61, 85.00                  # 268-B lock arm
TWIN_OFFSET_268B_SLU_PP, TWIN_OFFSET_268B_INTENT_PP = 1.15, -0.09            # 268-B cross-flight twin offset
TWIN_OFFSET_P31_SLU_PP, TWIN_OFFSET_P31_INTENT_PP = -0.61, 1.60              # P3.1 (DEV-2000-ADDED) cross-flight twin offset
FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65                                  # decision 190 node-column floors at n = 1,080
INTENT_GUARD_PP = -0.65                                                     # NOMINATED needs the intent point at or above this
EFFICIENT_SECONDS_RATIO = 0.85                                              # EFFICIENT-NO-LOSS needs Solver seconds per contact <= 0.85 x lock
EXPECTED_EFFECT_PP = 0.0                                                    # no effect is assumed; the round maps four templates

# ---- budget arithmetic (one place) ---------------------------------------------------------------------------------------------------
COST_INPUTS_PATH = HERE / "nxt_r3_cost_inputs.json"
COST_INPUTS = json.loads(COST_INPUTS_PATH.read_text(encoding="utf-8"))
M = COST_INPUTS["r2b_measured"]
NODE_SECONDS = {"perception": float(M["perception_seconds_per_contact_mean"]), "solver": float(M["solver_seconds_per_contact_mean"])}
SECONDS_PER_ROW_LOCK = float(M["seconds_per_row_lock"])
R2B_SLOTS = int(M["slots"])
LOCK_FLIGHT_GPU_HOURS_MEASURED = float(M["gpu_hours_per_1080_row_lock_flight"])


def ceil_hundredth(value: float) -> float:
    return math.ceil(round(value * 100.0, 9)) / 100.0


def floor_hundredth(value: float) -> float:
    return math.floor(round(value * 100.0, 9)) / 100.0


#: One row = one Perception contact + K Solver contacts, in lock-row equivalents (lock row = Perception + one Solver), rounded UP to 0.01.
ARM_MIX_ROWS = ceil_hundredth((NODE_SECONDS["perception"] + K * NODE_SECONDS["solver"]) / (NODE_SECONDS["perception"] + NODE_SECONDS["solver"]))
ROW_COST = {"column-row": ARM_MIX_ROWS, "lock-row": 1.0}
#: rows per minute of a lock-only pass at the measured seconds per row and 4 slots, registered rounded DOWN to 0.01 (a lower rate means more GPU-hours).
ROWS_PER_MINUTE_FULL = floor_hundredth(R2B_SLOTS * 60.0 / SECONDS_PER_ROW_LOCK)
GPU_MARGIN, GPU_ROUND_H = tf.GPU_PLAN_MARGIN, tf.GPU_PLAN_ROUND_H
SMOKE_GPU_HOURS = tsf.SMOKE_GPU_HOURS


def expected_gpu_hours(rows: int) -> float:
    """rows x arm mix / rows per minute / 60 (unrounded)."""

    return rows * ARM_MIX_ROWS / ROWS_PER_MINUTE_FULL / 60.0


def planned_gpu_hours(rows: int) -> float:
    """The registered ceiling: ``ceil_0.1( expected x 1.3 )``."""

    hours = expected_gpu_hours(rows) * GPU_MARGIN
    return round(math.ceil(round(hours / GPU_ROUND_H, 9)) * GPU_ROUND_H, 1)


def lock_flight_gpu_hours(rows: int = ROWS) -> float:
    """The projected GPU-h of a ``rows``-row LOCK-only flight at the registered rate."""

    return rows / ROWS_PER_MINUTE_FULL / 60.0


# ---- the context fit (the registered FIT_ESTIMATE form at the lock's cap) ---------------------------------------------------------------
SLOT_TOKENS, RESERVE_TOKENS, SPECIAL_RESERVE = tsf.SLOT_TOKENS, tsf.RESERVE_TOKENS, tsf.SPECIAL_RESERVE
PROMPT_LIMIT = tsf.PROMPT_LIMIT_THINKING                                                    # 17,406 at the 4,096 cap
FIT_ESTIMATE = {"base_prompt_tokens": 2000, "completion_ceiling": COMPLETION_CAP, "slot_tokens": SLOT_TOKENS, "tokens_per_supplied_item": 235}
MAX_SUPPLIED_ITEMS = tf.DELIVERING_MAX_SUPPLIED_ITEMS                                       # 55: the lock's own bound
OBSERVATIONS = {item["id"]: item for item in COST_INPUTS["fit_observations"]["sets"]}
OBSERVED_SOLVER_PROMPT_MAX = max(item["solver_prompt_tokens_max"] for item in OBSERVATIONS.values())


def estimated_prompt_tokens(items: int, template: int = 0) -> int:
    return FIT_ESTIMATE["base_prompt_tokens"] + template + items * FIT_ESTIMATE["tokens_per_supplied_item"]


def fit_proof() -> dict:
    """The context-fit proof of the template column, registered in the fit plan; ``ok`` is False (and the derive REFUSES) when the live slot cannot hold the longest
    template's Solver prompt plus the 4,096-token cap."""

    longest = max(TEMPLATE_TOKENS.values())
    added = longest - DELIVERING_TEMPLATE_TOKENS
    estimate = estimated_prompt_tokens(MAX_SUPPLIED_ITEMS, longest)
    checks = {
        "estimate_at_bound_fits_every_arm": estimate <= PROMPT_LIMIT,
        "observed_solver_prompt_max_plus_longest_added_fits": OBSERVED_SOLVER_PROMPT_MAX + added <= PROMPT_LIMIT,
        "slot_holds_prompt_plus_cap": OBSERVED_SOLVER_PROMPT_MAX + added + COMPLETION_CAP <= SLOT_TOKENS,
        "bound_is_positive": MAX_SUPPLIED_ITEMS >= 1,
    }
    return {
        "slot_tokens": SLOT_TOKENS, "slots": ACTIVE_GEOMETRY["slots"], "reserve_tokens": RESERVE_TOKENS, "special_reserve_tokens": SPECIAL_RESERVE,
        "completion_cap": COMPLETION_CAP, "prompt_limit_tokens": PROMPT_LIMIT, "fit_estimate": dict(FIT_ESTIMATE), "max_supplied_items": MAX_SUPPLIED_ITEMS,
        "template_tokens": dict(TEMPLATE_TOKENS), "template_token_method": f"ceil(bytes / {TEMPLATE_CHARS_PER_TOKEN}); no tokenizer contact (the NX R1 estimate method)",
        "longest_template_tokens": longest, "longest_added_tokens_over_lock": added, "estimate_at_bound_tokens": estimate, "estimate_headroom_tokens": PROMPT_LIMIT - estimate,
        "observed_solver_prompt_tokens_max": OBSERVED_SOLVER_PROMPT_MAX, "observed_headroom_tokens": PROMPT_LIMIT - OBSERVED_SOLVER_PROMPT_MAX - added,
        "observations": json.loads(json.dumps(OBSERVATIONS)), "checks": checks, "ok": all(checks.values()),
        "note": ("The Solver prompt mean is about 8,500 tokens against the 4,096 cap (prompt limit 17,406). A candidate template adds at most the longest template's extra "
                 "paragraph(s) to the lock's; the sealed Fold B Solver prompt maximum plus that addition still fits the limit and the slot. The context-fit policy is "
                 "compact-or-abstain, and the exact per-contact gate runs on every arm's REAL request."),
    }


# ---- the recoveries of a cell ----------------------------------------------------------------------------------------------------------
#: A (run_id, attempt_id) pair is a one-time key, so a cell whose attempt stopped is re-registered under the ``-recN`` attempt ids (generation AND the live
#: phase fit) with a plan that carries the original plan plus every earlier attempt's realised spend (run-cumulative). Generic mechanism:
#: ``scripts/flights/lib/recovery.py``. ``RECOVERIES`` is EMPTY on the first registration; every recovery is data-driven: the coordinator commits a predecessor
#: snapshot (``recovery.py snapshot`` for rec1, ``nxt_r3_rec2_snapshot.py`` for rec2) and a diagnosis input per recovery and the family builds
#: ``RECOVERY_HISTORY["arm"]`` from them. A predecessor's spend is the snapshot's, never typed here.
#:
#: * ``rec1`` hook: the column flight re-flown WHOLE after a host failure killed the first attempt. Files: ``predecessor-snapshot-arm-rec1-v1.json`` (the FIRST
#:   attempt) and ``recovery-input-arm-v1.json``.
#: * ``rec2`` hook (the resume form): the rec1 attempt was stopped; rec2 is a RESUME of it (a stopped attempt is resumed, never re-flown whole, whenever a checkpoint or
#:   trace exists), under an explicit owner exception to the one-recovery rule. Files: ``predecessor-snapshot-arm-rec2-v1.json`` (written by ``nxt_r3_rec2_snapshot.py``)
#:   and ``recovery-input-arm-rec2-v1.json`` (the diagnosis plus ``owner_exception`` and the COMPUTED ``resume_mode``; ``nxt_r3_rec2_mode.py``).
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
    """The arm cell's rec1 recovery record from the committed diagnosis ``inputs`` and the predecessor ``snap`` receipt."""

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
        "unchanged": ("Unchanged: the smoke cell (sealed, signed off, not re-flown) and every registered template, arm, roster, prompt, geometry, cap and the "
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
    """The arm cell's rec2 recovery record: a RESUME of the stopped rec1 attempt. ``first`` = the first attempt's snapshot, ``stopped`` = the rec1 attempt's snapshot (trace
    and checkpoint pins, both replay classifications, the code-identity comparison); ``inputs`` = the committed diagnosis and the computed ``resume_mode``."""

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
    pin_sha = trace["checkpoint_sha256"] if mode == "checkpoint" else trace["trace_sha256"]
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
            f"{gpu:.1f} GPU-h ({flown:,} rows x {ARM_MIX_ROWS} lock-row equivalents / {ROWS_PER_MINUTE_FULL} rows per minute). `--allow-output-change` is never "
            f"passed: the rebuilt supply, the roster ({ROWS:,} rows) and the read (n = {ROWS:,}) are the registered ones."),
        "fix": inputs["fix"],
        "unchanged": (f"Unchanged: the smoke cell `slurp-native-stage3-{SLUG}-smoke-4-v1` (sealed, not re-flown) and every registered template, arm, roster ({ROWS:,} rows), "
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
    "smoke": _spec("smoke", "four-row form smoke of the Solver template column", SMOKE_ROWS, "smoke", 0, SMOKE_GPU_HOURS,
                   ids_stem=f"{SLUG}-smoke-4", parent_key="smoke"),
    "arm": _spec("arm", f"Solver instruction-template column flight ({K} arms in one flight)", ROWS, "arm", 1, planned_gpu_hours(ROWS),
                 ids_stem=SLUG, parent_key="lock"),
}
ARM_KEYS = ("arm",)
ALL_KEYS = ("smoke", "arm")


def eligible_run_ids() -> list[str]:
    """The decision receipt's eligible run ids: each cell's generation run id then its first-registration FIT run id, in chain order, then the FIT run id of every
    recovery, oldest first (each receipt's list is a strict prefix of the next)."""

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
    """The audio the K - 1 extra Solver contacts re-send: (K - 1) extra contacts per row."""

    return roster_audio(kind) * (CONTACTS_PER_ROW - 2)


def thinking_promotion_sha256() -> str:
    return tsf.thinking_promotion_sha256()


def signoff_conditions() -> dict:
    """The machine sign-off conditions (owner ruling 314 A; ``scripts/flights/batch/smoke_signoff.py``) FOR THIS ARM TABLE. The derive emits them inside the package, so
    a change of the table regenerates them."""

    return {
        "schema": "saea-smoke-signoff-conditions-v1",
        "_note": (f"NX-T R3 machine sign-off conditions (owner ruling 314 A), emitted by nxt_r3_derive_cells.py from {ARMS_PATH.name}; regenerated whenever the arm table changes. "
                  "The smoke's job is to show that every node closes within its own cap (no cap hit, no empty answer, no malformed JSON, no length finish), that the cost is no "
                  "more than 1.3x the registered arm mix, and that no arm column is absent or unattributed. No node is no-think in this round."),
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
