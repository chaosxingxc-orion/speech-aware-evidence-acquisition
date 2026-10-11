#!/usr/bin/env python3
"""Derive one iteration's cells of the autonomous typed loop (decision 263-A, design sections 5 and 8-R3).

THREE FAMILIES OF CELL, all HELD, all config only (no contact, no ledger row, no receipt, no flip):

1. the COLUMN cell ``slurp-native-stage3-tfrl-loop-i<t>-fold-b-v1`` and its four-row smoke: the review-off COMP-1b module graph at
   lock v2.3 on TRAIN Fold B (the committed NX R6-P1 cell is the parent, exactly as VER-1a derives from it), with the Perception
   template columns removed and ONE Solver ``supply_variants`` block compiled by ``rails.consumption_module`` from ``kind: supply``
   columns (E-S1): ``par`` (the accumulated typed parent, iteration >= 2), ``typ`` (the typed child, when a valid candidate cleared
   the predicted bar), ``ace`` (``release_swap`` of the ``ace-playbook`` store to release ``i<t>``), the in-chain twin ``aa`` and the
   delivering arm ``lock`` LAST. An empty typed arm is a LEGAL state (iteration 1 under the 265 coverage pre-read).
2. the text-only TYPED PROPOSER cell and 3. the text-only ACE REFLECTOR cell, derived from the committed GEPA proposer cell
   (``construction-proposer-text`` arm, programs ``phase-tfrl-typed-proposer-v1`` / ``phase-tfrl-ace-reflector-v1``, fragment blocks
   ``tfrl_proposer`` / ``tfrl_ace_reflector``), carried by construction-role carrier rosters drawn by a seeded rule from Fold B.

LOCK. The cells compose on lock v2.3 (``rails/adapters/slurp_module_lock_v2_3.py``): v2.2 plus the ``ace-playbook`` store declared at
the EMPTY release i0 (owner decisions 263 A / 266-A), because ``rails.consumption_module`` takes a ``release_swap`` store from the lock
layer only. The compile and the loader's ``verify_declared_module`` both run under the REAL carrier hooks; no wrapper remains.
:func:`loader_verification` reports the loader's verdict in every derive report.

    python -B scripts/flights/tfrl/derive_tfrl_iteration_cells.py --iteration 1 [--typed-spec FILE] [--ace-pins FILE] [--dry-run]
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
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

ZERO = "0" * 64


def rd(path: str, root: Path | None = None) -> str:
    return io.open((root or REPO_ROOT) / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str, root: Path | None = None) -> None:
    target = (root or REPO_ROOT) / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


# ---------------------------------------------------------------------------------------------------------------------------
# the column cell
# ---------------------------------------------------------------------------------------------------------------------------


def pin(relpath: str | None = None, sha256: str | None = None) -> dict:
    return {"relpath": relpath or "", "sha256": sha256 or ZERO}


def ace_alternate(ace: Mapping[str, Any]) -> dict:
    """The ``{release, snapshot}`` alternate pins of the iteration's ``ace-playbook`` release (zeros until it is prepared)."""

    iteration = int(ace["iteration"])
    base = f"knowledge/slurp/semantic/ace-playbook-i{iteration}"
    return {"release": pin(ace.get("release_relpath") or f"{base}/release.json", ace.get("release_sha256")),
            "snapshot": pin(ace.get("snapshot_relpath") or f"{base}/snapshot.json", ace.get("snapshot_sha256"))}


def column_spec(column_id: str, spec: Mapping[str, Any]) -> dict:
    """One ``kind: supply`` column from an arm spec ``{overrides?, release_swap?}`` (at least one is required)."""

    column: dict[str, Any] = {"column_id": column_id, "kind": "supply", "node": "solver",
                              "max_supplied_items": tf.COLUMN_MAX_SUPPLIED_ITEMS}
    if spec.get("overrides"):
        column["overrides"] = dict(spec["overrides"])
    if spec.get("release_swap"):
        column["release_swap"] = dict(spec["release_swap"])
    if "overrides" not in column and "release_swap" not in column:
        raise SystemExit(f"arm {column_id}: a supply column needs an override or a release swap")
    return column


def iteration_arms(spec: Mapping[str, Any], iteration: int) -> tuple[str, ...]:
    return tf.arm_ids(iteration, typed_present=bool(spec.get("typed")), parent_present=bool(spec.get("parent")))


def module_block(parent: Mapping[str, Any], spec: Mapping[str, Any], iteration: int) -> dict:
    """The parent's COMP-1b review-off module block with the Perception template columns replaced by the supply columns."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (tf.PARENT_LOCK, "off"):
        raise SystemExit(f"the parent's module block is not review-off lock {tf.PARENT_LOCK}")
    block["lock"] = tf.LOCK                                   # v2.3: v2.2 + the declared ace-playbook store
    block.pop("columns", None)
    block.pop("template_frame", None)
    columns = []
    if spec.get("parent") and iteration >= 2:
        columns.append(column_spec(tf.ARM_PARENT, spec["parent"]))
    if spec.get("typed"):
        columns.append(column_spec(tf.ARM_TYPED, spec["typed"]))
    ace = spec["ace"]
    columns.append(column_spec(tf.ARM_ACE, {"release_swap": {
        "store_id": tf.ACE_STORE_ID, "release": ace_alternate(ace)["release"]["relpath"]}}))
    block["columns"] = columns
    alternates: dict[str, list] = {tf.ACE_STORE_ID: [ace_alternate(ace)]}
    for key in ("parent", "typed"):
        for store, pins in ((spec.get(key) or {}).get("alternates") or {}).items():
            alternates.setdefault(store, [])
            for entry in pins:
                if entry not in alternates[store]:
                    alternates[store].append(entry)
    block["supply_frame"] = {"twin": True, "fit_estimate": dict(tf.FIT_ESTIMATE),
                             "delivering_max_supplied_items": tf.DELIVERING_MAX_SUPPLIED_ITEMS, "alternates": alternates}
    return block


def parent_names(kind: str) -> dict:
    lo = "-smoke-4" if kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{tf.PARENT_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{tf.PARENT_SLUG}{lo}-baseline-v1"}


def substitution_pairs(iteration: int) -> list[tuple[str, str]]:
    slug = f"tfrl-loop-i{iteration}-fold-b"
    return [(f"slurp-stage3-{tf.PARENT_SLUG}", f"slurp-stage3-{slug}"), (tf.PARENT_SLUG.upper(), slug.upper()), (tf.PARENT_SLUG, slug)]


def substitute(text: str, iteration: int) -> str:
    for old, new in substitution_pairs(iteration):
        text = text.replace(old, new)
    return text


def _leaves(node: object, prefix: str = "") -> dict[str, object]:
    if isinstance(node, dict) and node:
        out: dict[str, object] = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return {prefix: node}


ALLOWED_DIFFS = (
    "policy", "native_episode.consumption_module", "native_episode.roles.solver.supply_variants",
    "native_episode.roles.perception.template_variants", "native_contact_fit", "prepared_phase_supply", "what_this_is",
    "knowledge_stores.ace-playbook", "knowledge_stores.train-exemplars", "knowledge_stores.slot-contracts",
    "knowledge_stores.intent-boundaries",
)

WHAT_THIS_IS = (
    "Autonomous typed loop with the ACE comparator (owner decision 263-A, design docs/superpowers/specs/"
    "2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md section 5): one same-flight SUPPLY-VARIANT cell on lock "
    "v2.3 (= v2.2 plus the declared, empty ace-playbook-i0 store) and TRAIN Fold B. THE BASE is the NX R6-P1 / VER-1a base -- COMP-1b (agree-vote-seed, centroid-boundary-key) as a "
    "consumption-module block, Reviewer loop OFF. THE COLUMN: at the one Solver visit the Solver is contacted K times over the SAME "
    "state, once per supply arm -- the typed arms (par = the accumulated typed parent, typ = the typed child, each a knob re-cap "
    "and/or one release swap), ace (the ACE playbook release swapped into the ace-playbook store), the in-chain twin aa "
    "(replicate_of lock) and the delivering arm lock LAST with no override (invariants I7 and I7v). Only the delivering arm's answer "
    "is carried forward. Delivery and scope rules are read OFFLINE over every column. Every policy block is the module compiler's "
    "output."
)

HELD = (
    " HELD (DRAFT): the coordinator countersigns the DRAFT rows, mints the admission receipt and re-pins with "
    "scripts/flights/repin_cell.py --set-ready (through scripts/flights/tfrl/tfrl_i1_flip.sh), which also mints this cell's own "
    "first-phase supply under its own run id (item E16); --allow-output-change must never be passed. Nothing here authorises a "
    "flight, a readiness flip or an admission entry."
)


def roster_audio(kind: str, repo_root: Path = REPO_ROOT) -> float:
    doc = json.loads(rd(tf.ROSTER[kind], repo_root))
    return sum(float(i["audio_seconds"]) for i in doc["items"])


def audio_cap(kind: str, contacts: int, repo_root: Path = REPO_ROOT) -> int:
    return math.ceil(roster_audio(kind, repo_root) * contacts - 1e-9)


def loader_verification(block: Mapping[str, Any], document: Mapping[str, Any], repo_root: Path) -> dict:
    """What the LOADER does with the derived cell: ``verify_declared_module`` under the REAL hooks (not the wrapper)."""

    try:
        cm.verify_declared_module(block, document, repo_root=repo_root)
    except Exception as error:  # noqa: BLE001 - the verdict is the report
        return {"ok": False, "refusal": f"{type(error).__name__}: {str(error)[:300]}"}
    return {"ok": True, "refusal": None}


def derive_iteration_baseline(iteration: int, kind: str, spec: Mapping[str, Any], *, repo_root: Path = REPO_ROOT,
                              write: bool = True) -> dict:
    parent_name = parent_names(kind)["baseline"]
    raw = rd(f"configs/baseline/{parent_name}.json", repo_root)
    parent = json.loads(raw)
    block = module_block(parent, spec, iteration)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=repo_root), repo_root=repo_root)
    arms = iteration_arms(spec, iteration)
    contacts = tf.ceiling(iteration, typed_present=bool(spec.get("typed")), parent_present=bool(spec.get("parent")))
    expected_program = f"phase-native-module-v1-c{contacts}"
    if composed.program_id != expected_program or composed.program_ceiling != contacts:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {expected_program} / {contacts}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)           # E16: the flip mints this cell's own
    rows = tf.SMOKE_ROWS if kind == "smoke" else tf.ROWS
    names = tf.names(iteration, kind)
    document["native_contact_fit"] = {**parent["native_contact_fit"], "run_id": names["fit_run_id"],
                                      "attempt_id": names["fit_attempt_id"], "contact_cap": tf.fit_contact_cap(rows, contacts)}
    document["what_this_is"] = ("Four-row form smoke of loop iteration %d cell. " if kind == "smoke" else "Loop iteration %d cell. ") % iteration + WHAT_THIS_IS
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    left, right = _leaves(parent), _leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    stray = [k for k in moved if not any(k == p or k.startswith(p + ".") for p in ALLOWED_DIFFS)]
    if stray:
        raise SystemExit(f"leaves moved beyond the registered diff: {stray[:12]}")
    group = episode["roles"]["solver"]["supply_variants"]
    declared = [row["arm_id"] for row in group["arms"]]
    if tuple(declared) != arms:
        raise SystemExit(f"compiled arm order {declared} differs from the declared {list(arms)}")
    out = f"configs/baseline/{names['baseline']}.json"
    if write:
        wr(out, dump_like(raw, document), repo_root)
    return {"path": out, "document": document, "block": block, "program": composed.program_id, "ceiling": contacts, "arms": list(arms),
            "loader_verification": loader_verification(block, document, repo_root)}


def budgets(iteration: int, kind: str, contacts: int, repo_root: Path = REPO_ROOT) -> tuple[dict, dict]:
    rows = tf.SMOKE_ROWS if kind == "smoke" else tf.ROWS
    calls = rows * contacts
    audio = audio_cap(kind, contacts, repo_root)
    if kind == "smoke":
        # The adapter's budget is RUN-CUMULATIVE across the attempts of a run id: a recovered smoke (tf.SMOKE_RECOVERIES) carries the original
        # plan plus the failed attempts' realised spend. The FIT cap below is structural and is NEVER scaled.
        calls, audio = tf.smoke_cumulative_budget(iteration, calls, audio)
    gpu = tf.PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else tf.planned_gpu_hours_arm(iteration, rows, contacts)
    fam = {"asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
           "fit_endpoint_calls_cap": tf.fit_contact_cap(rows, contacts), "generation_calls_cap": calls,
           "gpu_hours_fit_inclusive": gpu, "native_task_contract_calls_cap": calls,
           "official_complete_scoring_jobs": 0 if kind == "smoke" else 1, "repeated_speech_audio_seconds_cap": audio}
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu, "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return fam, plan


def algorithm_label(spec: Mapping[str, Any]) -> dict:
    columns = {}
    if spec.get("parent"):
        columns[tf.ARM_PARENT] = tf.ALGORITHM_TYPED
    if spec.get("typed"):
        columns[tf.ARM_TYPED] = tf.ALGORITHM_TYPED
    columns[tf.ARM_ACE] = tf.ALGORITHM_ACE
    return {
        "id": tf.ALGORITHM_TYPED,
        "operators_used": ["rollout", "scoring", "credit_assignment", "selection", "context_application"],
        "columns": columns,
        "note": ("This cell holds two algorithms in one fragment (design 4.5): the typed arms (par, typ) are sealed-credit-system-policy "
                 "supply variants whose credit is assigned per arm against the in-flight lock and twin and whose acceptance is the "
                 "preregistered selection rule; the ace arm is the ACE comparator (ace-grow-refine-v1), a non-delivering column that "
                 "can never be locked (decision 245)."),
    }


def derive_iteration_experiment(iteration: int, kind: str, spec: Mapping[str, Any], *, repo_root: Path = REPO_ROOT,
                                write: bool = True) -> dict:
    parent = parent_names(kind)["experiment"]
    raw = rd(f"configs/experiment/{parent}.json", repo_root)
    document = json.loads(substitute(raw, iteration))
    names = tf.names(iteration, kind)
    contacts = tf.ceiling(iteration, typed_present=bool(spec.get("typed")), parent_present=bool(spec.get("parent")))
    program = f"phase-native-module-v1-c{contacts}"
    rows = tf.SMOKE_ROWS if kind == "smoke" else tf.ROWS
    document["date"] = tf.DATE
    document["family_budget"], document["execution_plan"] = budgets(iteration, kind, contacts, repo_root)
    document["stage3_algorithm"] = algorithm_label(spec)
    n_arms = contacts - 1
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * contacts,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {program}: a "
                f"Solver supply-variant group of K = {n_arms} arms ({', '.join(iteration_arms(spec, iteration))}) raises the bounded graph "
                f"ceiling by K - 1 = {n_arms - 1} to {contacts} contacts per row, so {rows:,} x {contacts} = {rows * contacts:,} is the exact "
                f"program maximum and the expected spend. The budget is RUN-CUMULATIVE across every attempt of this run id."),
            "target": rows * contacts,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["attempt_id"] = names["attempt_id"]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    agreement = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("FOLD-B-V1/agreement.jsonl"))
    supply = {"kind": "preparation",
              "reason": ("This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with core.flight.cli "
                         "prepare-supply at the flip from the sealed TRAIN Fold B speech-query segment vectors, the centroid key file "
                         "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the Fold B agreement table (item E16). --allow-output-change "
                         "must never be passed."),
              "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json", "sha256": ZERO}
    decision_id = f"slurp-tfrl-loop-i{iteration}-admission-v1"
    decision = {"kind": "decision", "expected_decision_id": decision_id,
                "relpath": f"coordination/slurp-tfrl-loop-i{iteration}-v1/root-admission-v1.json", "sha256": ZERO,
                "reason": f"Decision {decision_id} pinned by scripts/flights/repin_cell.py."}
    cell["readiness"] = {
        "reason": (f"{'Four-row form smoke of the' if kind == 'smoke' else 'The'} loop iteration {iteration} cell registered before contact "
                   f"on {tf.DATE} by script (decision 58) from the committed Fold B parent fragments and the module compiler: arms "
                   f"{', '.join(iteration_arms(spec, iteration))} (owner decision 263-A)." + HELD),
        "requirements": [decision, agreement, supply], "state": "held"}
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of loop iteration {iteration}: that {program} (ceiling {contacts}) loads, that the "
            f"{n_arms} Solver supply arms fan out at the one Solver visit with the delivering lock arm last, that the empty "
            "ace-playbook-i0 route renders zero bytes on the non-ace arms (proof P-ACE-0), that every swap resolves its alternate "
            "(I7v), that every arm fits its bound, that the supply-variant receipt seals and that the episode completes. Scored by no "
            "one and read by no one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops "
            "the iteration. The smoke is re-flown whole if it is re-flown at all, under at most one root-diagnosed recovery "
            "re-registration; a second failure closes the cell and the fix is proven on a four-row dry run.")
        recovery = tf.smoke_recovery(iteration)
        if recovery:
            document["failure_policy"] += (
                f" This smoke has used the cell's single root-diagnosed recovery re-registration (rec{recovery['recovery_index']}, "
                f"{recovery['root_cause']}): a second failure closes the cell and the fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"Loop iteration {iteration} on TRAIN Fold B 1,080 (owner decision 263-A, preregistered selection rule in "
            f"{tf.PROTOCOL_RELPATH}): which of the declared supply arms ({', '.join(iteration_arms(spec, iteration))}) raises official "
            "pooled SLU-F1 over the delivering lock arm, paired per row inside one flight, with the in-chain twin aa as the null? "
            "Primary: official SLU-F1 delta with whole-utterance cluster-bootstrap CI95; intent is the guard (0.65 pp). The claim "
            "ceiling is 'nominated'. Development numbers only (owner decisions 28 and 86); never a test claim. Nothing here "
            "authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per flight; a second failure stops the flight "
            "and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts. A failed iteration is recorded "
            "by the loop driver as a stop; it is never substituted.")
    leftovers = [m.group(0) for m in re.finditer(r".{50}(?:nx-r6|NX-R6|NX_R6|R6-P1).{30}", json.dumps(document))]
    if leftovers:
        raise SystemExit(f"inherited R6 identity text survived the rewrite ({kind}): {leftovers[:3]}")
    out = f"configs/experiment/{names['experiment']}.json"
    if write:
        wr(out, dump_like(raw, document), repo_root)
    return {"path": out, "document": document}


def write_campaign(iteration: int, *, repo_root: Path = REPO_ROOT, write: bool = True) -> str:
    arm = tf.names(iteration, "arm")
    plan = {"cells": [{"cell": arm["experiment"], "experiment": arm["experiment"]}], "schema": "saea-campaign-plan-v1"}
    if write:
        wr(arm["campaign"], json.dumps(plan, indent=2) + "\n", repo_root)
    return arm["campaign"]


def derive_iteration(iteration: int, spec: Mapping[str, Any], *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    """Derive the column cell and its smoke. ``spec``: ``{"typed": arm-spec | None, "parent": arm-spec | None, "ace": {...}}``."""

    out: dict[str, Any] = {"iteration": iteration, "cells": {}}
    for kind in ("arm", "smoke"):
        baseline = derive_iteration_baseline(iteration, kind, spec, repo_root=repo_root, write=write)
        experiment = derive_iteration_experiment(iteration, kind, spec, repo_root=repo_root, write=write)
        out["cells"][kind] = {"baseline": baseline["path"], "experiment": experiment["path"],
                              "loader_verification": baseline["loader_verification"]}
        out["program"], out["ceiling"], out["arms"] = baseline["program"], baseline["ceiling"], baseline["arms"]
        out["_documents"] = out.get("_documents", {})
        out["_documents"][kind] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
    out["campaign"] = write_campaign(iteration, repo_root=repo_root, write=write)
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# the text-only cells (proposer, reflector)
# ---------------------------------------------------------------------------------------------------------------------------


def carrier_ids(parent_roster: Mapping[str, Any], n: int, *, seed: int, tag: str) -> list[str]:
    """A seeded, deterministic selection of ``n`` Fold B rows (identity anchors only; no gold is consulted)."""

    ids = sorted(str(item["sample_id"]) for item in parent_roster["items"])
    ranked = sorted(ids, key=lambda sid: hashlib.sha256(f"{seed}|{tag}|{sid}".encode("utf-8")).hexdigest())
    return sorted(ranked[:n])


def build_carrier_roster(iteration: int, kind: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    """The construction-role carrier roster receipt: a pure selection of the Fold B receipt (the GEPA precedent)."""

    from speech_aware_evidence_acquisition.core import roster as roster_module  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data import splits  # noqa: PLC0415

    names = tf.names(iteration, kind)
    n = tf.TYPED_CARRIERS if kind == "typed" else tf.n_ace_carriers()
    parent = json.loads(rd(tf.ROSTER["arm"], repo_root))
    ids = carrier_ids(parent, n, seed=tf.CARRIER_SEED, tag=f"{kind}-i{iteration}")
    keep = set(ids)
    items = [item for item in parent["items"] if str(item["sample_id"]) in keep]
    counts: dict[str, int] = {}
    for item in items:
        counts[str(item["stratum"])] = counts.get(str(item["stratum"]), 0) + 1
    counts = dict(sorted(counts.items()))
    roster_id = Path(names["carrier_roster"]).stem.upper().replace("_", "-")
    receipt: dict[str, Any] = {
        "schema": parent["schema"], "roster_id": roster_id, "carrier_lock_key": "slurp", "split_role": "discovery",
        "roster_role": "construction", "seed": tf.CARRIER_SEED, "per_stratum": counts, "strata_counts": counts, "items": items,
        "excluded_count": len(parent["items"]) - len(items),
        "split_identity_hash": splits.split_identity_hash(splits.prefixed("slurp", ids)),
        "authority": ("Decision 263-A (design docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md "
                      "3.1): the TFRL proposer / reflector contact is text-only and carried by ONE carrier row per contact; the flown "
                      "population is this construction-role selection of Fold B."),
        "roster_role_note": ("construction: the contact reads aggregate tables only (no per-row gold, no utterance text); the CARRIER row "
                             "is the flight's row identity, the material it carries is the iteration's tables."),
        "draw_method": "No draw: a seeded sha256 ranking of the parent's sample ids; every selected item is the parent's item verbatim.",
        "selection_rule": f"the first {n} Fold B ids by sha256(seed|tag|sample_id); order ascending sample_id",
        "generator": "scripts/flights/tfrl/derive_tfrl_iteration_cells.py",
        "parent": {"roster_id": parent.get("roster_id"), "count": len(parent["items"]), "relpath": tf.ROSTER["arm"],
                   "split_identity_hash": parent.get("split_identity_hash")},
        "selection_source": {"rule": "seeded-sha256-rank", "seed": tf.CARRIER_SEED},
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
    }
    for carried in ("d1_supplement", "disjointness_proof", "knowledge_source_guard"):
        if carried in parent:
            receipt[carried] = parent[carried]
    measured = roster_module.verify_roster(receipt)
    path = repo_root / names["carrier_roster"]
    if write:
        if path.is_file():
            if json.loads(path.read_text(encoding="utf-8")).get("split_identity_hash") != measured:
                raise SystemExit(f"{names['carrier_roster']} exists with a different split identity; refusing to rewrite")
        else:
            roster_module.write_roster(receipt, path)
    return {"relpath": names["carrier_roster"], "ids": ids, "split_identity_hash": measured, "roster_id": roster_id}


def text_only_label(kind: str) -> dict:
    if kind == "typed":
        return {"id": tf.ALGORITHM_TYPED, "operators_used": ["credit_assignment", "update"],
                "note": ("The typed proposer contact: the frozen core reads the iteration's aggregate credit tables and emits ONE candidate "
                         "edit under a closed schema; a deterministic validator accepts or refuses it and computes the predicted effect. "
                         "The model proposes and never judges.")}
    return {"id": tf.ALGORITHM_ACE, "operators_used": ["update", "selection"],
            "note": ("The ACE reflector contact (arXiv:2510.04618): one contact per scenario reads that scenario's credit tables and the "
                     "current playbook with its script-computed counters and proposes delta items; the deterministic curator, not the "
                     "model, merges, counts and prunes.")}


def derive_text_only(iteration: int, kind: str, pins: Mapping[str, Any], *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    """Derive the proposer (``typed``) or reflector (``ace``) cell from the GEPA proposer cell.

    ``pins``: for ``typed``: ``{"tables": {relpath, sha256}, "context": {relpath, sha256}}``; for ``ace``: ``{"playbook": {...},
    "token_cap": int, "materials": {scenario: {relpath, sha256}}}``. Data-root-relative relpaths."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    names = tf.names(iteration, kind)
    roster = build_carrier_roster(iteration, kind, repo_root=repo_root, write=write)
    ids = roster["ids"]
    base_raw = rd("configs/baseline/slurp-native-stage3-gepa-baseline-v1.json", repo_root)
    base = json.loads(base_raw)
    base.pop("gepa_groups", None)
    base["arm"] = "construction-proposer-text"
    parent_roster_path = tf.ROSTER["arm"]
    base["preparation_source_receipts"] = [
        {"relpath": roster["relpath"], "root": "repository", "sha256": tf.sha256_file(repo_root / roster["relpath"]) if (repo_root / roster["relpath"]).exists() else ZERO},
        {"relpath": parent_roster_path, "root": "repository", "sha256": tf.sha256_file(repo_root / parent_roster_path)},
    ]
    if kind == "typed":
        classes = tf.TYPED_CLASS_SETS
        carriers = [{"sample_id": sid, "allowed_classes": list(classes[i % len(classes)])} for i, sid in enumerate(ids)]
        base["policy"] = tp.TFRL_TYPED_PROGRAM_ID
        base["phase_material"] = {tp.TFRL_TYPED_PHASE_NAME: {
            "instruction_fill": None, "instruction_template": tp.TFRL_TYPED_TEMPLATE_RELPATH, "predecessor_binding": "none",
            "response_format_id": tp.TFRL_TYPED_RESPONSE_FORMAT_ID}}
        base["tfrl_proposer"] = {"tables": dict(pins["tables"]), "context": dict(pins["context"]), "carriers": carriers}
        what = ("Decision 263-A typed proposer contact: one text-only contact per carrier (construction, supply, delivery+scope) reading "
                "the iteration's aggregate tables and context and answering under the closed saea-tfrl-typed-candidate-v1 schema.")
    else:
        from speech_aware_evidence_acquisition.rails.tfrl_typed_proposer import SCENARIOS  # noqa: PLC0415

        carriers = [{"sample_id": sid, "scenario": SCENARIOS[i], "material": dict(pins["materials"][SCENARIOS[i]])}
                    for i, sid in enumerate(ids)]
        base["policy"] = tp.TFRL_ACE_PROGRAM_ID
        base["phase_material"] = {tp.TFRL_ACE_PHASE_NAME: {
            "instruction_fill": None, "instruction_template": ace.INSTRUCTION_RELPATH.replace("configs/", "", 1),
            "predecessor_binding": "none", "response_format_id": tp.TFRL_ACE_RESPONSE_FORMAT_ID}}
        base["tfrl_ace_reflector"] = {"playbook": dict(pins["playbook"]), "token_cap": int(pins["token_cap"]), "carriers": carriers}
        what = ("Decision 263-A ACE reflector contact: one text-only contact per scenario reading that scenario's credit tables and the "
                "current playbook and answering under the saea-ace-delta-items-v1 schema.")
    base["what_this_is"] = what + " Readiness HELD: this registration authorises no flight, no readiness flip and no admission entry."
    for key in ("instruction_note", "modality_note", "roster_note", "scoring_note", "task_instruction_note"):
        if key == "modality_note":
            base[key] = ("TEXT ONLY: the construction-proposer-text arm is bound by the D2 freeze to its text fields; no audio part and "
                         "no speech-feature packet is ever opened. The carrier row's audio seconds are declared as a positive ceiling "
                         "because the execution contract requires a positive declaration; realised speech seconds read 0.")
        elif key == "roster_note":
            base[key] = (f"The flown population is the {len(ids)} CARRIER rows of {roster['relpath']} (split identity "
                         f"{roster['split_identity_hash']}), a seeded selection of TRAIN Fold B; a carrier is an identity anchor only.")
        elif key == "instruction_note":
            base[key] = "The contact's instruction is rendered at flight time from the pinned aggregate artefacts and is never written to a receipt."
        elif key == "scoring_note":
            base[key] = "Only the 'cost' scorer: a proposal is an ARTIFACT validated or curated offline, never an answer to a scored row."
        else:
            base.pop(key, None)
    base["task_instruction"] = ("You are one contact of an automated optimisation loop for a spoken-language-understanding system. "
                                "Answer exactly once, in the closed format the instruction names.")
    baseline_doc = base
    exp_raw = rd("configs/experiment/slurp-native-stage3-gepa-r01-v1.json", repo_root)
    exp = json.loads(exp_raw)
    cell = exp["cells"][0]
    exp["cells"] = [cell]            # the GEPA parent carries a separate FIT cell; the text-only cells declare no FIT identity
    cell.update(cell_id=names["experiment"], run_id=names["run_id"], attempt_id=names["attempt_id"],
                baseline_fragment=names["baseline"], dataset_fragment="slurp-speech-native-evo-fold-b-1080")
    exp.update(experiment_id=names["run_id"], fragment_kind=f"saea-{names['experiment']}", date=tf.DATE)
    parent_exp = json.loads(rd(f"configs/experiment/{parent_names('arm')['experiment']}.json", repo_root))
    exp["split_id"] = parent_exp["split_id"]
    exp["service_session"] = tf.SESSION
    contacts = len(ids)
    planned = tp.planned_model_calls(contacts)
    audio = math.ceil(sum(float(i["audio_seconds"]) for i in json.loads(rd(roster["relpath"], repo_root))["items"]) * (1 + tf.RETRIES)) if (repo_root / roster["relpath"]).exists() else 0
    exp["population"] = {"count": contacts, "dataset_fragment": "slurp-speech-native-evo-fold-b-1080",
                         "decision_population": f"Exactly the {contacts} CARRIER rows of {roster['relpath']}.",
                         "split_identity_hash": roster["split_identity_hash"]}
    exp["populations"] = [{"dataset_fragment": "slurp-speech-native-evo-fold-b-1080", "ids": ids}]
    exp["execution_plan"] = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": tf.PLANNED_GPU_HOURS_TEXT_ONLY,
                             "planned_model_calls": planned, "planned_speech_audio_seconds": max(audio, 1), "split_role": "discovery",
                             "planned_speech_audio_seconds_note": "text-only contacts under the D2 freeze: realised speech seconds read 0 <= the declared ceiling"}
    exp["family_budget"] = {"asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
                            "fit_endpoint_calls_cap": 0, "generation_calls_cap": planned,
                            "gpu_hours_fit_inclusive": tf.PLANNED_GPU_HOURS_TEXT_ONLY, "native_task_contract_calls_cap": 0,
                            "official_complete_scoring_jobs": 0, "repeated_speech_audio_seconds_cap": max(audio, 1)}
    exp["generation_budget"] = {"cap": planned, "target": planned,
                                "definition": (f"{contacts} carriers x (1 + {tf.RETRIES} registered retries) = {planned} calls, "
                                               "RUN-CUMULATIVE across every attempt of this run id; one phase, max_contacts 1.")}
    exp["stage3_algorithm"] = text_only_label(kind)
    exp["purpose"] = (f"{what} Text-only form: no benefit is claimed (fewer than 200 rows). Aggregates of the sealed construction-source lock column "
                      "(R01C, TRAIN rows outside both folds) credit; no per-row gold, no utterance text, no output text.")
    exp["failure_policy"] = ("Stop on the first failure and preserve every contact; the registered retries are the only re-asks. "
                             "No re-sampling and no best-of-N over proposals.")
    exp["split_id_note"] = "The runtime split id equals the dataset fragment split_name; the population is the explicit populations block."
    decision_id = f"slurp-tfrl-proposers-i{iteration}-admission-v1"
    requirements = [{"kind": "decision", "expected_decision_id": decision_id,
                     "relpath": f"coordination/slurp-tfrl-proposers-i{iteration}-v1/root-admission-v1.json",
                     "sha256": ZERO, "reason": f"Decision {decision_id} pinned by scripts/flights/repin_cell.py."}]
    for label in ("tables", "context") if kind == "typed" else ("playbook",):
        requirements.append({"kind": "preparation", "reason": f"The pinned {label} artefact the contact renders (data-root relative).",
                             "relpath": pins[label]["relpath"], "sha256": pins[label]["sha256"]})
    cell["readiness"] = {"reason": what + HELD, "requirements": requirements, "state": "held"}
    cell["allowed_execution_stages"] = ["check", "worker", "campaign"]
    base_out, exp_out = f"configs/baseline/{names['baseline']}.json", f"configs/experiment/{names['experiment']}.json"
    left = [m for m in re.findall(r"gepa|GEPA", json.dumps(exp) + json.dumps(baseline_doc)) if m]
    if write:
        wr(base_out, dump_like(base_raw, baseline_doc), repo_root)
        wr(exp_out, dump_like(exp_raw, exp), repo_root)
        plan = {"cells": [{"cell": names["experiment"], "experiment": names["experiment"]}], "schema": "saea-campaign-plan-v1"}
        wr(f"configs/campaign/{names['experiment']}.json", json.dumps(plan, indent=2) + "\n", repo_root)
    return {"baseline": base_out, "experiment": exp_out, "roster": roster, "carriers": len(ids), "planned_calls": planned,
            "gepa_residue": len(left), "kind": kind, "_baseline": baseline_doc, "_experiment": exp}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--iteration", type=int, required=True, choices=tf.ITERATIONS)
    parser.add_argument("--spec", default=None, help="JSON {typed?, parent?, ace}; default is the iteration-1 stall form")
    parser.add_argument("--dry-run", action="store_true", help="derive and verify in memory; write nothing")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else {"typed": None, "parent": None, "ace": {"iteration": args.iteration}}
    result = derive_iteration(args.iteration, spec, write=not args.dry_run)
    result.pop("_documents", None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
