#!/usr/bin/env python3
"""W-SV-1's delivering arm A, proven model-free: is its first Solver request the AGREE arm's own?

Cell W-SV-1 (owner decision 172) is the retained AGREE arm with two registered changes: the program
switched to its 13-ceiling uncited ``first`` twin and a Solver ``supply_variants`` group (B k-30,
T the twin, A the delivering arm, override-free and last). The instrument's premise
(docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md section 2) is
that A's request is the locked form's request "by construction"; this script PROVES it for this
cell the way the knowledge wave's shared A/A was proven
(``scripts/flights/wave/wave_shared_aa_proof.py``, the decision-160 method), reusing that family's
pure helpers and request-capture routine unchanged.

Three proofs, each model-free (zero model, server, tokenizer, encoder or scorer contacts):

1. **Composed config.** Both cells composed from their committed fragments and flattened; every
   differing leaf is classified: ``bookkeeping`` (identity, prose, budgets, readiness -- never read
   by the request composer), ``supply-pin`` (the AGREE arm's committed prepared first-phase supply
   pin, which W-SV-1 drops so the flip mints its own, item E16), ``program-switch`` (``policy``),
   ``variants-block`` (``native_episode.roles.solver.supply_variants.*``), or ``unclassified``
   (request-affecting: the verdict fails).
2. **Prepared supply.** ``core.flight.cli prepare-supply`` mints W-SV-1's first-phase supply into a
   scratch directory (never ``prepared/``); its ``output_sha256`` must equal the AGREE arm's
   registered digest and the AGREE arm's committed artifact's recomputed output digest.
3. **Request bytes.** Each cell's REAL dispatch against the REAL transport with a fake POST that
   answers canned, role-appropriate completions, serially, under ONE common scratch run id: W-SV-1's
   arm-A contact at the first Solver visit (``<program>:solver:2:<sample>``, the group's third and
   last arm) against the AGREE arm's first Solver contact (``<program>:solver:0:<sample>``) --
   POST body bytes must be identical on every row. Reported beside it, never gating the verdict:
   the twin T's POST body against A's (acceptance test AT2), B's against A's (expected to differ:
   the exemplar supply), and every OTHER contact of the episode mapped across the two programs
   (Perception, Reviewer, Planner and the revisit Solver, whose global index is 3 in W-SV-1 and 1
   in AGREE). The payload (the pre-transport custody document) carries the program-scoped contact
   id and, for arm contacts, ``variant_arm_id``; the leaf classes it differs in are listed for a
   few rows.

FINDING (first run, 2026-09-28, 120 rows): the POST bodies are NOT byte-identical, on every contact
of both cells. The model-visible request text carries two program-identity fields the switch moves:
the program id (and the node's global invocation index) inside every quoted prior contact id, and
``remaining_model_contacts`` in the task-state block (ceiling 13 against 11). The comparison is
therefore run twice -- exactly, and after :func:`normalise_program_identity` maps exactly those two
fields back -- and the verdict says which holds.

Exit 0 with verdict ``IDENTICAL`` when proofs 1-2 hold and every arm-A first Solver POST body is
byte-identical; exit 4 with ``IDENTICAL_MODULO_PROGRAM_IDENTITY`` when they are identical only after
the normalisation; exit 3 with ``DIFFERENT`` otherwise. No raw request text is written anywhere but
the scratch directory, and the raw capture files are deleted right after they are read. Usage, in WSL
from the worktree::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA \\
    python -B scripts/flights/wsv1/wsv1_arm_a_proof.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--rows N] [--output PATH]
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROOF_SCHEMA = "saea-wsv1-arm-a-proof-v1"
PACKAGE = "docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1"
DEFAULT_OUTPUT = PACKAGE + "/arm-a-proof-v1.json"

CELLS: dict[str, str] = {
    "wsv1": "slurp-native-stage3-wsv1-fold-a-v1",
    "agree_arm": "slurp-native-stage3-agree-w1-fold-a-v1",
}
PROGRAMS = {"wsv1": "phase-native-candidates-review-revise-variants3first-v1",
            "agree_arm": "phase-native-candidates-review-revise-v1"}
#: Solver invocation indices: W-SV-1's first visit fans out B (0), T (1), A (2); a revisit is 3.
ARM_INDEX = {"b-exk30": 0, "t-twin": 1, "a-base": 2}
WSV1_SOLVER_REVISIT, AGREE_SOLVER_REVISIT = 3, 1

AGREE_ARM_SUPPLY_OUTPUT_SHA256 = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
SUPPLY_PIN_PREFIX = "prepared_phase_supply"
VARIANTS_PREFIX = "native_episode.roles.solver.supply_variants"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_FLIGHTS = Path(__file__).resolve().parents[1]
P160 = _load(_FLIGHTS / "comp1" / "comp1_g5_shared_aa_proof.py", "comp1_g5_shared_aa_proof")
WAVE = _load(_FLIGHTS / "wave" / "wave_shared_aa_proof.py", "wave_shared_aa_proof")
flatten = P160.flatten

EXTRA_BOOKKEEPING = (
    ("execution_plan.", "the declared execution plan's budget numbers (the plan builder and the gate read them; "
                        "planned_model_calls = rows x 13 at the new ceiling); never request bytes"),
    ("native_contact_fit.contact_cap", "the FIT endpoint cap (rows x 13 x 4 at the new ceiling); never request bytes"),
)


def classify_leaf(leaf: str) -> tuple[str, str]:
    if leaf == "policy":
        return ("program-switch", "the registered program switch phase-native-candidates-review-revise-v1 -> "
                "-variants3first-v1 (the two fragments differ only in program_id and max_contacts); the program id "
                "reaches the custody contact id, and proof 3 shows it never reaches the POST body")
    if leaf == VARIANTS_PREFIX or leaf.startswith(VARIANTS_PREFIX + "."):
        return ("variants-block", "the registered Solver supply_variants block; arm A carries no override and "
                "renders from the episode's own QueryState (proof 3)")
    for prefix, reason in EXTRA_BOOKKEEPING:
        if leaf == prefix or (prefix.endswith(".") and leaf.startswith(prefix)):
            return "bookkeeping", reason
    klass, reason = WAVE.classify_leaf(leaf)
    return klass, reason


def config_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    flat_left, flat_right = flatten(left), flatten(right)
    rows = []
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a, b = flat_left.get(leaf, "<absent>"), flat_right.get(leaf, "<absent>")
        if a == b:
            continue
        klass, reason = classify_leaf(leaf)
        short = lambda v: v if len(json.dumps(v, default=str)) < 300 else "<long>"  # noqa: E731
        rows.append({"leaf": leaf, "wsv1": short(a), "agree_arm": short(b), "class": klass,
                     "request_affecting": klass == "unclassified", "reason": reason})
    return rows


def prove_supply(repo: Path, data: Path, lock: Path, scratch: Path) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    experiment = CELLS["wsv1"]
    path = scratch / "wsv1" / "phase-supply-v1.json"
    if path.exists():
        raise SystemExit(f"scratch supply {path} already exists; use a fresh --scratch")
    started = time.time()
    subprocess.run(
        [sys.executable, "-B", "-m", "speech_aware_evidence_acquisition.core.flight.cli", "prepare-supply",
         "--repo-root", str(repo), "--data-root", str(data), "--runtime-root", str(Path.home()),
         "--lock-path", str(lock), "--experiment", experiment, "--cell", experiment, "--output", str(path),
         "--workers", "4"],
        check=True, env=env, cwd=str(repo), stdout=subprocess.DEVNULL,
    )
    raw = path.read_bytes()
    minted = json.loads(raw)
    baseline = json.loads((repo / "configs" / "baseline" / "slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")
                          .read_text(encoding="utf-8"))
    pin = baseline["prepared_phase_supply"]
    pinned_raw = (data / pin["relpath"]).read_bytes()
    pinned = json.loads(pinned_raw)
    from speech_aware_evidence_acquisition.core.preparation import digest as _digest

    recomputed = _digest(pinned["output"])
    equal = minted["output_sha256"] == pinned["output_sha256"] == recomputed
    pinned_ok = P160._sha(pinned_raw) == pin["sha256"]
    return {
        "wsv1": {"command": f"core.flight.cli prepare-supply --experiment {experiment} --cell {experiment} "
                            "--output <scratch>/wsv1/phase-supply-v1.json",
                 "output_sha256": minted["output_sha256"], "file_sha256": P160._sha(raw),
                 "seconds": round(time.time() - started, 1)},
        "agree_arm": {"source": "the AGREE arm's committed artifact (the one that flew), read raw -- not re-minted",
                      "relpath": pin["relpath"], "file_sha256_matches_pin": pinned_ok,
                      "output_sha256": pinned["output_sha256"], "output_sha256_recomputed": recomputed},
        "agree_arm_registered_output_sha256": AGREE_ARM_SUPPLY_OUTPUT_SHA256,
        "output_digests_equal": equal,
        "equal_registered_and_committed": equal and pinned_ok and minted["output_sha256"] == AGREE_ARM_SUPPLY_OUTPUT_SHA256,
    }


def _launch_worker(repo: Path, args, *, cell: str, out: Path, rows: int | None,
                   common: tuple[str, int], raw: bool):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--repo-root", str(repo),
               "--data-root", str(args.data_root), "--lock-path", str(args.lock_path),
               "--worker-cell", cell, "--worker-out", str(out), "--worker-common", f"{common[0]}:{common[1]}"]
    if rows is not None:
        command += ["--rows", str(rows)]
    if raw:
        command.append("--worker-raw")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    log = out.with_suffix(".log").open("w", encoding="utf-8")
    return subprocess.Popen(command, env=env, cwd=str(repo), stdout=log, stderr=subprocess.STDOUT)


def _split(key: str) -> tuple[str, str, str, int, str]:
    """``(sample, program, role, index, rest)`` of ``<sample>|<program>:<role>:<index>:<sample...>``."""
    sample, contact = key.split("|", 1)
    program, role, index, rest = contact.split(":", 3)
    return sample, program, role, int(index), rest


#: The two program-identity fields the model-visible request text carries (found by this proof's first
#: run, 2026-09-28): (1) every quoted prior contact id embeds the program id and the node's global
#: invocation index (arm A is the Solver's third invocation, index 2, where AGREE's first Solver is 0;
#: a revisit is 3 against 1); (2) the task-state block states ``remaining_model_contacts``, which is
#: the program ceiling minus the contacts spent (13 - n against 11 - n). The normalisation below maps
#: (1) back to the AGREE spelling and masks (2); nothing else is touched.
_REMAINING = re.compile(r'(\\*"remaining_model_contacts\\*": )\d+')


def normalise_program_identity(body: str) -> str:
    text = body.replace(PROGRAMS["wsv1"], PROGRAMS["agree_arm"])
    text = re.sub(re.escape(PROGRAMS["agree_arm"]) + r":solver:(\d+):",
                  lambda m: f"{PROGRAMS['agree_arm']}:solver:{_SOLVER_INDEX_MAP.get(int(m.group(1)), int(m.group(1)))}:",
                  text)
    return _REMAINING.sub(r"\g<1><masked>", text)


#: W-SV-1 Solver invocation index -> AGREE's, for the DELIVERED path (A at the first visit, the revisit).
_SOLVER_INDEX_MAP = {ARM_INDEX["a-base"]: 0, WSV1_SOLVER_REVISIT: AGREE_SOLVER_REVISIT}


def _norm_sha(row: Mapping[str, Any]) -> str | None:
    body = row.get("body")
    return None if body is None else P160._sha(normalise_program_identity(body).encode("utf-8"))


def map_contacts(wsv1: Mapping[str, Any], agree: Mapping[str, Any]) -> dict[str, Any]:
    """Pair every W-SV-1 contact with its AGREE counterpart and compare POST body bytes, exactly and
    after :func:`normalise_program_identity`."""

    agree_by = {}
    for key, row in agree.items():
        sample, program, role, index, rest = _split(key)
        agree_by[(sample, role, index, rest)] = row
    arm_a = {"rows": 0, "post_body_identical": 0, "post_body_identical_after_program_identity_normalisation": 0,
             "mismatch_rows": [], "normalised_mismatch_rows": []}
    twin = {"rows": 0, "post_body_identical_to_a": 0}
    b_arm = {"rows": 0, "post_body_identical_to_a": 0}
    others = {"contacts": 0, "post_body_identical": 0, "post_body_identical_after_program_identity_normalisation": 0,
              "unpaired": 0, "by_role": {}}
    first_visit = {}
    for key, row in wsv1.items():
        sample, program, role, index, rest = _split(key)
        if role == "solver" and index in ARM_INDEX.values():
            first_visit.setdefault((sample, rest), {})[index] = row
            continue
        mapped_index = AGREE_SOLVER_REVISIT if (role == "solver" and index == WSV1_SOLVER_REVISIT) else index
        partner = agree_by.get((sample, role, mapped_index, rest))
        others["contacts"] += 1
        tally = others["by_role"].setdefault(role, {"contacts": 0, "post_body_identical": 0, "normalised_identical": 0})
        tally["contacts"] += 1
        if partner is None:
            others["unpaired"] += 1
            continue
        if partner["body_sha256"] == row["body_sha256"]:
            others["post_body_identical"] += 1
            tally["post_body_identical"] += 1
        if _norm_sha(row) is not None and _norm_sha(row) == _norm_sha(partner):
            others["post_body_identical_after_program_identity_normalisation"] += 1
            tally["normalised_identical"] += 1
    for (sample, rest), arms in sorted(first_visit.items()):
        a = arms.get(ARM_INDEX["a-base"])
        partner = agree_by.get((sample, "solver", 0, rest))
        arm_a["rows"] += 1
        if a is not None and partner is not None and a["body_sha256"] == partner["body_sha256"]:
            arm_a["post_body_identical"] += 1
        elif len(arm_a["mismatch_rows"]) < 5:
            arm_a["mismatch_rows"].append(sample)
        if a is not None and partner is not None and _norm_sha(a) is not None and _norm_sha(a) == _norm_sha(partner):
            arm_a["post_body_identical_after_program_identity_normalisation"] += 1
        elif len(arm_a["normalised_mismatch_rows"]) < 20:
            arm_a["normalised_mismatch_rows"].append(sample)
        if a is not None and ARM_INDEX["t-twin"] in arms:
            twin["rows"] += 1
            twin["post_body_identical_to_a"] += int(arms[ARM_INDEX["t-twin"]]["body_sha256"] == a["body_sha256"])
        if a is not None and ARM_INDEX["b-exk30"] in arms:
            b = arms[ARM_INDEX["b-exk30"]]
            b_arm["rows"] += 1
            b_arm["post_body_identical_to_a"] += int(b["body_sha256"] == a["body_sha256"])
            if a.get("body") is not None and b.get("body") is not None:
                # utf-8 bytes of the whole POST body, B minus A: what the k-30 re-cap adds to the wire
                delta = len(b["body"].encode("utf-8")) - len(a["body"].encode("utf-8"))
                b_arm.setdefault("_deltas", []).append(delta)
                if sample == "slurp:train:000007:audio--1504197557":
                    b_arm["post_body_bytes_delta_on_the_check_representative_row"] = delta
    deltas = b_arm.pop("_deltas", [])
    if deltas:
        b_arm["post_body_bytes_delta_b_minus_a"] = {
            "min": min(deltas), "mean": round(sum(deltas) / len(deltas), 1), "max": max(deltas),
            "at_4_bytes_per_token_max": -(-max(deltas) // 4),
            "note": ("the check's placeholder counter is 4 bytes per token; the k-30 column's Solver physical margin "
                     "is the check's Solver margin minus these tokens"),
        }
    agree_first_solver = sum(1 for (s, role, index, rest) in agree_by if role == "solver" and index == 0)
    arm_a["agree_first_solver_contacts"] = agree_first_solver
    arm_a["all_identical"] = arm_a["rows"] == agree_first_solver and arm_a["post_body_identical"] == arm_a["rows"] > 0
    arm_a["all_identical_after_program_identity_normalisation"] = (
        arm_a["rows"] == agree_first_solver
        and arm_a["post_body_identical_after_program_identity_normalisation"] == arm_a["rows"] > 0
    )
    return {"arm_a_first_solver_vs_agree_first_solver": arm_a, "twin_vs_arm_a_AT2": twin,
            "b_exk30_vs_arm_a": b_arm, "every_other_contact_mapped_across_programs": others}


def payload_leaf_classes(wsv1_raw: Mapping[str, Any], agree_raw: Mapping[str, Any], limit: int = 12) -> dict:
    """Leaf classes of the arm-A vs AGREE first Solver PAYLOAD (custody document) on the first rows."""
    agree_by = {}
    for key, row in agree_raw.items():
        sample, _program, role, index, rest = _split(key)
        if role == "solver" and index == 0:
            agree_by[(sample, rest)] = row
    counts: dict[str, int] = {}
    body_counts: dict[str, int] = {}
    seen = 0
    for key, row in sorted(wsv1_raw.items()):
        sample, _program, role, index, rest = _split(key)
        if role != "solver" or index != ARM_INDEX["a-base"] or (sample, rest) not in agree_by:
            continue
        partner = agree_by[(sample, rest)]
        for leaf in P160._leaf_classes(row["payload"], partner["payload"]):
            counts[leaf] = counts.get(leaf, 0) + 1
        for leaf in P160._leaf_classes(row["body"], partner["body"]):
            body_counts[leaf] = body_counts.get(leaf, 0) + 1
        seen += 1
        if seen >= limit:
            break
    return {"rows": seen, "payload_leaf_classes_differing": dict(sorted(counts.items())),
            "post_body_leaf_classes_differing": dict(sorted(body_counts.items()))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=120, help="dispatch only the first N rows (the wave proof's 120)")
    parser.add_argument("--leaf-rows", type=int, default=12)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--worker-cell", help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-common", help=argparse.SUPPRESS)
    parser.add_argument("--worker-raw", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    import speech_aware_evidence_acquisition as package

    if not str(Path(package.__file__).resolve()).startswith(str(repo)):
        raise SystemExit(f"imported package {package.__file__} is not under {repo}")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if args.worker_cell:
        if args.worker_cell == "agree_arm":
            WAVE._lift_agree_pin()
        label, _, stamp = args.worker_common.rpartition(":")
        captured, receipt = P160.capture_requests(
            repo, args.data_root, args.lock_path, CELLS[args.worker_cell], args.rows,
            keep_raw=args.worker_raw, serial=True, common_run=(label, int(stamp)),
        )
        args.worker_out.write_text(json.dumps({"captured": captured, "receipt": receipt}), encoding="utf-8")
        return 0
    scratch = args.scratch or Path(f"/tmp/wsv1-arm-a-proof-{int(time.time())}")
    scratch.mkdir(parents=True, exist_ok=True)

    cells, composed = {}, {}
    for name, experiment in CELLS.items():
        _cell, composed[name], cells[name] = P160._composed(repo, experiment)
    diff = config_diff(composed["wsv1"].values, composed["agree_arm"].values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]

    supply = prove_supply(repo, args.data_root, args.lock_path, scratch)

    common = ("WSV1-ARM-A-PROOF", int(time.time() * 1000))
    outputs, jobs = {}, []
    for name in CELLS:
        out = scratch / f"capture-raw-{name}.json"
        outputs[name] = out
        jobs.append((f"raw/{name}", functools.partial(
            _launch_worker, repo, args, cell=name, out=out, rows=args.rows, common=common, raw=True)))
    P160._run_workers(jobs, args.parallel)

    hashed = {}
    raw = {}
    for name in CELLS:
        raw[name] = json.loads(outputs[name].read_text(encoding="utf-8"))
        outputs[name].unlink()  # no raw request text survives the comparison
    mapping = map_contacts(raw["wsv1"]["captured"], raw["agree_arm"]["captured"])
    leaves = payload_leaf_classes(raw["wsv1"]["captured"], raw["agree_arm"]["captured"], args.leaf_rows)
    for name in CELLS:
        hashed[name] = {"receipt": raw[name]["receipt"]}
    del raw
    arm_a = mapping["arm_a_first_solver_vs_agree_first_solver"]
    base_ok = not unclassified and supply["output_digests_equal"] and supply["equal_registered_and_committed"]
    identical = base_ok and arm_a["all_identical"]
    modulo = base_ok and arm_a["all_identical_after_program_identity_normalisation"]
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    proof = {
        "schema": PROOF_SCHEMA,
        "owner_decision": 172,
        "precedent": "scripts/flights/wave/wave_shared_aa_proof.py (owner decision 164), itself the decision-160 method",
        "question": (
            "Is W-SV-1's delivering arm A (override-free, last in the Solver arm group, under the 13-ceiling uncited "
            "program) the retained AGREE arm's own bytes at its FIRST Solver request: the same prepared first-phase "
            "supply output and byte-identical POST bodies?"
        ),
        "verdict": ("IDENTICAL" if identical else
                    "IDENTICAL_MODULO_PROGRAM_IDENTITY" if modulo else "DIFFERENT"),
        "program_identity_fields": (
            "the two model-visible fields the program switch moves (normalise_program_identity): (1) the program id "
            "and the node's global invocation index inside every quoted prior contact id (arm A is the Solver's "
            "invocation 2, AGREE's first Solver 0; a revisit 3 against 1); (2) remaining_model_contacts in the "
            "task-state block (ceiling 13 minus spent, against 11 minus spent: +2 on every contact). "
            "IDENTICAL_MODULO_PROGRAM_IDENTITY means every arm-A first Solver POST body equals the AGREE arm's once "
            "exactly these two fields are mapped / masked, and differs from it in exactly these"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_commit": head,
        "tool": "scripts/flights/wsv1/wsv1_arm_a_proof.py",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "cells": cells,
        "composed_config_diff": {
            "differing_leaves": diff,
            "by_class": {k: sum(1 for row in diff if row["class"] == k) for k in sorted({row["class"] for row in diff})},
            "request_affecting_leaves": unclassified,
        },
        "prepared_supply": supply,
        "request_bytes": {
            "method": (
                "the decision-160 method (P160.capture_requests): FlightRuntime._dispatch_phase_program("
                "model_free_check=True) on each cell's own composed fragments, against the composed model fragment's "
                "REAL llama-server transport with its POST replaced by a fake server that records the body bytes and "
                "answers a canned, role-appropriate completion (identical for both cells); dispatched serially under "
                "ONE common scratch run id; the AGREE side with its unloadable committed supply pin lifted (proof 2 "
                "shows the live supply equals the committed output)"
            ),
            "rows": args.rows,
            "receipts": {name: hashed[name]["receipt"] for name in CELLS},
            **mapping,
            "payload_custody_leaf_classes_first_rows": leaves,
        },
        "scratch": str(scratch),
        "hash_quoting": (
            "64-hex identities other than the prepared-supply output digests and the study commit are quoted as "
            "sha256-prefix16:<first 16 hex> (core.flight.repin rewrites package JSON from old identity hashes to new "
            "ones at the flip and refuses any old hash left under docs/)"
        ),
    }
    proof = P160.quote_hashes_by_prefix(proof)
    proof["prepared_supply"]["agree_arm_registered_output_sha256"] = AGREE_ARM_SUPPLY_OUTPUT_SHA256
    proof["prepared_supply"]["agree_arm"]["output_sha256_recomputed"] = supply["agree_arm"]["output_sha256_recomputed"]
    output = args.output or (repo / DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": proof["verdict"], "output": str(output),
                      "config_classes": proof["composed_config_diff"]["by_class"], "unclassified": unclassified,
                      "supply_equal_registered_and_committed": supply["equal_registered_and_committed"],
                      **{k: mapping[k] for k in mapping}, "payload_leaves": leaves}, indent=1))
    return 0 if identical else 4 if modulo else 3


if __name__ == "__main__":
    raise SystemExit(main())
