#!/usr/bin/env python3
"""Cell W4-SV, proven model-free: is arm A (``a-agree``) the AGREE arm's own bytes, and the twin A's?

The same-flight supply-variant instrument (owner decision 172) reads arm B (``b-w4``) and the twin
(``t-twin``) as first-visit columns against the DELIVERING arm A. That read means what it says only if
arm A's first Solver request is the retained AGREE arm's first Solver request, byte for byte, and every
other contact of the episode (Perception, Reviewer, Planner, the Solver revisit) is the AGREE arm's too.
This is the wave shared-A/A proof shape (``scripts/flights/wave/wave_shared_aa_proof.py``, itself the
decision-160 proof) pointed at the W4-SV arm and the sealed AGREE arm, with the one change the arm group
forces: the Solver's global contact index. Under ``arm_visits: "first"`` the first Solver visit spends
indices 0, 1, 2 on ``b-w4``, ``t-twin``, ``a-agree`` (declared order) and a revisit spends index 3; the
AGREE arm spends 0 and 1. So contacts are PAIRED by (sample, role, AGREE index), mapping W4-SV Solver
index 2 -> 0 (arm A), 1 -> 0 (the twin, AT2), 0 -> 0 (arm B, expected to differ where a W4 card reaches
the row) and i >= 3 -> i - 2 (the revisit); every other role keeps its index. The contact id itself
carries the program id (``...-variants3first-v1`` vs ``...-v1``), so the request PAYLOADS differ in custody
by construction; the proof is on the POST BODY bytes -- what the model server receives.

Three proofs, each model-free (zero model, server, tokenizer, encoder or scorer contacts):

1. **Composed config.** Every differing leaf of the two composed configs is classified: ``bookkeeping``
   (the wave proof's list), ``supply-pin`` (the AGREE arm's committed first-phase supply pin, which W4-SV
   drops so its flip mints its own), ``variant-declaration`` (the program id, the slot store's
   ``alternates``, the Solver's ``supply_variants`` block, the two appended W4 receipts, the 13-contact
   budget arithmetic) -- request-affecting ONLY through the arm group, which proof 3 measures -- or
   ``unclassified`` (fails the verdict).
2. **Prepared supply.** ``core.flight.cli prepare-supply`` mints W4-SV's first-phase supply into a scratch
   directory; its ``output_sha256`` must equal the AGREE arm's registered digest ``eab5c61e...`` and the
   output digest of the AGREE arm's committed artifact (read raw).
3. **Request bytes.** Each cell's REAL dispatch against the REAL transport with a fake POST (the
   decision-160 method, verbatim; the AGREE side with its unloadable pin lifted, as the wave proof does),
   serial, one slot, under each cell's own run id. Verdict IDENTICAL iff every paired non-arm-B contact's
   POST body is byte-identical (arm A's first Solver contact included), every twin body equals its arm A
   body, and no contact is unpaired. Arm B's bodies are counted (equal / different), never required equal.

Exit 0 with ``IDENTICAL``, 3 with ``DIFFERENT``. In WSL from the worktree::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA \\
    python -B scripts/flights/w4sv/w4sv_arm_a_proof.py --repo-root $REPO --data-root $DATA \\
      --lock-path $LOCK [--rows N] [--output PATH]
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

PROOF_SCHEMA = "saea-w4sv-arm-a-byte-identity-proof-v1"
PACKAGE = "docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1"
DEFAULT_OUTPUT = PACKAGE + "/arm-a-byte-identity-proof-v1.json"

CELLS: dict[str, str] = {
    "w4sv": "slurp-native-stage3-w4sv-fold-a-v1",
    "agree_arm": "slurp-native-stage3-agree-w1-fold-a-v1",
}
AGREE_ARM_SUPPLY_OUTPUT_SHA256 = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
#: Declared arm order at the first Solver visit (the delivering arm last).
ARM_ORDER = ("b-w4", "t-twin", "a-agree")
#: The program-derived prompt fields the arm group necessarily moves (found by this proof, 2026-09-28):
#: (1) the agent-state labels carry the program id; (2) they carry the Solver's GLOBAL contact index,
#: which the arm group shifts by K - 1 = 2 (the delivering arm's first-visit state is ``solver:2``, its
#: revisit ``solver:3``; the AGREE arm's ``solver:0`` / ``solver:1``); (3) the role context JSON carries
#: ``remaining_model_contacts`` (the program ceiling minus contacts spent: 13 - 0 vs 11 - 0 before the
#: Solver visit, equal after it). The NORMALISED comparison unifies exactly these three and nothing else.
W4SV_PROGRAM_ID = "phase-native-candidates-review-revise-variants3first-v1"
AGREE_PROGRAM_ID = "phase-native-candidates-review-revise-v1"
REMAINING = re.compile(r'(\\?"remaining_model_contacts\\?": )\d+')


SOLVER_LABEL = re.compile(re.escape(W4SV_PROGRAM_ID) + r":solver:(\d+):")


def normalised_body_sha256(body: str) -> str:
    """The POST body with the program id unified, the Solver's global contact index in agent-state labels
    shifted back by the arm group's K - 1 = 2 (W4-SV bodies only; the AGREE program id never matches), and
    ``remaining_model_contacts`` masked."""

    shift = len(ARM_ORDER) - 1
    text = SOLVER_LABEL.sub(
        lambda m: f"{AGREE_PROGRAM_ID}:solver:{int(m.group(1)) - shift if int(m.group(1)) >= shift else 'arm' + m.group(1)}:",
        body,
    )
    text = text.replace(W4SV_PROGRAM_ID, AGREE_PROGRAM_ID)
    text = REMAINING.sub(lambda m: m.group(1) + "<masked>", text)
    return P160._sha(text.encode("utf-8"))

VARIANT_DECLARATION_LEAVES: tuple[tuple[str, str], ...] = (
    ("policy", "the program id: the uncited 13-contact copy of the AGREE program (max_contacts 11 + (3 - 1))"),
    ("knowledge_stores.slot-contracts.alternates", "the ONE declared alternate (the W4 release/snapshot pins); "
     "read only when an arm's release_swap selects it"),
    ("native_episode.roles.solver.supply_variants", "the three-arm group, arm_visits first"),
    ("preparation_source_receipts", "the two W4 release receipts appended for the alternate's provenance"),
    ("native_contact_fit.contact_cap", "the FIT cap at the 13-contact ceiling"),
    ("execution_plan.planned_model_calls", "the plan budget at the 13-contact ceiling"),
    ("execution_plan.planned_speech_audio_seconds", "the plan audio budget at the 13-contact ceiling"),
)


def _load_module(relpath: str, name: str):
    path = Path(__file__).resolve().parents[1] / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


WAVE = _load_module("wave/wave_shared_aa_proof.py", "wave_shared_aa_proof")
P160 = WAVE.P160


def classify_leaf(leaf: str) -> tuple[str, str]:
    for prefix, reason in VARIANT_DECLARATION_LEAVES:
        if leaf == prefix or leaf.startswith(prefix + ".") or leaf.startswith(prefix + "["):
            return "variant-declaration", reason
    return WAVE.classify_leaf(leaf)


def config_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    flat_left, flat_right = P160.flatten(left), P160.flatten(right)
    rows = []
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a, b = flat_left.get(leaf, "<absent>"), flat_right.get(leaf, "<absent>")
        if a == b:
            continue
        klass, reason = classify_leaf(leaf)
        short = lambda v: v if len(json.dumps(v, default=str)) < 300 else "<long>"  # noqa: E731
        rows.append({"leaf": leaf, "w4sv": short(a), "agree_arm": short(b), "class": klass,
                     "request_affecting": klass == "unclassified", "reason": reason})
    return rows


def prove_supply(repo: Path, data: Path, lock: Path, scratch: Path) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    experiment = CELLS["w4sv"]
    path = scratch / "w4sv" / "phase-supply-v1.json"
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
    minted = json.loads(path.read_bytes())
    baseline = json.loads((repo / "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")
                          .read_text(encoding="utf-8"))
    pin = baseline["prepared_phase_supply"]
    pinned_raw = (data / pin["relpath"]).read_bytes()
    pinned = json.loads(pinned_raw)
    from speech_aware_evidence_acquisition.core.preparation import digest as _digest

    recomputed = _digest(pinned["output"])
    pinned_ok = P160._sha(pinned_raw) == pin["sha256"]
    equal = minted["output_sha256"] == pinned["output_sha256"] == recomputed
    return {
        "w4sv": {"output_sha256": minted["output_sha256"], "seconds": round(time.time() - started, 1)},
        "agree_arm": {"relpath": pin["relpath"], "file_sha256_matches_pin": pinned_ok,
                      "output_sha256": pinned["output_sha256"], "output_sha256_recomputed": recomputed},
        "agree_arm_registered_output_sha256": AGREE_ARM_SUPPLY_OUTPUT_SHA256,
        "output_digests_equal": equal,
        "equal_registered_and_committed": equal and pinned_ok
        and minted["output_sha256"] == AGREE_ARM_SUPPLY_OUTPUT_SHA256,
    }


def _split(key: str) -> tuple[str, str, int]:
    sample, _, contact = key.partition("|")
    role, index = P160.role_of(contact)
    return sample, role, index


def pair_captures(w4sv: Mapping[str, Mapping[str, str]], agree: Mapping[str, Mapping[str, str]],
                  field: str = "body_sha256") -> dict[str, Any]:
    """Pair W4-SV contacts with AGREE contacts by (sample, role, AGREE index) and compare POST bodies
    (``field``: the strict body hash, or the normalised one)."""

    arms = len(ARM_ORDER)
    agree_by = {}
    for key, row in agree.items():
        agree_by[_split(key)] = row[field]
    w4_by = {}
    for key, row in w4sv.items():
        w4_by[_split(key)] = row[field]
    paired, mismatched, twin_mismatch, unpaired_w4 = 0, [], [], []
    b_equal, b_different = 0, 0
    solver_first_a = 0
    used_agree = set()
    for (sample, role, index), body in sorted(w4_by.items()):
        if role != "solver":
            target = (sample, role, index)
        elif index < arms:
            arm = ARM_ORDER[index]
            target = (sample, role, 0)
            a_body = w4_by.get((sample, role, ARM_ORDER.index("a-agree")))
            if arm == "b-w4":
                if body == a_body:
                    b_equal += 1
                else:
                    b_different += 1
                continue
            if arm == "t-twin":
                if body != a_body:
                    twin_mismatch.append(f"{sample}|solver:{index}")
                continue
            solver_first_a += 1
        else:
            target = (sample, role, index - (arms - 1))
        if target not in agree_by:
            unpaired_w4.append(f"{sample}|{role}:{index}")
            continue
        used_agree.add(target)
        paired += 1
        if agree_by[target] != body:
            mismatched.append(f"{sample}|{role}:{index}")
    unpaired_agree = sorted(f"{s}|{r}:{i}" for (s, r, i) in set(agree_by) - used_agree)
    return {
        "contacts_w4sv": len(w4sv), "contacts_agree_arm": len(agree),
        "paired_contacts": paired, "arm_a_first_solver_contacts": solver_first_a,
        "post_body_mismatches": len(mismatched), "first_mismatches": mismatched[:20],
        "twin_body_mismatches": len(twin_mismatch), "first_twin_mismatches": twin_mismatch[:20],
        "unpaired_w4sv": unpaired_w4[:20], "unpaired_agree_arm": unpaired_agree[:20],
        "unpaired_counts": {"w4sv": len(unpaired_w4), "agree_arm": len(unpaired_agree)},
        "arm_b_bodies_equal_to_arm_a": b_equal, "arm_b_bodies_different_from_arm_a": b_different,
        "identical": (not mismatched and not twin_mismatch and not unpaired_w4 and not unpaired_agree
                      and solver_first_a > 0),
    }


def _launch_worker(repo: Path, args, *, cell: str, out: Path, rows: int | None):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--repo-root", str(repo),
               "--data-root", str(args.data_root), "--lock-path", str(args.lock_path),
               "--worker-cell", cell, "--worker-out", str(out)]
    if rows is not None:
        command += ["--rows", str(rows)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    log = out.with_suffix(".log").open("w", encoding="utf-8")
    return subprocess.Popen(command, env=env, cwd=str(repo), stdout=log, stderr=subprocess.STDOUT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=None, help="dispatch only the first N rows (default: all)")
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--worker-cell", help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
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
        captured, receipt = P160.capture_requests(
            repo, args.data_root, args.lock_path, CELLS[args.worker_cell], args.rows,
            keep_raw=True, serial=True, common_run=None,
        )
        for row in captured.values():  # bodies are hashed and dropped, never persisted
            row["normalised_body_sha256"] = normalised_body_sha256(row.pop("body"))
            row.pop("payload", None)
        args.worker_out.write_text(json.dumps({"captured": captured, "receipt": receipt}), encoding="utf-8")
        return 0
    scratch = args.scratch or Path(f"/tmp/w4sv-arm-a-proof-{int(time.time())}")
    scratch.mkdir(parents=True, exist_ok=True)

    cells, composed = {}, {}
    for name, experiment in CELLS.items():
        _cell, composed[name], cells[name] = P160._composed(repo, experiment)
    diff = config_diff(composed["w4sv"].values, composed["agree_arm"].values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]

    supply = prove_supply(repo, args.data_root, args.lock_path, scratch)

    outputs, jobs = {}, []
    for name in CELLS:
        out = scratch / f"capture-{name}.json"
        outputs[name] = out
        jobs.append((f"own_run_ids/{name}", functools.partial(_launch_worker, repo, args, cell=name, out=out,
                                                               rows=args.rows)))
    P160._run_workers(jobs, args.parallel)
    loaded = {name: json.loads(outputs[name].read_text(encoding="utf-8")) for name in CELLS}
    comparison = pair_captures(loaded["w4sv"]["captured"], loaded["agree_arm"]["captured"])
    normalised = pair_captures(loaded["w4sv"]["captured"], loaded["agree_arm"]["captured"],
                               field="normalised_body_sha256")
    base_ok = not unclassified and supply["output_digests_equal"] and supply["equal_registered_and_committed"]
    identical = base_ok and comparison["identical"]
    identical_modulo = base_ok and normalised["identical"]
    arm_b_inert = comparison["arm_b_bodies_different_from_arm_a"] == 0
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    proof = {
        "schema": PROOF_SCHEMA,
        "owner_decision": 172,
        "precedent": "the wave shared-A/A proof (scripts/flights/wave/wave_shared_aa_proof.py; decision 160's method)",
        "question": (
            "Is W4-SV's delivering arm a-agree the retained AGREE arm's own bytes (SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1) "
            "-- byte-identical prepared first-phase supply output and byte-identical POST bodies for every contact, "
            "arm A's first Solver contact included -- and is the twin t-twin's body arm A's, contact for contact?"
        ),
        "verdict": ("IDENTICAL" if identical else
                    "IDENTICAL-MODULO-PROGRAM-FIELDS" if identical_modulo else "DIFFERENT"),
        "arm_b_verdict": "ARM-B-INERT" if arm_b_inert else "ARM-B-VARIES",
        "arm_b_reading": (
            "every arm b-w4 first-visit POST body equals its arm a-agree body: the release swap re-selects value "
            "ids through the alternate's router, but rails.runner renders every arm's request from the FLIGHT's "
            "composite snapshot (base_messages over the row's snapshot, with only retrieved_value_ids replaced), "
            "and slot-contracts-w4-v1 carries the SAME 54 value ids as slot-contracts-v2 with new content on 19 "
            "of them -- so arm b-w4 renders the v2 cards and reads as a second twin. The cell cannot fly until the "
            "runner renders a release-swap arm from its own alternate snapshot" if arm_b_inert else
            "arm b-w4's first-visit bodies differ from arm a-agree's on the counted rows"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_commit": head,
        "tool": "scripts/flights/w4sv/w4sv_arm_a_proof.py",
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
                "P160.capture_requests on each cell's own composed fragments (own run ids, serial, one slot), the "
                "real transport with a fake POST answering a canned role-appropriate completion; contacts paired by "
                "(sample, role, AGREE index) with W4-SV Solver index 2 (a-agree) -> 0, 1 (t-twin) compared with its "
                "own arm A, 0 (b-w4) counted, i >= 3 -> i - 2; POST body sha256 compared"
            ),
            "rows": args.rows,
            "w4sv": loaded["w4sv"]["receipt"], "agree_arm": loaded["agree_arm"]["receipt"],
            "comparison": comparison,
            "comparison_normalised": normalised,
            "normalisation": (
                "the program id " + W4SV_PROGRAM_ID + " replaced by " + AGREE_PROGRAM_ID + ", the Solver's global "
                "contact index in agent-state labels shifted back by 2 (the arm group's K - 1), and every "
                "remaining_model_contacts value masked -- the three prompt fields the arm group necessarily moves"
            ),
        },
        "scratch": str(scratch),
        "hash_quoting": (
            "64-hex identities other than the prepared-supply output digests and the study commit are quoted as "
            "sha256-prefix16:<first 16 hex> (core.flight.repin rewrites package JSON from old identity hashes to "
            "new ones at the flip and refuses any old hash left under docs/); the full values are recomputable "
            "from study_commit"
        ),
    }
    proof = P160.quote_hashes_by_prefix(proof)
    proof["prepared_supply"]["agree_arm_registered_output_sha256"] = AGREE_ARM_SUPPLY_OUTPUT_SHA256
    proof["prepared_supply"]["agree_arm"]["output_sha256_recomputed"] = supply["agree_arm"]["output_sha256_recomputed"]
    proof["prepared_supply"]["agree_arm"]["output_sha256"] = supply["agree_arm"]["output_sha256"]
    proof["prepared_supply"]["w4sv"]["output_sha256"] = supply["w4sv"]["output_sha256"]
    output = args.output or (repo / DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": proof["verdict"], "arm_b_verdict": proof["arm_b_verdict"],
                      "normalised": {k: normalised[k] for k in ("paired_contacts", "post_body_mismatches",
                                                                "twin_body_mismatches", "identical")},
                      "output": str(output),
                      "config_classes": proof["composed_config_diff"]["by_class"], "unclassified": unclassified,
                      "supply": {"w4sv": supply["w4sv"]["output_sha256"],
                                 "equal_registered_and_committed": supply["equal_registered_and_committed"]},
                      "comparison": comparison}, indent=1))
    return 0 if identical else 3


if __name__ == "__main__":
    raise SystemExit(main())
