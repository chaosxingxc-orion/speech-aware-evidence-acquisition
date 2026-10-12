#!/usr/bin/env python3
"""Equivalence proofs AT-M0 / AT-M1 / AT-M2 of the evidence-consumption module.

Design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
section 4, migration step 2; coordinator rulings R1 and R2. Model-free and
contact-free: no model, server, GPU, network, flight, lease or ``core.flight.cli``.

For each case the script writes a module block whose component params are the
FLOWN bytes of each component's own admitting cell (AGREE's agreement term from
cell AGREE, the centroid key and the citation contract from cell COMP-1, the
re-listen block from cell E4-1, the Reviewer repair from cell G5), compiles it
with ``rails.consumption_module.compile_module`` for the SLURP carrier hooks,
and rebuilds each target cell's baseline fragment by replacing its four
policy-owned keys (``policy``, ``knowledge_stores``, ``native_episode``,
``phase_material``) with the compiled blocks. Every other key -- cell identity
and pinned prepared artifacts, never the module's -- is the target's own.

The proof is then made through the SAME composition function the runtime uses
(``core.config.compose``): the four fragments are written into a scratch
``configs/`` tree (model, dataset and experiment as their exact bytes; the
baseline as the rebuilt object) and composed; the composed config hash must
equal the target's own composed hash (and, where given, the hash a record
pinned). The report also names every differing leaf path between the compiled
blocks and the target's own policy blocks (must be empty).

Cases:

* ``m0`` -- every catalogued component ``off`` -> the CURRENT lock v2.1 (owner
  decision 204; migration step 6): ``lock: v2.1`` compiles to the bytes cell G5
  flew (arm, smoke), which are the v2.0 lock with the Reviewer template moved;
  and, kept as the second case so A2 and every queued v2.0 cell stay provable,
  no ``lock`` key -> the v2.0 lock (arm, smoke).
* ``m1`` -- the AGREE component alone -> cell AGREE (arm, smoke); plus the
  sealed-pool binding: the rebuilt arm's composed hash must equal the
  ``config.config_hash`` its sealed run manifest
  (``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``, under ``SPEECHRL_DATA_DIR``)
  records, i.e. the module-compiled policy is the exact configuration every
  request of that pool was rendered from.
* ``m2`` -- AGREE + centroid + citation -> cell COMP-1 (arm, smoke); AGREE +
  centroid -> cell COMP-1b (arm, smoke), at HEAD and at COMP-1b's
  registration commit (composed hashes ``8c4517a3...`` / ``3d9b7226...``).
* ``extra`` -- AGREE + re-listen (shadow) -> cell E4-1; the Reviewer repair
  alone -> cell G5.
* ``m4`` -- AGREE + ``top2-contrast`` as a ``column`` -> cell P-SV-1's
  registered branch block and program; AGREE + ``forced-candidate-list`` as a
  ``column`` -> cell P-SV-2's (arm and smoke fragments). The P-SV cells fly on
  TRAIN Fold B, so their Perception and Solver ``query_source`` pins are
  roster pins, not policy: the proof requires the compiled branch block to be
  the cell's own bytes, the program id and ceiling to be the cell's, and every
  other differing policy leaf to be a ``query_source`` leaf.
* ``m6`` -- migration step 6: the module's first end-to-end cell. Each of the
  three cells (arm, smoke, in-chain A/A) is compiled from ITS OWN declared
  ``native_episode.consumption_module`` block and must compose to its own
  hash; the arm and smoke blocks, compiled onto cell A2's own fragments (A2's
  roster pins), must differ from A2's policy blocks at EXACTLY the lock-v2.1
  Reviewer template leaf; the A/A must carry exactly the lock-v2.1 blocks on
  its roster and differ from A2's A/A at exactly the Reviewer template and
  the recall k (A2's A/A flew k 60 at w_agree 0, a proven supply no-op). The
  full composed-config diff against the A2 cell is listed and classified
  (policy / the module block itself / bookkeeping / experiment fragment).
* ``e220`` -- the same transfer on Earnings-22 (2026-10-11), whose direct layer is the shared base fragment
  ``e22-native-window-direct-base-v1`` alone: with no direct parent cell, each all-off cell's composed policy-owned
  blocks are compared with that base fragment's instead of a parent cell's.
* ``a2t0`` / ``e210`` -- the carrier transfer (direction 205, design 2b.3):
  the all-off block of the ``audio2tool`` / ``earnings`` profile compiles to
  that carrier's DIRECT layer (neither carrier has a locked system), whose
  policy blocks must equal the named direct baseline fragment byte for byte
  (``a2t-native-system-direct-v1`` / ``e21-native-window-direct-full44-v1``).
  Each registered all-off cell (arm, smoke) declares the block in its
  experiment fragment (``consumption_module_declaration``; a direct program
  carries no ``native_episode``, so the loader-verified slot is unavailable);
  the block must be the all-off block, compile to the cell's own composed
  hash, and the cell's composed config must differ from its direct parent
  cell (the A2T-AA pass A / smoke; the E21 full44 / four-row direct cells) by
  NO policy leaf -- only fit identity, prose and the experiment fragment's own
  block, none of which enters a request.

    python scripts/analysis/module_equivalence_proof.py --at all
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    DECISION_SUPPLY_PATH, carrier_module_hooks,
)

AGREE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
COMP1_BASELINE = "configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json"
RELISTEN_BASELINE = "configs/baseline/slurp-native-stage3-relisten-fold-a-baseline-v1.json"
G5_BASELINE = "configs/baseline/slurp-native-stage3-g5-fold-a-baseline-v1.json"
#: The scope rule's admitting read (owner decision 195 = B).
SCOPE_RULE_RECORD = "docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md"

#: COMP-1b's registration commit and the composed hashes its exposure-ledger
#: rows pinned at registration (arm, smoke).
COMP1B_REGISTRATION_COMMIT = "6291c23de"
COMP1B_REGISTERED_HASHES = {
    "slurp-native-stage3-comp1b-fold-a-v1": (
        "8c4517a3809f77b3973f683d488dcd2f4ea72eec05103408a2a20e1802c7d6f1"
    ),
    "slurp-native-stage3-comp1b-fold-a-smoke-4-v1": (
        "3d9b7226067f67a34207c57183b33b71193ac014c2cfd78ed0bc6e235c944243"
    ),
}
AGREE_SEALED_RUN_ID = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
#: AT-M4 targets: {baseline fragment: the Perception component its B branch carries}.
PSV_TARGETS = {
    "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1.json": cm.TOP2_CONTRAST,
    "configs/baseline/slurp-native-stage3-psv1-fold-b-smoke-4-baseline-v1.json": cm.TOP2_CONTRAST,
    "configs/baseline/slurp-native-stage3-psv2-fold-b-baseline-v1.json": cm.FORCED_CANDIDATE_LIST,
    "configs/baseline/slurp-native-stage3-psv2-fold-b-smoke-4-baseline-v1.json": cm.FORCED_CANDIDATE_LIST,
    # P-SV-4 (2026-09-30): the key_source column (key-source:k6p).
    "configs/baseline/slurp-native-stage3-psv4-fold-b-baseline-v1.json": cm.KEY_SOURCE_K6P,
    "configs/baseline/slurp-native-stage3-psv4-fold-b-smoke-4-baseline-v1.json": cm.KEY_SOURCE_K6P,
}
BRANCH_BLOCK_PATH = ("native_episode", "roles", "perception", "branches")
AGREE_ARM_EXPERIMENT = "slurp-native-stage3-agree-w1-fold-a-v1"


def _read_json(relpath: str, repo_root: Path = REPO_ROOT) -> dict:
    return json.loads((repo_root / relpath).read_text(encoding="utf-8"))


def _node(document: dict, path) -> dict:
    for key in path:
        document = document[key]
    return document


def component_entries(repo_root: Path = REPO_ROOT) -> dict[str, dict]:
    """One ``on``/``shadow`` component entry per compiled component, its params
    taken from the flown bytes of the cell that admits it."""

    agree_seed = _node(_read_json(AGREE_BASELINE, repo_root), DECISION_SUPPLY_PATH)
    comp1 = _read_json(COMP1_BASELINE, repo_root)
    comp1_seed = _node(comp1, DECISION_SUPPLY_PATH)
    relisten = _read_json(RELISTEN_BASELINE, repo_root)["native_episode"]["relisten"]
    g5 = _read_json(G5_BASELINE, repo_root)
    return {
        cm.AGREE_VOTE_SEED: {
            "component_id": cm.AGREE_VOTE_SEED, "state": "on",
            "admitted_by": "registry row 161", "record": AGREE_BASELINE,
            "params": {
                "w_agree": agree_seed["rank_weights"]["w_agree"],
                "k": agree_seed["k"],
                "agreement_source": agree_seed["agreement_source"],
            },
        },
        cm.CENTROID_BOUNDARY_KEY: {
            "component_id": cm.CENTROID_BOUNDARY_KEY, "state": "on",
            "admitted_by": "registry row 152", "record": COMP1_BASELINE,
            "params": {"facet_source": comp1_seed["facet_source"]},
        },
        cm.SOLVER_CITATION_CONTRACT: {
            "component_id": cm.SOLVER_CITATION_CONTRACT, "state": "on",
            "admitted_by": "registry row 152", "record": COMP1_BASELINE,
            "params": {
                "instruction_template": comp1["phase_material"]["solver"]["instruction_template"],
                "response_format_id": comp1["phase_material"]["solver"]["response_format_id"],
                "deliver_normaliser": comp1["native_episode"]["deliver_normaliser"]["normaliser"],
            },
        },
        cm.RELISTEN: {
            "component_id": cm.RELISTEN, "state": "shadow",
            "admitted_by": "registry row 185", "record": RELISTEN_BASELINE,
            "params": relisten,
        },
        cm.SCOPE_RULE: {
            "component_id": cm.SCOPE_RULE, "state": "on",
            "admitted_by": "registry row 195", "record": SCOPE_RULE_RECORD,
            "params": copy.deepcopy(dict(
                carrier_module_hooks(repo_root=repo_root).deliver_stages[cm.SCOPE_RULE]["params"]
            )),
        },
        cm.REVIEWER_G5_REPAIR: {
            "component_id": cm.REVIEWER_G5_REPAIR, "state": "on",
            "admitted_by": "registry rows 153, 189", "record": G5_BASELINE,
            "params": {"instruction_template": g5["phase_material"]["reviewer"]["instruction_template"]},
        },
    }


def module_block(armed: tuple[str, ...], repo_root: Path = REPO_ROOT, *, lock: str | None = None) -> dict:
    """A block listing EVERY catalogued component: the ``armed`` ones with
    their flown params, every other one ``off``; ``lock`` names a lock
    version (``None``: no ``lock`` key, the v2.0 layer every pre-step-6 block
    compiles onto)."""

    entries = component_entries(repo_root)
    components = [
        entries[spec.component_id] if spec.component_id in armed
        else {"component_id": spec.component_id, "state": "off"}
        for spec in cm.COMPONENT_CATALOGUE
    ]
    block = {
        "module_id": cm.CONSUMPTION_MODULE_ID, "profile": "slurp",
        "components": components, "columns": [],
    }
    if lock is not None:
        block["lock"] = lock
    return block


#: The v2.1 lock's flown bytes: cell G5 (``docs/results/2026-09-30-slurp-v2-1-lock-v1.md``).
LOCK_V2_1_TARGETS = ("slurp-native-stage3-g5-fold-a-v1", "slurp-native-stage3-g5-fold-a-smoke-4-v1")
LOCK_V2_0_TARGETS = ("slurp-native-default-plan-lock-v1", "slurp-native-default-plan-lock-smoke-4-v1")

#: ``(at, armed, target experiments, git rev or None, lock)`` rows are read as
#: 3-tuples (lock ``None``) or 4-tuples.
CASES: dict[str, list[tuple]] = {
    # at -> [(armed components, target experiments, git rev or None = working tree[, lock])]
    "m0": [
        ((), LOCK_V2_1_TARGETS, None, "v2.1"),
        ((), LOCK_V2_0_TARGETS, None),
    ],
    "m1": [((cm.AGREE_VOTE_SEED,), (AGREE_ARM_EXPERIMENT, "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"), None)],
    "m2": [
        ((cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY, cm.SOLVER_CITATION_CONTRACT),
         ("slurp-native-stage3-comp1-fold-a-v1", "slurp-native-stage3-comp1-fold-a-smoke-4-v1"), None),
        ((cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY),
         ("slurp-native-stage3-comp1b-fold-a-v1", "slurp-native-stage3-comp1b-fold-a-smoke-4-v1"), None),
        ((cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY),
         ("slurp-native-stage3-comp1b-fold-a-v1", "slurp-native-stage3-comp1b-fold-a-smoke-4-v1"),
         COMP1B_REGISTRATION_COMMIT),
    ],
    "extra": [
        ((cm.AGREE_VOTE_SEED, cm.RELISTEN),
         ("slurp-native-stage3-relisten-fold-a-v1", "slurp-native-stage3-relisten-fold-a-smoke-4-v1"), None),
        ((cm.REVIEWER_G5_REPAIR,),
         ("slurp-native-stage3-g5-fold-a-v1", "slurp-native-stage3-g5-fold-a-smoke-4-v1"), None),
    ],
}


def _fragment_text(kind: str, name: str, rev: str | None, repo_root: Path) -> str:
    relpath = f"configs/{kind}/{name}.json"
    if rev is None:
        return (repo_root / relpath).read_text(encoding="utf-8")
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{rev}:{relpath}"],
        capture_output=True, check=True,
    )
    return completed.stdout.decode("utf-8")


def rebuild_and_compose(
    composed_policy: cm.ComposedPolicy, experiment: str, *, rev: str | None = None,
    repo_root: Path = REPO_ROOT, declared_block: dict | None = None,
) -> dict:
    """Compose the target cell twice through ``core.config.compose`` in a
    scratch ``configs/`` tree -- once with its own baseline bytes, once with
    the module-rebuilt baseline -- and report both hashes and the diff."""

    cell = json.loads(_fragment_text("experiment", experiment, rev, repo_root))["cells"][0]
    names = {
        "model": cell["model_fragment"], "dataset": cell["dataset_fragment"],
        "baseline": cell["baseline_fragment"], "experiment": experiment,
    }
    texts = {kind: _fragment_text(kind, name, rev, repo_root) for kind, name in names.items()}
    own_baseline = json.loads(texts["baseline"])
    rebuilt = composed_policy.apply_to(own_baseline)
    if declared_block is not None:
        # A cell that DECLARES its block (migration step 6) carries the
        # declaration beside the compiled blocks, exactly as the loader reads it.
        rebuilt["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = copy.deepcopy(declared_block)
    hashes = {}
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        for variant, baseline_text in (
            ("own", texts["baseline"]),
            ("module", json.dumps(rebuilt, ensure_ascii=False, indent=2)),
        ):
            for kind, name in names.items():
                path = root / variant / "configs" / kind / f"{name}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(baseline_text if kind == "baseline" else texts[kind], encoding="utf-8")
            hashes[variant] = compose(
                root / variant, names["model"], names["dataset"], names["baseline"], experiment,
            ).config_hash
    return {
        "experiment": experiment,
        "rev": rev or "working-tree",
        "lock": composed_policy.lock_version,
        "program_id": composed_policy.program_id,
        "program_ceiling": composed_policy.program_ceiling,
        "own_composed_hash": hashes["own"],
        "module_composed_hash": hashes["module"],
        "composed_identical": hashes["own"] == hashes["module"],
        "baseline_object_identical": rebuilt == own_baseline,
        "differing_policy_paths": cm.differing_paths(
            composed_policy.values_on_roster_of(own_baseline),
            cm.policy_owned_values(own_baseline),
        ),
    }


def sealed_pool_binding(arm_module_hash: str) -> dict:
    """The AGREE sealed pool's run manifest records the composed config hash
    every request of that pool was rendered from."""

    data_dir = os.environ.get(
        "SPEECHRL_DATA_DIR", (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
    run_dir = Path(data_dir) / "runs" / AGREE_SEALED_RUN_ID
    manifests = sorted(run_dir.glob(f"*/{AGREE_SEALED_RUN_ID}.run-manifest.json"))
    if not manifests:
        return {"available": False, "run_dir": str(run_dir)}
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    sealed = manifest["config"]["config_hash"]
    return {
        "available": True,
        "run_manifest": str(manifests[0].relative_to(Path(data_dir))),
        "sealed_config_hash": sealed,
        "sealed_fragments": manifest["config"]["fragments"],
        "module_composed_hash": arm_module_hash,
        "identical": sealed == arm_module_hash,
    }


def psv_column_block(baseline_relpath: str, repo_root: Path = REPO_ROOT) -> dict:
    """The module block that should compile to a P-SV cell: AGREE on with the
    cell's own agreement term, the cell's B-branch component as a ``column``
    (params and prepared seed from the cell's own B row)."""

    cell = _read_json(baseline_relpath, repo_root)
    component = PSV_TARGETS[baseline_relpath]
    branches = _node(cell, BRANCH_BLOCK_PATH)
    b_row = branches["branches"][0]
    seed = _node(cell, DECISION_SUPPLY_PATH)
    agree = component_entries(repo_root)[cm.AGREE_VOTE_SEED]
    agree["params"] = {"w_agree": seed["rank_weights"]["w_agree"], "k": seed["k"],
                       "agreement_source": seed["agreement_source"]}
    params = {"max_supplied_items": b_row["max_supplied_items"]}
    for key in cm.PERCEPTION_AXIS_COMPONENTS[component]:
        params[key] = b_row[key]
    entries = {
        cm.AGREE_VOTE_SEED: agree,
        component: {"component_id": component, "state": "column", "admitted_by": "registry row 193",
                    "record": baseline_relpath, "params": params},
    }
    column = {"column_id": b_row["branch_id"], "toggle": component, "to": "on",
              "level": branches["level"]}
    if "prepared_seed" in b_row:
        column["prepared_seed"] = b_row["prepared_seed"]
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID, "profile": "slurp",
        "components": [entries.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
        "columns": [column],
    }


def run_m4(repo_root: Path = REPO_ROOT) -> dict:
    hooks = carrier_module_hooks(repo_root=repo_root)
    results, ok = [], True
    for relpath, component in PSV_TARGETS.items():
        cell = _read_json(relpath, repo_root)
        composed = cm.compile_module(psv_column_block(relpath, repo_root), hooks, repo_root=repo_root)
        compiled_block = _node(composed.values(), BRANCH_BLOCK_PATH)
        own_block = _node(cell, BRANCH_BLOCK_PATH)
        diff = cm.differing_paths(composed.values(), cm.policy_owned_values(cell))
        row = {
            "baseline": relpath, "component": component,
            "program_id": composed.program_id, "program_ceiling": composed.program_ceiling,
            "cell_program_id": cell["policy"],
            "branch_block_identical": cm._canonical(compiled_block) == cm._canonical(own_block),
            "branch_block_sha256": cm._sha256_text(cm._canonical(compiled_block)),
            "non_roster_differing_paths": [p for p in diff if ".query_source." not in p],
            "roster_pin_paths_differing": len([p for p in diff if ".query_source." in p]),
        }
        row["ok"] = (row["branch_block_identical"] and composed.program_id == cell["policy"]
                     and not row["non_roster_differing_paths"])
        ok &= row["ok"]
        results.append(row)
    return {"at": "m4", "results": results, "ok": bool(ok)}


#: Migration step 6: ``{key: (module cell, cell A2's counterpart)}``.
M6_CELLS = {
    "arm": ("slurp-native-stage3-module-comp1b-dev2000-added-v1", "slurp-native-stage3-comp1b-dev2000-added-v1"),
    "smoke": ("slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1",
              "slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1"),
    "aa": ("slurp-native-stage3-module-comp1b-aa-dev2000-added-v1", "slurp-native-stage3-comp1-aa-dev2000-added-v1"),
}
REVIEWER_TEMPLATE_LEAF = "phase_material.reviewer.instruction_template"
BOUNDARY_K_LEAF = "knowledge_stores.intent-boundaries.phase_supply.perception.k"
#: The expected policy-leaf difference of each module cell from its A2 counterpart.
M6_EXPECTED_VS_A2 = {"arm": [REVIEWER_TEMPLATE_LEAF], "smoke": [REVIEWER_TEMPLATE_LEAF],
                     "aa": [BOUNDARY_K_LEAF, REVIEWER_TEMPLATE_LEAF]}
_M6_BOOKKEEPING = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is",
                   "fragment_kind")


def _composed_values(experiment: str, repo_root: Path) -> dict:
    cell = json.loads(_fragment_text("experiment", experiment, None, repo_root))["cells"][0]
    return compose(repo_root, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"],
                   experiment).values


def _classify(paths: list[str], experiment_keys: set[str]) -> dict[str, list[str]]:
    module_prefix = "native_episode." + cm.CONSUMPTION_MODULE_CONFIG_KEY
    out: dict[str, list[str]] = {"policy": [], "module_block": [], "bookkeeping": [], "experiment_fragment": [],
                                 "anything_else": []}
    for path in paths:
        if path.startswith(module_prefix):
            out["module_block"].append(path)
        elif path.split(".", 1)[0] in cm.POLICY_OWNED_KEYS:
            out["policy"].append(path)
        elif path.startswith(_M6_BOOKKEEPING):
            out["bookkeeping"].append(path)
        elif path.split(".", 1)[0] in experiment_keys:
            out["experiment_fragment"].append(path)
        else:
            out["anything_else"].append(path)
    return out


def run_m6(repo_root: Path = REPO_ROOT) -> dict:
    """Migration step 6: the module cell's bytes are the admitted A2 bytes
    except the lock-v2.1 Reviewer pin, and its A/A is lock v2.1."""

    hooks = carrier_module_hooks(repo_root=repo_root)
    lock_v2_1 = dict(hooks.lock_versions["v2.1"]())
    results, ok = [], True
    for key, (experiment, a2_experiment) in M6_CELLS.items():
        cell = json.loads(_fragment_text("experiment", experiment, None, repo_root))["cells"][0]
        own = _read_json(f"configs/baseline/{cell['baseline_fragment']}.json", repo_root)
        block = own["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]
        composed_policy = cm.compile_module(block, hooks, repo_root=repo_root)
        row = rebuild_and_compose(composed_policy, experiment, repo_root=repo_root, declared_block=block)
        a2_cell = json.loads(_fragment_text("experiment", a2_experiment, None, repo_root))["cells"][0]
        a2_baseline = _read_json(f"configs/baseline/{a2_cell['baseline_fragment']}.json", repo_root)
        vs_a2 = cm.differing_paths(composed_policy.values_on_roster_of(a2_baseline),
                                   cm.policy_owned_values(a2_baseline))
        mine, theirs = _composed_values(experiment, repo_root), _composed_values(a2_experiment, repo_root)
        experiment_keys = set(json.loads(_fragment_text("experiment", experiment, None, repo_root)))
        row.update({
            "cell": key, "a2_counterpart": a2_experiment, "armed": [d.component_id for d in
                                                                   cm.parse_consumption_module_block(block).armed()],
            "module_block_sha256": composed_policy.config_block_sha256,
            "module_policy_on_a2_roster_differing_paths": vs_a2,
            "expected_differing_paths": M6_EXPECTED_VS_A2[key],
            "composed_config_diff_vs_a2": _classify(cm.differing_paths(mine, theirs), experiment_keys),
            "reviewer_template": {"a2": a2_baseline["phase_material"]["reviewer"]["instruction_template"],
                                  "module": own["phase_material"]["reviewer"]["instruction_template"]},
        })
        row["ok"] = (row["composed_identical"] and not row["differing_policy_paths"]
                     and vs_a2 == M6_EXPECTED_VS_A2[key]
                     and row["composed_config_diff_vs_a2"]["policy"] == M6_EXPECTED_VS_A2[key]
                     and not row["composed_config_diff_vs_a2"]["anything_else"])
        if key == "aa":
            row["off_arm"] = cm.is_module_off_block(block)
            row["lock_v2_1_differing_paths"] = cm.differing_paths(
                cm._rebind_roster(json.loads(json.dumps(lock_v2_1)), own, hooks.roster_pin_paths),
                cm.policy_owned_values(own),
            )
            row["ok"] &= row["off_arm"] and not row["lock_v2_1_differing_paths"]
        ok &= row["ok"]
        results.append(row)
    return {"at": "m6", "results": results, "ok": bool(ok)}


#: Carrier transfer: ``{at: {profile, the direct baseline the layer is, {cell key: (all-off cell, direct parent)}}}``.
ALLOFF_CASES = {
    "a2t0": {
        "profile": "audio2tool", "lock_fragment": "a2t-native-system-direct-v1",
        "cells": {"arm": ("a2t-native-stage3-module-alloff-v1", "a2t-stage3-aa-paired-400-a-v1"),
                  "smoke": ("a2t-native-stage3-module-alloff-smoke-4-v1", "a2t-stage3-aa-paired-400-smoke-4-v1")},
    },
    "e210": {
        "profile": "earnings", "lock_fragment": "e21-native-window-direct-full44-v1",
        "cells": {"arm": ("earnings21-native-stage3-module-alloff-v1", "e21-native-window-direct-full44-v1"),
                  "smoke": ("earnings21-native-stage3-module-alloff-smoke-4-v1",
                            "e21-native-window-four-row-direct-vs-system-v1")},
    },
    # Earnings-22 has no direct parent CELL: the direct layer is the shared base fragment alone, so the parent slot is
    # ``None`` and the cell's composed policy blocks are compared with the base fragment's instead.
    "e220": {
        "profile": "earnings22", "lock_fragment": "e22-native-window-direct-base-v1",
        "cells": {"arm": ("earnings22-native-stage3-module-alloff-v1", None),
                  "smoke": ("earnings22-native-stage3-module-alloff-smoke-4-v1", None)},
    },
}
#: The experiment-fragment key a direct all-off cell declares its block under.
DECLARATION_KEY = "consumption_module_declaration"
_ALLOFF_BOOKKEEPING = ("live_phase_fit.", "what_this_is")


def alloff_block(profile: str) -> dict:
    """The all-off block of ``profile``: every catalogued component ``off``, no column, no lock key."""

    return {
        "module_id": cm.CONSUMPTION_MODULE_ID, "profile": profile,
        "components": [{"component_id": spec.component_id, "state": "off"} for spec in cm.COMPONENT_CATALOGUE],
        "columns": [],
    }


def _classify_alloff(paths: list[str], experiment_keys: set[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"policy": [], "bookkeeping": [], "experiment_fragment": [], "anything_else": []}
    for path in paths:
        top = path.split(".", 1)[0]
        if top in cm.POLICY_OWNED_KEYS:
            out["policy"].append(path)
        elif path.startswith(_ALLOFF_BOOKKEEPING):
            out["bookkeeping"].append(path)
        elif top in experiment_keys:
            out["experiment_fragment"].append(path)
        else:
            out["anything_else"].append(path)
    return out


def run_alloff(at: str, repo_root: Path = REPO_ROOT) -> dict:
    """``a2t0`` / ``e210``: the carrier's all-off arm is its direct baseline's bytes."""

    spec = ALLOFF_CASES[at]
    hooks = cm.resolve_carrier_hooks(spec["profile"], repo_root=repo_root)
    block = alloff_block(spec["profile"])
    composed_policy = cm.compile_module(block, hooks, repo_root=repo_root)
    lock = _read_json(f"configs/baseline/{spec['lock_fragment']}.json", repo_root)
    lock_diff = cm.differing_paths(composed_policy.values(), cm.policy_owned_values(lock))
    results = [{
        "target": "direct-layer", "fragment": spec["lock_fragment"], "program_id": composed_policy.program_id,
        "program_ceiling": composed_policy.program_ceiling, "module_block_sha256": composed_policy.config_block_sha256,
        "differing_policy_paths": lock_diff, "ok": not lock_diff,
    }]
    ok = not lock_diff
    for key, (experiment, parent) in spec["cells"].items():
        path = repo_root / "configs" / "experiment" / f"{experiment}.json"
        if not path.is_file():
            results.append({"cell": key, "experiment": experiment, "registered": False, "ok": False})
            ok = False
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        declared = (document.get(DECLARATION_KEY) or {}).get("block")
        declared_policy = cm.compile_module(declared, hooks, repo_root=repo_root)
        row = rebuild_and_compose(declared_policy, experiment, repo_root=repo_root)
        if parent is None:
            # No parent cell: the cell's composed policy-owned blocks must equal the shared base fragment's.
            diff = {"policy": cm.differing_paths(cm.policy_owned_values(_composed_values(experiment, repo_root)),
                                                 cm.policy_owned_values(lock)),
                    "bookkeeping": [], "experiment_fragment": [], "anything_else": []}
        else:
            parent_document = json.loads(_fragment_text("experiment", parent, None, repo_root))
            diff = _classify_alloff(
                cm.differing_paths(_composed_values(experiment, repo_root), _composed_values(parent, repo_root)),
                set(document) | set(parent_document),
            )
        row.update({
            "cell": key, "direct_parent": parent or spec["lock_fragment"], "declared_is_the_all_off_block": declared == block,
            "off_arm": cm.is_module_off_block(declared, repo_root=repo_root),
              # The catalogue can grow after an immutable OFF cell is registered.
              # Compare compiled policy, retaining declaration inequality as evidence.
              "canonical_alloff_policy_differences": cm.differing_paths(
                  declared_policy.values(), composed_policy.values()),
              "omitted_components_default_off": sorted(
                  {item.component_id for item in cm.COMPONENT_CATALOGUE}
                  - {item["component_id"] for item in declared["components"]}),
            "composed_config_diff_vs_parent": diff,
        })
        row["ok"] = bool(row["composed_identical"] and not row["differing_policy_paths"]
                           and not row["canonical_alloff_policy_differences"] and row["off_arm"]
                         and not diff["policy"] and not diff["anything_else"])
        ok &= row["ok"]
        results.append(row)
    return {"at": at, "profile": spec["profile"], "results": results, "ok": bool(ok)}


def run_case(at: str, repo_root: Path = REPO_ROOT) -> dict:
    if at == "m4":
        return run_m4(repo_root)
    if at == "m6":
        return run_m6(repo_root)
    if at in ALLOFF_CASES:
        return run_alloff(at, repo_root)
    hooks = carrier_module_hooks(repo_root=repo_root)
    results = []
    ok = True
    for armed, experiments, rev, *rest in CASES[at]:
        lock = rest[0] if rest else None
        composed_policy = cm.compile_module(module_block(armed, repo_root, lock=lock), hooks, repo_root=repo_root)
        for experiment in experiments:
            row = rebuild_and_compose(composed_policy, experiment, rev=rev, repo_root=repo_root)
            row["armed"] = list(armed)
            if rev is not None and experiment in COMP1B_REGISTERED_HASHES:
                row["registered_hash"] = COMP1B_REGISTERED_HASHES[experiment]
                row["matches_registered_hash"] = row["module_composed_hash"] == row["registered_hash"]
                ok &= row["matches_registered_hash"]
            ok &= row["composed_identical"] and not row["differing_policy_paths"]
            results.append(row)
    report = {"at": at, "results": results}
    if at == "m1":
        arm = next(r for r in results if r["experiment"] == AGREE_ARM_EXPERIMENT)
        binding = sealed_pool_binding(arm["module_composed_hash"])
        report["sealed_pool"] = binding
        if binding["available"]:
            ok &= binding["identical"]
    report["ok"] = bool(ok)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--at", choices=(*CASES, "m4", "m6", *ALLOFF_CASES, "all"), nargs="+", default=["all"])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    ats = (*CASES, "m4", "m6", *ALLOFF_CASES) if "all" in args.at else tuple(args.at)
    reports = [run_case(at, args.repo_root) for at in ats]
    print(json.dumps({"reports": reports, "ok": all(r["ok"] for r in reports)}, indent=2, sort_keys=True))
    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
