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

* ``m0`` -- every catalogued component ``off`` -> the v2.0 lock (arm, smoke).
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

    python scripts/analysis/module_equivalence_proof.py --at all
"""

from __future__ import annotations

import argparse
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
        cm.REVIEWER_G5_REPAIR: {
            "component_id": cm.REVIEWER_G5_REPAIR, "state": "on",
            "admitted_by": "registry rows 153, 189", "record": G5_BASELINE,
            "params": {"instruction_template": g5["phase_material"]["reviewer"]["instruction_template"]},
        },
    }


def module_block(armed: tuple[str, ...], repo_root: Path = REPO_ROOT) -> dict:
    """A block listing EVERY catalogued component: the ``armed`` ones with
    their flown params, every other one ``off``."""

    entries = component_entries(repo_root)
    components = [
        entries[spec.component_id] if spec.component_id in armed
        else {"component_id": spec.component_id, "state": "off"}
        for spec in cm.COMPONENT_CATALOGUE
    ]
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID, "profile": "slurp",
        "components": components, "columns": [],
    }


CASES: dict[str, list[tuple[tuple[str, ...], tuple[str, ...], str | None]]] = {
    # at -> [(armed components, target experiments, git rev or None = working tree)]
    "m0": [((), ("slurp-native-default-plan-lock-v1", "slurp-native-default-plan-lock-smoke-4-v1"), None)],
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
    repo_root: Path = REPO_ROOT,
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
        "program_id": composed_policy.program_id,
        "program_ceiling": composed_policy.program_ceiling,
        "own_composed_hash": hashes["own"],
        "module_composed_hash": hashes["module"],
        "composed_identical": hashes["own"] == hashes["module"],
        "baseline_object_identical": rebuilt == own_baseline,
        "differing_policy_paths": cm.differing_paths(
            composed_policy.values(), cm.policy_owned_values(own_baseline),
        ),
    }


def sealed_pool_binding(arm_module_hash: str) -> dict:
    """The AGREE sealed pool's run manifest records the composed config hash
    every request of that pool was rendered from."""

    data_dir = os.environ.get(
        "SPEECHRL_DATA_DIR", "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data",
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


def run_case(at: str, repo_root: Path = REPO_ROOT) -> dict:
    hooks = carrier_module_hooks(repo_root=repo_root)
    results = []
    ok = True
    for armed, experiments, rev in CASES[at]:
        composed_policy = cm.compile_module(module_block(armed, repo_root), hooks, repo_root=repo_root)
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
    parser.add_argument("--at", choices=(*CASES, "all"), default="all")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    ats = tuple(CASES) if args.at == "all" else (args.at,)
    reports = [run_case(at, args.repo_root) for at in ats]
    print(json.dumps({"reports": reports, "ok": all(r["ok"] for r in reports)}, indent=2, sort_keys=True))
    return 0 if all(r["ok"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
