#!/usr/bin/env python3
"""Derive the CONSTRUCTION-SOURCE lock column cell of the typed loop (coordinator resolution of 2026-10-11 to decision 263-A).

WHY. The semantic-knowledge preparer FORBIDS TRAIN Fold B rows as carrier ids of a delta-store registration (the construction-roster
vs knowledge guard of 2026-09-23: knowledge must not be constructed from the evaluation fold). The loop's proposer tables and the ACE
reflector's material therefore come from ONE lock column flown on the CONSTRUCTION roster R01C (625 TRAIN rows outside Fold A and
Fold B), never from Fold B: Fold B is the held-out selection split, Fold A confirms. This script derives that column and its four-row
smoke. Config only: no contact, no ledger row, no receipt, no flip; both cells are HELD.

WHAT THE CELL IS. The review-off COMP-1b module graph (agree-vote-seed + centroid-boundary-key, Reviewer loop off) with NO columns and
NO supply arms: the plain lock, Perception 1 + Solver 1 = ``phase-native-module-v1-c2``, 2 contacts per row. Every policy-owned block
is written by ``rails.consumption_module.compile_module`` from the declared ``native_episode.consumption_module`` block; the roster
pins (the two sealed speech-query vector files) are R01C's own, taken from the committed VAR-2 R01C cell; the agreement table is the
roster's own and is OWED (a model-free preparation, hash zero until it is built). The parent is the committed NX R6-P1 Fold B cell,
exactly as the loop's iteration cells derive from it.

LOCK. The cell composes on ``tf.CONST_LOCK`` (v2.2), not v2.3: the v2.3 ``ace-playbook`` store declares ONE inert row whose source ids
are 50 R01C rows, and ``rails/runner.py`` refuses a query sample that lies inside the composite knowledge source roster. The i0 anchor
cannot be re-homed: the delta-store preparer takes carriers from the permitted roster, which must be a subset of the construction scope,
and the committed ``stage3-deltas-v1r`` scope IS R01C -- every admissible carrier lies inside R01C. Requests are byte-identical between
v2.2 and v2.3 (proof P-ACE-0), so the column on v2.2 serves as the lock's material source, and the construction variant refuses v2.3.

CONSTRUCTION VARIANT. The lock's exemplar pool contains every R01C row, so the block names ``construction_roster: "r01c"``
(``rails/adapters/slurp_module_construction.py``): the module compiles onto the lock layer with the ``train-exemplars`` release and
snapshot moved to the minus-r01 twins (0 ids shared with R01C), and the loader accepts the variant only on R01C. The agreement table is
the roster's own ``SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1``, built model-free against that minus-r01 pool. :func:`knowledge_source_guard`
measures the runner's roster intersection for the cell's declared stores.

    python -B scripts/flights/tfrl/derive_tfrl_construction_cells.py [--dry-run]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_construction as variant  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

ZERO = dv.ZERO
#: The committed VAR-2 R01C cell carries every R01C pin this cell needs (sealed vectors, promotion receipt, preparation receipts).
R01C_PIN_SOURCE = "slurp-native-stage3-var2-supply-variants-r01c-baseline-v1"
AGREEMENT_ID = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1"
AGREEMENT_RELPATH = f"prepared/{AGREEMENT_ID}/agreement.jsonl"
AGREEMENT_RECEIPT_RELPATH = f"prepared/{AGREEMENT_ID}/receipt.json"
AGREEMENT_RECEIPT_PIN = {"relpath": AGREEMENT_RECEIPT_RELPATH, "root": "data", "sha256": variant.R01C_AGREEMENT_RECEIPT_SHA256}
#: The full-pool receipt the parent lists; the construction variant's pool is the minus-r01 twin, whose receipt VAR-2 R01C pins.
FULL_POOL_RECEIPT = "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json"
SEGMENT_PATH = ("knowledge_stores", "intent-boundaries", "phase_supply", "perception", "query_source")
CONTENT_PATH = ("knowledge_stores", "train-exemplars", "phase_supply", "solver", "query_source")
#: Parent entries of ``preparation_source_receipts`` that name the Fold B roster (replaced by R01C's own).
FOLD_B_MARKERS = ("FOLD-B", "fold-b", "filler-fold-b")

ALLOWED_DIFFS = (
    "policy", "native_episode.consumption_module", "native_episode.roles.perception.template_variants", "native_contact_fit",
    "prepared_phase_supply", "what_this_is", "what_the_train_exemplars_store_is", "preparation_source_receipts",
    "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256",
    "knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source",
    "knowledge_stores.train-exemplars.release", "knowledge_stores.train-exemplars.snapshot",     # the construction variant's minus-r01 pool
)

WHAT_THIS_IS = (
    "Construction-source lock column of the autonomous typed loop (coordinator resolution of 2026-10-11 to owner decision 263-A; design "
    "docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md sections 1.3, 3.1, 3.3). THE BASE is the NX "
    "R6-P1 / iteration-cell base -- COMP-1b (agree-vote-seed, centroid-boundary-key) as a consumption-module block on the lock, Reviewer "
    "loop OFF -- with NO columns and NO supply arms: the plain lock, Perception 1 + Solver 1 = 2 contacts per row, on the CONSTRUCTION "
    "roster SLURP-STAGE3-CONSTRUCTION-R01C (625 TRAIN rows outside Fold A and Fold B). It is the proposer / reflector MATERIAL SOURCE "
    "for iterations 1-3 of the typed loop: its official per-row scores feed the contrast tables; no benefit is claimed. Every policy block "
    "is the module compiler's output."
)
WHAT_EXEMPLARS = (
    "SLURP v2 base program module M1 / cell B1 on the construction roster R01C: the top-20 TRAIN construction-pool exemplars recalled by "
    "cosine against this row's OWN sealed R01C speech vector in the content retrieval dimension. The store is the size-pool-annotated-"
    "exemplars-MINUS-R01 release (34,474 source ids, 0 shared with R01C), pinned by the construction variant of the lock "
    "(consumption_module.construction_roster r01c): the lock's own pool contains the R01C rows, which the runner's knowledge-source guard "
    "refuses (docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-minus-r01.json)."
)
HELD = (
    " HELD (DRAFT): the coordinator countersigns the DRAFT rows, mints the admission receipt and re-pins with "
    "scripts/flights/repin_cell.py --set-ready (through scripts/flights/tfrl/tfrl_const_flip.sh), which also mints this cell's own first-phase "
    "supply under its own run id (item E16); --allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip "
    "or an admission entry."
)


def parent_names(kind: str) -> dict:
    return dv.parent_names(kind)


def r01c_pins(repo_root: Path = REPO_ROOT) -> dict:
    """The committed R01C pins: the two sealed query-vector pins, the packet promotion receipt and the R01C preparation receipts."""

    source = json.loads(dv.rd(f"configs/baseline/{R01C_PIN_SOURCE}.json", repo_root))

    def at(path: tuple[str, ...]) -> dict:
        node: Any = source
        for key in path:
            node = node[key]
        return copy.deepcopy(node)

    receipts = [r for r in source["preparation_source_receipts"]
                if "construction-r01" in r["relpath"].lower() or "CONSTRUCTION-R01" in r["relpath"] or "size-pool-annotated-exemplars-minus-r01" in r["relpath"]]
    return {
        "segments": at(SEGMENT_PATH), "content": at(CONTENT_PATH),
        "promotion": source["speech_packet_promotion_receipt"], "promotion_sha256": source["speech_packet_promotion_receipt_sha256"],
        "receipts": receipts,
    }


def agreement_source(parent_source: Mapping[str, Any]) -> dict:
    """The parent's ``agreement_source`` retargeted at the roster's own (OWED) table."""

    out = copy.deepcopy(dict(parent_source))
    out["relpath"], out["sha256"], out["tool_contact_ledger_row"] = AGREEMENT_RELPATH, variant.R01C_AGREEMENT["sha256"], AGREEMENT_ID
    out["embedded_signal"] = (
        "derived: the share of this row's own top-20 sealed TRAIN-exemplar recall whose frozen build-time task_target equals each boundary "
        "intent, self-excluded by the row's utterance identity and normalised to 1. Speech-keyed by construction -- the recall it "
        "summarises is the row's own sealed R01C speech vector against the frozen minus-r01 pool -- and gold-free: the key is a released "
        "store property, never a label, transcript or future turn. Built model-free by scripts/build_slurp_intent_exemplar_agreement.py "
        "with zero model, server, encoder, embedder, scorer, network and GPU contacts.")
    return out


def module_block(parent: Mapping[str, Any]) -> dict:
    """The parent's COMP-1b review-off block with the columns and the template frame removed (the plain lock) and the roster's own table."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (tf.PARENT_LOCK, "off"):
        raise SystemExit(f"the parent's module block is not review-off lock {tf.PARENT_LOCK}")
    block["lock"] = tf.CONST_LOCK
    block["construction_roster"] = variant.CONSTRUCTION_R01C
    block["columns"] = []
    block.pop("template_frame", None)
    block.pop("supply_frame", None)
    seeded = 0
    for component in block["components"]:
        if component["component_id"] == cm.AGREE_VOTE_SEED and component.get("state") == "on":
            component["params"]["agreement_source"] = agreement_source(component["params"]["agreement_source"])
            seeded += 1
    if seeded != 1:
        raise SystemExit("the parent block does not arm agree-vote-seed exactly once")
    return block


def roster_parent(parent: Mapping[str, Any], pins: Mapping[str, Any]) -> dict:
    """The parent fragment with its roster pins (the two sealed query-vector sources) and promotion receipt taken from R01C."""

    out = copy.deepcopy(dict(parent))
    for path, key in ((SEGMENT_PATH, "segments"), (CONTENT_PATH, "content")):
        node: Any = out
        for step in path[:-1]:
            node = node[step]
        node[path[-1]] = copy.deepcopy(pins[key])
    out["speech_packet_promotion_receipt"] = pins["promotion"]
    out["speech_packet_promotion_receipt_sha256"] = pins["promotion_sha256"]
    return out


def substitution_pairs() -> list[tuple[str, str]]:
    slug = tf.CONST_SLUG
    return [(f"slurp-stage3-{tf.PARENT_SLUG}", f"slurp-stage3-{slug}"), (tf.PARENT_SLUG.upper(), slug.upper()), (tf.PARENT_SLUG, slug)]


def substitute(text: str) -> str:
    for old, new in substitution_pairs():
        text = text.replace(old, new)
    return text


def derive_baseline(kind: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    names = tf.const_names(kind)
    parent_name = parent_names(kind)["baseline"]
    raw = dv.rd(f"configs/baseline/{parent_name}.json", repo_root)
    parent = json.loads(raw)
    pins = r01c_pins(repo_root)
    swapped = roster_parent(parent, pins)
    block = module_block(parent)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=repo_root), repo_root=repo_root)
    if composed.program_id != tf.CONST_PROGRAM or composed.program_ceiling != tf.CONST_CONTACTS:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {tf.CONST_PROGRAM} / {tf.CONST_CONTACTS}")
    document = composed.apply_to(swapped)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)                      # E16: the flip mints this cell's own
    rows = tf.SMOKE_ROWS if kind == "smoke" else tf.CONST_ROWS
    document["native_contact_fit"] = {**parent["native_contact_fit"], "run_id": names["fit_run_id"], "attempt_id": names["fit_attempt_id"],
                                      "contact_cap": tf.fit_contact_cap(rows, tf.CONST_CONTACTS)}
    keep = [r for r in parent["preparation_source_receipts"]
            if not any(m in r["relpath"] for m in FOLD_B_MARKERS) and r["relpath"] != FULL_POOL_RECEIPT]
    seen = {r["relpath"] for r in keep}
    document["preparation_source_receipts"] = keep + [r for r in pins["receipts"] if r["relpath"] not in seen] + [AGREEMENT_RECEIPT_PIN]
    document["what_this_is"] = ("Four-row form smoke of the construction-source lock column. " if kind == "smoke" else "") + WHAT_THIS_IS
    document["what_the_train_exemplars_store_is"] = WHAT_EXEMPLARS
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode.get("review_loop"), episode.get("max_revisions")) != ("off", 0):
        raise SystemExit("the construction column must run the Reviewer loop off")
    if "supply_variants" in json.dumps(document["native_episode"]["roles"]):
        raise SystemExit("the construction column carries no supply arms")
    left, right = dv._leaves(parent), dv._leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    stray = [k for k in moved if not any(k == p or k.startswith(p + ".") for p in ALLOWED_DIFFS)]
    if stray:
        raise SystemExit(f"leaves moved beyond the registered diff: {stray[:12]}")
    out = f"configs/baseline/{names['baseline']}.json"
    if write:
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document, "block": block, "program": composed.program_id, "ceiling": composed.program_ceiling,
            "loader_verification": dv.loader_verification(block, document, repo_root)}


def roster_ids(kind: str, repo_root: Path = REPO_ROOT) -> tuple[list[str], dict]:
    doc = json.loads(dv.rd(tf.CONST_ROSTER[kind], repo_root))
    return [str(i["sample_id"]) for i in doc["items"]], doc


def budgets(kind: str, repo_root: Path = REPO_ROOT) -> tuple[dict, dict]:
    rows = tf.SMOKE_ROWS if kind == "smoke" else tf.CONST_ROWS
    calls = rows * tf.CONST_CONTACTS
    _, doc = roster_ids(kind, repo_root)
    audio = math.ceil(sum(float(i["audio_seconds"]) for i in doc["items"]) * tf.CONST_CONTACTS - 1e-9)
    gpu = tf.CONST_PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else tf.CONST_PLANNED_GPU_HOURS_ARM
    fam = {"asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0, "fit_endpoint_calls_cap": tf.fit_contact_cap(rows, tf.CONST_CONTACTS),
           "generation_calls_cap": calls, "gpu_hours_fit_inclusive": gpu, "native_task_contract_calls_cap": calls,
           "official_complete_scoring_jobs": 0 if kind == "smoke" else 1, "repeated_speech_audio_seconds_cap": audio}
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu, "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return fam, plan


def readiness_requirements(kind: str) -> list[dict]:
    names = tf.const_names(kind)
    decision = {"kind": "decision", "expected_decision_id": names["decision_id"], "relpath": names["decision_path"], "sha256": ZERO,
                "reason": f"Decision {names['decision_id']} pinned by scripts/flights/repin_cell.py."}
    agreement = {"kind": "preparation", "relpath": AGREEMENT_RELPATH, "sha256": variant.R01C_AGREEMENT["sha256"],
                 "reason": ("The pre-computed exemplar-intent AGREEMENT table this cell's boundary channel ranks with, BUILT model-free by "
                            "scripts/build_slurp_intent_exemplar_agreement.py from the pinned minus-r01 exemplar snapshot, the pinned pool key vectors "
                            "and THIS roster's own pinned speech query vectors (R01C) -- zero model, server, encoder, embedder, scorer, network and "
                            "GPU contacts. The centroid key file is pinned where the loader verifies it (facet_source.sha256).")}
    supply = {"kind": "preparation", "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json", "sha256": ZERO,
              "reason": ("This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with core.flight.cli "
                         "prepare-supply at the flip from the sealed R01C speech-query segment vectors, the centroid key file "
                         "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the R01C agreement table (item E16). --allow-output-change must "
                         "never be passed.")}
    return [decision, agreement, supply]


def derive_experiment(kind: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    names = tf.const_names(kind)
    parent_exp = parent_names(kind)["experiment"]
    raw = dv.rd(f"configs/experiment/{parent_exp}.json", repo_root)
    document = json.loads(substitute(raw))
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    ids, roster_doc = roster_ids(kind, repo_root)
    rows = len(ids)
    if rows != (tf.SMOKE_ROWS if kind == "smoke" else tf.CONST_ROWS):
        raise SystemExit(f"{tf.CONST_ROSTER[kind]} has {rows} rows")
    document["date"] = tf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind, repo_root)
    document["split_id"] = tf.CONST_SPLIT_ID
    document["stage3_algorithm"] = {
        "id": "shared-rollout", "operators_used": ["rollout", "scoring"],
        "note": ("The construction-source lock column: ONE rollout of the plain lock on the construction roster R01C, scored once with the "
                 "official scorer, whose per-row scores are the proposer tables' and the ACE reflector's MATERIAL SOURCE (counts and rates "
                 "only). No update operator, no selection and no benefit claim of its own; it is re-flown only if the lock changes.")}
    cell.update(dataset_fragment=tf.CONST_DATASET, attempt_id=names["attempt_id"])
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    population = {
        "count": rows, "dataset_fragment": tf.CONST_DATASET, "roster_receipt": tf.CONST_ROSTER[kind],
        "split_identity_hash": roster_doc["split_identity_hash"],
        "decision_population": (
            f"{'The first four rows, in roster order, of ' if kind == 'smoke' else 'All 625 rows of '}the clean construction subset "
            f"{tf.CONST_ROSTER_ID} ({tf.CONST_ROSTER[kind]}): TRAIN rows outside Fold A, Fold B, DEV-1000, DEV-2000, DEV-500-B and every "
            "other SLURP evaluation roster (the roster receipt's own disjointness proof); construction role, split role discovery. "
            + ("Structural form proof only, no score and no read." if kind == "smoke" else
               "No benefit is claimed: the column is the loop's material source."))}
    document["population"] = population
    document["populations"] = [{"dataset_fragment": tf.CONST_DATASET, "ids": ids}]
    contacts, program = tf.CONST_CONTACTS, tf.CONST_PROGRAM
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * contacts, "target": rows * contacts,
            "definition": (f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {program}: "
                           f"{rows:,} x {contacts} = {rows * contacts:,} is the exact program maximum and the expected spend. The budget is "
                           "RUN-CUMULATIVE across every attempt of this run id.")}
    cell["readiness"] = {
        "reason": (f"{'Four-row form smoke of the' if kind == 'smoke' else 'The'} construction-source lock column registered before contact on "
                   f"{tf.DATE} by script (decision 58) from the committed NX R6-P1 parent fragments, the committed VAR-2 R01C roster pins and "
                   "the module compiler: the plain review-off lock on the construction roster R01C (coordinator resolution to owner decision "
                   "263-A)." + HELD),
        "requirements": readiness_requirements(kind), "state": "held"}
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of the construction-source lock column: that {program} (ceiling {contacts}) loads on R01C rows, "
            "that the R01C sealed speech vectors and packets resolve, that every request fits its bound and that the episode completes. "
            "Scored by no one and read by no one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. The smoke is re-flown whole "
            "if it is re-flown at all, under at most one root-diagnosed recovery re-registration; a second failure closes the cell and the "
            "fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"Construction-source lock column on R01C ({rows} rows): one rollout of the plain lock, scored once with the official SLURP scorer, "
            "whose per-row scores are read OFFLINE into the contrast tables the typed proposer reads and the material the ACE reflector "
            "reads in iterations 1-3 of the autonomous typed loop. Fold B stays the held-out selection split and Fold A the confirmation. "
            "No benefit is claimed (measurement design material-source, claims_benefit false). Development numbers only (owner decisions 28 "
            "and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per flight; a second failure stops the flight and "
            "the fix is proven on a four-row dry run. The budget is run-cumulative across attempts. The column is flown once and re-flown "
            "only if the lock changes.")
    leftovers = [m.group(0) for m in re.finditer(r".{50}(?:nx-r6|NX-R6|NX_R6|FOLD-B|fold-b).{30}", json.dumps(document))]
    leftovers = [x for x in leftovers if "Fold A, Fold B" not in x and "outside Fold" not in x and "Fold B stays" not in x]
    if leftovers:
        raise SystemExit(f"inherited parent identity text survived the rewrite ({kind}): {leftovers[:3]}")
    out = f"configs/experiment/{names['experiment']}.json"
    if write:
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document}


def write_campaign(*, repo_root: Path = REPO_ROOT, write: bool = True) -> str:
    arm = tf.const_names("arm")
    plan = {"cells": [{"cell": arm["experiment"], "experiment": arm["experiment"]}], "schema": "saea-campaign-plan-v1"}
    if write:
        dv.wr(arm["campaign"], json.dumps(plan, indent=2) + "\n", repo_root)
    return arm["campaign"]


def knowledge_source_guard(data_root: Path | None, repo_root: Path = REPO_ROOT, block: Mapping[str, Any] | None = None) -> dict:
    """Measure the runner's BUILD/USE guard for this cell: R01C ids against the composite source ids of the stores the cell's compiled
    policy declares (and, for contrast, of lock v2.3's ``ace-playbook`` store). Reads ``source_sample_ids`` only. ``data_root`` None or
    absent -> ``{"measured": False}``."""

    if data_root is None or not Path(data_root).is_dir():
        return {"measured": False, "reason": "data root unavailable"}
    roster = json.loads(dv.rd(tf.CONST_ROSTER["arm"], repo_root))
    ids = {str(i["sample_id"]) for i in roster["items"]}
    baseline = json.loads(dv.rd(f"configs/baseline/{tf.const_names('arm')['baseline']}.json", repo_root))
    out: dict[str, Any] = {"measured": True, "roster_rows": len(ids), "stores": {}}
    from speech_aware_evidence_acquisition.rails.adapters import slurp_module_lock_v2_3 as lock_v2_3  # noqa: PLC0415

    declared = dict(baseline["knowledge_stores"])
    declared.setdefault(lock_v2_3.ACE_STORE_ID, lock_v2_3.ace_store_i0())
    for store_id, store in sorted(declared.items()):
        snap = Path(data_root) / store["snapshot"]["relpath"]
        if not snap.is_file():
            out["stores"][store_id] = {"snapshot": store["snapshot"]["relpath"], "present": False}
            continue
        sources = {str(x) for x in json.loads(snap.read_text(encoding="utf-8")).get("source_sample_ids", [])}
        out["stores"][store_id] = {"snapshot": store["snapshot"]["relpath"], "snapshot_sha256": store["snapshot"]["sha256"],
                                   "source_ids": len(sources), "shared_with_roster": len(ids & sources),
                                   "declared_by_this_cell": store_id in baseline["knowledge_stores"]}
    cell_sources = sum(v.get("shared_with_roster", 0) for v in out["stores"].values() if v.get("declared_by_this_cell"))
    out["cell_conflict_rows"] = cell_sources
    return out


def derive(*, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    out: dict[str, Any] = {"cells": {}}
    for kind in ("arm", "smoke"):
        baseline = derive_baseline(kind, repo_root=repo_root, write=write)
        experiment = derive_experiment(kind, repo_root=repo_root, write=write)
        out["cells"][kind] = {"baseline": baseline["path"], "experiment": experiment["path"], "loader_verification": baseline["loader_verification"]}
        out["program"], out["ceiling"] = baseline["program"], baseline["ceiling"]
        out.setdefault("_documents", {})[kind] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
    out["campaign"] = write_campaign(repo_root=repo_root, write=write)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="derive and verify in memory; write nothing")
    args = parser.parse_args(argv)
    result = derive(write=not args.dry_run)
    result.pop("_documents", None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
