"""Build the batch queue for the loop iteration chain (extracted from batch_chain_tfrl_i1.sh so it is testable).

``build_steps(t, which, short, facts_loader, only)``: ``which`` is column or proposers; ``only`` (proposers only) is "", "typed" or "ace"
(env TFRL_ONLY) and selects one cell -- used to queue the reflector alone after the typed cell is flown and sealed. Orders are
renumbered from 1 over the selected cells.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tfrl_family as tf  # noqa: E402

ROOT = "docs/readiness/2026-10-11-slurp-tfrl-loop-i%d-%s-v1"


def build_steps(t, which, short, facts_loader, only=""):
    steps = []
    if only not in ("", "typed", "ace"):
        raise ValueError("TFRL_ONLY must be typed or ace")
    if only and which != "proposers":
        raise ValueError("TFRL_ONLY applies to the proposers mode only")
    if which == "column":
        slug = f"tfrl-loop-i{t}-fold-b"
        facts = facts_loader(ROOT % (t, "fold-b") + "/registered-facts-v1.json")
        contacts = int(facts["accounting"]["contacts_per_row"])
        upper = slug.upper()
        steps.append({
            "order": 1, "short": short, "kind": "cell",
            "experiment": f"slurp-native-stage3-{slug}-v1", "cell": f"slurp-native-stage3-{slug}-v1",
            "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1", "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
            "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
            "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1", "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
            "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
            "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
            # the smoke's attempt id comes from the family (the rec1 id after its single recovery); the arm keeps its first-attempt id
            "smoke_attempt_id": tf.names(t, "smoke")["attempt_id"],
            "expected_rows": 1080, "contacts_per_row": contacts, "ceiling_per_row": contacts, "notool": True,
            "owner": f"root-slurp-native-stage3-{slug}-v1",
        })
    else:
        selected = [(tag, kind) for tag, kind in (("proposer", "typed"), ("ace-reflector", "ace")) if only in ("", kind)]
        for order, (tag, kind) in enumerate(selected, start=1):
            slug = f"tfrl-{tag}-i{t}"
            facts = facts_loader(ROOT % (t, "proposers") + "/registered-facts-v1.json")
            rows = int(facts["rows"][kind])
            steps.append({
                "order": order, "short": f"{short}-{kind}", "kind": "cell",
                "experiment": f"slurp-native-stage3-{slug}-v1", "cell": f"slurp-native-stage3-{slug}-v1",
                "smoke_experiment": None, "smoke_cell": None, "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
                "run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-V1", "fit_run_id": None,
                "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
                "smoke_run_id": None, "smoke_attempt_id": None,
                "expected_rows": rows, "contacts_per_row": 1, "ceiling_per_row": 1, "notool": True,
                "owner": f"root-slurp-native-stage3-{slug}-v1",
            })
    return steps


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


if __name__ == "__main__":
    out = build_steps(int(os.environ["TFRL_ITER"]), os.environ["TFRL_WHICH"], os.environ["TFRL_SHORT"], _load,
                      os.environ.get("TFRL_ONLY", ""))
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
