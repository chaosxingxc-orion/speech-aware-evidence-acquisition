#!/usr/bin/env python3
"""Render the sealed GEPA run's proposal outputs for the curation step.

MODEL-FREE. One JSON object per line: {"group_id", "carrier_sample_id", "response_text"}. The
response text is the sealed row's own model response, VERIFIED against its response_text_sha256,
and it lives only in this data-root file -- never in Git and never in a receipt. The join from a
flown row to its group is the prepared groups artifact's own carrier map.

The sibling of scripts/flights/batch/adv1_render_advantage_outputs.py, and the same discipline:
counts and digests are printed, text never is -- including the two rosters, which are COMMITTED
receipts copied byte for byte rather than receipts synthesised here:

* outer-construction-roster.json -- the construction scope: the committed R01C receipt.
* permitted-roster.json -- the rows an authored delta may cite, and the store's SOURCE
  identity: the committed ADV-1 DISAGREEING receipt
  (docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json, 225 rows), exactly
  the receipt stage3-deltas-v1r and stage3-deltas-v2 pin, so the GEPA store shares its source
  identity with the CELL-1 / CELL-2 stores. NOT the carriers receipt, which is the FLOWN
  population, and not the groups receipt either: this store is append-only over v1r and its
  retained iteration-1 rows cite R01C rows outside the group union, which
  rails.semantic_knowledge_build refuses. What the renderer proves instead is CONTAINMENT --
  every group row, i.e. every row a contact was shown and therefore every row a GEPA-authored
  delta can legally cite, must be inside the receipt.
  core.semantic_knowledge_preparation verifies this file as a full saea-roster-receipt-v1
  (core.roster.read_roster) and then checks that identity against the registration, so a
  hand-made selection without a split_identity_hash is refused -- which is exactly what
  stopped the first release attempt.
"""
import os
import argparse
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

DATA = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
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
        "--permitted-receipt",
        default="docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json",
        help=(
            "the COMMITTED construction roster this store's authored rows may cite -- the "
            "ADV-1 disagreeing receipt that stage3-deltas-v1r and -v2 pin, not the carriers; "
            "copied byte for byte and required to CONTAIN every group row"
        ),
    )
    ap.add_argument(
        "--permitted-out", default=None,
        help=(
            "where to write the permitted roster (the committed receipt above, copied byte "
            "for byte). Defaults beside the outputs."
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

    # The PERMITTED roster is the ADV-1 disagreeing receipt: the rows an authored delta of this
    # append-only store may cite, and the split identity the release registration pins. It is
    # copied BYTE FOR BYTE (the ADV-1 discipline): a receipt synthesised here would carry no
    # split_identity_hash and core.roster would refuse it, and a receipt re-hashed here would be
    # a second implementation of the identity rule.
    #
    # The check is CONTAINMENT, not equality: every GROUP row -- every row a contact was shown,
    # and therefore every row a GEPA-authored delta can legally cite -- must be inside the
    # receipt. Equality against the group union was tried on 2026-09-24 and is wrong, because
    # the store retains iteration-1 rows whose citations lie outside that union. A carriers
    # receipt still fails this check: most group rows are not carriers.
    permitted_path = Path(a.permitted_out) if a.permitted_out else out / "permitted-roster.json"
    receipt = json.loads(Path(a.permitted_receipt).read_text(encoding="utf-8"))
    held = {str(item["sample_id"]) for item in receipt["items"]}
    wanted = {str(row) for g in groups["groups"] for row in g["row_sample_ids"]}
    outside = wanted - held
    if outside:
        raise SystemExit(
            f"{a.permitted_receipt} holds {len(held)} rows and does not contain "
            f"{len(outside)} of the groups artifact's {len(wanted)} group rows, so an "
            "authored delta keyed to one of them would be refused by "
            "rails.semantic_knowledge_build. The GEPA store's permitted roster is the ADV-1 "
            "disagreeing receipt "
            "docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json, the same "
            "receipt stage3-deltas-v1r and stage3-deltas-v2 pin; the carriers receipt is the "
            "FLIGHT population and is never the permitted roster."
        )
    shutil.copyfile(a.permitted_receipt, permitted_path)
    print(
        "permitted-roster.json from", a.permitted_receipt,
        "roster_id", receipt.get("roster_id"),
        "rows", len(held),
        "group rows contained", len(wanted),
        "split_identity", receipt.get("split_identity_hash"),
        "sha256", sha(permitted_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
