#!/usr/bin/env python3
"""Owner decision 164's shared A/A, proven model-free: is the wave A/A the AGREE arm's own bytes?

Decision 164 (2026-09-27) reads the knowledge wave's arms (W1, W3, W4) against ONE shared in-chain
A/A "of the AGREE arm's own bytes" (row 160's precedent). This script proves that the registered
A/A cell ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`` is exactly that: the same composed config up to
bookkeeping, the same prepared first-phase supply output, and the same request bytes as the sealed,
retained AGREE arm ``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``. It is the decision-160 proof
(``scripts/flights/comp1/comp1_g5_shared_aa_proof.py``) pointed at a different pair, and it reuses
that script's pure helpers and its request-capture routine unchanged.

Three proofs, each model-free (zero model, server, tokenizer, encoder or scorer contacts):

1. **Composed config.** Both cells are composed from their committed fragments and every leaf is
   flattened. Every differing leaf is classified: ``bookkeeping`` (identity, prose, budget prose,
   the readiness block -- never read by the request composer), ``supply-pin`` (the AGREE arm's
   committed ``prepared_phase_supply`` pin, which the A/A drops so the flip mints its own, item E16:
   output-neutral exactly when proof 2 finds equal output digests), or ``unclassified`` (treated as
   request-affecting: the verdict fails).
2. **Prepared supply.** ``core.flight.cli prepare-supply`` mints the A/A's supply into a scratch
   directory (never ``prepared/``); its ``output_sha256`` must equal the AGREE arm's registered
   digest ``eab5c61e...`` and the output digest of the AGREE arm's own COMMITTED artifact (the one
   that flew), read raw and re-digested (it no longer loads at HEAD: item E16).
3. **Request bytes.** Each cell's REAL dispatch against the REAL transport with a fake POST (the
   decision-160 method, verbatim; the AGREE side with its unloadable pin lifted so its supply is
   computed live, which proof 2 shows is the committed output): mode A under one common scratch run id (every payload and POST
   body byte must match), mode B under each cell's own run id (every POST body byte must match; the
   payloads may differ only in the run-id-derived custody field), plus the concurrent
   self-control on the A/A.

Exit 0 with verdict ``IDENTICAL`` when all three hold; exit 3 with ``DIFFERENT`` otherwise. Usage, in
WSL from the worktree::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA \\
    python -B scripts/flights/wave/wave_shared_aa_proof.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--rows N] [--output PATH]
"""

from __future__ import annotations

import argparse
import functools
import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROOF_SCHEMA = "saea-wave1-shared-aa-proof-v1"
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1"
DEFAULT_OUTPUT = PACKAGE + "/shared-aa-proof-v1.json"

#: The pair (experiment id == cell id for both): the registered wave A/A and the retained AGREE arm.
CELLS: dict[str, str] = {
    "wave_aa": "slurp-native-stage3-wave1-aa-fold-a-v1",
    "agree_arm": "slurp-native-stage3-agree-w1-fold-a-v1",
}

#: The AGREE arm's registered first-phase supply output digest (the W1, W3 and W4 packages name it).
AGREE_ARM_SUPPLY_OUTPUT_SHA256 = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"

SUPPLY_PIN_PREFIX = "prepared_phase_supply"

#: Leaves (exact, or a prefix ending in ".") no request composer reads.
BOOKKEEPING_LEAVES: tuple[tuple[str, str], ...] = (
    ("cells.", "the experiment fragment's cell list: run, attempt and cell ids, the baseline fragment NAME, "
               "readiness state, reason and requirements (the AGREE arm's decision pin, the A/A's held state) -- "
               "read by the campaign loader, the readiness gate and the re-pin tool, never by request composition"),
    ("experiment_id", "the experiment's registered id (ledger and receipts)"),
    ("fragment_kind", "the fragment's self-description tag"),
    ("purpose", "prose"),
    ("what_this_is", "prose"),
    ("stage3_algorithm.", "the Stage-3 algorithm label and its prose (the label gate reads it)"),
    ("generation_budget.", "the run-cumulative generation budget prose and target (the ledger and the batch "
                           "inspector read it; the request composer never does)"),
    ("family_budget.", "the family caps (the decision receipt and the gate read them)"),
    ("native_contact_fit.run_id", "the cell's own FIT spend identity (a run id)"),
    ("native_contact_fit.attempt_id", "the cell's own FIT spend identity (an attempt id)"),
    ("date", "the registration date"),
    ("failure_policy", "prose"),
)


def _load_decision160_proof():
    path = Path(__file__).resolve().parents[1] / "comp1" / "comp1_g5_shared_aa_proof.py"
    spec = importlib.util.spec_from_file_location("comp1_g5_shared_aa_proof", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


P160 = _load_decision160_proof()
flatten = P160.flatten


def classify_leaf(leaf: str) -> tuple[str, str]:
    """``(class, reason)`` for one differing composed-config leaf of the (wave A/A, AGREE arm) pair."""

    if leaf == SUPPLY_PIN_PREFIX or leaf.startswith(SUPPLY_PIN_PREFIX + "."):
        return (
            "supply-pin",
            "the AGREE arm's committed prepared first-phase supply pin (relpath + file sha256); the A/A drops it so "
            "the flip mints its own under its own run id (item E16). It reaches a request only through the supply's "
            "OUTPUT, so it is output-neutral exactly when the two prepared supply output digests are equal",
        )
    normalized = leaf.replace("[", ".[")
    for prefix, reason in BOOKKEEPING_LEAVES:
        if prefix.endswith("."):
            if normalized.startswith(prefix) or leaf.startswith(prefix.rstrip(".") + "["):
                return "bookkeeping", reason
        elif leaf == prefix:
            return "bookkeeping", reason
    return "unclassified", "no rule names this leaf: treated as request-affecting"


def config_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    flat_left, flat_right = flatten(left), flatten(right)
    rows: list[dict[str, Any]] = []
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a = flat_left.get(leaf, "<absent>")
        b = flat_right.get(leaf, "<absent>")
        if a == b:
            continue
        klass, reason = classify_leaf(leaf)
        short = lambda v: v if len(json.dumps(v, default=str)) < 300 else "<long>"  # noqa: E731
        rows.append({"leaf": leaf, "wave_aa": short(a), "agree_arm": short(b), "class": klass,
                     "request_affecting": klass == "unclassified", "reason": reason})
    return rows


def relabel(comparison: Mapping[str, Any]) -> dict[str, Any]:
    """The decision-160 comparison with this pair's labels (left = wave A/A, right = AGREE arm)."""

    names = {"contacts_comp1_aa": "contacts_wave_aa", "contacts_g5_aa": "contacts_agree_arm",
             "only_in_comp1_aa": "only_in_wave_aa", "only_in_g5_aa": "only_in_agree_arm"}
    return {names.get(key, key): value for key, value in comparison.items()}


def prove_supply(repo: Path, data: Path, lock: Path, scratch: Path) -> dict[str, Any]:
    """Mint the A/A's supply into ``scratch``; compare it with the AGREE arm's COMMITTED artifact.

    The AGREE arm's own committed pin (``prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v2.json``)
    is the artifact that flew. It no longer LOADS at this HEAD -- ``core.preparation.load_artifact`` refuses an
    artifact whose recorded inputs (which carry the implementation identity of ``rails/kb_policy`` and its
    siblings, item E16) differ from the current ones, and the W3 merge moved ``rails/kb_policy`` -- so it is not
    re-minted here: its bytes are read raw, the file hash is checked against the AGREE baseline's pin, and its
    recorded ``output_sha256`` (the digest over the ``{facets, values}`` payload the request composer consumes)
    is re-digested and compared with the A/A's freshly minted one.
    """

    out: dict[str, Any] = {}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    experiment = CELLS["wave_aa"]
    path = scratch / "wave_aa" / "phase-supply-v1.json"
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

    def _summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
        values = {sample: ids for per_phase in artifact["output"]["values"].values() for sample, ids in per_phase.items()}
        return {"rows_seeded": sum(1 for ids in values.values() if ids),
                "selected_value_ids": sum(len(ids) for ids in values.values())}

    out["wave_aa"] = {
        "command": f"core.flight.cli prepare-supply --experiment {experiment} --cell {experiment} --output <scratch>/wave_aa/phase-supply-v1.json",
        "output_sha256": minted["output_sha256"], "file_sha256": P160._sha(raw), **_summary(minted),
        "seconds": round(time.time() - started, 1),
    }
    baseline = json.loads((repo / "configs" / "baseline" / "slurp-native-stage3-agree-w1-fold-a-baseline-v1.json").read_text(encoding="utf-8"))
    pin = baseline["prepared_phase_supply"]
    pinned_raw = (data / pin["relpath"]).read_bytes()
    pinned = json.loads(pinned_raw)
    pinned_ok = P160._sha(pinned_raw) == pin["sha256"]
    from speech_aware_evidence_acquisition.core.preparation import digest as _digest

    recomputed = _digest(pinned["output"])
    out["agree_arm"] = {
        "source": "the AGREE arm's committed artifact (the one that flew), read raw -- not re-minted",
        "relpath": pin["relpath"], "file_sha256_matches_pin": pinned_ok,
        "output_sha256": pinned["output_sha256"], "output_sha256_recomputed": recomputed, **_summary(pinned),
    }
    inputs_diff = [
        {"leaf": leaf, "wave_aa": a, "agree_arm": b}
        for leaf, a, b in P160._diff_pairs(minted["inputs"], pinned["inputs"])
    ]
    equal = minted["output_sha256"] == pinned["output_sha256"] == recomputed
    out.update({
        "agree_arm_registered_output_sha256": AGREE_ARM_SUPPLY_OUTPUT_SHA256,
        "output_digests_equal": equal,
        "equal_registered_and_committed": equal and pinned_ok and minted["output_sha256"] == AGREE_ARM_SUPPLY_OUTPUT_SHA256,
        "artifact_input_differences": inputs_diff,
        "note": ("the recorded INPUTS differ (the run id, and the implementation identity the W3 merge moved), which is "
                 "why the committed artifact no longer loads at HEAD; output_sha256 is core.preparation.digest over the "
                 "{facets, values} payload and is what the flip's byte-identity check and the request composer consume"),
    })
    return out


def _lift_agree_pin() -> None:
    """In a capture worker for the AGREE arm: dispatch it as a flip would mint it at this HEAD.

    Its committed ``prepared_phase_supply`` pin cannot load here (see :func:`prove_supply`), so the pin is
    removed from the AGREE arm's composed values as the runtime composes them (``FlightRuntime._prepare``) and
    the first-phase supply is computed LIVE through the same ``_phase_supply_seeds`` path the A/A uses. Proof 2
    separately shows the A/A's minted output equals the committed artifact's output byte for byte, so the live
    supply is the AGREE arm's own. Nothing else in the composed values is touched.
    """

    import dataclasses

    from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime

    real = flight_runtime.compose

    def compose(repo_root, model, dataset, baseline, experiment, *args, **kwargs):
        composed = real(repo_root, model, dataset, baseline, experiment, *args, **kwargs)
        if experiment != CELLS["agree_arm"] or "prepared_phase_supply" not in composed.values:
            return composed
        values = {key: value for key, value in composed.values.items() if key != "prepared_phase_supply"}
        return dataclasses.replace(composed, values=values)

    flight_runtime.compose = compose


def _launch_worker(repo: Path, args, *, cell: str, out: Path, rows: int | None,
                   common: tuple[str, int] | None, serial: bool, raw: bool):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--repo-root", str(repo),
               "--data-root", str(args.data_root), "--lock-path", str(args.lock_path),
               "--worker-cell", cell, "--worker-out", str(out)]
    if rows is not None:
        command += ["--rows", str(rows)]
    if common is not None:
        command += ["--worker-common", f"{common[0]}:{common[1]}"]
    if not serial:
        command.append("--worker-concurrent")
    if raw:
        command.append("--worker-raw")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    log = out.with_suffix(".log").open("w", encoding="utf-8")
    return subprocess.Popen(command, env=env, cwd=str(repo), stdout=log, stderr=subprocess.STDOUT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=None, help="dispatch only the first N rows (default: all)")
    parser.add_argument("--self-control-rows", type=int, default=12)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--worker-cell", help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-common", help=argparse.SUPPRESS)
    parser.add_argument("--worker-concurrent", action="store_true", help=argparse.SUPPRESS)
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
            _lift_agree_pin()
        common = None
        if args.worker_common:
            label, _, stamp = args.worker_common.rpartition(":")
            common = (label, int(stamp))
        captured, receipt = P160.capture_requests(
            repo, args.data_root, args.lock_path, CELLS[args.worker_cell], args.rows,
            keep_raw=args.worker_raw, serial=not args.worker_concurrent, common_run=common,
        )
        args.worker_out.write_text(json.dumps({"captured": captured, "receipt": receipt}), encoding="utf-8")
        return 0
    scratch = args.scratch or Path(f"/tmp/wave1-shared-aa-proof-{int(time.time())}")
    scratch.mkdir(parents=True, exist_ok=True)

    cells, composed = {}, {}
    for name, experiment in CELLS.items():
        _cell, composed[name], cells[name] = P160._composed(repo, experiment)
    diff = config_diff(composed["wave_aa"].values, composed["agree_arm"].values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]

    supply = prove_supply(repo, args.data_root, args.lock_path, scratch)

    common_run = ("WAVE1-SHARED-AA-PROOF", int(time.time() * 1000))
    jobs, outputs = [], {}
    for mode, common in (("common_run_id", common_run), ("own_run_ids", None)):
        for name in CELLS:
            out = scratch / f"capture-{mode}-{name}.json"
            outputs[(mode, name)] = out
            jobs.append((f"{mode}/{name}", functools.partial(
                _launch_worker, repo, args, cell=name, out=out, rows=args.rows, common=common, serial=True, raw=False)))
    if args.self_control_rows:
        for index in (1, 2):
            out = scratch / f"capture-self-control-{index}.json"
            outputs[("self_control", index)] = out
            jobs.append((f"self-control/{index}", functools.partial(
                _launch_worker, repo, args, cell="wave_aa", out=out, rows=args.self_control_rows,
                common=None, serial=False, raw=True)))
    P160._run_workers(jobs, args.parallel)

    def _load(key):
        return json.loads(outputs[key].read_text(encoding="utf-8"))

    modes: dict[str, dict[str, Any]] = {}
    for mode in ("common_run_id", "own_run_ids"):
        loaded = {name: _load((mode, name)) for name in CELLS}
        modes[mode] = {
            "wave_aa": loaded["wave_aa"]["receipt"],
            "agree_arm": loaded["agree_arm"]["receipt"],
            "comparison": relabel(P160.compare_captures(loaded["wave_aa"]["captured"], loaded["agree_arm"]["captured"])),
        }
    self_control = (
        P160.self_control_reading(_load(("self_control", 1))["captured"], _load(("self_control", 2))["captured"],
                                  args.self_control_rows)
        if args.self_control_rows else None
    )
    if self_control:
        self_control["what"] = self_control["what"].replace("cell COMP-1's A/A", "the wave A/A")
    common_cmp = modes["common_run_id"]["comparison"]
    own_cmp = modes["own_run_ids"]["comparison"]
    requests_identical = (
        common_cmp["payload_bytes_identical"] and common_cmp["post_body_bytes_identical"]
        and own_cmp["post_body_bytes_identical"] and own_cmp["run_id_normalized_payload_bytes_identical"]
    )
    identical = (not unclassified and supply["output_digests_equal"] and supply["equal_registered_and_committed"]
                 and requests_identical)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    proof = {
        "schema": PROOF_SCHEMA,
        "owner_decision": 164,
        "precedent": "owner decision 160 (scripts/flights/comp1/comp1_g5_shared_aa_proof.py)",
        "question": (
            "Is the knowledge wave's shared in-chain A/A (SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1) the retained AGREE arm's "
            "own bytes (SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1): byte-identical prepared first-phase supply output and "
            "byte-identical composed request bytes? If so, W1, W3 and W4 are each read at it (decision 164)."
        ),
        "verdict": "IDENTICAL" if identical else "DIFFERENT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_commit": head,
        "tool": "scripts/flights/wave/wave_shared_aa_proof.py",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "cells": cells,
        "composed_config_diff": {
            "differing_leaves": diff,
            "by_class": {k: sum(1 for row in diff if row["class"] == k) for k in sorted({row["class"] for row in diff})},
            "request_affecting_leaves": unclassified,
            "reading": (
                "every differing leaf is bookkeeping except the AGREE arm's committed supply pin, which the A/A drops "
                "(item E16) and which reaches a request only through the supply's output; proof 2 finds the outputs "
                "byte-identical to each other, to the registered digest and to the committed artifact, and proof 3 "
                "finds every request byte identical"
            ) if identical else "see request_affecting_leaves, prepared_supply and request_bytes",
        },
        "prepared_supply": supply,
        "request_bytes": {
            "method": (
                "the decision-160 method verbatim (P160.capture_requests): FlightRuntime._dispatch_phase_program("
                "model_free_check=True) on each cell's own composed fragments, against the composed model fragment's "
                "REAL llama-server transport with its POST replaced by a fake server that records the body bytes and "
                "answers a canned, role-appropriate completion; a fake session receipt bound to the fragment's decoder "
                "identity; keyed by (sample_id, contact_id); dispatched serially"
            ),
            "rows": args.rows,
            "common_run_id": modes["common_run_id"],
            "own_run_ids": modes["own_run_ids"],
            "scheduling_self_control": self_control,
        },
        "scratch": str(scratch),
        "hash_quoting": (
            "64-hex identities other than the prepared-supply output digests and the study commit are quoted as "
            "sha256-prefix16:<first 16 hex> (core.flight.repin rewrites package JSON from old identity hashes to new "
            "ones at the flip and refuses any old hash left under docs/); the full values are recomputable from "
            "study_commit"
        ),
    }
    proof = P160.quote_hashes_by_prefix(proof)
    # The AGREE digest keys are claims, quoted in full like the decision-160 output digests.
    proof["prepared_supply"]["agree_arm_registered_output_sha256"] = AGREE_ARM_SUPPLY_OUTPUT_SHA256
    proof["prepared_supply"]["agree_arm"]["output_sha256_recomputed"] = supply["agree_arm"]["output_sha256_recomputed"]
    output = args.output or (repo / DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": proof["verdict"], "output": str(output),
                      "config_classes": proof["composed_config_diff"]["by_class"],
                      "unclassified": unclassified,
                      "supply": {k: supply[k]["output_sha256"] for k in CELLS},
                      "supply_equal_registered_and_committed": supply["equal_registered_and_committed"],
                      "common_run_id": common_cmp, "own_run_ids": own_cmp}, indent=1))
    return 0 if identical else 3


if __name__ == "__main__":
    raise SystemExit(main())
