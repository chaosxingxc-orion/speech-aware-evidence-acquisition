#!/usr/bin/env python3
"""Render the sealed GEPA run's proposal outputs for the curation step.

MODEL-FREE. One JSON object per line: {"group_id", "carrier_sample_id", "response_text"}. The
response text is the sealed row's own model response, VERIFIED against its response_text_sha256,
and it lives only in this data-root file -- never in Git and never in a receipt. The join from a
flown row to its group is the prepared groups artifact's own carrier map.

The sibling of scripts/flights/batch/adv1_render_advantage_outputs.py, and the same discipline:
counts and digests are printed, text never is.
"""
import argparse
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

DATA = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR", "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data"
    )
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="SAEA-SLURP-STAGE3-GEPA-R01-V1")
    ap.add_argument("--attempt", default="attempt-slurp-native-stage3-gepa-r01-v1-generation")
    ap.add_argument(
        "--groups",
        default=str(DATA / "prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1/gepa-groups-v1.json"),
    )
    ap.add_argument(
        "--scope-receipt", default="docs/receipts/rosters/slurp-stage3-construction-r01c.json"
    )
    ap.add_argument(
        "--permitted-out", default=None,
        help=(
            "where to write the permitted roster: the GROUP rows (the rows the reflections were "
            "made from), not the carriers. Defaults beside the outputs."
        ),
    )
    ap.add_argument("--out-dir", default=str(DATA / "prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1"))
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    groups = json.loads(Path(a.groups).read_text(encoding="utf-8"))
    by_carrier = {g["carrier_sample_id"]: g for g in groups["groups"]}

    outputs = DATA / "runs" / a.run / a.attempt / f"{a.run}.outputs.jsonl"
    target = out / "gepa-proposal-outputs-v1.jsonl"
    kept = 0
    unmatched = 0
    with io.open(outputs, encoding="utf-8") as fh, io.open(
        target, "w", encoding="utf-8", newline="\n"
    ) as w:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            sample_id = row["sample_id"]
            text = row.get("text")
            if not isinstance(text, str):
                raise SystemExit(f"sealed row {sample_id} carries no text")
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != row.get(
                "response_text_sha256"
            ):
                raise SystemExit(
                    f"sealed row {sample_id}: text digest differs from response_text_sha256"
                )
            group = by_carrier.get(sample_id)
            if group is None:
                unmatched += 1
                continue
            w.write(
                json.dumps(
                    {
                        "group_id": group["group_id"],
                        "carrier_sample_id": sample_id,
                        "response_text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            kept += 1
    print("gepa-proposal-outputs rows", kept, "unmatched", unmatched, "sha256", sha(target))

    scope = out / "outer-construction-roster.json"
    shutil.copyfile(a.scope_receipt, scope)
    print("outer-construction-roster.json from", a.scope_receipt, "sha256", sha(scope))

    # The PERMITTED roster is the union of the GROUP rows, not the carriers: those are the rows an
    # authored GEPA delta may cite. It is a pure selection of the R01C receipt.
    permitted_path = Path(a.permitted_out) if a.permitted_out else out / "permitted-roster.json"
    parent = json.loads(Path(a.scope_receipt).read_text(encoding="utf-8"))
    wanted = {row for g in groups["groups"] for row in g["row_sample_ids"]}
    items = [item for item in parent["items"] if item["sample_id"] in wanted]
    missing = wanted - {item["sample_id"] for item in items}
    if missing:
        raise SystemExit(
            f"{len(missing)} group row(s) are not in {a.scope_receipt}; first {sorted(missing)[0]}"
        )
    permitted = dict(parent)
    permitted["roster_id"] = "SLURP-STAGE3-GEPA-R01C-GROUP-ROWS-V1"
    permitted["items"] = items
    permitted["excluded_count"] = len(parent["items"]) - len(items)
    permitted["selection_rule"] = (
        "R01C restricted to the union of the GEPA groups' row_sample_ids -- the rows the "
        "reflections were made from, which are the rows an authored GEPA delta may cite. A pure "
        "selection; no rng, no score, no label."
    )
    permitted.pop("split_identity_hash", None)
    permitted_path.write_text(
        json.dumps(permitted, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("permitted-roster.json rows", len(items), "sha256", sha(permitted_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
