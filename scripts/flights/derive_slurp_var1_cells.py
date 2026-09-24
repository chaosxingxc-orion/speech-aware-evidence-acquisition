#!/usr/bin/env python3
"""Idempotent generator for the VAR-1 construction-variant family (Stage-3,
owner directive 2026-09-24: training-free RL gains come from rolling out
VARIATIONS of prompts, data and content construction over an optimisation
space, scored per variant, never from running one algorithm mechanically).

MODEL-FREE. Profile ``model-free-check``. It writes, from already-sealed
precedents and never by hand:

* seven baseline fragments -- ``VAR1-PLAN`` (the locked v2.0 plan re-pointed
  at the R01C construction roster, exactly as cell ROLL-1 re-pointed it),
  ``VAR1-PLANR`` (its request-identical replicate = the roster's own null),
  the four construction variants ``VAR1-EX-K10`` / ``VAR1-EX-K30`` /
  ``VAR1-EX-DIV`` / ``VAR1-PER-K16C5``, and the four-row family smoke;
* seven experiment fragments (each carrying its generation cell and its fit
  cell) and six single-cell campaign plans (the smoke rides its arm's step);
* the readiness package's fourteen registered plan documents;
* the sixteen DRAFT exposure-ledger rows (14 flight + 2 model-free reads).

Every composed/protocol hash embedded in the package is computed live through
``core.config.compose`` / ``core.config.protocol_hash`` over the fragments
this script itself writes -- never hand-typed -- so a re-run after
``scripts/flights/repin_cell.py`` changes those fragments reproduces the same
values from the same bytes.

Idempotent: re-running with no intervening edits is a no-op. Refuses to
overwrite a config/readiness file whose on-disk content differs from what
this run would produce, and refuses to touch any exposure-ledger row already
marked ``consumed = yes``.

Writes nothing under ``$SPEECHRL_DATA_DIR``. No ``prepared_phase_supply`` key
is committed on any baseline: ``scripts/flights/repin_cell.py`` mints each
cell's own first-phase supply model-free at flip time (harness item E16), and
``--allow-output-change`` must never be passed.

Usage::

    python scripts/flights/derive_slurp_var1_cells.py
    python scripts/flights/derive_slurp_var1_cells.py --check   # write nothing
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash as compute_protocol_hash,
)

# ---------------------------------------------------------------------------
# Fixed identity.
# ---------------------------------------------------------------------------

DATASET_FRAGMENT = "slurp-speech-native-stage3-construction-r01c"
SPLIT_NAME = "STAGE3-CONSTRUCTION-R01C"
SPLIT_ROLE = "discovery"
SPLIT_IDENTITY_HASH = "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
ROSTER_RELPATH_REPO = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"
ROSTER_SHA256 = "e8abc65ba4626cccb4aae9d2eb1bd73f077a6e9a407b3dba9c18bbe4c03eeddd"
ROW_COUNT = 625
TOTAL_AUDIO_SECONDS = 2726.8471875
PER_ROW_CEILING = 11
AUDIO_CEIL = math.ceil(TOTAL_AUDIO_SECONDS * PER_ROW_CEILING)   # 29996
GEN_CAP = ROW_COUNT * PER_ROW_CEILING                            # 6875
FIT_CAP = GEN_CAP * 4                                            # 27500
EXPECTED_CONTACTS_PER_ROW = 4.1
EXPECTED_CONTACTS = math.ceil(ROW_COUNT * EXPECTED_CONTACTS_PER_ROW)  # 2563
GPU_HOURS_CAP = 8.0

SMOKE_IDS = (
    "slurp:train:000049:audio-1434542455",
    "slurp:train:000051:audio-1434531302-headset",
    "slurp:train:000234:audio-1499688528",
    "slurp:train:000260:audio-1488549919",
)
SMOKE_ROWS = 4
SMOKE_AUDIO_SECONDS = 17.0349375
SMOKE_AUDIO_CEIL = math.ceil(SMOKE_AUDIO_SECONDS * PER_ROW_CEILING)   # 188
SMOKE_GEN_CAP = SMOKE_ROWS * PER_ROW_CEILING                          # 44
SMOKE_FIT_CAP = SMOKE_GEN_CAP * 4                                     # 176
SMOKE_SPLIT_IDENTITY_HASH = (
    "e9dcea536028d17737b999c65267e47645ca7b3f6f9c4f57622961cf29363ed5"
)
SMOKE_GPU_HOURS_CAP = 1.0
NATIVE_TASK_CONTRACT_CALLS_CAP = 0

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
SERVICE_SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

LOCK_BASELINE = "slurp-native-default-plan-lock-baseline-v1"
ROLL_BASELINE = "slurp-native-stage3-rollout-baseline-v1"

DECISION_ID = "slurp-stage3-var1-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-var1-v1/root-admission-v1.json"

REGISTERED_AT_UTC = "2026-09-24T21:00:00.000000+00:00"
#: The commit that carries this registration. A commit cannot name its own
#: hash, so the sixteen DRAFT exposure rows were stamped by the follow-up
#: commit and this constant keeps the generator idempotent afterwards.
REGISTRATION_COMMIT = "1d2fc2e1"
REGISTRATION_DATE = "2026-09-24"
PACKAGE_NAME = "slurp-stage3-var1-v1"
READINESS_DIR = REPO_ROOT / "docs" / "readiness" / "2026-09-24-slurp-stage3-var1-v1"
PREREG_RELPATH = "docs/readiness/2026-09-24-slurp-stage3-var1-v1-preregistration.md"
LEDGER_PATH = REPO_ROOT / "docs" / "exposure-ledger.md"
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"
SOURCE_TREE = (
    "studies/speech-aware-evidence-acquisition, worktree "
    "/home/chao/saea-worktrees/fable-var1, branch fable/var1"
)

STAGE3_ALGORITHM = {
    "id": "shared-rollout",
    "note": (
        "Construction-variant rollout, VAR-1: the algorithm-neutral rollout substrate is "
        "flown once per CONSTRUCTION VARIANT on one roster, and the policy is learned "
        "OFFLINE by group-relative advantage over variants per runtime-observable state. "
        "No credit-assignment, update, selection or context_application operator runs "
        "inside any cell of this family -- each cell is one rollout of one fixed "
        "construction and its official score."
    ),
    "operators_used": ["rollout", "scoring"],
}

BOUNDED_PROJECTION_POLICY = (
    "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
)
CONFIGURABLE_PROJECTION_POLICY = (
    "configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
)

STORE_RELEASE_RELPATH = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/release.json"
)
STORE_RELEASE_SHA256 = "83620eb0b02f12424a00cd5572904f4df48a49c329b1b0e1a9321d4b9ec14fd0"
ENCODING_RECEIPT_RELPATH = (
    "preparation-runs/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1/"
    "encode-v1/receipt.json"
)
ENCODING_RECEIPT_SHA256 = "2117fa6d5fdb7563e4f609b66e2fc3971a340a7dd22d178fa3cfd5a7c111839a"

_VERIFY_BINDINGS = (
    ("vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl",
     "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8"),
    ("vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-content-v1.jsonl",
     "dd3b2924cda10810487b2b114e61380beaf8477634c602096b875e461ae44baa"),
    (STORE_RELEASE_RELPATH, STORE_RELEASE_SHA256),
    (ENCODING_RECEIPT_RELPATH, ENCODING_RECEIPT_SHA256),
)
PACKET_PROMOTION_RECEIPT = (
    "/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/STAGE3-CONSTRUCTION-R01-promotion.json"
)
PACKET_PROMOTION_SHA256 = "a1664e34742dcd2d59c226da701395edf41d150bbbf8db4acc0cdae9c3c0250f"

# ---------------------------------------------------------------------------
# The family.
# ---------------------------------------------------------------------------

#: ``short -> (label, run-id stem, cell-id stem)``. The run id is
#: ``SAEA-SLURP-STAGE3-<stem>-V1``; the config stem is
#: ``slurp-native-stage3-<cell stem>``.
FAMILY = (
    ("plan", "VAR1-PLAN", "VAR1-PLAN-R01C", "var1-plan-r01c"),
    ("planr", "VAR1-PLANR", "VAR1-PLANR-R01C", "var1-planr-r01c"),
    ("exk10", "VAR1-EX-K10", "VAR1-EX-K10-R01C", "var1-ex-k10-r01c"),
    ("exk30", "VAR1-EX-K30", "VAR1-EX-K30-R01C", "var1-ex-k30-r01c"),
    ("exdiv", "VAR1-EX-DIV", "VAR1-EX-DIV-R01C", "var1-ex-div-r01c"),
    ("perk16c5", "VAR1-PER-K16C5", "VAR1-PER-K16C5-R01C", "var1-per-k16c5-r01c"),
    ("smoke", "VAR1-SMOKE-4", "VAR1-SMOKE-4", "var1-smoke-4"),
)
VARIANT_SHORTS = ("exk10", "exk30", "exdiv", "perk16c5")
FLIGHT_SHORTS = ("plan", "planr") + VARIANT_SHORTS

#: The exact knob values each cell declares. ``exemplars`` is
#: ``knowledge_stores.train-exemplars.phase_supply.solver``; ``perception`` is
#: ``knowledge_stores.intent-boundaries.phase_supply.perception``;
#: ``candidates`` is BOTH ``phase_material.perception.fill_params
#: .max_candidates`` and ``knowledge_stores.slot-contracts.candidate_supply
#: .solver.max_candidates`` (they move together or the Solver is handed a
#: candidate list the Perception contract cannot produce).
KNOBS = {
    "plan":     {"ex_k": 20, "ex_c": 20, "ex_m": 20, "ex_l": 20,
                 "per_k": 8, "per_c": 1, "per_m": 8, "per_l": 8, "candidates": 3},
    "planr":    {"ex_k": 20, "ex_c": 20, "ex_m": 20, "ex_l": 20,
                 "per_k": 8, "per_c": 1, "per_m": 8, "per_l": 8, "candidates": 3},
    "exk10":    {"ex_k": 10, "ex_c": 10, "ex_m": 10, "ex_l": 10,
                 "per_k": 8, "per_c": 1, "per_m": 8, "per_l": 8, "candidates": 3},
    "exk30":    {"ex_k": 30, "ex_c": 30, "ex_m": 30, "ex_l": 30,
                 "per_k": 8, "per_c": 1, "per_m": 8, "per_l": 8, "candidates": 3},
    "exdiv":    {"ex_k": 20, "ex_c": 4, "ex_m": 20, "ex_l": 20,
                 "per_k": 8, "per_c": 1, "per_m": 8, "per_l": 8, "candidates": 3},
    "perk16c5": {"ex_k": 20, "ex_c": 20, "ex_m": 20, "ex_l": 20,
                 "per_k": 16, "per_c": 1, "per_m": 16, "per_l": 16, "candidates": 5},
    "smoke":    {"ex_k": 20, "ex_c": 20, "ex_m": 20, "ex_l": 20,
                 "per_k": 16, "per_c": 1, "per_m": 16, "per_l": 16, "candidates": 5},
}

SPEECH_FEATURE_ID = {
    "plan": "saea-slurp-task-agent-anchor-exemplars-k20-replicate-v1",
    "planr": "saea-slurp-task-agent-anchor-exemplars-k20-replicate-v1",
    "exk10": "saea-slurp-stage3-var1-exemplars-k10-v1",
    "exk30": "saea-slurp-stage3-var1-exemplars-k30-v1",
    "exdiv": "saea-slurp-stage3-var1-exemplars-k20-coverage4-v1",
    "perk16c5": "saea-slurp-task-agent-anchor-exemplars-k20-replicate-v1",
    "smoke": "saea-slurp-task-agent-anchor-exemplars-k20-replicate-smoke-v1",
}

WHAT_THIS_IS = {
    "plan": (
        "Cell VAR1-PLAN: the LOCKED v2.0 default plan "
        "(configs/baseline/slurp-native-default-plan-lock-baseline-v1.json), unchanged in "
        "every decided key, re-pointed at the SLURP-STAGE3-CONSTRUCTION-R01C roster -- its "
        "promoted speech packets, its two sealed speech query-vector files and its own "
        "preparation receipts -- exactly as cell B6 re-pointed PLAN at DEV-2000-ADDED and "
        "cell ROLL-1 re-pointed it at this very roster. One deviation is MANDATORY and is "
        "not a variant: the train-exemplars store is the size-pool-annotated-exemplars"
        "-MINUS-R01 release, because R01's own utterances are in the parent exemplar pool "
        "and a construction roster may never retrieve itself (coordinator decision 102). "
        "This cell is the COMPARATOR every VAR-1 variant is paired against; it is flown, "
        "not imported, because no plan-form arm has ever been sealed on R01C -- ROLL-1 "
        "flew the five-sample grouped Solver policy, not this one."
    ),
    "planr": (
        "Cell VAR1-PLANR: the REQUEST-IDENTICAL second pass of VAR1-PLAN on the same 625 "
        "R01C rows. It differs from VAR1-PLAN only by its run, attempt and native-contact"
        "-fit identities; every rendered byte of every request is the same. It is the "
        "roster's OWN NULL: the A/A cross-flight pair whose CI95 half-widths h_SLU and "
        "h_intent are the margins every VAR-1 variant is read at. It flies SECOND and its "
        "margin table is sealed BEFORE any variant contrast is read. Precedent: cell PLANr "
        "on TRAIN Fold A and cell PLANr-DEV2000 on DEV-2000-ADDED."
    ),
    "exk10": (
        "Cell VAR1-EX-K10: VAR1-PLAN with ONE construction knob moved -- the Solver's "
        "speech-keyed TRAIN exemplar supply drops from twenty demonstrations to ten "
        "(knowledge_stores.train-exemplars.phase_supply.solver.k 20 -> 10 with "
        "fuse_coverage c/m/top_l 10/10/10, ten in and ten out on every row under "
        "saea-fuse-supplyfilter-v1). Nothing else moves: same store release, same ranking, "
        "same query vectors, same node graph, same instruction bytes. It asks whether the "
        "locked k=20 is past the point where another demonstration pays for its tokens."
    ),
    "exk30": (
        "Cell VAR1-EX-K30: VAR1-PLAN with the same single knob moved the other way -- "
        "thirty demonstrations instead of twenty (k 20 -> 30, fuse_coverage 30/30/30). "
        "Nothing else moves. It asks whether the in-context learning curve is still rising "
        "at twenty. The registered fit expectation is COMPACT_REQUIRED at worst and never "
        "REFUSE: an exemplar value's rendered content averages 70 characters (p95 117, max "
        "200) in this released store, so ten more of them are hundreds of characters, not "
        "thousands, against a 24,576-token slot."
    ),
    "exdiv": (
        "Cell VAR1-EX-DIV: VAR1-PLAN with the exemplar COVERAGE reshaped rather than its "
        "depth -- k stays 20 and the top-m window stays 20, but fuse_coverage.c drops from "
        "20 to 4, so saea-fuse-supplyfilter-v1 admits at most FOUR exemplars per task "
        "target (an SLURP intent id) out of the twenty speech neighbours it recalled. On a "
        "row whose neighbourhood is intent-concentrated the supply shrinks and diversifies; "
        "on a row whose neighbourhood already spans five or more intents it is unchanged. "
        "It is the 'no coverage reshaping' discipline of cell KU-S3 deliberately relaxed, "
        "once, as a measured variant."
    ),
    "perk16c5": (
        "Cell VAR1-PER-K16C5: the INTENT-COVERAGE lever -- the only VAR-1 variant whose "
        "contract SHAPE changes. The Perception node's intent-card supply doubles "
        "(knowledge_stores.intent-boundaries.phase_supply.perception.k 8 -> 16 with "
        "fuse_coverage 1/16/16 under saea-fuse-associated-values-v1: sixteen cards, one per "
        "admitted facet), and the candidate bound rises from three to five at BOTH sites "
        "that must agree -- phase_material.perception.fill_params.max_candidates and "
        "knowledge_stores.slot-contracts.candidate_supply.solver.max_candidates. The "
        "slot-contracts caps max_total_values 28 and max_values_per_candidate 16 are NOT "
        "moved, so the Solver's candidate block does not grow; the same 28-value budget is "
        "spread round-robin over five candidates instead of three. ONE REQUIRED COMPANION, "
        "declared and not hidden: a candidate bound above three is legal only under the "
        "registered configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses"
        "-v1 projection (rails.candidate_semantic_supply refuses the literal-3 bounded "
        "policy above three). The projection itself does not change -- first occurrence in "
        "the model's own order, distinct on intent_id -- only its declared input bound. "
        "Target bad class: 'intent by candidate coverage' (own card supplied -> 96.5 % "
        "covered, absent -> 17.3 %; handoff section 6)."
    ),
    "smoke": (
        "The four-row FORM SMOKE of the VAR-1 family. It flies the VAR1-PER-K16C5 form -- "
        "the only variant whose contract shape changes (five candidates instead of three, "
        "sixteen intent cards instead of eight) -- on the first four rows of R01C in the "
        "roster's own order. The three exemplar variants change a retrieval budget and no "
        "contract byte, so they raise no structural question a four-row flight would "
        "answer, and VAR1-PLAN / VAR1-PLANR are the locked plan's own sealed form. "
        "Structural only: no official score is run and no effectiveness claim is read."
    ),
}


class DeriveError(RuntimeError):
    pass


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical(document: object) -> str:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bindings() -> None:
    """Re-hash every pinned binding against the bytes on disk instead of
    trusting a hand-typed constant."""

    roster_path = REPO_ROOT / ROSTER_RELPATH_REPO
    if _sha256_file(roster_path) != ROSTER_SHA256:
        raise DeriveError(f"{ROSTER_RELPATH_REPO} does not hash to the pinned {ROSTER_SHA256}")
    dataset = _read_json(REPO_ROOT / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json")
    if int(dataset["count"]) != ROW_COUNT:
        raise DeriveError("dataset fragment row count is not 625")
    if float(dataset["audio_seconds_total"]) != TOTAL_AUDIO_SECONDS:
        raise DeriveError("dataset fragment audio_seconds_total moved")
    if dataset["split_identity_hash"] != SPLIT_IDENTITY_HASH:
        raise DeriveError("dataset fragment split identity moved")
    ids = [item["sample_id"] for item in dataset["items"][:SMOKE_ROWS]]
    if tuple(ids) != SMOKE_IDS:
        raise DeriveError("the first four R01C rows are not the registered smoke population")
    raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
    if not raw or not Path(raw).is_dir():
        print("SPEECHRL_DATA_DIR not reachable; skipping data-root verification", file=sys.stderr)
        return
    root = Path(raw)
    for relpath, expected in _VERIFY_BINDINGS:
        path = root / relpath
        if not path.is_file():
            raise DeriveError(f"binding file missing on the data root: {relpath}")
        measured = _sha256_file(path)
        if measured != expected:
            raise DeriveError(f"{relpath} hashes to {measured}, not the pinned {expected}")
    promotion = Path(PACKET_PROMOTION_RECEIPT)
    if promotion.is_file() and _sha256_file(promotion) != PACKET_PROMOTION_SHA256:
        raise DeriveError("the R01 packet promotion receipt does not hash to the pinned value")


def _write_if_needed(path: Path, content: str, *, check: bool) -> str:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            return "unchanged"
        if check:
            return "WOULD-CHANGE"
        path.write_text(content, encoding="utf-8", newline="\n")
        return "rewritten"
    if check:
        return "WOULD-CREATE"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    return "written"


# ---------------------------------------------------------------------------
# Names.
# ---------------------------------------------------------------------------


def run_id(short: str) -> str:
    return "SAEA-SLURP-STAGE3-" + dict((s, r) for s, _l, r, _c in FAMILY)[short] + "-V1"


def fit_run_id(short: str) -> str:
    return "SAEA-SLURP-STAGE3-" + dict((s, r) for s, _l, r, _c in FAMILY)[short] + "-FIT-V1"


def cell_stem(short: str) -> str:
    return "slurp-native-stage3-" + dict((s, c) for s, _l, _r, c in FAMILY)[short]


def baseline_name(short: str) -> str:
    return f"{cell_stem(short)}-baseline-v1"


def experiment_name(short: str) -> str:
    return f"{cell_stem(short)}-v1"


def cell_id(short: str) -> str:
    return f"{cell_stem(short)}-v1"


def fit_cell_id(short: str) -> str:
    return f"{cell_stem(short)}-fit-v1"


def gen_attempt(short: str) -> str:
    return f"attempt-{cell_stem(short)}-v1-generation"


def fit_attempt(short: str) -> str:
    return f"attempt-{cell_stem(short)}-v1-fit"


def label(short: str) -> str:
    return dict((s, l) for s, l, _r, _c in FAMILY)[short]


def is_smoke(short: str) -> bool:
    return short == "smoke"


def rows_of(short: str) -> int:
    return SMOKE_ROWS if is_smoke(short) else ROW_COUNT


def split_hash_of(short: str) -> str:
    return SMOKE_SPLIT_IDENTITY_HASH if is_smoke(short) else SPLIT_IDENTITY_HASH


def gen_cap_of(short: str) -> int:
    return SMOKE_GEN_CAP if is_smoke(short) else GEN_CAP


def fit_cap_of(short: str) -> int:
    return SMOKE_FIT_CAP if is_smoke(short) else FIT_CAP


def audio_cap_of(short: str) -> int:
    return SMOKE_AUDIO_CEIL if is_smoke(short) else AUDIO_CEIL


def gpu_hours_of(short: str) -> float:
    return SMOKE_GPU_HOURS_CAP if is_smoke(short) else GPU_HOURS_CAP


# ---------------------------------------------------------------------------
# Baseline fragments.
# ---------------------------------------------------------------------------

EXEMPLAR_STORE_NOTE = (
    "SLURP v2 base program module M1 / cell B1: the top-k TRAIN construction-pool "
    "exemplars recalled by cosine against this row's OWN sealed R01C speech vector in the "
    "content retrieval dimension, ranked by saea-rank-wcos-prior-agree-v1 (identity on "
    "cosine: w_cos=1, w_prior=0, w_agree=0) and passed through saea-fuse-supplyfilter-v1. "
    "The store is the size-pool-annotated-exemplars-MINUS-R01 release: the parent pool "
    "contains R01's own utterances, and a construction roster that retrieved itself would "
    "read its own answer (coordinator decision 102; "
    "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-minus-r01.json). Each "
    "value renders as '<utterance> | <scenario>_<action> | type=filler; ...'. The decision "
    "is delivered to the SOLVER phase through the E6 acquire transition as typed content "
    "blocks, composed with the slot-contracts candidate supply on the same wave."
)


def build_baseline(short: str, lock: dict, roll: dict) -> dict:
    knobs = KNOBS[short]
    document = copy.deepcopy(lock)
    document.pop("prepared_phase_supply", None)

    # 1. The R01C re-pointing, key for key, from the sealed ROLL-1 fragment.
    document["knowledge_stores"] = copy.deepcopy(roll["knowledge_stores"])
    document["preparation_source_receipts"] = copy.deepcopy(roll["preparation_source_receipts"])
    document["speech_packet_promotion_receipt"] = roll["speech_packet_promotion_receipt"]
    document["speech_packet_promotion_receipt_sha256"] = (
        roll["speech_packet_promotion_receipt_sha256"]
    )
    # 2. The locked plan's own policy and episode (ROLL-1 flew the five-sample
    #    grouped Solver; VAR-1 flies the LOCKED single-sample plan).
    document["policy"] = lock["policy"]
    document["native_episode"] = copy.deepcopy(lock["native_episode"])
    document["scorers"] = list(lock["scorers"])

    # 3. The knobs.
    exemplars = document["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    exemplars["k"] = knobs["ex_k"]
    exemplars["fuse_coverage"] = {
        "c": knobs["ex_c"], "m": knobs["ex_m"], "top_l": knobs["ex_l"],
    }
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    perception["k"] = knobs["per_k"]
    perception["fuse_coverage"] = {
        "c": knobs["per_c"], "m": knobs["per_m"], "top_l": knobs["per_l"],
    }
    document["phase_material"]["perception"]["fill_params"]["max_candidates"] = (
        knobs["candidates"]
    )
    candidate_supply = (
        document["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    )
    candidate_supply["max_candidates"] = knobs["candidates"]
    # A candidate bound above three is only legal under the CONFIGURABLE bounded
    # first-occurrence projection (rails.candidate_semantic_supply: "projection_policy
    # requires bounded first-occurrence and compact source"). The projection itself is
    # unchanged -- first occurrence in the model's own order, distinct on intent_id --
    # and only its declared input bound moves from a literal 3 to the configured
    # max_candidates within the legal intent inventory. It is a REQUIRED COMPANION of
    # the candidate knob, not a second factor, and it is declared as such.
    candidate_supply["projection_policy"] = (
        CONFIGURABLE_PROJECTION_POLICY
        if knobs["candidates"] > 3
        else BOUNDED_PROJECTION_POLICY
    )

    # 4. Identity.
    document["native_contact_fit"] = {
        "attempt_id": fit_attempt(short),
        "contact_cap": fit_cap_of(short),
        "max_speech_packets": 1,
        "run_id": fit_run_id(short),
    }
    document["speech_feature_matcher_policy_id"] = SPEECH_FEATURE_ID[short]
    document["speech_feature_key_representation_id"] = (
        SPEECH_FEATURE_ID[short] + ":query-speech"
    )
    document["what_this_is"] = WHAT_THIS_IS[short]
    document["what_the_train_exemplars_store_is"] = EXEMPLAR_STORE_NOTE
    if is_smoke(short):
        document["smoke_note"] = (
            "Four-row form smoke of the VAR-1 family on the VAR1-PER-K16C5 form, over the "
            "first four rows of SLURP-STAGE3-CONSTRUCTION-R01C in the roster's own order "
            f"(split identity {SMOKE_SPLIT_IDENTITY_HASH}): "
            + ", ".join(SMOKE_IDS)
            + ". A pure positional selection with zero contacts and no label, score or gold "
            "input of any kind. Strata datetime / takeaway / alarm / audio, three far-field "
            "and one headset, 17.034938 s of audio. Structural evidence only."
        )
    return document


# ---------------------------------------------------------------------------
# Experiment fragments.
# ---------------------------------------------------------------------------

FAILURE_POLICY = (
    "Stop and preserve on the first failure. No automatic restart, replay, row filtering, "
    "roster, role-graph, prompt, knowledge, geometry or cap change. AT MOST ONE "
    "root-diagnosed recovery re-registration for this run, which needs BOTH a new "
    "generation attempt id AND a new native_contact_fit.attempt_id (the CELL-1 lesson: the "
    "fit gate binds the baseline's fit identity and refuses one that already carries "
    "evidence); a second failure closes this flight and the fix is proven on a four-row dry "
    "run before another mechanism is admitted. RESUME-RECOVERY CLAUSE (owner decision 22 of "
    "2026-09-18): if the abort is an INFRASTRUCTURE failure with code and request bytes "
    "unchanged, the one recovery takes the resume-recovery form of harness item E10 -- the "
    "same run id, a fresh attempt id, a resume_from declaration naming the predecessor "
    "attempt and its trace SHA-256, every COMPLETE row kept without selection under "
    "invariant I7r, every partial or unstarted row re-flown in full, no change to the "
    "question, roster, comparator, decision rule or caps, and the run-cumulative budget "
    "re-checked; otherwise the one recovery is a full re-fly. A partial manifest is never "
    "scored and never read. One experiment is in flight at a time: a failure in any VAR-1 "
    "cell stops the whole family's chain, and the remaining variants do not open."
)

PURPOSE_HEAD = (
    "Stage-3 VAR-1, the FIRST construction-variant rollout of the locked v2.0 plan (owner "
    "directive 2026-09-24: training-free RL gains come from rolling out VARIATIONS of "
    "prompts, data and content construction over an optimisation space, scored per variant, "
    "with the winners encoded into demonstrations, constraints and selection rules; handoff "
    "docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md sections 6-7, routes "
    "F3 and F4). Six cells on the 625-row SLURP-STAGE3-CONSTRUCTION-R01C construction "
    "roster: the locked plan re-pointed at R01C (VAR1-PLAN, the comparator), its "
    "request-identical replicate (VAR1-PLANR, the roster's own null), and four single-knob "
    "construction variants of its knowledge supply. "
)

PURPOSE_TAIL = (
    "READ DISCIPLINE: the output of this family is DESCRIPTIVE -- a per-row paired variant "
    "table at the roster's own null, a per-scenario table, entity FP/FN by slot type, "
    "Perception coverage, and the group-relative advantage of each variant per "
    "runtime-observable state. NO admission verdict, no lock, no store release and no claim "
    "is taken from it. R01C is a CONSTRUCTION roster (split role discovery): variants are "
    "chosen here on construction rows, and any winner must be re-read on TRAIN Fold A and on "
    "DEV-2000-ADDED, each at that roster's own null, before it becomes a claim of any kind. "
    "Owner decisions 28 and 86: TRAIN and DEV numbers are development numbers; the one test "
    "read (decision 29 / 108) is not authorised here and is deferred until a fresh-roster "
    "gain exists."
)

MODULE_NOTE = {
    "plan": "the locked v2.0 plan itself, re-pointed at R01C; no knob moves",
    "planr": "the locked v2.0 plan itself, re-pointed at R01C; a request-identical replicate",
    "exk10": "one knob: the Solver's exemplar depth k 20 -> 10 with coverage 10/10/10",
    "exk30": "one knob: the Solver's exemplar depth k 20 -> 30 with coverage 30/30/30",
    "exdiv": "one knob: the Solver's exemplar coverage c 20 -> 4 at fixed k 20",
    "perk16c5": (
        "one lever at three agreeing sites: Perception intent cards k 8 -> 16 with coverage "
        "1/16/16, and the candidate bound 3 -> 5 at the Perception fill contract and the "
        "slot-contracts candidate supply"
    ),
    "smoke": "the VAR1-PER-K16C5 form on four rows; structural only",
}


def readiness_requirements() -> list[dict]:
    return [
        {
            "kind": "preparation",
            "reason": (
                "The released train-exemplars store this family retrieves from: "
                "size-pool-annotated-exemplars-MINUS-R01, the parent pool with every R01 "
                "construction utterance removed (coordinator decision 102). Nothing new is "
                "released by this family; the requirement states what the fragment binds. "
                "The cell stays HELD on a root admission decision."
            ),
            "relpath": STORE_RELEASE_RELPATH,
            "sha256": STORE_RELEASE_SHA256,
        },
        {
            "kind": "preparation",
            "reason": (
                "The R01 speech-query encoding receipt both R01C query_source pins descend "
                "from (SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1, sealed "
                "and already consumed by cell ROLL-1). The R01C files are pure id SELECTIONS "
                "of that sealed parent: every kept line is the parent's own line bytes. "
                "Nothing new is encoded for this family. The cell stays HELD on a root "
                "admission decision."
            ),
            "relpath": ENCODING_RECEIPT_RELPATH,
            "sha256": ENCODING_RECEIPT_SHA256,
        },
    ]


def build_experiment(short: str) -> dict:
    rows = rows_of(short)
    purpose = (
        PURPOSE_HEAD
        + f"THIS FRAGMENT IS CELL {label(short)}: {MODULE_NOTE[short]}. "
        + WHAT_THIS_IS[short]
        + " "
        + PURPOSE_TAIL
    )
    generation_definition = (
        f"{gen_cap_of(short):,} = {rows:,} R01C rows x {PER_ROW_CEILING}, the locked plan's "
        "OWN per-row contact ceiling (configs/policy/"
        "phase-native-candidates-review-revise-v1.json max_contacts 11, resolved from the "
        "unchanged role graph perception 1 / solver 1 / reviewer 3 / planner 1 with "
        "max_revisions 1 as 1 + 2 x (3 + 1 + 1)). It is the exact program maximum, not a "
        "safety bound. Cell PLAN measured 4.0963 contacts per row on TRAIN Fold A and cell "
        "B6's plan arm 4.071 on DEV-2000-ADDED, so about "
        f"{EXPECTED_CONTACTS_PER_ROW} per row is the ESTIMATE and never a target. No VAR-1 "
        "variant adds a contact: every knob changes how much text an already-scheduled "
        "request carries, never how many requests are made."
    )
    cells = [
        {
            "allowed_execution_stages": ["check", "worker", "campaign"],
            "attempt_id": gen_attempt(short),
            "baseline_fragment": baseline_name(short),
            "cell_id": cell_id(short),
            "dataset_fragment": DATASET_FRAGMENT,
            "model_fragment": MODEL_FRAGMENT,
            "readiness": {
                "reason": (
                    f"Stage-3 VAR-1 cell {label(short)}: {MODULE_NOTE[short]}. HELD: root "
                    "mints the admission receipt "
                    f"{DECISION_RELPATH} (decision id {DECISION_ID}), rewrites its "
                    "eligible_run_ids to this family's FOURTEEN run ids and its budget caps "
                    "to this family's, and re-pins this cell with "
                    "scripts/flights/repin_cell.py --set-ready, which mints this cell's OWN "
                    "first-phase supply artifact under its own run id (harness item E16) and "
                    "inserts the matching preparation requirement. The committed baseline "
                    "carries NO prepared_phase_supply key, which is the cell-P0 form; "
                    "--allow-output-change must never be passed."
                ),
                "requirements": readiness_requirements(),
                "state": "held",
            },
            "run_id": run_id(short),
        },
        {
            "allowed_execution_stages": ["check", "worker", "campaign"],
            "attempt_id": fit_attempt(short),
            "baseline_fragment": baseline_name(short),
            "cell_id": fit_cell_id(short),
            "dataset_fragment": DATASET_FRAGMENT,
            "model_fragment": MODEL_FRAGMENT,
            "readiness": {
                "reason": (
                    f"The tokenizer-capacity fit pass for cell {label(short)} (same "
                    "population, same stores, same knobs). A SPEND identity: it is never "
                    "flown as a generation cell and stays held."
                ),
                "requirements": readiness_requirements(),
                "state": "held",
            },
            "run_id": fit_run_id(short),
        },
    ]
    document = {
        "cells": cells,
        "date": REGISTRATION_DATE,
        "execution_plan": {
            "execution_profile": "bounded-discovery-probe",
            "planned_gpu_hours": gpu_hours_of(short),
            "planned_model_calls": gen_cap_of(short),
            "planned_speech_audio_seconds": audio_cap_of(short),
            "split_role": SPLIT_ROLE,
        },
        "execution_profile": "bounded-discovery-probe",
        "experiment_id": run_id(short),
        "failure_policy": FAILURE_POLICY,
        "family_budget": {
            "asr_calls": 0,
            "ceilings_are_not_targets": True,
            "encoder_calls": 0,
            "fit_endpoint_calls_cap": fit_cap_of(short),
            "generation_calls_cap": gen_cap_of(short),
            "gpu_hours_fit_inclusive": gpu_hours_of(short),
            "native_task_contract_calls_cap": NATIVE_TASK_CONTRACT_CALLS_CAP,
            "official_complete_scoring_jobs": 0 if is_smoke(short) else 1,
            "repeated_speech_audio_seconds_cap": audio_cap_of(short),
        },
        "fragment_kind": f"saea-{cell_stem(short)}-v1",
        "generation_budget": {
            "cap": gen_cap_of(short),
            "definition": generation_definition,
            "target": 17 if is_smoke(short) else EXPECTED_CONTACTS,
        },
        "population": {
            "count": rows,
            "dataset_fragment": DATASET_FRAGMENT,
            "decision_population": population_note(short),
            "split_identity_hash": split_hash_of(short),
        },
        "preserve_wire_responses": True,
        "purpose": purpose,
        "service_session": SERVICE_SESSION,
        "split_id": SPLIT_NAME,
        "stage3_algorithm": copy.deepcopy(STAGE3_ALGORITHM),
    }
    # A SLURP TRAIN runtime view refuses to build without an EXPLICIT registered
    # population (rails.adapters.slurp_runtime._assert_sample_namespaces): a
    # construction roster never reaches the core as "whatever the dataset fragment
    # happens to list". Cell ROLL-1 carries the same block on this roster.
    ids = list(SMOKE_IDS) if is_smoke(short) else roster_ids()
    document["populations"] = [{"dataset_fragment": DATASET_FRAGMENT, "ids": ids}]
    return document


def roster_ids() -> list[str]:
    dataset = _read_json(REPO_ROOT / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json")
    return [str(item["sample_id"]) for item in dataset["items"]]


def population_note(short: str) -> str:
    if is_smoke(short):
        return (
            "The FIRST FOUR rows of SLURP-STAGE3-CONSTRUCTION-R01C in the roster's own order "
            "(positions 1-4 of docs/receipts/rosters/slurp-stage3-construction-r01c.json): "
            + ", ".join(SMOKE_IDS)
            + ". Strata datetime, takeaway, alarm and audio; three far-field recordings and "
            "one headset; 17.034938 s of audio. A pure positional selection with zero "
            "contacts -- no gold, no score, no label and no separate draw entered it. "
            "Structural evidence only; no quality read is taken from this fragment."
        )
    return (
        "SLURP-STAGE3-CONSTRUCTION-R01C (docs/receipts/rosters/"
        "slurp-stage3-construction-r01c.json, roster id SLURP-STAGE3-CONSTRUCTION-R01C, 625 "
        "TRAIN recordings, 18 scenario strata of 26-42, roster role construction, split role "
        "discovery). It is the clean subset of the 800-row R01 farthest-point draw: R01 minus "
        "every recording whose utterance is a source of any composed knowledge store "
        "(intent-boundaries-v1, slot-contracts-v2, size-pool-annotated-exemplars-minus-r01), "
        "175 removed, order preserved (coordinator decision 102). Its own receipt proves zero "
        "shared recordings and zero shared utterances with TRAIN Fold A, TRAIN Fold B, "
        "DEV-1000 and DEV-2000-ADDED. The roster receipt carries a per-item stratum, so a "
        "GOLD per-scenario table IS derivable here offline, unlike on DEV-2000-ADDED. This "
        "roster has been flown exactly once, by cell ROLL-1 (the five-sample grouped Solver "
        "rollout) plus the ADV-1 and GEPA proposer arms on subsets of it; no plan-form arm "
        "has ever been sealed on it, which is why VAR1-PLAN is flown rather than imported. "
        "TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000-ADDED and the test split stay "
        "untouched and unread by this family."
    )


def build_campaign(short: str) -> dict:
    return {
        "cells": [{"cell": cell_id(short), "experiment": experiment_name(short)}],
        "schema": "saea-campaign-plan-v1",
    }


# ---------------------------------------------------------------------------
# Hashes.
# ---------------------------------------------------------------------------


def composed_hashes(short: str) -> dict:
    """``{cell: (composed_config_hash, protocol_hash)}`` for the generation
    and fit cells of one experiment, computed live."""

    experiment = _read_json(EXPERIMENT_DIR / f"{experiment_name(short)}.json")
    out = {}
    for cell in experiment["cells"]:
        composed = compose(
            REPO_ROOT,
            model=cell["model_fragment"],
            dataset=cell["dataset_fragment"],
            baseline=cell["baseline_fragment"],
            experiment=experiment_name(short),
        )
        arm = str(composed.values["arm"])
        out[cell["cell_id"]] = (
            composed.config_hash,
            compute_protocol_hash(composed.config_hash, arm, split_hash_of(short)),
        )
    return out


# ---------------------------------------------------------------------------
# The readiness package.
# ---------------------------------------------------------------------------

DRY_RUN_RECEIPT = Path("/home/chao/var1-dry-run.json")

KNOB_TABLE = {
    "plan": {
        "exemplars_k": 20, "exemplars_fuse_coverage": {"c": 20, "m": 20, "top_l": 20},
        "perception_k": 8, "perception_fuse_coverage": {"c": 1, "m": 8, "top_l": 8},
        "perception_fill_max_candidates": 3, "slot_contracts_max_candidates": 3,
        "projection_policy": BOUNDED_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [],
    },
    "planr": {
        "exemplars_k": 20, "exemplars_fuse_coverage": {"c": 20, "m": 20, "top_l": 20},
        "perception_k": 8, "perception_fuse_coverage": {"c": 1, "m": 8, "top_l": 8},
        "perception_fill_max_candidates": 3, "slot_contracts_max_candidates": 3,
        "projection_policy": BOUNDED_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [],
    },
    "exk10": {
        "exemplars_k": 10, "exemplars_fuse_coverage": {"c": 10, "m": 10, "top_l": 10},
        "perception_k": 8, "perception_fuse_coverage": {"c": 1, "m": 8, "top_l": 8},
        "perception_fill_max_candidates": 3, "slot_contracts_max_candidates": 3,
        "projection_policy": BOUNDED_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [
            "knowledge_stores.train-exemplars.phase_supply.solver.k: 20 -> 10",
            "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage: "
            "{c:20,m:20,top_l:20} -> {c:10,m:10,top_l:10}",
        ],
    },
    "exk30": {
        "exemplars_k": 30, "exemplars_fuse_coverage": {"c": 30, "m": 30, "top_l": 30},
        "perception_k": 8, "perception_fuse_coverage": {"c": 1, "m": 8, "top_l": 8},
        "perception_fill_max_candidates": 3, "slot_contracts_max_candidates": 3,
        "projection_policy": BOUNDED_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [
            "knowledge_stores.train-exemplars.phase_supply.solver.k: 20 -> 30",
            "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage: "
            "{c:20,m:20,top_l:20} -> {c:30,m:30,top_l:30}",
        ],
    },
    "exdiv": {
        "exemplars_k": 20, "exemplars_fuse_coverage": {"c": 4, "m": 20, "top_l": 20},
        "perception_k": 8, "perception_fuse_coverage": {"c": 1, "m": 8, "top_l": 8},
        "perception_fill_max_candidates": 3, "slot_contracts_max_candidates": 3,
        "projection_policy": BOUNDED_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [
            "knowledge_stores.train-exemplars.phase_supply.solver.fuse_coverage.c: 20 -> 4 "
            "(k and the top-m window and top_l are unchanged at 20)",
        ],
    },
    "perk16c5": {
        "exemplars_k": 20, "exemplars_fuse_coverage": {"c": 20, "m": 20, "top_l": 20},
        "perception_k": 16, "perception_fuse_coverage": {"c": 1, "m": 16, "top_l": 16},
        "perception_fill_max_candidates": 5, "slot_contracts_max_candidates": 5,
        "projection_policy": CONFIGURABLE_PROJECTION_POLICY,
        "moved_against_the_locked_plan": [
            "knowledge_stores.intent-boundaries.phase_supply.perception.k: 8 -> 16",
            "knowledge_stores.intent-boundaries.phase_supply.perception.fuse_coverage: "
            "{c:1,m:8,top_l:8} -> {c:1,m:16,top_l:16}",
            "phase_material.perception.fill_params.max_candidates: 3 -> 5",
            "knowledge_stores.slot-contracts.candidate_supply.solver.max_candidates: 3 -> 5",
            "knowledge_stores.slot-contracts.candidate_supply.solver.projection_policy: "
            f"{BOUNDED_PROJECTION_POLICY} -> {CONFIGURABLE_PROJECTION_POLICY} "
            "(REQUIRED COMPANION: rails.candidate_semantic_supply refuses a candidate bound "
            "above three under the literal-3 bounded policy; the projection itself -- first "
            "occurrence in the model's own order, distinct on intent_id -- does not change)",
        ],
    },
    "smoke": {
        "exemplars_k": 20, "exemplars_fuse_coverage": {"c": 20, "m": 20, "top_l": 20},
        "perception_k": 16, "perception_fuse_coverage": {"c": 1, "m": 16, "top_l": 16},
        "perception_fill_max_candidates": 5, "slot_contracts_max_candidates": 5,
        "projection_policy": CONFIGURABLE_PROJECTION_POLICY,
        "moved_against_the_locked_plan": ["the VAR1-PER-K16C5 form on four rows"],
    },
}

FUSE_SEMANTICS = {
    "saea-fuse-supplyfilter-v1 (train-exemplars, Solver)": (
        "m is the top-m ranked-facet window the percept threshold tau is applied inside; the "
        "admitted values are grouped by their task_target (for this store an SLURP intent id, "
        "59 distinct over 8,554 values); top_l bounds how many TARGETS are served; c bounds "
        "how many values per served target. At k=m=c=top_l=20 the route is twenty in and "
        "twenty out, because each exemplar value associates with exactly one content facet. "
        "Dropping c to 4 therefore caps the supply at four demonstrations PER INTENT and "
        "shrinks the block on intent-concentrated neighbourhoods -- that is precisely what "
        "VAR1-EX-DIV measures, and the realised per-row counts are a deliverable, not an "
        "assumption."
    ),
    "saea-fuse-associated-values-v1 (intent-boundaries, Perception)": (
        "the first m ranked facets are admitted by the cosine threshold; they are traversed in "
        "rank order taking at most c NEW values per facet, and the traversal stops at top_l "
        "values overall. The released intent-boundaries store has 60 facets and 60 values, one "
        "per intent, so c=1 with m=top_l=k gives exactly k intent cards. k 8 -> 16 therefore "
        "doubles the Perception node's card block; the store's cards average 702 characters "
        "(max 895), so this is the single largest text change in the family and the reason "
        "VAR1-PER-K16C5 is the one form that carries a smoke."
    ),
}


def cells_block(hashes: dict) -> dict:
    block = {}
    for short in FLIGHT_SHORTS + ("smoke",):
        cid = cell_id(short)
        composed, proto = hashes[cid]
        entry = {
            "cell": cid,
            "run_id": run_id(short),
            "attempt_id": gen_attempt(short),
            "baseline_fragment": f"configs/baseline/{baseline_name(short)}.json",
            "experiment_fragment": f"configs/experiment/{experiment_name(short)}.json",
            "experiment": experiment_name(short),
            "composed_config_hash": composed,
            "protocol_hash": proto,
            "rows": rows_of(short),
            "split_identity_hash": split_hash_of(short),
            "knobs": KNOB_TABLE[short],
            "readiness": (
                "held -- the coordinator mints "
                f"{DECISION_RELPATH} (decision id {DECISION_ID}), rewrites its "
                "eligible_run_ids to this family's fourteen run ids, and re-pins this cell "
                "with scripts/flights/repin_cell.py --set-ready"
            ),
            "order_constraint": ORDER_CONSTRAINT[short],
        }
        if not is_smoke(short):
            entry["campaign_plan"] = f"configs/campaign/{experiment_name(short)}.json"
        block[short] = entry
    return block


ORDER_CONSTRAINT = {
    "plan": (
        "FLIES FIRST. Every variant is paired against this cell's sealed outputs, so nothing "
        "else in the family can be read until it has sealed and been scored once."
    ),
    "planr": (
        "FLIES SECOND, before any variant. Its contrast against VAR1-PLAN is the roster's own "
        "null, and the margins h_SLU / h_intent are sealed BEFORE any variant contrast is "
        "read and are never adjusted afterwards."
    ),
    "exk10": "flies third; one experiment in flight at a time",
    "exk30": "flies fourth; one experiment in flight at a time",
    "exdiv": "flies fifth; one experiment in flight at a time",
    "perk16c5": (
        "flies sixth and LAST, and only after its own four-row smoke has sealed: it is the "
        "only VAR-1 form whose contract shape changes"
    ),
    "smoke": (
        "flies immediately before the VAR1-PER-K16C5 arm, inside the same batch-driver step; "
        "the arm does not open until it has sealed"
    ),
}


def fit_only_block(hashes: dict) -> dict:
    block = {}
    for short in FLIGHT_SHORTS + ("smoke",):
        cid = fit_cell_id(short)
        composed, proto = hashes[cid]
        block[short] = {
            "cell": cid,
            "run_id": fit_run_id(short),
            "attempt_id": fit_attempt(short),
            "experiment": experiment_name(short),
            "composed_config_hash": composed,
            "protocol_hash": proto,
            "note": (
                "A SPEND identity, never flown as a generation cell and never flipped to "
                "ready. core.preparation_fit.build_native_contact_fit_gate fits each realised "
                "native request inside the same flight under the same lease; coordinate-fit "
                "must NOT be run, or these rows are double-charged."
            ),
        }
    return block


DECISION_RULE = {
    "STATUS_IS_DESCRIPTIVE": (
        "THIS FAMILY RETURNS NO ADMISSION VERDICT. It is a construction-variant ROLLOUT on a "
        "construction roster: its output is a table, not a decision. No ADMITTED / NEUTRAL / "
        "HARMFUL label is attached to any VAR-1 cell, no module is admitted, no store is "
        "released, nothing is locked and the v2.0 lock is untouched. The paired read driver "
        "writes status DESCRIPTIVE and the coordinator does not convert it."
    ),
    "PER_VARIANT_READING": (
        "For each variant v: delta(v) = v minus VAR1-PLAN on the same 625 rows, paired by row, "
        "in percentage points, for the official pooled SLU micro F1 (primary) and the intent "
        "(joint scenario+action) accuracy (guard). Each delta is reported with its CI90 and "
        "CI95 from the row-cluster bootstrap, beside h_SLU and h_intent from the own null. A "
        "variant is called SEPARATED FROM THE NULL when its CI95 excludes zero AND its point "
        "estimate is outside +-h on that metric; anything else is INSIDE THE NULL. That is a "
        "reading of a construction rollout, NOT an admission: the words ADMITTED and HARMFUL "
        "are not used of a VAR-1 cell."
    ),
    "OWN_NULL_FIRST": (
        "THE ORDER IS PART OF THE REGISTRATION. h_SLU and h_intent are the CI95 half-widths "
        "VAR1-PLAN against VAR1-PLANR produces on THIS roster, with the same estimator, "
        "clustering, seed and draws as every variant contrast. The own-null read "
        "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 is completed and its margin table SEALED before "
        "any variant contrast stage is read, and the margins are never adjusted after a "
        "variant's numbers are seen. The TRAIN Fold A margins (h_SLU 1.2485 / h_intent 0.9943) "
        "and the DEV-2000-ADDED margins (1.2525 / 1.1520) are CONTEXT ONLY: a margin is a "
        "property of a roster, never of a mechanism, and R01C is a different roster of a "
        "different size."
    ),
    "GROUP_RELATIVE_ADVANTAGE": (
        "PRIMARY DELIVERABLE. For every runtime-observable state key -- predicted scenario "
        "(the majority scenario of the row's own Perception candidates), candidate count, "
        "channel (headset / far-field) and audio-duration band -- the per-row scores of the "
        "K variants plus VAR1-PLAN are grouped, and each variant's advantage is its score "
        "minus the group mean over the variants ON THAT ROW. That is the group-relative "
        "advantage a training-free RL policy would be learned from, and computing it is the "
        "whole point of flying the variants paired on one roster. It is reported with its "
        "per-state sample size and is never read as an effect at a state with fewer than "
        "twenty rows."
    ),
    "PER_STRATUM": (
        "Owner decision 17: a per-scenario table in BOTH weightings, natural mixture and "
        "equal-stratum. R01C's roster receipt carries a per-item stratum (18 scenarios, 26-42 "
        "rows each), so unlike DEV-2000-ADDED a GOLD per-scenario table IS derivable here "
        "offline, from the roster receipt alone and with no gold at runtime. It is reported "
        "for every variant."
    ),
    "DENSE_PROXIES": (
        "Reported per variant beside the pooled score, because a 625-row pooled SLU delta is "
        "at the measurement floor and a dense proxy is not: entity FALSE POSITIVES and FALSE "
        "NEGATIVES by slot TYPE, the empty-gold-row emission rate, intent exactness, and -- "
        "from the sealed Perception receipts, model-free -- the coverage rate (gold intent "
        "present in the row's own candidate list). Coverage is the quantity VAR1-PER-K16C5 "
        "exists to move and is read directly, not inferred from the pooled score."
    ),
    "REPLICATION_AND_TRANSFER": (
        "NOTHING SELECTED HERE IS A RESULT. A variant that separates from the null on R01C is "
        "a CANDIDATE, and the next step is a re-read of that one variant on TRAIN Fold A "
        "against the sealed PLAN comparator at Fold A's own null, and then on DEV-2000-ADDED "
        "at its own null -- the CELL-3 lesson, where a store selected on Fold A did not "
        "transfer to a fresh roster. Selecting on construction rows and claiming on them is "
        "the error this family is designed not to repeat."
    ),
    "FRONTIER": (
        "Owner decision 75: the frontier row (official SLU-F1 delta x prefilled tokens per row "
        "x GPU hours per 625 rows) is reported for every variant beside the registered rows. "
        "The denominator is 625 here, not 1,080 or 1,000: a frontier row from another roster "
        "is rescaled or labelled, never silently placed beside."
    ),
    "EFFICIENCY_REGARDLESS": (
        "Every efficiency deliverable is reported whatever the table says. VAR1-EX-K10 in "
        "particular is expected to cost FEWER prefilled tokens per row than VAR1-PLAN, and a "
        "variant that holds the score at a lower token cost is a finding in its own right."
    ),
    "comparator": (
        "cell VAR1-PLAN (SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1), flown in this same family. It "
        "is FLOWN rather than imported because no plan-form arm has ever been sealed on R01C: "
        "cell ROLL-1 flew the five-sample grouped-Solver policy "
        "(phase-native-candidates-review-revise-samples5-v1), not the locked single-sample "
        "plan, and greedy decoding is not bit-reproducible across batch compositions, so a "
        "comparator from another roster would import a margin this family cannot measure."
    ),
}


def build_protocol(hashes: dict, dry_run: dict | None) -> dict:
    return {
        "schema": "saea-slurp-stage3-var1-protocol-v1",
        "protocol_id": "slurp-stage3-var1-protocol-v1",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "registered_at_utc": REGISTERED_AT_UTC,
        "source_tree": SOURCE_TREE,
        "authority": (
            "Owner directive of 2026-09-24 (training-free RL gains come from rolling out "
            "VARIATIONS of prompts, data and content construction over an optimisation space, "
            "scored per variant, with the winners encoded into demonstrations, constraints and "
            "selection rules -- never from running a simple algorithm mechanically and "
            "declaring a conclusion), recorded in "
            "docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md sections 5-7 as "
            "routes F3 (exemplar-construction variants) and F4 (Perception coverage). Owner "
            "decisions 17, 25, 28, 29, 58, 75, 79, 86, 99, 101, 102, 107, 108, 111, 112, 113 "
            "and 114. Owner decision 111 closed the semantic-delta APPLICATION line; this "
            "family opens no cell on that line."
        ),
        "family_kind": (
            "CONSTRUCTION-VARIANT ROLLOUT: one comparator, its request-identical replicate and "
            "four single-knob variants of the SAME locked plan, flown on ONE construction "
            "roster and read paired by row. Every knob is an existing config key of the locked "
            "plan. No new module, no new store, no new provider, no new policy id, no new "
            "rails file and no code change of any kind."
        ),
        "registered_facts": f"docs/readiness/{READINESS_DIR.name}/registered-facts-v1.json",
        "analysis_recipe": f"docs/readiness/{READINESS_DIR.name}/analysis-recipe-v1.json",
        "verdict_document": "docs/results/<date>-slurp-stage3-var1-construction-variant-read.md",
        "cells": cells_block(hashes),
        "fit_only_cells": fit_only_block(hashes),
        "fuse_semantics": FUSE_SEMANTICS,
        "decision_rule": DECISION_RULE,
        "comparator": {
            "cell": "VAR1-PLAN",
            "run_id": run_id("plan"),
            "flown_not_imported": (
                "No plan-form arm has ever been sealed on R01C. Cell ROLL-1 flew the "
                "five-sample grouped-Solver policy on this roster; the locked plan's own form "
                "has been sealed on TRAIN Fold A (official 63.63 / 82.22) and on "
                "DEV-2000-ADDED (65.40 / 76.60) and on neither of those is it comparable to a "
                "625-row TRAIN construction subset. Those two numbers are CONTEXT and are "
                "never used as this family's comparator."
            ),
            "never_reflown": (
                "once VAR1-PLAN has sealed it is never re-flown; every variant is paired "
                "against those sealed bytes"
            ),
        },
        "metrics": {
            "primary": (
                "official pooled SLU micro F1 (slurp-slu-official-train, the TRAIN gold "
                "sibling both baselines declare, through the pinned SLURP official "
                "evaluate.py), natural mixture"
            ),
            "guard": "intent (joint scenario+action) accuracy",
            "delta_convention": (
                "delta = variant minus VAR1-PLAN, in percentage points; negative is worse"
            ),
            "secondaries": [
                "scenario accuracy",
                "action accuracy",
                "pooled span F1",
                "per-row mean SLU F1",
                "per-row mean exact slot F1",
            ],
            "dense_proxies": [
                "entity false positives and false negatives by slot TYPE",
                "emission rate on empty-gold rows",
                "Perception coverage: gold intent present in the row's own candidate list",
                "candidate count per row and candidate-list distinctness",
            ],
            "train_siblings_available": (
                "slurp-slu-official-projected-v3-train and the TRAIN-symmetric sibling ARE "
                "defined on TRAIN gold and may be reported beside the official number on this "
                "roster, unlike on DEV-2000-ADDED. Whether they are run is the read's choice; "
                "the official number is the one the table is keyed on."
            ),
        },
        "scoring": {
            "official_scorer": (
                "pinned SLURP official evaluate.py through core.scoring_batch, TRAIN gold "
                "(slurp-slu-official-train)"
            ),
            "scorers": ["slurp-slu-official-train", "cost"],
            "complete_jobs_per_cell": 1,
            "complete_jobs_family": len(FLIGHT_SHORTS),
            "include_per_sample": True,
            "no_sharding": True,
            "scheduled_by": (
                "each cell's own campaign finalize step, once, over that cell's complete "
                "manifest; the four-row smoke runs no scorer"
            ),
        },
        "service": {
            "expected_session_id": SERVICE_SESSION,
            "slots": 4,
            "slot_tokens": 24576,
            "total_context": 98304,
            "decoder_only": True,
            "mmproj": "absent",
            "no_child_start_stop": True,
            "note": (
                "attach only, never spawn or stop. The geometry is the locked plan's and is "
                "NOT a variant: a geometry change would break the request identity of "
                "VAR1-PLANR against VAR1-PLAN and with it the family's own null."
            ),
        },
        "resampling": {
            "primary": (
                "paired row-cluster bootstrap over the roster's utterance ids. R01C carries "
                "625 DISTINCT utterance ids, so the cluster is the row and this is the paired "
                "per-row bootstrap; the cluster key is declared anyway so the estimator is the "
                "same function every other SLURP read uses."
            ),
            "cluster_key": "utterance_id",
            "distinct_clusters": ROW_COUNT,
            "speaker_clustering": (
                "NOT DERIVABLE: the R01C roster receipt carries no per-item speaker field. "
                "Stated in the verdict rather than worked around."
            ),
            "seed": 20260915,
            "draws": 10000,
            "intervals": ["CI95 for the reading clauses", "CI90 for diagnostics"],
            "interval_form": "percentile pairs of the same retained replicate sequence",
            "pairing_note": (
                "both sides of every contrast are decoded runs, so the paired interval carries "
                "real decoding noise; the roster's own null is the calibration for exactly "
                "that, which is why VAR1-PLANR flies before any variant."
            ),
            "tables": ["natural mixture", "equal-stratum weighting over the gold scenario"],
        },
        "fit": {
            "mode": "native_contact_fit",
            "contact_cap": FIT_CAP,
            "smoke_contact_cap": SMOKE_FIT_CAP,
            "arithmetic": (
                f"{ROW_COUNT} rows x {PER_ROW_CEILING} native contacts x (1 speech packet + 3 "
                f"endpoints) = {FIT_CAP}; the four-row smoke is 4 x {PER_ROW_CEILING} x 4 = "
                f"{SMOKE_FIT_CAP}"
            ),
            "coordinate_fit": "must NOT be run, or the FIT rows are double-charged",
        },
        "accounting": accounting_block(),
        "population": population_block(),
        "prompt_fit": prompt_fit_block(dry_run),
        "contact_free_evidence": contact_free_evidence_block(dry_run),
        "prepared_phase_supply": {
            "status": "NOT PINNED HERE, and deliberately not written by hand",
            "allow_output_change": "--allow-output-change must never be passed",
            "note": (
                "Harness item E16: a prepared artifact is evidence only for the implementation "
                "that produced it, so each of the seven flown cells prepares its OWN "
                "first-phase Perception supply under its OWN run id at the readiness flip. "
                "core.flight.repin.ensure_artifact_pinned runs core.flight.cli prepare-supply "
                "(model-free, zero model / tokenizer / encoder / scorer / server contacts), "
                "writes the pin into the baseline fragment and inserts the matching "
                "preparation readiness requirement. The committed baselines therefore carry NO "
                "prepared_phase_supply key at all -- the cell-P0 form. A PENDING_ string in "
                "its place is NOT a valid registration: core.flight.repin.ArtifactPin"
                ".from_mapping refuses it before the preparation step can run."
            ),
            "expected_identity": (
                "VAR1-PLANR's prepared first-phase supply MUST equal VAR1-PLAN's byte for "
                "byte: they differ only in run, attempt and fit identity, and the first-phase "
                "supply is the Perception selection over the same rows with the same store, "
                "the same k and the same coverage. A different value means the replicate is "
                "not a replicate -- stop and report. VAR1-EX-K10 / K30 / DIV must ALSO equal "
                "VAR1-PLAN's, because those three knobs live on the SOLVER route and the "
                "prepared artifact seeds PERCEPTION only. VAR1-PER-K16C5 and the smoke are the "
                "only cells whose prepared supply legitimately differs, because they are the "
                "only cells that move a Perception knob."
            ),
        },
        "smoke_acceptance": smoke_acceptance_block(dry_run),
        "diagnostics_required": DIAGNOSTICS_REQUIRED,
        "boundary": {
            "splits_untouched": (
                "TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000-ADDED and the test split stay "
                "untouched and unread by every cell of this family."
            ),
            "no_gold_at_runtime": (
                "no gold label, reference transcript, delivered answer or future turn enters "
                "runtime. Every knob is a retrieval budget or a candidate bound read from the "
                "row's own speech vector and its own sealed Perception state."
            ),
            "construction_roster_guard": (
                "R01C is the CLEAN subset: R01 minus every recording whose utterance is a "
                "source of any composed knowledge store, 175 removed (coordinator decision "
                "102). The exemplar store this family retrieves from is the MINUS-R01 release, "
                "so no row can retrieve its own utterance. The roster receipt's own "
                "knowledge_source_guard asserts the empty intersection the runner recomputes "
                "before it dispatches a row."
            ),
            "no_new_speech_identity": (
                "R01C's packets were promoted for cell ROLL-1 and its two query-vector files "
                "are sealed id SELECTIONS of the sealed R01 parents. This family promotes no "
                "packet, encodes nothing and opens no new speech identity."
            ),
            "split_role": (
                "discovery. R01C is a CONSTRUCTION roster: it exists to be optimised on. That "
                "is exactly why nothing selected on it is a result until it is re-read out of "
                "fold."
            ),
        },
        "failure_policy": FAILURE_POLICY,
        "one_experiment_in_flight": (
            "The owner's iteration rule: one experiment in flight. The six cells fly one at a "
            "time through the batch driver, in the registered order; a failure in any one "
            "stops the chain and the remaining variants do not open. At most one recovery "
            "re-registration per flight; a second failure stops the flight and the fix is "
            "proven on a four-row dry run."
        ),
        "quality_gate": (
            "no task-quality read of any cell before its complete sealed manifest, its exact "
            f"ordered {ROW_COUNT} outputs, its native phase summary and its single successful "
            "complete official TRAIN score all exist. THE OWN NULL IS READ FIRST: no variant's "
            "contrast stage is read until SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 has sealed its "
            "margin table. The efficiency reads may proceed from the sealed receipts, trace "
            "and server log as soon as a manifest seals, because they touch no answer, "
            "reference or quality field."
        ),
        "resume_recovery_clause": (
            "owner decision 22 of 2026-09-18. If an attempt dies of an INFRASTRUCTURE failure "
            "with code and request bytes unchanged, the one allowed recovery takes the "
            "resume-recovery form of harness item E10: the same run id, a fresh attempt id AND "
            "a fresh native_contact_fit.attempt_id, a resume_from declaration naming the "
            "predecessor attempt and its trace SHA-256, every COMPLETE row kept without "
            "selection under invariant I7r, every partial or unstarted row re-flown in full, "
            "no change to the question, roster, comparator, decision rule or caps, and the "
            "run-cumulative budget re-checked."
        ),
        "efficiency_measurement_method": {
            "sources": [
                "runs/<run>/<attempt>/<run>.trace.jsonl",
                "flight-receipts.json",
                "the generation manifest's cost block",
                "the serving monitor's monitor.jsonl",
            ],
            "derived": {
                "prompt_length": "n_tokens at slot release minus generated tokens",
                "prefilled": "the 'prompt eval time' token count -- what the GPU evaluated",
                "cached": "prompt length minus prefilled",
            },
            "join": (
                "server.log records are aligned to client contacts PER SLOT; the config pins "
                "decoding_params.id_slot = 'per-sample'"
            ),
            "read_only": (
                "the resident session's log and monitor are read read-only; the session is "
                "attached, never spawned, stopped or queried for control"
            ),
        },
        "harness_admission_entry_form": {
            "carrier": "slurp",
            "module": (
                "NONE. A construction-variant rollout admits no module. An admission entry is "
                "written only if a variant is later re-read out of fold, on TRAIN Fold A and "
                "DEV-2000-ADDED, under that roster's own admission rule -- and that is a "
                "different registration with its own cells."
            ),
            "written_by": "not written by this family",
        },
        "native_tool_calls_cap": 0,
        "not_authorized": [
            "no readiness flip -- all fourteen flight cells stay held until the coordinator "
            "mints the root decision receipt and runs scripts/flights/repin_cell.py --set-ready",
            "no model, tokenizer, encoder, scorer, server, GPU or network contact of any kind "
            "by this registration",
            "no core.flight.cli check (it needs the coordinator's clean-tree cycle against the "
            "minted receipt)",
            "no prompt-fit bound is claimed as measured",
            "no test read, no TRAIN Fold A read, no TRAIN Fold B read, no DEV-1000 read, no "
            "DEV-2000-ADDED read",
            "no paper-scale work, no manuscript, no publication claim",
            "no change to the locked v2.0 plan fragment, and no re-fly of any sealed cell",
            "no adjustment of h_SLU or h_intent after any variant contrast is read",
            "no new knob after the first variant's numbers are seen -- a VAR-2 family is a new "
            "registration",
        ],
        "not_claimed": [
            "NO ADMISSION. No VAR-1 cell is ADMITTED, NEUTRAL or HARMFUL; the family returns a "
            "table.",
            "NO TEST CLAIM. Owner decisions 28 / 86 / 29 / 108: TRAIN and DEV numbers are "
            "development numbers, and the one test read is deferred until a fresh-roster gain "
            "exists.",
            "NO SUPERIORITY, GENERALISATION OR CROSS-CARRIER CLAIM.",
            "NO CLAIM THAT A WINNER HERE IS A WINNER ANYWHERE. R01C is a construction roster; "
            "CELL-3 is the standing evidence that selection on one roster need not transfer.",
        ],
        "primary_deliverables": [
            "the per-row PAIRED VARIANT TABLE: every variant against VAR1-PLAN on the same 625 "
            "rows, official pooled SLU-F1 and intent, with CI90/CI95 and the own-null "
            "half-widths printed beside them",
            "the margin table VAR1-PLANR produces, read and sealed BEFORE any variant contrast",
            "the GOLD per-scenario table per variant, in both weightings (derivable on R01C "
            "from the roster receipt's per-item stratum)",
            "entity FALSE POSITIVES and FALSE NEGATIVES by slot TYPE per variant",
            "PERCEPTION COVERAGE per variant from the sealed Perception receipts: gold intent "
            "present in the row's own candidate list, with candidate counts",
            "the GROUP-RELATIVE ADVANTAGE of each variant per runtime-observable state "
            "(predicted scenario, candidate count, channel), with per-state sample sizes",
            "the frontier row per 625 rows for every variant (owner decision 75)",
        ],
        "open_items": OPEN_ITEMS,
        "the_venue": {
            "roster": "SLURP-STAGE3-CONSTRUCTION-R01C, 625 TRAIN recordings, split role discovery",
            "what_that_buys": (
                "a clean, knowledge-disjoint construction roster with GOLD per-scenario labels, "
                "already packeted and already vectorised, on which six paired arms cost about "
                f"{round(6 * ROW_COUNT * EXPECTED_CONTACTS_PER_ROW / 1000.0, 1)}k contacts and "
                "roughly six GPU-hours in total -- the cheapest venue in the program for a "
                "K-way construction sweep"
            ),
            "what_that_does_not_buy": (
                "any claim at all. R01C is the roster the Stage-3 store line was BUILT on; a "
                "variant that wins here has won on construction rows and nowhere else."
            ),
        },
    }


DIAGNOSTICS_REQUIRED = [
    "THE VARIANT TABLE, the item this family exists for: for each of the four variants and "
    "for VAR1-PLANR, the paired delta against VAR1-PLAN on official pooled SLU-F1 and intent, "
    "with CI90, CI95, saves / harms / ties and the exact McNemar sign-test p, beside h_SLU and "
    "h_intent from the own null.",
    "GROUP-RELATIVE ADVANTAGE PER RUNTIME-OBSERVABLE STATE: for each state key (predicted "
    "majority candidate scenario, candidate count, channel, audio-duration band), each "
    "variant's per-row score minus the per-row mean over the variants, aggregated, with the "
    "per-state n. Never read as an effect below n = 20.",
    "GOLD PER-SCENARIO TABLES per variant, in both the natural mixture and the equal-stratum "
    "weighting, over the 18 R01C strata (26-42 rows each) from the roster receipt's per-item "
    "stratum. This is available here and was NOT available on DEV-2000-ADDED.",
    "ENTITY FP / FN BY SLOT TYPE per variant, with the empty-gold-row emission rate: the "
    "bad-case classes the exemplar knobs are aimed at (entity FN about 31.5 %, date omission "
    "dominant; entity FP about 28.8 %, 184 of 414 empty-gold rows emitting).",
    "PERCEPTION COVERAGE per variant from the sealed Perception receipts, model-free: the rate "
    "at which the gold intent appears in the row's own projected candidate list, the candidate "
    "count distribution, and the distinctness of the candidate ids. This is the quantity "
    "VAR1-PER-K16C5 exists to move; reading it from the pooled score instead would be reading "
    "a 2 pp lever through a 1.3 pp floor.",
    "SUPPLY REALISATION per variant: the realised number of exemplar values supplied per row "
    "(the EX knobs) and of intent cards seeded per row (the PER knob), from the flight's own "
    "phase-supply receipts, beside the offline dry-run projection. VAR1-EX-DIV in particular "
    "has a DATA-DEPENDENT supply size -- c = 4 per intent target caps a concentrated "
    "neighbourhood and leaves a diverse one untouched -- and the realised distribution is a "
    "finding.",
    "PER-CHANNEL table (67 headset, 558 far-field) from the roster's own headset field, "
    "descriptive and unclustered.",
    "COST per variant: contacts, contacts per row, prefilled and cached tokens per row, GPU "
    "hours per 625 rows, and the frontier row. VAR1-EX-K10 is expected to be cheaper than "
    "VAR1-PLAN and VAR1-EX-K30 / VAR1-PER-K16C5 dearer; the exchange rate between tokens and "
    "score is part of what a construction rollout measures.",
    "E20 COMPACTION per phase and per variant: rows compacted, at which phase and by how much. "
    "Zero is expected on VAR1-PLAN / PLANR / EX-K10 / EX-DIV; a non-zero count on VAR1-EX-K30 "
    "or VAR1-PER-K16C5 is a caveat on that variant's token basis and is reported, not hidden. "
    "An ABSTENTION caused by compaction is a failure, not a caveat.",
    "DISPOSITIONS per variant: finite_completion rows (item E13), react_exhaustion rows (item "
    "E22), planner illegal-action rows, parse failures, and the delivery-normaliser receipt "
    "count. A variant whose disposition profile differs from VAR1-PLAN's has changed the "
    "episode's behaviour and not only its supply.",
]

OPEN_ITEMS = [
    {
        "id": "VAR1-OPEN-1",
        "item": (
            "scripts/analysis/slurp_paired_roster_read.py produces the pooled paired contrast, "
            "the per-channel table, the structural counts and the efficiency block on this "
            "roster, and nothing else. It hard-codes 'per-scenario NOT AVAILABLE' for its own "
            "roster and takes no --stratum-key, so the GOLD per-scenario table -- which IS "
            "derivable on R01C -- does not come out of it as committed."
        ),
        "resolution": (
            "Either teach that driver a --stratum-key flag (roster-generic, with its own unit "
            "tests), or write the VAR-1 variant driver scripts/analysis/slurp_var1_variant_"
            "read.py. Either is a separate engineering change with its own review. It must "
            "land BEFORE the variant reads and NEVER beside a live flight."
        ),
    },
    {
        "id": "VAR1-OPEN-2",
        "item": (
            "The entity FP/FN-by-slot-type decomposition, the Perception coverage read and the "
            "group-relative advantage table have no committed driver at all. The first exists "
            "inside scripts/analysis/slurp_cell3_fresh_roster_loss_diagnostic.py bound to that "
            "cell's runs; the second and third are new."
        ),
        "resolution": (
            "They belong in the VAR-1 variant driver of VAR1-OPEN-1, which reads only sealed "
            "bytes (per-sample official scores, sealed outputs, sealed phase summaries, the "
            "roster receipt) and prints labels, slot TYPE names, ids, counts and hashes only -- "
            "never an utterance, a transcript, a delivered filler or a gold string."
        ),
    },
    {
        "id": "VAR1-OPEN-3",
        "item": (
            "The prompt-fit bound of VAR1-EX-K30 and VAR1-PER-K16C5 is NOT measured in this "
            "registration; no tokenizer was contacted."
        ),
        "resolution": (
            "core.flight.cli check measures it in the coordinator's clean-tree cycle. The "
            "registered expectation and the fail-closed fallback are in this document's "
            "prompt_fit block: a COMPACT_REQUIRED is expected and proceeds; a REFUSE on "
            "VAR1-EX-K30 means that cell does not open and is re-registered at k = 26 with its "
            "own new run, attempt and fit identities."
        ),
    },
]


def accounting_block() -> dict:
    return {
        "per_cell_budget": {
            "asr_calls": 0,
            "ceilings_are_not_targets": True,
            "encoder_calls": 0,
            "fit_endpoint_calls_cap": FIT_CAP,
            "generation_calls_cap": GEN_CAP,
            "gpu_hours_fit_inclusive": GPU_HOURS_CAP,
            "native_task_contract_calls_cap": NATIVE_TASK_CONTRACT_CALLS_CAP,
            "official_complete_scoring_jobs": 1,
            "repeated_speech_audio_seconds_cap": AUDIO_CEIL,
        },
        "smoke_budget": {
            "asr_calls": 0,
            "ceilings_are_not_targets": True,
            "encoder_calls": 0,
            "fit_endpoint_calls_cap": SMOKE_FIT_CAP,
            "generation_calls_cap": SMOKE_GEN_CAP,
            "gpu_hours_fit_inclusive": SMOKE_GPU_HOURS_CAP,
            "native_task_contract_calls_cap": NATIVE_TASK_CONTRACT_CALLS_CAP,
            "official_complete_scoring_jobs": 0,
            "repeated_speech_audio_seconds_cap": SMOKE_AUDIO_CEIL,
        },
        "ceiling_arithmetic": (
            f"{GEN_CAP} = {ROW_COUNT} R01C rows x {PER_ROW_CEILING}, the locked plan's OWN "
            f"per-row contact ceiling; {FIT_CAP} = {GEN_CAP} x (1 speech packet + 3 endpoints); "
            f"{AUDIO_CEIL} s = the roster's {TOTAL_AUDIO_SECONDS} s of audio x "
            f"{PER_ROW_CEILING}. The four-row smoke is 4 x {PER_ROW_CEILING} = {SMOKE_GEN_CAP}, "
            f"{SMOKE_GEN_CAP} x 4 = {SMOKE_FIT_CAP} and {SMOKE_AUDIO_CEIL} s "
            f"({SMOKE_AUDIO_SECONDS} s x {PER_ROW_CEILING}, rounded up)."
        ),
        "expected_cost": {
            "contacts_per_row_expected": EXPECTED_CONTACTS_PER_ROW,
            "contacts_per_cell_expected": EXPECTED_CONTACTS,
            "family_contacts_expected": len(FLIGHT_SHORTS) * EXPECTED_CONTACTS + 17,
            "gpu_hours_per_cell_expected": 1.05,
            "family_gpu_hours_expected": 6.5,
            "note": (
                "Cell PLAN realised 4.0963 contacts per row on TRAIN Fold A and cell B6's plan "
                "arm 4.071 on DEV-2000-ADDED; 1.79 GPU-h per 1,080 rows at the L1 geometry "
                "scales to about 1.05 GPU-h per 625 rows. No VAR-1 knob adds a contact. These "
                "are ESTIMATES, never targets, and the ceilings above are the exact program "
                "maxima."
            ),
        },
        "plan_budget_is_run_cumulative": True,
        "unused_budget_is_not_attempt_authority": True,
        "exposure_rows": [f"{run_id(s)} (generation)" for s in FLIGHT_SHORTS]
        + [f"{fit_run_id(s)} (fit)" for s in FLIGHT_SHORTS]
        + [f"{run_id('smoke')} (generation)", f"{fit_run_id('smoke')} (fit)"]
        + [
            "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 (model-free read)",
            "SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1 (model-free read)",
        ],
        "family_scope": (
            "SIXTEEN registered rows: fourteen flight identities (seven cells x generation + "
            "fit) and two model-free-check reads. The decision receipt "
            f"{DECISION_RELPATH} (decision id {DECISION_ID}) lists the FOURTEEN flight run ids "
            "as eligible_run_ids."
        ),
    }


def population_block() -> dict:
    return {
        "roster": {"relpath": ROSTER_RELPATH_REPO, "sha256": ROSTER_SHA256},
        "roster_id": "SLURP-STAGE3-CONSTRUCTION-R01C",
        "rows": ROW_COUNT,
        "split_id": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "audio_seconds_total": TOTAL_AUDIO_SECONDS,
        "distinct_utterances": ROW_COUNT,
        "utterances_with_two_recordings": 0,
        "headset_rows": 67,
        "far_field_rows": 558,
        "scenario_strata_present": 18,
        "strata_counts": {
            "alarm": 26, "audio": 30, "calendar": 42, "cooking": 31, "datetime": 39,
            "email": 33, "general": 42, "iot": 33, "lists": 37, "music": 27, "news": 36,
            "play": 37, "qa": 38, "recommendation": 29, "social": 35, "takeaway": 37,
            "transport": 32, "weather": 41,
        },
        "gold_per_scenario_table": (
            "AVAILABLE. The roster receipt carries a per-item stratum, so the gold "
            "per-scenario table is derivable offline from the receipt alone, with no gold at "
            "runtime. This is the one thing R01C gives that DEV-2000-ADDED withheld."
        ),
        "cluster_key": "utterance_id (625 distinct; the cluster is the row on this roster)",
        "smoke_rows": SMOKE_ROWS,
        "smoke_population": list(SMOKE_IDS),
        "smoke_selection_rule": (
            "the FIRST FOUR rows of R01C in the roster's own order (positions 1-4). A pure "
            "positional selection with zero contacts: no gold, no score, no label and no "
            "separate draw entered it. Strata datetime, takeaway, alarm and audio; three "
            "far-field and one headset."
        ),
        "smoke_split_identity_hash": SMOKE_SPLIT_IDENTITY_HASH,
        "smoke_audio_seconds": SMOKE_AUDIO_SECONDS,
        "disjointness": (
            "the roster receipt proves 0 shared recordings and 0 shared utterances with TRAIN "
            "Fold A, TRAIN Fold B, DEV-1000 and DEV-2000-ADDED, and 0 overlap with the source "
            "utterances of every composed knowledge store."
        ),
        "prior_exposure": (
            "R01C has had exactly one generation exposure, cell ROLL-1 (the five-sample "
            "grouped-Solver rollout, 5,347 contacts, sealed 2026-09-23), plus the ADV-1 and "
            "GEPA proposer arms on subsets of it. It is a CONSTRUCTION roster and repeated "
            "exposure of it is its purpose."
        ),
    }


#: Chars per token used ONLY as a conservative UPPER bound on a token count
#: derived from a character count. Qwen's BPE runs about 3.5-4.0 characters per
#: token on English prose with punctuation; 2.5 is deliberately pessimistic, so
#: an estimate made with it over-states the tokens a block costs.
CONSERVATIVE_CHARS_PER_TOKEN = 2.5
CELL2_MEASURED_BOUND = {
    "perception": {"decision": "ALLOW", "required_window_tokens": 19992,
                   "operational_margin_tokens": 1512},
    "solver": {"decision": "COMPACT_REQUIRED", "required_window_tokens": 21821,
               "operational_margin_tokens": -317},
    "reviewer": {"decision": "ALLOW", "required_window_tokens": 19856,
                 "operational_margin_tokens": 1648},
    "planner": {"decision": "ALLOW", "required_window_tokens": 19795,
                "operational_margin_tokens": 1709},
    "source": (
        "docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1/registered-facts-v1.json, "
        "measured on TRAIN Fold A for the locked plan PLUS the stage3-deltas-v2 store"
    ),
}


def _mean_chars(dry_run: dict | None, form: str, phase: str) -> float | None:
    if not dry_run:
        return None
    try:
        return float(
            dry_run["forms"][form]["totals"][
                "mean_supplied_content_chars_per_node_per_row"
            ][phase]
        )
    except (KeyError, TypeError, ValueError):
        return None


def _max_chars(dry_run: dict | None, form: str, phase: str) -> int | None:
    if not dry_run:
        return None
    try:
        return int(
            dry_run["forms"][form]["totals"][
                "max_supplied_content_chars_per_node_per_row"
            ][phase]
        )
    except (KeyError, TypeError, ValueError):
        return None


def prompt_fit_block(dry_run: dict | None) -> dict:
    measured = {}
    for form in ("plan", "exk10", "exk30", "exdiv", "perk16c5"):
        entry = {}
        for phase in ("perception", "solver", "reviewer", "planner"):
            mean = _mean_chars(dry_run, form, phase)
            top = _max_chars(dry_run, form, phase)
            if mean is not None:
                entry[phase] = {
                    "mean_supplied_content_chars_per_row": mean,
                    "max_supplied_content_chars_per_row": top,
                }
        if entry:
            measured[form] = entry
    block = {
        "basis": (
            "NOT MEASURED IN TOKENS BY THIS REGISTRATION -- no tokenizer was contacted. "
            "core.flight.cli check's _assess_prompt_budget is the measurement and it runs in "
            "the coordinator's clean-tree cycle against the minted receipt."
        ),
        "slot_tokens": 24576,
        "operational_reserve_tokens": 3072,
        "rule": (
            "rails.context_budget: required_window_tokens = rendered text tokens + speech "
            "tokens + the registered special-token reserve + the 512-token completion ceiling. "
            "ALLOW when required <= slot - reserve = 21,504; COMPACT_REQUIRED when required <= "
            "slot = 24,576, which core.flight.runtime RECORDS and proceeds on under "
            "native_episode.context_fit_policy = compact-or-abstain (harness item E20, owner "
            "decision 45); REFUSE above the slot, which aborts."
        ),
        "cell2_measured_bound_for_reference": CELL2_MEASURED_BOUND,
        "offline_character_measurement": measured,
        "what_the_characters_say": (
            "The knowledge a store decides for a node does NOT travel in the rendered "
            "instruction -- it reaches the node as typed content blocks through the acquire "
            "transition, and every VAR-1 form's rendered instruction is the same 1,129 "
            "characters at the Solver and 960 at Perception. So the quantity that actually "
            "moves is measured directly: the SUPPLIED CONTENT CHARACTERS per node per row, "
            "summed from the released snapshots over the value ids the offline walk selected "
            "on the same four R01C rows. Converting a character DIFFERENCE to a token bound at "
            f"the deliberately pessimistic {CONSERVATIVE_CHARS_PER_TOKEN} characters per token "
            "over-states the tokens the extra block costs, so a fit conclusion drawn that way "
            "is conservative. The absolute required-window token count is NOT derived this "
            "way and is left to the tokenizer."
        ),
        "decision": prompt_fit_decision(dry_run),
        "the_authority_in_flight": (
            "core.preparation_fit.build_native_contact_fit_gate fits every realised immutable "
            "request against the resident tokenizer, contact by contact."
        ),
        "fallback_if_refused": (
            "FAIL-CLOSED AND REGISTERED BEFORE CONTACT: if the coordinator's check reports "
            "REFUSE (not COMPACT_REQUIRED) on VAR1-EX-K30's Solver, that cell DOES NOT OPEN. "
            "It is re-registered at k = 26 with fuse_coverage 26/26/26, a NEW run id, a NEW "
            "generation attempt id and a NEW native_contact_fit attempt id, and the k = 30 "
            "identity is retired unused. The same rule applies to VAR1-PER-K16C5 at k = 12 "
            "with coverage 1/12/12. No other cell is touched, and no margin or decision rule "
            "moves."
        ),
    }
    return block


def prompt_fit_decision(dry_run: dict | None) -> str:
    plan_solver = _max_chars(dry_run, "plan", "solver")
    k30_solver = _max_chars(dry_run, "exk30", "solver")
    plan_perc = _max_chars(dry_run, "plan", "perception")
    k16_perc = _max_chars(dry_run, "perk16c5", "perception")
    k16_solver = _max_chars(dry_run, "perk16c5", "solver")
    if None in (plan_solver, k30_solver, plan_perc, k16_perc, k16_solver):
        return (
            "EXPECTED COMPACT_REQUIRED at worst and never REFUSE on every phase of every "
            "cell; the offline character measurement was not available when this document was "
            "generated."
        )
    solver_delta = k30_solver - plan_solver
    perc_delta = k16_perc - plan_perc
    k16_solver_delta = k16_solver - plan_solver
    solver_tokens = math.ceil(solver_delta / CONSERVATIVE_CHARS_PER_TOKEN)
    perc_tokens = math.ceil(perc_delta / CONSERVATIVE_CHARS_PER_TOKEN)
    k16_solver_tokens = math.ceil(k16_solver_delta / CONSERVATIVE_CHARS_PER_TOKEN)
    return (
        "EXPECTED: ALLOW or COMPACT_REQUIRED on every phase of every cell, and NEVER REFUSE. "
        "Arithmetic, registered before contact. (1) VAR1-EX-K30's widest SUPPLIED Solver "
        f"content on the four offline rows is {k30_solver:,} characters against VAR1-PLAN's "
        f"{plan_solver:,} -- {solver_delta:,} more, at most {solver_tokens:,} tokens at "
        f"{CONSERVATIVE_CHARS_PER_TOKEN} characters per token. CELL-2's MEASURED Solver bound "
        "on TRAIN Fold A was 21,821 required-window tokens WITH a stage3-deltas block VAR-1 "
        "does not carry; adding the bound above to that upper reference gives at most "
        f"{21821 + solver_tokens:,} against the 24,576-token slot, so REFUSE is arithmetically "
        "excluded and COMPACT_REQUIRED is the expectation. (2) VAR1-PER-K16C5's widest "
        f"supplied Perception content is {k16_perc:,} characters against VAR1-PLAN's "
        f"{plan_perc:,} -- {perc_delta:,} more, at most {perc_tokens:,} tokens on the same "
        "basis. CELL-2's measured Perception bound was 19,992 with an unconditional delta "
        f"block VAR-1 does not carry, giving at most {19992 + perc_tokens:,}, again inside the "
        "slot. (3) VAR1-PER-K16C5's Solver block grows too, by a smaller amount: its widest "
        f"supplied Solver content is {k16_solver:,} characters, {k16_solver_delta:,} more than "
        f"VAR1-PLAN's, at most {k16_solver_tokens:,} tokens, for at most "
        f"{21821 + k16_solver_tokens:,}. That is the five-candidate round robin filling the "
        "UNCHANGED 28-value / 16-per-candidate slot-contract budget differently, not a larger "
        "budget: max_total_values and max_values_per_candidate are not moved. (4) VAR1-EX-K10 "
        "and VAR1-EX-DIV can only SHRINK the Solver block, and the offline measurement "
        "confirms it. A COMPACT_REQUIRED is recorded and the flight proceeds; a REFUSE "
        "triggers the registered fallback and that cell alone does not open."
    )


def contact_free_evidence_block(dry_run: dict | None) -> dict:
    if not dry_run:
        return {
            "dry_run": "NOT AVAILABLE when this document was generated",
            "proof_test": "tests/unit/test_slurp_var1_registration.py",
        }
    forms = {}
    for form, report in dry_run.get("forms", {}).items():
        totals = report.get("totals", {})
        forms[form] = {
            "ok": report.get("ok"),
            "knobs": report.get("knobs"),
            "canned_candidates": report.get("canned_candidates"),
            "first_phase_seed_source": sorted({
                walk.get("first_phase_seed_source")
                for walk in report.get("accept_walk", {}).values()
            }),
            "items_per_node_over_4_rows": totals.get("items_per_node"),
            "items_per_node_by_store_over_4_rows": totals.get("items_per_node_by_store"),
            "mean_instruction_chars_per_node": totals.get(
                "mean_instruction_chars_per_node"
            ),
            "max_instruction_chars_per_node": totals.get("max_instruction_chars_per_node"),
            "revise_second_visit_items": report.get("revise_walk", {}).get(
                "second_visit_items"
            ),
            "duplicate_walk_ok": report.get("duplicate_walk", {}).get("walked"),
        }
    return {
        "dry_run": {
            "driver": "scripts/flights/batch/var1_dry_run.py",
            "record": f"docs/readiness/{READINESS_DIR.name}/dry-run-v1.md",
            "contacts": dry_run.get("contacts"),
            "all_forms_ok": dry_run.get("ok"),
            "rows": SMOKE_ROWS,
            "what_it_walks": (
                "every one of the seven registered VAR-1 forms, composed from its OWN "
                "committed fragments over the REAL released stores, walked node by node on the "
                "same four R01C rows, with only the four role answers canned. Three walks per "
                "form: the ACCEPT path on all four rows, a REVISE revisit on row 1, and a "
                "duplicate-candidate Perception answer on row 1."
            ),
            "forms": forms,
        },
        "proof_test": (
            "tests/unit/test_slurp_var1_registration.py: every VAR-1 baseline equals the "
            "locked v2.0 plan fragment on every key except the R01C re-pointing, the per-cell "
            "identity bookkeeping and its OWN declared knobs; VAR1-PLANR equals VAR1-PLAN on "
            "every key except the fit identities and what_this_is; the knob table in "
            "protocol-registered-v1.json equals the bytes in the fragments; and the registered "
            "composed/protocol hashes reproduce from core.config.compose."
        ),
        "gates": [
            "engineering_base_check.py", "harness_admission_check.py",
            "results_ledger_check.py", "tool_catalog_check.py",
            "experiment_handoff_check.py", "finite_completion_policy_check.py",
            "stage3_algorithm_label_check.py", "derived_media_confinement_check.py",
        ],
    }


def smoke_acceptance_block(dry_run: dict | None) -> dict:
    smoke = (dry_run or {}).get("forms", {}).get("smoke", {})
    totals = smoke.get("totals", {})
    return {
        "rows_delivered": SMOKE_ROWS,
        "form": (
            "VAR1-PER-K16C5 -- the only VAR-1 form whose CONTRACT SHAPE changes. THE ITEM THIS "
            "SMOKE EXISTS FOR: that a five-candidate Perception contract renders, parses and "
            "seals on a real flight, that the configurable bounded first-occurrence projection "
            "accepts it, and that the slot-contracts candidate supply spreads its unchanged "
            "28-value budget over five candidates instead of three without exceeding "
            "max_values_per_candidate."
        ),
        "why_only_one_smoke": (
            "VAR1-PLAN and VAR1-PLANR are the locked plan's own sealed form. VAR1-EX-K10, "
            "VAR1-EX-K30 and VAR1-EX-DIV change a retrieval budget on a route whose contract, "
            "instruction bytes and response format are untouched -- there is no structural "
            "question a four-row flight would answer that the offline dry run has not already "
            "walked over the real released store."
        ),
        "contacts_per_row": (
            "4 (perception, solver, reviewer, planner); at most 11 with the review loop and "
            "one revision"
        ),
        "candidate_contract": (
            "the Perception response format must carry maxItems 5 and the realised answers must "
            "project to at most five DISTINCT intent ids in first-occurrence order; a repeated "
            "id is projected away, not an error (the CELL-1 lesson)"
        ),
        "supply": (
            "sixteen intent-boundary cards seeded at Perception on every row and twenty "
            "train-exemplar values plus the slot-contracts candidate block at the Solver, as "
            "the offline dry run measured: "
            + json.dumps(totals.get("items_per_node_by_store", {}), sort_keys=True)
        ),
        "fits": "every request fits (one request-fit receipt per contact); see prompt_fit",
        "compaction": (
            "the E20 compaction receipts per phase. A non-zero count is a CAVEAT on the token "
            "basis and is reported; an ABSTENTION caused by compaction is a FAILURE."
        ),
        "normaliser": "one deliver_normaliser receipt (saea-deliver-normalise-v3) per row",
        "dispositions": (
            "finite_completion (item E13) and react_exhaustion (item E22) counted, 0 expected "
            "on four rows; no abort"
        ),
        "tools_array": "absent on every request; tool_choice none; 0 tool calls",
        "revisit": (
            "a REVISE revisit must acquire only what the episode does not already hold; a "
            "duplicate acquisition is a FORM defect that kills the trajectory"
        ),
        "offline_precondition": (
            "scripts/flights/batch/var1_dry_run.py walks this exact composition on all four "
            "rows against the REAL released stores, zero contacts. Record in dry-run-v1.md."
        ),
        "no_score": (
            "STRUCTURAL ONLY: no official score is run on the smoke and no effectiveness claim "
            "is read from it."
        ),
    }


# ---------------------------------------------------------------------------
# Registered facts, analysis recipe, plan documents.
# ---------------------------------------------------------------------------


def build_registered_facts(hashes: dict, dry_run: dict | None) -> dict:
    return {
        "schema": "saea-slurp-stage3-var1-registered-facts-v1",
        "registered_at_utc": REGISTERED_AT_UTC,
        "source_tree": SOURCE_TREE,
        "what_this_is": (
            "Every number this registration asserts before contact, so a later read can be "
            "checked against it instead of against memory. Nothing here is a measurement of a "
            "VAR-1 cell; the cells have not flown."
        ),
        "family": {
            short: {
                "label": label(short),
                "run_id": run_id(short),
                "fit_run_id": fit_run_id(short),
                "rows": rows_of(short),
                "knobs": KNOB_TABLE[short],
            }
            for short, _l, _r, _c in FAMILY
        },
        "hashes": {
            name: {"composed_config_hash": composed, "protocol_hash": proto}
            for name, (composed, proto) in sorted(hashes.items())
        },
        "population": population_block(),
        "pins": {
            "roster": {"relpath": ROSTER_RELPATH_REPO, "sha256": ROSTER_SHA256},
            "dataset_fragment": DATASET_FRAGMENT,
            "train_exemplars_release": {
                "relpath": STORE_RELEASE_RELPATH, "sha256": STORE_RELEASE_SHA256,
            },
            "speech_query_encode_receipt": {
                "relpath": ENCODING_RECEIPT_RELPATH, "sha256": ENCODING_RECEIPT_SHA256,
            },
            "speech_packet_promotion_receipt": {
                "path": PACKET_PROMOTION_RECEIPT, "sha256": PACKET_PROMOTION_SHA256,
                "note": "800 R01 packets, a strict superset of R01C's 625",
            },
            "query_vectors": [
                {"relpath": relpath, "sha256": sha}
                for relpath, sha in _VERIFY_BINDINGS[:2]
            ],
            "verified": (
                "every pin above was re-hashed against the bytes on disk by "
                "scripts/flights/derive_slurp_var1_cells.py at generation time, not typed"
            ),
        },
        "store_facts": {
            "train_exemplars": {
                "release": "size-pool-annotated-exemplars-minus-r01",
                "values": 8554,
                "distinct_content_facets": 8554,
                "distinct_task_targets": 59,
                "mean_value_content_chars": 69.9,
                "median_value_content_chars": 66,
                "p95_value_content_chars": 117,
                "max_value_content_chars": 200,
                "note": (
                    "one value per content facet, so a k-deep recall yields at most k values; "
                    "task_target is the SLURP intent id, which is what fuse_coverage.c caps "
                    "per target in VAR1-EX-DIV"
                ),
            },
            "intent_boundaries": {
                "release": "intent-boundaries-v1",
                "values": 60,
                "facets": 60,
                "mean_value_content_chars": 702.2,
                "max_value_content_chars": 895,
                "note": (
                    "one card per intent; c=1 with m=top_l=k gives exactly k cards, so k "
                    "8 -> 16 is the single largest text change in the family"
                ),
            },
            "slot_contracts": {"release": "slot-contracts-v2", "values": 54},
        },
        "comparator_context_only": {
            "train_fold_a_plan": {"official_slu_f1": 63.63, "intent_accuracy": 82.22,
                                  "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"},
            "train_fold_a_planr": {"official_slu_f1": 63.80, "intent_accuracy": 82.50},
            "train_fold_a_margins": {"h_slu": 1.2485, "h_intent": 0.9943},
            "dev2000_added_plan": {"official_slu_f1": 65.40, "intent_accuracy": 76.60},
            "dev2000_added_margins": {"h_slu": 1.2525, "h_intent": 1.1520},
            "warning": (
                "CONTEXT ONLY. None of these is this family's comparator or bar: a margin is a "
                "property of a roster, and R01C is a different roster of a different size with "
                "a different scenario allocation. VAR1-PLAN and VAR1-PLANR measure this "
                "roster's own."
            ),
        },
        "bad_case_targets": {
            "entity_false_negatives": (
                "about 31.5 % of reference entities unmatched on TRAIN Fold A, date omission "
                "dominant (84 of 138 reference dates). The EX knobs aim at this through "
                "demonstration count and diversity."
            ),
            "entity_false_positives": (
                "about 28.8 %; 184 of 414 empty-gold rows emit entities. VAR1-EX-DIV's "
                "diversified neighbourhood and VAR1-EX-K10's shorter block are the two knobs "
                "that could move it in opposite directions."
            ),
            "intent_by_candidate_coverage": (
                "own card supplied -> 96.5 % covered, absent -> 17.3 %. This is "
                "VAR1-PER-K16C5's target and it is read DIRECTLY as a coverage rate, not "
                "inferred from the pooled score."
            ),
            "measurement_floor": (
                "about +-1.3 pp pooled SLU at n = 1,000 across flights. At n = 625 the "
                "cross-flight floor is wider still, which is exactly why this family measures "
                "its OWN null on its OWN roster and leans on dense per-class proxies."
            ),
        },
        "contact_free_evidence": contact_free_evidence_block(dry_run),
        "prompt_fit_bound": prompt_fit_block(dry_run),
        "accounting": accounting_block(),
    }


def build_analysis_recipe(hashes: dict) -> dict:
    return {
        "schema": "saea-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-var1-construction-variant-read-v1",
        "registered_at_utc": REGISTERED_AT_UTC,
        "execution_profile": "model-free-check",
        "title": (
            "VAR-1: the first construction-variant rollout of the locked v2.0 plan on the "
            "625-row R01C construction roster -- four single-knob variants and a "
            "request-identical replicate, each paired by row against VAR1-PLAN at the roster's "
            "own null"
        ),
        "cell_kind": (
            "CONSTRUCTION-VARIANT ROLLOUT. The deliverable is a per-variant table and a "
            "group-relative advantage table, not a verdict."
        ),
        "claim_boundary": (
            "Descriptive paired read on a CONSTRUCTION roster (split role discovery). No "
            "admission, no lock, no store release, no test claim, no superiority or "
            "generalisation claim. Owner decisions 28 / 86 / 29 / 108. A variant that "
            "separates from the null here is a CANDIDATE for an out-of-fold re-read on TRAIN "
            "Fold A and DEV-2000-ADDED, each at that roster's own null."
        ),
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": 0, "server": 0,
                     "tokenizer": 0},
        "delta_convention": (
            "delta = variant minus VAR1-PLAN, in percentage points; negative is worse"
        ),
        "arms": {
            short: {
                "run_id": run_id(short),
                "attempt_id": gen_attempt(short),
                "run_manifest_sha256": "PENDING_SEAL",
                "outputs_sha256": "PENDING_SEAL",
                "scores_sha256": "PENDING_SEAL",
            }
            for short in FLIGHT_SHORTS
        },
        "comparator": {"arm": "plan", "run_id": run_id("plan"),
                       "never_reflown": True},
        "own_null": {
            "left": run_id("plan"),
            "right": run_id("planr"),
            "root_id": "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1",
            "recipe_id": "slurp-stage3-var1-own-null-v1",
            "order": (
                "READ FIRST. h_SLU and h_intent are sealed before any variant contrast stage "
                "is read and are never adjusted afterwards."
            ),
            "h_slu": "PENDING_OWN_NULL_READ",
            "h_intent": "PENDING_OWN_NULL_READ",
        },
        "driver": {
            "own_null_invocation": (
                "bash scripts/flights/batch/var1_read.sh own-null"
            ),
            "variant_invocation": (
                "bash scripts/flights/batch/var1_read.sh variant "
                "<exk10|exk30|exdiv|perk16c5|planr>"
            ),
            "engine": "scripts/analysis/slurp_paired_roster_read.py",
            "scorer_id": "slurp-slu-official-train",
            "roster": ROSTER_RELPATH_REPO,
            "cluster_key": "utterance_id",
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "seed": 20260915,
            "draws": 10000,
            "status_written": (
                "DESCRIPTIVE, always. This family has no verdict for the coordinator to apply."
            ),
        },
        "estimators": {
            "cluster_core": "analysis.bootstrap.paired_cluster_bootstrap",
            "paired_per_row": "analysis.paired.paired_contrast",
            "bootstrap_pooled": "analysis.paired.resampled_statistic",
            "pooled_micro_f1": "analysis.null_calibration.pooled_f1",
            "mcnemar": "analysis.paired.paired_contrast's own sign_test_p",
        },
        "resampling": {
            "cluster_key": "utterance_id",
            "distinct_clusters": ROW_COUNT,
            "seed": 20260915,
            "draws": 10000,
            "intervals": ["CI95 for the reading clauses", "CI90 for diagnostics"],
            "interval_form": "percentile pairs of the same retained replicate sequence",
            "tables": ["natural mixture", "equal-stratum weighting over the gold scenario"],
        },
        "metrics": [
            {"id": "pooled_slu_f1", "estimand": "pooled count F1", "role": "primary",
             "null_half_width_pp": "PENDING_OWN_NULL_READ"},
            {"id": "intent_accuracy", "estimand": "joint scenario+action accuracy",
             "role": "guard", "null_half_width_pp": "PENDING_OWN_NULL_READ"},
            {"id": "span_f1", "estimand": "pooled count F1", "role": "secondary"},
            {"id": "scenario_accuracy", "estimand": "exact match", "role": "secondary"},
            {"id": "action_accuracy", "estimand": "exact match", "role": "secondary"},
        ],
        "scorer": {
            "id": "slurp-slu-official-train",
            "gold": "TRAIN",
            "evaluator": "the pinned SLURP official evaluate.py",
            "runs": (
                "once per complete manifest through core.scoring_batch, never sharded; this "
                "read invokes no scorer"
            ),
        },
        "population": {
            "roster": ROSTER_RELPATH_REPO,
            "rows": ROW_COUNT,
            "cluster_key": "utterance_id",
            "distinct_utterances": ROW_COUNT,
            "gold_per_scenario_table": (
                "AVAILABLE from the roster receipt's per-item stratum -- 18 strata, 26-42 rows "
                "each -- with no gold at runtime."
            ),
        },
        "tables_required": [
            "THE VARIANT TABLE: one row per variant (EX-K10, EX-K30, EX-DIV, PER-K16C5) plus "
            "PLANR as the A/A control row, columns = official pooled SLU-F1, delta, CI90, "
            "CI95, intent, intent delta, CI95, saves / harms / ties, McNemar p, with h_SLU and "
            "h_intent printed in the header",
            "the own-null margin table (VAR1-PLAN vs VAR1-PLANR), printed above the variant "
            "table and dated before it",
            "the GOLD per-scenario table per variant in both weightings",
            "entity FP / FN by slot TYPE per variant, with the empty-gold emission rate",
            "Perception coverage per variant: gold-intent-in-candidates rate and the candidate "
            "count distribution",
            "the group-relative advantage table per runtime-observable state, with per-state n",
            "the cost and frontier table per variant, per 625 rows",
            "the supply-realisation table per variant (exemplar values per row, intent cards "
            "per row) beside the offline dry-run projection",
        ],
        "diagnostics_required": DIAGNOSTICS_REQUIRED,
        "decision_rule": {
            "rule": (
                "see protocol-registered-v1.json decision_rule. The family returns a table; no "
                "ADMITTED / NEUTRAL / HARMFUL label is attached to any VAR-1 cell."
            ),
            "comparator": run_id("plan"),
        },
        "open_items": OPEN_ITEMS,
        "output": {
            "analysis_root": "analysis/SAEA-SLURP-STAGE3-VAR1-<stage>-V1",
            "files": ["stop.json", "structural.json", "score-contrasts.json",
                      "efficiency.json", "per-scenario-tables.json", "verdict.json",
                      "README.md"],
            "harm_rule": (
                "no utterance text, gold label, delivered filler or model output is printed or "
                "persisted; labels, slot TYPE names, ids, counts, rates and hashes only"
            ),
        },
        "authority": {
            "evidence_base": (
                "docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md sections 5-7; "
                "docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md; "
                "docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md"
            ),
            "own_null_precedent": (
                "docs/results/2026-09-22-slurp-planr-v2-lock-replicate-verdict.md (TRAIN Fold "
                "A) and the DEV-2000-ADDED own null of the CELL-3 package"
            ),
        },
    }


def build_plan_document(short: str, kind: str, hashes: dict, protocol_sha256: str) -> dict:
    composed, proto = hashes[cell_id(short) if kind == "generation" else fit_cell_id(short)]
    generation = kind == "generation"
    return {
        "schema": "saea-registered-generation-plan-v1",
        "plan_kind": "generation" if generation else "native contact fit",
        "cell": cell_id(short) if generation else fit_cell_id(short),
        "experiment": experiment_name(short),
        "composed_config_hash": composed,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "registered_at_utc": REGISTERED_AT_UTC,
        "source_tree": SOURCE_TREE,
        "expected_session_id": SERVICE_SESSION,
        "execution_plan": {
            "schema": "saea-execution-plan-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": run_id(short) if generation else fit_run_id(short),
            "attempt_id": gen_attempt(short) if generation else fit_attempt(short),
            "carrier_lock_key": "slurp",
            "execution_profile": "bounded-discovery-probe",
            "split_role": SPLIT_ROLE,
            "split_identity_hash": split_hash_of(short),
            "planned_model_calls": gen_cap_of(short) if generation else fit_cap_of(short),
            "planned_gpu_hours": gpu_hours_of(short),
            "planned_speech_audio_seconds": audio_cap_of(short),
            "protocol_hash": proto,
        },
        "execution_route": (
            (
                "Shared core.flight.cli campaign over the committed single-cell campaign plan "
                f"configs/campaign/{experiment_name(short)}.json; the campaign acquires its own "
                f"GenerationLease against the resident session {SERVICE_SESSION} (attach only, "
                "never spawn or stop) and schedules the one official complete TRAIN score at "
                "finalize. Queued through the SAEA-Batch-Driver scheduled task (owner decision "
                "77). coordinate-fit must NOT be run."
            )
            if generation and not is_smoke(short)
            else (
                "No standalone fit run. core.preparation_fit.build_native_contact_fit_gate "
                "fits each realised native request inside the same flight, under the same "
                "lease. coordinate-fit must NOT be run, or this row is double-charged."
            )
            if not generation
            else (
                "The four-row form smoke rides the VAR1-PER-K16C5 step of "
                "scripts/flights/batch/batch_chain_var1.sh; the batch driver flies it before "
                "that arm opens. No scorer runs on it."
            )
        ),
        "family_budget": {
            "asr_calls": 0,
            "ceilings_are_not_targets": True,
            "encoder_calls": 0,
            "fit_endpoint_calls_cap": fit_cap_of(short),
            "generation_calls_cap": gen_cap_of(short),
            "gpu_hours_fit_inclusive": gpu_hours_of(short),
            "native_task_contract_calls_cap": NATIVE_TASK_CONTRACT_CALLS_CAP,
            "official_complete_scoring_jobs": 0 if is_smoke(short) else 1,
            "repeated_speech_audio_seconds_cap": audio_cap_of(short),
        },
        "purpose": PURPOSE_HEAD + f"THIS PLAN IS CELL {label(short)}: {MODULE_NOTE[short]}. "
        + WHAT_THIS_IS[short] + " " + PURPOSE_TAIL,
        "modules": {
            "base": (
                "the LOCKED v2.0 default plan "
                "(configs/baseline/slurp-native-default-plan-lock-baseline-v1.json): the "
                "complete native episode with the review loop on, the shared controller and "
                "FlightRuntime path, no phase_tools on any role, Solver-only answer authority, "
                "the max512 np4 resident geometry, the intent-boundaries v1 / slot-contracts "
                "v2 / train-exemplars stores, saea-deliver-normalise-v3 at delivery, and items "
                "E13 and E22 declared. Nothing of it moves except this cell's own declared "
                "knobs."
            ),
            "roster_repointing": (
                "the R01C re-pointing cell ROLL-1 already proved on this venue, key for key: "
                "the two query_source pins, preparation_source_receipts, the packet promotion "
                "receipt and its sha256, and the MINUS-R01 exemplar store release and snapshot "
                "(coordinator decision 102: a construction roster may never retrieve itself). "
                "Not a variant, and identical across all seven cells."
            ),
            "knobs": KNOB_TABLE[short],
            "what_moved": KNOB_TABLE[short]["moved_against_the_locked_plan"],
            "zero_added_contacts": (
                "no VAR-1 knob adds a contact: every one of them changes how much text an "
                "already-scheduled request carries. The role graph, and therefore the "
                "11-contact per-row ceiling, is the locked plan's unchanged."
            ),
            "second_declared_key_not_a_factor": (
                "native_episode.react_exhaustion_policy = continue-without-answer (item E22) "
                "and finite_completion_policy = deliver-latest-or-abstain (item E13): "
                "failure-mode declarations the locked plan already carries, required of every "
                "live SLURP native cell by scripts/checks/finite_completion_policy_check.py. "
                "Neither renders a request byte."
            ),
            "per_role_rendering_held": "native_episode.tool_schema_rendering is NOT armed.",
        },
        "decision_rule": DECISION_RULE,
        "prepared_phase_supply": {
            "status": "NOT PINNED HERE",
            "allow_output_change": "--allow-output-change must never be passed",
            "note": (
                "harness item E16: scripts/flights/repin_cell.py mints this cell's own "
                "first-phase supply model-free at flip time and writes the pin plus the "
                "matching preparation requirement. The committed baseline carries no "
                "prepared_phase_supply key."
            ),
        },
        "protocol_document": {
            "relpath": f"docs/readiness/{READINESS_DIR.name}/protocol-registered-v1.json",
            "sha256": protocol_sha256,
        },
        "quality_read_gate": (
            "no task-quality read before this cell's complete sealed manifest, its exact "
            f"ordered {rows_of(short)} outputs, its native phase summary and "
            + ("no scorer (the smoke runs none)" if is_smoke(short)
               else "its single successful complete official TRAIN score")
            + " all exist, and not before the own-null read "
            "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 has sealed its margin table."
        ),
        "failure_policy": FAILURE_POLICY,
        "registration_base_commit": "8db3d5b3",
        "preparation_base_commit": "8db3d5b3",
        "unused_budget_is_not_attempt_authority": True,
    }


# ---------------------------------------------------------------------------
# Exposure-ledger rows.
# ---------------------------------------------------------------------------

_LEDGER_HEADER_RUN = "run/experiment id"

REGISTERED_BY = (
    "REGISTERED BEFORE CONTACT (draft, root countersignature pending) 2026-09-24 at study "
    "commit {commit} by the VAR-1 registration agent (worktree "
    "/home/chao/saea-worktrees/fable-var1, branch fable/var1)."
)

MODEL_TOOL = (
    "Frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M decoder-only (no mmproj) at np4 x 24,576 "
    "(98,304 total), max512, on the resident session "
    "serving-slurp-native-candidate-five-train-a-np4-v1, attached and never spawned or "
    "stopped; promoted SLURP-STAGE3-CONSTRUCTION-R01 speech packets; NO native tool authority "
    "on any role (no tools array is rendered on any request; realised native task-contract "
    "call count expected 0 against a ceiling of 0); one delivery normaliser receipt per row "
    "(saea-deliver-normalise-v3). No second answering model, retriever or judge."
)

INHERITED_EXPOSURE = (
    "All prior SLURP exposure carried forward unchanged. SLURP-STAGE3-CONSTRUCTION-R01C TRAIN "
    "rows: this roster's audio was contact-only for the model-free speech-query encoding pass "
    "that built its two query-vector files (SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY"
    "-ENCODING-V1 and the id-selected R01C derivatives), and has had exactly ONE generation "
    "exposure, cell ROLL-1 (SAEA-SLURP-STAGE3-ROLLOUT-R01-V1, the five-sample grouped-Solver "
    "rollout, 5,347 contacts, sealed 2026-09-23), plus the ADV-1 and GEPA proposer arms on "
    "subsets of it. It is a CONSTRUCTION roster (roster_role construction, split_role "
    "discovery) and repeated exposure of it is its purpose. No gold, reference or future turn "
    "is read at runtime. R01C is the CLEAN subset: R01 minus every recording whose utterance "
    "is a source of any composed knowledge store (175 removed, coordinator decision 102), and "
    "the exemplar store this family retrieves from is the MINUS-R01 release, so no row can "
    "retrieve its own utterance. TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000-ADDED and the "
    "test split stay untouched by this family."
)


def _split_row_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if len(stripped) < 2 or not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _find_ledger_row(text: str, row_id: str) -> str | None:
    header: list[str] | None = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = _split_row_cells(line)
        if cells is None:
            continue
        next_cells = _split_row_cells(lines[index + 1]) if index + 1 < len(lines) else None
        if next_cells is not None and all(not c.strip("-: ") for c in next_cells):
            lowered = [c.lower() for c in cells]
            header = lowered if _LEDGER_HEADER_RUN in lowered else None
            continue
        if header is not None and len(cells) == len(header):
            if cells[header.index(_LEDGER_HEADER_RUN)] == row_id:
                return line
    return None


def build_ledger_row(
    *, row_id: str, execution_profile: str, scope: str, model_tool: str, carrier_split: str,
    split_identity: str, calls: int, audio_seconds: int, gpu_hours: float, artifacts: str,
    notes: str,
) -> str:
    cells = [
        REGISTRATION_DATE, row_id, execution_profile, scope, model_tool, carrier_split,
        SPLIT_ROLE, split_identity, "no", str(calls), str(audio_seconds), str(gpu_hours),
        INHERITED_EXPOSURE, artifacts, notes,
    ]
    return "| " + " | ".join(cells) + " |"


def _cell_scope(short: str, kind: str) -> str:
    head = (
        f"Cell {label(short)} of the Stage-3 VAR-1 CONSTRUCTION-VARIANT family (owner directive "
        "2026-09-24: training-free RL gains come from rolling out VARIATIONS of prompts, data "
        "and content construction over an optimisation space, scored per variant; handoff "
        "docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md sections 5-7, routes "
        "F3 and F4). "
    )
    if kind == "fit":
        return (
            head
            + "THE TOKENIZER-CAPACITY FIT PASS of that cell: same population, same stores, same "
            "knobs. A SPEND identity, never flown as a generation cell. "
            "core.preparation_fit.build_native_contact_fit_gate fits each realised native "
            "request inside the same flight under the same lease; coordinate-fit must NOT be "
            "run, or this row is double-charged."
        )
    return head + WHAT_THIS_IS[short]


def _cell_notes(short: str, kind: str, commit: str, protocol_sha: str) -> str:
    generation = kind == "generation"
    plan_doc = (
        f"docs/readiness/{READINESS_DIR.name}/{short}-"
        f"{'generation' if generation else 'fit'}-plan-registered-v1.json"
    )
    order = ORDER_CONSTRAINT[short]
    common = (
        f"HELD. {order} "
        f"Registered budgets: {gen_cap_of(short)} generation calls "
        f"({rows_of(short)} rows x {PER_ROW_CEILING}, the locked plan's own per-row contact "
        f"ceiling), {fit_cap_of(short)} fit endpoint calls, {audio_cap_of(short)} repeated "
        f"speech audio seconds, {gpu_hours_of(short)} GPU hours. Expected about "
        f"{EXPECTED_CONTACTS_PER_ROW} contacts per row "
        f"({17 if is_smoke(short) else EXPECTED_CONTACTS} total) -- an ESTIMATE, never a "
        "target; no VAR-1 knob adds a contact. Shared core.flight.cli campaign over "
        + (
            f"configs/campaign/{experiment_name(short)}.json"
            if not is_smoke(short)
            else "the VAR1-PER-K16C5 step of scripts/flights/batch/batch_chain_var1.sh"
        )
        + ". No prepared_phase_supply pin is committed; scripts/flights/repin_cell.py builds "
        "each cell's own model-free at flip time (harness item E16) and --allow-output-change "
        "must never be passed. Held on the root admission receipt "
        f"{DECISION_RELPATH} (decision id {DECISION_ID}), whose eligible_run_ids must list this "
        "family's FOURTEEN run ids. The family returns a DESCRIPTIVE table and no admission "
        "verdict; R01C is a CONSTRUCTION roster (owner decisions 28, 86) and any variant that "
        "separates from this roster's own null must be re-read on TRAIN Fold A and on "
        "DEV-2000-ADDED before it is a claim of any kind. Preregistration: "
        f"{PREREG_RELPATH}; package README docs/readiness/{READINESS_DIR.name}/README.md; "
        f"offline seven-form dry run docs/readiness/{READINESS_DIR.name}/dry-run-v1.md (all "
        "forms PASS, zero contacts). Protocol document "
        f"docs/readiness/{READINESS_DIR.name}/protocol-registered-v1.json sha256 "
        f"{protocol_sha}. Plan document {plan_doc}. "
        + REGISTERED_BY.format(commit=commit)
    )
    return common


def build_all_ledger_rows(commit: str, protocol_sha: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for short in FLIGHT_SHORTS + ("smoke",):
        for kind in ("generation", "fit"):
            rid = run_id(short) if kind == "generation" else fit_run_id(short)
            rows.append((
                rid,
                build_ledger_row(
                    row_id=rid,
                    execution_profile="bounded-discovery-probe",
                    scope=_cell_scope(short, kind),
                    model_tool=MODEL_TOOL,
                    carrier_split=f"slurp SLURP-STAGE3-CONSTRUCTION-R01C {rows_of(short)}",
                    split_identity=split_hash_of(short),
                    calls=gen_cap_of(short) if kind == "generation" else fit_cap_of(short),
                    audio_seconds=audio_cap_of(short),
                    gpu_hours=gpu_hours_of(short),
                    artifacts=(
                        f"docs/readiness/{READINESS_DIR.name}/{short}-"
                        f"{'generation' if kind == 'generation' else 'fit'}"
                        "-plan-registered-v1.json"
                    ),
                    notes=_cell_notes(short, kind, commit, protocol_sha),
                ),
            ))
    read_rows = (
        (
            "SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1",
            "The R01C OWN NULL of the VAR-1 construction-variant family: the paired read of "
            "cell VAR1-PLAN against its request-identical replicate VAR1-PLANR over the same "
            "625 R01C rows, which produces the CI95 half-widths h_SLU and h_intent every VAR-1 "
            "variant is read at. It is READ FIRST and its margin table is SEALED before any "
            "variant contrast stage is read; the margins are never adjusted afterwards. A "
            "margin is a property of a roster, never of a mechanism: the TRAIN Fold A "
            "(1.2485 / 0.9943) and DEV-2000-ADDED (1.2525 / 1.1520) half-widths are context "
            "only and are not this family's bar.",
            "scripts/flights/batch/var1_read.sh own-null",
        ),
        (
            "SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1",
            "The VAR-1 VARIANT READ: each construction variant (EX-K10, EX-K30, EX-DIV, "
            "PER-K16C5) and the replicate paired by row against the sealed VAR1-PLAN outputs "
            "over the same 625 R01C rows, at the own-null margins. Deliverables: the per-row "
            "paired variant table, the GOLD per-scenario table in both weightings (derivable "
            "on R01C from the roster receipt's per-item stratum), entity false positives and "
            "false negatives by slot TYPE per variant, the Perception coverage per variant "
            "from the sealed Perception receipts, and the GROUP-RELATIVE ADVANTAGE of each "
            "variant per runtime-observable state (predicted scenario, candidate count, "
            "channel). DESCRIPTIVE ONLY: no admission verdict, no lock, no store release. "
            "Variants are chosen here on CONSTRUCTION rows; any winner must be re-read on "
            "TRAIN Fold A and on DEV-2000-ADDED, each at that roster's own null, before it is "
            "a claim.",
            "scripts/flights/batch/var1_read.sh variant <cell>",
        ),
    )
    for rid, scope, invocation in read_rows:
        rows.append((
            rid,
            build_ledger_row(
                row_id=rid,
                execution_profile="model-free-check",
                scope=scope,
                model_tool=(
                    "none -- scripts/analysis/slurp_paired_roster_read.py over sealed bytes "
                    "only; no model, tokenizer, encoder, ASR, scorer, embedder, server, "
                    "network, GPU or paid API contact; the resident llama-server is never "
                    "started, stopped, attached to or queried"
                ),
                carrier_split=f"slurp SLURP-STAGE3-CONSTRUCTION-R01C {ROW_COUNT}",
                split_identity=SPLIT_IDENTITY_HASH,
                calls=0,
                audio_seconds=0,
                gpu_hours=0.0,
                artifacts=(
                    f"docs/readiness/{READINESS_DIR.name}/analysis-recipe-v1.json; "
                    f"{invocation}"
                ),
                notes=(
                    "DRAFT, registered before the reads exist. It reads only sealed manifests, "
                    "sealed per-sample official scores (slurp-slu-official-train), sealed "
                    "per-row outputs, sealed phase summaries and sealed flight receipts of "
                    "cells that carry their own rows, plus the committed roster receipt. No "
                    "utterance text, gold label, delivered filler or model output is printed "
                    "or persisted anywhere: the read publishes label names, slot TYPE names, "
                    "identifiers, counts, rates and hashes only. OPEN ITEM registered before "
                    "contact: the committed driver produces the pooled paired contrast, the "
                    "per-channel table, the structural counts and the efficiency block, and "
                    "NOT the per-scenario table, the entity FP/FN-by-slot-type decomposition, "
                    "the Perception coverage or the group-relative advantage table; those need "
                    "a VAR-1 read driver that does not exist yet and must land, with its own "
                    "tests and review, BEFORE the variant reads and never beside a live "
                    "flight (protocol open_items VAR1-OPEN-1 and VAR1-OPEN-2). "
                    + REGISTERED_BY.format(commit=commit)
                ),
            ),
        ))
    return rows


def append_ledger_rows(commit: str, protocol_sha: str, *, check: bool) -> list[str]:
    text = LEDGER_PATH.read_text(encoding="utf-8")
    appended: list[str] = []
    new_text = text
    for row_id, row in build_all_ledger_rows(commit, protocol_sha):
        existing = _find_ledger_row(new_text, row_id)
        if existing is not None:
            cells = _split_row_cells(existing)
            if cells is not None and cells[8].strip().lower() == "yes":
                raise DeriveError(
                    f"exposure ledger row {row_id!r} is already consumed = yes; refusing"
                )
            if existing.strip() != row.strip():
                if check:
                    appended.append(f"WOULD-REWRITE {row_id}")
                    continue
                new_text = new_text.replace(existing, row)
                appended.append(f"rewritten {row_id}")
            continue
        if not new_text.endswith("\n"):
            new_text += "\n"
        new_text += row + "\n"
        appended.append(f"appended {row_id}")
    if appended and not check:
        LEDGER_PATH.write_text(new_text, encoding="utf-8", newline="\n")
    return appended


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="dry run: write nothing")
    parser.add_argument("--stage", choices=("configs", "hashes", "package"), default="configs")
    parser.add_argument(
        "--commit", default=REGISTRATION_COMMIT,
        help=(
            "the study commit the DRAFT ledger rows name. The default is the commit that "
            "actually carries this registration, so a re-run reproduces the committed rows "
            "byte for byte; a commit cannot name its own hash, which is why the value is a "
            "constant here and was stamped by a follow-up commit."
        ),
    )
    args = parser.parse_args(argv)

    verify_bindings()
    lock = _read_json(BASELINE_DIR / f"{LOCK_BASELINE}.json")
    roll = _read_json(BASELINE_DIR / f"{ROLL_BASELINE}.json")

    statuses: list[str] = []
    for short, _lbl, _rid, _cst in FAMILY:
        statuses.append(
            "%-28s %s" % (
                baseline_name(short),
                _write_if_needed(
                    BASELINE_DIR / f"{baseline_name(short)}.json",
                    _canonical(build_baseline(short, lock, roll)),
                    check=args.check,
                ),
            )
        )
        statuses.append(
            "%-28s %s" % (
                experiment_name(short),
                _write_if_needed(
                    EXPERIMENT_DIR / f"{experiment_name(short)}.json",
                    _canonical(build_experiment(short)),
                    check=args.check,
                ),
            )
        )
        if not is_smoke(short):
            statuses.append(
                "%-28s %s" % (
                    "campaign/" + experiment_name(short),
                    _write_if_needed(
                        CAMPAIGN_DIR / f"{experiment_name(short)}.json",
                        _canonical(build_campaign(short)),
                        check=args.check,
                    ),
                )
            )
    for line in statuses:
        print(line)

    if args.stage == "configs":
        return 0

    hashes: dict[str, tuple[str, str]] = {}
    for short, _lbl, _rid, _cst in FAMILY:
        hashes.update(composed_hashes(short))

    if args.stage == "hashes":
        print(json.dumps(
            {
                name: {"composed_config_hash": c, "protocol_hash": p}
                for name, (c, p) in sorted(hashes.items())
            },
            indent=1, sort_keys=True,
        ))
        return 0

    dry_run = None
    if DRY_RUN_RECEIPT.is_file():
        dry_run = json.loads(DRY_RUN_RECEIPT.read_text(encoding="utf-8"))
        if not dry_run.get("ok"):
            raise DeriveError("the offline dry run did not pass; refusing to register on it")
    else:
        print(f"{DRY_RUN_RECEIPT} missing; the package is generated without it",
              file=sys.stderr)

    package: list[str] = []

    protocol = build_protocol(hashes, dry_run)
    protocol_text = _canonical(protocol)
    package.append("%-42s %s" % (
        "protocol-registered-v1.json",
        _write_if_needed(READINESS_DIR / "protocol-registered-v1.json", protocol_text,
                         check=args.check),
    ))
    protocol_sha256 = _sha256_bytes(protocol_text.encode("utf-8"))

    package.append("%-42s %s" % (
        "registered-facts-v1.json",
        _write_if_needed(READINESS_DIR / "registered-facts-v1.json",
                         _canonical(build_registered_facts(hashes, dry_run)),
                         check=args.check),
    ))
    package.append("%-42s %s" % (
        "analysis-recipe-v1.json",
        _write_if_needed(READINESS_DIR / "analysis-recipe-v1.json",
                         _canonical(build_analysis_recipe(hashes)), check=args.check),
    ))
    for short, _lbl, _rid, _cst in FAMILY:
        for kind in ("generation", "fit"):
            name = f"{short}-{kind}-plan-registered-v1.json"
            package.append("%-42s %s" % (name, _write_if_needed(
                READINESS_DIR / name,
                _canonical(build_plan_document(short, kind, hashes, protocol_sha256)),
                check=args.check,
            )))
    for line in package:
        print(line)
    print("protocol-registered-v1.json sha256", protocol_sha256)
    for line in append_ledger_rows(args.commit, protocol_sha256, check=args.check):
        print("ledger:", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
