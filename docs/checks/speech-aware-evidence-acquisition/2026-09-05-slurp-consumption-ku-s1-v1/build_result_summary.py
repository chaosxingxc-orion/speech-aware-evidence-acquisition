"""Assemble the KU-S1c verdict's machine-readable result-summary.json.

Reads only the receipts beside it in this directory; zero model, GPU, tool,
embedding, network and gold contacts. Run from this directory::

    python build_result_summary.py --out result-summary.json
"""

import argparse
import hashlib
import json
from pathlib import Path

CHECKS = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()

read = load(CHECKS / "read.json")
flight = load(CHECKS / "flight-receipt-ku-s1c.json")
smoke = load(CHECKS / "smoke-receipt-ku-s1c.json")
fit = load(CHECKS / "prompt-fit.json")
containment = load(CHECKS / "containment-analysis.json")

official = read["official"]
paired = read["paired_ku_s1c_over_closed_list"]


def contrast(population, metric):
    entry = paired[population][metric]
    boot = entry["bootstrap"] or {}
    return {
        "left_mean_pct": round(100 * entry["left_mean"], 2),
        "right_mean_pct": round(100 * entry["right_mean"], 2),
        "delta_pp": round(100 * entry["delta"], 2),
        "ci90_pp": [
            round(100 * boot.get("ci_low", float("nan")), 2),
            round(100 * boot.get("ci_high", float("nan")), 2),
        ],
        "saves": entry["saves"],
        "harms": entry["harms"],
        "ties": entry["ties"],
        "sign_test_p": entry["sign_test_p"],
        "n": entry["n"],
    }


METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slot_f1_exact_precision",
    "slot_f1_exact_recall",
)

realized = read["realized_contacts"] or {}
contact_count = realized.get("contact_count")
intent_delta = 100 * paired["unexposed_new500"]["scenario_action_exact"]["delta"]
slu_delta = 100 * (
    official["KU-S1C"]["aggregate"]["slu_f1"]
    - official["CLOSED-LIST"]["aggregate"]["slu_f1"]
)
intent_corpus_delta = 100 * (
    official["KU-S1C"]["aggregate"]["intent_accuracy"]
    - official["CLOSED-LIST"]["aggregate"]["intent_accuracy"]
)

document = {
    "schema": "saea-slurp-ku-s1c-result-summary-v1",
    "study": "speech-aware-evidence-acquisition",
    "cell": "KU-S1c",
    "run_id": "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1",
    "attempt_id": realized.get("attempt_id"),
    "study_commit": realized.get("study_commit"),
    "status": realized.get("status"),
    "profile": "bounded-discovery-probe",
    "preregistration": (
        "docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-preregistration.md"
    ),
    "verdict": (
        "REPORTED, NEVER DECIDED. KU-S1c carries no admission gate of its own; it is "
        "the equal-contact, no-knowledge control every two-contact SLURP cell's delta "
        "is stated net of."
    ),
    "companion_cell_ku_s1": {
        "status": "REFUSED BEFORE REGISTRATION -- unread, neither ADMITTED nor NULL nor HARMFUL",
        "receipt": "containment-analysis.json",
        "receipt_sha256": sha(CHECKS / "containment-analysis.json"),
        "supply_refusal_rate": 1.0,
        "phase2_control_turn_refusals_under_size_full": containment["snapshots"][
            "slurp-kb-size-full"
        ]["revise_control_turn_collision_count"],
        "phase2_control_turn_refusals_under_bound_snapshot": containment["snapshots"][
            "slurp-kb-size-full-label-prior-speaker"
        ]["revise_control_turn_collision_count"],
    },
    "official": {
        name: entry["aggregate"] for name, entry in official.items()
    },
    "official_identity_check": {
        name: entry["identity_check"] for name, entry in official.items()
    },
    "n_predicted": read["n_predicted"],
    "headline": {
        "intent_new500_delta_pp": round(intent_delta, 2),
        "intent_corpus_delta_pp": round(intent_corpus_delta, 2),
        "slu_f1_corpus_delta": round(slu_delta, 2),
        "realized_contacts_per_row": realized.get("contacts_per_row"),
        "control_turn_effect_intent_pp_pooled": round(
            100 * read["paired_draft_over_closed_list"]["pooled_1000"][
                "scenario_action_exact"
            ]["delta"],
            2,
        ),
        "second_contact_effect_intent_pp_pooled": round(
            100 * read["paired_revise_over_draft"]["pooled_1000"][
                "scenario_action_exact"
            ]["delta"],
            2,
        ),
        "second_contact_effect_intent_pp_new500": round(
            100 * read["paired_revise_over_draft"]["unexposed_new500"][
                "scenario_action_exact"
            ]["delta"],
            2,
        ),
        "gain_per_extra_contact_slu_f1_over_own_draft": round(
            100
            * (
                official["KU-S1C"]["aggregate"]["slu_f1"]
                - official["KU-S1C-DRAFT"]["aggregate"]["slu_f1"]
            ),
            2,
        ),
        "gain_per_extra_contact_slu_f1_over_comparator": round(slu_delta, 2),
        "answers_the_second_contact_changed": read["answer_churn"][
            "revise_vs_own_draft_pooled_1000"
        ],
    },
    "paired": {
        population: {metric: contrast(population, metric) for metric in METRICS}
        for population in ("unexposed_new500", "pooled_1000", "prior_exposed_dev500")
    },
    # The decomposition: KU-S1c changes two things against the comparator at
    # once -- it adds a CONTROL turn and it adds a CONTACT -- and the draft
    # phase's own sealed responses separate them.
    "paired_draft_over_closed_list": read["paired_draft_over_closed_list"],
    "paired_revise_over_draft": read["paired_revise_over_draft"],
    "entity_supply": read["entity_supply"],
    "weightings": read["weightings"],
    "per_stratum": read["per_stratum"],
    "answer_churn": read["answer_churn"],
    "realized": realized,
    "prompt_fit": {
        "receipt_sha256": sha(CHECKS / "prompt-fit.json"),
        "generated_tokens": fit["contacts"]["generations"],
        "apply_template_calls": fit["contacts"]["POST /apply-template"],
        "tokenize_calls": fit["contacts"]["POST /tokenize"],
        "reserve_decision": fit["reserve_decision"],
    },
    "smoke": {
        "run_id": "SAEA-SLURP-KU-S1C-SMOKE-4-V1",
        "attempt_id": smoke["attempt_id"],
        "contacts": smoke["stages"]["run_phases"]["contact_count"],
        "phases": smoke["stages"]["run_phases"]["phases"],
        "manifest_sha256": smoke["stages"]["seal"]["manifest_sha256"],
        "numbers_are_a_wiring_proof": True,
    },
    "flight_receipt_sha256": sha(CHECKS / "flight-receipt-ku-s1c.json"),
    "read_sha256": sha(CHECKS / "read.json"),
    "populations": read["populations"],
    "bootstrap": read["bootstrap"],
    "boundary": (
        "Dev roster only. No test contact, no superiority claim, no generalization "
        "claim, no Stage-3 activity. Gold opened once, scoring-side, after the seal."
    ),
}

args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(
    json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)
print("wrote", args.out, sha(args.out))
print(json.dumps(document["headline"], indent=2))
print(json.dumps(document["official"], indent=2))
