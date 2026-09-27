#!/usr/bin/env python3
"""Derive cell W4 -- knowledge-wave item W4, slot conventions (owner decision 164) --
from the RETAINED AGREE arm fragments (decision 58: script-derived registrations).

THE ONE CHANGE. ``knowledge_stores.slot-contracts`` is re-pinned from the released
``slot-contracts-v2`` store (release ``f8e42d4f...``, snapshot ``d5992bd1...``) to the
new ``slot-contracts-w4-v1`` release built model-free by
``scripts/build_slurp_slot_conventions_w4.py`` + ``saea-driver prepare-semantic-knowledge``
(registration ``docs/readiness/2026-09-27-slurp-slot-contracts-w4-preparation-registration-v1.json``),
and the release's two receipts (completion, release) are appended to
``preparation_source_receipts`` so the knowledge pin carries its provenance. The new
store is v2 with 19 cards' ``extraction_cues`` / ``admissible_formats`` extended; every
intent binding, hence every candidate-keyed supply decision and every facet key, is
byte-identical. Nothing else moves: roster, geometry, session, program and its
11-contact ceiling, the agreement term (w_agree 1.0, k 60, fuse 8-1-8) and its sealed
agreement table, the boundary and exemplar stores and their pins, every template, the
deliver normaliser and the scorers are the AGREE arm's, byte for byte.

TWO CELLS: the arm on TRAIN Fold A 1,080 and its four-row form smoke. The in-chain A/A
is NOT derived here: the knowledge wave shares ONE A/A, ``SAEA-SLURP-STAGE3-WAVE1-AA-
FOLD-A-V1``, registered by the coordinator; the arm's ``replicate_run_id`` names it.

Both cells drop ``prepared_phase_supply`` so the flip mints each cell's OWN first-phase
supply under its own run id (item E16). The slot store is not an input to the
first-phase (Perception boundary) supply, so the minted supply must reproduce the AGREE
arm's own first-phase output digest -- the flip's byte-identity check.

This script writes CONFIG ONLY: two baselines and two experiment fragments. It
performs no contact, writes no ledger row, mints no receipt and flips nothing.

    python scripts/flights/w4/derive_slurp_w4_cells.py --date 2026-09-27
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

AGREE_ARM_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"

OLD_STORE = {
    "release": {"relpath": "knowledge/slurp/semantic/slot-contracts-v2/release.json",
                "sha256": "f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b"},
    "snapshot": {"relpath": "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
                 "sha256": "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"},
}
NEW_STORE = {
    "release": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json",
                "sha256": "c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0"},
    "snapshot": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/snapshot.json",
                 "sha256": "51d634cfcb398038377feca89d2783f59a705546390839e7cf4dd7d15ad3b9d6"},
}
NEW_RECEIPTS = [
    {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/completion.json", "root": "data",
     "sha256": "1e71784e1af305dee8ead126449d44081fc3740e32d912a131625ece3897d834"},
    {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json", "root": "data",
     "sha256": "c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0"},
]
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"

ONE_CHANGE = (
    "ONE change against the retained AGREE arm: knowledge_stores.slot-contracts is re-pinned from the "
    "released slot-contracts-v2 store to slot-contracts-w4-v1 (release sha256 "
    + NEW_STORE["release"]["sha256"] + ", snapshot content hash " + NEW_STORE["snapshot"]["sha256"]
    + "), built model-free from the R01-excluded TRAIN exemplar pool by "
    "scripts/build_slurp_slot_conventions_w4.py and saea-driver prepare-semantic-knowledge: the v2 cards "
    "with 19 cards' extraction cues and admissible formats EXTENDED by three kinds of slot convention "
    "mined from TRAIN annotations -- K2 the value vocabulary of closed types (all values) and "
    "semi-closed types (the most frequent values covering at least 90 % of mentions, at most 20), K3 the "
    "annotation scope (which spoken values TRAIN tags as the type and which it usually leaves untagged, "
    "with counts), K4 span-extent rules (which adjacent articles, possessives, modifiers, prepositions "
    "and unit or head words sit inside or outside the value, with counts and schematic minimal pairs). "
    "Every intent binding is byte-identical to v2, so a card still reaches a row only when the row's "
    "candidate intents bind it and the facet keys and candidate-keyed supply do not move; the release's "
    "completion and release receipts are appended to preparation_source_receipts. Nothing else moves: "
    "roster, geometry, session, program and its 11-contact ceiling, the agreement term (w_agree 1.0, "
    "k 60, fuse 8-1-8) and its sealed agreement table, the boundary and exemplar stores, every template, "
    "the deliver normaliser and the scorers are the AGREE arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a one-pin knowledge "
    "content change -- slot conventions mined model-free from TRAIN annotations and appended to the "
    "existing slot-contract cards, the cards chosen by a model-free audit over sealed bytes -- with no "
    "rollout, no per-sample scoring, no credit assignment, no update operator and no evolving store."
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


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the AGREE fragment to this cell's own."""
    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-w4-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-w4-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-w4-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "slurp-native-stage3-w4-fold-a-smoke-4-v1"),
            ("saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "saea-slurp-native-stage3-w4-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-W4-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-w4-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-w4-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", "slurp-native-stage3-w4-fold-a-baseline-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-w4-fold-a-v1"),
        ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-w4-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent: str, out: str, pairs, *, what_this_is: str) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    store = document["knowledge_stores"]["slot-contracts"]
    if {"release": store["release"], "snapshot": store["snapshot"]} != OLD_STORE:
        raise SystemExit("the AGREE parent does not pin slot-contracts-v2; refusing")
    store["release"] = dict(NEW_STORE["release"])  # THE ONE PIN
    store["snapshot"] = dict(NEW_STORE["snapshot"])
    receipts = list(document["preparation_source_receipts"])
    if any(r["relpath"] in {x["relpath"] for x in NEW_RECEIPTS} for r in receipts):
        raise SystemExit("the parent already carries a W4 receipt")
    document["preparation_source_receipts"] = receipts + [dict(r) for r in NEW_RECEIPTS]
    document["what_this_is"] = what_this_is
    # everything else must be the parent's, id rewrites aside
    for key in parent_doc:
        if key in ("knowledge_stores", "preparation_source_receipts", "prepared_phase_supply", "what_this_is",
                   "native_contact_fit"):
            continue
        if json.dumps(parent_doc[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the one pin")
    wr(out, dump_like(raw, document))


def derive_experiment(parent: str, out: str, pairs, args, *, purpose: str, readiness_reason: str,
                      campaign: bool, failure_policy: str | None = None) -> None:
    raw = rd(parent)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    if failure_policy is not None:
        document["failure_policy"] = failure_policy
    else:
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    cell = document["cells"][0]
    agreement = [r for r in cell["readiness"]["requirements"]
                 if r.get("kind") == "preparation" and r.get("relpath") == AGREEMENT_RELPATH]
    if len(agreement) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table requirement")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement, "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    args = parser.parse_args(argv)
    if args.data_root:
        for pin in (NEW_STORE["release"], *NEW_RECEIPTS):
            path = os.path.join(args.data_root, pin["relpath"])
            if hashlib.sha256(io.open(path, "rb").read()).hexdigest() != pin["sha256"]:
                raise SystemExit(f"{pin['relpath']} does not hash to its pin")

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(through scripts/flights/w4/w4_flip.sh), which also mints this cell's own first-phase supply under its "
        "own run id (item E16); --allow-output-change must never be passed, and the minted supply must reproduce "
        "the AGREE arm's own first-phase output digest (the slot store is not an input to it). Nothing here "
        "authorises a flight, a readiness flip or an admission entry."
    )
    written = []
    arm_pairs = substitutions(smoke=False)
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-w4-fold-a-baseline-v1.json", arm_pairs,
                    what_this_is="Cell W4 (knowledge wave, owner decision 164): the retained AGREE arm with the slot "
                                 "conventions store. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w4-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-w4-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell W4 on TRAIN Fold A 1,080 (knowledge wave, owner decision 164): with the slot-contract cards "
            "extended by TRAIN-mined slot conventions (value vocabulary, annotation scope, span extent), does the "
            "official pooled SLU-F1 (primary: the mechanism acts on slots, so owner decision 133's intent-primary "
            "rule does not apply and decision 115's shape holds) stay within -- or rise above -- the retained "
            "AGREE form, read at the knowledge wave's shared in-chain A/A " + SHARED_AA_RUN + ", with intent "
            "accuracy the non-inferiority guard? " + ONE_CHANGE + " Development numbers only (owner decisions 28 "
            "and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell W4 registered before contact on " + args.date + " from the retained AGREE arm fragments by script "
            "(decision 58) with one pin moved (owner decision 164). Comparator: the sealed AGREE arm " + AGREE_RUN
            + ", never re-flown, read at the knowledge wave's shared in-chain A/A replicate " + SHARED_AA_RUN
            + " (registered by the coordinator) flown in the same campaign chain." + held
        ),
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-w4-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-w4-fold-a-smoke-4-baseline-v1.json",
                    smoke_pairs,
                    what_this_is="Four-row structural form smoke of cell W4: the same one pin on the first four rows "
                                 "of the unchanged TRAIN Fold A roster. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w4-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-w4-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell W4: that the slot-contracts-w4-v1 release loads by its pins, "
            "that every extended card renders, that every request fits and that the episode completes. It is "
            "scored by no one and read by no one: four rows can never be evidence of benefit or of harm. "
            + ONE_CHANGE
        ),
        readiness_reason=(
            "Four-row form smoke of cell W4, registered before contact on " + args.date + " from the AGREE smoke "
            "fragments by script (decision 58). Structural form proof only: no score, no read, no claim." + held
        ),
        campaign=False,
        failure_policy=(
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell W4 and the arm does not open. The resume-recovery clause of owner decision 22 "
            "applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        ),
    )
    written.append("configs/experiment/slurp-native-stage3-w4-fold-a-smoke-4-v1.json")
    print(json.dumps({"written": written, "new_store": NEW_STORE}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
