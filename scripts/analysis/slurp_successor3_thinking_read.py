#!/usr/bin/env python3
"""slurp_successor3_thinking_read.py -- the preregistered verdict stage of the SUCCESSOR-3 test-sample read (the Thinking system vs the sealed successor-2 column).

Package ``docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/``. The official scoring and the paired contrast are done by
``scripts/analysis/stage3_paired_read.py`` (pair mode, ``--strata-source scorer``; the wrapper ``scripts/flights/nx/successor3_thinking_read.sh``). THIS stage reads only that
pass's AGGREGATE output (``per-scenario-tables.json``: post-stratified natural mixture and equal-stratum, ``score-contrasts.json``) and the recipe, and applies the
registered rule. It never opens a per-row score, a gold label, a transcript or a model output; nothing from the sample is printed before the aggregate it writes.

Words (successor 2's, claims_benefit false): d = Thinking minus the sealed successor-2 column; |o| the DECLARED DEV twin offset (recipe ``declared_flight_offset``).
  HARM        the CI95 upper bound of d on SLU-F1 or on intent is below -|o| (a resolved loss beyond the declared offset)
  NEUTRAL     not HARM, and the CI95 lower bound of d on SLU-F1 and on intent is at or above -harm_margin (2.5 pp)
  UNRESOLVED  otherwise
Reported beside the word, never a word: ``gain_reported_not_claimed`` (SLU CI95 lower bound above |o_slu|), the point against the 2.5 pp bar, the equal-stratum contrast.
The no-in-chain-replicate LIMITATION is written into the output and printed with the word.

    python -B scripts/analysis/slurp_successor3_thinking_read.py --stage verdict --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
sys.path.insert(0, str(_REPO / "scripts" / "flights" / "nx"))

import successor3_thinking_family as fam  # noqa: E402

SCHEMA = "saea-slurp-successor3-thinking-verdict-v1"
VERDICT_WORDS = ("NEUTRAL", "HARM", "UNRESOLVED")
LIMITATION = ("NO IN-CHAIN REPLICATE on the sample: the null is the DECLARED DEV P3.1 twin offset (a different roster and n), not a measured null of the sample. "
              "A milestone development read (owner decisions 28, 151, 301); never a test claim; claims_benefit is false.")


class ReadError(Exception):
    pass


def verdict_word(slu: Mapping, intent: Mapping, offset: Mapping, margin_pp: float = fam.HARM_MARGIN) -> str:
    """``slu`` / ``intent``: ``{"delta_pp", "ci95_pp": [lo, hi]}`` of Thinking minus successor 2; ``offset``: ``{"slu_pp", "intent_pp"}`` (absolute values)."""

    o_slu, o_int = abs(float(offset["slu_pp"])), abs(float(offset["intent_pp"]))
    if float(slu["ci95_pp"][1]) < -o_slu or float(intent["ci95_pp"][1]) < -o_int:
        return "HARM"
    if float(slu["ci95_pp"][0]) >= -margin_pp and float(intent["ci95_pp"][0]) >= -margin_pp:
        return "NEUTRAL"
    return "UNRESOLVED"


def beside(slu: Mapping, intent: Mapping, equal: Mapping, offset: Mapping, margin_pp: float = fam.HARM_MARGIN) -> dict:
    o_slu = abs(float(offset["slu_pp"]))
    return {
        "gain_reported_not_claimed": bool(float(slu["ci95_pp"][0]) > o_slu),
        "slu_point_at_or_above_the_bar": bool(float(slu["delta_pp"]) >= margin_pp),
        "intent_point_pp": round(float(intent["delta_pp"]), 4),
        "equal_stratum_slu": {"delta_pp": round(float(equal["slu_f1"]["delta_pp"]), 4), "ci95_pp": [round(float(x), 4) for x in equal["slu_f1"]["ci95_pp"]]},
        "equal_stratum_intent": {"delta_pp": round(float(equal["intent"]["delta_pp"]), 4), "ci95_pp": [round(float(x), 4) for x in equal["intent"]["ci95_pp"]]},
        "note": "reported, not part of the verdict word; the registered words are HARM / NEUTRAL / UNRESOLVED (claims_benefit false)"}


def verdict_from_pass(pass_dir: Path, recipe: Mapping) -> dict:
    tables = json.loads((pass_dir / "per-scenario-tables.json").read_text(encoding="utf-8"))
    contrasts = json.loads((pass_dir / "score-contrasts.json").read_text(encoding="utf-8"))
    selected = tables["natural_mixture"].get("selected_weighting")
    if selected != "post-stratified" or tables["natural_mixture"].get("roster_floored") is not True:
        raise ReadError(f"the natural-mixture slot is {selected!r}, not the post-stratified weighting of a floored roster")
    if contrasts.get("scorer_id") != fam.SCORER or int(contrasts.get("n_rows", -1)) != fam.ROWS:
        raise ReadError("the pass was not scored by slurp-slu-official-test over 3,010 rows")
    slu, intent = tables["natural_mixture"]["slu_f1"], tables["natural_mixture"]["intent"]
    offset = recipe["declared_flight_offset"]
    word = verdict_word(slu, intent, offset)
    return {
        "schema": SCHEMA, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "verdict": word, "verdict_words": list(VERDICT_WORDS), "limitation": LIMITATION, "harm_margin_pp": fam.HARM_MARGIN,
        "declared_flight_offset": {"slu_pp": offset["slu_pp"], "intent_pp": offset["intent_pp"]},
        "contrast_thinking_minus_successor2": {
            "slu_f1_post_stratified": {"delta_pp": round(float(slu["delta_pp"]), 4), "ci95_pp": [round(float(x), 4) for x in slu["ci95_pp"]],
                                       "left_pct": round(float(slu["left_pct"]), 4), "right_pct": round(float(slu["right_pct"]), 4)},
            "intent_post_stratified": {"delta_pp": round(float(intent["delta_pp"]), 4), "ci95_pp": [round(float(x), 4) for x in intent["ci95_pp"]],
                                       "left_pct": round(float(intent["left_pct"]), 4), "right_pct": round(float(intent["right_pct"]), 4)},
            "n_rows": contrasts["n_rows"]},
        "reported_beside_the_word": beside(slu, intent, tables["equal_scenario"], offset),
        "interval": {"kind": "prompt-cluster paired bootstrap", "draws": recipe["resampling"]["bootstrap_draws"], "seed": recipe["resampling"]["seed"], "level": "CI95"},
        "sources": {"per-scenario-tables.json": "post_stratified natural mixture slot", "score-contrasts.json": "scorer id, rows"},
        "contacts": {"model": 0, "server": 0, "encoder": 0, "tokenizer": 0}}


def render(result: Mapping) -> str:
    c, b = result["contrast_thinking_minus_successor2"], result["reported_beside_the_word"]
    s, i = c["slu_f1_post_stratified"], c["intent_post_stratified"]
    return "\n".join([
        f"# Successor 3 read -- verdict {result['verdict']}", "", f"LIMITATION: {result['limitation']}", "",
        f"Declared DEV twin offset: SLU {result['declared_flight_offset']['slu_pp']} pp, intent {result['declared_flight_offset']['intent_pp']} pp; harm margin {result['harm_margin_pp']} pp.", "",
        "| metric (post-stratified natural mixture) | successor 2 | Thinking | d (pp) | CI95 |", "| --- | ---: | ---: | ---: | --- |",
        f"| SLU-F1 | {s['left_pct']:.2f} | {s['right_pct']:.2f} | {s['delta_pp']:+.2f} | [{s['ci95_pp'][0]:+.2f}, {s['ci95_pp'][1]:+.2f}] |",
        f"| intent | {i['left_pct']:.2f} | {i['right_pct']:.2f} | {i['delta_pp']:+.2f} | [{i['ci95_pp'][0]:+.2f}, {i['ci95_pp'][1]:+.2f}] |", "",
        f"Beside the word: gain reported, not claimed: {b['gain_reported_not_claimed']}; SLU point at or above the 2.5 pp bar: {b['slu_point_at_or_above_the_bar']}; "
        f"equal-stratum SLU d {b['equal_stratum_slu']['delta_pp']:+.2f} {b['equal_stratum_slu']['ci95_pp']}.", ""]) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("verdict",), required=True)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "."))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    args = parser.parse_args(argv)
    try:
        recipe = json.loads((args.repo_root / fam.package_file("analysis-recipe-v1.json")).read_text(encoding="utf-8"))
        root = args.data_root / "analysis" / fam.READ_RUN
        pass_dir = root / "vs-comparator"
        if not (pass_dir / "per-scenario-tables.json").is_file():
            raise ReadError(f"missing aggregate pass output {pass_dir}/per-scenario-tables.json")
        result = verdict_from_pass(pass_dir, recipe)
    except (ReadError, KeyError, OSError, ValueError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    out = root / "successor3-verdict.json"
    if out.exists():
        print(f"REFUSED: {out} exists (write-once)", file=sys.stderr)
        return 6
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "successor3-verdict.md").write_text(render(result), encoding="utf-8")
    print(render(result))
    print(json.dumps({"written": str(out), "verdict": result["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
