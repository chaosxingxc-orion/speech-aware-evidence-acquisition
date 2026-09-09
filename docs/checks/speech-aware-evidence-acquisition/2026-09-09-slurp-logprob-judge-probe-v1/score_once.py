"""Score the logprob arm ONCE through ``core.scoring_batch``, and hand the read
its ``--per-sample`` file.

Zero model contacts. One job over the arm's ONE complete 1,000-row manifest,
``include_per_sample=True``, never sharded -- the standard-scoring rule.

The paper-facing scorer is ``slurp-slu-official-projected-v2`` with
``slurp-slu-f1-normalized-v1`` beside it as the secondary. Neither is declared
by the sealed manifest (``scorers`` is a baseline-fragment key and enters
``config_hash``, which this cell holds fixed at the comparator's own value plus
the two decoding keys), so ONE DERIVED MANIFEST is written beside the sealed one
differing from it ONLY in the ``scorers`` list. The sealed manifest is not
touched and its sha256 is recorded.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.scoring_batch import (  # noqa: E402
    ScoreJob,
    run_score_batch,
)

OFFICIAL = "slurp-slu-official-projected-v2"
NORMALIZED = "slurp-slu-f1-normalized-v1"
DERIVED_SUFFIX = ".logprob-judge-probe-v1-read.run-manifest.json"

ATTEMPT_DIR = Path(sys.argv[1])
SCORE_DIR = Path(sys.argv[2])
OUT_DIR = Path(sys.argv[3])
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


sealed = sorted(ATTEMPT_DIR.glob("*.run-manifest.json"))
sealed = [p for p in sealed if DERIVED_SUFFIX not in p.name]
if len(sealed) != 1:
    raise SystemExit("expected one sealed manifest, found %s" % sealed)
sealed = sealed[0]
sealed_doc = json.loads(sealed.read_text(encoding="utf-8"))
print("sealed manifest:", sealed)
print("  status:", sealed_doc.get("status"), " study_commit:", sealed_doc.get("study_commit"))
print("  scorers:", sealed_doc.get("scorers"))
print("  protocol_hash:", sealed_doc.get("protocol_hash"))
print("  cost:", json.dumps(sealed_doc.get("cost"))[:400])

document = dict(sealed_doc)
if list(document.get("scorers") or []) == [OFFICIAL, NORMALIZED]:
    raise SystemExit("derived manifest would be a no-op copy")
document["scorers"] = [OFFICIAL, NORMALIZED]
derived = sealed.with_name(sealed.name.replace(".run-manifest.json", "") + DERIVED_SUFFIX)
derived.write_text(
    json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)

if SCORE_DIR.exists() and any(SCORE_DIR.iterdir()):
    raise SystemExit("score directory is not empty: %s" % SCORE_DIR)

batch = run_score_batch(
    [ScoreJob(job_id="logprob", manifest=derived)],
    output_dir=SCORE_DIR,
    max_workers=1,
    include_per_sample=True,
)
(SCORE_DIR / "batch-summary.json").write_text(
    json.dumps(batch, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)
print("BATCH:", json.dumps(batch, indent=2, default=str)[:900])

score_path = SCORE_DIR / "logprob.score.json"
score = json.loads(score_path.read_text(encoding="utf-8"))
if score.get("verified") is not True:
    raise SystemExit("score file is not a verified manifest score: %s" % score_path)

official = score["scores"][OFFICIAL]
normalized = score["scores"][NORMALIZED]
per_sample = official["per_sample"]
print("per-sample rows:", len(per_sample))
print(
    "AGGREGATE (this arm's OWN numbers, never a comparator):",
    json.dumps(
        {
            k: v
            for k, v in official.items()
            if k not in ("per_sample", "raw", "stdout", "command")
        },
        indent=2,
        default=str,
    )[:2500],
)

per_sample_path = OUT_DIR / "per-sample.json"
per_sample_path.write_text(
    json.dumps({"per_sample": per_sample}, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)

provenance = {
    "schema": "saea-slurp-logprob-score-v1",
    "model_contacts": 0,
    "sealed_manifest": str(sealed),
    "sealed_manifest_sha256": sha256_file(sealed),
    "sealed_manifest_scorers": sealed_doc.get("scorers"),
    "sealed_manifest_status": sealed_doc.get("status"),
    "sealed_manifest_study_commit": sealed_doc.get("study_commit"),
    "derived_manifest": str(derived),
    "derived_manifest_sha256": sha256_file(derived),
    "derived_manifest_scorers": [OFFICIAL, NORMALIZED],
    "score_file": str(score_path),
    "score_file_sha256": sha256_file(score_path),
    "batch": batch,
    "per_sample_path": str(per_sample_path),
    "per_sample_sha256": sha256_file(per_sample_path),
    "per_sample_rows": len(per_sample),
    "include_per_sample": True,
    "sharded": False,
    "jobs": 1,
}
(OUT_DIR / "score-provenance.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True, default=str) + "\n",
    encoding="utf-8",
    newline="\n",
)
summary_path = OUT_DIR / "official-aggregate.json"
summary_path.write_text(
    json.dumps(
        {
            "official": {
                k: v
                for k, v in official.items()
                if k not in ("per_sample", "raw", "stdout", "command")
            },
            "normalized": {
                k: v for k, v in normalized.items() if k not in ("per_sample",)
            },
        },
        indent=2,
        sort_keys=True,
        default=str,
    )
    + "\n",
    encoding="utf-8",
    newline="\n",
)
print("wrote", per_sample_path, provenance["per_sample_sha256"])
