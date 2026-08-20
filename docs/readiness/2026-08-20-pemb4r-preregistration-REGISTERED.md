# P-EMB-4R — multi-model kNN retrieval routing (register-aligned) — REGISTERED

Date: 2026-08-20. Status: **REGISTERED — machinery next; flies after P-CORR-F.** Profile:
`bounded-discovery-probe`. Authority: owner design input 2026-08-20 ("query = speech
embedding, key = gold text samples, value = gold label — value is used, never embedded;
feed the deduplicated retrieved labels to the core") plus the owner's extension the same
day: "try several embedding models; analyze overall feasibility and reachability."

## 1. Hypothesis under test (the owner's register-alignment diagnosis)

Every prior audio arm matched an UTTERANCE-register query against WORD-register label
keys (bare label strings; P-EMB-1/3L/3M reviewed — 3L's instruct prefixes made it worse).
An utterance embedding carries whole-sentence semantics and need not live near an isolated
label word. This probe re-tests audio embeddings on the natural pairing — utterance query
↔ utterance keys — with labels demoted to un-embedded metadata (values). kNN + label
voting; the frozen core stays the final authority in the consumption arm.

## 2. Shared harness

- **Key bank**: 18 scenarios × 50 = 900 SLURP `train.jsonl` utterance TEXTS (train-only,
  no synthetic; seed 20260807; bank manifest sha256 pinned at binding). Values = the
  bank rows' gold scenarios, metadata only.
- **Queries**: the frozen 60 (split `fc9de436…5ee5`): audio for audio arms; the consumed
  pkey2-338 T0 self-transcripts (registry sha256 `f8f6426a…4959`) for text arms.
- Per arm: L2-normalized vectors, top-K by cosine (K=5 primary; K=1/3 reported),
  majority-vote label prediction (tie → highest-mean-cosine label).

## 3. Arms (each model embeds its own bank once; arms sharing a model share the bank)

| Arm | Query | Model / stack | Isolates |
|---|---|---|---|
| A-LCO3 | audio | LCO-3B, pinned llama.cpp (POOLING-OVERRIDE scope carried) | register-alignment rescue on the primary embedder |
| A-LCO7 | audio | LCO-7B, same stack (server sanity in gates; DROPPED-* on failure) | scale axis |
| A-GLAP | audio | GLAP, transformers in-process (the only defect-free audio path) | unscoped audio kNN floor |
| T-LCO3 | T0 transcript | LCO-3B text tower | audio-path vs semantic-space attribution |
| T-LCO7 | T0 transcript | LCO-7B text tower | same, at scale |
| T-GLAP | T0 transcript | GLAP text tower | GLAP modality-gap decomposition |
| T-QW | T0 transcript | qwen3-embedding-0.6b (the proven 0.75 instrument) | cascade kNN vs cascade label-match |
| C-DECODE | winner's top-K dedup labels → frozen-core closed-set decode | pinned q4km generation | does retrieval-shrunk label space convert end-to-end? |

Environment-gated, documented NOT flown: omni-embed-nemotron-3b (NC + pinned
transformers branch), CLSP (transformers 5.12 incompatibility). Their feasibility rows
enter the read's feasibility matrix as design inputs for the escalation decision.

## 4. Verdicts (chance 0.0556; CITED: FS-NONE 0.8167, A1'r 0.7833, M4 label-match 0.7500,
audio-vs-label floor 0.0500-0.1333)

- **REGISTER-RESCUE**: any audio arm's vote accuracy ≥ 0.30 (LCO arms stay stack-scoped
  while the pooling override stands; GLAP is unscoped). ≥ 0.65 additionally names
  **AUDIO-ROUTES**.
- **AUDIO-CONTENT-ABSENT**: every audio arm ≤ 0.15 AND best text arm ≥ 0.65 — register
  alignment did not rescue audio; the audio-native closure stands with this stronger
  scope (the label-register confound is removed).
- **KNN-BEATS-LABEL-MATCH** (named finding): best arm > 0.7500 (utterance-utterance
  retrieval beats utterance-label matching).
- **C-DECODE**: paired per-sample vs the consumed FS-NONE rows (cross-session ±2-sample
  drift carried): RETRIEVAL-SUPPLY-HELPS if ≥ +3 samples; RETRIEVAL-SUPPLY-HURTS if
  ≤ −3; else reported descriptively.
- Otherwise **INCONCLUSIVE-4R** with the full matrix.
- **Mandatory pre-verdict reachability**: per-arm recall@1/3/5 of the gold label within
  the retrieved set (the mechanical ceiling on voting AND on C-DECODE); per-sample top-1
  margins vs each server session's measured repeat-δ (NO blanket "argmax unaffected"
  claim — the 3M jitter lesson); cross-arm agreement structure.

## 5. Cost (registered ceilings)

Planned: bank 4×900=3,600 + audio queries 180 + text queries 240 + C-DECODE 60 generation
+ gates/jitter ≤20 ≈ 4,100. Ceilings: **≤4,500 calls; ≤700 metered audio-seconds
(3×182.26 planned); ≤0.5 GPU-h.** Embedding contacts are pinned-tool contacts; C-DECODE
contacts are frozen-core contacts. Encode-only machine check carried unchanged from
P-EMB-3M for every embedding surface.

## 6. Discipline

One-shot read; pinned suite `analysis/pemb4r_read.py` (vote evaluator, recall table,
margin/degeneracy stats, feasibility matrix) coordinator-reviewed BEFORE the read;
exposure row `SAEA-PROBE-pemb4r-4100` at machinery landing (consumed=no); vectors/bank
manifests on the data root, hashes only in Git; gold labels scoring-side and value-
metadata only (never embedded, never in an embedding prompt); SLURP CC BY-NC 4.0 carried;
T0 transcripts are consumed pkey2 artifacts (cited, not re-generated).
