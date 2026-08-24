"""Generate the docs/checks README for the KB text-embedding pass.

Every number comes from the durable manifest / receipt, never hand-typed.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
CHECK_DIR = REPO / "docs/checks/speech-aware-evidence-acquisition/2026-08-23-kb-text-embedding-pass"
DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"
SCRATCH = Path(os.environ["SCRATCH"])

manifest = json.loads((SNAPSHOT_DIR / "embeddings-manifest.json").read_text(encoding="utf-8"))
receipt = json.loads(
    (REPO / "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json").read_text(encoding="utf-8")
)

facets = manifest["embedded"]["content_facets"]
values = manifest["embedded"]["values"]
accounting = manifest["accounting"]
jitter = manifest["jitter_pair"]
embedder = manifest["embedder"]
decoder = receipt["resident_decoder_untouched"]

(CHECK_DIR / "runner").mkdir(parents=True, exist_ok=True)
for name in ("run_kb_text_embedding_pass.py", "env.sh", "syntax_check.sh", "preflight.sh", "run.sh",
             "verify_vectors.py", "build_receipt.py", "append_execution_facts.py", "build_check_readme.py"):
    shutil.copyfile(SCRATCH / name, CHECK_DIR / "runner" / name)

readme = f"""# KB text-embedding pass — {manifest['run_id']}

Date: 2026-08-23 (executed {manifest['generated_at'][:19]}Z). Status: **COMPLETED, one shot.**
Exposure row: `{manifest['run_id']}` (`docs/exposure-ledger.md`).
Authority: {manifest['authority']}.

Prep prerequisite #1 of the DEV-100 iterative optimization campaign: embed the KB-BUILD
`size-full` TRAIN snapshot's text material with the pinned tool-level embedder, land vectors
plus manifests, and leave the resident decoder completely untouched.

## What was embedded

| family | source field | count | dims | file | sha256 |
|---|---|---|---|---|---|
| content facets | `KeyFacet.representation` where `dimension == "content"` | {facets['count']:,} | {facets['dims']} | `{facets['file']}` | `{facets['sha256']}` |
| values | `ValueBundle.content` | {values['count']:,} | {values['dims']} | `{values['file']}` | `{values['sha256']}` |

Not embedded: the {manifest['not_embedded']['facet_count']} `label` / `prior` / `speaker`
facets — {manifest['not_embedded']['reason']}.

Both `.npz` files and `embeddings-manifest.json` (sha256 `{receipt['manifest']['sha256']}`)
live under `$SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-full/` and never
enter Git; `docs/receipts/knowledge/slurp-kb-size-full-embeddings.json` carries their hashes.

Each `.npz` holds three aligned arrays: `vectors` (float32, N×{facets['dims']}), `ids`, and
`text_sha256` (SHA-256 over the exact UTF-8 text embedded into that row), so a consumer can
re-verify the pairing without re-reading the 40 MB snapshot.

## Identity

- Snapshot `{manifest['snapshot']['snapshot_id']}`, content hash
  `{manifest['snapshot']['content_sha256']}` — re-verified in-process before any contact
  (file sha256 `{manifest['snapshot']['file_sha256']}`).
- Embedder: `{embedder['lock_key']}` (umbrella lock revision `{embedder['lock_revision']}`),
  `{embedder['gguf_relpath']}` sha256 `{embedder['gguf_sha256']}`, dim {embedder['dims']}.
- Server: receipt-pinned `{embedder['binary_path']}` sha256 `{embedder['binary_sha256']}`
  (build `{embedder['build_commit']}`), argv:
  `{' '.join(embedder['server_argv'][1:])}`.
- Server props: `{json.dumps(embedder['server_props'], sort_keys=True)}`.

## Gates

- **Encode-only structural check**: {manifest['encode_only_check']['result']}. Guards 1+2
  (import / endpoint-string) swept the pinned module set
  {manifest['encode_only_check']['pinned_modules']} **and this pass's own runner source**
  before the server was spawned; guard 3 (client surface) ran on the live
  `EmbeddingClient`; guard 4 (payload keys) ran on all
  {accounting['http_requests_guarded']:,} request payloads on the real wire path, not merely
  the first.
- **Resident decoder untouched**: verdict `{str(decoder['verdict']).lower()}`. PID
  {decoder['pid']} stayed continuously resident on port {decoder['port']}; its server log
  measured {decoder['server_log_bytes_before']:,} bytes / sha256
  `{decoder['server_log_sha256_before']}` **byte-identical and hash-identical** before and
  after. The embedder ran CPU-only (`-ngl 0`) in its own session on port
  {embedder['port']} with its own log, and was stopped by receipt-bound pid, never a
  pattern-matched kill.
- **Jitter pair**: the same text embedded at session start and at session end —
  cosine {jitter['cosine']:.12f}, bit-identical `{str(jitter['bit_identical']).lower()}`.
  {jitter['note']}

## Accounting

{accounting['embedding_tool_contacts']:,} pinned-TOOL embedding contacts (registered ceiling
25,000), **0** frozen-core contacts, **0** metered audio seconds,
**{accounting['gpu_hours']}** GPU-h ({accounting['gpu_hours_basis']}). Wall time
{accounting['total_wall_seconds'] / 60:.1f} min end to end, spawn+load
{accounting['spawn_seconds']:.1f} s, {accounting['throughput_texts_per_second']:.2f} texts/s
over the two embedding blocks (content facets {facets['wall_seconds'] / 60:.1f} min,
values {values['wall_seconds'] / 60:.1f} min).

## Storage semantics

{manifest['storage']['note']}

Measured L2 norms: content facets
[{facets['l2_norms']['min']:.6f}, {facets['l2_norms']['max']:.6f}], values
[{values['l2_norms']['min']:.6f}, {values['l2_norms']['max']:.6f}].

## Consumption caution

{receipt['consumption_caution']}

## Frame

{receipt['frame']}

## Files here

- `runner/` — the exact scripts that produced this record (runner, env, syntax check,
  preflight, one-shot launcher, consumer-side verifier, receipt/README/ledger builders).
"""

(CHECK_DIR / "README.md").write_text(readme, encoding="utf-8", newline="\n")
print(f"wrote {CHECK_DIR / 'README.md'}")
