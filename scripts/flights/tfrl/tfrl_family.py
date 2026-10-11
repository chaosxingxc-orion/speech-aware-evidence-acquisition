"""Shared identities of the autonomous typed loop with the ACE comparator (decision 263-A), per iteration.

One module, imported by the protocol builder, the derive and registration scripts, the loop driver and the tests, so no id is
spelled twice. Model-free. Read constants as ``tf.NAME`` and call ``tf.names(t, kind)`` for the per-iteration identities.

STATUS. DRAFT / HELD. Nothing here registers a cell, authorises a flight or writes an exposure-ledger row. The coordinator
countersigns later (design section 7: the countersign attests conformance only).

ARM SETS (design sections 0 and 5.1). Iteration 1: ``ace``, ``aa`` (twin) and ``lock`` (delivering, last) -- the typed arm is
EMPTY by measurement when no candidate clears the 1.5 pp predicted bar (the 265 coverage pre-read; decision 266 proposed), and
an empty typed arm is a LEGAL state. From iteration 2: ``typ`` (the typed child, when a valid candidate exists), ``par`` (the
accumulated accepted typed parent), ``ace``, ``aa``, ``lock``. The arm order in a flown block is: candidates first, then the
twin, then the delivering arm LAST (rails.consumption_module._compile_supply_columns).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-11"
LOOP_ID = "SAEA-SLURP-TFRL-LOOP-V1"
PACKAGE_NAME = "slurp-tfrl-loop-v1"
PACKAGE_DIR = f"docs/readiness/{DATE}-{PACKAGE_NAME}"
PROTOCOL_RELPATH = f"{PACKAGE_DIR}/tfrl-loop-protocol-v1.json"
ANALYSIS_ROOT = f"analysis/{LOOP_ID}"          # the ONLY place under the data root this loop writes (design section 7)

ITERATIONS = (1, 2, 3)
STOP_AFTER_ITERATIONS = 3

# ---- arms ----------------------------------------------------------------------------------------------------------------
DELIVERING, TWIN = "lock", "aa"
ARM_TYPED, ARM_PARENT, ARM_ACE = "typ", "par", "ace"
ALGORITHM_TYPED = "sealed-credit-system-policy-v1"
ALGORITHM_ACE = "ace-grow-refine-v1"
ACE_STORE_ID = "ace-playbook"

#: The five Solver arms of a flown block by iteration; ``typ`` is present only when a valid candidate cleared the bar.
def arm_ids(iteration: int, *, typed_present: bool = False, parent_present: bool | None = None) -> tuple[str, ...]:
    """Declared arm order of the iteration's supply block (candidates, twin, delivering LAST)."""

    if iteration not in ITERATIONS:
        raise ValueError(f"iteration must be one of {ITERATIONS}")
    if parent_present is None:
        parent_present = iteration >= 2
    arms: list[str] = []
    if parent_present and iteration >= 2:
        arms.append(ARM_PARENT)
    if typed_present:
        arms.append(ARM_TYPED)
    arms.append(ARM_ACE)
    arms.extend((TWIN, DELIVERING))
    return tuple(arms)


#: Contacts per row: Perception 1 + Solver K arms (K = len(arm_ids)).
def ceiling(iteration: int, *, typed_present: bool = False, parent_present: bool | None = None) -> int:
    return 1 + len(arm_ids(iteration, typed_present=typed_present, parent_present=parent_present))


def program_id(iteration: int, **kw) -> str:
    return f"phase-native-module-v1-c{ceiling(iteration, **kw)}"


# ---- rosters and folds (design section 5.5) -----------------------------------------------------------------------------
ROWS = 1080
SMOKE_ROWS = 4
ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
}
FOLD_ROLES = {
    "material": {"roster": "SLURP-STAGE3-CONSTRUCTION-R01C", "rows": 625, "roster_relpath": "docs/receipts/rosters/slurp-stage3-construction-r01c.json",
                 "split_identity_hash_prefix": "f56bc386",
                 "role": ("proposer-table and ACE-reflector material source for iterations 1-3: ONE lock column flown on the construction roster "
                          "(TRAIN rows outside Fold A and Fold B); never a selection or confirmation split; re-flown only if the lock changes")},
    "select": {"fold": "SLURP-EVO-FOLD-B-V2", "rows": 1080,
               "role": ("HELD-OUT selection (instrument); never a table, material or knowledge source (it contributes only ACE counters and the "
                        "refused-candidate buffer); read three times, so the winner's curse applies (design R6)")},
    "confirm": {"fold": "SLURP-EVO-FOLD-A-V2", "split_identity_hash_prefix": "61b0f062", "rows": 1080,
                "role": "confirmation, ONE attempt, every rule fixed; prior exposure disclosed"},
    "compose": {"fold": "DEV-2000-ADDED", "roster": "docs/receipts/rosters/slurp-dev-2000-added-v1.json", "rows": 1000,
                "role": "composed read of the final state, same-flight; claim ceiling nominated"},
}
TUNING_ROSTER, READ_ROSTER = "none", "SLURP-EVO-FOLD-B-V2"
PARENT_SLUG = "nx-r6-perception-fold-b"          # the committed R6-P1 Fold B cell the Fold B pins are inherited from
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-train"
#: The lock the iteration cells compose on: v2.3 = v2.2 + the ace-playbook store declared at the empty release i0 (decisions 263 A / 266-A;
#: P-ACE-0: byte-identical requests). PARENT_LOCK is the lock the committed R6-P1 parent block names and the typed root state hashes.
LOCK = "v2.3"
PARENT_LOCK = "v2.2"

# ---- the supply frame every column set shares (measured; re-measure at the FIT step) -------------------------------------------
#: R1 Solver fit measure (docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/fit-measure-v1.json): the delivering arm's
#: first Solver visit already flew in COMP-1b; ``tokens_per_supplied_item`` 235 is the NX fit frame (S1 spec 1.1).
DELIVERING_MAX_SUPPLIED_ITEMS = 55
FIT_ESTIMATE = {"base_prompt_tokens": 2000, "completion_ceiling": 512, "slot_tokens": 24576, "tokens_per_supplied_item": 235}
#: A non-delivering arm may spend the ACE allowance A = 8 items (4.3): 55 + 8.
ALLOWANCE_ITEMS = 8
COLUMN_MAX_SUPPLIED_ITEMS = DELIVERING_MAX_SUPPLIED_ITEMS + ALLOWANCE_ITEMS
FIT_ENDPOINTS_PER_CONTACT = 4
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 1.5, 1.0
PLANNED_GPU_HOURS_TEXT_ONLY = 0.1
FLOOR_SLU_PP, FLOOR_INTENT_PP = 1.49, 0.65         # decision 190 at n = 1,080 (same-flight-supply-variant)
OFFLINE_FLOOR_PP = 0.67                              # an offline delivery / scope candidate (design 5.3)
PREDICTED_BAR_PP = 1.5                               # decision 192 (rails.tfrl_typed_proposer.PREDICTED_SLU_FLOOR_PP)

# ---- proposer / reflector cells -----------------------------------------------------------------------------------------------
TEXT_ONLY_PROGRAM = {"typed": "phase-tfrl-typed-proposer-v1", "ace": "phase-tfrl-ace-reflector-v1"}
TYPED_CARRIERS = 3                                   # construction, supply, delivery+scope (design 3.1)
TYPED_CLASS_SETS = (("construction",), ("supply",), ("delivery", "scope"))
RETRIES = 2
CARRIER_SEED = 20261011
GEPA_CARRIER_PARENT = "gepa"                         # the text-only GEPA proposer cell the two text-only cells are derived from


def n_ace_carriers() -> int:
    from speech_aware_evidence_acquisition.rails.tfrl_typed_proposer import SCENARIOS  # noqa: PLC0415

    return len(SCENARIOS)


def names(iteration: int, kind: str) -> dict:
    """Identities of one iteration's cell. ``kind``: ``arm`` | ``smoke`` | ``typed`` | ``ace``."""

    if iteration not in ITERATIONS:
        raise ValueError(f"iteration must be one of {ITERATIONS}")
    if kind in ("arm", "smoke"):
        smoke = kind == "smoke"
        slug = f"tfrl-loop-i{iteration}-fold-b"
        lo, up = ("-smoke-4" if smoke else ""), ("-SMOKE-4" if smoke else "")
        return {
            "experiment": f"slurp-native-stage3-{slug}{lo}-v1",
            "baseline": f"slurp-native-stage3-{slug}{lo}-baseline-v1",
            "run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}{up}-V1",
            "fit_run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}{up}-FIT-V1",
            "attempt_id": f"attempt-slurp-native-stage3-{slug}{lo}-generation-v1",
            "fit_attempt_id": f"attempt-slurp-native-stage3-{slug}{lo}-fit-v1",
            "prefix": "smoke-" if smoke else "",
            "campaign": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
            "read_run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-COLUMN-READ-V1",
            "recipe_id": f"slurp-{slug}-column-analysis-v1",
        }
    if kind in ("typed", "ace"):
        tag = "proposer" if kind == "typed" else "ace-reflector"
        slug = f"tfrl-{tag}-i{iteration}"
        return {
            "experiment": f"slurp-native-stage3-{slug}-v1",
            "baseline": f"slurp-native-stage3-{slug}-baseline-v1",
            "run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-V1",
            "fit_run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-FIT-V1",
            "attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
            "fit_attempt_id": f"attempt-slurp-native-stage3-{slug}-fit-v1",
            "prefix": f"{tag}-",
            "carrier_roster": f"docs/receipts/rosters/slurp-tfrl-{tag}-fold-b-carriers-i{iteration}-v1.json",
        }
    raise ValueError(f"unknown kind {kind!r}")


# ---- the construction-source column (coordinator resolution of 2026-10-11 to decision 263-A) -------------------------------------
#: The proposer's tables and the ACE reflector's material come from ONE lock column flown on the CONSTRUCTION roster R01C (TRAIN rows
#: outside Fold A and Fold B), never from Fold B: Fold B is the held-out selection split, Fold A confirms. The column is flown once and
#: re-flown only if the lock changes; its counters-free tables serve iterations 1-3 alike. Package
#: ``docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/``.
CONST_SLUG = "tfrl-construction-lock-r01c"
CONST_PACKAGE_NAME = "slurp-tfrl-construction-source-v1"
CONST_PACKAGE_DIR = f"docs/readiness/{DATE}-{CONST_PACKAGE_NAME}"
CONST_PREREG_RELPATH = f"{CONST_PACKAGE_DIR}-preregistration.md"
CONST_ROWS = 625
CONST_DATASET = "slurp-speech-native-stage3-construction-r01c"
CONST_SPLIT_ID = "STAGE3-CONSTRUCTION-R01C"
CONST_ROSTER_ID = "SLURP-STAGE3-CONSTRUCTION-R01C"
CONST_ROSTER = {
    "arm": "docs/receipts/rosters/slurp-stage3-construction-r01c.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-roll-aa-r01c-smoke-4-v1.json",
}
#: The column flies the plain lock (no columns, no supply arms): Perception 1 + Solver 1 = 2 contacts per row. It composes on v2.2, whose
#: requests are byte-identical to v2.3's (proof P-ACE-0): the v2.3 ``ace-playbook`` store's source ids lie INSIDE R01C, so a cell flying
#: R01C rows cannot declare it (rails/runner.py refuses a query sample inside the composite knowledge source roster).
CONST_LOCK = PARENT_LOCK
CONST_CONTACTS = 2
CONST_PROGRAM = "phase-native-module-v1-c2"
CONST_SCORER = SCORER
CONST_ARM = DELIVERING
#: The ace-playbook release staging: the carrier rows of every release are the first ``ACE_CARRIERS`` sorted ids of the permitted roster of the
#: committed ``stage3-deltas-v1r`` registration (the i0 builder's own rule), never a Fold B row.
ACE_CARRIERS = 50
#: Measured throughput of the review-off composed arm at 2.00 contacts per row: 1.38 GPU-h per 1,000 rows
#: (docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md, efficiency table); 625 rows -> 0.86 GPU-h before FIT.
CONST_MEASURED_GPU_H_PER_1000_ROWS = 1.38
CONST_PLANNED_GPU_HOURS_ARM, CONST_PLANNED_GPU_HOURS_SMOKE = 1.0, 1.0
CONST_RUN_ID = f"SAEA-SLURP-STAGE3-{CONST_SLUG.upper()}-V1"
CONST_ATTEMPT_ID = f"attempt-slurp-native-stage3-{CONST_SLUG}-generation-v1"


def const_names(kind: str) -> dict:
    """Identities of the construction-source cell. ``kind``: ``arm`` | ``smoke``."""

    if kind not in ("arm", "smoke"):
        raise ValueError("kind must be 'arm' or 'smoke'")
    smoke = kind == "smoke"
    lo, up = ("-smoke-4" if smoke else ""), ("-SMOKE-4" if smoke else "")
    slug = CONST_SLUG
    return {
        "experiment": f"slurp-native-stage3-{slug}{lo}-v1",
        "baseline": f"slurp-native-stage3-{slug}{lo}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}{up}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}{up}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{slug}{lo}-generation-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{slug}{lo}-fit-v1",
        "prefix": "smoke-" if smoke else "",
        "campaign": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
        "read_run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-COLUMN-READ-V1",
        "recipe_id": f"slurp-{slug}-column-analysis-v1",
        "decision_id": f"slurp-{slug}-admission-v1",
        "decision_path": f"coordination/slurp-{slug}-v1/root-admission-v1.json",
    }


def fit_contact_cap(rows: int, contacts: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""

    return rows * contacts * FIT_ENDPOINTS_PER_CONTACT


def iteration_package_dir(iteration: int) -> str:
    return f"{PACKAGE_DIR}/iterations/i{iteration}"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(document: object) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(document: object) -> str:
    return sha256_bytes(canonical_json(document).encode("ascii"))


__all__ = [name for name in globals() if not name.startswith("_")]
