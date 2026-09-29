#!/usr/bin/env python3
"""Derive cell E4-1 -- the core-native targeted re-listen on TRAIN Fold A (owner decision 185;
docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md with its section 8
coordinator rulings) -- from the RETAINED AGREE arm fragments (decision 58: script-derived
registrations).

THE BASE CHANGES, AND NOTHING ELSE MOVES.

1. ``policy``: ``phase-native-candidates-review-revise-v1`` (ceiling 11) ->
   ``phase-native-candidates-review-revise-relisten-v1`` (ceiling 17 = 11 + 2 x 3, the relisten
   stage's own additive term ``rails.relisten.relisten_extra_ceiling(3)``). The two fragments differ
   ONLY in ``program_id`` and ``max_contacts``; verified here leaf by leaf, anything else refuses.
2. ``native_episode.relisten``: the post-accept targeted re-listen block, exactly the key set
   ``rails.relisten.RELISTEN_CONFIG_KEYS`` requires -- policy ``saea-obs-targeted-relisten-v1``,
   ``max_slots_per_row`` 3, ``value_max_words`` 8, ``delivery`` ``shadow``, ``blind_template_id``
   ``slurp_relisten_blind_v1``, ``confirm_template_id`` ``slurp_relisten_confirm_v1`` -- parsed
   here through ``rails.relisten.parse_relisten`` so a malformed block refuses before any write.

Shadow delivery (ruling 5): the DELIVERED answer is the AGREE form's answer; the relisten stage
runs after the deliver normaliser, never mutates the delivered text, and seals a
``saea-relisten-v1`` receipt from which two shadow columns are rendered offline (ruling 2).

Bookkeeping that follows from (1)/(2): the run / attempt / FIT ids, ``native_contact_fit.
contact_cap`` (rows x 17 x 4, the AGREE arithmetic at the new ceiling), the family budget and
execution plan (rows x 17 generation contacts, ceil(audio x 17) speech seconds, GPU hours scaled by
17 / 11), prose, and ``prepared_phase_supply`` DROPPED so the flip mints this cell's own
first-phase supply under its own run id (item E16); the arm's minted output must carry the AGREE
arm's digest (the Perception supply is upstream of the program id and of the post-accept stage).

THE SMOKE ROSTER (the required 4-row dry run, spec section 6 step 2). The smoke must exercise the
blind AND the forced-choice path, so it does NOT reuse the AGREE smoke's first four rows (they
carry 1, 1, 0 and 1 delivered entities in the sealed AGREE arm and were entity-stable across the
AGREE arm and its wave A/A re-fly, so a confirm contact was unlikely on any of them). Its four rows
are the FIRST FOUR Fold A roster rows (roster order) whose sealed AGREE answer delivered >= 3
entities AND whose delivered entity set differed between the sealed AGREE arm and its request-form
re-fly SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 -- a model-free, gold-free rule over sealed model
outputs (counts and set inequality only; no value is printed or persisted), measured by
``scripts/flights/e4/e4_cost_measure.py`` and re-checked here against its output file when
``--data-root`` holds it. Up to 3 blind contacts per row (12 on the smoke) and entity instability
make a disagreement -- hence a confirm contact -- likely; the smoke's pass condition requires at
least one fired confirm (preregistration).

TWO CELLS: the arm on TRAIN Fold A 1,080 and its four-row smoke, plus the arm's one-cell campaign
plan. No A/A cell: the read is the same flight's shadow columns against its delivered column.

This script writes CONFIG ONLY. It performs no contact, writes no ledger row, mints no receipt and
flips nothing.

    python scripts/flights/e4/derive_slurp_e4_cells.py --date 2026-09-29 --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

AGREE_ARM_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
DATASET_FRAGMENT = "configs/dataset/slurp-speech-native-evo-fold-a-1080.json"

BASE_PROGRAM = "phase-native-candidates-review-revise-v1"
NEW_PROGRAM = "phase-native-candidates-review-revise-relisten-v1"
BASE_CEILING, NEW_CEILING = 11, 17
FIT_ENDPOINTS_PER_CONTACT = 4  # the AGREE arithmetic: contact_cap = rows x ceiling x 4

#: The registered relisten block (owner decision 185; field names are rails.relisten.RELISTEN_CONFIG_KEYS).
RELISTEN_BLOCK = {
    "policy": "saea-obs-targeted-relisten-v1",
    "max_slots_per_row": 3,
    "value_max_words": 8,
    "delivery": "shadow",
    "blind_template_id": "slurp_relisten_blind_v1",
    "confirm_template_id": "slurp_relisten_confirm_v1",
}

#: The smoke roster (rule in the module docstring; measured by e4_cost_measure.py).
SMOKE_IDS = [
    "slurp:train:000215:audio-1502200839",
    "slurp:train:001461:audio-1489672182",
    "slurp:train:002697:audio-1501756377",
    "slurp:train:003384:audio--1505406264",
]
COST_MEASURE = "analysis/SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COST-MEASURE-V1/cost-measure-v1.json"

ARM_NAMES = {
    "run": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1",
    "fit": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1",
    "gen_attempt": "attempt-slurp-native-stage3-relisten-fold-a-generation-v1",
    "fit_attempt": "attempt-slurp-native-stage3-relisten-fold-a-fit-v1",
    "baseline": "slurp-native-stage3-relisten-fold-a-baseline-v1",
    "experiment": "slurp-native-stage3-relisten-fold-a-v1",
    "kind": "saea-slurp-native-stage3-relisten-fold-a-v1",
}
SMOKE_NAMES = {
    "run": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-V1",
    "fit": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-FIT-V1",
    "gen_attempt": "attempt-slurp-native-stage3-relisten-fold-a-smoke-4-generation-v1",
    "fit_attempt": "attempt-slurp-native-stage3-relisten-fold-a-smoke-4-fit-v1",
    "baseline": "slurp-native-stage3-relisten-fold-a-smoke-4-baseline-v1",
    "experiment": "slurp-native-stage3-relisten-fold-a-smoke-4-v1",
    "kind": "saea-slurp-native-stage3-relisten-fold-a-smoke-4-v1",
}

THE_CHANGE = (
    "THE BASE CHANGE (the only one besides the relisten block): policy " + BASE_PROGRAM + " (ceiling 11) -> "
    + NEW_PROGRAM + " (ceiling 17 = 11 + 2 x max_slots_per_row 3; the two program fragments differ only in "
    "program_id and max_contacts; the Solver stays uncited). THE RELISTEN BLOCK: native_episode.relisten "
    + json.dumps(RELISTEN_BLOCK, sort_keys=True) + " -- a post-accept stage after the deliver normaliser: for up "
    "to 3 delivered entities per row, in delivery order, a BLIND contact (packet + decided intent + slot type, "
    "never the delivered value) and, when the blind value is canonically different, unheard or unparsed, a "
    "FORCED-CHOICE contact (delivered value vs the blind value or the unheard sentinel, order fixed by "
    "sha256(sample_id, slot type); the decided intent only, never Perception's candidates). SHADOW DELIVERY: the "
    "delivered answer is the AGREE form's own and is never mutated; the saea-relisten-v1 receipt is sealed per "
    "row and two shadow columns (relisten-replace-only, relisten-replace-drop-unheard) are rendered offline. The "
    "delivered path's request bytes are the AGREE arm's EXCEPT the two program-identity fields the switch moves "
    "(the program id inside quoted prior contact ids; remaining_model_contacts, +6) -- proven by "
    "scripts/flights/e4/e4_shadow_proof.py. Nothing else moves: roster (arm), geometry, session, role graph, "
    "max_revisions 1, the agreement term and its sealed table, every knowledge store and pin, every template, the "
    "deliver normaliser and the scorers are the AGREE arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: E4-1 is a post-accept OBSERVATION "
    "node (owner decisions 180 and 185) -- one pre-declared, model-free trigger and acceptance rule over two "
    "core-native re-listen contacts per targeted entity, read as two offline shadow columns against the same "
    "flight's delivered column -- with no rollout pool, no per-sample credit, no update operator, no evolving "
    "store and no selection among sampled answers (so not inference-time-verification-v1, whose selection "
    "operator commits one of several sampled answers). The design's section 6 names a dedicated "
    "STAGE3_ALGORITHMS label; none is registered on this branch, so the cell is labelled 'none' with this note."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.update(flatten(value, f"{prefix}[{index}]."))
    else:
        out[prefix[:-1]] = node
    return out


def check_program_fragments() -> None:
    base = flatten(json.loads(rd(f"configs/policy/{BASE_PROGRAM}.json")))
    new = flatten(json.loads(rd(f"configs/policy/{NEW_PROGRAM}.json")))
    moved = sorted(k for k in set(base) | set(new) if base.get(k, "<absent>") != new.get(k, "<absent>"))
    if moved != ["max_contacts", "program_id"]:
        raise SystemExit(f"{NEW_PROGRAM} differs from {BASE_PROGRAM} beyond program_id/max_contacts: {moved}")
    if (base["max_contacts"], new["max_contacts"]) != (BASE_CEILING, NEW_CEILING):
        raise SystemExit("unexpected program ceilings")


def check_relisten_block() -> None:
    from speech_aware_evidence_acquisition.rails.relisten import (  # noqa: PLC0415
        RELISTEN_CONFIG_KEYS, parse_relisten, relisten_extra_ceiling,
    )

    if set(RELISTEN_BLOCK) != set(RELISTEN_CONFIG_KEYS):
        raise SystemExit(f"relisten block keys {sorted(RELISTEN_BLOCK)} != {sorted(RELISTEN_CONFIG_KEYS)}")
    parsed = parse_relisten(RELISTEN_BLOCK)
    if BASE_CEILING + relisten_extra_ceiling(parsed.max_slots_per_row) != NEW_CEILING:
        raise SystemExit("ceiling 17 is not 11 + relisten_extra_ceiling(max_slots_per_row)")


def substitutions(names: dict, parent: dict) -> list[tuple[str, str]]:
    return [(parent[k], names[k]) for k in ("fit", "run", "gen_attempt", "fit_attempt", "baseline", "experiment", "kind")]


AGREE_ARM = {
    "run": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "fit": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1",
    "gen_attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
    "fit_attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1",
    "baseline": "slurp-native-stage3-agree-w1-fold-a-baseline-v1",
    "experiment": "slurp-native-stage3-agree-w1-fold-a-v1",
    "kind": "saea-slurp-native-stage3-agree-w1-fold-a-v1",
}
AGREE_SMOKE = {
    "run": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "fit": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1",
    "gen_attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1",
    "fit_attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1",
    "baseline": "slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1",
    "experiment": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1",
    "kind": "saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1",
}


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    # longest first, so an id never rewrites inside a longer id
    for old, new in sorted(pairs, key=lambda p: -len(p[0])):
        text = text.replace(old, new)
    return text


def derive_baseline(parent: str, out: str, pairs, *, rows: int, what_this_is: str) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    if document.get("policy") != BASE_PROGRAM:
        raise SystemExit(f"the AGREE parent's policy is {document.get('policy')!r}, not {BASE_PROGRAM}")
    document["policy"] = NEW_PROGRAM  # THE ONE BASE CHANGE
    episode = document["native_episode"]
    if "relisten" in episode:
        raise SystemExit("the AGREE parent already carries native_episode.relisten")
    episode["relisten"] = dict(RELISTEN_BLOCK)  # THE RELISTEN BLOCK
    if parent_doc["native_contact_fit"]["contact_cap"] != rows * BASE_CEILING * FIT_ENDPOINTS_PER_CONTACT:
        raise SystemExit("the AGREE parent's FIT cap is not rows x 11 x 4")
    document["native_contact_fit"]["contact_cap"] = rows * NEW_CEILING * FIT_ENDPOINTS_PER_CONTACT
    document["what_this_is"] = what_this_is
    for key in parent_doc:
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit"):
            continue
        if json.dumps(parent_doc[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the registered change")
    reduced = json.loads(json.dumps(document["native_episode"]))
    reduced.pop("relisten")
    if reduced != parent_doc["native_episode"]:
        raise SystemExit("native_episode moved beyond the relisten block")
    wr(out, dump_like(raw, document))


def dataset_audio() -> dict[str, float]:
    return {i["sample_id"]: float(i["audio_seconds"]) for i in json.loads(rd(DATASET_FRAGMENT))["items"]}


def budgets(rows: int, audio_new: float, audio_parent: float, parent: dict) -> tuple[dict, dict]:
    fam = dict(parent["family_budget"])
    if fam["generation_calls_cap"] != rows * BASE_CEILING:
        raise SystemExit("the AGREE parent's generation cap is not rows x 11")
    if fam["repeated_speech_audio_seconds_cap"] != math.ceil(audio_parent * BASE_CEILING - 1e-9):
        raise SystemExit("the AGREE parent's speech cap is not ceil(audio x 11)")
    gpu = round(fam["gpu_hours_fit_inclusive"] * NEW_CEILING / BASE_CEILING, 1) if rows > 4 else fam["gpu_hours_fit_inclusive"]
    fam.update({
        "generation_calls_cap": rows * NEW_CEILING,
        "fit_endpoint_calls_cap": rows * NEW_CEILING * FIT_ENDPOINTS_PER_CONTACT,
        "repeated_speech_audio_seconds_cap": math.ceil(audio_new * NEW_CEILING - 1e-9),
        "native_task_contract_calls_cap": fam["native_task_contract_calls_cap"] + rows * (NEW_CEILING - BASE_CEILING),
        "gpu_hours_fit_inclusive": gpu,
    })
    plan = dict(parent["execution_plan"])
    plan.update({"planned_model_calls": fam["generation_calls_cap"], "planned_gpu_hours": gpu,
                 "planned_speech_audio_seconds": fam["repeated_speech_audio_seconds_cap"]})
    return fam, plan


def derive_experiment(parent: str, out: str, pairs, args, *, purpose: str, readiness_reason: str,
                      campaign: bool, audio: dict[str, float], smoke_ids: list[str] | None,
                      failure_policy: str | None = None, expected_blind: int) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    rows = int(document["population"]["count"])
    parent_ids = (parent_doc.get("populations") or [{}])[0].get("ids")
    audio_parent = sum(audio[s] for s in parent_ids) if parent_ids else sum(audio.values())
    if smoke_ids is not None:
        from speech_aware_evidence_acquisition.core.config import compose  # noqa: PLC0415
        from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: PLC0415

        cell = parent_doc["cells"][0]
        carrier = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"],
                          Path(parent).stem).values["carrier_lock_key"]
        if split_identity_hash(prefixed(carrier, parent_ids)) != parent_doc["population"]["split_identity_hash"]:
            raise SystemExit("cannot reproduce the AGREE smoke's split identity hash")
        if len(smoke_ids) != 4 or len(set(smoke_ids)) != 4 or not set(smoke_ids) <= set(audio):
            raise SystemExit("the smoke roster is not four distinct Fold A rows")
        document["populations"] = [{"dataset_fragment": document["populations"][0]["dataset_fragment"],
                                    "ids": list(smoke_ids)}]
        document["population"]["split_identity_hash"] = split_identity_hash(prefixed(carrier, smoke_ids))
        document["population"]["decision_population"] = (
            "Four rows of the unchanged TRAIN Fold A roster chosen to exercise the blind and forced-choice relisten "
            "contacts: the first four rows in roster order whose sealed AGREE answer delivered >= 3 entities and "
            "whose delivered entity set differed between the sealed AGREE arm and its wave A/A re-fly (a model-free, "
            "gold-free rule over sealed outputs; scripts/flights/e4/e4_cost_measure.py)."
        )
        audio_new = sum(audio[s] for s in smoke_ids)
    else:
        audio_new = sum(audio.values())
    document["date"] = args.date
    document["purpose"] = purpose
    if failure_policy is not None:
        document["failure_policy"] = failure_policy
    else:
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    family, plan = budgets(rows, audio_new, audio_parent, parent_doc)
    document["family_budget"] = family
    document["execution_plan"] = plan
    if "generation_budget" in document:
        target = document["generation_budget"].get("target")
        document["generation_budget"] = {
            "cap": rows * NEW_CEILING,
            "definition": (
                f"The AGREE role graph (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1) under program "
                f"{NEW_PROGRAM}: the native_episode.relisten block raises the bounded graph ceiling by "
                f"2 x max_slots_per_row = 6 to 17 contacts per row (rails.native_episode_config, item E4), so "
                f"{rows:,} x 17 = {rows * NEW_CEILING:,} is the exact program maximum. The sealed AGREE arm realised "
                f"4.060 contacts per row; the relisten stage adds min(delivered entities, 3) blind contacts per row "
                f"({expected_blind:,} over these rows on the sealed AGREE answers) plus one forced-choice contact per "
                "disagreeing, unheard or unparsed blind contact (not predictable; bounded by the blind count). The "
                "budget is RUN-CUMULATIVE across every attempt of this run id."
            ),
            "target": (round(4.060 * rows) + 2 * expected_blind) if isinstance(target, int) else target,
        }
    cell = document["cells"][0]
    agreement = [r for r in cell["readiness"]["requirements"]
                 if r.get("kind") == "preparation" and "AGREEMENT" in str(r.get("relpath"))]
    if len(agreement) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table requirement")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement, "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out, dump_like(raw, document))


def check_smoke_selection(data_root: str | None) -> str:
    if not data_root:
        return "not-checked (no --data-root)"
    path = Path(data_root) / COST_MEASURE
    if not path.is_file():
        return f"not-checked ({COST_MEASURE} absent; run scripts/flights/e4/e4_cost_measure.py)"
    measured = json.loads(path.read_text(encoding="utf-8"))["smoke_selection"]["sample_ids"]
    if measured != SMOKE_IDS:
        raise SystemExit(f"the measured smoke selection {measured} differs from the registered {SMOKE_IDS}")
    return "matches the cost measure"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--arm-blind-contacts", type=int, default=1018,
                        help="sum over the sealed AGREE rows of min(delivered entities, 3) (e4_cost_measure.py)")
    parser.add_argument("--smoke-blind-contacts", type=int, default=12)
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    check_program_fragments()
    check_relisten_block()
    smoke_check = check_smoke_selection(args.data_root)
    audio = dataset_audio()

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(through scripts/flights/e4/e4_flip.sh), which also mints this cell's own first-phase supply under its "
        "own run id (item E16); --allow-output-change must never be passed, and the arm's minted supply must "
        "reproduce the AGREE arm's own first-phase output digest (the Perception supply is upstream of the program "
        "id and of the post-accept stage). Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    written = []
    arm_pairs = substitutions(ARM_NAMES, AGREE_ARM)
    derive_baseline(AGREE_ARM_BASELINE, f"configs/baseline/{ARM_NAMES['baseline']}.json", arm_pairs, rows=1080,
                    what_this_is="Cell E4-1 (owner decision 185): the core-native targeted re-listen as a shadow "
                                 "post-accept stage on the retained AGREE arm. " + THE_CHANGE)
    written.append(f"configs/baseline/{ARM_NAMES['baseline']}.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, f"configs/experiment/{ARM_NAMES['experiment']}.json", arm_pairs, args,
        purpose=(
            "Cell E4-1 on TRAIN Fold A 1,080 (owner decision 185; the E4 v1 design with its section 8 rulings): the "
            "AGREE form delivers its own answer; after the deliver normaliser a post-accept relisten stage re-listens "
            "to up to 3 delivered entities per row (blind value, then a forced choice on disagreement or unheard) and "
            "seals a saea-relisten-v1 receipt without touching the delivered text. Two shadow columns rendered offline "
            "from the sealed receipts -- (a) relisten-replace-only, (b) relisten-replace-drop-unheard -- are each read "
            "against the same flight's delivered column: official pooled SLU-F1 (micro) primary, intent identical by "
            "construction (tested as a guard). Claim ceiling 'nominated'. " + THE_CHANGE + " Development numbers only "
            "(owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an "
            "admission entry."
        ),
        readiness_reason=(
            "Cell E4-1 registered before contact on " + args.date + " from the retained AGREE arm fragments by script "
            "(decision 58) with the program switched to its 17-ceiling relisten twin and a native_episode.relisten "
            "block (owner decision 185). No cross-flight comparator: the paired read is within this flight (two "
            "shadow columns against the delivered column); the sealed AGREE arm " + AGREE_RUN + " is context only."
            + held
        ),
        campaign=True, audio=audio, smoke_ids=None, expected_blind=args.arm_blind_contacts,
    )
    written.append(f"configs/experiment/{ARM_NAMES['experiment']}.json")

    smoke_pairs = substitutions(SMOKE_NAMES, AGREE_SMOKE)
    derive_baseline(AGREE_SMOKE_BASELINE, f"configs/baseline/{SMOKE_NAMES['baseline']}.json", smoke_pairs, rows=4,
                    what_this_is="Four-row charged dry run of cell E4-1 (spec section 6 step 2): the same program "
                                 "switch and the same native_episode.relisten block on four TRAIN Fold A rows chosen "
                                 "to exercise the blind and forced-choice contacts. " + THE_CHANGE)
    written.append(f"configs/baseline/{SMOKE_NAMES['baseline']}.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, f"configs/experiment/{SMOKE_NAMES['experiment']}.json", smoke_pairs, args,
        purpose=(
            "Four-row charged dry run of cell E4-1 (the design's section 6 step 2; a form proof, claims_benefit "
            "false): that the 17-ceiling relisten program loads, that every row with a delivered entity seals a "
            "saea-relisten-v1 receipt whose blind and forced-choice contacts verify under I7l, that at least one "
            "forced-choice contact fires, that the realised contact count equals the sealed receipts' contacts_used "
            "plus the AGREE-form contacts, that nothing truncates, that the delivered text is untouched and that both "
            "shadow columns render with zero intent differences. Never scored for benefit and never read: four rows "
            "can never be evidence of benefit or of harm. " + THE_CHANGE
        ),
        readiness_reason=(
            "Four-row charged dry run of cell E4-1, registered before contact on " + args.date + " from the AGREE "
            "smoke fragments by script (decision 58), on four Fold A rows chosen to exercise both relisten "
            "contacts. Form proof only: no benefit score, no read, no claim." + held.replace(
                "the arm's minted supply must reproduce the AGREE arm's own first-phase output digest",
                "the smoke's minted supply has no AGREE counterpart (its roster is new)")
        ),
        campaign=False, audio=audio, smoke_ids=SMOKE_IDS, expected_blind=args.smoke_blind_contacts,
        failure_policy=(
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell E4-1 and the arm does not open. The resume-recovery clause of owner decision "
            "22 applies to the arm, not to a four-row dry run, which is re-flown whole if it is re-flown at all."
        ),
    )
    written.append(f"configs/experiment/{SMOKE_NAMES['experiment']}.json")
    campaign = {"cells": [{"cell": ARM_NAMES["experiment"], "experiment": ARM_NAMES["experiment"]}],
                "schema": "saea-campaign-plan-v1"}
    wr(f"configs/campaign/{ARM_NAMES['experiment']}.json", json.dumps(campaign, indent=2) + "\n")
    written.append(f"configs/campaign/{ARM_NAMES['experiment']}.json")
    print(json.dumps({"written": written, "relisten": RELISTEN_BLOCK, "smoke_ids": SMOKE_IDS,
                      "smoke_selection_check": smoke_check,
                      "audio_seconds": {"arm": round(sum(audio.values()), 7),
                                        "smoke": round(sum(audio[s] for s in SMOKE_IDS), 7)}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
