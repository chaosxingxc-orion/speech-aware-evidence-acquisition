#!/usr/bin/env python3
"""Register item E41 -- the bounded Perception note on the Earnings21 + ConEC system
form -- as two HELD cells on the E21 geometry, before any contact.

Owner decision 158 (row 158 of
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``) judged E41
unfinished Stage-2 engineering base and ordered it registered with its four-row
dry run and the sub10 re-read; row 103 defines it: "a bounded Perception note
(structured / length-constrained instruction) with its own dry run before the
sub10 re-read of the Earnings system form".

This script is model-free and deterministic. It

1. DERIVES the four config fragments and two campaign plans:

   * the dry run = the E39b dry-run cell (``e21-native-window-system-four-row-
     e39b-v1``, base lock v3.1 as flown) with ONE pin moved --
     ``phase_material.perception.instruction_template`` v1 -> v2 -- plus
     bookkeeping (run / fit / episode ids, prose, readiness, the decision-101
     label);
   * the sub10 re-read = the same system form (v3.1 leaves + the E41 pin) on the
     E35 sub10 roster: the E35 sub10 system baseline's roster pins, the dry
     run's everything else;

2. COMPOSES all four cells through ``core.flight.repin.compute_cell_identity``
   (the re-pin tool's own path) and ``rails.native_episode_config.
   load_native_episode_config`` on the real program, and writes the composed
   leaf diffs against the E39b dry run and the E35 sub10 system arm;

3. BINDS the sealed E35 sub10 direct comparator per window (ids and hashes only,
   from the sealed ``outputs.jsonl``; no text);

4. WRITES the readiness package ``docs/readiness/2026-09-27-e21-native-window-
   e41-v1/`` (protocol, plans, recipes, facts, admission drafts, README), the
   preregistration, and appends the DRAFT exposure-ledger section (no ``|`` in
   any cell).

The two model-free receipts it cites (``perception-trace-read-v1.json``,
``instruction-token-measurement-v1.json``) come from
``scripts/analysis/e21_e41_perception_note_trace_read.py`` and must exist first.

    python scripts/flights/write_e21_e41_registration.py --data-root "$SPEECHRL_DATA_DIR" --base-commit <sha>
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.repin import compute_cell_identity  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.stage3_algorithms import validate_stage3_algorithm_label  # noqa: E402
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config  # noqa: E402

DATE = "2026-09-27"
REGISTERED_AT = "2026-09-27T16:00:00.000000+00:00"
PKG = "e21-native-window-e41-v1"
RD = f"docs/readiness/{DATE}-{PKG}"
PREREG = f"{RD}-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
SESSION = "serving-e21-native-window-flightruntime-np4-max1024-v1"
MODEL = "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1"
POLICY = "phase-native-review-revise-acquire-v1"
OLD_PROBE = "probes/e21_native_window_system_perception_v1.txt"
NEW_PROBE = "probes/e21_native_window_system_perception_v2.txt"
PIN_PATH = "phase_material.perception.instruction_template"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DEC_DIR = f"coordination/{PKG}"

PARENT_DRY = {"experiment": "e21-native-window-four-row-e39b-dry-run-v1", "cell": "e21-native-window-system-four-row-e39b-v1",
              "baseline": "e21-native-window-system-four-row-e39b-v1", "run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1"}
PARENT_SUB10 = {"experiment": "e21-native-window-sub10-direct-vs-system-v1", "cell": "e21-native-window-system-sub10-v1",
                "baseline": "e21-native-window-system-sub10-v1", "run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1"}
DIRECT_SUB10 = {"run": "SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1", "attempt": "attempt-e21-native-window-direct-sub10-v1",
                "cell": "e21-native-window-direct-sub10-v1", "flight_commit": "1a9c78d2"}
SYSTEM_SUB10 = {"run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1", "attempt": "attempt-e21-native-window-system-sub10-v1", "flight_commit": "1a9c78d2"}

CELLS = {
    "dry-run": {
        "label": "the four-row dry run",
        "experiment": "e21-native-window-four-row-e41-dry-run-v1",
        "experiment_id": "SAEA-E21-NATIVE-WINDOW-FOUR-ROW-E41-DRY-RUN-V1",
        "cell": "e21-native-window-system-four-row-e41-v1",
        "baseline": "e21-native-window-system-four-row-e41-v1",
        "dataset": "e21-native-window-four-row-v1",
        "run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1",
        "attempt": "attempt-e21-native-window-system-four-row-e41-v1",
        "fit_run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-FIT-V1",
        "fit_attempt": "attempt-e21-native-window-system-four-row-e41-v1-fit",
        "windows": 4, "calls": 1, "calls_cap": 44, "fit_cap": 176, "speech_cap": 3960, "gpu": 0.5,
        "window_seconds": 360, "decision_id": "e21-native-window-e41-dry-run-admission-v1",
        "decision_relpath": f"{DEC_DIR}/root-admission-dry-run-v1.json",
        "draft": "root-admission-draft-dry-run-v1.json", "prefix": "dry-run",
        "chain": {"expected_rows": 1, "contacts_per_row": 20, "ceiling_per_row": 44},
    },
    "sub10": {
        "label": "the sub10 re-read",
        "experiment": "e21-native-window-sub10-e41-v1",
        "experiment_id": "SAEA-E21-NATIVE-WINDOW-SUB10-E41-V1",
        "cell": "e21-native-window-system-sub10-e41-v1",
        "baseline": "e21-native-window-system-sub10-e41-v1",
        "dataset": "e21-native-window-sub10-v1",
        "run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1",
        "attempt": "attempt-e21-native-window-system-sub10-e41-v1",
        "fit_run": "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1-FIT-V1",
        "fit_attempt": "attempt-e21-native-window-system-sub10-e41-v1-fit",
        "windows": 342, "calls": 10, "calls_cap": 3762, "fit_cap": 15048, "speech_cap": 334477, "gpu": 12.0,
        "window_seconds": 30407, "decision_id": "e21-native-window-e41-sub10-admission-v1",
        "decision_relpath": f"{DEC_DIR}/root-admission-sub10-v1.json",
        "draft": "root-admission-draft-sub10-v1.json", "prefix": "sub10",
        "chain": {"expected_rows": 10, "contacts_per_row": 160, "ceiling_per_row": 550},
    },
}

STAGE3_ALGORITHM = {
    "id": "none",
    "operators_used": [],
    "note": (
        "This cell carries NO training-free RL operator and says so explicitly: item E41 is unfinished Stage-2 "
        "engineering base (owner decision 158) -- one instruction pin that bounds the Perception note of the "
        "Earnings system form so the shared harness carries that form soundly -- with no rollout, no per-sample "
        "scoring, no credit assignment, no update operator and no learned artifact."
    ),
}


def rd(path: Path) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, document: object, indent: int = 2) -> str:
    text = json.dumps(document, indent=indent, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fragment(kind: str, name: str) -> dict:
    return json.loads(rd(REPO / "configs" / kind / f"{name}.json"))


def walk(node, prefix=""):
    if isinstance(node, dict):
        if not node:
            yield prefix, {}
        for key, value in node.items():
            yield from walk(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(node, list):
        if not node:
            yield prefix, []
        for index, value in enumerate(node):
            yield from walk(value, f"{prefix}[{index}]")
    else:
        yield prefix, node


def leaf_diff(old: dict, new: dict) -> list[dict]:
    a, b = dict(walk(old)), dict(walk(new))
    rows = []
    for path in sorted(set(a) | set(b)):
        if a.get(path, "<absent>") != b.get(path, "<absent>"):
            rows.append({"path": path, "old": a.get(path, "<absent>"), "new": b.get(path, "<absent>")})
    return rows


# ---------------------------------------------------------------------------
# 1. Fragments.
# ---------------------------------------------------------------------------


def derive_fragments() -> dict:
    e39b_base = fragment("baseline", PARENT_DRY["baseline"])
    e39b_exp = fragment("experiment", PARENT_DRY["experiment"])
    e35_sub10_base = fragment("baseline", PARENT_SUB10["baseline"])
    e35_sub10_exp = fragment("experiment", PARENT_SUB10["experiment"])
    out = {}

    for key, cell in CELLS.items():
        base = copy.deepcopy(e39b_base)
        if key == "sub10":
            for pin in ("prepared_execution_units", "prepared_window_feature_packets"):
                base[pin] = copy.deepcopy(e35_sub10_base[pin])
            for pin in ("knowledge_snapshot_relpath", "knowledge_snapshot_sha256", "d1_evidence_supplement"):
                if pin in e35_sub10_base:
                    assert base.get(pin) == e35_sub10_base[pin], pin
        base["native_contact_fit"] = {
            "attempt_id": cell["fit_attempt"], "contact_cap": cell["fit_cap"],
            "max_speech_packets": 1, "run_id": cell["fit_run"],
        }
        base["native_episode"]["episode_id"] = cell["cell"]
        assert base["phase_material"]["perception"]["instruction_template"] == OLD_PROBE
        base["phase_material"]["perception"]["instruction_template"] = NEW_PROBE
        base["what_this_is"] = (
            f"Item E41 (owner decisions 103 and 158, 2026-09-27), {cell['label']}, HELD: the Earnings21 + ConEC "
            "six-node native system form exactly as base lock v3.1 carries it (finite_completion_scope "
            "answering-node, per-role caps Perception 640 / Reviewer 640, tool-free Reviewer probe v2) with ONE "
            "pin moved -- the Perception node's instruction, from the free-text working note "
            f"({OLD_PROBE}) to the BOUNDED note ({NEW_PROBE}): a numbered list of at most 5 lines, at most 20 "
            "words each, at most 4 quoted spoken words per reading, never repeated, explicitly not a transcript. "
            "The E35 sub10 read and the E39 / E39b dry runs traced every Earnings Perception truncation to an "
            "unbounded note (loops, open enumerations, transcript re-emission and long prose; "
            f"{RD}/perception-trace-read-v1.json). NO optimisation, NO new mechanism, NO flight: a "
            "registered-before-contact engineering-base proof; no score, comparison, effectiveness or "
            "generalization claim may be made from it."
        )
        base["readiness"] = {
            "state": "held",
            "reason": (
                f"E41 {cell['label']} (2026-09-27): registered before contact; the flight-readiness authority is "
                "the experiment cell's readiness block, flipped by scripts/flights/repin_cell.py after root mints "
                f"{cell['decision_relpath']} ({cell['decision_id']})."
            ),
        }
        out[("baseline", cell["baseline"])] = base

        if key == "dry-run":
            exp = copy.deepcopy(e39b_exp)
            exp["experiment_id"] = cell["experiment_id"]
            exp["date"] = DATE
            exp["purpose"] = (
                "Item E41 (owner decisions 103 and 158): a four-row dry run of the BOUNDED Perception note on the "
                "Earnings21 + ConEC six-node system form, on the SAME roster, the SAME shared harness "
                "(rails.controllers.EvidenceAgentController, core.flight.FlightRuntime, the OpenJiuwen executor) "
                "and the SAME E21 geometry the E39b dry run flew, with one pin moved (the Perception instruction). "
                "NO optimisation, NO new mechanism, NO flight: registered-before-contact configuration only. No "
                "score, comparison, decision, effectiveness or generalization claim may be made from this proof."
            )
            c = exp["cells"][0]
            c["cell_id"], c["run_id"], c["attempt_id"] = cell["cell"], cell["run"], cell["attempt"]
            c["baseline_fragment"] = cell["baseline"]
            c["readiness"] = {
                "state": "held",
                "reason": (
                    f"E41 dry run (2026-09-27): registered before contact; decision id {cell['decision_id']} at "
                    f"{cell['decision_relpath']}; held until root mints and flips."
                ),
                "requirements": [],
            }
            c["attempt_note"] = (
                "First attempt of this run id. The one pin against e21-native-window-system-four-row-e39b-v1 is "
                f"{PIN_PATH} {OLD_PROBE} -> {NEW_PROBE}. Every pinned artifact (execution-unit subset, window "
                "feature packets, knowledge snapshot) is the parent's, unchanged: those pins are bound to the "
                "four-row roster batch SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1, not to a run id."
            )
            exp["execution_plan_note"] = (
                "One arm only (the E41 system form); its direct comparator is the already-flown "
                "e21-native-window-direct-four-row-v1 cell, and its structural comparator the sealed E39b dry run, "
                "on the same roster and the same serving geometry. Ceilings, not targets, enforced run-cumulatively "
                "per run id by the runtime. Speech seconds are REPEATED seconds: every native-episode contact "
                "re-sends the window audio, so the ceiling is windows x 11 x window seconds."
            )
        else:
            exp = {
                "experiment_id": cell["experiment_id"],
                "date": DATE,
                "execution_profile": "bounded-discovery-probe",
                "purpose": (
                    "Item E41 (owner decisions 103 and 158): the sub10 re-read of the Earnings21 + ConEC six-node "
                    "system form at base lock v3.1 with the BOUNDED Perception note, on the SAME seeded 10-of-44 "
                    "discovery subset (342 native windows) the sealed E35 sub10 pair flew, through the SAME shared "
                    "harness and the SAME E21 geometry; its direct comparator is the sealed E35 sub10 direct arm, "
                    "bound per window and never re-flown. A descriptive structural read: n = 10 calls is below "
                    "every power floor. NO optimisation, NO new mechanism, NO flight: registered-before-contact "
                    "configuration only. No effectiveness, superiority or generalization claim may be made from it."
                ),
                "failure_policy": e35_sub10_exp["failure_policy"],
                "population": copy.deepcopy(e35_sub10_exp["population"]),
                "cells": [{
                    "cell_id": cell["cell"], "run_id": cell["run"], "attempt_id": cell["attempt"],
                    "arm": "speech-feature-query", "policy": POLICY, "model_fragment": MODEL,
                    "dataset_fragment": cell["dataset"], "baseline_fragment": cell["baseline"],
                    "allowed_execution_stages": ["check", "worker", "campaign"],
                    "readiness": {
                        "state": "held",
                        "reason": (
                            f"E41 sub10 re-read (2026-09-27): registered before contact; flies ONLY after the E41 "
                            f"four-row dry run's receipts read holds R1-R3; decision id {cell['decision_id']} at "
                            f"{cell['decision_relpath']}; held until root mints and flips."
                        ),
                        "requirements": [],
                    },
                    "execution_plan": {"split_role": "discovery", "planned_model_calls": cell["calls_cap"],
                                       "planned_gpu_hours": cell["gpu"], "planned_speech_audio_seconds": cell["speech_cap"]},
                    "attempt_note": (
                        "First attempt of this run id. Against the sealed E35 sub10 system cell the form moves by the "
                        "base lock v3.1 leaves (finite_completion_scope answering-node, Perception / Reviewer caps "
                        "640 / 640, Reviewer probe v2) and the one E41 pin; the roster pins (execution-unit subset, "
                        "window feature packets, knowledge snapshot) are E35 sub10's, bound to the roster batch "
                        "SAEA-E21-NATIVE-WINDOW-SUB10-V1."
                    ),
                }],
                "execution_plan": {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": cell["gpu"],
                                   "planned_model_calls": cell["calls_cap"],
                                   "planned_speech_audio_seconds": cell["speech_cap"], "split_role": "discovery"},
                "execution_plan_note": (
                    "One arm only (the E41 system form); its direct comparator is the sealed E35 sub10 direct arm "
                    "SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1, bound per window, never re-flown. Ceilings, not "
                    "targets, enforced run-cumulatively per run id by the runtime: 3,762 = 342 windows x 11 "
                    "contacts; 334,477 REPEATED speech seconds = 11 x 30,407 window seconds (every native-episode "
                    "contact re-sends the window audio); 12.0 GPU hours = the sealed E35 sub10 system arm's own "
                    "registered value."
                ),
                "service_session": SESSION,
            }
        exp["stage3_algorithm"] = copy.deepcopy(STAGE3_ALGORITHM)
        validate_stage3_algorithm_label(exp["stage3_algorithm"], cell=cell["cell"])
        out[("experiment", cell["experiment"])] = exp
        out[("campaign", cell["cell"])] = {"cells": [{"cell": cell["cell"], "experiment": cell["experiment"]}],
                                           "schema": "saea-campaign-plan-v1"}
    return out


def write_fragments(fragments: dict) -> None:
    for (kind, name), document in fragments.items():
        dump(REPO / "configs" / kind / f"{name}.json", document)


# ---------------------------------------------------------------------------
# 2. Identities and diffs.
# ---------------------------------------------------------------------------


def identity(experiment: str, cell_id: str):
    cell = next(c for c in load_campaign_cells(REPO, experiment) if c.document["cell_id"] == cell_id)
    ident = compute_cell_identity(REPO, experiment, cell)
    composed = compose(REPO, ident.model_fragment, ident.dataset_fragment, ident.baseline_fragment, experiment)
    config = load_native_episode_config(composed.values, default_phase_program(composed.values["policy"]))
    return ident, composed, config


#: The base lock v3.1 leaves the E39 / E39b dry runs proved (docs/results/2026-09-22-base-lock-v3.md section 5b);
#: they differ only against the PRE-v3.1 E35 sub10 system arm, never against the E39b dry run.
V31_PATHS = (
    "native_episode.finite_completion_scope",
    "native_episode.roles.perception.max_completion_tokens",
    "native_episode.roles.reviewer.max_completion_tokens",
    "phase_material.reviewer.instruction_template",
)


def classify(path: str) -> str:
    if path == PIN_PATH:
        return "pin"
    if path in V31_PATHS:
        return "base-lock-v3.1"
    return "bookkeeping"


def composed_diffs() -> dict:
    report = {}
    parents = {"dry-run": PARENT_DRY, "sub10": PARENT_SUB10}
    for key, cell in CELLS.items():
        p = parents[key]
        p_ident, p_comp, p_conf = identity(p["experiment"], p["cell"])
        n_ident, n_comp, n_conf = identity(cell["experiment"], cell["cell"])
        rows = leaf_diff(dict(p_comp.values), dict(n_comp.values))
        for row in rows:
            row["class"] = classify(row["path"])
            for side in ("old", "new"):
                if isinstance(row[side], str) and len(row[side]) > 160:
                    row[side] = {"chars": len(row[side]), "sha256": hashlib.sha256(row[side].encode()).hexdigest()}
        report[key] = {
            "parent": {"experiment": p["experiment"], "cell": p["cell"], "run_id": p["run"],
                       "composed_config_hash_as_committed": p_ident.config_hash,
                       "protocol_hash_as_committed": p_ident.protocol_hash},
            "child": {"experiment": cell["experiment"], "cell": cell["cell"], "run_id": cell["run"]},
            "differing_leaf_paths": len(rows),
            "pins": [r for r in rows if r["class"] == "pin"],
            "rows": rows,
            "episode_config": {
                "parent": {"finite_completion_scope": p_conf.finite_completion_scope,
                           "role_completion_caps": dict(p_conf.role_completion_caps),
                           "finite_completion_policy": p_conf.finite_completion_policy,
                           "react_exhaustion_policy": p_conf.react_exhaustion_policy, "max_contacts": p_conf.max_contacts},
                "child": {"finite_completion_scope": n_conf.finite_completion_scope,
                          "role_completion_caps": dict(n_conf.role_completion_caps),
                          "finite_completion_policy": n_conf.finite_completion_policy,
                          "react_exhaustion_policy": n_conf.react_exhaustion_policy, "max_contacts": n_conf.max_contacts},
            },
            "_identity": n_ident,
        }
    return report


# ---------------------------------------------------------------------------
# 3. The sealed per-window comparator binding.
# ---------------------------------------------------------------------------


def comparator_binding(data_root: Path) -> dict:
    def sources(run: str, attempt: str) -> tuple[list[dict], str]:
        path = data_root / "runs" / run / attempt / f"{run}.outputs.jsonl"
        rows = [json.loads(line) for line in io.open(path, encoding="utf-8")]
        return [(row["sample_id"], s) for row in rows for s in row["execution_unit_delivery"]["sources"]], sha_file(path)

    direct, direct_sha = sources(DIRECT_SUB10["run"], DIRECT_SUB10["attempt"])
    system, system_sha = sources(SYSTEM_SUB10["run"], SYSTEM_SUB10["attempt"])
    system_by_unit = {s["execution_unit_id"]: s for _call, s in system}
    windows = []
    for call, s in direct:
        unit = s["execution_unit_id"]
        e35 = system_by_unit[unit]
        windows.append({
            "execution_unit_id": unit, "call": call,
            "direct": {"request_id": s["request_id"], "delivery_text_sha256": s["delivery_text_sha256"],
                       "raw_text_sha256": s["raw_text_sha256"], "saturated": s["saturated"], "skipped": s["skipped"],
                       "empty": s["delivery_text_sha256"] == EMPTY_SHA},
            "e35_system": {"request_id": e35["request_id"], "delivery_text_sha256": e35["delivery_text_sha256"],
                           "empty": e35["delivery_text_sha256"] == EMPTY_SHA,
                           "abstained": e35["request_id"].endswith("/delivery/native-abstention-v1")},
        })
    assert len(windows) == 342 and len(system_by_unit) == 342, (len(windows), len(system_by_unit))
    calls = sorted({w["call"] for w in windows})
    return {
        "schema": "saea-e41-sub10-comparator-binding-v1",
        "boundary": "ids, request ids, booleans and SHA-256 digests only; no utterance, transcript, reference or delivered text",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "scorer": 0, "tokenizer": 0},
        "roster": {"dataset_fragment": "e21-native-window-sub10-v1", "batch": "SAEA-E21-NATIVE-WINDOW-SUB10-V1",
                   "split_identity_hash": "744c4b2e2d2eece3b05c68089c02000e38c96d5c62db8055d9c421fd509a8f61",
                   "calls": calls, "windows": len(windows),
                   "windows_per_call": {c: sum(1 for w in windows if w["call"] == c) for c in calls}},
        "direct_comparator": {**DIRECT_SUB10, "outputs_sha256": direct_sha, "never_reflown": True,
                              "sealed_read": "docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md"},
        "e35_system_arm": {**SYSTEM_SUB10, "outputs_sha256": system_sha, "never_reflown": True,
                           "abstained_windows": sum(1 for w in windows if w["e35_system"]["abstained"]),
                           "empty_windows": sum(1 for w in windows if w["e35_system"]["empty"])},
        "direct_empty_windows": sum(1 for w in windows if w["direct"]["empty"]),
        "join_key": "execution_unit_id (<call>#w<nnnn>); the E41 sub10 arm flies the same roster batch, so its outputs.jsonl sources carry the same 342 ids",
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# 4. The package.
# ---------------------------------------------------------------------------


def stage3_measurement() -> dict:
    return {
        CELLS["dry-run"]["run"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "rows": 1, "claims_benefit": False,
            "primary_metric": "the Perception length-truncation count on the four windows (target zero), with R1 (no auxiliary node voids its window) and R2 (4 / 4 non-empty deliveries)",
            "note": "A receipts-only STRUCTURAL dry run of one instruction pin: one call (four windows) is far under MIN_BENEFIT_ROWS, so under rule 5 it is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because the cell registers no effect on any task metric. It is NOT an admission request: no admission mode is declared and no harm margin is claimed.",
        },
        CELLS["sub10"]["run"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "rows": 10, "claims_benefit": False,
            "primary_metric": "structural receipts at scale (windows voided by an auxiliary node, non-empty deliveries, the Perception truncation rate) beside the carrier's standard scorer (Whisper-normalised corpus WER) and the agentic metrics (ConEC entity WER mirror, numeric-value accuracy), all DESCRIPTIVE against the sealed E35 sub10 direct arm bound per window",
            "note": "A descriptive structural read: 10 calls (342 windows) sit below every power floor of the measurement instrument and under MIN_BENEFIT_ROWS, so this is a form proof by size; claims_benefit is false and expected_effect_pp is 0.0 because no effect on any metric is registered or may be claimed. The comparator is a sealed arm from another flight (a cross-flight contrast with no in-chain replicate), which is exactly why the read is descriptive and never an admission. It is NOT an admission request.",
        },
    }


def plan_document(key: str, kind: str, ident, protocol_sha: str, base_commit: str) -> dict:
    cell = CELLS[key]
    is_fit = kind == "fit"
    run = cell["fit_run"] if is_fit else cell["run"]
    attempt = cell["fit_attempt"] if is_fit else cell["attempt"]
    calls = cell["fit_cap"] if is_fit else cell["calls_cap"]
    roster = ("the four-row roster batch SAEA-E21-NATIVE-WINDOW-FOUR-ROW-V1 (4 native windows of call 4320211)"
              if key == "dry-run" else "the E35 sub10 roster batch SAEA-E21-NATIVE-WINDOW-SUB10-V1 (10 seeded discovery calls, 342 native windows)")
    return {
        "schema": "saea-registered-generation-plan-v1",
        "plan_kind": "native contact fit" if is_fit else "generation",
        "cell": cell["cell"],
        "experiment": cell["experiment"],
        "campaign_plan": f"configs/campaign/{cell['cell']}.json",
        "protocol_document": {"relpath": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha},
        "root_registration_required": True,
        "execution_plan": {
            "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
            "run_id": run, "attempt_id": attempt, "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "earnings21-original", "split_role": "discovery",
            "split_identity_hash": ident.split_identity_hash, "planned_model_calls": calls,
            "planned_gpu_hours": cell["gpu"], "planned_speech_audio_seconds": cell["speech_cap"],
            "protocol_hash": ident.protocol_hash,
        },
        "execution_route": (f"Shared core.flight.cli campaign over the committed single-cell campaign plan "
                            f"configs/campaign/{cell['cell']}.json; the campaign acquires its own GenerationLease "
                            f"against the resident E21 session and attaches only."),
        "execution_location": "Shared six-node controller (phase-native-review-revise-acquire-v1: perception, solver, reviewer x3, planner, zero-contact acquisition, delivery normaliser) and the OpenJiuwen executor, through core.flight.FlightRuntime.",
        "expected_session_id": SESSION,
        "family_budget": {
            "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
            "fit_endpoint_calls_cap": cell["fit_cap"], "generation_calls_cap": cell["calls_cap"],
            "gpu_hours_fit_inclusive": cell["gpu"], "native_task_contract_calls_cap": 0,
            "official_complete_scoring_jobs": 1, "paid_api_calls": 0,
            "repeated_speech_audio_seconds_cap": cell["speech_cap"],
        },
        "modules": {
            "base": ("the Earnings21 + ConEC six-node native system form at base lock v3.1 exactly as the sealed E39b "
                     "dry run flew it (flight commit 48c4bd1e): phase-native-review-revise-acquire-v1, ceiling 11, "
                     "tool-free, finite_completion_scope answering-node, Perception / Reviewer caps 640 / 640, "
                     "tool-free Reviewer probe v2, finite_completion_policy deliver-latest-or-abstain, "
                     "react_exhaustion_policy continue-without-answer, the np4 x 24,576 max1024 E21 geometry, "
                     f"the shared controller / FlightRuntime / OpenJiuwen path; roster: {roster}."),
            "factor": (f"ONE pin: {PIN_PATH} {OLD_PROBE} -> {NEW_PROBE} (the bounded Perception note). Everything "
                       "else is the base's own bytes; the remaining composed differences are bookkeeping "
                       f"({RD}/composed-config-diff-v1.json)."),
            "zero_added_contacts": "The role graph is untouched: the ceiling stays 11 contacts per window.",
        },
        "scoring": ("At most one complete official scoring job at finalize over the baseline's unchanged scorer stack "
                    "(asr-wer-whisper, conec-entity-wer-official mirror, numeric-value-accuracy-v1, "
                    "semantic-high-impact-error-rate-v1, cost), through core.scoring_batch, never sharded. "
                    + ("The dry-run read is RECEIPTS ONLY and quotes no score." if key == "dry-run" else
                       "The sub10 read quotes the scores DESCRIPTIVELY beside the sealed E35 direct arm; no claim.")),
        "quality_read_gate": ("No read of any kind before the single attempt's manifest is sealed and complete; the "
                              "read prints or persists no utterance, transcript, reference or delivered text."),
        "requires_before_flight": [
            "The roster's execution-unit subset, window feature packets and knowledge snapshot present at their pinned hashes (they are: the sealed parent flights used them).",
            f"The resident serving session {SESSION} up on the E21 geometry and the SLURP np4 session stopped; the flight attaches and never spawns or stops a server.",
            f"Root has minted {cell['decision_relpath']} ({cell['decision_id']}) and flipped this cell with scripts/flights/repin_cell.py; readiness is HELD until then.",
        ] + (["The E41 four-row dry run's receipts read holds R1, R2 and R3 (dry-run-analysis-recipe-v1.json); the sub10 decision receipt is minted only after that read is committed."] if key == "sub10" else []),
        "prepared_phase_supply_note": "NONE and none is pinned: the program declares no supplied first phase (item E38); --allow-output-change must never be passed.",
        "fit_arithmetic": f"{cell['windows']} units x 11 native contacts x (1 speech packet + 3 endpoints) = {cell['fit_cap']}",
        "registration_state": ("REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending); readiness HELD. The "
                               "flip moves the composed and protocol hashes below and the re-pin tool rewrites them."),
        "composed_config_hash": ident.config_hash,
        "registered_at_utc": REGISTERED_AT,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree /home/chao/saea-worktrees/fable-e41, branch fable/e41, base commit {base_commit}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "unused_budget_is_not_attempt_authority": True,
        "attempt_note": "First attempt of this run id. At most one separately registered recovery after a named cause; a second failure stops the flight.",
    }


def dry_run_recipe() -> dict:
    cell = CELLS["dry-run"]
    return {
        "schema": "saea-receipts-only-read-recipe-v1",
        "recipe_id": "e21-native-window-e41-dry-run-receipts-read-v1",
        "registered_at_utc": REGISTERED_AT,
        "title": "Item E41 four-row dry run on the Earnings21+ConEC native-window system form: receipts-only read",
        "cell_kind": "STRUCTURAL DRY RUN -- the receipt assertions are the deliverable. No score is quoted.",
        "authority": {
            "item": "E41, row 103 (definition) and row 158 (carry it out) of docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md",
            "rule_source": "the E39 / E39b rule R1-R3 (docs/readiness/2026-09-23-e21-native-window-four-row-e39b-v1/analysis-recipe-v1.json), with R3 read on the Perception node first",
            "trace_read": f"{RD}/perception-trace-read-v1.json",
        },
        "claim_boundary": "Structural receipts on four historically exposed discovery windows of one call. No score, effectiveness, comparison or generalization claim of any kind.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": 0, "server": 0, "tokenizer": 0},
        "run_ids": {"arm": cell["run"], "fit": cell["fit_run"]},
        "inputs": {
            "sealed_manifest": f"the single attempt's COMPLETED manifest for {cell['run']}",
            "trace": f"$SPEECHRL_DATA_DIR/runs/{cell['run']}/{cell['attempt']}/{cell['run']}.trace.jsonl (receipt FIELDS only)",
            "comparators": "the sealed E39b dry run SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1 (flight commit 48c4bd1e; Perception 504 / 523 / 640 / 640 tokens, 2 truncated) and the E35 four-row direct arm SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1, read structurally, never re-scored",
        },
        "decision_rule": {
            "kind": "receipts-only; no estimator, no interval, no margin, no bar",
            "assertions": [
                {"id": "R1", "statement": "ZERO retained rows carry a terminal_disposition whose role_id is 'perception' or 'reviewer' together with an abstention (unchanged from E39 / E39b).", "verdict_effect": "a single such row FAILS"},
                {"id": "R2", "statement": "4 of 4 windows deliver NON-EMPTY text: one saea-deliver-earnings-text-v1 receipt per window, zero blank deliveries (unchanged from E39 / E39b).", "verdict_effect": "fewer than 4 FAILS"},
                {"id": "R3", "statement": "The Perception truncation RATE -- Perception contacts with finish_reason 'length' at the 640 cap, over Perception contacts -- is REPORTED with its exact count on every verdict, TARGET ZERO; the Reviewer truncation count at its 640 cap is reported beside it (E39 / E39b's R3 counted both).", "verdict_effect": "item E41's own deliverable is R3 = 0 / 4 Perception truncations; a non-zero count FAILS E41 with the named cause and the truncated note's structure (lines, words per line, repetition share) reported; a non-zero Reviewer count is a named cause carried into the next registration"},
            ],
            "pass": "PASS iff R1 and R2 hold and zero Perception or Reviewer contacts are length-truncated.",
            "consequence": "On PASS root may mint the sub10 decision receipt (e21-native-window-e41-sub10-admission-v1) and flip the sub10 re-read. On FAIL the sub10 cell stays HELD, the named cause is registered, and at most ONE recovery re-registration of this dry run is allowed (a second failure stops E41 and the fix is proven on a fresh four-row dry run).",
        },
        "tables_required": [
            "per-role contact counts beside the sealed E39b dry run's (25 contacts)",
            "per-role finish_reason counts (stop / length / other) beside E39b's",
            "terminal_disposition table: role_id x reason x count, this arm and E39b",
            "delivery table: window, delivered non-empty (yes / no), normaliser receipt present (yes / no)",
            "contact and repeated-speech-second totals against the registered ceilings 44 / 3,960",
        ],
        "diagnostics_required": [
            "the realized Perception completion-token distribution against the 640 cap and against the E41 bound (the digit-dense worst case 574 tokens), counts and quantiles only",
            "Perception note compliance with the bound, counted on the sealed responses with the SAME feature code as scripts/analysis/e21_e41_perception_note_trace_read.py (non-empty lines <= 5, words per line <= 20, 6-gram repetition share, window-transcript 4-gram re-emission against the E35 four-row direct arm): counts only, never text",
            "the Solver completion tokens per window beside E39b's (the answering node must stay near the direct arm's count)",
            "the number of REVISE / ACCEPT Planner routes and byte-identical second Solver drafts, beside E39b's",
            "every abort, refusal and recovery re-registration, with its cause",
        ],
        "scorer": {"runs": "NONE is read. The finalize may schedule the baseline's scorer stack once; this read quotes no score.",
                   "why": "n = 4 carries no quality information; the deliverable is the truncation mode, not a number."},
        "output": {"verdict_document": "docs/results/2026-09-2x-e21-native-window-e41-four-row-dry-run-read.md",
                   "prints_only_aggregates": "counts, role ids, reasons, booleans and hashes only",
                   "harness_admission": "NONE -- a base item admits no module"},
    }


def sub10_recipe() -> dict:
    cell = CELLS["sub10"]
    return {
        "schema": "saea-descriptive-structural-read-recipe-v1",
        "recipe_id": "e21-native-window-e41-sub10-descriptive-read-v1",
        "registered_at_utc": REGISTERED_AT,
        "title": "Item E41 sub10 re-read of the Earnings21+ConEC system form: descriptive structural read against the sealed E35 direct arm, bound per window",
        "cell_kind": "DESCRIPTIVE STRUCTURAL READ below every power floor (n = 10 calls, 342 windows); stage3_measurement form-proof, claims_benefit false.",
        "authority": {
            "item": "E41, rows 103 and 158; row 98 (the Earnings full-discovery calibration n >= 400 stays after the SLURP main line)",
            "attribution_method": "docs/results/2026-09-22-e21-native-window-e35-sub10-diagnosis.md section 0 ('Attribution method and its validation') and sections 1-5",
            "comparator_binding": f"{RD}/sub10-comparator-binding-v1.json",
        },
        "gate_before_any_read": "The E41 dry-run read holds R1-R3 and is committed BEFORE this cell is flipped; this read starts only after the single attempt's manifest is sealed COMPLETE.",
        "claim_boundary": "No effectiveness, superiority, generalization, admission or paper claim. WER is reported as the carrier's standard scorer, not as the agentic task; entity and numeric metrics are reported beside it. Every number is descriptive and development-grade (decisions 28, 86).",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "server": 0, "tokenizer": 0,
                     "scorer": "the ONE complete scoring job the flight's finalize runs over the complete manifest; the read itself runs none"},
        "run_ids": {"arm": cell["run"], "fit": cell["fit_run"]},
        "comparators": {
            "direct": {**DIRECT_SUB10, "role": "the bare-core comparator, bound per window by execution_unit_id; its sealed scores are read, never re-scored"},
            "e35_system": {**SYSTEM_SUB10, "role": "the same six-node form BEFORE v3.1 and E41 (episode scope, cap 1,024, Reviewer probe v1, Perception note v1): the structural contrast"},
        },
        "structural_readings": [
            {"id": "S1", "statement": "windows whose terminal_disposition names perception or reviewer with an abstention: TARGET ZERO (R1 at scale; E35 sealed 75 + 1)"},
            {"id": "S2", "statement": "windows delivering the empty string (delivery_text_sha256 = e3b0c442...): TARGET ZERO beyond the direct arm's own count (E35 system 76, E35 direct 1)"},
            {"id": "S3", "statement": "the Perception truncation rate (finish_reason 'length' at 640 over 342 Perception contacts): TARGET ZERO, reported with its count; the Reviewer truncation count beside it (E35 sealed Perception 75 / 342 and Reviewer 30 / 428 at 1,024)"},
            {"id": "S4", "statement": "contacts per window, role visits, Planner routes, byte-identical second Solver drafts, terminal reasons (finite_completion / revision_limit / none), against the E35 system arm's 4.67 contacts per window"},
            {"id": "S5", "statement": "Perception note compliance with the E41 bound over the 342 sealed notes, counted with scripts/analysis/e21_e41_perception_note_trace_read.py's feature code (lines, words per line, repetition share, window-transcript re-emission against the bound direct arm): counts only"},
        ],
        "scores_reported_descriptively": {
            "from": "the sealed E41 arm's own scores.json (one complete job) beside the sealed E35 direct arm's scores.json (never re-scored)",
            "carrier_standard_scorer": "asr-wer-whisper: corpus WER, S / D / I, per-call WER (Whisper-normalised, beside saea-scoring-v1)",
            "agentic_metrics": [
                "conec-entity-wer-official: per-entity-class WER (PERSON first, ORG, GPE, PRODUCT) -- a DEFINITION MIRROR of fstalign RecordTagWer with official_tool_run false; the official ConEC tool (revdotcom/fstalign, a C++/OpenFST binary) is NOT installed or runnable in this repository and is not run for this read; the label 'mirror' travels with every number",
                "numeric-value-accuracy-v1: accuracy, expected / matched / spurious numeric words, by kind",
                "semantic-high-impact-error-rate-v1: rate (advisory: the taxonomy's only HIGH trigger is negation)",
            ],
        },
        "per_window_attribution": {
            "method": "exactly the E35 diagnosis's: reference tokens via data.references.reference_tokens + reproduction.asr_wer_whisper.normalize_whisper_english (the sealed scorer's own normaliser); alignment path from rapidfuzz.distance.Levenshtein.opcodes; the reference partition into windows taken ONCE from the DIRECT arm's alignment and reused for both arms, so per-window deltas are on identical reference spans",
            "validation": "the recomputed edit distance per call must equal the sealed per-call edit distance on both arms (10 / 10) before any per-window number is reported; a mismatch stops the read",
            "tables": [
                "delivered-token / reference-word ratio per window, bucketed (0, < 0.25, 0.25-0.75, 0.75-1.25, >= 1.25), both arms",
                "per-window extra error mass (E41 errors minus direct errors on the same span): windows carrying 50 / 80 / 90 % of the positive mass and their delivery sources",
                "by delivery source (accepted Solver / terminal Solver / abstention), by terminal reason, by contacts per window: windows, extra errors per window, reference words per window",
                "which node's text was delivered, by hash equality of deliver_normaliser.input_sha256 against each contact's stripped response",
                "numeric shortfall by window class (the E35 diagnosis section 4 table)",
                "the same per-window table for the sealed E35 system arm beside it (sealed, recomputed from its own outputs)",
            ],
            "boundary": "reference text is loaded in memory for alignment only (the scorer's own normaliser); the read prints and persists counts, rates, ids and hashes, never reference, transcript or delivered text",
        },
        "what_is_not_here": "No paired estimator, no bootstrap CI as a claim, no margin, no bar, no admission, no frontier row: n = 10 calls cannot carry them (row 98 sequences the n >= 400 Earnings calibration after the SLURP main line).",
        "output": {"verdict_document": "docs/results/2026-09-2x-e21-native-window-e41-sub10-read.md",
                   "harness_admission": "NONE -- a base item admits no module"},
    }


def protocol_document(trace: dict, tokens: dict, base_commit: str) -> dict:
    pooled = trace["pooled"]
    return {
        "schema": "saea-e41-bounded-perception-protocol-v1",
        "protocol_id": "e21-native-window-e41-bounded-perception-protocol-v1",
        "item": "E41",
        "registered_at_utc": REGISTERED_AT,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree /home/chao/saea-worktrees/fable-e41, branch fable/e41, base commit {base_commit}",
        "hash_policy": "This shared document quotes NO composed config or protocol hash of either E41 cell (each cell's hashes live only in its own plan files), so flipping one cell never rewrites the other cell's plan documents through this file's sha256.",
        "authority": ("owner decisions 103 (E41 defined: a bounded Perception note with its own dry run before the sub10 re-read) "
                      "and 158 (E41 is unfinished Stage-2 engineering base: carry it out after COMP-1, on the E21 "
                      "geometry, a serving swap); 89 / 91 / 92 / 98 (Earnings on FlightRuntime, the E21 geometry, the "
                      "shared slice tree, the n >= 400 calibration after the SLURP main line); base lock v3.1 "
                      "(docs/results/2026-09-22-base-lock-v3.md section 5b)."),
        "question": "Does bounding the Perception note of the Earnings system form (a numbered list of at most 5 lines, at most 20 words each, never repeated, explicitly not a transcript) remove the Perception length-truncation mode that E35, E39 and E39b recorded, with nothing else moved?",
        "claim_surface": "Engineering structure only. No score, comparison, effectiveness or generalization claim.",
        "one_pin": {"path": PIN_PATH, "old": OLD_PROBE, "new": NEW_PROBE,
                    "new_sha256": tokens["instruction_files"]["new"]["sha256"], "old_sha256": tokens["instruction_files"]["old"]["sha256"]},
        "model_free_argument": {
            "receipt": f"{RD}/perception-trace-read-v1.json",
            "sealed_perception_contacts": pooled["perception_contacts"],
            "truncated": pooled["truncated"],
            "truncated_modes": pooled["truncated_modes"],
            "truncated_within_e41_bound": pooled["truncated_within_e41_bound"],
            "stopped_within_e41_bound": f"{pooled['stopped_within_e41_bound']} of {pooled['stopped']}",
            "worst_case_compliant_note_tokens": tokens["completion_side_bound"]["synthetic_compliant_notes"]["digit_dense_worst_case_compliant_note"]["tokens"],
            "cap": 640,
        },
        "cells": {key: {"cell_id": c["cell"], "experiment": c["experiment"], "run_id": c["run"], "attempt_id": c["attempt"],
                        "fit_run_id": c["fit_run"], "fit_attempt_id": c["fit_attempt"], "baseline_fragment": c["baseline"],
                        "dataset_fragment": c["dataset"], "model_fragment": MODEL, "policy": POLICY,
                        "campaign_plan": f"configs/campaign/{c['cell']}.json", "windows": c["windows"], "calls": c["calls"],
                        "decision_id": c["decision_id"], "decision_relpath": c["decision_relpath"],
                        "plans": [f"{RD}/{c['prefix']}-generation-plan-registered-v1.json", f"{RD}/{c['prefix']}-fit-plan-registered-v1.json"],
                        "analysis_recipe": f"{RD}/{c['prefix']}-analysis-recipe-v1.json"}
                  for key, c in CELLS.items()},
        "order": "The dry run flies first; the sub10 re-read is flipped and flown ONLY after the dry-run receipts read holds R1-R3 and is committed (row 103: 'its own dry run before the sub10 re-read').",
        "service": {"expected_session_id": SESSION, "attach_only": True, "no_child_start_stop": True, "slots": 4,
                    "slot_tokens": 24576, "max_completion_tokens": 1024, "decoder_only": True, "mmproj": "absent",
                    "swap": "the resident SLURP np4 session is stopped and the E21 session started before a chain runs (decision 91; scripts/flights/batch/serving_switch_to_e21.sh, serving_task_entry_e21.sh); the SLURP geometry returns after the seal; row 158 schedules E41 after COMP-1 so the SLURP line keeps the card"},
        "fit": {key: {"mode": "native_contact_fit", "run_id": c["fit_run"], "attempt_id": c["fit_attempt"],
                      "contact_cap": c["fit_cap"], "arithmetic": f"{c['windows']} x 11 x (1 speech packet + 3 endpoints) = {c['fit_cap']}",
                      "coordinate_fit": "must NOT be run, or the FIT row is double-charged"} for key, c in CELLS.items()},
        "accounting": {key: {"generation_calls_cap": c["calls_cap"], "fit_endpoint_calls_cap": c["fit_cap"],
                             "repeated_speech_audio_seconds_cap": c["speech_cap"], "gpu_hours_fit_inclusive": c["gpu"],
                             "official_complete_scoring_jobs": 1, "asr_calls": 0, "encoder_calls": 0, "paid_api_calls": 0,
                             "native_task_contract_calls_cap": 0, "plan_budget_is_run_cumulative": True,
                             "ceilings_are_not_targets": True} for key, c in CELLS.items()},
        "failure_policy": "Stop and preserve on the first failure: no automatic restart, replay, roster, graph, prompt, knowledge, geometry or cap change. At most ONE separately registered recovery per cell after a named cause; a second failure stops E41 and the fix is proven on a fresh four-row dry run.",
        "prepared_phase_supply_note": "NONE for either cell (item E38 path); --allow-output-change must never be passed.",
        "not_authorised": [
            "any flight before the decision receipt is minted and the cell flipped",
            "the sub10 flip before the dry-run read holds R1-R3",
            "any ASR, transcript, encoder, paid-API or Earnings-22 contact; FSD50K / AudioSet / ESC-50 are never consumed",
            "re-flying or re-scoring any sealed E35 / E39 / E39b arm",
            "any change beyond the one registered pin",
            "any effectiveness, superiority or generalization claim",
        ],
    }


def registered_facts(trace: dict, tokens: dict, diffs: dict, binding_sha: str, base_commit: str) -> dict:
    return {
        "_note": "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement block (keyed by run id). It quotes no composed / protocol hash of an E41 cell; those live in the plan files.",
        "schema": "saea-e41-registered-facts-v1",
        "registered_at_utc": REGISTERED_AT,
        "study_commit_at_registration": base_commit,
        "item": {"id": "E41", "definition": "row 103: a bounded Perception note (structured / length-constrained instruction) with its own dry run before the sub10 re-read of the Earnings system form",
                 "judgement": "row 158: unfinished Stage-2 engineering base; carry it out after COMP-1"},
        "one_pin": {"path": PIN_PATH, "old": OLD_PROBE, "new": NEW_PROBE, "instruction_files": tokens["instruction_files"]},
        "stage3_measurement": stage3_measurement(),
        "stage3_algorithm": STAGE3_ALGORITHM,
        "token_cost": {
            "receipt": f"{RD}/instruction-token-measurement-v1.json",
            "prompt_side_tokens": tokens["prompt_side_tokens"],
            "prompt_side_delta_per_perception_contact": tokens["prompt_side_delta_per_perception_contact"],
            "prompt_side_delta_per_flight": tokens["prompt_side_delta_per_flight"],
            "completion_side_bound": {k: v for k, v in tokens["completion_side_bound"].items() if k != "synthetic_compliant_notes"},
            "synthetic_compliant_note_tokens": {k: v["tokens"] for k, v in tokens["completion_side_bound"]["synthetic_compliant_notes"].items()},
        },
        "truncation_argument": {
            "receipt": f"{RD}/perception-trace-read-v1.json",
            "mode_rule": trace["mode_rule"],
            "pooled": trace["pooled"],
            "per_run": [{"label": r["label"], "run_id": r["run_id"], "caps": r["perception_caps"],
                         "perception_contacts": r["perception_contacts"], "truncated": r["truncated"]["count"],
                         "truncated_modes": r["truncated"]["modes"], "truncated_lines": r["truncated"]["lines"],
                         "truncated_loops": r["truncated_loops"], "stopped_reemit_ge_half_window": r["stopped"]["reemit_ge_half_window"],
                         "stopped": r["stopped"]["count"]} for r in trace["runs"]],
        },
        "composed_config_diff": {key: {"parent": d["parent"], "child": d["child"], "differing_leaf_paths": d["differing_leaf_paths"],
                                       "pins": d["pins"], "episode_config": d["episode_config"],
                                       "base_lock_v31_paths": sorted({r["path"] for r in d["rows"] if r["class"] == "base-lock-v3.1"}),
                                       "bookkeeping_paths": sorted({r["path"] for r in d["rows"] if r["class"] == "bookkeeping"})}
                                 for key, d in diffs.items()},
        "sub10_comparator_binding": {"relpath": f"{RD}/sub10-comparator-binding-v1.json", "sha256": binding_sha},
    }


def admission_draft(key: str, shas: dict, base_commit: str) -> dict:
    cell = CELLS[key]
    antecedents = {
        "preregistration": {"path": PREREG, "sha256": None},
        "readiness_readme": {"path": f"{RD}/README.md", "sha256": None},
        "protocol": {"path": f"{RD}/protocol-registered-v1.json", "sha256": shas["protocol-registered-v1.json"]},
        "registered_facts": {"path": f"{RD}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
        "analysis_recipe": {"path": f"{RD}/{cell['prefix']}-analysis-recipe-v1.json", "sha256": shas[f"{cell['prefix']}-analysis-recipe-v1.json"]},
        "perception_trace_read": {"path": f"{RD}/perception-trace-read-v1.json", "sha256": shas["perception-trace-read-v1.json"]},
        "token_measurement": {"path": f"{RD}/instruction-token-measurement-v1.json", "sha256": shas["instruction-token-measurement-v1.json"]},
        "bounded_instruction": {"path": f"configs/{NEW_PROBE}", "sha256": sha_file(REPO / "configs" / NEW_PROBE)},
        "owner_decisions": {"path": "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md", "sha256": None},
        "e39b_read": {"path": "docs/results/2026-09-23-e21-native-window-e39b-four-row-dry-run-read.md", "sha256": None},
        "e35_read": {"path": "docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md", "sha256": None},
        "registration_base_commit": base_commit,
    }
    if key == "sub10":
        antecedents["comparator_binding"] = {"path": f"{RD}/sub10-comparator-binding-v1.json", "sha256": shas["sub10-comparator-binding-v1.json"]}
        antecedents["dry_run_read"] = {"path": "docs/results/<the committed E41 dry-run read; root fills this path before minting>", "sha256": None}
    return {
        "_draft_note": (f"A DRAFT written by the registration agent for root to mint on the data root with "
                        f"scripts/flights/e41/e41_mint_receipt.py --which {key}, which sets status 'decided', stamps "
                        "recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It "
                        "authorises nothing while its status is not 'decided'."
                        + (" The sub10 receipt is minted ONLY after the E41 dry-run read holds R1-R3; the mint tool "
                           "refuses while the dry_run_read antecedent is a placeholder." if key == "sub10" else "")),
        "schema": "saea-campaign-decision-v1",
        "decision_id": cell["decision_id"],
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": [cell["run"], cell["fit_run"]],
        "cell_kind": f"Stage-2 engineering-base item E41, {cell['label']}: the Earnings21 + ConEC system form at base lock v3.1 with the bounded Perception note; label none (decision 101); form-proof, claims_benefit false",
        "decision": (f"Admit E41 {cell['label']}: the base lock v3.1 Earnings system form with one pin moved "
                     f"({PIN_PATH} {OLD_PROBE} -> {NEW_PROBE})."
                     + (" Receipts only (R1-R3; R3 = Perception truncation rate, target zero)." if key == "dry-run" else
                        " A descriptive structural read against the sealed E35 sub10 direct arm bound per window; no claim.")),
        "authorization_basis": "Owner decisions 103 and 158; 89 / 91 / 92 / 98; decision 77 (flights only through the batch driver); base lock v3.1.",
        "antecedents": antecedents,
        "service": {"expected_session_id": SESSION, "model_fragment": MODEL, "slots": 4, "slot_tokens": 24576,
                    "max_tokens": 1024, "no_child_start_stop": True,
                    "note": "the E21 geometry runs under the Windows Scheduled Task SAEA-Serving-E21 while this cell flies; the SLURP session is stopped for the duration and restarted afterwards (decision 91)"},
        "budget": {"arm": {"generation_calls_cap": cell["calls_cap"], "fit_endpoint_calls_cap": cell["fit_cap"],
                           "repeated_speech_audio_seconds_cap": cell["speech_cap"], "gpu_hours_fit_inclusive_cap": cell["gpu"],
                           "native_task_contract_calls_cap": 0, "official_complete_score_jobs": 1}},
        "claim_boundary": "No effectiveness, superiority or generalization claim; form-proof (claims_benefit false).",
        "failure_policy": "Stop and preserve on the first failure; one root-diagnosed recovery re-registration at most; the dry run flies first and the sub10 re-read only after its receipts read holds.",
        "not_authorized": ["any ASR, transcript, encoder or paid-API contact", "any test-split or Earnings22 contact",
                           "re-flying or re-scoring a sealed arm", "any Earnings optimisation cell", "any change beyond the one pin"],
    }


def readme(trace: dict, tokens: dict, diffs: dict, base_commit: str) -> str:
    pooled = trace["pooled"]
    tb = tokens["completion_side_bound"]
    synth = tb["synthetic_compliant_notes"]
    sub = next(r for r in trace["runs"] if r["label"] == "E35-sub10")
    loops = sub["truncated_loops"]
    lines = [
        "# Item E41: the bounded Perception note on the Earnings21 + ConEC system form (launch runbook)",
        "",
        f"Registered {DATE}, before any contact, in the worktree `/home/chao/saea-worktrees/fable-e41` (branch `fable/e41`,",
        f"base commit `{base_commit}`). Authority: owner decisions 103 (E41 defined) and 158 (E41 judged unfinished Stage-2",
        "engineering base: carry it out after COMP-1). Model-free registration: zero model, server, encoder and scorer contacts;",
        "one local vocab-only tokenizer process measured the token cost.",
        "",
        "**Question:** with nothing else moved, does bounding the Perception note remove the Perception length-truncation mode",
        "the E35 sub10 read (75 / 342 at 1,024), the E39 dry run (4 / 4 at 320) and the E39b dry run (2 / 4 at 640) recorded?",
        "**It does not ask** whether anything improves: no score, comparison or effectiveness claim is made by either cell.",
        "",
        "## The one pin",
        "",
        f"`{PIN_PATH}`: `{OLD_PROBE}` -> `{NEW_PROBE}`. The v2 note is a numbered list of at most 5 lines, at most 20 words",
        "per line, `N. KIND near S s: reading A or reading B` with KIND in NAME / NUMBER / BOUNDARY / MISSING and at most 4",
        "quoted spoken words per reading; never a repeated line; `1. NONE` when nothing is uncertain; and explicitly not a",
        "transcript (the Perception contact's system message is the Solver's task instruction, which orders a transcript).",
        "Everything else is the sealed E39b dry run's form (base lock v3.1): scope answering-node, caps 640 / 640, Reviewer",
        "probe v2, `deliver-latest-or-abstain`, `continue-without-answer`, the E21 geometry. Composed diff:",
        f"`composed-config-diff-v1.json` -- dry run vs E39b: {diffs['dry-run']['differing_leaf_paths']} differing leaves,",
        f"exactly one pin; sub10 vs the sealed E35 sub10 system arm: {diffs['sub10']['differing_leaf_paths']} differing leaves (the pin, the",
        "v3.1 leaves the dry runs proved, and bookkeeping).",
        "",
        "## Token cost (`instruction-token-measurement-v1.json`)",
        "",
        f"- Prompt side: the instruction grows {tokens['prompt_side_tokens']['old_instruction']} -> {tokens['prompt_side_tokens']['new_instruction']} tokens;",
        f"  as the wire renders it (with the native-episode limits) {tokens['prompt_side_tokens']['old_as_wire_user_turn']} -> {tokens['prompt_side_tokens']['new_as_wire_user_turn']},",
        f"  i.e. +{tokens['prompt_side_delta_per_perception_contact']} tokens per Perception contact (one per window): +{tokens['prompt_side_delta_per_flight']['four_row_dry_run']} on the dry run,",
        f"  +{tokens['prompt_side_delta_per_flight']['sub10_re_read']} on the sub10 re-read (E35 sub10 system prompt total 4,016,159).",
        f"- Completion side: a typical compliant note is {synth['typical_compliant_note']['tokens']} tokens; the digit-dense worst case",
        f"  (every reading four 12-character numerals) is {synth['digit_dense_worst_case_compliant_note']['tokens']} tokens, {tb['worst_case_headroom_tokens']} under the 640 cap;",
        f"  the ratio bound 5 x 20 x {trace['pooled']['tokens_per_whitespace_word']['max']} (the maximum tokens per word observed) is {tb['ratio_bound_tokens']}.",
        "  The v1 notes ran median 324 / p95 821 tokens (E35 sub10).",
        "",
        "## The model-free truncation argument (`perception-trace-read-v1.json`, counts only)",
        "",
        f"All {pooled['perception_contacts']} sealed Perception contacts of the Earnings system form (E35 sub10, E35 four-row, E39,",
        f"E39b) were joined to their wire finish_reason; {pooled['truncated']} were length-truncated. Mode by a fixed rule:",
        f"{json.dumps(pooled['truncated_modes'])}. **None of the {pooled['truncated']} truncated notes fits the E41 bound**",
        f"({pooled['truncated_within_e41_bound']} within), and none of the {pooled['stopped']} naturally stopped v1 notes does either",
        f"({pooled['stopped_within_e41_bound']}): the v1 instruction never produced a bounded note, so v2 is a real change of form.",
        "",
        f"- LOOP (the 1,024 mode, {sub['truncated']['modes'].get('LOOP', 0)} of {sub['truncated']['count']} on E35 sub10): the repeated unit has a period of median",
        f"  {loops['loop_period_words']['p50']} words (about one list item) repeated to the cap -- an open list with no terminator.",
        "  v2 closes the list (numbered, at most 5 lines, 'Never repeat a line', 'Stop after line 5'). Residual risk, named:",
        f"  {loops['onset_within_100_words']} of {loops['count']} loops began within the first 100 words, so length alone does not",
        "  exclude a loop; the form does, if the core complies -- which the dry run's R3 measures.",
        "- ENUMERATION (the 320 / 640 mode): 14-64 lines at 1,024, 6-10 at 320, 19-21 at 640. v2: at most 5 lines.",
        "- TRANSCRIPT: the note re-emits at least half of the window's direct-arm transcript 4-grams. v2 forbids",
        "  transcription and caps quoting at 4 words per reading; on E35 sub10 36 of 267 STOPPED v1 notes also re-emitted at",
        "  least half the window -- transcript tokens in a NON-answering node's intermediate state, which the 2026-09-06",
        "  owner ruling (no transcript or ASR state; only the Solver's draft answer, the carrier's deliverable, is a",
        "  transcript) does not admit; v2 removes them.",
        "- PROSE: long free text. v2: at most 20 words per line.",
        "",
        f"A note that obeys v2 is at most {synth['digit_dense_worst_case_compliant_note']['tokens']} tokens, so it cannot reach the 640 cap: under v2 every",
        "length-truncated Perception contact is a NON-compliant note by construction. The argument is conditional on",
        "compliance; the dry run's R3 (Perception truncation rate, target zero) is the measurement of compliance.",
        "",
        "## The two cells (both HELD)",
        "",
        "| item | dry run | sub10 re-read |",
        "| --- | --- | --- |",
    ]
    d, s = CELLS["dry-run"], CELLS["sub10"]
    for label, a, b in (
        ("cell", d["cell"], s["cell"]),
        ("experiment", d["experiment"], s["experiment"]),
        ("baseline", d["baseline"], s["baseline"]),
        ("dataset", d["dataset"], s["dataset"]),
        ("generation run", f"{d['run']} ({d['calls_cap']} calls)", f"{s['run']} ({s['calls_cap']} calls)"),
        ("fit run", f"{d['fit_run']} ({d['fit_cap']})", f"{s['fit_run']} ({s['fit_cap']})"),
        ("repeated speech s / GPU-h", f"{d['speech_cap']} / {d['gpu']}", f"{s['speech_cap']} / {s['gpu']}"),
        ("roster", "4 windows of call 4320211 (E35 / E39 / E39b roster)", "10 calls, 342 windows (the E35 sub10 roster)"),
        ("comparator", "sealed E39b dry run (receipts) + E35 four-row direct", "sealed E35 sub10 direct arm, bound per window (+ E35 system arm, structural)"),
        ("read", "receipts only: R1, R2, R3 (Perception truncation rate, target zero)", "descriptive structural read S1-S5 + standard scorer and agentic metrics, no claim"),
        ("stage3_measurement", "form-proof, rows 1, claims_benefit false", "form-proof, rows 10, claims_benefit false"),
        ("decision", f"{d['decision_id']}", f"{s['decision_id']} (minted only after the dry-run read)"),
    ):
        lines.append(f"| {label} | `{a}` | `{b}` |" if label in ("cell", "experiment", "baseline", "dataset", "decision") else f"| {label} | {a} | {b} |")
    lines += [
        "",
        "Both cells declare `native_episode.finite_completion_policy = deliver-latest-or-abstain` and",
        "`native_episode.react_exhaustion_policy = continue-without-answer` (`scripts/checks/finite_completion_policy_check.py`),",
        "`finite_completion_scope = answering-node`, and `stage3_algorithm` `none` with its reason in the experiment fragment.",
        "",
        "## Mint, re-pin, switch, fly (root)",
        "",
        "1. Countersign the DRAFT exposure rows of the E41 section of `docs/exposure-ledger.md`.",
        "2. Mint the dry-run receipt: `python scripts/flights/e41/e41_mint_receipt.py --which dry-run`.",
        "3. Flip: `bash scripts/flights/e41/e41_flip_dryrun.sh` (the per-cell `repin_loop_generic.sh` cycle; records",
        "   `/home/chao/e41-dryrun-flight-commit.txt`).",
        "4. After COMP-1 seals (row 158): stop the SLURP np4 session (`scripts/flights/batch/serving_switch_to_e21.sh`), start",
        "   the E21 session (`SAEA-Serving-E21` -> `serving_task_entry_e21.sh`), then run",
        "   `bash scripts/flights/e41/batch_chain_e41_dryrun.sh` (refuses unless the E21 session is resident and the SLURP one is not).",
        "5. Read the dry run by `dry-run-analysis-recipe-v1.json`. Only on PASS: fill the sub10 draft's `dry_run_read`",
        "   antecedent, mint `--which sub10`, flip with `e41_flip_sub10.sh`, fly with `batch_chain_e41_sub10.sh` (same",
        "   serving preconditions), read by `sub10-analysis-recipe-v1.json`. Return the SLURP geometry after each seal.",
        "",
        "## Files",
        "",
        "`protocol-registered-v1.json` (shared; quotes no cell hash), `dry-run-*` and `sub10-*` plans and recipes, `registered-facts-v1.json`",
        "(stage3_measurement keyed by run id), `composed-config-diff-v1.json`, `perception-trace-read-v1.json`,",
        "`instruction-token-measurement-v1.json`, `sub10-comparator-binding-v1.json`, two root-admission drafts. Proofs:",
        "`tests/unit/test_e41_bounded_perception_note.py`. Generator: `scripts/flights/write_e21_e41_registration.py`.",
        "",
        "## Not authorised by this package",
        "",
        "No flight before the receipt is minted and the cell flipped; the sub10 flip never before the dry-run read holds; no",
        "contact by this registration; no re-flying or re-scoring of a sealed arm; no change beyond the one pin; no claim.",
        "",
    ]
    return "\n".join(lines)


def preregistration(trace: dict, tokens: dict, base_commit: str) -> str:
    block = {"stage3_measurement": stage3_measurement()}
    pooled = trace["pooled"]
    return "\n".join([
        "# Item E41 preregistration: the bounded Perception note -- four-row dry run, then the sub10 re-read",
        "",
        f"Registered {DATE} before any contact by the E41 registration agent (Claude Opus 5.5) in the worktree",
        f"`/home/chao/saea-worktrees/fable-e41` (branch `fable/e41`, base commit `{base_commit}`). DRAFT: root countersignature",
        "pending. **Development receipts only.**",
        "",
        "## 1. Why",
        "",
        "E35 (`docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`) root-caused the Earnings system form's",
        "HARM to E13's episode-wide scope voiding 76 windows after a length-truncated Perception contact; E39 / E39b repaired",
        "the scope and the Reviewer cap and both still failed R3 on the Perception node (4 / 4 at 320, 2 / 4 at 640); row 103",
        "defined E41 and row 158 ordered it carried out as unfinished Stage-2 base.",
        "",
        "## 2. The factor",
        "",
        f"ONE pin, `{PIN_PATH}`: `{OLD_PROBE}` -> `{NEW_PROBE}` (sha256 `{tokens['instruction_files']['new']['sha256']}`).",
        f"Token cost: +{tokens['prompt_side_delta_per_perception_contact']} prompt tokens per Perception contact; a compliant note is at most",
        f"{tokens['completion_side_bound']['synthetic_compliant_notes']['digit_dense_worst_case_compliant_note']['tokens']} tokens (digit-dense worst case) against the 640 cap.",
        f"Of {pooled['perception_contacts']} sealed Perception notes, {pooled['truncated']} truncated, 0 within the bound (modes",
        f"{json.dumps(pooled['truncated_modes'])}).",
        "",
        "## 3. Decision rules (fixed here, before contact)",
        "",
        "**Dry run** (`dry-run-analysis-recipe-v1.json`): R1 zero auxiliary-node abstentions; R2 4 / 4 non-empty deliveries;",
        "R3 the Perception truncation rate at 640, reported with its count, TARGET ZERO (the Reviewer count beside it). PASS iff",
        "R1 and R2 hold and zero Perception or Reviewer contacts truncate. A non-zero Perception count FAILS E41 with the",
        "truncated note's structure named; at most one recovery re-registration.",
        "",
        "**Sub10 re-read** (`sub10-analysis-recipe-v1.json`), flipped only after the dry run PASSES: a descriptive structural",
        "read S1-S5 (voided windows, empty deliveries, Perception truncation rate, contacts and routes, note compliance) with",
        "the carrier's standard scorer (Whisper-normalised corpus WER) and the agentic metrics (ConEC entity WER mirror with",
        "official_tool_run false -- the official fstalign tool is not runnable here -- numeric-value accuracy) reported beside",
        "the sealed E35 sub10 direct arm, bound per window, with the E35 diagnosis's per-window attribution. No claim.",
        "",
        "## 4. Measurement declaration (the canonical copy is `registered-facts-v1.json`)",
        "",
        "```json",
        json.dumps(block, indent=2),
        "```",
        "",
        "`stage3_algorithm` is `none` in both experiment fragments: E41 carries no training-free RL operator.",
        "",
        "## 5. What is not claimed",
        "",
        "No score, WER, entity, numeric or semantic-error claim from the dry run; no effectiveness, superiority, comparison or",
        "generalization claim from either cell (n = 1 and 10 calls, below every floor; row 98 keeps the n >= 400 Earnings",
        "calibration after the SLURP main line). No transcript, reference or delivered text is printed or persisted by any read.",
        "",
        "## 6. Budgets and failure rule",
        "",
        "Dry run: 44 calls / 176 fit endpoints / 3,960 repeated speech seconds / 0.5 GPU-h. Sub10: 3,762 / 15,048 / 334,477 /",
        "12.0. Ceilings, never targets, run-cumulative per run id; zero ASR, encoder, paid-API and task-contract calls. First",
        "failure stops and preserves; at most one separately registered recovery per cell.",
        "",
        "## 7. Registration state",
        "",
        "Both cells HELD. Runbook: `docs/readiness/2026-09-27-e21-native-window-e41-v1/README.md`.",
        "",
    ])


def ledger_section(idents: dict, plan_shas: dict, trace_sha: str, token_sha: str, tokens: dict, trace: dict, base_commit: str) -> str:
    model = ("Frozen Q4_K_M decoder-only (q4km-e21-native-window-packets-cddb000c-np4-max1024-v1): c98304, np4, max1024, no "
             "mmproj; pinned e21-cddb000c-dr-full-gpu-v1 speech-feature packets; NO native tool authority; the six-node "
             "native episode at base lock v3.1 (answering-node scope, Perception / Reviewer caps 640 / 640, Reviewer probe "
             "v2) with item E41's bounded Perception note (probes/e21_native_window_system_perception_v2.txt)")
    inherited = {
        "dry-run": ("These four windows of call 4320211 are already exposed by the sealed E35 four-row pair, the E39 and E39b "
                    "dry runs and, before them, the OBS-path current-executor four-row proof. No new population, no fresh "
                    "roster, no gold, reference transcript or new knowledge read. Prior exposure inherited in full."),
        "sub10": ("These 342 windows of ten seeded discovery calls are already exposed by the sealed E35 sub10 pair "
                  "(SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1, SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1 and its FIT row) and "
                  "by the earlier full-44 E21 cells. No new population, no fresh roster, no gold or new knowledge read at "
                  "runtime. Prior exposure inherited in full."),
    }
    split = {"dry-run": "earnings21-original discovery four native windows of call 4320211 (construction stratum)",
             "sub10": "earnings21-original discovery sub10: 10 seeded discovery calls, 342 native windows"}
    rows = []
    for key, cell in CELLS.items():
        ident = idents[key]
        for kind in ("generation", "fit"):
            run = cell["run"] if kind == "generation" else cell["fit_run"]
            calls = cell["calls_cap"] if kind == "generation" else cell["fit_cap"]
            scope = (f"Item E41 (owner decisions 103 and 158), {cell['label']}: "
                     + ("the generation pass" if kind == "generation" else "FIT spend identity, request envelopes only, no generation")
                     + " of the Earnings21 + ConEC six-node system form at base lock v3.1 with ONE pin moved (the bounded Perception note). "
                     + ("Receipts only (R1-R3; R3 = Perception truncation rate, target zero)." if key == "dry-run" else
                        "A descriptive structural read against the sealed E35 sub10 direct arm bound per window; form-proof, claims_benefit false.")
                     + " No score, effectiveness, comparison or generalization claim.")
            plan = f"{RD}/{cell['prefix']}-{kind}-plan-registered-v1.json"
            notes = (f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {DATE} at study commit {base_commit} by the "
                     "E41 registration agent (worktree /home/chao/saea-worktrees/fable-e41, branch fable/e41). This "
                     f"registration performs no contact and authorises none. Plan SHA256 {plan_shas[plan]}; attempt "
                     f"{cell['attempt'] if kind == 'generation' else cell['fit_attempt']}. Protocol hash {ident.protocol_hash}; composed config "
                     f"{ident.config_hash}; expected session {SESSION} (attach only, never spawn or stop). READINESS HELD: root "
                     f"mints {cell['decision_relpath']} (decision id {cell['decision_id']}) from the package's {cell['draft']} "
                     f"with the two eligible run ids {cell['run']}, {cell['fit_run']}, then re-pins with scripts/flights/e41/"
                     f"e41_flip_{'dryrun' if key == 'dry-run' else 'sub10'}.sh; every hash in this row moves at the flip and the "
                     f"re-pin tool rewrites it. ONE PIN: {PIN_PATH} {OLD_PROBE} -> {NEW_PROBE}."
                     + (" FLIES ONLY AFTER the E41 dry-run read holds R1-R3." if key == "sub10" else ""))
            rows.append([REGISTERED_AT, run, "bounded-discovery-probe", scope, model, split[key], "discovery",
                         ident.split_identity_hash, "no", str(calls), str(cell["speech_cap"]), str(cell["gpu"]),
                         inherited[key], plan, notes])
    pooled = trace["pooled"]
    modes_text = ", ".join(f"{k} {v}" for k, v in pooled["truncated_modes"].items())
    rows.append([
        DATE, "SAEA-E21-E41-PERCEPTION-NOTE-TRACE-READ-V1", "model-free-check",
        ("Read every sealed Perception contact of the Earnings system form (E35 sub10 and four-row, E39, E39b) for its "
         "wire finish_reason and the STRUCTURE of its note (counts only), bind the sealed E35 sub10 direct comparator per "
         "window (ids and hashes), and measure the E41 instruction's token cost with the local vocab-only tokenizer. Zero "
         "model, server, encoder, embedder, scorer, network, GPU and paid-API contacts; ports 8080 / 8081 untouched."),
        f"no model or tool contact; local vocab-only llama-tokenize process ({tokens['tokenizer']['invocations']} invocations) over committed and synthetic text; read-only sealed traces and outputs",
        "earnings21-original discovery: the sealed E35 sub10 (342 windows) and four-row (4 windows) traces; ids, counts and hashes only",
        "discovery", "744c4b2e2d2eece3b05c68089c02000e38c96d5c62db8055d9c421fd509a8f61", "no", "0", "0", "0",
        "No new speech exposure: no speech byte is read; the sealed traces read were already exposed by the arms that sealed them. Prior exposure inherited in full.",
        f"{RD}/perception-trace-read-v1.json",
        (f"REGISTERED WITH ITS RESULT (DRAFT, root countersignature pending) {DATE} at study commit {base_commit}: a "
         "model-free read of already-sealed bytes that ran before this row was written, recorded so the facts the one "
         "pin rests on are on the ledger. "
         f"Receipt {RD}/perception-trace-read-v1.json SHA256 {trace_sha}; token receipt {RD}/instruction-token-measurement-v1.json "
         f"SHA256 {token_sha}; script scripts/analysis/e21_e41_perception_note_trace_read.py. Measured: {pooled['perception_contacts']} "
         f"sealed Perception contacts, {pooled['truncated']} length-truncated, modes {modes_text}, "
         f"0 within the E41 bound; prompt +{tokens['prompt_side_delta_per_perception_contact']} tokens per Perception contact; "
         f"compliant-note worst case {tokens['completion_side_bound']['synthetic_compliant_notes']['digit_dense_worst_case_compliant_note']['tokens']} tokens against the 640 cap. "
         "It constructs no ExecutionPlan, reserves no contact, re-pins no committed config and authorises nothing."),
    ])
    for row in rows:
        for cell_text in row:
            assert "|" not in cell_text, cell_text[:80]
            assert "\n" not in cell_text
    header = ("| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
              "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |")
    sep = "| " + " | ".join(["---"] * 15) + " |"
    body = "\n".join("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join([
        "",
        "## Item E41: the bounded Perception note on the Earnings21 + ConEC system form -- the four-row dry run, the sub10 re-read and the model-free trace read (DRAFT, root countersignature pending)",
        "",
        "Four unconsumed flight rows -- the dry run, the sub10 re-read and their two FIT spend identities -- plus one model-free "
        "row for the sealed-trace read, the per-window comparator binding and the token measurement. Owner decisions 103 and "
        "158. None of these rows is countersigned and none authorises a contact.",
        "",
        header, sep, body, "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--skip-ledger", action="store_true")
    args = parser.parse_args()
    pkg = REPO / RD
    trace = json.loads(rd(pkg / "perception-trace-read-v1.json"))
    tokens = json.loads(rd(pkg / "instruction-token-measurement-v1.json"))

    fragments = derive_fragments()
    write_fragments(fragments)
    diffs = composed_diffs()
    idents = {key: diffs[key].pop("_identity") for key in diffs}
    for key, d in diffs.items():
        assert [p["path"] for p in d["pins"]] == [PIN_PATH], (key, d["pins"])
        child = d["episode_config"]["child"]
        assert child["finite_completion_scope"] == "answering-node"
        assert child["role_completion_caps"] == {"perception": 640, "reviewer": 640}
        assert child["finite_completion_policy"] == "deliver-latest-or-abstain"
        assert child["react_exhaustion_policy"] == "continue-without-answer"

    shas = {}
    shas["composed-config-diff-v1.json"] = dump(pkg / "composed-config-diff-v1.json", {
        "schema": "saea-e41-composed-config-diff-v1", "registered_at_utc": REGISTERED_AT,
        "method": "core.flight.repin.compute_cell_identity + core.config.compose over the committed fragments at registration (readiness HELD, no decision requirement); every composed leaf compared by dotted path; a string longer than 160 characters is shown by length and sha256",
        "classification": {"pin": [PIN_PATH], "base-lock-v3.1": list(V31_PATHS),
                           "base-lock-v3.1_note": "the leaves the E39 / E39b dry runs proved and base lock v3.1 (decision 103) carries into every Earnings native cell; they differ only in the sub10 cell's diff, whose parent is the PRE-v3.1 E35 sub10 system arm, and never in the dry run's diff against E39b",
                           "bookkeeping": "every other differing leaf: run / attempt / fit / episode ids, experiment ids and dates, the one-arm execution-plan ceilings (sub10: the E35 experiment carried the PAIR total), service_session, prose (purpose, what_this_is, notes), readiness blocks, the decision-101 label; the sub10 diff also lists the E35 experiment's second cell (the direct arm, cells[0]) as removed and its system cell re-identified, because the E35 experiment fragment declared both arms"},
        "diffs": diffs,
    }, indent=1)
    binding = comparator_binding(args.data_root)
    shas["sub10-comparator-binding-v1.json"] = dump(pkg / "sub10-comparator-binding-v1.json", binding, indent=1)
    shas["protocol-registered-v1.json"] = dump(pkg / "protocol-registered-v1.json", protocol_document(trace, tokens, args.base_commit))
    shas["dry-run-analysis-recipe-v1.json"] = dump(pkg / "dry-run-analysis-recipe-v1.json", dry_run_recipe())
    shas["sub10-analysis-recipe-v1.json"] = dump(pkg / "sub10-analysis-recipe-v1.json", sub10_recipe())
    plan_shas = {}
    for key, cell in CELLS.items():
        for kind in ("generation", "fit"):
            rel = f"{RD}/{cell['prefix']}-{kind}-plan-registered-v1.json"
            plan_shas[rel] = dump(REPO / rel, plan_document(key, kind, idents[key], shas["protocol-registered-v1.json"], args.base_commit))
    shas["registered-facts-v1.json"] = dump(pkg / "registered-facts-v1.json",
                                            registered_facts(trace, tokens, diffs, shas["sub10-comparator-binding-v1.json"], args.base_commit), indent=1)
    shas["perception-trace-read-v1.json"] = sha_file(pkg / "perception-trace-read-v1.json")
    shas["instruction-token-measurement-v1.json"] = sha_file(pkg / "instruction-token-measurement-v1.json")
    for key, cell in CELLS.items():
        dump(pkg / cell["draft"], admission_draft(key, shas, args.base_commit))
    write_text(pkg / "README.md", readme(trace, tokens, diffs, args.base_commit))
    write_text(REPO / PREREG, preregistration(trace, tokens, args.base_commit))

    ledger_path = REPO / LEDGER
    ledger = rd(ledger_path)
    if not args.skip_ledger:
        if CELLS["dry-run"]["run"] in ledger:
            raise SystemExit("the E41 ledger section already exists; refusing to append twice (use --skip-ledger)")
        section = ledger_section(idents, plan_shas, shas["perception-trace-read-v1.json"],
                                 shas["instruction-token-measurement-v1.json"], tokens, trace, args.base_commit)
        io.open(ledger_path, "w", encoding="utf-8", newline="").write(ledger.rstrip("\n") + "\n" + section)
    print(json.dumps({
        "cells": {k: {"run": CELLS[k]["run"], "config_hash": idents[k].config_hash, "protocol_hash": idents[k].protocol_hash,
                      "differing_leaves": diffs[k]["differing_leaf_paths"],
                      "bookkeeping_paths": sorted({r["path"] for r in diffs[k]["rows"] if r["class"] == "bookkeeping"})}
                  for k in CELLS},
        "plans": plan_shas, "package_shas": shas,
        "binding": {"windows": len(binding["windows"]), "e35_abstained": binding["e35_system_arm"]["abstained_windows"],
                    "direct_empty": binding["direct_empty_windows"]},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
