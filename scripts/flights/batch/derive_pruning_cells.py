"""Derive the two decision-85 pruning cells' fragments from a sealed base cell (decision 97 picks the base).

Cells (owner decisions 85 and 97, 2026-09-21/22): P1 = Reviewer 3 -> 1 (``native_episode.roles.reviewer.max_iterations = 1``),
P0 = review-off (``roles.reviewer.max_iterations = 0``, ``roles.planner.max_iterations = 0``, ``native_episode.max_revisions
= 0``: the B0 form of item E1 on the locked plan). Each cell = the base cell's four fragments (baseline, smoke baseline,
experiment, smoke experiment) with the ids substituted and exactly the factor changed; the readiness package, campaign plan
and ledger rows are then derived by ``derive_plan_cell_registration.py`` (script-derived registrations, decision 58).

    python scripts/flights/batch/derive_pruning_cells.py --base review-primitives   # decision 97: R-PRIM not HARMFUL
    python scripts/flights/batch/derive_pruning_cells.py --base default-plan-lock   # decision 97: R-PRIM HARMFUL

Model-free; Windows Python from the study root; writes only the eight fragment files.
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASES = {
    "review-primitives": {"name": "review-primitives", "tag": "REVIEW-PRIMITIVES", "short": "R-PRIM"},
    "default-plan-lock": {"name": "default-plan-lock", "tag": "DEFAULT-PLAN-LOCK", "short": "PLAN"},
}
CELLS = {
    "prune-reviewer1": {
        "tag": "PRUNE-REVIEWER1", "short": "P1", "policy": "phase-native-candidates-review1-revise-v1", "ceiling": 7,
        "factor": "native_episode.roles.reviewer.max_iterations: 3 -> 1 (one Reviewer visit per revision round; everything else byte-identical to the base)",
        "edit": lambda ne: ne["roles"]["reviewer"].__setitem__("max_iterations", 1),
    },
    "prune-review-off": {
        "tag": "PRUNE-REVIEW-OFF", "short": "P0", "policy": "phase-native-candidates-solve-v1", "ceiling": 2,  # item E1 / cell B0
        "factor": "review-off: native_episode.roles.reviewer.max_iterations 3 -> 0, roles.planner.max_iterations 1 -> 0, max_revisions 1 -> 0 (the item-E1 / cell-B0 form: Perception -> Solver -> Delivery; everything else byte-identical to the base)",
        "edit": lambda ne: (ne["roles"]["reviewer"].__setitem__("max_iterations", 0),
                            ne["roles"]["planner"].__setitem__("max_iterations", 0),
                            ne.__setitem__("max_revisions", 0),
                            ne.__setitem__("review_loop", "off")),
    },
}


def rd(p):
    return io.open(p, encoding="utf-8", newline="").read()


def wr(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="").write(s)


def dump_like(raw, obj):
    m = re.search(r"\n( +)\"", raw)
    ind = len(m.group(1)) if m else 2
    return json.dumps(obj, indent=ind, ensure_ascii=False) + ("\n" if raw.endswith("\n") else "")


PROTECTED = ("saea-review-primitives-v1",)  # registry ids that contain the base slug must survive the substitution


def subst(text, base, cell):
    for i, tok in enumerate(PROTECTED):
        text = text.replace(tok, f"@@PROTECTED{i}@@")
    text = (text.replace(base["name"], cell_name(cell)).replace(base["tag"], CELLS[cell]["tag"])
            .replace(base["short"], CELLS[cell]["short"]))
    for i, tok in enumerate(PROTECTED):
        text = text.replace(f"@@PROTECTED{i}@@", tok)
    return text


def cell_name(cell):
    return cell


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, choices=sorted(BASES))
    ap.add_argument("--date", default="2026-09-22")
    a = ap.parse_args()
    base = BASES[a.base]
    for cell, spec in CELLS.items():
        for kind, suffix in (("baseline", "baseline-v1"), ("baseline", "smoke-4-baseline-v1"), ("experiment", "v1"), ("experiment", "smoke-4-v1")):
            src = f"configs/{kind}/slurp-native-{base['name']}-{suffix}.json"
            dst = f"configs/{kind}/slurp-native-{cell}-{suffix}.json"
            raw = rd(src)
            text = subst(raw, base, cell)
            obj = json.loads(text)
            if kind == "baseline":
                ne = obj["native_episode"]
                spec["edit"](ne)
                obj["policy"] = spec["policy"]  # the program whose max_contacts equals the pruned graph ceiling
                rows = 4 if "smoke" in suffix else 1080
                obj["native_contact_fit"]["contact_cap"] = rows * spec["ceiling"] * (int(obj["native_contact_fit"]["max_speech_packets"]) + 3)
                obj["what_this_is"] = (f"Cell {spec['short']} (owner decision 85, base chosen by decision 97 = cell {base['short']}): "
                                       f"{spec['factor']}. Derived {a.date} by scripts/flights/batch/derive_pruning_cells.py from {src}. "
                                       + str(obj.get("what_this_is", "")))
            else:
                rows = 4 if "smoke" in suffix else 1080
                gen, fit = rows * spec["ceiling"], rows * spec["ceiling"] * 4
                if isinstance(obj.get("execution_plan"), dict) and isinstance(obj["execution_plan"].get("planned_model_calls"), int):
                    obj["execution_plan"]["planned_model_calls"] = gen
                fb = obj.get("family_budget")
                if isinstance(fb, dict):
                    if "generation_calls_cap" in fb: fb["generation_calls_cap"] = gen
                    if "fit_endpoint_calls_cap" in fb: fb["fit_endpoint_calls_cap"] = fit
                for c in obj.get("cells", []):
                    r = c.get("readiness", {})
                    r["state"] = "held"
                    r["reason"] = (f"Registered {a.date} by the coordinator as pruning cell {spec['short']} (owner decisions 85 and 97; base = cell "
                                   f"{base['short']}, decision 97): {spec['factor']}. Derived from {src} by scripts/flights/batch/derive_pruning_cells.py; "
                                   "readiness flips only through scripts/flights/repin_cell.py after the decision receipt is minted. "
                                   "Stage-3 algorithm label (decision 101): none -- a pruning cell on the locked plan carries no training-free RL operator.")
                obj["stage3_algorithm"] = {"id": "none", "operators_used": [],
                                           "note": f"pruning cell {spec['short']} (decision 85): no training-free RL operator; base = cell {base['short']}"}
                if "purpose" in obj:
                    obj["purpose"] = f"Cell {spec['short']} (decision 85): {spec['factor']}. Base: cell {base['short']} (decision 97). " + str(obj["purpose"])
            wr(dst, dump_like(raw, obj))
            print("wrote", dst)


if __name__ == "__main__":
    main()
