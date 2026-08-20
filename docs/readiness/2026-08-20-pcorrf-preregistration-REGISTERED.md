# P-CORR-F — percept-keyed type-corrective supply (filling tier) — REGISTERED

Date: 2026-08-20. Status: **REGISTERED — flyable once the machinery lands.** Profile:
`bounded-discovery-probe`. Design queue item 4 (scheme scoreboard), executed under the
2026-08-19 blanket exploration release. Design basis: the 2026-08-20 read-only design
analysis over CONSUMED artifacts only (worksheets were scratchpad-transient; every figure
below is re-derivable from the cited consumed reads and is DESCRIPTIVE, published here
pre-read as reachability material, never used to select supply content).

## 0. Scope correction (disclosed to the owner)

The design-queue phrase "corrective CONFUSABLE supply" assumed a phonetic-neighbour error
population. Measured on the consumed A0 decode: **that population is empty** — 0/37
value-confusion pairs share a `phonetic_key`; the highest-scoring pairs are
format/segmentation variants ("8 PM"→"eight pm"). The dominant channel is **type-name
collision**: 68/95 emitted slots (71.6%) carry entity types outside SLURP's 55-type train
vocabulary (`location→place_name`, `currency→currency_name`, … 28 distinct pairs, 39
instances). This probe is therefore the TYPE/NORMALIZATION-corrective twin of P-TRAP —
a scope correction, not a cancellation. Concordant priors: P-PHON NEAR-MISS starvation
(4/85), P-KEY recall-bank finding.

## 1. Construction — L1 TYPE-LOOKUP (gold-free)

For each sample, take ALL of the core's own A0 emitted (type, filler) slots — never the
wrong-only subset: "wrong" is gold-defined and a wrong-only key is an oracle (legality
audit item I1; `analysis.ptrap_read.harvest_a0_wrong_values` is legal for a HARM probe,
fatal for a benefit probe). Look each emitted filler up in the train-mined legal pool
(SLURP `train.jsonl` ONLY; the pool derivation is pinned in this probe's own binding step —
the g0 binding's `distinct_values: 4157` label is pair-count-ambiguous and is NOT
inherited) and supply the legal types that value actually occurs under. Measured yield:
mean **1.02 entries/sample** (max 4), entry precision 0.590, gold-slot coverage **36/89**
— beating the consumed A3 100-entry roster's coverage (29/89) at ~1% of its dose.
Widening beyond L1 collapses precision (top-5 ungated: 0.089, 463 wrong-but-legal
percept-derived entries = P-TRAP trap material at 0.9062 capture) and is capped at L2b in
arm W4.

## 2. Arms (frozen SLURP 60, split identity `fc9de436…5ee5`; one call per sample,
A3-form base so V1/V2/A3 are directly citable)

| Arm | Construction | Calls |
|---|---|---|
| W1 CORR-SELF | A3 100-entry legal roster + THIS sample's L1 corrective entries, rendered in the roster's item shape (renderer pinned at binding) | 60 |
| W2 CORR-CROSS (control) | identical construction and per-sample entry count, corrective entries seeded fixed-point-free from OTHER samples' A0 percepts | 60 |
| W3 CORR-ONLY (dose) | the L1 corrective entries alone, no roster base | 60 |
| W4 CORR-WIDE (descriptive) | A3 + L2b (`core.retrieval.retrieve(k=3, min_score=0.70)` ∪ L1, mean 2.00 entries) | 60 |

## 3. Verdicts (paired cluster bootstrap, `analysis.bootstrap`, N=10,000, seed 20260807,
90% CI, clustered on the 60 sample ids)

- **Q-1 mechanism** — Δ₁ = SLU-F1(W1) − SLU-F1(W2), paired per-sample:
  **CORRECTIVE-PERCEPT** if Δ₁ ≥ +0.03 and CI lower > 0; **CORRECTIVE-INERT** if the
  entire CI ⊂ [−0.03, +0.03]; else **INCONCLUSIVE-CORR**. (0.03 = the study separability
  bar; measured duplicate-condition floor ±0.013 and the P-KEY byte-identical-resend
  |ΔF1| floor of exactly 0.0000 keep the equivalence branch reachable.)
- **Q-2 dose efficiency** — Δ₂ = SLU-F1(W3) − CITED A3 0.5961 (constant pinned as in
  `ptrap_read.py`): **DOSE-EFFICIENT** if Δ₂ ≥ −0.03 at ≤4 entries/sample vs A3's 100;
  **DOSE-INSUFFICIENT** if Δ₂ ≤ −0.10; else **INCONCLUSIVE-DOSE**. Cross-session
  comparison; the ±0.013 drift bound travels with the verdict.
- **W4 carries no clause** — it reports the widening dose curve descriptively.
- **Mandatory dual measurement (pre-declared): P-CORR-F is P-TRAP with the sign
  flipped.** W1's corrective set contains 25 wrong-but-legal percept-derived entries
  (61 total, 36 gold); the read reports BOTH recovery (gold slots newly emitted) and
  contamination (non-gold corrective entries emitted), using P-TRAP's own capture
  detector. For W4 (82 non-gold entries) contamination is load-bearing.
- **Reachability statement (pre-read, mandatory):** per-arm corrective-entry count
  distribution; samples at K=0 (**20/60** under L1 — untouched by construction);
  max attainable slot recovery = gold slots present in each arm's own supplied set
  (**36/89** W1/W3, **38/89** W4). No unreachable branch may be reported affirmatively.
- Guardrails (descriptive): induced substitutions, copy-rate, parse/empty rates,
  per-arm `slot_f1_exact`, per-scenario breakdown.

## 4. Legality (replaces P-TRAP's gold zero-overlap guard, which is an oracle here)

1. The corrective binding hash is re-derived from `(A0 response text, train-mined pool,
   seed)` in three independent places (builder, validator, flight preflight), refusing on
   any disagreement — the `build_trap_sets` pattern.
2. Source-introspection assertion in the flight module (the
   `assert_never_calls_ontology_miner` pattern): it never imports
   `analysis.ptrap_read.harvest_a0_wrong_values`, any gold loader, or
   `load_slurp_ontology(include_synthetic=True)`.
3. Declarations: `span_source = "percept-keyed-type-lookup"`,
   `reference_source = "slurp-train-ontology"`, `legality_tier = "legal"`. The either-field
   rule catches declared contradictions only; guards 1–2 exist because it cannot detect a
   silently gold-conditioned construction.
4. A corrective entry MAY equal gold (that is the point); no gold-keyed accept/reject
   exists anywhere in the construction path.

## 5. Cited comparators (consumed; never re-flown)

A0 0.1741 / A2 0.4686 / **A3 0.5961** / A1 gold-ceiling 0.6340 / A4 0.3087 / F1 filler
0.1356 / A1'r self-scoped 0.6093 / V1 trap 0.5003 / V2 cross 0.5907 (SLU-F1;
`2026-08-18-pslu-read`, `2026-08-18-pslu-s2-read`, `2026-08-19-ptrap-read`).

## 6. Cost (registered ceilings)

240 calls planned (4×60). Ceilings: **≤260 calls; ≤1000 metered audio-seconds
(4 passes × 182.26 s = 729 s planned); ≤0.35 GPU-h** (measured-equivalent ≈0.15 at the
consumed 0.00059 GPU-h/call rate).

## 7. Discipline

One-shot read; pinned suite `analysis/pcorrf_read.py` built and coordinator-reviewed
BEFORE the read; exposure row `SAEA-PROBE-pcorrf-240` at machinery landing (consumed=no);
gold scoring-side only; SLURP CC BY-NC 4.0 carried; no test split; discovery-tier
same-distribution n=60 — no superiority/generalization claim attaches.

## 8. Pre-read accounting adjudication (coordinator, 2026-08-20, after landing, before
## any result read — no result value was consulted)

The flight receipt records three GPU figures: server-alive wall **0.3628 h** (exceeds the
§6 ceiling number by 46.1 s), GPU-active occupancy **0.0967 h**, per-call
measured-equivalent **0.1416 h**. The wall overshoot is fully attributed (three archived
corroborations) to a 959 s cold-cache sha256 of the 20.76 GB GGUF set that ran AFTER
server spawn while the GPU sat at 0–1% util — a launcher sequencing flaw, not compute.
Ruling: §6's ceiling metric is the registration's own stated basis — the per-call
measured-equivalent (its parenthetical "measured-equivalent ≈0.15") and GPU-active
occupancy, consistent with the program's G1 latency-sum precedent; both are inside the
ceiling, so the flight is NOT in breach. The wall figure stays on the record untouched.
Forward rule for every successor flight: build transport + payload binding BEFORE
spawning the server. This section is accounting-only and was written without reading any
flown response.
