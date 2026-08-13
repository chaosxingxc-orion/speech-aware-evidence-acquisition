# Clean-floor context verdict — the day the evidence tax was measured, replicated, and caught in the act (2026-08-12)

All runs on baseline A″ (fixed 60 s windows, tail 0, slice-parallel, featcache warm, mmproj
off-GPU; bare np16 / evidence np8). Every number below is registered in
`docs/exposure-ledger.md`; run dirs under `$SPEECHRL_DATA_DIR/runs/`.

## 1. E-005F four-arm pilot (fast-3): the R4-era conclusion reverses

| arm | macro WER |
|---|---|
| context instruction, NO evidence | **13.08** |
| bare instruction, no evidence | 13.89 |
| matched ConEC pack | 14.81 |
| mismatched pack | 15.27 |

Decomposition: **instruction wording −0.81 pp** (uniform across samples, no evidence needed);
**matched-evidence tax +1.73 pp** (instruction held constant, uniform sign); mismatched +2.19;
content sensitivity C3 = −0.46 pp (corpus-level ≈ 68× the corpus noise floor 0.0083 pp).
Noise floors (same-arm twice-run + third replicate): corpus 0.008 pp, macro 0.031 pp,
per-sample max 0.59 pp.

The tail-era R4 read (any context ≫ nocontext) does not survive the clean floor: it was
compensation for self-poisoned context, as hypothesized (H2).

## 2. Wave5 replication (seeded n=5, bare spread 0.69 pp): both effects replicate

ctxinstr **9.58** vs matched **11.73** → **tax +2.16 pp, 4/5 samples worse, none better**.
Instruction gain replicates too (bare-instruction floor 10.35 → ctxinstr 9.58 = −0.77 pp,
matching fast-3's −0.81). Two independent splits, same story.

## 3. Dose-of-prefix curve (fast-3): short salient lists are the worst supply of all

ConEC pack head is a word-frequency list (bag-of-words). Byte-prefix budgets via the
`evidence_budget_bytes` knob (37560c9):

| supplied prefix | macro WER |
|---|---|
| 0 | 13.08 |
| 2,000 B (~250 terms) | **19.96 (+6.88)** |
| 4,000 B | 18.10 |
| 8,000 B | 14.89 |
| full pack (10–16 k) | 14.81 |

Monotone toward the full pack, never better than zero: a SHORT salient term list is an
attention attractor; a long list dilutes per-term prior. "Dose" via naive truncation is not
dose — it is coherence/selection destruction.

## 4. Mechanism forensics (offline, outputs diff): insertion pressure, counted

Pack-head-term occurrences in the stitched hypotheses, dose2k vs zero-evidence, same samples:
`reproxalap` 3→15, `aldeyra` 0→4 (4366522); pack-term tokens 509→696 (+37%) with
`bistricer`/`david` inflated (4387383); 543→705, `ifeng` 2→8 (4389907). The tax is not
distributed noise — the model force-inserts supplied entities into the verbatim transcript.

## 5. Commit-window curve (QF-3): geometry is monotone toward larger windows

30 s **15.45** (+1.56, all samples worse) · 60 s 13.89 · 90 s **13.35** (−0.54, zero
truncation verified). Seams cost accuracy; context helps; no latency constraint exists, so
the frontier points at 120 s (needs a wider slot — np10 shape exists; QF-4 candidate).

## 6. Substrate receipts banked today

E-22 bare floor 12.75 (n=10, cold pass 125 min = one-time +36% cold tax; corpus now warm);
wave5 bare floor 10.35 (n=5); feature cache 806 → 7,415 files; evidence-arm noise floor
pinned (§1); three fail-closed gate saves (arm-type/evidence pairing, carrier-cell ambiguity,
advance-window legality) — all at zero spend.

## 7. What this locks for the KC/KX convergence (owner synthesis, 2026-08-12)

- **KC**: construct MANY, well-organized (multimodal index: term, span, speaker, domain) —
  but **supply FEW, right ones**. Full-dump registration of all possible knowledge destroys
  generalization (measured, §3-§4); it is dead as a supply policy.
- **KX**: the problem is retrieval-gated candidate-set loading. Query sources to test:
  prior-slice committed text (runtime-legal, cheap — IC-001's supply gate), draft-decode
  two-pass (C-5a's correction-after cousin), audio-derived embedding (C-4a).
- **The decisive pilot** (next code, then ~1 h GPU): same 2 k bytes, selected by relevance
  instead of by prefix. If retrieval flips +6.9 to ≤0, the organize-then-retrieve thesis is
  proven at pilot scale. Needs: per-slice supply hook + a deterministic lexical/phonetic
  matcher (Sonnet batch), `conec-names` evidence source (participant names: small, coherent,
  cased) as the first coherent-small-form arm.
- **Headroom note**: best clean numbers (9.58 wave5 / 13.08 fast-3) still carry entity
  errors — the knowledge-addressable fraction of residual WER is exactly what the
  entity-class scorer (owner decision D-3) will quantify; corpus WER provably hides the
  entity slice where knowledge must pay.

## Open owner decisions (unchanged)

D-1 (n=10 admission — the tax is now double-replicated; the upgrade case is strong),
D-3 (entity scorer — now the value chain's core metric), Tier-2 authorization batch
(B-8a contextasr replication ~40 min, slue, AMI, tool-model locks for the aligner stack).
