"""The smoke's acceptance, checked with the study's OWN accessors.

Zero contacts. The join is the outputs row's own ``request_id`` (the field the
sealed row carries), and the hash is the adapter's own ``_logprobs_sha256`` --
neither reimplemented here, because a checker that reimplements the thing it
checks proves only that two guesses agree.
"""

import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "scripts"))

from speech_aware_evidence_acquisition.core.model.adapter import (  # noqa: E402
    _logprobs_sha256,
)
from slurp_logprob_judge_read import (  # noqa: E402
    load_jsonl,
    logprobs_by_request,
    row_confidence,
    token_entries,
)

RUN_DIR = Path(sys.argv[1])
trace_path = sorted(RUN_DIR.rglob("*.trace.jsonl"))[-1]
outputs_path = sorted(RUN_DIR.rglob("*.outputs.jsonl"))[-1]

trace = load_jsonl(trace_path)
outputs = load_jsonl(outputs_path)

by_request = logprobs_by_request(trace)
payloads = {
    str(r["record_id"])[: -len("/logprobs")]: r["payload"]
    for r in trace
    if r.get("channel") == "MODEL_LOGPROBS"
}

failures = []
report = []
for row in outputs:
    rid = str(row["request_id"])
    sid = str(row["sample_id"])
    if rid not in by_request:
        failures.append("%s (%s): NO MODEL_LOGPROBS record" % (rid, sid))
        continue
    logprobs = by_request[rid]
    payload = payloads[rid]
    entries = token_entries(logprobs)
    alt_counts = sorted({len(e.get("top_logprobs") or []) for e in entries})
    first_is_sampled = all(
        (e.get("top_logprobs") or [{}])[0].get("token") == e.get("token")
        and (e.get("top_logprobs") or [{}])[0].get("logprob") == e.get("logprob")
        for e in entries
    )
    reconstructed = "".join(str(e.get("token", "")) for e in entries)
    sealed_text = row.get("text")
    matches = reconstructed == sealed_text
    declared = payload.get("logprobs_sha256")
    recomputed = _logprobs_sha256(logprobs)
    requested_k = payload.get("requested_top_logprobs")

    report.append(
        {
            "request_id": rid,
            "sample_id": sid,
            "generated_tokens": len(entries),
            "top_logprobs_counts": alt_counts,
            "first_alt_is_sampled_token": first_is_sampled,
            "reconstruction_equals_sealed_text": matches,
            "requested_top_logprobs": requested_k,
            "logprobs_sha256_recomputes": declared == recomputed,
            "min_token_logprob": row_confidence(logprobs)["min_token_logprob"],
            "sealed_text": sealed_text,
        }
    )
    if alt_counts != [5]:
        failures.append("%s: top_logprobs counts %s, not exactly 5" % (rid, alt_counts))
    if not first_is_sampled:
        failures.append("%s: the first alternative is not the sampled token" % rid)
    if not matches:
        failures.append(
            "%s: reconstruction %r != sealed text %r" % (rid, reconstructed, sealed_text)
        )
    if requested_k != 5:
        failures.append("%s: requested_top_logprobs %r, not 5" % (rid, requested_k))
    if declared != recomputed:
        failures.append("%s: logprobs_sha256 does not recompute" % rid)

result = {
    "trace": str(trace_path),
    "outputs": str(outputs_path),
    "sealed_rows": len(outputs),
    "model_logprobs_records": len(by_request),
    "rows": report,
    "failures": failures,
    "acceptance": "PASS" if not failures and len(by_request) == len(outputs) else "FAIL",
}
print(json.dumps(result, indent=2))
out = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if out is not None:
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
raise SystemExit(0 if result["acceptance"] == "PASS" else 2)
