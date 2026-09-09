"""The one union the registered read does not compute: schema OR legality alone.

The verdict claims that adding the confidence flag to the deterministic judges
LOWERS their precision. The read reports schema alone, legality alone,
confidence+schema and all three -- but not the deterministic pair on its own, so
that claim was an inference. This measures it. Zero contacts.
"""

import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from slurp_logprob_judge_read import (  # noqa: E402
    build_rows,
    flag_at_budget,
    load_jsonl,
    precision_recall,
)

SP = Path(sys.argv[1])
ATTEMPT = Path(sys.argv[2])

rows = build_rows(
    trace=load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.trace.jsonl"),
    outputs=load_jsonl(ATTEMPT / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.outputs.jsonl"),
    per_sample=json.loads((SP / "per-sample.json").read_text(encoding="utf-8"))["per_sample"],
    inventory=json.loads((SP / "label-inventory.json").read_text(encoding="utf-8")),
)

schema = {sid for sid, r in rows.items() if r["judges"]["schema"]}
legality = {sid for sid, r in rows.items() if r["judges"]["legality"]}
score = {
    sid: -float(r["confidence"]["min_token_logprob"])
    for sid, r in rows.items()
    if r["confidence"].get("min_token_logprob") is not None
}
confidence, _ = flag_at_budget(score, 86)

out = {}
for target in ("intent_error", "slot_error", "unmatched_gold"):
    errors = {sid: bool(r["labels"][target]) for sid, r in rows.items()}
    out[target] = {
        "deterministic_pair_schema_or_legality": precision_recall(schema | legality, errors),
        "plus_confidence_all_three": precision_recall(
            schema | legality | confidence, errors
        ),
    }
print(json.dumps(out, indent=2))
(SP / "deterministic-pair.json").write_text(
    json.dumps(
        {
            "schema": "saea-slurp-logprob-deterministic-pair-v1",
            "model_contacts": 0,
            "note": (
                "the union the registered read does not compute: the two deterministic "
                "judges on their own, so the claim that adding the confidence flag lowers "
                "their precision is measured rather than inferred"
            ),
            "results": out,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
    newline="\n",
)
