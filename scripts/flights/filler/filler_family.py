"""Shared identities and derivation rules of the standing rollout FILLER family (owner decision 162).

The filler family is sealed five-sample rollout pools of the CURRENT BEST SLURP system on TRAIN rows
that lie outside Fold A, outside every evaluation roster and outside every knowledge source the
system reads, cut into chunks of about 200 rows, each chunk its own run id, exposure rows and decision
receipt. The pools are the rollout substrate of the training-free RL inner loop
(``sealed-credit-system-policy-v1`` in ``core/stage3_algorithms.py``); each chunk is DESCRIPTIVE by
construction and never an admission cell.

THE FORM. Cell ROLL-2's grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality
commit at min_support 3 / similarity 0.8, policy program
``phase-native-candidates-review-revise-samples5-v1`` at max_contacts 19) composed with cell AGREE's
agreement-term pins (owner decision 161: ``w_agree`` 1.0 over the self-excluded exemplar-intent vote,
recall ``k`` 60, delivered width ``fuse_coverage`` 8-1-8), re-pointed onto the filler roster. The
agreement table is roster-specific, so the filler roster carries its OWN table, built model-free the
way AGREE's was (``scripts/build_slurp_intent_exemplar_agreement.py``) from the committed FILLER BASE
cell -- ROLL-2's form on the whole filler roster at ``w_agree`` 0.0, never flown -- so its source
identity is a committed config and not a working-tree state.

THE ROSTER. The exemplar pool the system retrieves from (``size-pool-annotated-exemplars``, 9,354
utterances) is every SLURP TRAIN utterance except TRAIN Fold A and TRAIN Fold B, and the runner's
BUILD/USE guard refuses a query row whose sample id is a knowledge source. The only TRAIN rows outside
Fold A that the current best system can fly are therefore TRAIN Fold B's 1,080
(``docs/receipts/rosters/slurp-evo-fold-b-v2.json``); ``build_filler_roster.py`` proves that and the
disjointness from every evaluation roster before it writes anything.

Everything here is model-free: no model, server, encoder, embedder, tokenizer, scorer or network
contact is made by any function in this module.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# ---- the family ---------------------------------------------------------------------------------
FAMILY = "filler-fold-b"
FAMILY_DATE = "2026-09-27"
OWNER_DECISION = 162
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
FAMILY_DIR = f"docs/readiness/{FAMILY_DATE}-slurp-stage3-{FAMILY}-family-v1"
SEED = 20260927
PER_SCENARIO_PER_CHUNK = 10
SMOKE_ROWS = 4

PARENT_ROSTER = "docs/receipts/rosters/slurp-evo-fold-b-v2.json"
PARENT_ROSTER_ID = "SLURP-EVO-FOLD-B-V2"
#: the Fold B runtime view's own split_name; rails.adapters.slurp_runtime requires a TRAIN cell's split_id to equal it
DATASET_SPLIT_NAME = "SLURP-EVO-FOLD-B-V2"
FAMILY_ROSTER = f"docs/receipts/rosters/slurp-stage3-{FAMILY}-v1.json"
FAMILY_ROSTER_ID = "SLURP-STAGE3-FILLER-FOLD-B-V1"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-b-1080"
MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

# ---- the parents --------------------------------------------------------------------------------
ROLL2 = {
    "arm": {
        "cell": "slurp-native-stage3-roll-2-fold-a-v1",
        "baseline": "slurp-native-stage3-roll-2-fold-a-baseline-v1",
        "run": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1",
        "fit_run": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-FIT-V1",
        "gen_attempt": "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation",
        "fit_attempt": "attempt-slurp-native-stage3-roll-2-fold-a-v1-fit",
    },
    "smoke": {
        "cell": "slurp-native-stage3-roll-2-fold-a-smoke-4-v1",
        "baseline": "slurp-native-stage3-roll-2-fold-a-smoke-4-baseline-v1",
        "run": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-V1",
        "fit_run": "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-SMOKE-4-FIT-V1",
        "gen_attempt": "attempt-slurp-native-stage3-roll-2-fold-a-smoke-4-v1-generation",
        "fit_attempt": "attempt-slurp-native-stage3-roll-2-fold-a-smoke-4-v1-fit",
    },
}
ROLL2_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1"
ROLL2_DATASET = "slurp-speech-native-evo-fold-a-1080"
ROLL2_SPLIT_ID = "SLURP-EVO-FOLD-A-V2"
ROLL2_ROSTER = "docs/receipts/rosters/slurp-evo-fold-a-v2.json"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
AGREE_ARM = "slurp-native-stage3-agree-w1-fold-a-v1"
AGREE_DERIVER = "scripts/flights/derive_slurp_agree_cells.py"

#: ROLL-2's sealed arm: 8,996 contacts for 1,080 rows over 8,558 s of campaign wall
#: (batch-status arm-start 2026-09-26T16:00:01Z, arm-exit 18:22:39Z; arm-inspect calls 8996).
ROLL2_CONTACTS = 8996
ROLL2_ROWS = 1080
ROLL2_WALL_SECONDS = 8558
CONTACTS_PER_ROW_CEILING = 19
FIT_MULTIPLIER = 4
ROLL2_GPU_HOURS_CAP = 12.0

# ---- the roster-bound pins (TRAIN Fold B) --------------------------------------------------------
BOUNDARY_QUERY = {
    "relpath": "vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl",
    "sha256": "83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299",
    "tool_contact_ledger_row": "SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1",
}
FOLD_A_ALIAS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-A-ALIAS-V1/query-dimension-alias.json"
FOLD_B_ALIAS = {
    "relpath": "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-B-ALIAS-V1/query-dimension-alias.json",
    "sha256": "78de8aa2d30afab442d286b1a14919e1dfc031f79b007f62b3eebd747a9d0ea0",
}
FOLD_B_ENCODE_RECEIPT = {
    "relpath": "preparation-runs/SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json",
    "sha256": "583d37669b3a8275be6a244454e21ebd7b5fbe1fd90af2b73f251d86bf7d00eb",
}
CONTENT_QUERY_DIR = f"vectors/slurp-stage3-{FAMILY}-v1"
CONTENT_QUERY = f"{CONTENT_QUERY_DIR}/query-vectors-speech-content-v1.jsonl"
CONTENT_QUERY_PROVENANCE = f"{CONTENT_QUERY_DIR}/query-vectors-speech-content-v1.provenance.json"
PREPARE_ROW = "SAEA-SLURP-STAGE3-FILLER-FOLD-B-PREPARE-V1"
AGREEMENT_ID = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1"
AGREEMENT = f"prepared/{AGREEMENT_ID}/agreement.jsonl"
AGREEMENT_RECEIPT = f"prepared/{AGREEMENT_ID}/receipt.json"
AGREEMENT_BUILDER = "scripts/build_slurp_intent_exemplar_agreement.py"
CONTENT_BUILDER = "scripts/build_slurp_query_content_derivative.py"

PERCEPTION = ("knowledge_stores", "intent-boundaries", "phase_supply", "perception")
SOLVER = ("knowledge_stores", "train-exemplars", "phase_supply", "solver")

TRAIN_SCORER = "slurp-slu-official-projected-v3-train"
SEALED_TRAIN_SCORER = "slurp-slu-official-train"
READ_SEEDS = "1249110493,1249110494,1249110495,1249110496,1249110497"


# ---- names --------------------------------------------------------------------------------------
def chunk_base(k: int) -> str:
    return f"{FAMILY}-c{k:02d}"


def names(k: int | None, *, smoke: bool = False, base: bool = False) -> dict:
    """Every identity of chunk ``k`` (or its four-row smoke, or the never-flown FILLER BASE)."""

    if base:
        tag = f"{FAMILY}-base"
        package_tag = tag
    else:
        if not isinstance(k, int) or k < 1 or k > 99:
            raise ValueError("a chunk index is an integer 1..99")
        package_tag = chunk_base(k)
        tag = package_tag + ("-smoke-4" if smoke else "")
    upper = tag.upper()
    return {
        "chunk": k,
        "smoke": smoke,
        "base": base,
        "tag": tag,
        "cell": f"slurp-native-stage3-{tag}-v1",
        "baseline": f"slurp-native-stage3-{tag}-baseline-v1",
        "run": f"SAEA-SLURP-STAGE3-{upper}-V1",
        "fit_run": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
        "gen_attempt": f"attempt-slurp-native-stage3-{tag}-generation-v1",
        "fit_attempt": f"attempt-slurp-native-stage3-{tag}-fit-v1",
        "package": f"slurp-stage3-{package_tag}-v1",
        "readiness_dir": f"docs/readiness/{FAMILY_DATE}-slurp-stage3-{package_tag}-v1",
        "preregistration": f"docs/readiness/{FAMILY_DATE}-slurp-stage3-{package_tag}-v1-preregistration.md",
        "decision_id": f"slurp-stage3-{package_tag}-admission-v1",
        "decision_relpath": f"coordination/slurp-stage3-{package_tag}-v1/root-admission-v1.json",
        "campaign": f"configs/campaign/slurp-native-stage3-{package_tag}-v1.json",
        "roster": f"docs/receipts/rosters/slurp-stage3-{tag}-v1.json",
        "roster_id": f"SLURP-STAGE3-{upper}-V1",
        "plan_prefix": "smoke-generation" if smoke else "generation",
        "fit_plan_prefix": "smoke-fit" if smoke else "fit",
        "read_id": f"SAEA-SLURP-STAGE3-{upper}-READ-V1",
        "flight_commit_file": (None if base else f"/home/chao/filler-flight-commit-c{k:02d}.txt"),
    }


def parse_chunks(spec: str) -> list[int]:
    """``"1-6"`` / ``"3"`` / ``"1,3,5-6"`` -> sorted unique chunk indices."""

    out: set[int] = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    if not out or min(out) < 1 or max(out) > 99:
        raise ValueError(f"bad chunk spec {spec!r}")
    return sorted(out)


# ---- io -----------------------------------------------------------------------------------------
def _abs(path: str | Path) -> Path:
    return Path(path) if os.path.isabs(str(path)) else REPO_ROOT / path


def rd(path: str | Path) -> str:
    return io.open(_abs(path), encoding="utf-8", newline="").read()


def rjson(path: str | Path) -> dict:
    return json.loads(rd(path))


def wr(path: str | Path, text: str) -> str:
    target = _abs(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str | Path, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(_abs(path), "rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def utterance_of(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) < 3:
        raise ValueError(f"sample id {sample_id!r} carries no utterance identity")
    return ":".join(parts[:3])


# ---- budgets ------------------------------------------------------------------------------------
def budgets(rows: int, audio_seconds: float, *, smoke: bool) -> dict:
    """The chunk's caps: ROLL-2's own arithmetic rescaled to ``rows`` -- ceiling 19 contacts per row, FIT x4,
    repeated speech ceil(audio x 19), GPU hours ROLL-2's 12.0 per 1,080 rows (1.0 for a smoke) -- plus the
    expectation at ROLL-2's measured rate (8,996 contacts / 1,080 rows, 8,558 s / 1,080 rows)."""

    generation = rows * CONTACTS_PER_ROW_CEILING
    return {
        "rows": rows,
        "audio_seconds": round(audio_seconds, 6),
        "generation_calls_cap": generation,
        "fit_endpoint_calls_cap": generation * FIT_MULTIPLIER,
        "native_task_contract_calls_cap": 0,
        "repeated_speech_audio_seconds_cap": math.ceil(audio_seconds * CONTACTS_PER_ROW_CEILING),
        "gpu_hours_fit_inclusive": 1.0 if smoke else round(ROLL2_GPU_HOURS_CAP * rows / ROLL2_ROWS, 4),
        "official_complete_scoring_jobs": 0 if smoke else 1,
        "expected_contacts": round(rows * ROLL2_CONTACTS / ROLL2_ROWS),
        "expected_wall_minutes": round(rows * ROLL2_WALL_SECONDS / ROLL2_ROWS / 60.0, 1),
    }


# ---- derivation ---------------------------------------------------------------------------------
def replace_exact(node, mapping: dict):
    """Replace every string VALUE equal to a mapping key (never a substring): ids move, prose does not;
    prose is rewritten explicitly by the caller."""

    if isinstance(node, dict):
        return {key: replace_exact(value, mapping) for key, value in node.items()}
    if isinstance(node, list):
        return [replace_exact(value, mapping) for value in node]
    if isinstance(node, str) and node in mapping:
        return mapping[node]
    return node


def count_exact(node, needle: str) -> int:
    if isinstance(node, dict):
        return sum(count_exact(value, needle) for value in node.values())
    if isinstance(node, list):
        return sum(count_exact(value, needle) for value in node)
    return int(node == needle)


def id_mapping(n: dict) -> dict:
    parent = ROLL2["smoke" if n["smoke"] else "arm"]
    return {
        parent["run"]: n["run"],
        parent["fit_run"]: n["fit_run"],
        parent["gen_attempt"]: n["gen_attempt"],
        parent["fit_attempt"]: n["fit_attempt"],
        parent["baseline"]: n["baseline"],
        parent["cell"]: n["cell"],
        f"saea-{parent['cell']}": f"saea-{n['cell']}",
        ROLL2_DATASET: DATASET_FRAGMENT,
        ROLL2_SPLIT_ID: DATASET_SPLIT_NAME,
    }


def get_path(document: dict, path: tuple):
    node = document
    for key in path:
        node = node[key]
    return node


BOUNDARY_SIGNAL = (
    "speech: complete original TRAIN Fold B recordings represented by sealed full-utterance segments in "
    "the intent-boundary retrieval dimension; segment identities are preserved and no flattening, "
    "re-encoding, transcript, answer or future turn enters this query."
)
CONTENT_SIGNAL = (
    "speech: complete original TRAIN Fold B recordings represented by the sealed full-utterance speech "
    "vector of the row's own recording, in the content retrieval dimension; flattened by "
    "scripts/build_slurp_query_content_derivative.py from the sealed intent-boundary full-utterance "
    "SEGMENT vectors (one segment per row, dimension renamed intent-boundary to content, every float "
    "byte-identical to the parent; provenance beside the file) -- the exact transform cell ROLL-2's Fold A "
    "pin was built with -- because docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md "
    "establishes intent-boundary as an alias of the content embedding space; no flattening of MEANING, "
    "re-encoding, transcript, answer or future turn enters this query."
)
AGREEMENT_SIGNAL = (
    "derived: the share of this row's own top-20 sealed TRAIN-exemplar recall whose frozen build-time "
    "task_target equals each boundary intent, self-excluded by the row's utterance identity and "
    "normalised to 1. Speech-keyed by construction -- the recall it summarises is the row's own sealed "
    "TRAIN Fold B speech vector against the frozen pool -- and gold-free: the key is a released store "
    "property, never a label, transcript or future turn. Built model-free by "
    "scripts/build_slurp_intent_exemplar_agreement.py from the committed FILLER BASE cell "
    "slurp-native-stage3-filler-fold-b-base-v1 with zero model, server, encoder, embedder, scorer, "
    "network and GPU contacts; receipt beside the artifact."
)


def what_this_is(n: dict, rows: int) -> str:
    if n["base"]:
        return (
            "The FILLER BASE (owner decision 162): cell ROLL-2's grouped-Solver form re-pointed from TRAIN Fold A to "
            f"the whole {rows}-row filler roster (TRAIN Fold B) at w_agree 0.0 with no agreement_source. NEVER FLOWN "
            "(allowed stage: check only, readiness held, no ledger row, no budget authority). It exists for two "
            "reasons only: it is the committed source identity scripts/build_slurp_intent_exemplar_agreement.py "
            "builds the filler roster's own exemplar-intent agreement table from (the vote is formed through the "
            "same seam the flight runs at the Solver), and it is the roster-move reference the chunk cells' "
            "composed-diff proof is read against."
        )
    what = (
        f"Filler chunk c{n['chunk']:02d} (owner decision {OWNER_DECISION}): a sealed five-sample rollout pool of the "
        "CURRENT BEST SLURP system -- the locked PLAN plan plus the agreement term retained into COMP-1 (owner "
        "decision 161: w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell "
        "ROLL-2's grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at min_support 3), "
        f"on {rows} TRAIN Fold B rows outside Fold A, every evaluation roster and every knowledge source. The pool is "
        "the rollout substrate of the training-free RL inner loop (sealed-credit-system-policy-v1); DESCRIPTIVE by "
        "construction and never an admission cell."
    )
    if n["smoke"]:
        what = "Four-row structural form smoke of " + what[0].lower() + what[1:]
    return what


def derive_baseline(n: dict, *, prepared: dict, rows: int, caps: dict, agreement: bool,
                    roster_relpath: str, roster_sha: str) -> tuple[str, dict]:
    """ROLL-2's baseline fragment (arm or smoke) re-pointed to TRAIN Fold B, plus -- for a chunk -- AGREE's
    agreement pins. Nothing else moves. Returns ``(parent raw text, derived document)``."""

    parent = ROLL2["smoke" if n["smoke"] else "arm"]
    raw = rd(f"configs/baseline/{parent['baseline']}.json")
    document = json.loads(raw)
    for needle in (parent["fit_run"], parent["fit_attempt"]):
        if count_exact(document, needle) != 1:
            raise SystemExit(f"the ROLL-2 baseline does not carry {needle!r} exactly once")
    document = replace_exact(document, id_mapping(n))

    perception = get_path(document, PERCEPTION)
    solver = get_path(document, SOLVER)
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}:
        raise SystemExit("ROLL-2's boundary rank weights are not the flown identity")
    if perception["k"] != 8 or perception["tau"] != 0.0 or perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("ROLL-2's boundary k / tau / fuse are not the flown 8 / 0.0 / 8-1-8")
    if "agreement_source" in perception or "agreement_source" in solver:
        raise SystemExit("ROLL-2 declares an agreement_source; refusing")

    # ---- ROSTER PINS: TRAIN Fold A -> TRAIN Fold B ----------------------------------------------
    perception["query_source"] = {
        "embedded_signal": BOUNDARY_SIGNAL,
        "kind": "sealed-segment-vectors",
        "relpath": BOUNDARY_QUERY["relpath"],
        "sha256": BOUNDARY_QUERY["sha256"],
        "tool_contact_ledger_row": BOUNDARY_QUERY["tool_contact_ledger_row"],
    }
    solver["query_source"] = {
        "embedded_signal": CONTENT_SIGNAL,
        "kind": "sealed-vectors",
        "relpath": CONTENT_QUERY,
        "sha256": prepared["content_query_sha256"],
        "tool_contact_ledger_row": BOUNDARY_QUERY["tool_contact_ledger_row"],
    }
    receipts = document["preparation_source_receipts"]
    alias = [r for r in receipts if r["relpath"] == FOLD_A_ALIAS]
    roster = [r for r in receipts if r["relpath"] == ROLL2_ROSTER]
    if len(alias) != 1 or len(roster) != 1:
        raise SystemExit("ROLL-2's preparation_source_receipts do not carry exactly one Fold A alias and one roster")
    alias[0].update({"relpath": FOLD_B_ALIAS["relpath"], "sha256": FOLD_B_ALIAS["sha256"]})
    roster[0].update({"relpath": roster_relpath, "sha256": roster_sha})
    receipts.append({"relpath": FOLD_B_ENCODE_RECEIPT["relpath"], "root": "data", "sha256": FOLD_B_ENCODE_RECEIPT["sha256"]})
    receipts.append({"relpath": CONTENT_QUERY_PROVENANCE, "root": "data", "sha256": prepared["content_query_provenance_sha256"]})

    # ---- AGREEMENT PINS (AGREE, owner decision 161) ---------------------------------------------
    if agreement:
        perception["k"] = 60
        perception["rank_weights"] = {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0}
        perception["agreement_source"] = {
            "embedded_signal": AGREEMENT_SIGNAL,
            "kind": "sealed-agreement",
            "relpath": AGREEMENT,
            "sha256": prepared["agreement_sha256"],
            "tool_contact_ledger_row": PREPARE_ROW,
        }
        receipts.append({"relpath": AGREEMENT_RECEIPT, "root": "data", "sha256": prepared["agreement_receipt_sha256"]})

    # ---- bookkeeping -----------------------------------------------------------------------------
    document.pop("prepared_phase_supply", None)  # item E16: the flip mints this cell's own
    document["native_contact_fit"]["contact_cap"] = caps["fit_endpoint_calls_cap"]
    document["what_this_is"] = what_this_is(n, rows)
    document["what_the_train_exemplars_store_is"] = (
        "Unchanged from cell ROLL-2 and the locked PLAN plan: the top-20 TRAIN construction-pool exemplars of "
        "size-pool-annotated-exemplars (9,354 facets; every SLURP TRAIN utterance except TRAIN Fold A and TRAIN "
        "Fold B, so no filler row can recall itself) recalled by cosine against this row's OWN sealed TRAIN Fold B "
        "speech vector, identity rank, saea-fuse-supplyfilter-v1 at m=c=top_l=20, delivered to the SOLVER phase as "
        "typed content blocks. Only the query file moves (TRAIN Fold A -> TRAIN Fold B); the store, its release and "
        "its snapshot are byte-identical."
    )
    filled = [
        ("knowledge_stores.intent-boundaries.phase_supply.perception.query_source",
         "TRAIN Fold A -> TRAIN Fold B: the sealed Fold B speech-query encoding "
         "SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1 through its model-free query-dimension alias "
         "SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-B-ALIAS-V1. Nothing is newly encoded, promoted or released."),
        ("knowledge_stores.train-exemplars.phase_supply.solver.query_source",
         f"the Fold B content-dimension query derivative, built model-free by {CONTENT_BUILDER} (ledger row "
         f"{PREPARE_ROW}); every float byte-identical to the Fold B segment vectors."),
        ("preparation_source_receipts",
         "ROLL-2's receipts with the Fold A alias and roster replaced by the Fold B alias and this cell's own "
         "roster receipt, plus the Fold B encode receipt and the content derivative's provenance"
         + (", plus the agreement table's receipt." if agreement else ".")),
        ("prepared_phase_supply",
         "REMOVED: the readiness flip mints this cell's OWN first-phase supply under its own run id (item E16)."),
        ("native_contact_fit",
         f"new FIT spend identities {n['fit_run']} / {n['fit_attempt']}, cap {caps['fit_endpoint_calls_cap']}."),
    ]
    if agreement:
        filled.append((
            "knowledge_stores.intent-boundaries.phase_supply.perception",
            "AGREE's agreement pins (owner decision 161): k 8 -> 60 (the recall width; the delivered width stays "
            f"fuse_coverage 8-1-8), w_agree 0.0 -> 1.0, agreement_source = this roster's own table {AGREEMENT}.",
        ))
    document["stage3_placeholders_filled"] = [
        {"by": f"{FAMILY_DATE} filler derivation (owner decision {OWNER_DECISION}): {text}", "filled": FAMILY_DATE, "path": path}
        for path, text in filled
    ]
    leftover = [value for value in _strings(document) if "fold-a" in value.lower()]
    if leftover:
        raise SystemExit(f"a Fold A identifier survived the derivation: {leftover[:3]}")
    return raw, document


def _strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)
    elif isinstance(node, str):
        yield node


# ---- the composed-diff rule ---------------------------------------------------------------------
#: Composed paths the ROLL-2 -> filler derivation may move, by reason. Anything else is a refusal.
AGREEMENT_PATHS = (
    "knowledge_stores.intent-boundaries.phase_supply.perception.k",
    "knowledge_stores.intent-boundaries.phase_supply.perception.rank_weights.w_agree",
    "knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source.",
)
ROSTER_PATHS = (
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.",
    "population.",
    "populations",
    "split_id",
    "preparation_source_receipts",
)
BOOKKEEPING_PATHS = (
    "native_contact_fit.",
    "prepared_phase_supply.",
    "cells",
    "experiment_id",
    "fragment_kind",
    "date",
    "purpose",
    "execution_plan.",
    "family_budget.",
    "generation_budget.",
    "what_this_is",
    "what_the_train_exemplars_store_is",
    "stage3_placeholders_filled",
    "stage3_algorithm.note",
    "failure_policy",
)


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _matches(path: str, prefixes: tuple) -> bool:
    return any(path == p.rstrip(".") or path.startswith(p if p.endswith(".") else p + ".") or path == p for p in prefixes)


def classify_composed_diff(parent_values: dict, mine_values: dict, dataset_keys: set) -> dict:
    """Every composed path that differs between ROLL-2 and a filler cell, classified. The dataset
    fragment's own keys move as a whole with the roster (TRAIN Fold A view -> TRAIN Fold B view)."""

    a, b = flatten(parent_values), flatten(mine_values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    out = {"agreement": [], "roster": [], "bookkeeping": [], "other": [], "all": changed}
    for path in changed:
        if _matches(path, AGREEMENT_PATHS):
            out["agreement"].append(path)
        elif _matches(path, ROSTER_PATHS) or path.split(".", 1)[0] in dataset_keys:
            out["roster"].append(path)
        elif _matches(path, BOOKKEEPING_PATHS):
            out["bookkeeping"].append(path)
        else:
            out["other"].append(path)
    return out


def expected_receipts(parent_receipts: list, *, roster_relpath: str, roster_sha: str, prepared: dict,
                      agreement: bool) -> list:
    """ROLL-2's preparation_source_receipts with exactly the filler replacements and additions."""

    out = []
    for pin in parent_receipts:
        pin = dict(pin)
        if pin["relpath"] == FOLD_A_ALIAS:
            pin.update({"relpath": FOLD_B_ALIAS["relpath"], "sha256": FOLD_B_ALIAS["sha256"]})
        elif pin["relpath"] == ROLL2_ROSTER:
            pin.update({"relpath": roster_relpath, "sha256": roster_sha})
        out.append(pin)
    out.append({"relpath": FOLD_B_ENCODE_RECEIPT["relpath"], "root": "data", "sha256": FOLD_B_ENCODE_RECEIPT["sha256"]})
    out.append({"relpath": CONTENT_QUERY_PROVENANCE, "root": "data", "sha256": prepared["content_query_provenance_sha256"]})
    if agreement:
        out.append({"relpath": AGREEMENT_RECEIPT, "root": "data", "sha256": prepared["agreement_receipt_sha256"]})
    return out
