#!/usr/bin/env python3
"""Write the TEST-SAMPLE milestone registration package of COMP-1b (owner decisions 151 and 202)
from the committed configs ``derive_slurp_comp1b_testsample_cells.py`` wrote.

Reads the two milestone cells (MILESTONE-00-PLAN, the comparator; MILESTONE-01, COMP-1b) and
their DEV-2000-ADDED sources (the sealed DEV plan arm; cell A2's arm), recomposes every hash and
PROVES from the composed configs (``core.config.compose``):

* ``plan_vs_dev_plan`` / ``arm_vs_a2_arm``: each milestone cell differs from its DEV source by
  EXACTLY the roster-bound paths (dataset view, roster receipt, packet promotion receipt, the
  roster's own query vectors, alias and agreement table, row-scaled budgets), the role-bound
  paths the ``final-report`` split role forces (split role, owner-allowance pin, the TEST scorer
  sibling, the one-attempt failure policy), per-flight bookkeeping and the experiment fragment's
  own block -- ``anything_else`` is empty or this writer refuses;
* ``composition_square``: the arm-vs-comparator delta on the sample is, path for path and value
  for value outside the roster-bound agreement-table pin, cell A2's arm-vs-DEV-plan delta.

It also checks the signed allowance: both read run ids are among its ``read_run_ids``; the two
FIT run ids are NOT among its ``permitted_run_ids`` and the package says so (a successor
allowance is required before the flip).

It writes the package documents (registered facts with the CANONICAL ``stage3_measurement``,
protocol, four plan documents, the analysis recipe, a draft decision receipt, README and
preregistration) and, with ``--append-ledger``, five DRAFT exposure rows (MILESTONE-00-PLAN, its
FIT, MILESTONE-01, its FIT, READ) in a new ledger section.

AMENDMENTS CARRIED FORWARD. A re-run of this writer (e.g. after the derive script pins the
sample-preparation artifacts, ``--data-root``) must not lose what landed in the package after the
first registration. It reads the COMMITTED package before overwriting it and carries forward,
verbatim: the expectation re-declaration from the A2 read (``redeclared_from_a2_read`` and the
``redeclaration`` block, e36bee27f; the arm's ``expected_effect_pp`` / ``expected_effect_status``
follow it), the post-stratification ruling (``post_stratification_read`` and the report-form
weightings in the facts, the recipe's ``strata_source`` / ``post_stratification``, and the README /
preregistration sections, 06c86ff2d). The blockers and the composition wording follow the
current pin state; ``sample_preparation_pins`` in the facts lists every real sample-preparation pin.

Config and receipt-pinned bytes alone: no contact of any kind, no media, no gold; flips nothing,
mints nothing, countersigns nothing.
"""

from __future__ import annotations

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
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

CELLS = {
    "arm": "slurp-native-stage3-comp1b-testsample-v1",
    "plan": "slurp-native-stage3-plan-testsample-milestone00-v1",
}
SOURCES = {
    "arm": "slurp-native-stage3-comp1b-dev2000-added-v1",
    "plan": "slurp-native-default-plan-dev2000-added-v1",
}
A2_PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1"
A2_ARM_RUN = "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1"
A2_READ_RUN = "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
COMP1B_READ_NOTE = "docs/results/2026-09-29-slurp-comp1b-fold-a-read.md"
DERIVE_SCRIPT = "scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py"
ALLOWANCE = "docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json"  # owner decision 207: the signed successor of the decision-151 allowance v1
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
DESIGN_NOTE = "docs/readiness/2026-09-27-slurp-test-sample-design-v1.md"
PREP_NOTE = "docs/readiness/2026-09-27-slurp-test-sample-preparations-v1.md"
PROTOCOL_DRAFT = "docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1b-testsample-v1.json"
PACKAGE_NAME = "slurp-stage3-comp1b-testsample-v1"
DECISION_ID = "slurp-stage3-comp1b-testsample-milestone-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-READ-V1"
ANALYSIS_ROOT = f"analysis/{READ_RUN}"
READ_DRIVER = "scripts/flights/comp1/comp1b_testsample_read.sh"
LEDGER = "docs/exposure-ledger.md"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-test"
ROSTER_ID = "SLURP-TEST-SAMPLE-3010-V1"
ROWS = 3010
PROMPTS = 682
ZERO = "0" * 64

#: The DEV-2000-ADDED own null (instrument section 2d, row 'cross-flight A/A, DEV-2000-ADDED', the
#: B6 pair), measured at 1,000 recordings / 913 prompts. The sample has NO own null: the design's
#: fallback is this null scaled by sqrt(n) -- conservatively at the PROMPT level (rho = 1, the
#: test-sample design note section 4: "Sample paired h 1.33"), with the recording-level scaling
#: beside it. FLAGGED: a borrowed, scaled null, not a measured one.
DEV_NULL = {"h_intent": 1.1520, "h_slu": 1.2525, "n_recordings": 1000, "n_prompts": 913,
            "source": INSTRUMENT + " section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"}


def scaled_null() -> dict:
    by_prompt = math.sqrt(DEV_NULL["n_prompts"] / PROMPTS)
    by_recording = math.sqrt(DEV_NULL["n_recordings"] / ROWS)
    return {
        "h_intent": round(DEV_NULL["h_intent"] * by_prompt, 4),
        "h_slu": round(DEV_NULL["h_slu"] * by_prompt, 4),
        "h_intent_recording_scaled": round(DEV_NULL["h_intent"] * by_recording, 4),
        "h_slu_recording_scaled": round(DEV_NULL["h_slu"] * by_recording, 4),
        "n": ROWS,
        "n_prompts": PROMPTS,
        "kind": "FALLBACK-SCALED-NOT-MEASURED",
        "flag": (
            "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 (no A/A pair has flown on it, and the allowance "
            "names no second PLAN read id that could measure one). Declared guard = the DEV-2000-ADDED own null "
            "scaled by sqrt(913 / 682) at the PROMPT level (rho = 1, conservative: every recording of a prompt "
            "moves together; design note section 4 'Sample paired h 1.33'). The recording-level scaling "
            "sqrt(1000 / 3010) is given beside it and is the OPTIMISTIC bound; the read reports both."
        ),
        "source": DEV_NULL["source"] + "; scaling: " + DESIGN_NOTE + " section 4",
    }


BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
ROSTER_BOUND = (
    "audio_seconds_total", "count", "d1_manifest_sha256", "d1_media_supplement", "d1_media_supplement_sha256",
    "items", "runtime_view_sha256", "seed", "source_binding_sha256", "split_id", "split_identity_hash",
    "split_name", "population.", "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.",
    f"{BOUNDARY}.agreement_source.relpath", f"{BOUNDARY}.agreement_source.sha256",
    f"{BOUNDARY}.agreement_source.tool_contact_ledger_row",
    "preparation_source_receipts", "execution_plan.planned_gpu_hours", "execution_plan.planned_model_calls",
    "execution_plan.planned_speech_audio_seconds", "family_budget.", "generation_budget.",
    "native_contact_fit.contact_cap", "what_the_train_exemplars_store_is",
)
ROLE_BOUND = ("split_role", "execution_plan.split_role", "owner_allowance.", "scorers", "failure_policy")
BOOKKEEPING = ("native_contact_fit.run_id", "native_contact_fit.attempt_id", "prepared_phase_supply.", "what_this_is")
EXPERIMENT_BLOCK = ("cells", "date", "experiment_id", "purpose", "stage3_algorithm.")
COMPOSITION_FACTORS = (f"{BOUNDARY}.k", f"{BOUNDARY}.rank_weights.w_agree", f"{BOUNDARY}.agreement_source.",
                       f"{BOUNDARY}.facet_source.")


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def _matches(key: str, patterns) -> bool:
    return any(key == p or (p.endswith(".") and key.startswith(p)) for p in patterns)


def classify(a_values: dict, b_values: dict) -> dict:
    a, b = flatten(a_values), flatten(b_values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    out = {"roster_bound": [], "role_bound": [], "bookkeeping": [], "experiment_fragment_own_block": [],
           "composition_factor": [], "anything_else": []}
    for key in changed:
        if _matches(key, ROSTER_BOUND):
            out["roster_bound"].append(key)
        elif _matches(key, ROLE_BOUND):
            out["role_bound"].append(key)
        elif _matches(key, BOOKKEEPING):
            out["bookkeeping"].append(key)
        elif _matches(key, EXPERIMENT_BLOCK):
            out["experiment_fragment_own_block"].append(key)
        elif _matches(key, COMPOSITION_FACTORS):
            out["composition_factor"].append(key)
        else:
            out["anything_else"].append(key)
    return out


def composed_of(experiment: str):
    document = json.loads(rd(f"configs/experiment/{experiment}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def _prior_json(path: str) -> dict:
    return json.loads(rd(path)) if os.path.isfile(path) else {}


def _prior_section(path: str, start: str, end: str) -> str:
    """The committed text from ``start`` up to (not including) ``end``, or '' when absent."""

    if not os.path.isfile(path):
        return ""
    text = rd(path)
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"{path}: carried section {start!r} has no end marker {end!r}")
    return text[i:j]


def _is_sample_preparation(relpath: str) -> bool:
    return relpath != ROSTER_RECEIPT and ("TEST-SAMPLE-3010" in relpath or "test-sample-3010" in relpath)


def ledger_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--expected-effect-pp", required=True, type=float,
                        help="A2's own declared number (3.8); root re-declares from the A2 read before the flip")
    parser.add_argument("--branch", default="fable/milestoneprep")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-milestoneprep")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    expected = round(args.expected_effect_pp, 2)

    # ---- amendments carried forward from the committed package (see the module docstring) -----
    prior_facts = _prior_json(package + "/registered-facts-v1.json")
    prior_recipe = _prior_json(package + "/analysis-recipe-v1.json")
    redeclaration = prior_facts.get("redeclaration") if prior_facts.get("redeclared_from_a2_read") is True else None
    if prior_facts.get("redeclared_from_a2_read") is True and not redeclaration:
        raise SystemExit("the committed facts read redeclared_from_a2_read true without a redeclaration block")
    readme_post_strat = _prior_section(package + "/README.md", "**Post-stratification: inside the official scorer",
                                       "**Blockers before the flip.**")
    prereg_post_strat = _prior_section(prereg, "## Post-stratification: inside the official scorer", "## Blockers before the flip")

    # ---- the allowance -----------------------------------------------------------------------
    allowance = json.loads(rd(ALLOWANCE))
    if allowance.get("status") != "authorised":
        raise SystemExit("the sample allowance is not authorised")
    allowance_sha = sha_file(ALLOWANCE)

    # ---- identities --------------------------------------------------------------------------
    ids: dict[str, dict] = {}
    composed: dict[str, object] = {}
    documents: dict[str, dict] = {}
    for key, experiment in CELLS.items():
        document, cell, comp = composed_of(experiment)
        documents[key] = document
        composed[key] = comp
        split = document["population"]["split_identity_hash"]
        fit = comp.values["native_contact_fit"]
        perception = comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
        ids[key] = {
            "cell": cell["cell_id"], "experiment": experiment, "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": fit["run_id"], "fit_attempt_id": fit["attempt_id"], "fit_contact_cap": fit["contact_cap"],
            "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"], "arm": comp.values["arm"], "rows": document["population"]["count"],
            "split_identity_hash": split, "split_role": document["execution_plan"]["split_role"],
            "composed_config_hash": comp.config_hash, "protocol_hash": protocol_hash(comp.config_hash, comp.values["arm"], split),
            "family_budget": document["family_budget"], "readiness_state": cell["readiness"]["state"],
            "readiness_requirements": cell["readiness"]["requirements"],
            "boundary": {k: perception.get(k) for k in ("k", "tau", "rank_weights", "fuse_coverage")},
            "policy": comp.values["policy"], "scorers": comp.values["scorers"],
            "owner_allowance": comp.values.get("owner_allowance"),
        }
        if ids[key]["readiness_state"] != "held":
            raise SystemExit(f"{key} is not held")
        if ids[key]["scorers"] != [SCORER, "cost"]:
            raise SystemExit(f"{key} does not score with the TEST sibling {SCORER}")
        if ids[key]["split_role"] != "final-report" or split != allowance["split"]["split_identity_hash"]:
            raise SystemExit(f"{key} is not a final-report plan on the allowance's split identity")
        if ids[key]["owner_allowance"] != {"path": ALLOWANCE, "sha256": allowance_sha}:
            raise SystemExit(f"{key} does not pin the committed allowance bytes")
        if ids[key]["rows"] != ROWS:
            raise SystemExit(f"{key} is not the 3,010-row sample")
    if ids["plan"]["run_id"] not in allowance["read_run_ids"] or ids["arm"]["run_id"] not in allowance["read_run_ids"]:
        raise SystemExit("a milestone cell's run id is not a read run id of the signed allowance")
    fit_not_permitted = sorted(ids[k]["fit_run_id"] for k in CELLS if ids[k]["fit_run_id"] not in allowance["permitted_run_ids"])
    plan_cells = [c["cell"] for c in json.loads(rd(CAMPAIGN_PLAN))["cells"]]
    if plan_cells != [CELLS["plan"], CELLS["arm"]]:
        raise SystemExit(f"the campaign plan must fly MILESTONE-00-PLAN then MILESTONE-01: {plan_cells}")

    # ---- the diff proofs ---------------------------------------------------------------------
    src: dict[str, object] = {}
    for key, experiment in SOURCES.items():
        _, _, src[key] = composed_of(experiment)
    diffs = {
        "plan_vs_dev_plan": classify(src["plan"].values, composed["plan"].values),
        "arm_vs_a2_arm": classify(src["arm"].values, composed["arm"].values),
    }
    for name, diff in diffs.items():
        if diff["anything_else"] or diff["composition_factor"]:
            raise SystemExit(f"{name}: moved beyond the roster re-target: {diff['anything_else'] + diff['composition_factor']}")
    # preparation_source_receipts is a list leaf: prove it entry by entry.
    for key in CELLS:
        before = src[key].values["preparation_source_receipts"]
        after = composed[key].values["preparation_source_receipts"]
        if len(before) != len(after):
            raise SystemExit(f"{key}: preparation_source_receipts changed length")
        for b, a in zip(before, after):
            if a["relpath"] == b["relpath"]:
                if a["sha256"] != b["sha256"] or a.get("root") != b.get("root"):
                    raise SystemExit(f"{key}: an unchanged preparation receipt moved its pin: {a['relpath']}")
            elif not (a["sha256"] == ZERO or a["relpath"] == ROSTER_RECEIPT or _is_sample_preparation(a["relpath"])):
                raise SystemExit(f"{key}: a re-targeted preparation receipt carries a non-pending pin: {a['relpath']}")

    sq_sample = classify(composed["plan"].values, composed["arm"].values)
    sq_dev = classify(src["plan"].values, src["arm"].values)
    fs, fd = flatten(composed["arm"].values), flatten(src["arm"].values)
    fps, fpd = flatten(composed["plan"].values), flatten(src["plan"].values)
    roster_bound_in_square = {f"{BOUNDARY}.agreement_source.relpath", f"{BOUNDARY}.agreement_source.sha256",
                              f"{BOUNDARY}.agreement_source.tool_contact_ledger_row"}
    if sorted(sq_sample["composition_factor"]) != sorted(sq_dev["composition_factor"]):
        raise SystemExit("the composition square does not commute: the factor paths differ")
    for key in sq_sample["composition_factor"]:
        if key in roster_bound_in_square:
            continue
        if fs.get(key, "<absent>") != fd.get(key, "<absent>") or fps.get(key, "<absent>") != fpd.get(key, "<absent>"):
            raise SystemExit(f"the composition square moves {key} to different values on the two rosters")
    # The arm pins two more preparation receipts (the agreement table's and the centroid key's) than the
    # comparator -- the composition's own provenance -- so preparation_source_receipts is the one list leaf
    # allowed to differ between the two cells on one roster.
    allowed_in_square = {"preparation_source_receipts"} | roster_bound_in_square
    if sq_sample["anything_else"] or sq_sample["role_bound"] or set(sq_sample["roster_bound"]) - allowed_in_square:
        raise SystemExit(f"arm vs comparator differs beyond the composition: {sq_sample}")
    if set(sq_sample["roster_bound"]) != set(sq_dev["roster_bound"]) - {"population.roster_receipt"}:
        raise SystemExit(f"the composition square's roster-bound leaves differ: {sq_sample['roster_bound']} vs {sq_dev['roster_bound']}")
    extra = [r["relpath"] for r in composed["arm"].values["preparation_source_receipts"]
             if r not in composed["plan"].values["preparation_source_receipts"]]
    extra_dev = [r["relpath"] for r in src["arm"].values["preparation_source_receipts"]
                 if r not in src["plan"].values["preparation_source_receipts"]]
    if len(extra) != len(extra_dev):
        raise SystemExit(f"the composition's provenance receipts differ in number between the rosters: {extra} vs {extra_dev}")
    diffs["composition_square"] = {
        "arm_vs_plan_on_sample": sq_sample["composition_factor"],
        "a2_arm_vs_dev_plan": sq_dev["composition_factor"],
        "commutes": True,
        "roster_bound_within_the_factor": sorted(roster_bound_in_square),
        "note": "the agreement table's pin is roster-bound by construction (each roster votes with its own table); every other factor value is equal on the two rosters",
    }

    own_null = scaled_null()
    caps = ids["arm"]["family_budget"]
    a2_facts = json.loads(rd(A2_PACKAGE + "/registered-facts-v1.json"))
    a2_declared = a2_facts["stage3_measurement"][A2_ARM_RUN]["expected_effect_pp"]
    if expected != a2_declared:
        raise SystemExit(f"--expected-effect-pp {expected} is not A2's own declared {a2_declared}")
    arm_expected, arm_expected_status = expected, "PROVISIONAL: A2's own declared number; root re-declares from the A2 read before the flip"
    if redeclaration:
        prior_arm = prior_facts["stage3_measurement"][ids["arm"]["run_id"]]
        if redeclaration.get("from_expected_effect_pp") != expected or prior_arm["expected_effect_pp"] != redeclaration["to_expected_effect_pp"]:
            raise SystemExit("the committed redeclaration does not match --expected-effect-pp and the committed measurement")
        arm_expected, arm_expected_status = prior_arm["expected_effect_pp"], prior_arm["expected_effect_status"]
    measurement = {
        ids["arm"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": True,
            "expected_effect_pp": arm_expected,
            "expected_effect_status": arm_expected_status,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official-test) the non-inferiority guard (owner decision 133)",
            "primary_metric_key": "intent",
            "replicate_run_id": ids["plan"]["run_id"],
            "rows": ROWS,
            "own_null": own_null,
            "roster": f"TEST-SAMPLE ({ROSTER_ID}, split identity {ids['arm']['split_identity_hash']}), 3,010 recordings / 682 prompts",
            "tuning_roster": ["slurp-train-construction-pool-agree-kprobe-r01-excluded", "SLURP-DEV-2000-ADDED-V1"],
            "read_roster": ROSTER_ID,
            "note": (
                f"MILESTONE-01 = COMP-1b on the signed test sample (owner decisions 151 and 202). expected_effect_pp {expected} "
                f"is cell A2's own declared number ({A2_PACKAGE}/registered-facts-v1.json: the COMP-1b TRAIN Fold A intent "
                "point, docs/results/2026-09-29-slurp-comp1b-fold-a-read.md), carried PROVISIONALLY because the floor gate "
                "refuses a placeholder: root RE-DECLARES it from the A2 read (owner decision 139: a measured number, not a "
                "prior) before the flip, and the flip refuses while registered-facts' redeclared_from_a2_read is false. The "
                "contrast is against MILESTONE-00-PLAN, the LOCKED plan (recall k 8), not A2's in-chain A/A (k 60), so the "
                "milestone delta includes the k 8 -> 60 recall change the composed arm carries (the allowance prescribes "
                "the locked system as the comparator). The guard is a FALLBACK null (own_null.flag). tuning_roster / "
                "read_roster (item D3): the vote pool and centroid key are TRAIN construction artifacts; the arm was "
                "SELECTED on DEV-2000-ADDED by cell A2's read; both are disjoint from the sample by the sample's own "
                "disjointness proof (docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/"
                "disjointness.json, CLEAN); nothing was chosen or tuned on the sample."
            ),
        },
        ids["plan"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
            "primary_metric_key": "intent",
            "replicate_run_id": ids["arm"]["run_id"],
            "rows": ROWS,
            "tuning_roster": "none",
            "read_roster": ROSTER_ID,
            "note": (
                "MILESTONE-00-PLAN is the INSTRUMENT, not a claim: the locked v2.0 plan exactly as flown on DEV-2000-ADDED, "
                "re-targeted to the sample, flown in the same chain before MILESTONE-01. The allowance makes it THE "
                "comparator of every milestone arm; its own number is the locked system's sample read."
            ),
        },
    }

    agreement_pin = composed["arm"].values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["agreement_source"]["sha256"]
    composition = (
        "MILESTONE-01 is cell A2's arm (COMP-1b) with only the roster moved to the signed test sample: the locked v2.0 "
        "plan + (1) the agreement term (w_agree 1.0, recall k 60, delivered 8-1-8) with this roster's own vote table "
        "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1" + (" (PENDING)" if agreement_pin == ZERO else "")
        + " + (2) the centroid boundary key + (3) no "
        "citation contract + (4) nothing else. MILESTONE-00-PLAN is the sealed DEV plan arm (the v2.0 lock as flown) "
        "with only the roster moved."
    )
    pending = sorted({r["relpath"] for k in CELLS for r in ids[k]["readiness_requirements"] if r["sha256"] == ZERO})
    pinned: dict[str, str] = {}
    for key in CELLS:
        for r in ids[key]["readiness_requirements"]:
            if r["sha256"] != ZERO and r["reason"].startswith("PINNED"):
                pinned[r["relpath"]] = r["sha256"]
        for r in composed[key].values["preparation_source_receipts"]:
            if _is_sample_preparation(r["relpath"]) and r["sha256"] != ZERO:
                pinned[r["relpath"]] = r["sha256"]
    sample_pending = [p for p in pending if not p.endswith("/phase-supply-v1.json")]
    if pinned:
        preparations_blocker = (
            "PREPARATIONS: preparations 2 and 3 of the sample (SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, "
            "SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1; label-free, owner decision 156) have run and their "
            f"artifacts are pinned (sample_preparation_pins: {len(pinned)} pins, verified against the data-root bytes by "
            f"{DERIVE_SCRIPT} --data-root). "
            + ("REMAINING: this roster's agreement table, built model-free by scripts/build_slurp_intent_exemplar_agreement.py "
               "against MILESTONE-00-PLAN (as the DEV-2000-ADDED table was built against the sealed DEV plan cell), then "
               f"re-derived with --data-root. Pending pins: {pending}." if sample_pending else
               "No sample-preparation pin remains pending (this roster's agreement table and its receipt are pinned from "
               "the builder's own receipt, ledger row SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1); the only "
               f"zero pins are each cell's own first-phase supply, "
               f"minted at the flip (item E16): {pending}.")
        )
    else:
        preparations_blocker = (
            "PREPARATIONS: preparation 2 (SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, GPU encoder) and preparation "
            "3 (SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1) have not run; their rows are not countersigned. Then this "
            "roster's agreement table must be built model-free (scripts/build_slurp_intent_exemplar_agreement.py against "
            f"MILESTONE-00-PLAN). Pending pins: {pending}."
        )
    expectation_blocker = (
        f"EXPECTATION: CLEARED -- re-declared {redeclaration['from_expected_effect_pp']} -> "
        f"{redeclaration['to_expected_effect_pp']} from the A2 read on {redeclaration['at_utc']} (registered-facts "
        "redeclaration; redeclared_from_a2_read true)." if redeclaration else
        "EXPECTATION: root re-declares expected_effect_pp from the A2 read (registered-facts redeclared_from_a2_read)."
    )
    blockers = [
        "OWNER GATE (decisions 151 and 202): cell A2 must read NOMINATED or better and the coordinator must report the "
        "dev-admitted composed arm to the owner in conversation; the root countersignature of the first milestone row "
        "names that report (allowance first_contact_gate).",
        ("ALLOWANCE: CLEARED -- owner decision 207 signed the successor allowance "
         f"{ALLOWANCE} (sha256 {allowance_sha}), which names both FIT run ids as preparation-kind (non-read) run ids; "
         "both fragments pin its bytes (the v1 file is superseded, never edited)." if not fit_not_permitted else
         "ALLOWANCE (v1 names no FIT run id): the native contact-fit gate needs a distinct run id per cell "
         "(core.preparation_fit.build_native_contact_fit_gate) and passes it through the same gate touch, which "
         "contracts.plan.require_owner_split_allowance refuses for a run id outside permitted_run_ids. A SUCCESSOR "
         f"allowance (...-slurp-test-sample-allowance-v2.json, the v1 file superseded, never edited) must name {fit_not_permitted} "
         "as preparation-kind (non-read) run ids, and both fragments re-pin to its bytes. Owner signature required."),
        preparations_blocker,
        expectation_blocker,
        "READ DRIVER: scripts/analysis/stage3_paired_read.py reports the raw roster mean as 'natural_mixture'; on the "
        "floored sample that is NOT the natural-mixture number (design note section 5: post-stratify per-intent "
        "accuracy by full-test shares, the roster receipt's weightings block). The post-stratified weighting must land "
        "in the read path, with tests on fakes, before the READ row is countersigned.",
    ]

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free fact the COMP-1b test-sample milestone registration rests on, and the CANONICAL "
            "stage3_measurement block for MILESTONE-00-PLAN and MILESTONE-01."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "redeclared_from_a2_read": bool(redeclaration),
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "28/86": "development numbers only; never a test claim",
            "133": "intent primary, official SLU-F1 the guard",
            "139": "no prior; a number derived from a measured read is not a prior",
            "141": "a coverage-guaranteed test sample is permitted for milestone comparison",
            "151": "the sample allowance signed; first contact gated on a reported dev-admitted composed arm",
            "156": "the three label-free sample preparations may run ahead",
            "190": "primary_metric_key and the tuning_roster / read_roster split (item D3)",
            "198": "A2 = COMP-1b on DEV-2000-ADDED",
            "202": "GO for the test-sample milestone read once A2 reads NOMINATED or better",
        },
        "allowance": {
            "path": ALLOWANCE, "sha256": allowance_sha, "status": allowance["status"],
            "read_run_ids_used": [ids["plan"]["run_id"], ids["arm"]["run_id"]],
            "fit_run_ids_not_permitted_by_this_allowance": fit_not_permitted,
            "smoke": "NOT REGISTERED: the allowance names no smoke run id, and a smoke under a read run id would consume that read's one attempt. The form proof is cell A2's own four-row smoke (SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1) of the same composition on DEV-2000-ADDED, plus the model-free core.flight.cli check of both milestone cells at the flip.",
            "attempts": "ONE per read run id, ever; no recovery, no resume, no re-score (allowance attempt_budget and milestone_rule)",
        },
        "rows": ROWS,
        "the_composition": composition,
        "stage3_measurement": measurement,
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("family_budget", "readiness_requirements")} for key in CELLS},
        "composed_config_diffs": {
            **diffs,
            "derive_script": {"relpath": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
            "classes": {"roster_bound": list(ROSTER_BOUND), "role_bound": list(ROLE_BOUND), "bookkeeping": list(BOOKKEEPING),
                        "experiment_fragment_own_block": list(EXPERIMENT_BLOCK), "composition_factor": list(COMPOSITION_FACTORS)},
        },
        "pending_pins": pending,
        "sample_preparation_pins": {
            "pins": [{"relpath": k, "sha256": pinned[k]} for k in sorted(pinned)],
            "note": ("Every sample-preparation pin the cells carry, read from the preparations' summary receipt (the "
                     "agreement table and its receipt: from the agreement builder's own receipt) and verified "
                     f"against the data-root bytes by {DERIVE_SCRIPT} --data-root. protocol-registered-v1.json and the plan "
                     "documents were re-derived with these pins and carry the current stage3_measurement (the redeclaration's "
                     "note that the protocol kept the provisional copy is superseded by this re-derivation).") if pinned else
                    "none yet: every sample-preparation pin is PENDING",
        },
        "blockers_before_the_flip": blockers,
        "budget_arithmetic": {
            "family_budget": caps,
            "derivation": [
                "generation_calls_cap = 3,010 rows x 11 contacts per row (1 + 2 x (1 + 3 + 1) at max_revisions 1), run-cumulative",
                "fit_endpoint_calls_cap = 3,010 x 11 x (1 packet + 3 endpoints)",
                "repeated_speech_audio_seconds_cap = ceil(11 x 8,206.436875)",
                "gpu_hours_fit_inclusive = the source's 12.0 per 1,000 rows scaled to 3,010, rounded up to 0.1",
                "one official complete slurp-slu-official-test score per generation cell over the complete 3,010-row manifest, never sharded",
            ],
        },
        "report_form": {
            "headline": "intent accuracy and official pooled SLU-F1, reported SEPARATELY, arm minus MILESTONE-00-PLAN on the same rows",
            "weightings": "natural mixture = post-stratified to full-test per-intent shares (roster receipt weightings); equal stratum = 1/58 over the intents present (general_greet is closure-only)",
            "per_stratum": "per-intent and per-scenario tables in both weightings",
            "claim_wording": "a MILESTONE read: development evidence under owner decision 28 ('dev numbers are not test claims'), never a test claim, never the final read, never publication-grade; it may say the arm held / did not hold its DEV-nominated intent gain on a test sample against the locked system",
        },
        "authority_relpaths": [OWNER_DECISIONS, ALLOWANCE, DESIGN_NOTE, PREP_NOTE, PROTOCOL_DRAFT, A2_PACKAGE + "/README.md", INSTRUMENT],
        "prohibitions": [
            "No contact before every blocker above is cleared, root countersigns the rows, mints the decision receipt and both cells are flipped in one converged cycle.",
            "ONE attempt per read run id, ever: no re-fly, no recovery, no resume, no re-score, no re-projection, no best-of, no tuning on the sample.",
            "No smoke on the sample; no direct-baseline read; no closure-roster or FULL-test contact.",
            "No k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change. --allow-output-change is never passed.",
            "No utterance text, gold label, transcript or model output is printed or persisted by any read.",
        ],
    }
    if redeclaration:
        facts["redeclaration"] = redeclaration
    if "post_stratification_read" in prior_facts:
        facts["post_stratification_read"] = prior_facts["post_stratification_read"]
    if (prior_facts.get("report_form") or {}).get("weightings"):
        facts["report_form"]["weightings"] = prior_facts["report_form"]["weightings"]
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read MILESTONE-01 against MILESTONE-00-PLAN flown in the same chain, on the same 3,010 rows. PRIMARY: intent "
        "accuracy (scenario_action exact), paired per recording with prompt-clustered bootstrap, 10,000 draws, seed "
        "20260929. GUARD: official pooled SLU-F1 (slurp-slu-official-test) non-inferior at the FALLBACK null "
        f"h_SLU {own_null['h_slu']} (h_intent {own_null['h_intent']}; the DEV-2000-ADDED own null scaled by sqrt(913 / 682), "
        "flagged). HELD: the intent CI95 lower bound above zero AND the guard holds. NEUTRAL: both metrics non-inferior "
        "at the fallback null without a held gain. HARMFUL: a measured loss on either metric (decision 25). Every "
        "verdict carries intent and SLU separately, per-intent and per-scenario tables in both weightings "
        "(post-stratified natural mixture; equal stratum over 58 intents). The number is a MILESTONE read, "
        "development evidence under owner decision 28, never a test claim."
    )
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-comp1b-testsample-milestone-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_HELD_BLOCKED_ON_OWNER_ALLOWANCE_AND_PREPARATIONS",
        "the_question": (
            "Does COMP-1b, nominated or admitted on DEV-2000-ADDED by cell A2, hold its intent gain against the locked "
            "v2.0 plan on the signed test sample, with official SLU-F1 non-inferior?"
        ),
        "the_composition": composition,
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "policy")} for key in CELLS},
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "one_shot_semantics": facts["allowance"]["attempts"],
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"]},
        "blockers_before_the_flip": blockers,
        "development_numbers_only": "Every number is a milestone development number (owner decisions 28, 86, 151); never a test claim and never the final read.",
        "failure_policy": documents["arm"]["failure_policy"],
        "authority": f"owner decisions 151 and 202 ({OWNER_DECISIONS}); allowance {ALLOWANCE}; design {DESIGN_NOTE}; one-read protocol {PROTOCOL_DRAFT}; cell A2 {A2_PACKAGE}; the instrument {INSTRUMENT}",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "plan"):
        identity = ids[key]
        own_supply = next(r for r in identity["readiness_requirements"] if r["relpath"].endswith("phase-supply-v1.json"))
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            if is_fit:
                route = ("The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures "
                         "request envelopes and produces no generation. REFUSED by the v1 allowance until a successor "
                         "names this run id.")
            else:
                route = (f"Shared core.flight.cli campaign over {CAMPAIGN_PLAN}, which flies MILESTONE-00-PLAN and then "
                         "MILESTONE-01 in ONE campaign (instrument rule 3), one official slurp-slu-official-test score per "
                         "generation cell at finalize. No smoke step.")
            plan = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": identity["cell"],
                "experiment": identity["experiment"],
                "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at,
                "status": protocol["status"],
                "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit,
                "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1",
                    "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": "slurp",
                    "run_id": identity["fit_run_id"] if is_fit else identity["run_id"],
                    "attempt_id": identity["fit_attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "final-report",
                    "split_identity_hash": identity["split_identity_hash"],
                    "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                    "owner_allowance": {"path": ALLOWANCE, "sha256": allowance_sha},
                },
                "family_budget": budget,
                "execution_route": route,
                "prepared_phase_supply": {
                    "relpath": own_supply["relpath"], "sha256": own_supply["sha256"],
                    "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip (item E16); --allow-output-change must never be passed.",
                },
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": f"{identity['run_id']}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule if key == "arm" else "THE COMPARATOR and in-chain replicate: the locked system's own sample read."),
                "quality_read_gate": "No task-quality read before BOTH manifests are complete and sealed with one successful complete official slurp-slu-official-test score each, and the READ row is root countersigned.",
            }
            prefix = {"arm": "", "plan": "plan-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-comp1b-testsample-milestone-read-v1",
        "read_run_id": READ_RUN,
        "title": "Test-sample MILESTONE-01 -- COMP-1b against MILESTONE-00-PLAN (the locked system) on SLURP-TEST-SAMPLE-3010-V1",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": ids["plan"]["run_id"], "attempt_id": ids["plan"]["attempt_id"], "fit_run_id": ids["plan"]["fit_run_id"], "role": "THE COMPARATOR the allowance prescribes and the in-chain replicate the delta is read at", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
        },
        "read_driver": {
            "command": f"bash {READ_DRIVER}",
            "passes": ["vs-aa (gating: arm minus MILESTONE-00-PLAN)"],
            "scorer": SCORER,
            "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned",
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260929, "unit": "prompt cluster (paired)"},
        "weightings": {
            "natural_mixture": f"POST-STRATIFIED: per-intent accuracy weighted by the full-test per-intent shares of the roster receipt {ROSTER_RECEIPT} (weightings block); the raw roster mean is NOT the natural-mixture number (design note section 5)",
            "equal_stratum": "1/58 over the intents present in the sample",
            "driver_gap": blockers[-1],
        },
        "steps": [
            "1. Refuse unless BOTH manifests are COMPLETE at 3,010 rows with this registration's composed config hashes (as re-pinned at the flip), sealed, each with one successful complete official slurp-slu-official-test score, and unless the READ row is root countersigned.",
            "2. THE DELIVERY CHECK (gold-free): each cell's flown first-phase boundary selections equal its own prepared supply. A mismatch is an engineering defect, is reported, and consumes the milestone (no re-fly).",
            f"3. Primary: intent accuracy paired per recording, prompt-clustered, 10,000 draws, seed 20260929. Guard: official pooled SLU-F1. Apply the protocol's rule at the fallback null h_intent {own_null['h_intent']} / h_SLU {own_null['h_slu']} (recording-scaled beside it: {own_null['h_intent_recording_scaled']} / {own_null['h_slu_recording_scaled']}) against the declared expected_effect_pp.",
            "4. Intent and SLU reported SEPARATELY, each in both weightings, with per-intent and per-scenario tables and the recording-channel split (headset / far-field).",
            "5. Entity FP / TP / FN against MILESTONE-00-PLAN with the zero-gold-row emission count.",
            "6. Write the read under its own id; every number is a MILESTONE development number (owner decisions 28 and 151), never a test claim.",
        ],
        "output": {"analysis_root": ANALYSIS_ROOT},
        "boundary": "A milestone read on the signed test sample. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    if (prior_recipe.get("read_driver") or {}).get("strata_source"):
        recipe["read_driver"]["strata_source"] = prior_recipe["read_driver"]["strata_source"]
    if (prior_recipe.get("weightings") or {}).get("post_stratification"):
        recipe["weightings"]["post_stratification"] = prior_recipe["weightings"]["post_stratification"]
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["plan"]["run_id"], ids["plan"]["fit_run_id"], ids["arm"]["run_id"], ids["arm"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/comp1/comp1b_testsample_mint_receipt.py, which refuses while any blocker in the registered facts is open. It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Test-sample milestone read (owner decisions 151 and 202): the locked PLAN comparator and one dev-nominated composed arm (COMP-1b), one attempt each.",
        "decision": f"Fly MILESTONE-00-PLAN then MILESTONE-01 in one campaign on SLURP-TEST-SAMPLE-3010-V1; read at intent primary against expected_effect_pp {arm_expected}{'' if redeclaration else ' (to be re-declared from the A2 read)'} with official SLU-F1 the guard at the fallback null.",
        "authorization_basis": "Owner decisions 151 (allowance) and 202 (GO once A2 reads NOMINATED or better); the A2 read; the coordinator's conversational report to the owner (named in the countersignature).",
        "first_contact_report": {"date": None, "arm": None, "note": "root fills this with the conversational report of decision 151 before minting"},
        "antecedents": {
            "allowance": {"path": ALLOWANCE, "sha256": allowance_sha},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "a2_registration": {"path": A2_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(A2_PACKAGE + "/registered-facts-v1.json")},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "A milestone development read (owner decisions 28, 151). No test claim, no superiority, generalisation, confirmatory or paper-scale claim. claim: nominated.",
        "failure_policy": documents["arm"]["failure_policy"],
        "not_authorized": [
            "any contact before every blocker is cleared and both cells are flipped",
            "a second attempt of either read run id, a recovery, a resume or a re-score",
            "a smoke, a direct-baseline read, the closure roster or the FULL test split",
            "--allow-output-change on the re-pin tool",
        ],
        "population": {"count": ROWS, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "final-report", "roster": ROSTER_ID, "closure_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS} | {"note": f"the values of the fragments exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    runs_line = "; ".join(f"`{ids[k]['run_id']}` / `{ids[k]['fit_run_id']}`" for k in ("plan", "arm"))
    blockers_md = "\n".join(f"{i}. {b}" for i, b in enumerate(blockers, 1))
    measurement_wording = (
        f"RE-DECLARED {redeclaration['at_utc']} from the cell A2 read (was A2's own declared {redeclaration['from_expected_effect_pp']}; "
        "`redeclaration` in the facts, owner decision 139: a measured number, not a prior)" if redeclaration else
        "A2's own declared number, PROVISIONAL: root re-declares it from the A2 read before the flip\n"
        "(`redeclared_from_a2_read` in the facts; the flip refuses while it is false)"
    )
    readme = f"""# Test-sample milestone: COMP-1b against the locked plan on SLURP-TEST-SAMPLE-3010-V1

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decisions 151 and 202);
both cells **held** and **blocked** (below). Nothing here authorises a contact, a flip, a mint or a countersignature.

**Authority.** The signed allowance `{ALLOWANCE}` (status `authorised`, owner decision 151) names the two read run ids
used here: `{ids['plan']['run_id']}` (THE COMPARATOR: the locked v2.0 plan as flown, unchanged) and `{ids['arm']['run_id']}`
(one dev-admitted composed arm). Owner decision 202: GO once cell A2 (`{SOURCES['arm']}`) reads NOMINATED or better.
Each read run id gets ONE attempt, ever; the milestone number is consumed whatever the outcome.

**What it is.** {composition} Proven by `registered-facts-v1.json` (`composed_config_diffs`): each milestone cell differs
from its DEV source by roster-bound, role-bound (final-report: split role, allowance pin, the TEST scorer sibling
`slurp-slu-official-test`, the one-attempt failure policy) and bookkeeping paths alone, and the arm-vs-comparator delta on
the sample equals A2's arm-vs-DEV-plan delta (recall k 8 -> 60, w_agree, agreement table, centroid key). Derived by
`{DERIVE_SCRIPT}`.

**What the allowance forbids, so this package does not carry it.** No four-row smoke on the sample (no smoke run id is
permitted, and a smoke under a read id would consume its one attempt; the form proof is A2's own DEV smoke of the same
composition plus the model-free `check` at the flip). No direct-baseline read. No recovery or resume.

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 3,010 (682 prompts), intent primary, `expected_effect_pp`
**{arm_expected}** -- {measurement_wording}. Guard: official SLU-F1 at a FALLBACK null --
no own null exists for the sample; the DEV-2000-ADDED own null scaled by sqrt(913 / 682) (prompt level, conservative):
h_intent {own_null['h_intent']}, h_SLU {own_null['h_slu']} (recording-scaled {own_null['h_intent_recording_scaled']} /
{own_null['h_slu_recording_scaled']}). FLAGGED.

**Report form.** Intent and SLU-F1 reported separately, each in the post-stratified natural mixture and equal-stratum
(58 intents) weightings, per-intent and per-scenario. A milestone read is development evidence under owner decision 28
("dev numbers are not test claims"): it may say whether COMP-1b held its DEV-nominated intent gain against the locked
system on a test sample; it is never a test claim, never the final read, never publication-grade.

{readme_post_strat}**Blockers before the flip.**

{blockers_md}

**Runs.** {runs_line}. READ `{READ_RUN}`.

**Declare, mint, flip, queue, read** (after every blocker clears): (1) root countersigns the five DRAFT rows (naming the
conversational report) and mints `{DECISION_RELPATH}` with `scripts/flights/comp1/comp1b_testsample_mint_receipt.py`;
(2) `scripts/flights/comp1/comp1b_testsample_flip.sh` re-pins comparator then arm to one HEAD; (3)
`scripts/flights/comp1/batch_chain_comp1b_testsample.sh` queues the two-cell campaign (no smoke); (4) after both seals
the READ row is countersigned and `bash {READ_DRIVER}` reads it.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Test-sample milestone MILESTONE-01 (COMP-1b) against MILESTONE-00-PLAN: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact (owner decisions 151 and 202).
A MILESTONE read: development evidence under owner decision 28; never a test claim and never the final read.

## One-shot semantics

ONE attempt per read run id, ever (allowance `milestone_rule` and `attempt_budget`; enforced by
`contracts.gate_exposure._ExposureAndCarrierMixin._require_final_report_attempt_budget`). No re-fly, no recovery, no
resume, no re-score, no re-projection of delivered bytes, no best-of, no tuning on the sample. A failed or aborted
attempt consumes the milestone number; a further milestone needs a fresh run id in a successor allowance under a fresh
coordinator report to the owner. The results are reported as the milestone read of decisions 151 and 202, whatever
they are.

## The cells

| item | value |
| --- | --- |
| composition | {composition} |
| roster | {ROSTER_ID}, 3,010 recordings / 682 prompts, split role final-report, scorer {SCORER} |
| comparator / in-chain replicate | `{ids['plan']['run_id']}`, flown in the same campaign before the arm |
| guard null | FALLBACK (no own null): h_intent {own_null['h_intent']}, h_SLU {own_null['h_slu']} (DEV-2000-ADDED null x sqrt(913/682)) |
| smoke | none (the allowance names no smoke run id) |
| runs | {runs_line} |
| composed config hashes | comparator `{ids['plan']['composed_config_hash']}`; arm `{ids['arm']['composed_config_hash']}` |
| protocol hashes | comparator `{ids['plan']['protocol_hash']}`; arm `{ids['arm']['protocol_hash']}` |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

{prereg_post_strat}## Blockers before the flip

{blockers_md}

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    appended = 0
    if args.append_ledger:
        ledger = rd(LEDGER)
        if READ_RUN in ledger:
            raise SystemExit("the milestone rows are already in the ledger")
        model_tool = (
            "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted TEST-SAMPLE-3010 speech packets "
            "(TEST-SAMPLE-3010-promotion.json, sha256 d0a827b6...); NO native tool authority on any role; the locked plan's "
            "role prompts; the official scorer slurp-slu-official-test after delivery only"
        )
        inherited = (
            "The 3,010 sample recordings carry the label-free packet ENCODE+PROMOTE exposure of SAEA-SN-TEST-SAMPLE-3010-PREPROCESS "
            "(owner decision 156) and, before the flip, the label-free speech-query encoding of preparation 2; NO answer surface "
            "of any sample row has been read. The sample's roster receipt read test scenario/action offline for stratification "
            "(decision 141 item 5). Every prior SLURP exposure is inherited in full; the closure roster stays unread."
        )
        common = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the test-sample milestone registration (worktree {args.worktree}, branch {args.branch}); "
            "owner decisions 151 and 202. This registration performs no contact and authorises none. BLOCKED: see "
            f"{package}/README.md (owner report of the dev-admitted arm; a successor allowance naming the FIT run ids; "
            "preparations 2 and 3 and this roster's agreement table; expected_effect_pp re-declared from the A2 read)."
        )
        rows = []
        for key, fit_flag in (("plan", False), ("plan", True), ("arm", False), ("arm", True)):
            identity = ids[key]
            prefix = {"arm": "", "plan": "plan-"}[key]
            plan_name = f"{prefix}{'fit' if fit_flag else 'generation'}-plan-registered-v1.json"
            run_id = identity["fit_run_id"] if fit_flag else identity["run_id"]
            attempt = identity["fit_attempt_id"] if fit_flag else identity["attempt_id"]
            budget = identity["family_budget"]
            calls = budget["fit_endpoint_calls_cap"] if fit_flag else budget["generation_calls_cap"]
            what = ("MILESTONE-00-PLAN, THE COMPARATOR: the locked v2.0 plan on the test sample" if key == "plan"
                    else "MILESTONE-01: COMP-1b on the test sample") + (
                " -- FIT spend identity, request envelopes only, no generation; NOT PERMITTED by allowance v1 (successor required)" if fit_flag else
                " -- a READ run id of the signed allowance, ONE attempt, ever")
            notes = (
                f"{common} Plan SHA256 {plan_shas[f'{key}:' + ('fit' if fit_flag else 'generation')]}; attempt {attempt}. Protocol hash "
                f"{identity['protocol_hash']}; composed config {identity['composed_config_hash']}; allowance {ALLOWANCE} sha256 "
                f"{allowance_sha}; expected session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} "
                f"(decision id {DECISION_ID}) with the four eligible run ids, then scripts/flights/comp1/comp1b_testsample_flip.sh "
                "re-pins with scripts/flights/repin_cell.py --set-ready (item E16); --allow-output-change must never be passed; "
                f"every hash in this row moves at the flip. Measurement: cross-flight-with-in-chain-replicate, n 3010, intent "
                f"primary, expected_effect_pp {expected if key == 'arm' else 0.0} (claims_benefit {'true' if key == 'arm' else 'false'}; "
                f"PROVISIONAL, re-declared from the A2 read), guard official SLU-F1 at the FALLBACK null h_intent {own_null['h_intent']} / "
                f"h_SLU {own_null['h_slu']}. Read: {READ_RUN}. ONE attempt; no recovery; no smoke; no test claim (owner decision 28)."
            )
            rows.append(ledger_row([
                args.registered_at[:10], run_id, "bounded-discovery-probe", what, model_tool,
                f"slurp {ROSTER_ID} TEST sample {identity['rows']}", "final-report", identity["split_identity_hash"], "no", str(calls),
                str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), inherited,
                f"{package}/{plan_name}", notes,
            ]))
        rows.append(ledger_row([
            args.registered_at[:10], READ_RUN, "model-free-check",
            "The test-sample MILESTONE-01 read: COMP-1b minus MILESTONE-00-PLAN on the same 3,010 rows (gating; intent primary, official SLU-F1 the guard, at the fallback null), intent and SLU separately in the post-stratified natural-mixture and equal-stratum weightings, per-intent and per-scenario tables, entity FP/TP/FN.",
            "No model, tokenizer, encoder or server contact: scripts/flights/comp1/comp1b_testsample_read.sh over the sealed per-sample official slurp-slu-official-test scores and sealed receipts.",
            f"slurp {ROSTER_ID} TEST sample 3010", "final-report", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
            "Reads only the two sealed milestone manifests and their one official score each; no new audio exposure.",
            f"{package}/analysis-recipe-v1.json",
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package, so the pre-launch gate scripts/checks/flight_registration_check.py finds it. Analysis root $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/; recipe {package}/analysis-recipe-v1.json (recipe_id {recipe['recipe_id']}); the driver refuses before any score is opened until root countersigns this row (after both seals). A MILESTONE read under owner decisions 151 and 202: development evidence (decision 28), never a test claim. No utterance text, gold, transcript or model output is printed or persisted.",
        ]))
        header = (
            "\n## Test-sample milestone: COMP-1b (MILESTONE-01) against the locked plan (MILESTONE-00-PLAN) on SLURP-TEST-SAMPLE-3010-V1 "
            "(owner decisions 151 and 202; DRAFT, root countersignature pending; BLOCKED)\n\n"
            f"Five unconsumed DRAFT rows registered before contact under the signed allowance {ALLOWANCE} (status authorised, "
            f"sha256 {allowance_sha}): the two READ run ids MILESTONE-00-PLAN and MILESTONE-01, their FIT spend identities "
            "(NOT named by allowance v1: a successor allowance is required before either can be countersigned), and the "
            f"model-free READ row. Package {package}; preregistration {prereg}. No smoke row: the allowance names no smoke run "
            "id. None of these rows is countersigned and none authorises a contact.\n\n"
            "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        )
        body = ledger.rstrip("\n") + "\n" + header + "\n".join(rows) + "\n"
        io.open(LEDGER, "w", encoding="utf-8", newline="").write(body)
        appended = len(rows)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "composed_config_diffs": {k: ({kk: len(vv) for kk, vv in v.items() if isinstance(vv, list)} if k != "composition_square" else v["arm_vs_plan_on_sample"]) for k, v in diffs.items()},
        "fit_run_ids_not_permitted_by_allowance_v1": fit_not_permitted,
        "own_null_fallback": own_null,
        "ledger_rows_appended": appended,
        "expected_effect_pp": arm_expected,
        "sample_preparation_pins": pinned,
        "pending_pins": pending,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
