"""Root preparation for S3-3 / S3-5 (owner decisions 82, 106): export the CONSTRUCTION gold of the R01C roster.

Two files under the data root, never under the repository, both derived model-free from the SLURP TRAIN metadata for
exactly the rows of ``docs/receipts/rosters/slurp-stage3-construction-r01c.json`` (a construction roster: its gold is
legal to read, owner decision 82):

* ``--gold-intents`` map ``{sample_id: "<scenario>_<action>"}`` for ``scripts/analysis/stage3_rollout_score.py``
  (``gold_intent_in_candidates`` in the S3-4s trajectory block; the map itself is never copied into pairs.json);
* ``construction-transcripts.jsonl`` (``{"sample_id", "text"}`` per line) for the six-token containment rule of
  ``scripts/build_slurp_stage3_delta_store.py`` (``load_construction_spans`` reduces it to n-grams and discards it).

Prints counts and sha256 digests only. WSL Python from the study root.
"""
import os
import argparse
import hashlib
import io
import json
import os
from pathlib import Path

DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default="docs/receipts/rosters/slurp-stage3-construction-r01c.json")
    ap.add_argument("--train-metadata", default=str(DATA / "datasets/slurp/metadata/train.jsonl"))
    ap.add_argument("--gold-intents-out", default=str(DATA / "coordination/slurp-stage3-advantage-r01-v1/r01c-gold-intents.json"))
    ap.add_argument("--transcripts-out", default=str(DATA / "prepared/SAEA-SLURP-STAGE3-DELTAS-V1/construction-transcripts.jsonl"))
    a = ap.parse_args()
    roster = json.load(io.open(a.roster, encoding="utf-8"))
    wanted = {item["sample_id"] for item in roster["items"]}
    intents: dict[str, str] = {}
    texts: dict[str, str] = {}
    with io.open(a.train_metadata, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            for rec in row.get("recordings", []):
                sid = "slurp:train:%06d:%s" % (int(row["slurp_id"]), Path(rec["file"]).stem)
                if sid in wanted:
                    intents[sid] = "%s_%s" % (row["scenario"], row["action"])
                    texts[sid] = row["sentence"]
    missing = sorted(wanted - set(intents))
    if missing:
        raise SystemExit("%d roster ids not found in the TRAIN metadata (first: %s)" % (len(missing), missing[0]))
    for out, payload in ((a.gold_intents_out, json.dumps(dict(sorted(intents.items())), indent=2, sort_keys=True) + "\n"),
                         (a.transcripts_out, "".join(json.dumps({"sample_id": k, "text": texts[k]}, ensure_ascii=False) + "\n" for k in sorted(texts)))):
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        io.open(out, "w", encoding="utf-8", newline="\n").write(payload)
        print(out, "rows", len(intents), "sha256", hashlib.sha256(payload.encode("utf-8")).hexdigest())
    print("distinct intents", len(set(intents.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
