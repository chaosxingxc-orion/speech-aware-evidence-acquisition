"""Shared identities of NX round R6-P1 (the Perception instruction-template column, TRAIN Fold B).

One module, imported by the derive, writer, mint, dry-run and read scripts and by the preflight test, so no id is spelled
twice. Model-free. Read constants as ``nf.NAME``.

WHAT R6-P1 IS. Owner decisions 245-248 (design of record
``docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md`` sections 2.2 and 4): the Perception node's own
entity-presence verdict and heard-mention list, measured node-locally in a same-flight Perception template column. Three
hand-written candidate templates (``configs/probes/nx/perception/r6/``, the pinned tag grammar beside them), the in-chain twin
``aa`` and the delivering locked template ``lock`` (last, untemplated), on the review-off COMP-1b module graph at lock v2.2
(v4g at delivery), roster TRAIN Fold B. It is a MEASUREMENT cell: the delivering arm is the lock (invariant I7), so the
delivered answer is unchanged; the delivered-metric effect is estimated offline from the cell's own sealed columns.

It is a clone of the R1 family (``nx_r1_family``) with node = perception: one iteration. The smoke carries the cell's single
root-diagnosed recovery re-registration (``SMOKE_RECOVERY``, rec1, 2026-10-10); the arm has none.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-10"
PARENT_SLUG = "psv4-fold-b"                       # the Fold B pins are copied from the P-SV-4 fragments
COMP1B_EXPERIMENT = "slurp-native-stage3-comp1b-fold-a-v1"

SLUG = "nx-r6-perception-fold-b"
ROUND_LABEL = "NX round R6-P1"
CELL_LABEL = "NX-R6-PERCEPTION"
SHORT = "nxr6"
BRANCH = "sonnet/nx-r6-engineering"
WORKTREE = "/home/chao/saea-worktrees/sonnet-nx-r6"
SOURCE_TREE = f"studies/speech-aware-evidence-acquisition, worktree {WORKTREE}, branch {BRANCH}"
LEDGER_MARK = "## NX round R6-P1: the Perception instruction-template column on TRAIN Fold B"

PKG_NAME = f"slurp-{SLUG}-v1"                     # coordination dir, package suffix, decision-id stem
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = f"SAEA-SLURP-STAGE3-{SLUG.upper()}-COLUMN-READ-V1"
RECIPE_ID = f"slurp-{SLUG}-column-analysis-v1"
CAMPAIGN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"

NODE = "perception"
ROWS = 1080
SMOKE_ROWS = 4
DELIVERING, TWIN = "lock", "aa"
ARMS = ("p1", "p2", "p3")
ARM_ORDER = (*ARMS, TWIN, DELIVERING)
#: Perception template group at level 2: each non-delivering arm adds one Perception AND one level-2 Solver contact
#: (``base + 2 (K - 1)``, ``rails.supply_variants.perception_branch_ceiling``): 2 + 2 x (5 - 1) = 10.
BASE_CONTACTS = 2
CEILING = BASE_CONTACTS + 2 * (len(ARM_ORDER) - 1)
PROGRAM = f"phase-native-module-v1-c{CEILING}"
FIT_ENDPOINTS_PER_CONTACT = 4                      # max_speech_packets (1) + 3, the gate's endpoints_per_contact
#: 10,800 contacts at the measured 44 requests per minute on np4 is about 4.1 GPU-h (design section 2.2).
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 4.1, 1.0
LOCK = "v2.2"                                      # v4g at delivery (module step 7), the R5 arm's base

LOCKED_TEMPLATE = "configs/probes/slurp_native_role_perception_v3.txt"
LOCKED_TEMPLATE_SHA = "767497809ccad58589f4f2537ffb29c3bb15120b4828dfa5edcb87abe63ac8a2"
CANDIDATES_DIR = "configs/probes/nx/perception/r6"
CANDIDATE_PATHS = {a: f"{CANDIDATES_DIR}/r6-{a}.txt" for a in ARMS}
TAG_GRAMMAR = f"{CANDIDATES_DIR}/TAG-GRAMMAR-v1.md"
CANDIDATES_README = "docs/readiness/2026-10-10-slurp-nx-r6-perception-candidates-v1/README.md"
DESIGN_NOTE = "docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md"
INSTRUMENT_README = "docs/readiness/2026-10-10-slurp-nx-perception-template-column-instrument-v1/README.md"
OFFLINE_NOTE = "docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md"
#: The E= values each arm's template allows (the reader's ``--tag-set``); the default is ``none,some``.
TAG_SETS = {"p1": ("none", "some"), "p2": ("none", "some"), "p3": ("none", "some", "unsure")}

#: The declared expectation (decision 192 form, measurement cell under decisions 245/247): the design's gate estimate, i.e. the
#: ``c3verdict`` rule with the Perception verdict swapped in, IF the Perception verdict matches the Solver-side c3 verdict's quality
#: (design section 2.2: +0.75 (i1) .. +0.98 (i2) pp). The cell claims NO benefit (it sits under the 1.49 pp same-flight floor and
#: under the 1.5 pp registration bar); it measures a node metric and an information gain.
EXPECTED_EFFECT_PP = 0.75
EXPECTED_EFFECT_RANGE_PP = (0.75, 0.98)

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
}
TUNING_ROSTER, READ_ROSTER = "SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2"
#: Disclosed, not hidden (R5 precedent): the candidates' mechanism hypotheses were authored from AGGREGATE tables of the R6 offline
#: note, which were computed on TRAIN Fold B (the R1 flights' columns), i.e. this cell's read roster; the gate threshold N1 >= 0.2 was
#: chosen there too. Fold B is the SELECTION roster of the design (section 2.3: Fold B selects, Fold A confirms); naming it in
#: ``tuning_roster`` would make the launch gate report a blocking ``tuning-read-overlap``, so the roster list keeps Fold A and this text
#: carries the exposure.
TUNING_DISCLOSURE = (
    "the three Perception templates' mechanism hypotheses and the N1 >= 0.2 gate of the delivered-metric estimate were derived from "
    "AGGREGATE tables of docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md, which were computed on TRAIN Fold B "
    "(the NX R1 flights' columns), this cell's read roster; no utterance text, gold value or note body was read to author them. Fold B is "
    "the selection roster of the design (docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.3: Fold B "
    "selects, Fold A confirms, DEV-2000-ADDED composes), so the read here is a selection read and every number is descriptive until the "
    "Fold A confirmation (R6-A) fixes the rule."
)
FLOOR_SLU_PP = 1.49
FLOOR_INTENT_PP = 0.65

#: Perception fit numbers MEASURED on the P-SV-4 AGREE arm's 1,080 Perception contacts (``psv_fit_measure.py``; the P-SV-4 fragment's
#: ``fit_estimate``): base prompt 2,577 tokens (excluding the template), 149 tokens per supplied item, completion ceiling 512. The
#: bound on supplied items is the P-SV-4 branch's (boundary block, 8 items observed, 10 registered).
FIT_ESTIMATE = {"slot_tokens": 24576, "completion_ceiling": 512, "base_prompt_tokens": 2577, "tokens_per_supplied_item": 149}
MAX_SUPPLIED_ITEMS = 10
PROMPT_LIMIT_TOKENS = 20990                        # 24,576 - 3,072 - 512 - 2 (the Solver-form arithmetic of the R1 fit measure)
#: ``template_tokens`` are an ESTIMATE from word counts (2.0 tokens per whitespace-separated word, conservative for JSON-heavy
#: instruction text), NOT a tokenizer pass: a tokenizer pass needs the frozen core's tokenizer (a server-side contact) and no contact
#: is made at registration. TODO (root, before the flip): replace with the registered tokenizer pass; the exact command is in the package
#: README ("Template tokens: ESTIMATE"). The preflight test is written against the estimate and must be adjusted with the measurement.
TOKENS_PER_WORD_ESTIMATE = 2.0

V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"
V4_RULES = ["fx-article", "fx-oclock", "scope", "ti1", "ee10"]
V4G_GUARDS = ["ee-wilson", "ti-expressible"]

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-train"


#: The smoke's single root-diagnosed recovery re-registration (2026-10-10). The first smoke attempt stopped after 20 of its 40 model
#: contacts (4 rows x 5 Perception arms) at ``SlurpIntentHypothesisError: hypothesis content does not match its source response
#: SHA-256`` in the first level-2 Solver input: the level-2 branch view swapped the Perception state's content for the branch's note
#: without rebinding ``source_response_sha256`` (the level-2 note source-hash binding fix, rails/runner.py; commit named at merge).
#: A (run_id, attempt_id) pair is a one-time key, so the smoke is re-flown WHOLE under the rec1 attempt ids (generation AND FIT);
#: the arm never started and keeps its attempt ids. The generation budget is RUN-CUMULATIVE across the attempts of a run id (the
#: model adapter), so the recovery plan carries the original plan plus the failed attempt's realised spend; the FIT cap is structural
#: and never scaled. The spend below was read from the failed attempt's own attempt record (``attempts/<run id>/<attempt id>.json``
#: ``actual``) and its trace COST records (20 records, audio_seconds summed): aggregates only, no per-row output was opened.
_SMOKE_RECOVERY = {
    "recovery_index": 1,
    "predecessor_attempt_id": "attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-generation-v1",
    "predecessor_fit_attempt_id": "attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-fit-v1",
    "predecessor_state": (
        "OPENED; 20 contacts / 50.908 speech-seconds spent (4 rows x 5 Perception arms); stopped 2026-10-10T08:11:08Z at flight "
        "commit 58c546b54 on SlurpIntentHypothesisError in the first level-2 Solver input; preserved unread"
    ),
    "predecessors": [
        {
            "attempt_id": "attempt-slurp-native-stage3-nx-r6-perception-fold-b-smoke-4-generation-v1",
            "state": "stopped after 20 contacts (SlurpIntentHypothesisError at the first level-2 Solver input)",
            "contacts_spent": 20,
            "speech_seconds_spent": 50.908,
        },
    ],
    "reason": (
        "The predecessor attempt made its 20 Perception contacts (4 rows x 5 arms) and stopped when the first level-2 Solver input "
        "was built: the level-2 branch view in rails/runner.py replaced the Perception state's content with the branch's note "
        "without rebinding source_response_sha256, so SlurpIntentHypothesisError ('hypothesis content does not match its source "
        "response SHA-256') fired. Root cause fixed by the level-2 note source-hash binding fix (rails/runner.py; commit named at "
        "merge). The smoke is re-flown whole under the rec1 attempt ids; the arm is untouched."
    ),
    "amendment": (
        "RECOVERY 2026-10-10 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across "
        "the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's "
        "realised spend: planned_model_calls 40 + 20 = 60 and planned_speech_audio_seconds ceil(102 + 50.908) = 153 (gpu hours "
        "unchanged, 1.0). The FIT cap is structural and unchanged: rows x max_contacts x (max_speech_packets + 3) = 4 x 10 x 4 = 160; "
        "the FIT attempt id also takes the rec1 suffix because a (run_id, attempt_id) pair is a one-time key and the failed FIT "
        "attempt was opened. The Perception arm, its attempt ids, its caps and its template pins are untouched."
    ),
    "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
    "fit_cap_rule": "The FIT cap is structural: rows x max_contacts x (max_speech_packets + 3).",
}
SMOKE_RECOVERY = _SMOKE_RECOVERY
SMOKE_REC = "-rec1"
SMOKE_PREDECESSOR_CONTACTS_SPENT = sum(p["contacts_spent"] for p in SMOKE_RECOVERY["predecessors"])
SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT = sum(p.get("speech_seconds_spent", 0.0) for p in SMOKE_RECOVERY["predecessors"])


def names(kind: str) -> dict:
    smoke = kind == "smoke"
    lo = "-smoke-4" if smoke else ""
    up = "-SMOKE-4" if smoke else ""
    rec = SMOKE_REC if smoke else ""                  # the smoke's single recovery (SMOKE_RECOVERY); the arm has none
    return {
        "experiment": f"slurp-native-stage3-{SLUG}{lo}-v1",
        "baseline": f"slurp-native-stage3-{SLUG}{lo}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-generation{rec}-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-fit{rec}-v1",
        "prefix": "smoke-" if smoke else "",
    }


def smoke_cumulative_budget(original_calls: int, original_audio: int) -> tuple[int, int]:
    """The run-cumulative smoke plan budget: the original plan plus the failed attempt's realised spend (audio rounded up)."""

    return (original_calls + SMOKE_PREDECESSOR_CONTACTS_SPENT,
            math.ceil(original_audio + SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT - 1e-9))


ARM, SMOKE = names("arm"), names("smoke")


def candidate_pins() -> dict[str, dict]:
    return {
        a: {"relpath": p, "sha256": hashlib.sha256((REPO_ROOT / p).read_bytes()).hexdigest()}
        for a, p in CANDIDATE_PATHS.items()
    }


def word_count(relpath: str) -> int:
    return len((REPO_ROOT / relpath).read_bytes().split())


def template_tokens_estimate(relpath: str) -> int:
    """ESTIMATE (word count x 2.0, rounded up). Not a tokenizer measurement."""

    return math.ceil(word_count(relpath) * TOKENS_PER_WORD_ESTIMATE)


def template_tokens() -> dict[str, int]:
    return {DELIVERING: template_tokens_estimate(LOCKED_TEMPLATE),
            **{a: template_tokens_estimate(p) for a, p in CANDIDATE_PATHS.items()}}


def template_frame() -> dict:
    return {
        "max_supplied_items": MAX_SUPPLIED_ITEMS,
        "delivering_template_tokens": template_tokens_estimate(LOCKED_TEMPLATE),
        "twin": True,
        "fit_estimate": dict(FIT_ESTIMATE),
    }


def arm_prompt_estimates() -> dict[str, int]:
    """base + template + max_supplied_items x tokens_per_supplied_item, per arm (the pre-flight fit rule)."""

    f = FIT_ESTIMATE
    return {k: f["base_prompt_tokens"] + v + MAX_SUPPLIED_ITEMS * f["tokens_per_supplied_item"]
            for k, v in template_tokens().items()}


def fit_measure() -> dict:
    """The fit numbers and the template-token ESTIMATES as the package records them (labelled)."""

    return {
        "schema": "saea-slurp-nx-r6-perception-fit-measure-v1",
        "status": "ESTIMATE: template_tokens are word-count estimates, not a tokenizer pass; fit numbers are P-SV-4's measured Perception numbers",
        "source": {
            "fit_estimate": "configs/baseline/slurp-native-stage3-psv4-fold-b-baseline-v1.json native_episode.roles.perception.branches.fit_estimate",
            "measured_on": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1 Perception contacts (scripts/flights/psv/psv_fit_measure.py)",
        },
        "template_tokens": template_tokens(),
        "template_tokens_method": f"ceil({TOKENS_PER_WORD_ESTIMATE} x whitespace-separated words) of the pinned file",
        "words": {DELIVERING: word_count(LOCKED_TEMPLATE), **{a: word_count(p) for a, p in CANDIDATE_PATHS.items()}},
        "template_frame": template_frame(),
        "arm_prompt_estimates": arm_prompt_estimates(),
        "prompt_limit_tokens": PROMPT_LIMIT_TOKENS,
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
    }


def fit_contact_cap(rows: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""

    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def fit_measure_json() -> str:
    return json.dumps(fit_measure(), indent=2, sort_keys=True) + "\n"
