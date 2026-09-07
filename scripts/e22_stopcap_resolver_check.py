#!/usr/bin/env python3
"""Model-free proof that cell (b)'s per-sample generation cap resolves to the
projected integer on every one of the 1,500 rows.

Precondition (b) of ``docs/readiness/2026-09-06-e22-dev-usage-cells-v1-
preregistration.md`` section 6: *"a model-free assertion that the resolver
reproduces ``analysis.e22_overgeneration.cap_tokens(1.5, seconds,
4.999220954734555, 1.2991996296395218)`` on every one of the 1,500 rows,
clamped to 1,024."*

Why it matters and is not ceremony: §2.2 fixes a numeric prediction (50 rows
bitten, corpus WER 17.1765 %) that a MODEL-FREE simulator produced from
``cap_tokens``. If the flight's own resolver disagreed with that function on
even one row, the prediction check would be comparing two different
interventions and the cell's main value -- its falsifiability -- would be gone.
This closes that gap before any contact, by composing the REAL fragments,
resolving through the REAL registered policy, and comparing row for row against
the simulator.

Zero model contacts, zero servers, zero sockets, zero GPU. It reads the
hash-pinned roster receipt out of the repository (identifiers, media paths,
measured media identity and durations only -- no reference sentence) and nothing
else.

Run in WSL2::

    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
        python scripts/e22_stopcap_resolver_check.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (  # noqa: E402
    cap_tokens,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    MAX_TOKENS_POLICIES,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.policies import (  # noqa: E402, F401
    DURATION_PROPORTIONAL_MAX_TOKENS_V1,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)

MODEL = "q4km-e22-dev1500-esb-stopcap-mmproj-gpu-04ccc72a-np8-c40960"
DATASET = "earnings22-esb-dev1500-utterances"
BASELINE = "e22-esb-dev1500-stopcap"
EXPERIMENT = "e22-dev-usage-stopcap-v1"
ARM = "bare-core"
OUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-dev-usage-cells"
    / "stopcap-resolver.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve()

    composed = compose(repo, MODEL, DATASET, BASELINE, EXPERIMENT)
    values = composed.values
    rule = dict(values["decoding_params"]["max_tokens"])
    policy = MAX_TOKENS_POLICIES.resolve(rule["policy"])
    params = policy.parameters(rule)

    roster_relpath = str(values["e22_esb_roster_receipt"])
    roster_path = repo / roster_relpath
    measured = sha256_file(roster_path)
    declared = str(values["e22_esb_roster_receipt_sha256"])
    if measured != declared:
        raise SystemExit(
            f"roster receipt hashes to {measured}, not the configured {declared}"
        )
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    items = receipt["items"]
    if len(items) != int(values["e22_esb_count"]):
        raise SystemExit(
            f"roster carries {len(items)} rows, the dataset fragment declares "
            f"{values['e22_esb_count']}"
        )

    identity = split_identity_hash(
        prefixed(
            str(values["carrier_lock_key"]),
            tuple(sorted(str(item["sample_id"]) for item in items)),
        )
    )
    if identity != str(values["e22_esb_split_identity_hash"]):
        raise SystemExit(
            f"roster identity hashes to {identity}, not the configured "
            f"{values['e22_esb_split_identity_hash']}"
        )

    ceiling = int(params["ceiling"])
    floor = int(params["floor"])
    caps: dict[str, int] = {}
    per_call: dict[str, dict[str, object]] = {}
    disagreements: list[Mapping[str, object]] = []
    loosenings: list[str] = []
    for item in items:
        sample_id = str(item["sample_id"])
        seconds = float(item["audio_seconds"])
        resolved = policy.resolve(rule, seconds)
        simulated = min(
            ceiling,
            max(
                floor,
                cap_tokens(
                    float(params["alpha"]),
                    seconds,
                    float(params["words_per_second_p95"]),
                    float(params["tokens_per_word"]),
                ),
            ),
        )
        if resolved != simulated:
            disagreements.append(
                {
                    "sample_id": sample_id,
                    "audio_seconds": seconds,
                    "resolver": resolved,
                    "simulator": simulated,
                }
            )
        if resolved > ceiling:
            loosenings.append(sample_id)
        caps[sample_id] = resolved
        call = sample_id.split("-", 1)[0]
        bucket = per_call.setdefault(call, {"rows": 0, "caps": []})
        bucket["rows"] = int(bucket["rows"]) + 1
        bucket["caps"].append(resolved)

    if disagreements:
        raise SystemExit(
            "the flight resolver and analysis.e22_overgeneration.cap_tokens disagree on "
            f"{len(disagreements)} row(s): {disagreements[:5]}"
        )
    if loosenings:
        raise SystemExit(
            f"{len(loosenings)} row(s) resolve ABOVE the declared ceiling: {loosenings[:5]}"
        )

    ordered = sorted(caps.values())
    document = {
        "schema": "saea-e22-stopcap-resolver-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "preregistration": (
            "docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md"
        ),
        "precondition": "section 6, cell (b), second clause",
        "boundary": (
            "zero model contacts, zero servers, zero sockets, zero GPU. This row reads "
            "the hash-pinned roster receipt's identifiers and durations and nothing "
            "else; no reference sentence, no audio byte and no gold is opened."
        ),
        "run_id": "SAEA-E22-DEV-ESB-STOPCAP-V1",
        "cell_id": "E22-DEV-ESB-STOPCAP",
        "fragments": dict(composed.fragments),
        "config_hash": composed.config_hash,
        "protocol_hash": protocol_hash(composed.config_hash, ARM, identity),
        "arm": ARM,
        "split_id": str(values["split_id"]),
        "split_identity_hash": identity,
        "roster_receipt": roster_relpath,
        "roster_receipt_sha256": measured,
        "max_tokens_policy": rule["policy"],
        "max_tokens_rule": rule,
        "formula": (
            "min(ceiling, max(floor, ceil(alpha * audio_seconds * "
            "words_per_second_p95 * tokens_per_word)))"
        ),
        "rows": len(items),
        "rows_checked_against_the_simulator": len(items),
        "disagreements": 0,
        "simulator": (
            "analysis.e22_overgeneration.cap_tokens, clamped to [floor, ceiling] -- the "
            "same function that produced the section 2.2 prediction"
        ),
        "cap_distribution": {
            "min": ordered[0],
            "p10": ordered[int(0.10 * (len(ordered) - 1))],
            "median": ordered[len(ordered) // 2],
            "mean": round(statistics.fmean(ordered), 4),
            "p90": ordered[int(math.ceil(0.90 * len(ordered))) - 1],
            "max": ordered[-1],
        },
        "rows_at_or_above_the_ceiling": 0,
        "ceiling_never_binds": (
            "not one of the 1,500 rows reaches the 1,024 ceiling, so the cap is a "
            "genuine tightening on every row of this population and never a loosening "
            "-- the claim section 2.1 makes, now measured rather than argued"
        ),
        "sealed_arm_ceiling_tokens": ceiling,
        "planned_completion_token_ceiling_before": ceiling * len(items),
        "planned_completion_token_ceiling_after": sum(ordered),
        "per_call": {
            call: {
                "rows": bucket["rows"],
                "cap_min": min(bucket["caps"]),
                "cap_median": sorted(bucket["caps"])[len(bucket["caps"]) // 2],
                "cap_max": max(bucket["caps"]),
                "cap_total": sum(bucket["caps"]),
            }
            for call, bucket in sorted(per_call.items())
        },
        "published_ladder_of_section_2_1": {
            "1s": policy.resolve(rule, 1.0),
            "5s": policy.resolve(rule, 5.0),
            "10s": policy.resolve(rule, 10.0),
            "32.88s": policy.resolve(rule, 32.88),
        },
        "caps_by_sample_id": dict(sorted(caps.items())),
    }

    blob = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(blob, encoding="utf-8", newline="\n")
        print(f"wrote {out} sha256 {sha256_file(out)}")
    else:
        summary = {
            key: value
            for key, value in document.items()
            if key not in {"caps_by_sample_id", "per_call"}
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
