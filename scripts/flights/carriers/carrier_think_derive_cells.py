#!/usr/bin/env python3
"""Derive the nine carrier cells of the Thinking-core carrier base (config only): baselines, experiments, campaign plans and the sign-off conditions.

For each carrier (A2T, E21, E22) three HELD cells -- the four-row smoke, the consumption-module ALL-OFF arm and the DIRECT baseline -- are derived from the
registered Instruct all-off cells (``configs/experiment/<source>.json`` and the baselines they name) by exactly the leaves the core swap and the Thinking knobs
move, and nothing else:

* the model fragment (the SLURP lock's Thinking fragment, np4 x 24,576, budget 3,072 / cap 4,096) and its serving session;
* the carrier's serving geometry in the baseline (A2T: np3 x 32,768 / cap 2,048 -> np4 x 24,576 / cap 4,096; the Earnings baselines gain the explicit
  ``serving_geometry`` their runtime adapter reads, because the SLURP fragment does not carry one);
* the speech-packet pins: A2T ``speech_packet_promotion_receipt`` (+ sha256) and the Earnings ``prepared_window_feature_packets`` / ``prepared_execution_units``
  (the Thinking mmproj audio tower differs from the Instruct one, so no Instruct packet is valid input);
* the run, attempt and live-phase-fit ids, the budgets (the plan ceiling adds ONE answer-only fallback contact per contact), the Earnings workflow timeout and the
  prose.

``direct`` is the ``alloff`` cell without its module declaration: the module's all-off block compiles to the carrier's direct layer (the Instruct byte proof), so
the pair is request-identical and is the carrier's in-chain A/A. ``prove`` composes every cell through the runtime's own ``core.config.compose`` and refuses unless
(1) alloff and direct differ by identity leaves only and (2) every request-shaping leaf of each Thinking cell equals its Instruct source's except the declared moves.

    python -B scripts/flights/carriers/carrier_think_derive_cells.py [--require-receipts] [--no-write] [--prove]

``--require-receipts`` pins the real Thinking packet artifacts (A2T promotion receipt, Earnings window-packet artifacts) and refuses when one is absent; without it
the baselines carry the zero sentinel and the flip refuses it (the SLURP precedent: pin, then register, then flip).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ZERO = fam.ZERO
DATA_PLACEHOLDER = "${SAEA_DATA_ROOT}"

# Leaves that may differ between a Thinking cell and its Instruct source. Everything not listed is a PROTECTED request-shaping leaf and must be equal.
MOVED_MODEL = ("decoding_params", "server_args", "server_env", "speech_feature_root", "runtime_receipt", "model_lock_key", "timeout_seconds", "base_url",
               "reasoning_", "enable_thinking", "forced_close_message_sha256", "answer_reserve_tokens", "geometry_basis", "preparation_basis",
               "feature_encoder_runtime_receipt", "preserve_wire_responses", "transport", "model_materialization_root", "profile_slot_count", "serving_geometry",
               "serving_slot_tokens", "serving_slots", "thinking_", "speech_decoder")
MOVED_BASELINE = ("speech_packet_promotion_receipt", "prepared_window_feature_packets", "prepared_execution_units", "live_phase_fit", "what_this_is",
                  "ojw_workflow_timeout_seconds")
MOVED_EXPERIMENT = ("experiment_id", "date", "execution_plan", "family_budget", "generation_budget", "fragment_kind", "stage3_", "failure_policy", "purpose",
                    "service_session", "cells", "consumption_module_declaration", "own_null_pair", "analysis_plan", "core_read_design")
MOVED_ALLOWED = MOVED_MODEL + MOVED_BASELINE + MOVED_EXPERIMENT
#: Leaves that are identity / prose only and may differ between the two request-identical arms (alloff vs direct).
IDENTITY_ONLY = ("live_phase_fit", "what_this_is", "experiment_id", "execution_plan", "family_budget", "generation_budget", "fragment_kind", "stage3_",
                 "failure_policy", "purpose", "cells", "consumption_module_declaration", "own_null_pair", "core_read_design", "date")


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return io.open(Path(root) / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str, root: Path = REPO_ROOT) -> None:
    target = Path(root) / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def sha_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data_root() -> Path | None:
    value = os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR")
    return Path(value) if value else None


# ---- the packet pins -------------------------------------------------------------------------------------------------------------
def load_window_pins(root: Path = REPO_ROOT) -> dict:
    path = fam.WINDOW_PINS_PATH
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def receipt_pins(carrier: str, kind: str, *, require: bool, root: Path = REPO_ROOT) -> dict:
    """The Thinking packet pins of one cell: ``{"promotion_sha256"}`` (A2T) or ``{"packets_sha256", "units"}`` (Earnings). A missing artifact is the zero sentinel,
    or a refusal when ``require`` is set."""

    smoke = kind == "smoke"
    data = data_root()
    if carrier == "a2t":
        sha = ZERO
        path = Path(fam.A2T_PROMOTION_RECEIPT)
        if path.is_file():
            sha = sha_file(path)
        elif require:
            raise SystemExit(f"--require-receipts: the A2T Thinking promotion receipt {path} is absent (run the P3.2 packets chain first)")
        return {"promotion_sha256": sha}
    out: dict[str, Any] = {"packets_sha256": ZERO, "units": None}
    rel = fam.window_artifact_relpath(carrier, smoke)
    if data is not None and (data / rel).is_file():
        out["packets_sha256"] = sha_file(data / rel)
    elif require:
        raise SystemExit(f"--require-receipts: the Thinking window-packet artifact {rel} is absent under the data root (run the P3.2 packets chain first)")
    pins = load_window_pins(root).get(carrier, {}).get("smoke" if smoke else "full")
    if pins:
        out["units"] = pins
    elif require:
        raise SystemExit(f"--require-receipts: {fam.WINDOW_PINS_PATH.name} carries no Thinking inventory pin for {carrier} ({'smoke' if smoke else 'full'})")
    return out


# ---- baseline ---------------------------------------------------------------------------------------------------------------------
def what_this_is(carrier: str, kind: str) -> str:
    c = fam.CARRIER_SPEC[carrier]
    core = (f"the Thinking core (the SLURP lock's serving session {fam.THINK_SESSION}; reasoning budget {fam.BUDGET} + answer reserve {fam.RESERVE} = cap {fam.CAP}, "
            f"{fam.tsf.REASONING_CONTEXT_POLICY}), its own speech packets")
    if kind == "smoke":
        return (f"Four-row form smoke of the {c['label']} carrier base on {core}: the all-off form on the carrier's first four units. It proves the request form, the Thinking "
                "packet plane, the reasoning-format option and the seal, and measures decode cost for the machine sign-off BEFORE the arms are flown. Scored by no one.")
    if kind == "alloff":
        return (f"{c['label']} consumption-module ALL-OFF arm on {core}: every module component off, which compiles to the carrier's direct layer (the direct-only phase "
                "program of the shared controller). Request-identical to the direct arm of the same package; the pair is the carrier's in-chain A/A on the Thinking core. No "
                "knowledge supply, no analytical tool, no native tool authority, no mechanism.")
    return (f"{c['label']} DIRECT baseline on {core}: the direct-only phase program of the shared controller through the same FlightRuntime and the same OpenJiuwen executor "
            "as the all-off arm (no separate baseline code path). Request-identical to the all-off arm of the same package; the pair is the carrier's in-chain A/A.")


def derive_baseline(key: str, *, require: bool, root: Path = REPO_ROOT) -> tuple[str, dict]:
    s = fam.CELLS[key]
    carrier, kind = s["carrier"], s["kind"]
    src_name = fam.source_baseline_name(carrier, kind, root)
    raw = rd(f"configs/baseline/{src_name}.json", root)
    doc = json.loads(raw)
    geometry = {"max_tokens": fam.CAP, "slot_tokens": fam.SLOT_TOKENS, "slots": fam.SLOTS}
    pins = receipt_pins(carrier, kind, require=require, root=root)
    if carrier == "a2t":
        doc["serving_geometry"] = geometry
        doc["serving_slot_tokens"], doc["serving_slots"] = fam.SLOT_TOKENS, fam.SLOTS
        doc["speech_packet_promotion_receipt"] = fam.A2T_PROMOTION_RECEIPT
        doc["speech_packet_promotion_receipt_sha256"] = pins["promotion_sha256"]
        cap = fam.fit_cap(key)
        if doc["live_phase_fit"]["contact_cap"] != cap:
            raise SystemExit(f"{key}: the source FIT cap {doc['live_phase_fit']['contact_cap']} differs from the structural cap {cap}")
        doc["live_phase_fit"] = {"attempt_id": s["fit_attempt"], "contact_cap": cap, "run_id": s["fit_run"]}
    else:
        if doc.get("serving_slot_tokens") != fam.SLOT_TOKENS or doc.get("serving_slots") != fam.SLOTS:
            raise SystemExit(f"{key}: the source baseline is not on the np4 x 24,576 geometry")
        doc["serving_geometry"] = geometry                         # the Earnings runtime adapter reads it; the Instruct fragment carried it, the SLURP fragment does not
        doc["ojw_workflow_timeout_seconds"] = int(fam.CARRIER_SPEC[carrier]["workflow_timeout_seconds"])
        packets = {"path": f"{DATA_PLACEHOLDER}/{fam.window_artifact_relpath(carrier, kind == 'smoke')}", "sha256": pins["packets_sha256"]}
        doc["prepared_window_feature_packets"] = packets
        if pins["units"]:
            doc["prepared_execution_units"] = copy.deepcopy(pins["units"])
    doc["what_this_is"] = what_this_is(carrier, kind)
    out = f"configs/baseline/{s['baseline']}.json"
    return out, {"path": out, "text": dump_like(raw, doc), "doc": doc}


# ---- experiment ---------------------------------------------------------------------------------------------------------------------
def units_word(carrier: str) -> str:
    return "window" if fam.CARRIER_SPEC[carrier]["unit_kind"] == "windows" else "row"


STAGE3_ALGORITHM_NOTE = ("This cell carries NO training-free RL operator and says so explicitly: it is a carrier BASELINE on the Thinking core (the consumption module with every "
                         "component off, or the direct-only program it compiles to). No rollout, no per-sample scoring, no credit assignment, no update operator, no evolving "
                         "store and no mechanism.")

FAILURE_POLICY = ("Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, prompt, knowledge, geometry or cap change. A failure in the smoke stops the "
                  "chain and the arms do not open; a failure in the first arm stops the chain and the second arm does not open. AT MOST ONE root-diagnosed recovery re-registration "
                  "per run id (a new generation attempt id, and for a cell with a live phase fit a new fit run and attempt id as well); a second failure closes the cell and the fix is "
                  "proven on a four-row dry run. RESUME-RECOVERY CLAUSE (owner decision 22 of 2026-09-18): an INFRASTRUCTURE abort with code and request bytes unchanged takes the "
                  "resume-recovery form of harness item E10 -- the same run id, a fresh attempt id, a resume_from declaration naming the predecessor attempt and its trace SHA-256, "
                  "every COMPLETE row kept without selection under invariant I7r, every partial or unstarted row re-flown in full, no change to the roster, comparator, decision rule "
                  "or caps, and the run-cumulative budget re-checked. A response whose delivered content carries a reasoning marker stops the flight (reasoning_content_guard). A "
                  "partial manifest is never scored and never read. If the all-off and direct arms do not seal on ONE resident session, the pair is not request-identical and the "
                  "null is not read from it.")


def measurement_note(carrier: str, kind: str) -> str:
    if kind == "smoke":
        return ("Four units prove FORM only: the request form, the Thinking packet plane, the reasoning-format option and the seal work on the Thinking core, and the decode cost is "
                "measured for the machine sign-off. Scored by no one; four units claim nothing under instrument rule 5.")
    return (f"Form proof of the {fam.CARRIER_SPEC[carrier]['label']} baseline on the Thinking core (design 2b.3): the all-off arm and the direct arm are request-identical, so "
            "their difference is the carrier's A/A on this core and nothing is expected to move; the numbers are the baseline of record (development numbers only, owner decisions 28 "
            "and 86). No benefit is claimed.")


def derive_experiment(key: str, *, root: Path = REPO_ROOT) -> tuple[str, dict]:
    s = fam.CELLS[key]
    carrier, kind = s["carrier"], s["kind"]
    c = fam.CARRIER_SPEC[carrier]
    src_name = fam.source_experiment_name(carrier, kind)
    raw = rd(f"configs/experiment/{src_name}.json", root)
    doc = json.loads(raw)
    units = s["units"]
    u = units_word(carrier)
    calls, audio = fam.generation_calls(key), fam.audio_cap(key, root)
    fit_cap = fam.fit_cap(key)
    gpu = s["gpu_hours"]
    family = dict(doc["family_budget"])
    family.update({"generation_calls_cap": calls, "repeated_speech_audio_seconds_cap": audio, "gpu_hours_fit_inclusive": gpu,
                   "fit_endpoint_calls_cap": fit_cap})
    plan = dict(doc["execution_plan"])
    plan.update({"planned_gpu_hours": gpu, "planned_model_calls": calls, "planned_speech_audio_seconds": audio})
    doc["execution_plan"], doc["family_budget"] = plan, family
    fit_text = (f" The live phase fit makes 1 + (2 + 1) x {units} = {fit_cap:,} tokenizer endpoint calls under its own run id {s['fit_run']}." if s["fit_run"]
                else " No fit identity (the direct baseline declares none, as the flown E35 direct arms).")
    doc["generation_budget"] = {
        "cap": calls, "target": calls, "ceilings_are_not_targets": True,
        "definition": (f"The direct-only phase program makes exactly one contact per {u}: {units:,} x 1 = {units:,} is the program's exact maximum; the plan ceiling adds ONE "
                       f"answer-only fallback contact per budgeted-thinking contact (core.reasoning_knobs, FALLBACK_CONTACTS_PER_ROW_DIRECT = 1): {calls:,} = {units:,} x 2." + fit_text
                       + f" The GPU-hour ceiling is a BOUND (units x {fam.seconds_per_contact(carrier):g} s per contact measured on the Thinking SLURP lock / 4 slots / 3600 x "
                       f"{fam.GPU_MARGIN:g}, ceil {fam.GPU_ROUND_H:g}), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id.")}
    doc["experiment_id"] = s["run"]
    doc["date"] = fam.DATE
    doc["fragment_kind"] = f"saea-{s['cell'][:-3]}-v1"
    doc["service_session"] = s["session"]
    # The Instruct Earnings model fragment carried preserve_wire_responses=true; the Thinking fragment carries none, so the experiment states it (A2T already did).
    doc["preserve_wire_responses"] = True
    doc["failure_policy"] = FAILURE_POLICY
    doc["stage3_algorithm"] = {"id": "none", "note": STAGE3_ALGORITHM_NOTE, "operators_used": []}
    measurement = dict(doc["stage3_measurement"])
    measurement.update({"claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof", "note": measurement_note(carrier, kind),
                        "tuning_roster": "none"})
    doc["stage3_measurement"] = measurement
    doc["purpose"] = (f"{s['role']} (owner rulings 302 A / 306 A / 333 B; registry P3.3). "
                      + ("A four-unit decode-cost smoke: it seals and reports tokens per answer, seconds per contact and the GPU-hour projection BEFORE the arms are queued. "
                         "No score, no read. " if kind == "smoke" else
                         "One of the carrier's two request-identical arms on the Thinking core, flown back to back in one chain so their difference is the carrier's A/A on this "
                         "core and their level is the baseline of record. ")
                      + f"Instruct comparator: {c['instruct_comparator']}. Development numbers only (owner decisions 28 and 86); never a test claim. "
                      "Nothing here authorises a flight, a readiness flip or an admission entry.")
    if kind == "direct":
        doc.pop("consumption_module_declaration", None)
    elif "consumption_module_declaration" in doc:
        doc["consumption_module_declaration"]["compiles_to"] += " (on the Thinking core: the same bytes with the Thinking model fragment, geometry and packet pins)"
    cell = doc["cells"][0]
    cell.update(attempt_id=s["attempt"], baseline_fragment=s["baseline"], cell_id=s["cell"], model_fragment=s["model"], run_id=s["run"])
    decision = {"kind": "decision", "expected_decision_id": fam.DECISION_ID, "relpath": fam.DECISION_RELPATH, "sha256": ZERO,
                "reason": f"Decision {fam.DECISION_ID} pinned by scripts/flights/repin_cell.py."}
    held = ("HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/carriers/carrier_think_mint_receipt.py), swaps the serving geometry to "
            f"the Thinking session (scripts/flights/batch/serving_swap.sh {fam.THINK_SWAP_TARGET}) and flips the cells with scripts/flights/batch/flip_package_ext4.sh through "
            "scripts/flights/carriers/carrier_think_flip.sh; the program declares no supplied first phase, so the flip creates no prepared artifact; --allow-output-change "
            "must never be passed. The flip refuses while a Thinking packet pin is the zero sentinel. Nothing here authorises a flight, a readiness flip or an admission entry.")
    cell["readiness"] = {
        "reason": (f"{s['role']}, registered before contact on {fam.DATE} by script (decision 58) from the registered Instruct all-off cell {src_name} (owner rulings 302 A / 306 A / "
                   f"333 B). {held}"),
        "requirements": [decision], "state": "held"}
    out = f"configs/experiment/{s['cell']}.json"
    existing = Path(root) / out
    if existing.is_file():
        # A re-derivation after the flip keeps the cell's readiness block (state, reason, pinned receipt): the flip's re-pin owns it.
        previous = json.loads(existing.read_text(encoding="utf-8"))["cells"][0]["readiness"]
        if previous.get("state") != "held":
            cell["readiness"] = previous
    return out, {"path": out, "text": dump_like(raw, doc), "doc": doc}


def campaign_text(key: str) -> tuple[str, str]:
    s = fam.CELLS[key]
    return s["campaign"], json.dumps({"cells": [{"cell": s["cell"], "experiment": s["cell"]}], "schema": "saea-campaign-plan-v1"}, indent=2, sort_keys=True) + "\n"


def signoff_text(carrier: str) -> str:
    return json.dumps(fam.signoff_conditions(carrier), indent=2, ensure_ascii=False, sort_keys=True) + "\n"


# ---- the proof ---------------------------------------------------------------------------------------------------------------------------
def flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, Mapping):
        for k, v in node.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(node, list) and any(isinstance(v, (dict, list)) for v in node):
        for i, v in enumerate(node):
            out.update(flatten(v, f"{prefix}{i}."))
    else:
        out[prefix[:-1]] = node
    return out


def _starts(key: str, prefixes: tuple[str, ...]) -> bool:
    return any(key == p or key.startswith(p) or key.startswith(p + ".") for p in prefixes)


def compose_cell(root: Path, experiment: str):
    from speech_aware_evidence_acquisition.core.config import compose

    cell = json.loads((Path(root) / "configs" / "experiment" / f"{experiment}.json").read_text(encoding="utf-8"))["cells"][0]
    return compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)


def moved_leaves(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    fa, fb = flatten(a), flatten(b)
    return sorted(k for k in set(fa) | set(fb) if fa.get(k, "<absent>") != fb.get(k, "<absent>"))


def prove(root: Path = REPO_ROOT) -> dict:
    """The composed-config proof. Raises SystemExit on any leaf beyond the declared set; returns the proof document."""

    report: dict[str, Any] = {}
    for carrier in fam.CARRIERS:
        per: dict[str, Any] = {}
        composed = {k: compose_cell(root, fam.CELLS[fam.cell_key(carrier, k)]["cell"]) for k in fam.KINDS}
        sources = {k: compose_cell(root, fam.source_experiment_name(carrier, k)) for k in ("smoke", "alloff")}
        pair = moved_leaves(composed["alloff"].values, composed["direct"].values)
        stray = [k for k in pair if not _starts(k, IDENTITY_ONLY)]
        if stray:
            raise SystemExit(f"{carrier}: alloff and direct differ beyond identity leaves: {stray}")
        per["alloff_vs_direct_moved_identity_leaves"] = pair
        for kind in fam.KINDS:
            src = sources["smoke" if kind == "smoke" else "alloff"]
            moved = moved_leaves(src.values, composed[kind].values)
            stray = [k for k in moved if not _starts(k, MOVED_ALLOWED)]
            if stray:
                raise SystemExit(f"{carrier}/{kind}: leaves moved beyond the declared Thinking changes: {stray}")
            per[f"{kind}_vs_instruct_source"] = {"source": fam.source_experiment_name(carrier, kind), "moved": moved,
                                                 "composed_config_hash": composed[kind].config_hash}
        report[carrier] = per
    return report


# ---- main -----------------------------------------------------------------------------------------------------------------------------
def derive(*, write: bool = True, require_receipts: bool = False, root: Path = REPO_ROOT) -> dict:
    written: list[str] = []
    for key in fam.ALL_KEYS:
        for path, entry in (derive_baseline(key, require=require_receipts, root=root), derive_experiment(key, root=root)):
            if write:
                wr(path, entry["text"], root)
            written.append(path)
        if fam.CELLS[key]["campaign"]:
            path, text = campaign_text(key)
            if write:
                wr(path, text, root)
            written.append(path)
    for carrier in fam.CARRIERS:
        path = fam.signoff_conditions_path(carrier)
        if write:
            wr(path, signoff_text(carrier), root)
        written.append(path)
    result: dict[str, Any] = {"written": written if write else [], "cells": list(fam.ALL_KEYS)}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--require-receipts", action="store_true", help="pin the real Thinking packet artifacts; refuse when one is absent")
    parser.add_argument("--no-write", action="store_true", help="derive and verify in memory; write nothing")
    parser.add_argument("--prove", action="store_true", help="print the composed-config proof of the committed cells")
    parser.add_argument("--verbose", action="store_true", help="with --prove: print every moved leaf")
    parser.add_argument("--root", default=str(REPO_ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.prove:
        proof = prove(root)
        print(json.dumps(proof if args.verbose else {c: {k: (len(v) if isinstance(v, list) else len(v["moved"])) for k, v in per.items()} for c, per in proof.items()},
                         indent=2, sort_keys=True))
        return 0
    result = derive(write=not args.no_write, require_receipts=args.require_receipts, root=root)
    if not args.no_write:
        proof = prove(root)
        result["proof_ok"] = True
        result["moved_counts"] = {c: {k: len(v["moved"]) for k, v in per.items() if isinstance(v, dict) and "moved" in v} for c, per in proof.items()}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
