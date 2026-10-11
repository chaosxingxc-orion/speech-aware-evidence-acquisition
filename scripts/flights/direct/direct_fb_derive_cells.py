#!/usr/bin/env python3
"""Derive the four cells of the 266-E bare-core read (config only): baselines, experiments, campaign plans, the smoke roster receipt.

WHAT THE CELLS ARE. The sealed ``slurp-direct-max512-train-fold-a-v1`` baseline (the direct-only phase program of the shared
controller, the closed-list task instruction, the full legal ontology) re-pointed at TRAIN Fold B, flown on two cores:

* ``instruct`` / ``replicate`` -- the resident Instruct session (fragment ``q4km-mmproj-free-slurp-native-bounded-perception-proof-
  np4-ctx24k-max512-v1``), twice, request-identical, in one chain;
* ``thinking`` / ``smoke`` -- the Thinking session (fragment ``q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1``, the
  completion cap amended 2,048 -> 8,192 at the decode-cost sign-off; ``direct_fb_family.THINK_MODEL``), the 1,080-row arm and a four-row
  decode-cost smoke on the first four Fold B rows.

HOW IT IS DERIVED (nothing hand-edited). Every baseline is the parent's bytes except the ``live_phase_fit`` identity and contact cap, the
audio-seconds cap, the prose, and (Thinking only) the packet promotion receipt, which names the Thinking core's OWN packet root because
the audio-encoder tensors of the two mmproj files differ (748 of 860 tensors; the Instruct packets are not valid input). Every
experiment is the committed VER-1a Fold B experiment's skeleton (roster, populations, split identity) with the cell, budget, readiness and
declaration blocks replaced. ``preserve_wire_responses`` is FALSE for every arm: a preserved wire response would persist the Thinking
core's ``reasoning_content`` (owner decision 266-E constraint (iii)).

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. All cells are HELD.

    python -B scripts/flights/direct/direct_fb_derive_cells.py
"""

from __future__ import annotations

import copy
import io
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import direct_fb_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash  # noqa: E402


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def smoke_roster_receipt() -> dict:
    """The first four rows of the Fold B roster, in roster order (the rule the smoke is registered under)."""

    parent_path = fam.ROSTER["arm"]
    parent = json.loads(rd(parent_path))
    items = copy.deepcopy(parent["items"][: fam.SMOKE_ROWS])
    ids = [item["sample_id"] for item in items]
    strata: dict[str, int] = {}
    for item in items:
        strata[item["stratum"]] = strata.get(item["stratum"], 0) + 1
    return {
        "audio_seconds_total": sum(float(item["audio_seconds"]) for item in items),
        "authority": "owner decision 266-E (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md): the four-row decode-cost smoke of the bare-core read.",
        "carrier_lock_key": "slurp",
        "distinct_utterances": len({item["utterance_id"] for item in items}),
        "draw_method": "No draw: a prefix of the parent roster.",
        "generator": "scripts/flights/direct/direct_fb_derive_cells.py",
        "headset_recordings": sum(1 for item in items if item["headset"]),
        "items": items,
        "offline_guard": {"attempted_targets": [], "outbound_connection_attempts": 0},
        "parent": {
            "count": len(parent["items"]),
            "file_sha256": __import__("hashlib").sha256((REPO_ROOT / parent_path).read_bytes()).hexdigest(),
            "relpath": parent_path,
            "roster_id": parent["roster_id"],
            "split_identity_hash": parent["split_identity_hash"],
        },
        "per_stratum": strata,
        "roster_id": fam.SMOKE_ROSTER_ID,
        "roster_role": "construction",
        "roster_role_note": "construction: TRAIN Fold B rows; the smoke is a structural decode-cost proof, never scored and never read for quality.",
        "schema": "saea-roster-receipt-v1",
        "seed": parent.get("seed"),
        "selection_rule": f"The FIRST {fam.SMOKE_ROWS} items of {parent['roster_id']} in the parent's order.",
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
        "split_role": "discovery",
        "strata_counts": strata,
    }


WHAT_THIS_IS = {
    "instruct": (
        "the Instruct arm of the bare-core Thinking-versus-Instruct read (owner decision 266-E): the sealed slurp-direct-max512 form, one complete "
        "direct answer per row through the shared controller's direct-only phase program, FlightRuntime and OpenJiuwen on the resident "
        "Instruct session, TRAIN Fold B 1,080. No knowledge supply, no analytical tool, no native tool authority. The comparator of the read."
    ),
    "replicate": (
        "the in-chain request-identical REPLICATE of the Instruct arm of the bare-core read (owner decision 266-E; measurement instrument "
        "rule 3): the same fragment bytes, session and 1,080 rows flown a second time, so the cross-session Thinking delta is read against a "
        "measured same-core offset. Between the two Instruct passes only the live_phase_fit identity and this prose differ; neither enters a request."
    ),
    "thinking": (
        "the Thinking arm of the bare-core read (owner decision 266-E): the SAME direct-only form on the Thinking core (its own session, its own "
        f"speech-packet root, completion cap {fam.THINK_MAX_TOKENS}, --reasoning-format deepseek so reasoning never enters message.content), TRAIN Fold B 1,080. "
        "The delivered answer is the content channel only; reasoning text is never delivered, never persisted beyond hashes and never scored."
    ),
    "smoke": (
        "the four-row decode-cost smoke of the Thinking arm of the bare-core read (owner decision 266-E): the same fragment content as the "
        "Thinking arm on the first four Fold B rows. It seals and reports tokens per answer, seconds per contact and the GPU-hour projection for "
        "1,080 rows BEFORE the arm is queued. No score, no read."
    ),
}


def derive_baseline(key: str) -> str:
    spec = fam.CELLS[key]
    raw = rd(f"configs/baseline/{fam.PARENT_BASELINE}.json")
    document = json.loads(raw)
    if document.get("policy") != fam.POLICY or document.get("scorers", [None])[0] != fam.SCORER:
        raise SystemExit("the parent baseline is not the direct-only form scored by slurp-slu-official-train")
    for forbidden in ("prepared_phase_supply", "native_episode", "phase_tools"):
        if forbidden in document:
            raise SystemExit(f"the parent baseline declares {forbidden}")
    # The fold-excluded knowledge view (never the parent's full-TRAIN one): the runner's roster guard compares it with the query roster.
    document["knowledge_snapshot_relpath"] = fam.KNOWLEDGE_SNAPSHOT_RELPATH
    document["knowledge_snapshot_sha256"] = fam.KNOWLEDGE_SNAPSHOT_SHA256
    document["live_phase_fit"] = {"attempt_id": spec["fit_attempt"], "contact_cap": fam.fit_contact_cap(spec["rows"]), "run_id": spec["fit_run"]}
    document["live_phase_fit_audio_seconds_cap"] = fam.audio_cap(spec["roster"])
    out = f"configs/baseline/{spec['baseline']}.json"
    if spec["core"] == "thinking":
        document["speech_packet_promotion_receipt"] = fam.THINK_PROMOTION_RECEIPT
        document["speech_packet_promotion_receipt_sha256"] = fam.UNPINNED_SHA
        # Re-derivation after the pin step keeps the real pin: writing the zero sentinel back would undo
        # scripts/slurp_fold_preprocess_thinking.py --pin-receipt --write (the flip refuses the sentinel).
        if (REPO_ROOT / out).is_file():
            existing = json.loads(rd(out))
            real = existing.get("speech_packet_promotion_receipt_sha256")
            if existing.get("speech_packet_promotion_receipt") == fam.THINK_PROMOTION_RECEIPT and real not in (None, fam.UNPINNED_SHA):
                document["speech_packet_promotion_receipt_sha256"] = real
    document["what_this_is"] = f"Cell 266-E {spec['role']}: " + WHAT_THIS_IS[key]
    rec = fam.recovery(key)
    if rec:
        document["what_this_is"] += f" Recovery rec1 ({rec['recovered_at']}): {rec['root_cause']}."
    wr(out, dump_like(raw, document))
    return out


def budgets(key: str) -> tuple[dict, dict]:
    spec = fam.CELLS[key]
    rows = spec["rows"]
    calls = rows * fam.CONTACTS_PER_ROW
    audio = fam.audio_cap(spec["roster"])
    calls, audio = fam.cumulative_budget(key, calls, audio)        # a recovered cell: the original plan plus the failed attempts' recorded spend
    family = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": fam.fit_contact_cap(rows),
        "generation_calls_cap": calls,
        "gpu_hours_fit_inclusive": spec["gpu_hours"],
        "native_task_contract_calls_cap": 0,
        "official_complete_scoring_jobs": spec["scoring_jobs"],
        "repeated_speech_audio_seconds_cap": audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": spec["gpu_hours"], "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return family, plan


STAGE3_ALGORITHM_NOTE = (
    "The 266-E read carries NO training-free RL operator and says so explicitly: it is a bare-core capability read -- the sealed direct-only "
    "form on two cores -- with no rollout, no per-sample scoring, no credit assignment, no update operator, no evolving store and no mechanism."
)

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/direct/direct_fb_mint_receipt.py), swaps the "
    "serving geometry (scripts/flights/batch/serving_swap.sh think-np4, checklist in the package README) and re-pins with "
    "scripts/flights/repin_cell.py --set-ready (through scripts/flights/direct/direct_fb_flip.sh). The program declares no supplied first "
    "phase (item E38), so the re-pin creates no prepared artifact; --allow-output-change must never be passed. The Thinking cells additionally "
    "need the Thinking speech-packet root prepared and its promotion receipt pinned (the baseline carries a zero sentinel the flip refuses). "
    "Nothing here authorises a flight, a readiness flip or an admission entry."
)


def derive_experiment(key: str, parent_arm: dict, parent_smoke: dict) -> str:
    spec = fam.CELLS[key]
    smoke = key == "smoke"
    parent = parent_smoke if smoke else parent_arm
    document = copy.deepcopy(parent)
    rows = spec["rows"]
    family, plan = budgets(key)
    roster = fam.roster_doc(spec["roster"])
    document["date"] = fam.DATE
    document["experiment_id"] = spec["run"]
    document["execution_plan"], document["family_budget"] = plan, family
    document["fragment_kind"] = f"saea-{fam.PKG_NAME}"
    document["service_session"] = spec["session"]
    document["preserve_wire_responses"] = False
    document["stage3_algorithm"] = {"id": "none", "note": STAGE3_ALGORITHM_NOTE, "operators_used": []}
    document["generation_budget"] = {
        "cap": rows * fam.CONTACTS_PER_ROW,
        "definition": (
            f"The direct-only phase program (configs/policy/{fam.POLICY}.json: one phase, max_contacts 1, always-run-full-program) makes exactly ONE "
            f"contact per row, so {rows:,} x 1 = {rows * fam.CONTACTS_PER_ROW:,} is the program's exact maximum and its expectation at once. The live "
            f"phase fit makes 1 + (2 + 1) x {rows} = {fam.fit_contact_cap(rows):,} tokenizer endpoint calls under its own run id {spec['fit_run']}. "
            "The GPU-hour ceiling is a BOUND, never a target. Budgets are run-cumulative across every attempt of a run id."
        ),
        "target": rows * fam.CONTACTS_PER_ROW,
    }
    cell = document["cells"][0]
    cell.update(
        attempt_id=spec["attempt"], baseline_fragment=spec["baseline"], cell_id=spec["cell"], dataset_fragment=fam.DATASET,
        model_fragment=spec["model"], run_id=spec["run"],
        allowed_execution_stages=["check", "worker"] if smoke else ["check", "worker", "campaign"],
    )
    decision = {
        "kind": "decision", "expected_decision_id": fam.DECISION_ID, "relpath": fam.DECISION_RELPATH, "sha256": "0" * 64,
        "reason": f"Decision {fam.DECISION_ID} pinned by scripts/flights/repin_cell.py.",
    }
    cell["readiness"] = {
        "reason": (
            f"Cell 266-E {spec['role']} registered before contact on {fam.DATE} by script (decision 58) from the sealed Fold A direct baseline "
            f"and the committed Fold B experiment skeleton (owner decision 266-E)." + HELD
        ),
        "requirements": [decision],
        "state": "held",
    }
    out = f"configs/experiment/{spec['cell']}.json"
    if (REPO_ROOT / out).is_file():
        # Re-derivation after the flip keeps the cell's readiness block (state, reason, pinned decision receipt): the flip's re-pin owns it, and
        # resetting it to HELD here would silently un-flip a cell. A first derivation (no file yet) writes HELD.
        cell["readiness"] = json.loads(rd(out))["cells"][0]["readiness"]
    document["population"] = {
        "count": rows,
        "dataset_fragment": fam.DATASET,
        "decision_population": (
            f"TRAIN Fold B ({roster['roster_id']}): {rows} rows of {fam.ROSTER[spec['roster']]}"
            + (", the first four rows in roster order; structural decode-cost proof only, no score and no read." if smoke else
               "; discovery role, rollout-exposed, never a test claim (owner decisions 28 and 86).")
        ),
        "roster_receipt": fam.ROSTER[spec["roster"]],
        "split_identity_hash": roster["split_identity_hash"],
    }
    ids = [item["sample_id"] for item in roster["items"]]
    document["populations"] = [{"dataset_fragment": fam.DATASET, "ids": ids}]
    document["split_id"] = "SLURP-EVO-FOLD-B-V2"
    core_text = ("the Thinking core (its own session " + fam.THINK_SESSION + f", completion cap {fam.THINK_MAX_TOKENS}, --reasoning-format deepseek)"
                 if spec["core"] == "thinking" else "the resident Instruct core (max512)")
    document["core_read_design"] = {
        "arms": {k: fam.CELLS[k]["run"] for k in fam.ALL_KEYS},
        "chain": "smoke -> coordinator decode-cost sign-off -> Thinking arm (Thinking session) -> serving restore -> Instruct arm -> Instruct replicate (Instruct session)",
        "reading": "paired per row on the official SLU-F1; the Thinking delta is read against the mean of the two Instruct passes at the cross-flight bar",
        "this_cell": spec["role"],
        "stage3_measurement_discipline": "docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md",
    }
    if smoke:
        document["purpose"] = (
            f"Four-row decode-cost smoke of the Thinking arm of the 266-E read on {core_text}: that the request form, the Thinking packet plane, the "
            "reasoning-format option, the live phase fit and the seal work, and what a Thinking answer costs (completion tokens per answer p50/p99, "
            "seconds per contact, the GPU-hour projection for 1,080 rows). Scored by no one and read by no one: four rows are never evidence."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops the cell and "
            "the Thinking arm does not open. A smoke is re-flown whole at most once under one root-diagnosed recovery re-registration."
        )
    else:
        document["purpose"] = (
            f"{spec['run']}: the {spec['role']} of the 266-E bare-core read on TRAIN Fold B 1,080 on {core_text} (owner decision 266-E): does a "
            "stronger core, with the system held out entirely, move the official SLU-F1 by more than the cross-flight bar (about 2.5 pp) over the "
            "Instruct core? Development numbers only (owner decisions 28 and 86); never a test claim. The read is cross-session by necessity, so the "
            "Instruct arm flies twice in the same chain and the Thinking delta is judged against the mean of the two. Nothing here authorises a "
            "flight, a readiness flip or an admission entry."
        )
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, prompt, geometry or cap change. AT MOST "
            "ONE root-diagnosed recovery re-registration per run id (a new generation attempt id AND a new live_phase_fit run and attempt id); a second "
            "failure closes the cell and the fix is proven on a four-row dry run. A response whose delivered content carries a reasoning marker is a "
            "failure of the read, not of a row: it stops the flight (reasoning_content_guard). A partial manifest is never scored and never read."
        )
    rec = fam.recovery(key)
    if rec:
        # prose only (generation_budget is outside the request-identity proof); failure_policy stays byte-equal across the Instruct pair
        spent_calls, spent_audio = fam.predecessor_spend(key)
        budget_text = ("the run-cumulative budget equals the original plan." if spent_calls == 0 else
                       f"the run-cumulative budget is the original plan plus that spend ({spent_calls} contacts, {spent_audio:g} speech-seconds): "
                       f"{plan['planned_model_calls']} calls, {plan['planned_speech_audio_seconds']} speech-seconds.")
        document["generation_budget"]["definition"] += (
            f" Recovery rec1 (the cell's single one; a second failure closes the cell): the failed predecessor attempt {rec['predecessor_attempt_id']} spent "
            f"{spent_calls} contacts, so {budget_text}")
    document.pop("analysis_binding", None)
    wr(out, dump_like(rd(f"configs/experiment/{fam.PARENT_EXPERIMENT}.json"), document))
    return out


def main(argv=None) -> int:
    written = []
    smoke_path = fam.ROSTER["smoke"]
    wr(smoke_path, json.dumps(smoke_roster_receipt(), indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    written.append(smoke_path)
    parent_arm = json.loads(rd(f"configs/experiment/{fam.PARENT_EXPERIMENT}.json"))
    parent_smoke = json.loads(rd(f"configs/experiment/{fam.PARENT_EXPERIMENT.replace('-v1', '-smoke-4-v1')}.json"))
    for key in fam.ALL_KEYS:
        written.append(derive_baseline(key))
        written.append(derive_experiment(key, parent_arm, parent_smoke))
    for key in fam.ARM_KEYS:
        spec = fam.CELLS[key]
        path = f"configs/campaign/{spec['cell']}.json"
        wr(path, json.dumps({"cells": [{"cell": spec["cell"], "experiment": spec["cell"]}], "schema": "saea-campaign-plan-v1"}, indent=2, sort_keys=True) + "\n")
        written.append(path)
    for path in written:
        if re.search(r"ver1a|VER-1a|VER1A", rd(path)):
            raise SystemExit(f"{path}: carries inherited VER-1a identity text")
    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
