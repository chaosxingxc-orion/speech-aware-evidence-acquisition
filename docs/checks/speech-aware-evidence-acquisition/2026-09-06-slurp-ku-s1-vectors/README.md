# KU-S1 sealed vectors — 2026-09-06

Two pre-flight vector artifacts for the SLURP consumption dimension, and what the owner rule of
2026-09-06 did to the second one. Both artifacts live under `SPEECHRL_DATA_DIR` and never enter
Git; these receipts carry their hashes.

| receipt | ledger row | profile | contacts | artifact | sha256 |
|---|---|---|---|---|---|
| `facet-vectors.json` | `SAEA-SLURP-MF-KU-S1-FACET-VECTORS-V1` | `model-free-check` | 0 of everything | `vectors/slurp-ku-s1/facet-vectors.jsonl`, 11,514 × 1,024, 262,190,415 B | `922e8e9f…f8fad` |
| `query-vectors.json` | `SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1` | `bounded-discovery-probe` | 1,002 embedding tool contacts, 0 frozen-core, 0 GPU | `vectors/slurp-ku-s1/query-vectors.jsonl`, 1,000 × 1,024, 22,789,268 B | `c194adfb…ff4c6` |

## 1. Facet vectors — a format conversion, zero contacts

`vectors-content-facets.npz` (sha256 `0bcb955a…c1c72`, produced 2026-08-24 by
`SAEA-SN-TOOL-KB-TEXT-EMB-PASS`, 23,030 embedding tool contacts already paid) rewritten in the
one-object-per-line form `rails.phase_supply.load_sealed_vectors` reads. No server, no socket, no
model, no text, no embedding, no gold, no audio.

Gates, all before a byte was written: the npz hashes to the embeddings receipt's own pin; the
snapshot's content hash is the fragment's `e27b2745…a51b57`; the npz's `ids` array equals, in
order, the snapshot's 11,514 `dimension == "content"` facet ids; every row carries 1,024 finite
components. Afterwards the written file was read back through the flight's own reader and all
11,790,336 components compared against the npz: **max |delta| 0.0**. No rounding, no
normalization — each `float32` is widened to the exactly equal Python `float`.

Value vectors (`vectors-values.npz`) are deliberately not converted and never loaded (owner Q-K-V
ruling of 2026-08-23: V is consumed, never embedded as key material). Label / prior / speaker
facets carry no vectors at all.

## 2. Query vectors — produced, then re-scoped by the owner rule

The pass embedded, once each, the 1,000 phase-1 (`draft`) response texts of the sealed KU-S1c run
`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1` (attempt `attempt-20260906T042946Z-44720f`; run
manifest sha256 `1b5143aa…11a74d` and phases file sha256 `f6ed3c14…264e63` both verified against
the KU-S1c verdict's pins **before** any response text was read). Exactly two fields per row were
read — the sample id and the model's own response text. No gold, no reference transcript, no SLURP
devel sentence text, no audio, no other run's material.

**Owner rule, 2026-09-06 (binding): the retrieval QUERY must contain the speech signal.** It may
be speech plus an agent intermediate state (speech plus the draft answer, say), but it can never
be text-only. These vectors are text-only. They are therefore **not** cell KU-S1's query vectors:
`configs/baseline/slurp-phase-blend-cl-v1.json` leaves `phase_supply.evidence.query_source.sha256`
at the 64-f placeholder until MF-7 fixes a speech-containing embedder, and
`rails.phase_supply` now refuses any `query_source` whose `embedded_signal` does not declare
`speech:` or `speech+state:`.

What the artifact is, and why the pass still ran:

1. **The Q-draft arm of the MF-7 retrieval-key audit** — the text-only baseline every
   speech-carrying key is measured against. MF-7 (worktree `wt-mf7`) reads this exact path and
   this exact receipt; both are stable and citable.
2. **The state half of a future `speech+state` fusion**, if MF-7's decision table picks the fused
   form: the state component is the row's own draft answer, which is precisely what is embedded
   here.

### Deviation recorded, not explained away

The jitter pair — the same text embedded at session start and at session end — is **not
bit-identical** on this pass: cosine `0.9997014083444208`. The 2026-08-24 KB pass on the same
CPU-only geometry was bit-identical and recorded that as its tolerance evidence. A second CPU
embedder (another agent's, pid 4602 on port 8092, same GGUF, same `-t 6`) was resident for part of
this pass and is the obvious candidate cause, but the cause is not established here. Any consumer
that needs bit-exactness must re-measure rather than inherit the 2026-08-24 claim.

That other process was never contacted, signalled or reconfigured by this pass:
`scripts/slurp_ku_s1_query_embedding_pass.py` contains no `pkill`,
`core.session.stop_session` targets only the receipt-bound pid (7738, SIGTERM, not forced) after
re-verifying its identity, and pid 4602 exited on its own between the before and after process
fingerprints (`outcome.json` in the run directory). No GPU server existed at any point during
either pass.

## 3. What neither receipt authorizes

Neither is an accuracy, admission, promotion or superiority claim, and neither authorizes a
flight. Cell KU-S1 stays un-flyable until MF-7 fixes the speech-containing query embedder and the
preregistration `docs/readiness/2026-09-06-slurp-consumption-ku-s1-v2-preregistration.md` records
the choice.
