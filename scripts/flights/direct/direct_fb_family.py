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
#: The LIVE packets exposure row: the GPU encoder pass (2026-10-11 re-registration; the CPU sidecar pass was too slow and was stopped).
PACKETS_ROW_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1"
#: SUPERSEDED, kept in the record: the CPU sidecar run id (stopped by the owner after 50 of 1,076 Fold B rows; its recovery was spent).
CPU_PACKETS_ROW_ID = "SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1"
GPU_PACKETS_LEDGER_MARK = "## Cell 266-E packets re-registration: the Thinking speech packets on the GPU"
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
#: The LIVE Thinking packet root: encoder OUTPUT made by the GPU encoder. CPU- and GPU-made encoder outputs are not bit-identical, so the
#: GPU pass has its OWN root and never mixes with the 50 rows the CPU pass left in the superseded root below.
THINK_PACKET_ROOT = "/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6"
THINK_PROMOTION_RECEIPT = f"{THINK_PACKET_ROOT}/EVO-FOLD-B-V2-promotion.json"
CPU_THINK_PACKET_ROOT = "/home/chao/feat-cache/slurp-q4km-packets-thinking-afdaeff6"     # SUPERSEDED (CPU pass, stopped after 50 rows)
CPU_THINK_PROMOTION_RECEIPT = f"{CPU_THINK_PACKET_ROOT}/EVO-FOLD-B-V2-promotion.json"
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


#: The knowledge view every 266-E baseline pins. The direct-only program supplies no evidence (``evidence_source = none``), but the runner's
#: roster guard still compares the pinned snapshot's source roster with the query roster. The parent Fold A baseline pins the FULL-TRAIN view
#: (50,628 source rows, every Fold B id inside it), which made the Instruct arm abort before any model contact (2026-10-11T20:07:46Z). The
#: fold-excluded twin of the same view (37,407 source rows; 0 Fold A ids, 0 Fold B ids) is what every TRAIN-fold cell pins.
KNOWLEDGE_SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1/snapshot.json"
KNOWLEDGE_SNAPSHOT_SHA256 = "9c64e8ec48a0fce4f172bd190932f99c98c7efa18bbfb14526d54c62fdf7032b"
#: The full-TRAIN view the parent baseline pins; recorded so a test can prove no 266-E fragment carries it.
FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256 = "609854e4211891614b621e6431ccf23706c2aa3a3bc9133dae9d9765628c88b8"

# ---- the single recovery (rec1) of a cell ------------------------------------------------------------------------------------------
#: A (run_id, attempt_id) pair is a one-time key, so a cell whose attempt stopped is re-flown WHOLE under the ``-rec1`` attempt ids with a
#: recovery plan that carries the original plan plus the failed attempt's realised spend (the adapter budget is run-cumulative across the
#: attempts of a run id). Same mechanism as ``scripts/flights/tfrl/tfrl_family.SMOKE_RECOVERIES`` and ``nx_r6_family.SMOKE_RECOVERY``. The
#: package protocol fixes ONE root-diagnosed recovery re-registration per run id: a new generation attempt id AND a new live_phase_fit run
#: and attempt id; a second failure closes the cell. Keyed by cell key; every identity, plan, ledger row and queue step reads this table.
REC = "-rec1"
_INSTRUCT_ATTEMPT = "attempt-slurp-direct-only-fold-b-instruct-generation-v1"
RECOVERIES: dict[str, dict] = {
    "instruct": {
        "recovery_index": 1,
        "recovered_at": "2026-10-11",
        "predecessor_attempt_id": _INSTRUCT_ATTEMPT,
        "predecessor_fit_run_id": "SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-V1",
        "predecessor_fit_attempt_id": "attempt-slurp-direct-only-fold-b-instruct-fit-v1",
        "predecessor_state": (
            "ABORTED at 20:07:46Z at flight commit 77b2283e9 before any model contact, 0 calls / 0.0 speech-seconds; preserved unread "
            "(reserved 1080 calls / 3155 speech-seconds). The FIT attempt was never opened."
        ),
        "predecessors": [
            {"attempt_id": _INSTRUCT_ATTEMPT, "state": "ABORTED before any model contact", "contacts_spent": 0, "speech_seconds_spent": 0.0},
        ],
        "reason": (
            "The predecessor attempt aborted before any model contact: \"RailsRunnerError: AgentLoop query samples overlap the TRAIN knowledge "
            "source roster\" (raised by the runner's roster guard, rails/runner.py). The guard compares the query roster with the pinned "
            "knowledge snapshot's source roster even when the program supplies no evidence. The Instruct arm is re-flown whole under the rec1 ids; "
            "the replicate, the Thinking arm and the smoke are untouched (their attempts never opened) and only take the knowledge pin."
        ),
        "root_cause": (
            "the full-TRAIN knowledge view (609854e4...; 50,628 source rows, every Fold B id inside it) was pinned on a TRAIN-fold cell; "
            "corrected to the fold-excluded view of the same family (9c64e8ec...; 37,407 source rows, 0 Fold A and 0 Fold B ids)"
        ),
        "amendment": (
            "RECOVERY 2026-10-11 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across the "
            "attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's recorded spend "
            "(0 calls, 0 speech-seconds): the cumulative budget equals the original plan (1080 calls, 3155 speech-seconds). The FIT cap is "
            "structural and unchanged (1 + 3 x rows). The FIT run id and the FIT attempt id both take the rec1 marker because the cell is "
            "re-flown whole and a (run_id, attempt_id) pair is a one-time key; the generation run id is unchanged."
        ),
        "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
        "fit_cap_rule": "The FIT cap is structural: 1 + (2 + 1) x rows.",
    },
}


def recovery(key: str) -> dict | None:
    """The cell's recovery record, or ``None`` when the cell is on its first attempt."""

    return RECOVERIES.get(key)


def rec_suffix(key: str) -> str:
    return REC if key in RECOVERIES else ""


def predecessor_spend(key: str) -> tuple[int, float]:
    """(model calls, speech seconds) the failed attempts of the cell spent, as recorded."""

    rec = recovery(key)
    if not rec:
        return 0, 0.0
    return (sum(int(p["contacts_spent"]) for p in rec["predecessors"]),
            sum(float(p.get("speech_seconds_spent", 0.0)) for p in rec["predecessors"]))


def cumulative_budget(key: str, original_calls: int, original_audio: int) -> tuple[int, int]:
    """The run-cumulative plan budget: the original plan plus the failed attempts' realised spend (audio rounded up)."""

    calls, audio = predecessor_spend(key)
    return original_calls + calls, math.ceil(original_audio + audio - 1e-9)


def plan_file_name(key: str, plan_kind: str) -> str:
    """Package file name of a cell's registered plan; a recovered cell's plans carry the ``-rec1`` marker."""

    return f"{key}-{plan_kind}-plan-registered{rec_suffix(key)}-v1.json"


def superseded_plan_file_names(key: str) -> list[str]:
    """First-attempt plan names a recovery supersedes (removed from the package; the failed attempt stays on the data root)."""

    if not recovery(key):
        return []
    return [f"{key}-{kind}-plan-registered-v1.json" for kind in ("generation", "fit")]


def _spec(key, stem, role, core, rows, gpu, scoring, roster):
    upper = stem.upper()
    rec, rec_up = rec_suffix(key), rec_suffix(key).upper()
    return {
        "key": key, "role": role, "core": core, "rows": rows, "gpu_hours": gpu, "scoring_jobs": scoring, "roster": roster,
        "cell": f"slurp-direct-only-fold-b-{stem}-v1",
        "baseline": f"slurp-direct-only-fold-b-{stem}-baseline-v1",
        "run": f"SAEA-SLURP-DIRECT-ONLY-FOLD-B-{upper}-V1",
        "fit_run": f"SAEA-SLURP-DIRECT-ONLY-FOLD-B-{upper}-FIT{rec_up}-V1",
        "attempt": f"attempt-slurp-direct-only-fold-b-{stem}-generation{rec}-v1",
        "fit_attempt": f"attempt-slurp-direct-only-fold-b-{stem}-fit{rec}-v1",
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


def eligible_run_ids() -> list[str]:
    """The run ids the decision receipt makes eligible: the eight first-registration ids (the minted receipt lists exactly these, in this order),
    then each recovered cell's rec1 FIT run id."""

    out: list[str] = []
    for key in ALL_KEYS:
        rec = recovery(key)
        out += [CELLS[key]["run"], rec["predecessor_fit_run_id"] if rec else CELLS[key]["fit_run"]]
    out += [CELLS[key]["fit_run"] for key in ALL_KEYS if recovery(key)]
    return out


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
