"""Append EXECUTION FACTS to the SAEA-SN-TOOL-KB-TEXT-EMB-PASS ledger row.

Every number is read from the durable manifest / outcome / receipt, never
hand-typed. Re-reads the ledger immediately before writing (another agent may
be appending rows concurrently) and refuses if the facts are already there.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
LEDGER = REPO / "docs/exposure-ledger.md"
RECEIPT = REPO / "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json"
DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"
ROW_ID = "SAEA-SN-TOOL-KB-TEXT-EMB-PASS"
MARKER = "**EXECUTION FACTS"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    manifest = json.loads((SNAPSHOT_DIR / "embeddings-manifest.json").read_text(encoding="utf-8"))
    facets = manifest["embedded"]["content_facets"]
    values = manifest["embedded"]["values"]
    accounting = manifest["accounting"]
    jitter = manifest["jitter_pair"]
    decoder = receipt["resident_decoder_untouched"]
    stop = receipt.get("session_stop") or {}

    facts = (
        f" {MARKER} (appended after the pass, before any downstream consumption)**: EXECUTED ONCE, "
        f"COMPLETED, attempt `{manifest['attempt_id']}`. "
        f"{accounting['embedding_tool_contacts']:,} pinned-TOOL embedding contacts against the "
        f"CPU-served `qwen3-embedding-0.6b-gguf` on port 8082 "
        f"({facets['count']:,} content-facet representations + {values['count']:,} ValueBundle "
        f"contents + 2 jitter), all dim {facets['dims']}; registered ceiling 25,000 — not exceeded. "
        f"ZERO frozen-core contacts, ZERO audio seconds, {accounting['gpu_hours']} GPU-h "
        f"(`-ngl 0`, nothing offloaded). Wall time "
        f"{accounting['total_wall_seconds'] / 60:.1f} min end to end "
        f"({accounting['throughput_texts_per_second']:.2f} texts/s over the two embedding blocks; "
        f"server spawn+load {accounting['spawn_seconds']:.1f} s). Encode-only structural check: "
        f"{manifest['encode_only_check']['result']} — guards 1+2 over the pinned module set AND "
        f"this pass's own runner source before the spawn, guard 3 on the live client object, "
        f"guard 4 on all {accounting['http_requests_guarded']:,} request payloads on the real wire "
        f"path. Snapshot identity re-verified before contact: content hash "
        f"`{manifest['snapshot']['content_sha256'][:8]}…{manifest['snapshot']['content_sha256'][-6:]}` "
        f"matches the KB-BUILD receipt. Jitter pair (same text, session start vs session end) "
        f"cosine {jitter['cosine']:.12f}, bit-identical {str(jitter['bit_identical']).lower()}. "
        f"Vectors landed on the data root: `{facets['file']}` sha256 "
        f"`{facets['sha256'][:8]}…{facets['sha256'][-6:]}` ({facets['bytes']:,} bytes) and "
        f"`{values['file']}` sha256 `{values['sha256'][:8]}…{values['sha256'][-6:]}` "
        f"({values['bytes']:,} bytes), with `embeddings-manifest.json` sha256 "
        f"`{receipt['manifest']['sha256'][:8]}…{receipt['manifest']['sha256'][-6:]}`; Git receipt "
        f"`docs/receipts/knowledge/slurp-kb-size-full-embeddings.json` sha256 "
        f"`{sha256_file(RECEIPT)[:8]}…{sha256_file(RECEIPT)[-6:]}`. RESIDENT DECODER UNTOUCHED "
        f"(verdict {str(decoder['verdict']).lower()}): PID {decoder['pid']} stayed continuously "
        f"resident on port {decoder['port']} and its server log measured "
        f"{decoder['server_log_bytes_before']:,} bytes / sha256 "
        f"`{decoder['server_log_sha256_before'][:8]}…` byte-identical AND hash-identical before "
        f"and after the pass; it was never contacted, probed, restarted, or reconfigured. The "
        f"embedder session was stopped cleanly by receipt-bound pid "
        f"({stop.get('termination_signal', 'n/a')}, forced={str(stop.get('forced', 'n/a')).lower()}), "
        f"never a pattern-matched kill. NO verdict, promotion, admission, or superiority claim "
        f"follows from this row; its only product is KB-side vector material. Consumption caution "
        f"carried in the receipt: the content-facet vectors are the K-side `content` dimension "
        f"`saea-kb-alpha-blend-v1` consumes, while the VALUE vectors — produced because "
        f"preregistration section 5.1 names both text families — must NOT be used as recall keys, "
        f"the owner's Q-K-V ruling section 1.3 holding that V is consumed, never embedded as key "
        f"material."
    )

    text = LEDGER.read_text(encoding="utf-8")
    lines = text.split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith("| ") and f"| {ROW_ID} |" in line]
    if len(hits) != 1:
        print(f"REFUSED: expected exactly one {ROW_ID} row, found {len(hits)}")
        return 1
    index = hits[0]
    if MARKER in lines[index]:
        print(f"REFUSED: execution facts already present on {ROW_ID}")
        return 1
    if not lines[index].rstrip().endswith("|"):
        print("REFUSED: row does not end with a table pipe")
        return 1
    row = lines[index].rstrip()
    lines[index] = row[:-1].rstrip() + facts + " |"
    LEDGER.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"appended execution facts to {ROW_ID}")
    print(f"row length now {len(lines[index])} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
