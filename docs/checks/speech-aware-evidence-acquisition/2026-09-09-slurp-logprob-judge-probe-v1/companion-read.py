"""The three readings the flight owes beside the registered read.

Zero model contacts, zero GPU, no dataset access of its own beyond the same
five files the registered read consumes plus the sealed manifest and the gold
scenario the null replicate already uses as a reporting stratum.

1. **The per-scenario breakdown** of the primary statistic and of the two
   intent-span statistics: AUROC for intent error within each gold scenario,
   with its n. Reported per the standing rule that every verdict carries the
   per-stratum table, and read with the null replicate's own warning attached:
   a per-stratum reading is not admissible without its own replicate.

2. **The token diagnostic** the 0.69-vs-0.85 gap demands: WHICH token carries
   the row minimum. The 2026-08-14 P1 ceiling verdict found every logprob flag
   on Earnings landing on function words rather than entities; this asks the
   same question of a structured answer, where the candidates are JSON
   punctuation, the label, and the filler text.

3. **The cost of the decoding parameter**, against the comparator's own
   realized rate and against the greedy replicate null's -- the second is the
   honest reference, because the null already measured how much two byte
   identical passes of this cell differ on wall clock (1.7 %).
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from slurp_logprob_judge_read import (  # noqa: E402
    auroc,
    load_jsonl,
    logprobs_by_request,
    row_confidence,
    token_entries,
    _token_offsets,
    _value_span,
)

SP = Path(sys.argv[1])
ATTEMPT = Path(sys.argv[2])

trace = load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.trace.jsonl")
outputs = load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.outputs.jsonl")
per_sample = json.loads((SP / "per-sample.json").read_text(encoding="utf-8"))["per_sample"]

by_request = logprobs_by_request(trace)
labels = {
    str(row["sample_id"]): float(row["scenario_action_exact"]) == 0.0 for row in per_sample
}

# -- gold scenario, as a REPORTING STRATUM only ----------------------------
lock = load_lock(umbrella_lock_path())
root = data_root()
split = load_slurp_split(lock, root, "devel")
gold_scenario = {}
for item in split:
    sid = getattr(item, "sample_id", None)
    scen = getattr(item, "scenario", None)
    if isinstance(sid, str) and isinstance(scen, str):
        gold_scenario[sid] = scen
print("gold scenarios indexed:", len(gold_scenario))

STATS = ("min_token_logprob", "intent_mean_token_logprob", "intent_min_token_logprob")

confidence = {}
minimum_token = {}
for row in outputs:
    sid = str(row["sample_id"])
    logprobs = by_request[str(row["request_id"])]
    values = row_confidence(logprobs)
    values.pop("reconstructed_text", None)
    confidence[sid] = values

    entries = token_entries(logprobs)
    offsets = _token_offsets(entries)
    text = "".join(str(e.get("token", "")) for e in entries)
    index = min(range(len(entries)), key=lambda i: float(entries[i]["logprob"]))
    token = str(entries[index].get("token", ""))
    low, high = offsets[index]

    region = "other"
    for key in ("scenario", "action"):
        span = _value_span(text, key)
        if span and low < span[1] and high > span[0]:
            region = key + "_value"
            break
    else:
        span = _value_span(text, "filler")
        stripped = token.strip()
        if span and low < span[1] and high > span[0]:
            region = "filler_value"
        elif not stripped or all(ch in '{}[]":, ' for ch in stripped):
            region = "json_punctuation"
        elif '"type"' in text and text[low:high].strip('"') in {
            "type",
            "filler",
            "entities",
            "scenario",
            "action",
        }:
            region = "json_key"
    minimum_token[sid] = {"token": token, "region": region}

# 1. per-scenario ----------------------------------------------------------
by_scenario = defaultdict(list)
missing_scenario = []
for sid in confidence:
    scen = gold_scenario.get(sid)
    if scen is None:
        missing_scenario.append(sid)
        continue
    by_scenario[scen].append(sid)
print("rows with no gold scenario:", len(missing_scenario))

per_scenario = []
for scen in sorted(by_scenario):
    ids = by_scenario[scen]
    errs = [labels[sid] for sid in ids]
    entry = {
        "scenario": scen,
        "n": len(ids),
        "intent_errors": sum(1 for e in errs if e),
    }
    for stat in STATS:
        usable = [sid for sid in ids if confidence[sid].get(stat) is not None]
        if len(set(labels[sid] for sid in usable)) < 2:
            entry[stat] = None
            continue
        entry[stat] = round(
            auroc([-float(confidence[sid][stat]) for sid in usable], [labels[sid] for sid in usable]),
            4,
        )
    per_scenario.append(entry)

# 2. token diagnostic ------------------------------------------------------
region_counts = Counter(v["region"] for v in minimum_token.values())
region_by_error = defaultdict(Counter)
for sid, info in minimum_token.items():
    region_by_error["error" if labels[sid] else "correct"][info["region"]] += 1
top_tokens = Counter(v["token"] for v in minimum_token.values()).most_common(15)

document = {
    "schema": "saea-slurp-logprob-companion-read-v1",
    "model_contacts": 0,
    "n": len(confidence),
    "per_scenario": per_scenario,
    "per_scenario_caveat": (
        "a per-stratum reading is not admissible without its own replicate "
        "(SAEA-SLURP-DEV1000-NULL-REPLICATE-V1 moved intent by -5.13 to +5.41 pp "
        "across these same 18 scenarios with nothing changed)"
    ),
    "minimum_token_region": {
        "counts": dict(region_counts),
        "by_label": {k: dict(v) for k, v in region_by_error.items()},
        "top_tokens": top_tokens,
        "definition": (
            "the region of the reconstructed answer that the row's LOWEST-logprob "
            "generated token falls in: the scenario value, the action value, a "
            "filler value, a JSON key, JSON punctuation, or other"
        ),
    },
}
(SP / "companion-read.json").write_text(
    json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)

print("\n=== PER-SCENARIO (intent-error AUROC) ===")
print("%-16s %5s %6s %10s %10s %10s" % ("scenario", "n", "errs", "min_tok", "int_mean", "int_min"))
for e in per_scenario:
    print(
        "%-16s %5d %6d %10s %10s %10s"
        % (
            e["scenario"],
            e["n"],
            e["intent_errors"],
            e["min_token_logprob"],
            e["intent_mean_token_logprob"],
            e["intent_min_token_logprob"],
        )
    )
print("\n=== WHERE THE ROW MINIMUM LANDS ===")
print(json.dumps(document["minimum_token_region"], indent=2, default=str))
