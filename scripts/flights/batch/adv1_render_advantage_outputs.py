"""Root preparation for S3-5 (spec S3-5 / S3-4s): materialise the three inputs of scripts/flights/batch/adv1_to_deltas.sh
under prepared/SAEA-SLURP-STAGE3-DELTAS-V1 from already-sealed, committed bytes. Model-free; prints counts and digests only.

* advantage-outputs-v1.jsonl -- one {"sample_id", "response_text", "disagreement"} per sealed ADV-1 row: response_text is
  the row's raw model response (the sealed outputs.jsonl `text`, verified against its response_text_sha256), disagreement
  is S3-3's best-minus-worst score for that row (pairs.json). The statement text lives ONLY in this data-root file.
* outer-construction-roster.json -- the construction scope: the committed R01C roster receipt, byte for byte.
* permitted-roster.json -- the permitted support roster: the committed disagreeing-row roster receipt (its split identity
  is the registration's source_split_identity_hash), byte for byte.
"""
import os
import argparse
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1")
    ap.add_argument("--attempt", default="attempt-slurp-native-stage3-advantage-r01-v1-generation")
    ap.add_argument("--pairs", default=str(DATA / "analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json"))
    ap.add_argument("--scope-receipt", default="docs/receipts/rosters/slurp-stage3-construction-r01c.json")
    ap.add_argument("--permitted-receipt", default="docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json")
    ap.add_argument("--out-dir", default=str(DATA / "prepared/SAEA-SLURP-STAGE3-DELTAS-V1"))
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    outputs = DATA / "runs" / a.run / a.attempt / f"{a.run}.outputs.jsonl"
    pairs = json.load(io.open(a.pairs, encoding="utf-8"))
    dis = {}
    for row in pairs.get("pairs") or pairs.get("rows") or []:
        d = row.get("disagreement")
        if d is None and isinstance(row.get("best"), dict):
            d = float(row["best"].get("slu_f1_f1", 0)) - float(row["worst"].get("slu_f1_f1", 0))
        dis[row["sample_id"]] = float(d)
    n = 0; missing = 0
    target = out / "advantage-outputs-v1.jsonl"
    with io.open(outputs, encoding="utf-8") as fh, io.open(target, "w", encoding="utf-8", newline="\n") as w:
        for line in fh:
            r = json.loads(line); sid = r["sample_id"]; text = r.get("text")
            if not isinstance(text, str):
                raise SystemExit(f"sealed row {sid} carries no text")
            if hashlib.sha256(text.encode("utf-8")).hexdigest() != r.get("response_text_sha256"):
                raise SystemExit(f"sealed row {sid}: text digest differs from response_text_sha256")
            if sid not in dis:
                missing += 1; continue
            w.write(json.dumps({"sample_id": sid, "response_text": text, "disagreement": dis[sid]}, ensure_ascii=False) + "\n"); n += 1
    print("advantage-outputs rows", n, "unmatched", missing, "sha256", sha(target))
    for src, name in ((a.scope_receipt, "outer-construction-roster.json"), (a.permitted_receipt, "permitted-roster.json")):
        shutil.copyfile(src, out / name); print(name, "from", src, "sha256", sha(out / name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
