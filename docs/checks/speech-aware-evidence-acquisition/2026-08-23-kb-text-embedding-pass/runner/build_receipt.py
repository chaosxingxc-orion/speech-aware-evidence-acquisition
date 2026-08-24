"""Land the Git-side receipt for SAEA-SN-TOOL-KB-TEXT-EMB-PASS.

Reads ONLY the durable on-disk records this pass wrote (the data-root manifest
and the attempt's outcome.json) and emits
``docs/receipts/knowledge/slurp-kb-size-full-embeddings.json``. No model or
tool contact; no number is re-derived by hand.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"
MANIFEST = SNAPSHOT_DIR / "embeddings-manifest.json"
RECEIPT = REPO / "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    attempt_dir = Path(sys.argv[1])
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    outcome = json.loads((attempt_dir / "outcome.json").read_text(encoding="utf-8"))
    if outcome["status"] != "COMPLETED":
        raise SystemExit(f"attempt status is {outcome['status']}, refusing to land a receipt")

    resident = outcome["resident_decoder"]
    receipt = {
        "schema": "saea-kb-text-embeddings-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": manifest["run_id"],
        "attempt_id": manifest["attempt_id"],
        "exposure_ledger_row": "SAEA-SN-TOOL-KB-TEXT-EMB-PASS",
        "authority": manifest["authority"],
        "generated_at": manifest["generated_at"],
        "generator": "scratchpad runner, archived at docs/checks/speech-aware-evidence-acquisition/2026-08-23-kb-text-embedding-pass/runner/run_kb_text_embedding_pass.py",
        "snapshot": manifest["snapshot"],
        "manifest": {
            "artifact_relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-full/embeddings-manifest.json",
            "sha256": sha256_file(MANIFEST),
            "bytes": MANIFEST.stat().st_size,
        },
        "vectors": manifest["embedded"],
        "not_embedded": manifest["not_embedded"],
        "storage": manifest["storage"],
        "embedder": manifest["embedder"],
        "encode_only_check": manifest["encode_only_check"],
        "jitter_pair": manifest["jitter_pair"],
        "accounting": manifest["accounting"],
        "resident_decoder_untouched": {
            "verdict": resident["untouched"],
            "pid": resident["before"]["pid"],
            "port": resident["before"]["port"],
            "server_log_path": resident["before"]["server_log_path"],
            "server_log_bytes_before": resident["before"]["server_log_bytes"],
            "server_log_bytes_after": resident["after"]["server_log_bytes"],
            "server_log_sha256_before": resident["before"]["server_log_sha256"],
            "server_log_sha256_after": resident["after"]["server_log_sha256"],
            "ps_before": resident["before"]["ps"],
            "ps_after": resident["after"]["ps"],
            "note": (
                "the resident q4km decoder was never contacted, probed, restarted, or "
                "reconfigured by this pass; the embedder ran CPU-only (-ngl 0) in its own "
                "session on port 8082. An unchanged server-log byte length AND sha256 across "
                "the whole pass is the proof."
            ),
        },
        "session_stop": outcome.get("session_stop"),
        "run_dir": manifest["run_dir"],
        "consumption_caution": (
            "The content-facet vectors are the K-side 'content' dimension the "
            "saea-kb-alpha-blend-v1 policy's multidim recall consumes (rails.kb_policy takes "
            "facet_vectors as facet_id -> {dimension: vector}). The VALUE vectors are produced "
            "because the DEV-100 preregistration section 5.1 names both text families, but the "
            "owner's Q-K-V ruling (2026-08-23-knowledge-plane-baseline-rulings.md section 1.3) "
            "states that V is consumed, never embedded as key material. Value vectors must "
            "therefore NOT be used as recall keys without an explicit owner decision; they are "
            "available for evidence-side work (deduplication, supply-side reranking, diagnostics) "
            "only."
        ),
        "frame": (
            "Artifact-producing prep pass (DEV-100 prep prerequisite 1). No accuracy, promotion, "
            "admission, or superiority claim follows from this receipt; its only product is the "
            "KB-side vector material the DEV-100 campaign's alpha-blend policy consumes. Vectors "
            "and the manifest live on the data root and never enter Git; this receipt carries "
            "their hashes."
        ),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {RECEIPT}")
    print(f"receipt sha256 {sha256_file(RECEIPT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
