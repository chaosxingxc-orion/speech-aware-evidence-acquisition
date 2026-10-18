#!/usr/bin/env python3
"""P3.2: derive and DRAFT-register the Thinking speech packets of the three carriers (A2T paired 400, Earnings-21 and Earnings-22 windows). Model-free.

Writes (config and receipt-pinned bytes only; no adapter, server, model, tokenizer, encoder or scorer contact; no ledger row unless ``--append-ledger``):

* the encoder model fragments (the SLURP Thinking GPU encoder fragment ``q4km-thinking-feature-preprocess-gpu-np1-v1`` with one legacy feature cache per pass, so no pass
  sees a foreign cache entry): one for A2T, a smoke and a full one per Earnings carrier;
* the experiment fragments: ``carrier-think-a2t-packets-gpu-v1`` (the SLURP-preprocess form, driven by ``carrier_think_packets.py a2t``) and the four Earnings window-encode
  experiments (the ``e21-dr-full-window-gpu-encoding-v1`` form, ``prepare-window-features`` under a root lease), pinned to the Thinking-identity inventories of
  ``carrier_think_window_pins_v1.json`` (so they are registrable BEFORE any inventory exists on the data root);
* the package ``docs/readiness/2026-10-18-carrier-packets-thinking-v1/`` (README, registered facts, DRAFT ledger rows, countersign texts) and its preregistration.

The seven DRAFT rows: the A2T packets pass; per Earnings carrier the model-free inventory re-key, the four-window smoke encode and the full-window encode.

    python -B scripts/flights/carriers/carrier_think_packets_write_registration.py --study-commit <sha> [--registered-at UTC] [--root DIR] [--append-ledger]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import write_tfrl_iteration_registration as reg  # noqa: E402

PKG_NAME = "carrier-packets-thinking-v1"
PACKAGE = f"docs/readiness/{fam.DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
LEDGER_MARK = "## Cell CARRIER-PACKETS-THINKING: the Thinking speech packets of the carriers (A2T paired 400; Earnings-21 and Earnings-22 windows; GPU encode in swap windows)"
BASE_FRAGMENT = "q4km-thinking-feature-preprocess-gpu-np1-v1"
INSTRUCTION = "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
CACHE_BASE = "/home/chao/feat-cache"
STATUS = reg.STATUS
INHERITED = ("A2T paired-400 / Earnings-21 discovery / Earnings-22 dev media already exposed by prior Instruct cells; label-free packet preparation, no gold, transcript or model "
             "answer is opened. Prior exposure is inherited in full.")
ZERO = fam.ZERO


def fragment_name(carrier: str, smoke: bool = False) -> str:
    return f"q4km-thinking-feature-preprocess-gpu-np1-carrier-{carrier}{'-smoke4' if smoke else ''}-v1"


def pass_specs() -> list[dict]:
    """The seven rows, in chain order."""

    out: list[dict] = []
    for carrier in fam.CARRIERS:
        p = fam.packets_spec(carrier)
        c = fam.CARRIER_SPEC[carrier]
        if p["kind"] == "receipt-rows":
            out.append({"key": f"{carrier}-packets", "carrier": carrier, "kind": "rows", "run": p["run_id"], "experiment": p["experiment"], "model": fragment_name(carrier),
                        "cache_dir": p["legacy_cache_dir"], "contacts": p["rows"], "audio": math.ceil(p["audio_seconds"]), "gpu": p["plan_gpu_hours"], "profile": "bounded-discovery-probe",
                        "split_role": "discovery", "split_hash": "965f145f581753874353216a25109a4746627095027cefbab0ed91c88090990a",
                        "carrier_text": "audio2tool A2T-PAIRED-400-V1 400 recordings",
                        "scope": ("Thinking-core speech-packet preparation for the Audio2Tool paired 400 (registry P3.2): a GPU encoder pass in a serving-swap window, one contact per row at "
                                  "max_tokens 1 (the four-row smoke stage first, then the remaining rows), then ADDITIVE promotion into the existing Thinking packet root under the new receipt "
                                  f"{fam.A2T_PROMOTION_NAME}. Label-free: no gold, task text or model output is opened.")})
            continue
        pins = json.loads(fam.WINDOW_PINS_PATH.read_text(encoding="utf-8"))[carrier]
        role = "dev" if carrier == "e22" else "discovery"
        out.append({"key": f"{carrier}-inventory", "carrier": carrier, "kind": "inventory", "run": p["inventory_run_id"], "experiment": None, "model": None, "cache_dir": None,
                    "contacts": 0, "audio": 0, "gpu": 0.0, "profile": "model-free-check", "split_role": role, "split_hash": pins["full"]["split_identity_hash"],
                    "carrier_text": f"{c['carrier_lock_key']} {role} window inventories (full {pins['full']['unit_count']:,} and smoke {pins['smoke']['unit_count']})",
                    "scope": (f"Model-free re-key of the registered Instruct window inventories of {c['label']} to the Thinking encoder identity (carrier_think_windows.py materialize): the "
                              "same slice media, request keys and digests, only the encoder identity and the identity-dependent encoding keys change. Zero model contact.")})
        for smoke in (True, False):
            key = "smoke" if smoke else "full"
            count = pins["counts"][key]["unique_audio"]
            out.append({"key": f"{carrier}-encode{'-smoke' if smoke else ''}", "carrier": carrier, "kind": "window-smoke" if smoke else "window-full",
                        "run": p["smoke_encode_run_id" if smoke else "encode_run_id"],
                        "experiment": f"carrier-think-{carrier}-window-encoding{'-smoke-4' if smoke else ''}-v1", "model": fragment_name(carrier, smoke),
                        "cache_dir": p["smoke_legacy_cache_dir" if smoke else "legacy_cache_dir"], "contacts": count,
                        "audio": math.ceil(pins["counts"][key]["unique_audio_seconds"]), "gpu": 0.3 if smoke else p["plan_gpu_hours"], "profile": "bounded-discovery-probe",
                        "split_role": role, "split_hash": pins[key]["split_identity_hash"], "pins": pins[key],
                        "carrier_text": f"{c['carrier_lock_key']} {role} {'four-window smoke' if smoke else 'full'} windows ({count:,})",
                        "scope": (f"Thinking-core exact-window feature encoding for {c['label']} ({count:,} unique {'smoke ' if smoke else ''}windows): one contact per unique window at "
                                  "max_tokens 1 on the GPU encoder under a root lease, then the cache audit, the source-bound preparation provenance and the formal window-packet promotion "
                                  "into the existing Thinking packet root. Label-free: no draft text, reference or transcript is opened.")})
    return out


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return io.open(Path(root) / path, encoding="utf-8", newline="").read()


def dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def derive_fragment(spec: Mapping[str, Any], root: Path) -> tuple[str, str]:
    doc = json.loads(rd(f"configs/model/{BASE_FRAGMENT}.json", root))
    doc["server_env"] = dict(doc["server_env"], LLAMA_MTMD_FEAT_CACHE_DIR=spec["cache_dir"])
    if spec["kind"] != "rows":
        # The Earnings runtime adapter reads an explicit serving_geometry whose max_tokens equals the request cap; the window encoder is served by the standard serving session
        # on the GPU port, as the E21 DR encoder was.
        doc["serving_geometry"] = {"slots": 1, "slot_tokens": 16384, "max_tokens": 1}
        doc["base_url"] = "http://127.0.0.1:8080"
    doc["preparation_basis"] = (f"P3.2 (registry 'P3 programme under decision 299 A', owner ruling 333 B): the GPU encoder pass of {spec['run']}. Identical to {BASE_FRAGMENT} in every serving "
                                "flag, the model pins and the runtime receipt; it differs ONLY in the legacy feature cache directory (its own, so no earlier pass's entry is a foreign entry for "
                                "this one) and, for window passes, the explicit serving_geometry the Earnings adapter reads. Offline packet preparation only: one-token responses are "
                                "discarded unread, no answer is scored. The card holds one core: every serving session is stopped before this server starts.")
    return f"configs/model/{spec['model']}.json", dump(doc)


def derive_experiment(spec: Mapping[str, Any], root: Path) -> tuple[str, str]:
    carrier = spec["carrier"]
    plan = {"execution_profile": spec["profile"], "split_role": spec["split_role"], "planned_model_calls": spec["contacts"], "planned_gpu_hours": spec["gpu"],
            "planned_speech_audio_seconds": spec["audio"]}
    if spec["kind"] == "rows":
        p = fam.packets_spec(carrier)
        doc = {
            "experiment_id": spec["run"], "execution_profile": spec["profile"], "execution_plan": plan,
            "feature_root": fam.THINK_PACKET_ROOT, "legacy_cache_dir": spec["cache_dir"], "promotion_receipt": fam.A2T_PROMOTION_RECEIPT,
            "preregistration": PREREG,
            "a2t_packets_scope": {"subset_receipt": p["roster_receipt"], "subset_receipt_sha256": p["roster_receipt_sha256"], "count": p["rows"],
                                  "audio_seconds_total": p["audio_seconds"], "smoke_rows": p["smoke_roster_rows"], "packet_id_convention": "sample_id with ':' replaced by '/'"},
            "purpose": (f"Exposure row {spec['run']} (package {PACKAGE}): {spec['scope']} The Instruct packets of these rows are decoder-ready outputs of the Instruct audio encoder and "
                        "are not valid input to the Thinking decoder (748 of 860 mmproj tensors differ). Keep every other Thinking packet and receipt untouched."),
        }
        return f"configs/experiment/{spec['experiment']}.json", dump(doc)
    pins = spec["pins"]
    dataset = {("e21", False): "earnings21-discovery", ("e21", True): "e21-native-window-four-row-v1", ("e22", False): "earnings22-dev-subset10", ("e22", True): "e22-native-window-four-row-v1"}[
        (carrier, spec["kind"] == "window-smoke")]
    smoke = spec["kind"] == "window-smoke"
    cell_stem = f"carrier-think-{carrier}-window-encoding{'-smoke-4' if smoke else ''}"
    doc = {
        "experiment_id": spec["run"], "date": fam.DATE,
        "purpose": (f"{spec['scope']} Package {PACKAGE}. One-token responses materialise features only and are not a scientific task answer."),
        "execution_plan": plan,
        "window_feature_preparation": {"inventory_relpath": pins["relpath"], "inventory_sha256": pins["sha256"], "source_run_id": pins["registry_run_id"], "expected_n_embd": 2048,
                                       "instruction": INSTRUCTION},
        "budget_basis": (f"Exactly {spec['contacts']:,} unique inputs from the Thinking-identity inventory {pins['relpath']}. Each unique window is encoded once with max_tokens=1; no automatic "
                         "retry, no extra performance probe. The GPU-hour figure is an upper bound, not a predicted use."),
        "cells": [{
            "cell_id": cell_stem, "run_id": spec["run"], "attempt_id": f"attempt-{cell_stem}-v1", "model_fragment": spec["model"], "dataset_fragment": dataset,
            "baseline_fragment": "window-feature-preprocess-ojw", "allowed_execution_stages": ["prepare-window-features"],
            "readiness": {"state": "ready", "requirements": [{"kind": "preparation", "relpath": pins["relpath"], "sha256": pins["sha256"],
                                                              "reason": "The Thinking-identity window inventory must exist unchanged (carrier_think_windows.py materialize)"}]}}],
        "service_session_id": f"serving-{cell_stem}-v1",
        "output_relpath": f"analysis/{spec['run']}/window-encoding.json",
        "split_id": "dev" if carrier == "e22" else "discovery",
    }
    return f"configs/experiment/{spec['experiment']}.json", dump(doc)


def draft_rows(specs: list[dict], commit: str, at: str, shas: Mapping[str, str]) -> list[list[str]]:
    rows = []
    for s in specs:
        artifact = f"configs/experiment/{s['experiment']}.json" if s["experiment"] else f"scripts/flights/carriers/carrier_think_windows.py (materialize --carrier {s['carrier']})"
        model_tool = (fam.think_model_text().split(";")[0] + f" ENCODER pass (GPU, -np 1 -ngl 999, fragment {s['model']}); fixed one-token response never read" if s["model"]
                      else "no model or tool contact; a pure re-keying of registered inventory bytes")
        rows.append([at[:10], s["run"], s["profile"], f"DRAFT -- REGISTERED. {s['scope']}", model_tool, s["carrier_text"], s["split_role"], s["split_hash"], "no",
                     str(s["contacts"]), str(s["audio"]), str(s["gpu"]), INHERITED, artifact,
                     f"DRAFT at study commit {commit}; nothing authorised. Package {PACKAGE}."])
    return rows


def countersign_texts(specs: list[dict]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner ruling 333 B of 2026-10-17 and the P3 programme "
            "(registry P3.2) -- the Thinking speech packets of the carriers; ")
    tail = "; promotion receipts per root are pinned into the carrier baselines by carrier_think_derive_cells.py --require-receipts after the chain seals)"
    return {"_note": "Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text below.",
            "rows": {s["run"]: head + s["carrier_text"] + tail for s in specs}}


def readme(specs: list[dict], pins: dict) -> str:
    table = "\n".join(f"| {s['key']} | `{s['run']}` | {s['profile']} | {s['contacts']:,} | {s['audio']:,} | {s['gpu']} |" for s in specs)
    return (
        "# Thinking speech packets of the carriers (P3.2) (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. Nothing is countersigned, minted or flown. Generated by `scripts/flights/carriers/carrier_think_packets_write_registration.py` from "
        "`scripts/flights/carriers/carrier_think_spec.json` and `carrier_think_window_pins_v1.json`.\n\n"
        "## Why a separate package, and why packets come first\n\n"
        "The Thinking mmproj audio tower differs from the Instruct one (748 of 860 tensors), so no Instruct packet is valid input to the Thinking decoder. The carrier baselines "
        "(`docs/readiness/2026-10-18-carrier-base-thinking-v1`) pin the SHA-256 of their Thinking packet artifact, which exists only after this chain runs; the P3.3 package is "
        "therefore derived (`--require-receipts`), registered and flipped AFTER it. All Thinking packets live in ONE root, "
        f"`{fam.THINK_PACKET_ROOT}`, extended ADDITIVELY under their own receipt per roster (the Fold B / DEV / test-sample precedent); a packet id is the recording id (A2T) or the audio "
        "digest (windows), so the root needs no carrier directory.\n\n"
        "## Rows\n\n| step | run id | profile | contacts | speech s | GPU-h ceiling |\n| --- | --- | --- | ---: | ---: | ---: |\n"
        f"{table}\n\n"
        "## A2T (`carrier_think_packets.py a2t`)\n\n"
        "The SLURP-Thinking packet pass applied to the 400 rows of `docs/checks/speech-aware-evidence-acquisition/2026-09-27-a2t-paired-400-roster/flight-roster-receipt.json`: the encoder "
        "server (Thinking decoder + its bf16 mmproj on the GPU, `-np 1`) starts inside a serving-swap window, the four-row smoke stage encodes the first four rows into the legacy cache "
        "only and measures rows per minute, the full stage encodes the remaining rows, the server stops normally, and all 400 are promoted into the packet root under "
        f"`{fam.A2T_PROMOTION_NAME}` (create-only). Wrapper: `scripts/flights/carriers/carrier_think_packets_gpu.sh a2t`.\n\n"
        "## Earnings windows (`carrier_think_packets.py windows`)\n\n"
        "An exact-window inventory binds the encoder identity, so the registered Instruct inventories are RE-KEYED to the Thinking identity model-free "
        "(`carrier_think_windows.py`; the transform reproduces all four registered Instruct inventory hashes byte for byte, `selfcheck`) with NO new slice cut: the requests point at the "
        "registered Instruct slices (4.3 GB / 1.2 GB are not duplicated). The pins are in `carrier_think_window_pins_v1.json`; the encode experiments are registered against them now. "
        "Per carrier the chain then runs the four-window SMOKE pass (encode under a root lease, audit, provenance, formal packets) and, only if it passes, the FULL pass. "
        "The 4 smoke windows are re-encoded in the full pass into its own cache (4 extra contacts, inside the plan); their packets are promoted twice, and the second promotion "
        "is accepted only when the chunks are identical (harness item E40: `shared`); a conflicting packet id is never overwritten and stops the chain.\n\n"
        "## Order\n\n"
        "1. `bash scripts/flights/batch/package_launch.sh scripts/flights/carriers/carrier_think_packets_launch_spec.json --root-countersign --until commit` (derive, write, countersign "
        "the seven rows, commit).\n"
        "2. `bash scripts/flights/carriers/batch_chain_carrier_packets.sh all` (the Windows task SAEA-Chain-CARRIERPACKETS; A2T -> E21 -> E22): per carrier one swap window "
        "(stop the resident session, encode, promote, start the Thinking session) with a rate gate between the smoke and the full stage.\n"
        "3. Then the P3.3 package (`carrier_think_base_launch_spec.json`), which refuses unless every packet pin exists.\n\n"
        "## Honest limits\n\n"
        "* The A2T stage follows the proven SLURP-Thinking and A2T-G1 drivers primitive for primitive; the Earnings window stage (lease, `prepare-window-features`, audit, provenance, "
        "packets) follows the library contracts and the registered E21 DR encoding, but has never been exercised on the Thinking core: the four-window smoke pass IS its rehearsal, and "
        "the chain stops after the smoke unless the rate gate and every receipt check pass.\n"
        "* Window inventories are new data-root files (about 5 MB each); nothing else on the data root is written by the model-free stage.\n")


def write_package(root: Path, commit: str, at: str | None, *, append_ledger: bool = False) -> dict:
    root = Path(root)
    at = at or datetime.now(timezone.utc).isoformat()
    specs = pass_specs()
    written = []
    for s in specs:
        if s["model"]:
            path, text = derive_fragment(s, root)
            reg.wr(root, path, text)
            written.append(path)
            path, text = derive_experiment(s, root)
            reg.wr(root, path, text)
            written.append(path)
    pins = json.loads(fam.WINDOW_PINS_PATH.read_text(encoding="utf-8"))
    facts = {"schema": "saea-registered-facts-v1", "status": "DRAFT-HELD", "registered_at_utc": at, "study_commit_at_registration": commit,
             "passes": [{k: v for k, v in s.items() if k != "pins"} for s in specs], "window_pins": pins, "packet_root": fam.THINK_PACKET_ROOT,
             "a2t_promotion_receipt": fam.A2T_PROMOTION_RECEIPT, "encoder_fragment_base": BASE_FRAGMENT, "owner_rulings": fam.OWNER_RULINGS,
             "totals": {"contacts": sum(s["contacts"] for s in specs), "gpu_hours_ceiling": round(sum(float(s["gpu"]) for s in specs), 1)},
             "prohibitions": ["No test-split contact.", "No Instruct packet, receipt or cache entry is touched.", "No pass starts before its exposure row is countersigned.",
                              "No window pass starts unless its inventory hashes to the pin in carrier_think_window_pins_v1.json."]}
    shas = {"registered-facts-v1.json": reg.wjson(root, f"{PACKAGE}/registered-facts-v1.json", facts)}
    rows = draft_rows(specs, commit, at, shas)
    lines = [LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(rows)} unconsumed rows for the P3.2 carrier packets of the owner rulings in {fam.OWNER_RULINGS}. Package {PACKAGE}. No row is countersigned and no row authorises a contact.", "",
             "| " + " | ".join(reg.LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in reg.LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(r) for r in rows]
    rows_text = "\n".join(lines) + "\n"
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{PACKAGE}/draft-ledger-rows.md", rows_text)
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{PACKAGE}/countersign-row-texts-v1.json", countersign_texts(specs))
    shas["README.md"] = reg.wr(root, f"{PACKAGE}/README.md", readme(specs, pins))
    shas["__prereg__"] = reg.wr(root, PREREG, f"# Carrier Thinking packets, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. Label-free packet preparation.\n\n"
                                f"Runs: {', '.join('`' + s['run'] + '`' for s in specs)}.\n\nThe design is in `{PACKAGE}/README.md`.\n")
    result = {"package": PACKAGE, "written": written, "shas": shas, "rows": len(rows)}
    if append_ledger:
        ledger = root / reg.LEDGER
        current = io.open(ledger, encoding="utf-8", newline="").read()
        if LEDGER_MARK in current:
            result["ledger_appended"] = False
        else:
            io.open(ledger, "w", encoding="utf-8", newline="").write(current.rstrip("\n") + "\n\n" + rows_text)
            result["ledger_appended"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", default=None)
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
