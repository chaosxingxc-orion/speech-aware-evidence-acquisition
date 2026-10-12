#!/usr/bin/env python3
"""Derive and register the per-carrier ALL-OFF arm of the evidence-consumption module -- the carrier admission gate of
design section 2b.3 -- for Audio2Tool (``--carrier a2t``), Earnings-21 (``--carrier e21``) or Earnings-22
(``--carrier e22``, 2026-10-11). HELD, model-free.

Owner decision 196, direction 205; design ``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md``
sections 2b and 3.2 ("bare": every component off compiles to the carrier's direct baseline through the same harness).
Neither carrier has a locked system, so the module's all-off block compiles to the carrier's DIRECT layer
(``rails/adapters/<profile>_module_hooks.py``) and the all-off arm IS that direct baseline's bytes:

* ``a2t``: ``a2t-native-stage3-module-alloff-v1`` (+ ``-smoke-4-v1``) on the paired 400 (A2T-PAIRED-400-V1, the roster
  h_A2T was measured on), derived from the A2T-AA pass A / smoke fragments with fresh run, attempt and live-fit
  identities (a journaled fit identity binds one attempt, so each cell needs its own baseline file);
* ``e21``: ``earnings21-native-stage3-module-alloff-v1`` (+ ``-smoke-4-v1``) on the full 44-call discovery roster (the
  four-row form smoke on the E35 four windows), pointing at the EXISTING direct baselines
  ``e21-native-window-direct-full44-v1`` / ``e21-native-window-direct-four-row-v1`` byte for byte (they carry no fit
  identity);
* ``e22``: ``earnings22-native-stage3-module-alloff-v1`` (+ ``-smoke-4-v1``) on the whole 10-call Earnings-22 dev split
  (451 native windows; the four-row form smoke on the first four windows of call 4453225). Earnings-22 has no direct
  parent cell, so this derivation WRITES the two baseline fragments (the shared ``e22-native-window-direct-base-v1``
  policy layer plus the E21-shaped geometry and pins), the smoke dataset fragment and the two experiment fragments from
  the model-free window-inventory receipt (``window-inventory-receipt-v1.json`` in the package); the byte proof compares
  against the base fragment instead of a parent cell.

A direct program carries no ``native_episode``, so each cell declares its block in the experiment fragment
(``consumption_module_declaration``); ``scripts/analysis/module_equivalence_proof.py --at a2t0 | e210`` proves the
block compiles to the cell's own composed hash and that the cell differs from its direct parent by no policy leaf.
The ``stage3_measurement`` is a FORM proof (``claims_benefit: false``); no component-on cell is registered.

It writes configs (A2T only: two baselines), two experiment fragments, one campaign plan, the readiness package
(registered facts, protocol, plan documents, analysis recipe, root-admission draft, README) and the preregistration,
and with ``--append-ledger`` DRAFT exposure rows. No contact of any kind; flips nothing, mints nothing.

    python -B scripts/flights/module/register_carrier_module_alloff_cells.py --carrier a2t \\
        --study-commit <sha> --registered-at <iso> [--append-ledger]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "analysis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402

DATE = "2026-09-30"
LEDGER = "docs/exposure-ledger.md"
DESIGN = "docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
FIT_ENDPOINTS = lambda rows: 1 * (1 + (2 + 1) * rows)  # noqa: E731  (direct-only program, one media packet per row)

CARRIERS = {
    "a2t": {
        "at": "a2t0", "profile": "audio2tool", "carrier_lock_key": "audio2tool", "stem": "a2t-native-stage3-module-alloff-v1",
        "run_stem": "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF", "roster": "A2T-PAIRED-400-V1 (docs/receipts/rosters/a2t-paired-400-v1.json)",
        "session": "serving-a2t-native-role-base-np3-max2048-v3", "live_fit": True,
        "parents": {"arm": "a2t-stage3-aa-paired-400-a-v1", "smoke": "a2t-stage3-aa-paired-400-smoke-4-v1"},
        "cells": {"arm": "a2t-native-stage3-module-alloff-v1", "smoke": "a2t-native-stage3-module-alloff-smoke-4-v1"},
        "budget": {"arm": {"calls": 400, "audio": 2761, "gpu": 0.5, "scoring": 1}, "smoke": {"calls": 4, "audio": None, "gpu": 0.2, "scoring": 0}},
        "lock_fragment": "a2t-native-system-direct-v1",
        "no_lock": "Audio2Tool has no locked system (base lock v3 section 4; the harness receipt names no Audio2Tool default plan), so the module's all-off arm is the DIRECT baseline of the shared controller -- a2t-native-system-direct-v1's policy blocks (phase-direct-only-v1 and its one phase_material.direct entry), byte-identical to the sealed direct a2t-native-role-direct-union4000-v1 and to both A2T-AA passes.",
        "own_null": "h_A2T 1.625 pp official tool accuracy, 1.375 pp official exact match, parameter-F1 margin 2.23 (owner decision 167, docs/results/2026-09-27-a2t-aa-paired-400-read.md), measured on THESE request bytes: the all-off arm is request-identical to A2T-AA pass A and pass B, so its module null is that null by construction, and the carrier admission gate (design 2b.3) is met by the byte proof without a new flight.",
        "scorers": "a2t-toolcall-official (paper-facing, arXiv:2604.22821 Table 3 calibration) beside a2t-toolcall-v2 / a2t-toolcall / cost",
        "model_tool": "Frozen Q4_K_M decoder-only (q4km-mmproj-free-a2t-native-role-np3-max2048-v1): c98304 np3 max2048; promoted A2T speech packets; NO native tool authority; the direct-only program (one contact per row) compiled by the consumption module from its all-off block (profile audio2tool)",
        "carrier_line": "audio2tool A2T-PAIRED-400-V1 {rows}",
        "chain": {"rows": 400, "cpr": 1, "ceil": 1, "smoke_rows": 4},
        "inherited": "Every row already flew in the sealed direct SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1 and in both A2T-AA passes; this cell adds no new speech identity and opens no split. Prior exposure is inherited in full.",
    },
    "e21": {
        "at": "e210", "profile": "earnings", "carrier_lock_key": "earnings21-original", "stem": "earnings21-native-stage3-module-alloff-v1",
        "run_stem": "SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF", "roster": "Earnings-21 full discovery, 44 calls / 1,593 native windows (split identity fcc1b0bc...)",
        "session": "serving-e21-native-window-flightruntime-np4-max1024-v1", "live_fit": False,
        "parents": {"arm": "e21-native-window-direct-full44-v1", "smoke": "e21-native-window-four-row-direct-vs-system-v1"},
        "parent_cells": {"arm": "e21-native-window-direct-full44-v1", "smoke": "e21-native-window-direct-four-row-v1"},
        "cells": {"arm": "earnings21-native-stage3-module-alloff-v1", "smoke": "earnings21-native-stage3-module-alloff-smoke-4-v1"},
        "budget": {"arm": {"calls": 1593, "audio": 141346, "gpu": 4.0, "scoring": 1}, "smoke": {"calls": 4, "audio": 360, "gpu": 0.3, "scoring": 0}},
        "lock_fragment": "e21-native-window-direct-full44-v1",
        "no_lock": "Earnings has no locked system: the six-node form flew once (item E35, STRUCTURAL PASS) and is NOT admitted (base lock v3 section 4; E39 / E41 are four-row form proofs). The E35 read names the DIRECT arm as the comparator, so the module's all-off arm is the direct baseline on the full discovery roster -- e21-native-window-direct-full44-v1, referenced byte for byte (it carries no fit identity).",
        "own_null": "E21's measured own null (WER 0.058, PERSON 0.250, ORG 0.356, numeric 0.157; docs/results/2026-09-27-verdict-reclassification.md) was measured on the pre-FlightRuntime buf90 direct form (SAEA-E21-FULL44-NULL-REPLICATE-V1), NOT on these native-window bytes; the module null on this form is unmeasured until an in-chain A/A of this arm seals (design 2b.3).",
        "scorers": "asr-wer-whisper (Whisper-normalised WER) beside conec-entity-wer-official, numeric-value-accuracy-v1, semantic-high-impact-error-rate-v1 and cost",
        "model_tool": "Frozen Q4_K_M decoder-only (q4km-e21-native-window-packets-cddb000c-np4-max1024-v1): c98304 np4 max1024, no mmproj; pinned e21-cddb000c-dr-full-gpu-v1 speech-feature packets; NO native tool authority; the direct-only program (one contact per window) compiled by the consumption module from its all-off block (profile earnings)",
        "carrier_line": "earnings21-original discovery {rows}",
        "chain": {"rows": 44, "cpr": 37, "ceil": 400, "smoke_rows": 1},
        "inherited": "Every window already exposed by the E21 full-window encoding pass and the sealed E21 direct / system cells (E35 sub10 and four-row, E39, E41) on the same discovery calls; no new speech identity and no new split. Prior exposure is inherited in full.",
    },
    "e22": {
        "at": "e220", "profile": "earnings22", "carrier_lock_key": "earnings22-original", "stem": "earnings22-native-stage3-module-alloff-v1",
        "package_stem": "earnings22-module-alloff-v1", "date": "2026-10-11", "split_role": "dev",
        "run_stem": "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF", "roster": "Earnings-22 whole dev split, 10 calls / 451 native windows (split identity 89b178d6...)",
        "session": "serving-e22-native-window-flightruntime-np4-max1024-v1", "live_fit": False,
        "parents": {"arm": None, "smoke": None},
        "cells": {"arm": "earnings22-native-stage3-module-alloff-v1", "smoke": "earnings22-native-stage3-module-alloff-smoke-4-v1"},
        "budget": {"arm": {"calls": 451, "audio": 40056, "gpu": 1.5, "scoring": 1}, "smoke": {"calls": 4, "audio": 360, "gpu": 0.3, "scoring": 0}},
        "lock_fragment": "e22-native-window-direct-base-v1",
        "baselines": {"arm": "e22-native-window-direct-dev10-v1", "smoke": "e22-native-window-direct-four-row-v1"},
        "datasets": {"arm": "earnings22-native-window-dev10-v1", "smoke": "e22-native-window-four-row-v1"},
        "model_fragment": "q4km-e22-native-window-packets-cddb000c-np4-max1024-v1",
        "inventory_receipt": "docs/readiness/2026-10-11-earnings22-module-alloff-v1/window-inventory-receipt-v1.json",
        "no_lock": "Earnings-22 has no locked system and no direct parent cell: the shared direct layer e22-native-window-direct-base-v1 (the phase-direct-only-v1 program and its one phase_material.direct entry, the generic transcription instruction bytes shared with E21) is the whole comparator, so the module's all-off arm is that base fragment plus the E21-shaped native-window geometry and pins on the Earnings-22 dev split. No knowledge supply, no ConEC layer, no entity scorer, no analytical tool.",
        "own_null": "Earnings-22 has NO measured own null on this form (no cell has ever flown on the native-window dev form); the module null is unmeasured until an in-chain A/A of this arm seals (design 2b.3). The all-off arm is therefore a form proof only, and no benefit may be claimed on this carrier until that A/A exists.",
        "scorers": "asr-wer-whisper only (corpus-level Whisper English-normalizer WER, the paper-facing metric; no ConEC, entity or numeric layer exists for Earnings-22). Scorer variant: the PLAIN window-form scorer, NOT the ESB short-form tail-2 s variant of docs/readiness/2026-09-05-scoring-alignment-conclusions.md (15.937 sealed vs 9.2377 under the 2.0 s digital-silence tail, deviation D-TS2-3): this cell appends no tail silence, reads whole 90 s windows of whole dev calls rather than ESB test utterances, and so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band is claimed",
        "model_tool": "Frozen Q4_K_M decoder-only (q4km-e22-native-window-packets-cddb000c-np4-max1024-v1): c98304 np4 max1024, no mmproj; Earnings-22 dev speech-feature packets NOT YET PRODUCED (they need an encoder pass); NO native tool authority; the direct-only program (one contact per window) compiled by the consumption module from its all-off block (profile earnings22)",
        "carrier_line": "earnings22-original dev {rows}",
        "chain": {"rows": 10, "cpr": 45, "ceil": 400, "smoke_rows": 1},
        "inherited": "Every call already exposed to the Qwen3-Omni core in earlier Earnings-22 dev work (R0 smoke, the BENCH e22cold / e22-b90 subset10 runs and the ESB dev prompt A/B and shape-C cells on the same ten calls); the 451 windows themselves were cut model-free on 2026-10-11 and have never met an encoder or the core. No new speech identity and no new split. Prior exposure is inherited in full.",
    },
}

E22_README_EXTRA = """
## Earnings-22 specifics (read before reopening this carrier)

**Model-free work done.** The 10-call dev window inventory (451 fixed 90-second windows, 40,055.9 decoded seconds) and
the four-row subset batch (call 4453225, windows w0001-w0004) were built CPU-only on 2026-10-11 through the shared
`prepare-window-inventory` path, with the Earnings-21 protocol, into the data root (write-once). Counts, hashes and the
exact command are in `window-inventory-receipt-v1.json` (this directory); nothing else about the audio is recorded.
Both cells pin them; `FlightRuntime` verifies the pins down to slice bytes (4 and 451 execution units load).

**Where the first contact-requiring step sits.** `core.flight.cli check` and a Python-API wire check reach the
execution-unit roster (verified), then refuse at `core.driver.run.load_window_packet_binding`: the Earnings-22 window feature
packets (`analysis/SAEA-E22-DEV-WINDOW-GPU-ENCODING-V1/window-feature-packets.json`, and the four-row twin) do not exist.
Producing them is an encoder forward pass (root lease, GPU, registration, owner authorization); both baselines carry an
all-zero PENDING sha256 for that pin, so the composed hashes change when the real pin lands. Behind that step the runtime requires a validated non-empty knowledge snapshot for every phase-program contact, and
Earnings-22 has no governed knowledge, so both baselines pin an INERT placeholder snapshot (one facet, one value, bound to no
dataset sample; `scripts/build_e22_inert_knowledge_snapshot.py`, asset `knowledge/e22/inert/all-off-placeholder-v1/snapshot.json`
under the data root, sha256 `19c61475ef1d6a641cd5ec182479285b6bb6af2928cc17115bb01b3ef8633a31`), the same way the Earnings-21 and Audio2Tool cells pin theirs. The direct
phase declares `knowledge: "none"`, so the placeholder is bound invisibly and supplies nothing.

**Shared-code change this registration needed.** The four-row smoke is a one-call subset of the dev split, which the
Earnings runtime adapter admitted only for Earnings-21 discovery. Commit `8383e68f1` takes the parent split and carrier
from `DEFAULT_SPLIT` / `CARRIER_LOCK_KEY` (Earnings-21 messages and behaviour byte-identical) and drops the Earnings-22
refusal; the smoke dataset fragment therefore carries the adapter's own `e21_runtime_subset` key. Drop that commit and
the smoke cell becomes unrunnable (the arm is unaffected).

**Scorer variant (declared in each baseline's `what_this_is`).** `asr-wer-whisper` only, corpus-level WER under the Whisper
English normalizer, on the PLAIN window form. It is NOT the ESB short-form tail-2 s variant (15.937 sealed, NOT ALIGNED, vs
9.2377 ALIGNED with 2.0 s of digital silence appended, deviation D-TS2-3): this cell appends no silence and reads whole dev
calls in 90 s windows, not ESB test utterances, so none of 15.937 / 9.2377 / 9.79 / 12.3 is a comparator and no alignment band
is claimed. An ESB-comparable Earnings-22 number needs the existing short-form tail-2 s dataset fragments, a different form.

**Other facts.** `earnings22-dev-subset10` has no `split_id`, which the flight runtime requires, so the arm uses the new
`earnings22-native-window-dev10-v1`. The serving session name is NEW (its feature root differs from the resident E21
session); its launch entry is a root item. The inventory plan label `split_role: discovery` (copied from the E21 inventory
fragment) is a label only; the cells declare `dev`. No in-chain A/A exists, so no benefit may be claimed on this carrier.
"""


STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the evidence-consumption module "
    "with every component off on a carrier with no locked system -- the carrier's direct baseline expressed as a "
    "module block, the carrier admission gate of the consumption-module design (section 2b.3). No rollout, no "
    "per-sample scoring, no credit assignment, no update operator, no evolving store and no mechanism."
)


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    target = REPO_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def ledger_row(cells: list[str]) -> str:
    return "| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |"


def identities(spec: dict) -> dict:
    out = {}
    for key, cell in spec["cells"].items():
        suffix = "" if key == "arm" else "-SMOKE-4"
        run = f"{spec['run_stem']}{suffix}-V1"
        out[key] = {
            "cell": cell, "run_id": run, "attempt_id": f"attempt-{cell}-generation-v1",
            "fit_run_id": f"{spec['run_stem']}{suffix}-FIT-V1" if spec["live_fit"] else None,
            "fit_attempt_id": f"attempt-{cell}-fit-v1" if spec["live_fit"] else None,
        }
    return out


def family_budget(spec: dict, key: str, rows: int, audio_seconds: float) -> dict:
    b = spec["budget"][key]
    return {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": FIT_ENDPOINTS(rows) if spec["live_fit"] else 0,
        "generation_calls_cap": b["calls"], "gpu_hours_fit_inclusive": b["gpu"],
        "native_task_contract_calls_cap": 0, "official_complete_scoring_jobs": b["scoring"],
        "repeated_speech_audio_seconds_cap": b["audio"] if b["audio"] is not None else math.ceil(audio_seconds),
    }


def derive_a2t(spec: dict, ids: dict, block: dict, measurement: dict, package: str) -> dict:
    written = {}
    for key in ("arm", "smoke"):
        parent_doc = json.loads(rd(f"configs/experiment/{spec['parents'][key]}.json"))
        parent_cell = parent_doc["cells"][0]
        baseline = json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json"))
        rows = int(parent_doc["population"]["count"])
        baseline["live_phase_fit"] = {"attempt_id": ids[key]["fit_attempt_id"], "contact_cap": FIT_ENDPOINTS(rows),
                                      "run_id": ids[key]["fit_run_id"]}
        baseline["what_this_is"] = (
            "Consumption-module all-off arm on Audio2Tool (" + ("four-row form smoke" if key == "smoke" else "the paired 400")
            + "): the module saea-evidence-consumption-module-v1 with every component off, profile audio2tool, which "
            "compiles to the carrier's DIRECT layer -- the direct-only phase program of the shared controller, "
            "byte-for-byte the sealed direct a2t-native-role-direct-union4000-v1 and the A2T-AA passes in every "
            "request-shaping field -- re-declared under its own live phase-fit identity. No knowledge supply, no "
            "analytical tools, no native tool authority, no mechanism; a form proof of the carrier admission gate."
        )
        baseline_name = ids[key]["cell"][: -len("-v1")] + "-baseline-v1"
        written[f"configs/baseline/{baseline_name}.json"] = wr(
            f"configs/baseline/{baseline_name}.json", json.dumps(baseline, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        document = json.loads(json.dumps(parent_doc))
        document.pop("own_null_pair", None)
        cell = document["cells"][0]
        cell.update({"cell_id": ids[key]["cell"], "run_id": ids[key]["run_id"], "attempt_id": ids[key]["attempt_id"],
                     "baseline_fragment": baseline_name})
        seconds = document.get("execution_plan", {}).get("planned_speech_audio_seconds", 0)
        document["family_budget"] = family_budget(spec, key, rows, seconds)
        document["execution_plan"]["planned_gpu_hours"] = spec["budget"][key]["gpu"]
        document["generation_budget"] = {
            "cap": document["family_budget"]["generation_calls_cap"], "target": document["family_budget"]["generation_calls_cap"],
            "definition": f"The direct-only phase program makes exactly one contact per row: {rows} x 1 = {rows}; the live phase fit makes 1 + (2 + 1) x {rows} = {FIT_ENDPOINTS(rows)} tokenizer endpoint calls under {ids[key]['fit_run_id']}. Ceilings, not targets; run-cumulative across attempts.",
        }
        written.update(_finish_experiment(spec, key, ids, document, block, measurement, package))
    return written


def derive_e21(spec: dict, ids: dict, block: dict, measurement: dict, package: str) -> dict:
    written = {}
    for key in ("arm", "smoke"):
        parent_doc = json.loads(rd(f"configs/experiment/{spec['parents'][key]}.json"))
        parent_cell = next(c for c in parent_doc["cells"] if c["cell_id"] == spec["parent_cells"][key])
        population = dict(parent_doc["population"])
        document = {
            "cells": [{
                "allowed_execution_stages": ["check", "worker", "campaign"],
                "attempt_id": ids[key]["attempt_id"], "baseline_fragment": parent_cell["baseline_fragment"],
                "cell_id": ids[key]["cell"], "dataset_fragment": parent_cell["dataset_fragment"],
                "model_fragment": parent_cell["model_fragment"], "run_id": ids[key]["run_id"],
            }],
            "execution_plan": {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": spec["budget"][key]["gpu"],
                               "planned_model_calls": spec["budget"][key]["calls"],
                               "planned_speech_audio_seconds": spec["budget"][key]["audio"], "split_role": spec.get("split_role", "discovery")},
            "execution_profile": "bounded-discovery-probe",
            "population": population,
        }
        document["family_budget"] = family_budget(spec, key, int(population.get("execution_units", 0)), spec["budget"][key]["audio"])
        document["generation_budget"] = {
            "cap": spec["budget"][key]["calls"], "target": spec["budget"][key]["calls"], "ceilings_are_not_targets": True,
            "definition": f"The direct-only phase program makes exactly one contact per native window: {spec['budget'][key]['calls']} windows x 1. No fit identity (the direct baseline declares none, as the flown E35 direct arms). Ceilings, not targets; run-cumulative across attempts.",
        }
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, prompt, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation "
            "attempt id); a second failure closes the cell and the fix is proven on a four-row dry run. A partial "
            "manifest is never scored and never read.")
        written.update(_finish_experiment(spec, key, ids, document, block, measurement, package))
    return written


DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
#: A pin whose artifact does not exist yet (the Earnings-22 window feature packets need an encoder pass): an all-zero
#: SHA-256 can never match a real file, so a runtime that reaches it refuses at "file missing" -- the first
#: contact-requiring step -- and the package carries the placeholder as a named pending pin.
PENDING_SHA256 = "0" * 64
#: The inert one-facet placeholder snapshot (scripts/build_e22_inert_knowledge_snapshot.py): the runner needs a non-empty
#: snapshot for every phase-program contact and Earnings-22 has no governed knowledge.
INERT_SNAPSHOT_RELPATH = "knowledge/e22/inert/all-off-placeholder-v1/snapshot.json"
INERT_SNAPSHOT_SHA256 = "19c61475ef1d6a641cd5ec182479285b6bb6af2928cc17115bb01b3ef8633a31"


def e22_receipt(spec: dict) -> dict:
    return json.loads(rd(spec["inventory_receipt"]))


def e22_rows(spec: dict) -> dict:
    receipt = e22_receipt(spec)
    return {"arm": int(receipt["inventory"]["request_count"]), "smoke": int(receipt["four_row"]["unit_count"])}


def derive_e22(spec: dict, ids: dict, block: dict, measurement: dict, package: str) -> dict:
    """Write the two baseline fragments, the smoke dataset fragment, the two experiment fragments and the campaign plans
    of the Earnings-22 all-off cells from the model-free window-inventory receipt (no parent cell exists to copy)."""

    from speech_aware_evidence_acquisition.reproduction.probe_split import load_verified_probe_split  # noqa: PLC0415

    receipt = e22_receipt(spec)
    base = json.loads(rd(f"configs/baseline/{spec['lock_fragment']}.json"))
    e21_direct = json.loads(rd("configs/baseline/e21-native-window-direct-full44-v1.json"))
    inventory, four = receipt["inventory"], receipt["four_row"]
    smoke_split = load_verified_probe_split(REPO_ROOT, "e22-native-window-four-row-v1")
    probe = json.loads(rd("docs/receipts/probe-samples/e22-native-window-four-row-v1.json"))
    if probe["split_identity_hash"] != four["split_identity_hash"]:
        raise SystemExit("the four-row receipt split hash differs from the probe-sample receipt")
    written: dict = {}
    pins = {
        "arm": {
            "units": {"batch": inventory["batch"], "registry_run_id": inventory["run_id"], "relpath": inventory["relpath"],
                      "sha256": inventory["file_sha256"], "split_identity_hash": receipt["split_identity_hash"],
                      "unit_count": inventory["request_count"]},
            "packets": f"{DATA_ROOT}/analysis/SAEA-E22-DEV-WINDOW-GPU-ENCODING-V1/window-feature-packets.json",
        },
        "smoke": {
            "units": {"batch": four["batch"], "registry_run_id": four["registry_run_id"], "relpath": four["relpath"],
                      "sha256": four["file_sha256"], "split_identity_hash": smoke_split.identity_hash,
                      "unit_count": four["unit_count"]},
            "packets": f"{DATA_ROOT}/analysis/SAEA-E22-NATIVE-WINDOW-FOUR-ROW-V1/window-feature-packets.json",
        },
    }
    for key in ("arm", "smoke"):
        form = ("the four-row form smoke (the first four windows of call 4453225)" if key == "smoke"
                else "the whole 10-call dev split (451 windows)")
        baseline = {
            "arm": "speech-feature-query", "evidence_mismatch": False, "evidence_source": "none",
            "ojw_workflow_timeout_seconds": e21_direct["ojw_workflow_timeout_seconds"],
            "phase_material": base["phase_material"], "policy": base["policy"],
            "prepared_execution_units": pins[key]["units"],
            "prepared_window_feature_packets": {"path": pins[key]["packets"], "sha256": PENDING_SHA256},
            "knowledge_snapshot_relpath": INERT_SNAPSHOT_RELPATH, "knowledge_snapshot_sha256": INERT_SNAPSHOT_SHA256,
            "prompt_fit_multiple": e21_direct["prompt_fit_multiple"], "scorers": ["asr-wer-whisper"],
            "serving_slot_tokens": e21_direct["serving_slot_tokens"], "serving_slots": e21_direct["serving_slots"],
            "speech_feature_key_representation_id": "saea-e22-native-window-v1:current-window",
            "speech_feature_matcher_policy_id": "saea-e22-native-window-v1",
            "task_contract_source": e21_direct["task_contract_source"], "task_instruction": e21_direct["task_instruction"],
            "what_this_is": (
                "HELD pure frozen-core comparator of the Earnings-22 consumption-module all-off arm on " + form + ", through the "
                "same source-unit, shared controller / OpenJiuwen, delivery and scoring path the Earnings-21 native-window direct "
                "cells use. One direct contact per 90 s window; no facets, values, supply route, knowledge supply or tool. "
                "SCORER VARIANT (declared): asr-wer-whisper only -- corpus-level WER under the Whisper English normalizer, the "
                "paper-facing metric -- on the PLAIN window form. It is NOT the ESB short-form tail-2 s variant "
                "(docs/readiness/2026-09-05-scoring-alignment-conclusions.md: 15.937 NOT ALIGNED sealed vs 9.2377 ALIGNED with "
                "2.0 s of digital silence appended, deviation D-TS2-3): this cell appends no silence, its population is whole "
                "dev calls in 90 s windows rather than ESB test utterances, and so neither number, nor the published 9.79 / 12.3, "
                "is a comparator; D-TS2-3 does not apply and no alignment band is claimed. The prepared_window_feature_packets "
                "sha256 is an all-zero PENDING pin: the Earnings-22 dev packets need an encoder pass (lease, GPU) that this "
                "registration neither performs nor authorizes."),
        }
        name = spec["baselines"][key]
        written[f"configs/baseline/{name}.json"] = wjson(f"configs/baseline/{name}.json", baseline)
    smoke_dataset = {
        "carrier_lock_key": spec["carrier_lock_key"], "split_id": "e22-native-window-four-row-v1",
        "split_name": "e22-native-window-four-row-v1",
        "e21_runtime_subset": {"receipt_split_name": "e22-native-window-four-row-v1", "parent_split": "dev", "subset_role": "construction"},
        "dataset_note": ("The key name e21_runtime_subset is the shared Earnings runtime adapter's own (one subset form for both Earnings carriers). "
                         "One already-dev call (4453225, the first dev call in inventory order; docs/receipts/probe-samples/e22-native-window-four-row-v1.json), "
                         "re-bound to the native-window execution-unit mechanism: its first four windows of the shared Earnings-22 dev window inventory, "
                         "contiguous from w0001. No new sample authority: it names no id the dev split does not already contain."),
    }
    written["configs/dataset/e22-native-window-four-row-v1.json"] = wjson("configs/dataset/e22-native-window-four-row-v1.json", smoke_dataset)
    # earnings22-dev-subset10 carries no split_id, which the flight runtime requires of every cell's dataset fragment;
    # this is its native-window twin (the shape of earnings21-native-window-full44-v1, without a names supplement).
    arm_dataset = {
        "carrier_lock_key": spec["carrier_lock_key"], "split_id": "dev", "split_name": "dev",
        "dataset_note": ("The whole Earnings-22 dev split (the 10 calls of earnings22-dev-subset10) with an explicit shared phase-runtime split ID. "
                         "Both direct and any later agent arm use this identical dataset declaration. No names supplement exists or is needed: "
                         "Earnings-22 has no ConEC layer."),
    }
    written["configs/dataset/earnings22-native-window-dev10-v1.json"] = wjson("configs/dataset/earnings22-native-window-dev10-v1.json", arm_dataset)
    for key in ("arm", "smoke"):
        units = pins[key]["units"]["unit_count"]
        document = {
            "cells": [{
                "allowed_execution_stages": ["check", "worker", "campaign"],
                "attempt_id": ids[key]["attempt_id"], "baseline_fragment": spec["baselines"][key],
                "cell_id": ids[key]["cell"], "dataset_fragment": spec["datasets"][key],
                "model_fragment": spec["model_fragment"], "run_id": ids[key]["run_id"],
            }],
            "execution_plan": {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": spec["budget"][key]["gpu"],
                               "planned_model_calls": spec["budget"][key]["calls"],
                               "planned_speech_audio_seconds": spec["budget"][key]["audio"], "split_role": spec["split_role"]},
            "execution_profile": "bounded-discovery-probe",
            "population": {
                "carrier": spec["carrier_lock_key"], "count": 10 if key == "arm" else 1, "dataset_fragment": spec["datasets"][key],
                "execution_units": units, "historically_exposed": True,
                "split_identity_hash": pins[key]["units"]["split_identity_hash"],
                **({"roster_receipt": "docs/receipts/probe-samples/e22-native-window-four-row-v1.json"} if key == "smoke" else {}),
            },
        }
        document["family_budget"] = family_budget(spec, key, units, spec["budget"][key]["audio"])
        document["generation_budget"] = {
            "cap": spec["budget"][key]["calls"], "target": spec["budget"][key]["calls"], "ceilings_are_not_targets": True,
            "definition": f"The direct-only phase program makes exactly one contact per native window: {spec['budget'][key]['calls']} windows x 1. No fit identity (the direct baseline declares none, as the flown E35 direct arms). Ceilings, not targets; run-cumulative across attempts.",
        }
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, prompt, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation "
            "attempt id); a second failure closes the cell and the fix is proven on a four-row dry run. A partial "
            "manifest is never scored and never read.")
        written.update(_finish_experiment(spec, key, ids, document, block, measurement, package))
    return written


def _finish_experiment(spec, key, ids, document, block, measurement, package) -> dict:
    cell = document["cells"][0]
    cell["readiness"] = {
        "reason": (
            f"Consumption-module all-off arm on {spec['profile']} (owner decision 196, direction 205; design 2b.3 carrier "
            f"admission gate), registered before contact on {spec.get('date', DATE)} by scripts/flights/module/"
            "register_carrier_module_alloff_cells.py. HELD: decision 187 keeps the GPU on SLURP until the SLURP lock; "
            f"nothing flies before the owner reopens this carrier and root mints coordination/{spec['stem']}/"
            "root-admission-v1.json. The flip is scripts/flights/module/module_alloff_" + spec["at"] + "_flip.sh. "
            "The program declares no supplied first phase, so the re-pin creates no prepared artifact; "
            "--allow-output-change is never passed. Nothing here authorises a flight, a readiness flip or an admission entry."),
        "requirements": [], "state": "held",
    }
    document["date"] = spec.get("date", DATE)
    document["experiment_id"] = ids[key]["run_id"]
    document["fragment_kind"] = f"saea-{spec['stem']}"
    document["purpose"] = (
        ("Four-row form smoke of " if key == "smoke" else "")
        + f"the evidence-consumption module's ALL-OFF arm on {spec['profile']}: every component off, which compiles to the "
        "carrier's DIRECT layer. " + spec["no_lock"] + " It is the carrier admission gate of design section 2b.3: the "
        "module-bare arm on the carrier's own roster before any component is turned on there. Own null: " + spec["own_null"]
        + " A FORM proof: it claims no benefit, admits nothing and compares no mechanism; no component-on cell exists "
        "for this carrier. Development numbers only (owner decisions 28 and 86).")
    document["consumption_module_declaration"] = {
        "block": block,
        "compiles_to": f"the {spec['profile']} direct layer = configs/baseline/{spec['lock_fragment']}.json policy blocks",
        "why_not_native_episode": "A direct program carries no native_episode block (the native-episode loader refuses one on any program that is not the native-role episode), so the declaration lives here and is proven by the byte proof rather than verified by the loader.",
        "proof": f"python -B scripts/analysis/module_equivalence_proof.py --at {spec['at']}",
    }
    document["stage3_algorithm"] = {"id": "none", "note": STAGE3_ALGORITHM_NOTE, "operators_used": []}
    document["stage3_measurement"] = measurement[ids[key]["run_id"]]
    if spec["live_fit"]:
        document["service_session"] = spec["session"]
    path = f"configs/experiment/{ids[key]['cell']}.json"
    out = {path: wjson(path, document)}
    # The A2T smoke flies through the driver's smoke slot; the E21 smoke is its own cell step (the E35 form).
    if key == "arm" or not spec["live_fit"]:
        plan = f"configs/campaign/{ids[key]['cell']}.json"
        out[plan] = wjson(plan, {"cells": [{"cell": ids[key]["cell"], "experiment": ids[key]["cell"]}],
                                 "schema": "saea-campaign-plan-v1"})
    return out


def measurement_blocks(spec: dict, ids: dict, rows: dict) -> dict:
    out = {}
    for key in ("arm", "smoke"):
        out[ids[key]["run_id"]] = {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "rows": rows[key], "claims_benefit": False,
            "primary_metric": spec["scorers"], "tuning_roster": "none", "read_roster": spec["roster"],
            "note": ("Form proof of the consumption module's carrier admission gate (design 2b.3): the all-off arm is the "
                     "carrier's direct baseline bytes; nothing is expected to move and no benefit is claimed."),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--carrier", choices=sorted(CARRIERS), required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-carrierhooks")
    parser.add_argument("--branch", default="fable/carrierhooks")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    spec = CARRIERS[args.carrier]
    ids = identities(spec)
    block = proof.alloff_block(spec["profile"])
    package = f"docs/readiness/{spec.get('date', DATE)}-{spec.get('package_stem', spec['stem'])}"
    prereg = package + "-preregistration.md"
    read_run = f"{spec['run_stem']}-FORM-READ-V1"
    decision_id = f"{spec['stem']}-admission-v1"
    decision_relpath = f"coordination/{spec['stem']}/root-admission-v1.json"

    rows = {}
    if args.carrier == "e22":
        rows = e22_rows(spec)
    else:
        for key in ("arm", "smoke"):
            parent_doc = json.loads(rd(f"configs/experiment/{spec['parents'][key]}.json"))
            rows[key] = int(parent_doc["population"].get("execution_units") or parent_doc["population"]["count"])
    measurement = measurement_blocks(spec, ids, rows)
    derive = {"a2t": derive_a2t, "e21": derive_e21, "e22": derive_e22}[args.carrier]
    written = derive(spec, ids, block, measurement, package)

    byte_proof = proof.run_case(spec["at"], REPO_ROOT)
    if not byte_proof["ok"]:
        print(json.dumps(byte_proof, indent=2, sort_keys=True))
        raise SystemExit(f"the {spec['at']} byte proof failed; nothing registered beyond the configs above")

    cells = {}
    for key in ("arm", "smoke"):
        document = json.loads(rd(f"configs/experiment/{ids[key]['cell']}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], ids[key]["cell"])
        split = document["population"]["split_identity_hash"]
        cells[key] = {
            **ids[key], "experiment": ids[key]["cell"], "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "policy": composed.values["policy"], "arm": composed.values["arm"], "rows": rows[key],
            "split_identity_hash": split, "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "family_budget": document["family_budget"], "scorers": composed.values.get("scorers"),
        }

    hooks = cm.resolve_carrier_hooks(spec["profile"])
    hook_table = {name: ("None" if getattr(hooks, name) is None else "implemented")
                  for name in cm.CarrierHooks.__dataclass_fields__}
    facts = {
        "_note": "Every model-free fact this registration rests on, and the CANONICAL stage3_measurement mapping (run id -> block) scripts/checks/stage3_effect_floor_check.py resolves; this copy has precedence over the preregistration's fence.",
        "authority_relpaths": [DESIGN, OWNER_DECISIONS, INSTRUMENT, f"configs/baseline/{spec['lock_fragment']}.json",
                               f"src/speech_aware_evidence_acquisition/rails/adapters/{spec['profile']}_module_hooks.py"],
        "carrier_hooks": {"profile": spec["profile"], "members": hook_table,
                          "carrier_components": json.loads(json.dumps(hooks.carrier_components or {}))},
        "cells": cells, "consumption_module_block": block,
        "module_byte_proof": {"command": f"python -B scripts/analysis/module_equivalence_proof.py --at {spec['at']}",
                              "ok": byte_proof["ok"], "results": byte_proof["results"]},
        "no_lock": spec["no_lock"], "own_null": spec["own_null"], "read_run_id": read_run,
        "stage3_measurement": measurement,
        "not_registered": "No component-on cell for this carrier (decision 187 keeps the GPU on SLURP; a component turns on per carrier only through its own read, design 2b.3 item 4).",
    }
    if spec.get("inventory_receipt"):
        facts["window_inventory_receipt"] = {"path": spec["inventory_receipt"], "sha256": hashlib.sha256(rd(spec["inventory_receipt"]).encode("utf-8")).hexdigest()}
        facts["pending_pins"] = {
            "prepared_window_feature_packets": ("all-zero sha256 placeholder in both baseline fragments: the Earnings-22 dev window feature "
                                                "packets do not exist; they need an encoder pass (root lease, GPU, registration, owner authorization). "
                                                "Producing them changes both composed config hashes, so root re-runs this script (or the repin tool) afterwards."),
            "knowledge_snapshot": "inert placeholder snapshot (one facet, one value, bound to no sample) pinned in both baselines; bound invisibly by the knowledge-none direct phase",
            "serving_session": f"{spec['session']} is a NEW session name: its feature root differs from the resident E21 session, so no resident session serves it",
        }
    facts_sha = wjson(f"{package}/registered-facts-v1.json", facts)
    protocol = {
        "authority": f"{DESIGN} sections 2b and 3.2; {OWNER_DECISIONS} rows 187, 196; {INSTRUMENT} rule 5 (a form proof claims no benefit)",
        "cells": cells, "consumption_module_block": block, "decision_id": decision_id, "decision_relpath": decision_relpath,
        "one_factor": "None: the all-off arm is the carrier's direct baseline bytes; between it and its direct parent cell only fit identity, prose and the experiment fragment's own block differ, none of which enters a request (the byte proof).",
        "read_run_id": read_run, "schema": "saea-registered-protocol-v1", "service_session": spec["session"],
    }
    protocol_sha = wjson(f"{package}/protocol-registered-v1.json", protocol)
    plan_shas = {}
    for key in ("arm", "smoke"):
        c = cells[key]
        prefix = "" if key == "arm" else "smoke-"
        base = {
            "cell": c["cell"], "composed_config_hash": c["composed_config_hash"], "experiment": c["experiment"],
            "expected_session_id": spec["session"], "family_budget": c["family_budget"],
            "preparation_base_commit": args.study_commit[:9],
            "protocol_document": {"relpath": f"{package}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": args.registered_at,
            "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
            "unused_budget_is_not_attempt_authority": True,
        }
        generation = {**base, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
                      "execution_plan": {"attempt_id": c["attempt_id"], "carrier_lock_key": spec["carrier_lock_key"],
                                         "execution_profile": "bounded-discovery-probe",
                                         "planned_gpu_hours": c["family_budget"]["gpu_hours_fit_inclusive"],
                                         "planned_model_calls": c["family_budget"]["generation_calls_cap"],
                                         "planned_speech_audio_seconds": c["family_budget"]["repeated_speech_audio_seconds_cap"],
                                         "protocol_hash": c["protocol_hash"], "run_id": c["run_id"], "schema": "saea-execution-plan-v1",
                                         "split_identity_hash": c["split_identity_hash"], "split_role": spec.get("split_role", "discovery"),
                                         "study": "speech-aware-evidence-acquisition"},
                      "purpose": f"{c['run_id']}: the consumption module's all-off arm on {spec['profile']} ({key}); a form proof, no benefit claimed.",
                      "scoring": "One complete official score after a successful seal; no partial score." if key == "arm" else "No score (form smoke)."}
        plan_shas[f"{prefix}generation-plan-registered-v1.json"] = wjson(f"{package}/{prefix}generation-plan-registered-v1.json", generation)
        if spec["live_fit"]:
            fit = {**base, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1", "attached_generation_run_id": c["run_id"],
                   "contact_cap": c["family_budget"]["fit_endpoint_calls_cap"], "max_speech_packets": 1,
                   "execution_plan": {**generation["execution_plan"], "attempt_id": c["fit_attempt_id"], "run_id": c["fit_run_id"],
                                      "planned_model_calls": c["family_budget"]["fit_endpoint_calls_cap"]},
                   "purpose": f"{c['fit_run_id']}: the live phase-fit spend identity of {c['run_id']}; request envelopes only.",
                   "scoring": "No fit score."}
            plan_shas[f"{prefix}fit-plan-registered-v1.json"] = wjson(f"{package}/{prefix}fit-plan-registered-v1.json", fit)
    recipe = {
        "recipe_id": f"{spec['stem']}-form-read-v1", "read_run_id": read_run, "schema": "saea-analysis-recipe-v1",
        "arms": {"arm": {"run_id": cells["arm"]["run_id"], "attempt_id": cells["arm"]["attempt_id"],
                         "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
                 "direct_parent": {"experiment": spec["parents"]["arm"] or spec["lock_fragment"], "role": "the direct cell (or, for a carrier with no direct cell, the shared direct base fragment) whose bytes the all-off arm carries; context only"}},
        "design": "DESCRIPTIVE form read: request identity against the direct parent's registered bytes, row completeness, the official scorer(s) reported beside, contacts per minute; no verdict, no benefit, no admission.",
        "scorers": spec["scorers"], "own_null": spec["own_null"],
        "boundary": "Development numbers only (owner decisions 28 and 86). No utterance text, transcript, gold label or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(f"{package}/analysis-recipe-v1.json", recipe)
    eligible = [cells[k][f] for k in ("arm", "smoke") for f in ("run_id", "fit_run_id") if cells[k][f]]
    draft = {
        "_draft_note": f"A DRAFT for root to mint on the data root with scripts/flights/module/module_alloff_mint_receipt.py --carrier {args.carrier}; it authorises nothing while its status is not 'decided'.",
        "antecedents": {"registered_facts": {"path": f"{package}/registered-facts-v1.json", "sha256": facts_sha},
                        "protocol": {"path": f"{package}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "analysis_recipe": {"path": f"{package}/analysis-recipe-v1.json", "sha256": recipe_sha},
                        "preregistration": {"path": prereg, "sha256": None},
                        "design": {"path": DESIGN, "sha256": None},
                        "registration_base_commit": args.study_commit[:9]},
        "authorization_basis": "Owner decision 196 and direction 205; decision 187 (the GPU stays on SLURP until the owner reopens this carrier).",
        "budget": {**cells["arm"]["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "smoke": cells["smoke"]["family_budget"]},
        "cell_kind": f"Consumption-module all-off arm (carrier admission gate) on {spec['profile']}: the direct baseline as a module block; a form proof.",
        "claim_boundary": "No benefit, superiority, generalisation or component claim; claims_benefit false.",
        "decision": "Fly only after the owner reopens this carrier (decision 187) and the coordinator decides the byte proof is not enough.",
        "decision_id": decision_id, "eligible_run_ids": eligible, "status": "draft",
        "not_authorized": ["any flight before decision 187 is lifted for this carrier, the receipt is minted and the cells are flipped",
                           "any component-on cell on this carrier", "any ASR, transcript, encoder or paid-API contact"],
    }
    draft_sha = wjson(f"{package}/root-admission-draft-v1.json", draft)
    proof_rows = "\n".join(
        f"| {r.get('cell', r.get('target'))} | `{r.get('experiment', r.get('fragment'))}` | "
        f"{r.get('composed_identical', '--')} | {r.get('differing_policy_paths')} | "
        f"{(r.get('composed_config_diff_vs_parent') or {}).get('policy', '--')} | "
        f"{(r.get('composed_config_diff_vs_parent') or {}).get('bookkeeping', '--')} | {r['ok']} |"
        for r in byte_proof["results"])
    none_members = ", ".join(sorted(n for n, v in hook_table.items() if v == "None"))
    readme = f"""# Consumption-module all-off arm on {spec['profile']} (carrier admission gate, HELD)

Registered before contact {spec.get("date", DATE)} at study commit `{args.study_commit[:9]}` (branch `{args.branch}`) by
`scripts/flights/module/register_carrier_module_alloff_cells.py --carrier {args.carrier}`; owner decision 196, direction
205; design `{DESIGN}` sections 2b.3 and 3.2. **HELD**: decision 187 keeps the GPU on SLURP until the SLURP lock. Nothing
here authorises a flight, a flip or an admission entry.

**What it is.** The evidence-consumption module `saea-evidence-consumption-module-v1`, profile `{spec['profile']}`, with
every component off. {spec['no_lock']}

**Why.** Design 2b.3 item 3: a carrier admits the module only after its module-bare arm is flown as an A/A on the
carrier's own roster; its half-widths are that carrier's module null. Own null: {spec['own_null']}

**The byte proof** (`python -B scripts/analysis/module_equivalence_proof.py --at {spec['at']}`): ok = {byte_proof['ok']}.

| cell | experiment / fragment | composed identical | policy leaves differing from own | policy leaves vs direct parent | bookkeeping vs direct parent | ok |
| --- | --- | --- | --- | --- | --- | --- |
{proof_rows}

**Cells.** arm `{cells['arm']['cell']}` (`{cells['arm']['run_id']}`, {rows['arm']} rows, composed `{cells['arm']['composed_config_hash'][:16]}...`);
smoke `{cells['smoke']['cell']}` (`{cells['smoke']['run_id']}`, {rows['smoke']} rows). Read row `{read_run}` (descriptive form read).
Carrier hooks with no analogue here (`None`, so the module refuses those components): {none_members}.

**Measurement.** `form-proof`, `claims_benefit: false`, expected effect 0.0 (instrument rule 5). Scorers: {spec['scorers']}.

**If the owner reopens this carrier.** (1) Root countersigns the DRAFT rows and mints `{decision_relpath}` with
`scripts/flights/module/module_alloff_mint_receipt.py --carrier {args.carrier}`. (2) `scripts/flights/module/module_alloff_{spec['at']}_flip.sh`
re-pins the smoke and the arm. (3) `scripts/flights/module/batch_chain_module_alloff_{spec['at']}.sh` queues them on
`{spec['session']}`. (4) `scripts/flights/module/module_alloff_{spec['at']}_read.sh` names the read.

**Not authorised.** No flight, no component-on cell on this carrier, no re-flight of any sealed cell, no test-split contact.
"""
    readme_sha = wr(f"{package}/README.md", readme + (E22_README_EXTRA if args.carrier == "e22" else ""))
    prereg_text = f"""# Preregistration: consumption-module all-off arm on {spec['profile']} ({spec.get('date', DATE)}, HELD)

Package `{package}/`. The all-off block of profile `{spec['profile']}` compiles to the carrier's direct layer; the cell is
a FORM proof of the carrier admission gate (design 2b.3). No benefit is claimed and no number from it admits anything.

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, sort_keys=True)}
```
"""
    prereg_sha = wr(prereg, prereg_text)

    appended = 0
    if args.append_ledger:
        ledger = rd(LEDGER)
        if read_run in ledger:
            raise SystemExit(f"{LEDGER} already carries {read_run}; refusing to append twice")
        common = (f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
                  f"{args.study_commit[:9]} by the consumption-module carrier transfer (worktree {args.worktree}, branch {args.branch}); "
                  "owner decision 196, direction 205. HELD under decision 187. This registration performs no contact and authorises none.")
        out = []
        for key in ("arm", "smoke"):
            c = cells[key]
            prefix = "" if key == "arm" else "smoke-"
            for fit_flag in ((False, True) if spec["live_fit"] else (False,)):
                run = c["fit_run_id"] if fit_flag else c["run_id"]
                calls = c["family_budget"]["fit_endpoint_calls_cap"] if fit_flag else c["family_budget"]["generation_calls_cap"]
                plan = f"{prefix}{'fit' if fit_flag else 'generation'}-plan-registered-v1.json"
                what = (f"The evidence-consumption module's all-off arm on {spec['profile']} -- the carrier admission gate (design 2b.3); the direct baseline's bytes as a module block"
                        + (" (four-row form smoke)" if key == "smoke" else "") + (" -- FIT spend identity, request envelopes only, no generation" if fit_flag else ""))
                notes = (f"{common} Plan SHA256 {plan_shas[plan]}; attempt {c['fit_attempt_id'] if fit_flag else c['attempt_id']}. Protocol hash {c['protocol_hash']}; "
                         f"composed config {c['composed_config_hash']}; expected session {spec['session']} (attach only). READINESS HELD: root mints {decision_relpath} "
                         f"(decision id {decision_id}); scripts/flights/module/module_alloff_{spec['at']}_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready; "
                         f"--allow-output-change must never be passed. Byte proof: module_equivalence_proof.py --at {spec['at']} ok. Measurement: form-proof, "
                         f"claims_benefit false. Read: {read_run}. Stop and preserve on the first failure; AT MOST ONE recovery re-registration.")
                out.append(ledger_row([args.registered_at, run, "bounded-discovery-probe", what, spec["model_tool"],
                                       spec["carrier_line"].format(rows=c["rows"]), spec.get("split_role", "discovery"), c["split_identity_hash"], "no", str(calls),
                                       str(c["family_budget"]["repeated_speech_audio_seconds_cap"]), str(c["family_budget"]["gpu_hours_fit_inclusive"]),
                                       spec["inherited"], f"{package}/{plan}", notes]))
        out.append(ledger_row([args.registered_at, read_run, "model-free-check",
                               f"The {spec['profile']} all-off arm's descriptive form read: request identity against the direct parent, completeness, official scorer(s) beside; no verdict.",
                               "No model, tokenizer, encoder or server contact: sealed manifests, per-sample official scores and receipts only.",
                               spec["carrier_line"].format(rows=cells["arm"]["rows"]), spec.get("split_role", "discovery"), cells["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
                               "Reads only sealed manifests of this package; no new audio, gold or reference exposure.", f"{package}/analysis-recipe-v1.json",
                               f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package so scripts/checks/flight_registration_check.py finds it; recipe {package}/analysis-recipe-v1.json. No utterance text, gold, transcript or model output is printed or persisted."]))
        if spec.get("inventory_receipt"):
            rec = e22_receipt(spec)
            inv = rec["inventory"]
            out.append(ledger_row([
                args.registered_at, inv["run_id"], "model-free-check",
                "Prepare the Earnings-22 dev (10 whole calls) fixed 90-second window roster once through the shared exact cutter: the execution-unit inventory the HELD Earnings-22 all-off cells pin, with the first-four-window subset batch " + rec["four_row"]["batch"],
                "Shared exact cutter and source inventory (FlightRuntime.prepare_window_inventory); 16 CPU workers; deterministic roster order; no encoder forward pass",
                spec["carrier_line"].format(rows=inv["request_count"]) + " windows", "dev (plan label discovery, as the E21 inventory fragment)",
                rec["split_identity_hash"], "yes", "0", "0", "0.0",
                "Source dev audio only; no model service, encoder, tokenizer, scorer, reference or transcript read; calls already exposed in earlier Earnings-22 dev work.",
                "configs/experiment/e22-dev-window-inventory-v1.json; " + rec["inventory"]["relpath"],
                f"EXECUTED MODEL-FREE (agent run, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit[:9]} (worktree {args.worktree}, branch {args.branch}). "
                f"Completed {inv['request_count']} unique windows from {inv['calls']} calls; decoded window audio {inv['window_audio_seconds_decoded']} seconds; inventory file SHA256 {inv['file_sha256']} (output_sha256 {inv['output_sha256']}); "
                f"four-row batch {rec['four_row']['batch']} file SHA256 {rec['four_row']['file_sha256']} (4 windows of call {rec['four_row']['sample_id']}, metadata re-partition, no audio read). "
                f"Receipt {package}/window-inventory-receipt-v1.json. Preserve the one source MP3 decoder warning; no neural or scorer contact."]))
        header = (f"\n## The consumption module's all-off arm on {spec['profile']} (carrier admission gate, design 2b.3; owner decision 196, direction 205) "
                  f"-- the arm, the four-row smoke{', their FIT identities' if spec['live_fit'] else ''}{', the model-free window-inventory row' if spec.get('inventory_receipt') else ''} and the READ row (DRAFT, root countersignature pending; HELD under decision 187)\n\n"
                  + ("Unconsumed rows registered with the package, except the model-free window-inventory row, which was executed (zero contacts). None is countersigned and none authorises a contact.\n\n"
                     if spec.get("inventory_receipt") else
                     "Unconsumed rows registered with the package. None is countersigned and none authorises a contact.\n\n")
                  + "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write(ledger.rstrip("\n") + "\n" + header + "\n".join(out) + "\n")
        appended = len(out)

    print(json.dumps({
        "carrier": args.carrier, "package": package, "byte_proof_ok": byte_proof["ok"],
        "written": {**written, f"{package}/README.md": readme_sha, f"{package}/registered-facts-v1.json": facts_sha,
                    f"{package}/protocol-registered-v1.json": protocol_sha, f"{package}/analysis-recipe-v1.json": recipe_sha,
                    f"{package}/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha,
                    **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {k: {f: cells[k][f] for f in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for k in cells},
        "ledger_rows_appended": appended,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
