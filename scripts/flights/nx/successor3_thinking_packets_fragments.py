#!/usr/bin/env python3
"""Write the config fragments of the successor-3 Thinking PACKETS pass and the DRAFT v2 allowance that would permit it (model-free, writes files only).

Modes::

    python -B scripts/flights/nx/successor3_thinking_packets_fragments.py write          # sidecar fragment, experiment fragment, DRAFT v2 allowance (idempotent)
    python -B scripts/flights/nx/successor3_thinking_packets_fragments.py pin-allowance  # after the owner signs v2: pin its sha256 into the experiment fragment

The signed successor-3 allowance (``docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json``) permits only the generation id and the FIT id,
so ``contracts.plan.require_owner_split_allowance`` refuses an encoder pass under any other run id. Coordinator ruling (decision 308 proposed): the signed bytes
are NOT edited; a DRAFT v2 receipt supersedes them by sha and adds the packets run id as a preparation id. The packets experiment fragment pins the v2 path with
64 zeros until the owner signs; while the pin is zero the driver (dry-run, ``--run``, ``--promote-only``) refuses. The guard is unmodified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import successor3_thinking_family as fam  # noqa: E402

ROOT = fam.REPO_ROOT
V2 = "docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2.json"
MODEL_SRC = "configs/model/q4km-thinking-feature-preprocess-gpu-np1-dev2000-added-v1.json"
MODEL_OUT = f"configs/model/{fam.PACKETS_SIDECAR_FRAGMENT}.json"
EXPERIMENT_OUT = f"configs/experiment/{fam.PACKETS_EXPERIMENT_FRAGMENT}.json"
DEV_CACHE = "/home/chao/feat-cache/slurp-thinking-gpu-q4km-dev2000-added"


def _dump(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _write(relpath: str, text: str) -> None:
    (ROOT / relpath).parent.mkdir(parents=True, exist_ok=True)
    with (ROOT / relpath).open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def model_fragment() -> dict:
    doc = json.loads((ROOT / MODEL_SRC).read_text(encoding="utf-8"))
    if doc["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] != DEV_CACHE:
        raise SystemExit("the DEV sidecar fragment's cache directory moved; refusing to derive")
    doc["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"] = fam.PACKETS_LEGACY_CACHE
    doc["preparation_basis"] = (
        "Successor 3 (owner ruling 301 A): the GPU encoder pass for the Thinking speech packets of the signed SLURP test SAMPLE (3,010 slurp:test: rows). "
        "Identical to q4km-thinking-feature-preprocess-gpu-np1-dev2000-added-v1 in every serving flag, the model pins and the runtime receipt; it differs ONLY in "
        "the legacy feature cache directory (its own, so no Fold B or DEV cache entry is a foreign entry for this roster). Offline, label-free packet "
        "preparation only: one-token responses are discarded unread, no answer is scored. The card holds one core: the chain is "
        "scripts/flights/direct/direct_fb_packets_gpu.sh --stage test-sample-3010 inside a serving-swap window.")
    return doc


def experiment_fragment(sha: str) -> dict:
    return {
        "execution_profile": "bounded-discovery-probe",
        "experiment_id": fam.PACKETS_RUN,
        "feature_root": fam.THINK_PACKET_ROOT,
        "legacy_cache_dir": fam.PACKETS_LEGACY_CACHE,
        "owner_allowance": {"path": V2, "sha256": sha},
        "preregistration": fam.PREREG,
        "promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
        "purpose": (
            f"Exposure row {fam.PACKETS_RUN} (package {fam.PACKAGE}): materialize the Thinking-core speech-feature packets for the 3,010 recordings of the signed SLURP "
            "test SAMPLE (SLURP-TEST-SAMPLE-3010-V1, 8,206.437 s) by one GPU encoder pass inside a serving-swap window: one contact per row at max_tokens 1 (the "
            "response is never read), then ADDITIVE promotion into the existing Thinking packet root under the new receipt TEST-SAMPLE-3010-promotion.json. The "
            "Instruct packets of these rows are not valid input to the Thinking decoder (the audio-encoder tensors differ). Label-free: no gold, transcript or model "
            f"output is opened. A final-report preparation: it is refused unless the pinned owner allowance ({V2}, a DRAFT until the owner signs decision 308) is "
            "authorised and lists this run id. Keep the Fold B and DEV Thinking packets and receipts untouched."),
    }


def v2_allowance() -> dict:
    signed = json.loads((ROOT / fam.ALLOWANCE).read_text(encoding="utf-8"))
    a = copy.deepcopy(signed)
    a["status"] = "draft-awaiting-owner-signature"
    a["date"] = "2026-10-14"
    a["permitted_run_ids"] = [fam.RUN, fam.FIT_RUN, fam.PACKETS_RUN]
    a["read_run_ids"] = [fam.RUN]
    a["preparation_run_ids"] = [fam.FIT_RUN, fam.PACKETS_RUN]
    a["supersedes"] = {"path": fam.ALLOWANCE, "sha256": fam.sha_file(fam.ALLOWANCE),
                       "scope": ("Adds ONE preparation run id (the Thinking packets encoder pass) and corrects the budgets to the Thinking ceilings. The signed bytes are preserved, "
                                 "not edited; every other term (one attempt per read id, aggregate-only, no smoke, no re-fly, lock arm only, comparator = the sealed successor-2 run) is unchanged.")}
    a["budgets"] = {
        "contacts_per_row": fam.CONTACTS_PER_ROW,
        "program_contacts_total": fam.program_calls(),
        "generation_cap_per_arm": fam.generation_calls(), "generation_cap_total": fam.generation_calls(),
        "fit_endpoint_cap_per_arm": fam.fit_contact_cap(), "fit_endpoint_cap_total": fam.fit_contact_cap(),
        "gpu_hour_cap_per_arm_fit_inclusive": fam.planned_gpu_hours(),
        "official_score_jobs_total": 1,
        "repeated_speech_audio_seconds_cap": fam.audio_cap(),
        "packets_pass": {"run_id": fam.PACKETS_RUN, "contacts": fam.PACKETS_ROW_CALLS, "speech_audio_seconds": fam.PACKETS_ROW_SPEECH_SECONDS,
                         "gpu_hours": fam.PACKETS_ROW_GPU_HOURS, "max_tokens_per_contact": 1},
        "basis": ("generation plan cap = 3,010 x (2 program contacts + 2 answer-only fallback contacts) = 12,040; program contacts 6,020; "
                  "gpu = ceil_0.1(3010 / 1.84 / 60 x 1.3) = 35.5; audio = ceil(8206.436875 x 4) = 32,826; FIT = 3010 x 2 x 4 = 24,080"),
    }
    a["run_ids"] = {
        fam.FIT_RUN: {"core_contacts": 0, "execution_profile": "bounded-discovery-probe", "kind": "preparation", "reads_labels": False,
                      "serves_read_run_id": fam.RUN, "subkind": "native_contact_fit"},
        fam.PACKETS_RUN: {"execution_profile": "bounded-discovery-probe", "kind": "preparation", "subkind": "label_free_speech_packet_encode",
                          "core_contacts": fam.PACKETS_ROW_CALLS, "reads_labels": False, "answers_read": False,
                          "what": ("Thinking mmproj packets for the sample roster: ONE encoder contact per row at max_tokens 1, response discarded unread; GPU swap window; "
                                   "additive promotion under TEST-SAMPLE-3010-promotion.json; own countersigned exposure row"),
                          "serves_read_run_id": fam.RUN},
        fam.RUN: {"execution_profile": "bounded-discovery-probe", "kind": "read", "rows": fam.ROWS,
                  "reads_labels": "Official scoring only after complete delivery. No labels, transcripts or future state enter runtime.",
                  "what": "SLURP lock candidate v3.0 (the locked system on the Thinking core), lock arm only, one attempt"},
    }
    a["attempt_budget"] = {"preparation_run_ids": 1, "read_run_ids": 1,
                           "statement": "No automatic retry. Each generation identity is consumed by its sole attempt; any failure stops this successor comparison. The packets pass is one attempt (the gate's preparation limit allows one recovery; none is pre-authorised here)."}
    a["dated_owner_decision"] = ("DRAFT -- awaiting owner decision 308 (proposed 2026-10-14 in docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, section 'Decision 308 (proposed)'). "
                                 "Ruling 301 A (2026-10-13) signed the successor-3 allowance whose core.packets clause requires the Thinking packets 'under their own countersigned exposure row' "
                                 "but whose permitted_run_ids omit that run id; this v2 supplies the missing preparation id.")
    a["not_authorized"] = [x for x in a["not_authorized"] if x != "new encoding"] + [
        "any encoder contact other than the single Thinking packets pass named in preparation_run_ids", "answer-bearing contacts outside the registered read and FIT ids"]
    a["signature"] = {"status": "DRAFT: awaiting owner decision 308", "recorded_by": "coordinator Fable 5.1"}
    a["status_meaning"] = ("DRAFT v2 of the successor-3 allowance. Status is NOT 'authorised', so contracts.plan.require_owner_split_allowance refuses every plan that pins it. "
                           "On the owner's decision 308 the coordinator sets status to 'authorised', fills the signature block, commits the bytes and runs "
                           "successor3_thinking_packets_fragments.py pin-allowance.")
    a["core"] = dict(a["core"], packets=("the Thinking mmproj packets for the sample roster, promoted in a GPU swap window under their own countersigned exposure row "
                                         f"({fam.PACKETS_RUN}) before any contact"))
    return a


def current_pin() -> str:
    path = ROOT / EXPERIMENT_OUT
    return json.loads(path.read_text(encoding="utf-8"))["owner_allowance"]["sha256"] if path.is_file() else fam.ZERO


def write() -> dict:
    _write(MODEL_OUT, _dump(model_fragment()))
    _write(V2, _dump(v2_allowance()))
    _write(EXPERIMENT_OUT, _dump(experiment_fragment(current_pin())))
    return {"written": [MODEL_OUT, EXPERIMENT_OUT, V2], "v2_sha256": fam.sha_file(V2), "pin": current_pin()}


def pin_allowance() -> dict:
    document = json.loads((ROOT / V2).read_text(encoding="utf-8"))
    if document.get("status") != "authorised":
        raise SystemExit(f"REFUSED: {V2} status is {document.get('status')!r}, not 'authorised'; the owner has not signed decision 308")
    sha = fam.sha_file(V2)
    _write(EXPERIMENT_OUT, _dump(experiment_fragment(sha)))
    return {"pinned": sha, "fragment": EXPERIMENT_OUT}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("mode", choices=("write", "pin-allowance"))
    args = parser.parse_args(argv)
    print(json.dumps(write() if args.mode == "write" else pin_allowance(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
