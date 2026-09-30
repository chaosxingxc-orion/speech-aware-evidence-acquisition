#!/usr/bin/env python3
"""Derive the phase-2 Perception-branch cells P-SV-1, P-SV-2 and P-SV-3 (owner decisions 184, 186, 188, 190; spec
docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md with the coordinator
rulings O1-O6) from the RETAINED AGREE arm fragments by script (decision 58).

THREE registered changes to the AGREE bytes, and nothing else moves:

1. **Fold A -> Fold B** (the read roster, ruling O2), exactly the pins the filler family re-pointed
   (scripts/flights/filler/derive_filler_cells.py): the dataset view ``slurp-speech-native-evo-fold-b-1080``,
   the roster/population/split id, the boundary-channel speech query (``query_source`` of the Perception
   ``intent-boundaries`` supply) and the exemplar-channel speech query (``query_source`` of the Solver
   ``train-exemplars`` supply), both copied from the committed filler chunk c01 baseline, the agreement table
   (``prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1``, byte-identical to the filler table, the id the
   phase-2 inputs README says a phase-2 cell should pin), and the preparation receipts (Fold A alias -> Fold B
   alias, Fold A agreement receipt -> Fold B agreement receipt, + the Fold B encode receipt, the content
   derivative's provenance and the roster receipt).
2. **The program switch** ``phase-native-candidates-review-revise-v1`` (ceiling 11) ->
   ``phase-native-candidates-review-revise-pbranch3-l2-v1`` (ceiling 15 = 11 + 2 (K - 1), K = 3, level 2); the
   two program fragments differ only in ``program_id`` and ``max_contacts`` (verified leaf by leaf here).
3. **The branch block** ``native_episode.roles.perception.branches`` (level 2, K = 3, A last): the B branch
   (P-SV-1 ``b-top2contrast``: ``presentation_id`` ``top2-contrast-v1``; P-SV-2 ``b-list3``: ``min_candidates``
   3; P-SV-3 ``b-depth``: ``overrides`` raising the boundary-supply knobs ``fuse_coverage.m`` and
   ``fuse_coverage.top_l`` together from 8 to 12, c unchanged -- ONE axis, ``knob_overrides()`` below; P-SV-4
   ``b-k6p``: ``key_source`` swapping the boundary ``facet_source`` and ``query_source`` for the K6p centred
   centroid key and the centred Fold B speech queries, agreement unchanged, ``psv_family.k6p_key_source()``), the twin
   ``t-twin`` (``replicate_of`` ``a-agree``) and the delivering ``a-agree`` (AGREE's Perception evidence as
   flown: w_agree 1.0, k 60, fuse 8/1/8). ``fit_estimate`` and every ``max_supplied_items`` are MEASURED (P-SV-1 /
   P-SV-2) or DECLARED from the new depth (P-SV-3, never flown) on the sealed AGREE arm by
   scripts/flights/psv/psv_fit_measure.py (hash-checked here).

Bookkeeping that follows: run / attempt / FIT ids, ``native_contact_fit.contact_cap`` (rows x 15 x 4), the
family budget and execution plan at ceiling 15 with the Fold B audio, readiness HELD with the Fold B agreement
table as its preparation requirement, ``prepared_phase_supply`` DROPPED so the flip mints each cell's own
first-phase supply under its own run id (item E16), ``stage3_algorithm`` ``none``, prose.

FOUR experiment cells per P-SV cell (the 1,080-row arm and its four-row form smoke on the committed Fold B prefix
receipt) plus one one-cell campaign plan per P-SV cell. No A/A cell: the twin branch T flies inside every row.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip.

    python scripts/flights/psv/derive_slurp_psv_cells.py --data-root "$SPEECHRL_DATA_DIR" [--cells psv1,psv2,psv3]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import psv_family as ff  # noqa: E402

FIT_MEASURE_SHA256 = "134f72812823f802ac9d62b616b29536f649bcb83d62aead295891bde9820237"
# P-SV-4 (2026-09-30): the v2 file psv_fit_measure.py writes beside v1 (v1 is never overwritten); it adds exactly
# max_supplied_items.key_source / estimates.key_source (= A's bound: a key swap changes which items, never how many).
FIT_MEASURE_V2_SHA256 = "e67441a97ba4bb75ba7cc5e5bded1e0b97447100dd9a4bc5bcf0f89806e86e5f"
FIT_MEASURE_SHAS = {ff.FIT_MEASURE: FIT_MEASURE_SHA256, ff.FIT_MEASURE_V2: FIT_MEASURE_V2_SHA256}
# The previous pin (P-SV-1 / P-SV-2 registration, before the P-SV-3 boundary_depth bound was added to
# psv_fit_measure.py::measure()): f82f4a6c8e0e0b226e3ab3ae7b07732041112bc119d5a307853aff69db747118. The new file
# adds exactly two keys (max_supplied_items.boundary_depth, estimates.boundary_depth); every P-SV-1 / P-SV-2 bound
# (a_and_twin 10, top2_contrast 12, min_candidates 10) and fit_estimate leaf is byte-identical.


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def sha_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


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
    base = flatten(json.loads(rd(f"configs/policy/{ff.BASE_PROGRAM}.json")))
    new = flatten(json.loads(rd(f"configs/policy/{ff.NEW_PROGRAM}.json")))
    moved = sorted(k for k in set(base) | set(new) if base.get(k, "<absent>") != new.get(k, "<absent>"))
    if moved != ["max_contacts", "program_id"]:
        raise SystemExit(f"{ff.NEW_PROGRAM} differs from {ff.BASE_PROGRAM} beyond program_id/max_contacts: {moved}")
    if (base["max_contacts"], new["max_contacts"]) != (ff.BASE_CEILING, ff.NEW_CEILING):
        raise SystemExit("unexpected program ceilings")


def pin_branch_seed(block: dict, key: str, kind: str, data_root: str) -> dict:
    """Copy ``block`` and, if this (key, kind) cell's own prepared Perception
    branch-seed artifact already exists on disk (written by
    ``core.flight.cli prepare-branch-seeds``, design section 5 item 4; the
    item-4 GAP), pin it as the B branch's ``prepared_seed {relpath, sha256}``.

    A no-op (returns an unpinned copy) until that artifact exists, so this
    script stays re-runnable before the offline prepare step has run, exactly
    like every other pin this module writes only once its bytes exist.
    """

    block = copy.deepcopy(block)
    relpath = ff.branch_seed_relpath(key, kind)
    absolute = Path(data_root) / relpath
    if not absolute.is_file():
        return block
    b_branch_id = ff.CELLS[key]["b_branch"]
    for row in block["branches"]:
        if row["branch_id"] == b_branch_id:
            row["prepared_seed"] = {"relpath": relpath, "sha256": sha_file(str(absolute))}
    return block


def knob_overrides(fuse_coverage: dict) -> dict:
    """A boundary-supply-knob branch's ``overrides`` (design section 1's "boundary supply knob" axis;
    rails/supply_variants.py PERCEPTION_BRANCH_KNOB_TAILS ``("fuse_coverage", "m")`` / ``("fuse_coverage",
    "top_l")``): full ``knowledge_stores.<store>.phase_supply.<first phase>.fuse_coverage.<leaf>`` paths so
    ``parse_perception_branch_knob`` resolves them. Every leaf here lands in the SAME branch's ``knobs`` tuple, so
    ``parse_perception_branches`` counts it as exactly ONE axis category (``bool(knobs)``), whatever its length.
    """

    return {
        f"knowledge_stores.{ff.BOUNDARY_STORE_ID}.phase_supply.{ff.FIRST_PHASE_ID}.fuse_coverage.{leaf}": value
        for leaf, value in sorted(fuse_coverage.items())
    }


def branches_block(key: str, measure: dict) -> dict:
    bounds = measure["max_supplied_items"]
    cell = ff.CELLS[key]
    axis = cell["b_axis"]
    if "presentation_id" in axis:
        b_row = {"branch_id": cell["b_branch"], "max_supplied_items": bounds["top2_contrast"], **axis}
    elif "min_candidates" in axis:
        b_row = {"branch_id": cell["b_branch"], "max_supplied_items": bounds["min_candidates"], **axis}
    elif "fuse_coverage" in axis:
        b_row = {
            "branch_id": cell["b_branch"], "max_supplied_items": bounds["boundary_depth"],
            "overrides": knob_overrides(axis["fuse_coverage"]),
        }
    elif "key_source" in axis:
        # P-SV-4: the key_source axis (rails/supply_variants.py PerceptionBranchKeySource) -- the K6p centred key and
        # the centred Fold B queries swapped into the branch's own router; the agreement pin is kept (null).
        b_row = {
            "branch_id": cell["b_branch"], "max_supplied_items": bounds["key_source"],
            "key_source": ff.k6p_key_source(),
        }
    else:
        raise SystemExit(f"cell {key!r} declares an unrecognised b_axis shape: {sorted(axis)}")
    if axis.get("presentation_id") == "top2-contrast-v1":
        # the pinned contrast-pair table (ruling O7, V2); the runtime verifies its bytes before any contact
        b_row["contrast_pairs"] = ff.contrast_pairs_pin()
    return {
        "level": ff.LEVEL,
        "branches": [
            b_row,
            {"branch_id": ff.ARM_T, "max_supplied_items": bounds["a_and_twin"], "replicate_of": ff.ARM_A},
            {"branch_id": ff.ARM_A, "deliver": True, "max_supplied_items": bounds["a_and_twin"]},
        ],
        "fit_estimate": dict(measure["fit_estimate"]),
    }


def substitutions(key: str, kind: str) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the AGREE fragment to this cell's own."""
    n = ff.names(key, kind)
    if kind == "smoke":
        old = ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4", "slurp-native-stage3-agree-w1-fold-a-smoke-4")
    else:
        old = ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A", "slurp-native-stage3-agree-w1-fold-a")
    return [
        (old[0] + "-FIT-V1", n["fit_run_id"]),
        (old[0] + "-V1", n["run_id"]),
        (f"attempt-{old[1]}-generation-v1", n["attempt_id"]),
        (f"attempt-{old[1]}-fit-v1", n["fit_attempt_id"]),
        (f"{old[1]}-baseline-v1", n["baseline"]),
        (f"saea-{old[1]}-v1", n["fragment_kind"]),
        (f"{old[1]}-v1", n["experiment"]),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def roster(kind: str) -> dict:
    spec = dict(ff.ROSTER[kind])
    doc = json.loads(rd(spec["relpath"]))
    spec["sha256"] = sha_file(spec["relpath"])
    if kind == "arm" and spec["sha256"] != ff.ROSTER["arm"]["sha256"]:
        raise SystemExit("the Fold B roster receipt does not hash to its registered sha256")
    if doc.get("split_identity_hash", spec["split_identity_hash"]) != spec["split_identity_hash"]:
        raise SystemExit(f"{spec['relpath']}: split identity moved")
    spec["ids"] = [item["sample_id"] for item in doc["items"]]
    spec["audio"] = sum(float(item["audio_seconds"]) for item in doc["items"])
    return spec


def retarget_baseline(document: dict, filler: dict, spec: dict) -> None:
    """Fold A -> Fold B: the pins the filler family re-pointed, and nothing else."""
    stores = document["knowledge_stores"]
    perception = stores["intent-boundaries"]["phase_supply"]["perception"]
    solver = stores["train-exemplars"]["phase_supply"]["solver"]
    f_stores = filler["knowledge_stores"]
    agreement = perception["agreement_source"]
    if agreement["relpath"] != ff.FOLD_A_AGREEMENT["relpath"]:
        raise SystemExit("the AGREE parent's agreement pin is not the Fold A table")
    agreement.update({
        "relpath": ff.AGREEMENT["relpath"], "sha256": ff.AGREEMENT["sha256"],
        "tool_contact_ledger_row": ff.AGREEMENT["ledger_row"],
        "embedded_signal": agreement["embedded_signal"].replace(
            "the row's own sealed speech vector", "the row's own sealed TRAIN Fold B speech vector"),
    })
    perception["query_source"] = copy.deepcopy(f_stores["intent-boundaries"]["phase_supply"]["perception"]["query_source"])
    solver["query_source"] = copy.deepcopy(f_stores["train-exemplars"]["phase_supply"]["solver"]["query_source"])
    receipts = []
    for entry in document["preparation_source_receipts"]:
        entry = dict(entry)
        if entry["relpath"] == ff.FOLD_A_ALIAS:
            entry.update(relpath=ff.FOLD_B_ALIAS["relpath"], sha256=ff.FOLD_B_ALIAS["sha256"])
        elif entry["relpath"] == ff.FOLD_A_AGREEMENT["receipt_relpath"]:
            entry.update(relpath=ff.AGREEMENT["receipt_relpath"], sha256=ff.AGREEMENT["receipt_sha256"])
        receipts.append(entry)
    receipts += [
        {"relpath": spec["relpath"], "root": "repository", "sha256": spec["sha256"]},
        {"relpath": ff.FOLD_B_ENCODE_RECEIPT["relpath"], "root": "data", "sha256": ff.FOLD_B_ENCODE_RECEIPT["sha256"]},
        {"relpath": ff.FOLD_B_CONTENT_PROVENANCE["relpath"], "root": "data", "sha256": ff.FOLD_B_CONTENT_PROVENANCE["sha256"]},
    ]
    moved = {e["relpath"] for e in receipts}
    if ff.FOLD_A_ALIAS in moved or ff.FOLD_A_AGREEMENT["receipt_relpath"] in moved:
        raise SystemExit("a Fold A preparation receipt survived the re-target")
    document["preparation_source_receipts"] = receipts
    text = document["what_the_train_exemplars_store_is"]
    if "OWN sealed Fold A speech vector" not in text:
        raise SystemExit("the AGREE parent's exemplar-store prose no longer names the Fold A speech vector")
    document["what_the_train_exemplars_store_is"] = text.replace(
        "OWN sealed Fold A speech vector", "OWN sealed TRAIN Fold B speech vector"
    ) + (" Phase-2 re-target (P-SV-1/P-SV-2): only the query file moves (TRAIN Fold A -> TRAIN Fold B, the pin the "
         "filler family uses); the store, its release and its snapshot are byte-identical.")


def derive_baseline(key: str, kind: str, block: dict, spec: dict, filler: dict) -> str:
    raw = rd(ff.AGREE[kind]["baseline"])
    parent = json.loads(raw)
    document = json.loads(substitute(raw, substitutions(key, kind)))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    if document.get("policy") != ff.BASE_PROGRAM:
        raise SystemExit(f"the AGREE parent's policy is {document.get('policy')!r}")
    document["policy"] = ff.NEW_PROGRAM
    roles = document["native_episode"]["roles"]
    perception = roles["perception"]
    if "branches" in perception or perception.get("max_iterations") != 1 or "supply_variants" in roles["solver"]:
        raise SystemExit("the AGREE parent's Perception role is not the plain one-visit role")
    perception["branches"] = block
    rows = len(spec["ids"])
    if parent["native_contact_fit"]["contact_cap"] != rows * ff.BASE_CEILING * ff.FIT_ENDPOINTS_PER_CONTACT:
        raise SystemExit("the AGREE parent's FIT cap is not rows x 11 x 4")
    document["native_contact_fit"]["contact_cap"] = rows * ff.NEW_CEILING * ff.FIT_ENDPOINTS_PER_CONTACT
    retarget_baseline(document, filler, spec)
    if key == "psv4":
        # the two K6p artifacts' receipts beside the Fold B receipts (both zero-contact prepared inputs)
        document["preparation_source_receipts"] = document["preparation_source_receipts"] + [
            {"relpath": ff.K6P_KEY["receipt_relpath"], "root": "data", "sha256": ff.K6P_KEY["receipt_sha256"]},
            {"relpath": ff.K6P_QUERIES_FOLD_B["receipt_relpath"], "root": "data",
             "sha256": ff.K6P_QUERIES_FOLD_B["receipt_sha256"]},
        ]
    c = ff.CELLS[key]
    axis = ", ".join(f"{k} {v}" for k, v in c["b_axis"].items())
    document["what_this_is"] = (
        f"Cell {c['label']}{' four-row form smoke' if kind == 'smoke' else ''} (owner decisions 184, 186, 188): the "
        "phase-2 same-flight Perception-branch instrument on TRAIN Fold B. THE BASE is the retained AGREE arm "
        f"({ff.AGREE_RUN}) re-targeted to Fold B exactly as the filler family re-pointed it (dataset view, roster, "
        "the two speech-query pins, the Fold B agreement table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1, the "
        f"preparation receipts). THE PROGRAM SWITCH: {ff.BASE_PROGRAM} (ceiling 11) -> {ff.NEW_PROGRAM} (ceiling 15 = "
        "11 + 2 (K - 1), level 2; the fragments differ only in program_id and max_contacts). THE BRANCH BLOCK: "
        f"native_episode.roles.perception.branches, level 2, K = 3, delivering branch last -- {c['b_branch']} (B: "
        f"{axis}), {ff.ARM_T} (T: replicate_of {ff.ARM_A}) and {ff.ARM_A} (A: deliver true, AGREE's Perception "
        "evidence as flown, w_agree 1.0, k 60, fuse 8/1/8). B and T contact Perception once each at the one "
        "Perception visit and, at level 2, the Solver once each at its first visit; A alone continues through "
        "Solver/Reviewer/Planner and delivers. Nothing else moves: geometry, session, role graph, templates, stores, "
        "releases, snapshots, the deliver normaliser and the scorers are the AGREE arm's, byte for byte."
    )
    for k in parent:
        if k in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit",
                 "knowledge_stores", "preparation_source_receipts", "what_the_train_exemplars_store_is"):
            continue
        if json.dumps(parent[k], sort_keys=True) != json.dumps(document[k], sort_keys=True):
            raise SystemExit(f"baseline key {k!r} moved beyond the registered change")
    episode = copy.deepcopy(document["native_episode"])
    episode["roles"]["perception"].pop("branches")
    if episode != parent["native_episode"]:
        raise SystemExit("native_episode moved beyond the Perception branches block")
    out = f"configs/baseline/{ff.names(key, kind)['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


def budgets(rows: int, audio: float, parent: dict, kind: str) -> tuple[dict, dict]:
    fam = dict(parent["family_budget"])
    if fam["generation_calls_cap"] != rows * ff.BASE_CEILING:
        raise SystemExit("the AGREE parent's generation cap is not rows x 11")
    fam.update({
        "generation_calls_cap": rows * ff.NEW_CEILING,
        "fit_endpoint_calls_cap": rows * ff.NEW_CEILING * ff.FIT_ENDPOINTS_PER_CONTACT,
        "repeated_speech_audio_seconds_cap": ff.speech_cap(audio),
        "native_task_contract_calls_cap": fam["native_task_contract_calls_cap"] + rows * (ff.NEW_CEILING - ff.BASE_CEILING),
        "gpu_hours_fit_inclusive": ff.gpu_hours(kind),
    })
    plan = dict(parent["execution_plan"])
    plan.update({"planned_model_calls": fam["generation_calls_cap"], "planned_gpu_hours": fam["gpu_hours_fit_inclusive"],
                 "planned_speech_audio_seconds": fam["repeated_speech_audio_seconds_cap"]})
    return fam, plan


def contrast_pin_sentence() -> str:
    """P-SV-1's readiness sentence naming the V2 contrast-pair pin on the b-top2contrast branch (ruling O7)."""

    v2, v1, cov = ff.CONTRAST_PAIR_TABLE, ff.CONTRAST_PAIR_TABLE_V1, ff.CONTRAST_PAIR_COVERAGE
    return (
        " The top2-contrast-v1 branch's contrast-pair table pin now sits on the branch (b-top2contrast.contrast_pairs: "
        f"{v2['table_relpath']}, sha256 {v2['sha256']}, {ff.CONTRAST_PAIR_BUILDER} {ff.CONTRAST_PAIR_BUILDER_ARGS}; "
        f"{ff.CONTRAST_PAIR_RULING} ruling, {ff.SPEC}), receipt {v2['receipt_relpath']} ({v2['pairs_written']:,} pairs "
        f"written / {v2['pairs_skipped']} skipped of {v2['pairs_considered']:,} considered, insufficient-pool-support). "
        f"This REPLACES the nearest-rival V1 pin ({v1['pairs_written']} pairs written / {v1['pairs_skipped']} skipped of "
        f"{v1['pairs_considered']}, sha256 {v1['sha256']}, unchanged on disk and content-verified by --check), which "
        f"covered only {cov['v1_nearest_rival']['rows_hit']} of {cov['rows_total']:,} P-SV-1 b-top2contrast rows (38.5%; "
        f"{cov['coverage_script']}); V2 covers {cov['v2_all_pairs']['rows_hit']:,} of {cov['rows_total']:,} rows (96.0%), "
        "and the runtime verifies the file's bytes against that sha256 before any contact."
    )


STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a phase-2 cell of the same-flight "
    "INSTRUMENT (owner decisions 172 and 184) -- one Perception-branch axis and an in-flight twin read as branch "
    "columns (the branch note at level 1, the branch Solver answer at level 2) against the delivering branch A -- "
    "with no rollout pool, no per-sample credit, no update operator and no evolving store. It is not labelled "
    "sealed-credit-system-policy-v1, and no delivered answer or downstream node depends on more than branch A."
)


def derive_experiment(key: str, kind: str, spec: dict, date: str) -> str:
    raw = rd(ff.AGREE[kind]["experiment"])
    parent = json.loads(raw)
    document = json.loads(substitute(raw, substitutions(key, kind)))
    n = ff.names(key, kind)
    c = ff.CELLS[key]
    rows = len(spec["ids"])
    if int(parent["population"]["count"]) != rows:
        raise SystemExit("the AGREE parent's row count differs from the Fold B roster")
    document["date"] = date
    document["split_id"] = ff.SPLIT_ID
    document["population"] = {
        "count": rows, "dataset_fragment": ff.DATASET_FRAGMENT, "roster_receipt": spec["relpath"],
        "split_identity_hash": spec["split_identity_hash"],
        "decision_population": (
            f"TRAIN Fold B, the phase-2 READ roster (coordinator ruling O2; owner decision 186: rollout-exposed only, "
            f"and no branch value of this cell is built from Fold B rollouts): {rows} rows of {spec['relpath']} "
            f"({spec['roster_id']})" + (", the first four Fold B rows the filler family froze as a prefix receipt; "
                                        "structural form proof only, no score and no read." if kind == "smoke" else
                                        "; outside TRAIN Fold A (the tuning roster), the exemplar pool, the centroid "
                                        "construction pool, both semantic stores and every SLURP evaluation roster "
                                        f"({ff.AGREEMENT['inputs_readme']}).")
        ),
    }
    document["populations"] = [{"dataset_fragment": ff.DATASET_FRAGMENT, "ids": list(spec["ids"])}]
    fam, plan = budgets(rows, spec["audio"], parent, kind)
    document["family_budget"], document["execution_plan"] = fam, plan
    if "generation_budget" in document:
        target = document["generation_budget"].get("target")
        document["generation_budget"] = {
            "cap": rows * ff.NEW_CEILING,
            "definition": (
                f"The AGREE role graph (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1) under program "
                f"{ff.NEW_PROGRAM}: a level-2 Perception branch group of K = 3 raises the bounded graph ceiling by "
                f"2 (K - 1) = 4 to 15 contacts per row (rails.native_episode_config, phase 2), so {rows:,} x 15 = "
                f"{rows * ff.NEW_CEILING:,} is the exact program maximum. The sealed AGREE arm realised 4.060 contacts "
                "per row on Fold A; the branch contacts (B and T: one Perception and one first-visit Solver contact "
                "each) add exactly 4 per row, so the expected spend is about 8.06 x rows contacts. The budget is "
                "RUN-CUMULATIVE across every attempt of this run id."
            ),
            "target": (round(4.060 * rows) + 4 * rows) if isinstance(target, int) else target,
        }
    cell = document["cells"][0]
    cell["dataset_fragment"] = ff.DATASET_FRAGMENT
    requirement = {
        "kind": "preparation",
        "reason": (
            "The Fold B exemplar-intent AGREEMENT table this cell's boundary channel ranks with (w_agree 1.0), built "
            "model-free by scripts/build_slurp_intent_exemplar_agreement.py (DEV parameters, the DEV/Fold A builder) "
            "from the committed FILLER BASE cell's pins -- zero model, server, encoder, embedder, scorer, network and "
            "GPU contacts. Measured: 1,080 rows, every row 20 votes, 0 self-excluded exemplars, 0 rows without a vote, "
            "60 facets reachable; bytes identical to the filler table "
            f"({ff.AGREEMENT['inputs_readme']}; ledger row {ff.AGREEMENT['ledger_row']})."
        ),
        "relpath": ff.AGREEMENT["relpath"],
        "sha256": ff.AGREEMENT["sha256"],
    }
    k6p_requirements = [
        {
            "kind": "preparation",
            "reason": (
                f"The K6p {what} the b-k6p branch's key_source pins ({ff.K6P_NOTE}): built model-free by {pin['builder']} "
                "from pinned vectors only with the recall read's own key_construction / centre_keys / centre_queries -- "
                "zero model, server, encoder, embedder, scorer, network and GPU contacts; the artifact proof "
                f"({ff.K6P_PROOF['script']}) recomputes the K6p block from it: Fold B gold at block rank 1 "
                f"{ff.K6P_PROOF['fold_b']['rank1_k6p']} vs {ff.K6P_PROOF['fold_b']['rank1_cent_agree']} under the "
                f"centroid + agreement key (ledger row {pin['ledger_row']})."
            ),
            "relpath": pin["relpath"],
            "sha256": pin["sha256"],
        }
        for what, pin in (("centred centroid key", ff.K6P_KEY), ("centred TRAIN Fold B speech queries", ff.K6P_QUERIES_FOLD_B))
    ] if key == "psv4" else []
    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready (through "
        "scripts/flights/psv/psv_flip.sh), which also mints this cell's own first-phase supply under its own run id "
        "(item E16; the first Fold B supply at w_agree 1.0 over the whole roster, so there is no earlier digest to "
        "reproduce); --allow-output-change must never be passed."
        + (contrast_pin_sentence() if key == "psv1" else "")
        + " Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "prepare-branch-seeds", "worker"] + (
        ["campaign"] if kind == "arm" else []
    )
    cell["readiness"] = {
        "reason": (
            f"Cell {c['label']}{' four-row form smoke' if kind == 'smoke' else ''} registered before contact on {date} "
            "from the retained AGREE arm fragments by script (decision 58): Fold A -> Fold B re-target, program "
            f"switched to {ff.NEW_PROGRAM}, a level-2 K = 3 Perception branch block (owner decisions 184, 186, 188). "
            "No cross-flight comparator: the read is within this flight (B and T branch columns against the "
            f"delivering A column)." + held
        ),
        "requirements": [requirement, *k6p_requirements],
        "state": "held",
    }
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of cell {c['label']}: that the 15-ceiling pbranch3-l2 program loads, that "
            "the three Perception branches fan out at the one Perception visit and the two non-A branches each take one "
            "first-visit Solver contact, that every branch fits its measured bound, that the perception-branch receipt "
            f"({'saea-perception-branch-arms-v3' if key == 'psv4' else 'saea-perception-branch-arms-v1'}) and invariant "
            "I7v's Perception path seal, and that the episode completes. "
            "Scored by no one and read by no one: four rows are never evidence of benefit or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A "
            f"failed smoke stops cell {c['label']} and the arm does not open. The resume-recovery clause of owner decision "
            "22 applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        )
    else:
        document["purpose"] = (
            f"Cell {c['label']} on TRAIN Fold B 1,080 (owner decisions 184, 186, 188; phase 2 of the same-flight "
            f"instrument, level 2, K = 3): {c['question']} Primary: {c['primary_metric']}. The claim ceiling is "
            "'nominated' (ruling O1: a level-2 result nominates the composed policy for a full-system cross-flight read "
            "against an in-chain A/A; it admits nothing). Tuning roster TRAIN Fold A (the node ledger that shaped the "
            "design), read roster TRAIN Fold B. Development numbers only (owner decisions 28 and 86); never a test "
            "claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        )
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    out = f"configs/experiment/{n['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    # Default: each cell's own registration date (psv_family.cell_date: P-SV-1..3 2026-09-29, P-SV-4 2026-09-30).
    parser.add_argument("--date", default=None)
    parser.add_argument("--data-root", required=True)
    # Default stays "every cell in ff.CELLS" (today psv1,psv2,psv3): unscoped re-runs keep deriving the whole
    # family, byte-identically, for any cell whose inputs have not moved. A caller that wants to touch only ONE
    # cell's own baseline/experiment/campaign files (e.g. registering a new cell without re-deriving an
    # already-flown one) passes --cells explicitly.
    parser.add_argument("--cells", default=",".join(ff.CELLS))
    args = parser.parse_args(argv)
    check_program_fragments()
    measures = {}
    for relpath, expected_sha in FIT_MEASURE_SHAS.items():
        path = os.path.join(args.data_root, relpath)
        if not os.path.isfile(path):
            continue
        raw = io.open(path, "rb").read()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise SystemExit(f"{relpath} does not hash to its registered sha256; re-run psv_fit_measure.py and re-pin")
        measures[relpath] = json.loads(raw)
    filler = json.loads(rd(ff.FILLER_C01_BASELINE))
    written, blocks = [], {}
    keys = args.cells.split(",")
    unknown = [key for key in keys if key not in ff.CELLS]
    if unknown:
        raise SystemExit(f"--cells names unknown cell(s) {unknown}; known cells are {sorted(ff.CELLS)}")
    for key in keys:
        fit_relpath = ff.fit_measure_relpath(key)
        if fit_relpath not in measures:
            raise SystemExit(f"{fit_relpath} is missing; run psv_fit_measure.py first")
        block = branches_block(key, measures[fit_relpath])
        blocks[key] = block
        for kind in ("arm", "smoke"):
            spec = roster(kind)
            pinned_block = pin_branch_seed(block, key, kind, args.data_root)
            written.append(derive_baseline(key, kind, pinned_block, spec, filler))
            written.append(derive_experiment(key, kind, spec, args.date or ff.cell_date(key)))
        n = ff.names(key, "arm")
        campaign = {"cells": [{"cell": n["experiment"], "experiment": n["experiment"]}], "schema": "saea-campaign-plan-v1"}
        wr(n["campaign"], json.dumps(campaign, indent=2) + "\n")
        written.append(n["campaign"])
    print(json.dumps({"written": written, "branches": blocks,
                      "audio_seconds": {k: round(roster(k)["audio"], 6) for k in ("arm", "smoke")}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
