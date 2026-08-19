# P-PHON verdict — MIXED (recall-dominant), A1'r concordant (registered model-free re-read, 2026-08-18)

Mechanical outcome per the registered classes and verdict rules
(`docs/readiness/2026-08-18-pphon-preregistration-REGISTERED.md` §1/§3, verbatim), computed by the
pinned offline read suite (`analysis.pphon_decomp`, built at `653ad9c`, coordinator-reviewed;
53/53 unit tests green immediately before the read at HEAD `754b18c`, clean tree) over five
ALREADY-CONSUMED attempts — zero model contact, zero GPU, no attempt-directory mutation:

- SLURP parent (A0+A3): `attempt-20260818T010218Z-4c97cb` (`SAEA-PROBE-pslu-n60`)
- SLURP s2 (A1'r): `attempt-20260818T200339Z-80119a` (`SAEA-PROBE-pslu-s2-183`)
- A2T A0 baseline: `attempt-20260818T055500Z-res315` (`SAEA-BASE-a2t-a0-400`)
- A2T s2b (B1): `attempt-20260818T153859Z-8da515`; A2T s2c (C1/C2): `attempt-20260818T175018Z-0d3363`
- Stage-2 arm plan reused verbatim from the consumed s2 attempt `attempt-20260818T124955Z-84b944`

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-18-pphon-decomp/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0. Exposure row `SAEA-CHECK-pphon-decomp` flips to
consumed in the same commit. Scope: **descriptive, discovery-tier, n=60 SLURP devel / n=120 A2T
headroom**. CC BY-NC 4.0 carried from both carriers.

Integrity: all reconciliation gates passed — SLURP three-way (computed / parent-recomputed /
archived) baseline failures 85/85/85, A3 conversions−regressions 44/44/44, A1'r 41/41/41
(regressions = 0 on both arms); A2T EM-flips three-way + literal exact gate at n=120: B1 = 8,
C1 = 10, C2 = 9, all exact. All five input archives MANIFEST-verified before reading.

## 1. SLURP-A3 primary verdict (first, before any interpretation)

**OVERALL (slurp/A3): MIXED — no flag fired.**

| Clause | Result | Margin |
|---|---|---|
| SPEECH-SNAP-PRESENT (i): NEAR-MISS conversions >= 25% of all conversions | **not met** | near_miss_share = **0.0227** (1/44) vs floor 0.25 — short by 0.2273 |
| SPEECH-SNAP-PRESENT (ii): CR(NEAR-MISS) >= CR(FAR-WRONG) + 0.15 | **not met** | CR(NEAR-MISS) = 0.2500, CR(FAR-WRONG) = 0.2500, margin = **+0.0000** vs floor +0.15 |
| FORMAT-DOMINANT: EQUIV-FORMAT conversions >= 60% of all conversions | **not met** | equiv_format_share = **0.1364** (6/44) vs floor 0.60 |

The class that actually dominates A3's conversions is **MISSING: 36/44 = 81.8%** of everything
supply converted was a slot the zero-supply baseline never emitted at all.

## 2. A1'r concordance

**CONCORDANT.** A1'r is also MIXED with both independent booleans matching A3
(speech_snap_present = False / format_dominant = False on both arms). A1'r clause numbers:
near_miss_share = 0.0000 (0/41) vs floor 0.25; CR(NEAR-MISS) = 0.0000 vs CR(FAR-WRONG) = 0.2500,
margin = −0.2500 vs floor +0.15; equiv_format_share = 0.1220 (5/41) vs floor 0.60. MISSING
likewise dominates: 35/41 = 85.4% of conversions.

## 3. SLURP four-class tables

n_gold_entities_total = 89; baseline (A0) total failures = 85 — the baseline failure profile is
itself MISSING-dominated (71/85 = 83.5%), leaving only 4 NEAR-MISS baseline slots for supply to
act on.

A3 (full-ontology dose-capped roster, primary supply arm; regressions = 0):

| Class | Baseline failures | Converted | CR(c) |
|---|---|---|---|
| MISSING | 71 | 36 | 0.5070 |
| EQUIV-FORMAT | 6 | 6 | 1.0000 |
| NEAR-MISS | 4 | 1 | 0.2500 |
| FAR-WRONG | 4 | 1 | 0.2500 |
| **TOTAL** | **85** | **44** | **0.5176** |

A1'r (self-scoping scenario-roster re-fly, concordance arm; regressions = 0):

| Class | Baseline failures | Converted | CR(c) |
|---|---|---|---|
| MISSING | 71 | 35 | 0.4930 |
| EQUIV-FORMAT | 6 | 5 | 0.8333 |
| NEAR-MISS | 4 | 0 | 0.0000 |
| FAR-WRONG | 4 | 1 | 0.2500 |
| **TOTAL** | **85** | **41** | **0.4824** |

## 4. A2T descriptive tables (secondary, orthographic proxy only; clean-form arms)

Baseline: 56 A0-failed string-valued arguments over the 120 headroom ids. B1 = clean replacing-form
nodefaults row; C1 = B1 content, seeded field/clause permutation; C2 = B1 content, constraints
verbalized as prose. No verdict clauses attach here (prereg §2: descriptive).

| Class | Baseline | B1 conv (CR) | C1 conv (CR) | C2 conv (CR) |
|---|---|---|---|---|
| MISSING | 12 | 0 (0.0000) | 1 (0.0833) | 1 (0.0833) |
| EQUIV-FORMAT | 5 | 0 (0.0000) | 0 (0.0000) | 0 (0.0000) |
| NEAR-MISS | 15 | 2 (0.1333) | 0 (0.0000) | 2 (0.1333) |
| FAR-WRONG | 24 | 3 (0.1250) | 4 (0.1667) | 4 (0.1667) |
| **TOTAL** | **56** | **5 (0.0893)** | **5 (0.0893)** | **7 (0.1250)** |

Headline: argument-level conversion on the A2T carrier is sparse (5–7 of 56) and spread across
NEAR-MISS/FAR-WRONG/MISSING with **zero** EQUIV-FORMAT conversions; the item-level EM-flip counts
(8/10/9) reconcile exactly with the consumed s2b/s2c reads.

## 5. Per-sample NEAR-MISS conversion evidence rows

Every NEAR-MISS conversion across all arms, with the value the baseline actually emitted and the
supplied entry the converted answer snapped to. These are the rows the speech-term reading would
ride on — there are three, and none is a clean acoustic-confusion repair.

SLURP (the single A3 row; A1'r converted zero NEAR-MISS slots):

| Arm | Sample | Slot type | Gold value | A0 wrong value | Roster entry snapped to |
|---|---|---|---|---|---|
| A3 | `slurp:devel:007852:audio-1494416109-headset` (calendar) | `time` | `five pm` | `5:00 PM` | `["time", "five pm"]` — same-type entry, A3 global dose-capped roster |

Reading this row honestly: `5:00 PM` vs `five pm` is a **clock-format variant**, not a plausible
mishearing — it lands in NEAR-MISS only because the pinned digit↔word map does not absorb the
`:00` token (normalized forms `five 00 pm` vs `five pm`, distance 0.30). The one row that could
have carried a speech-snap reading is format-adjacent on inspection.

A2T (B1 and C2 converted the same two URL arguments; C1 converted neither):

| Arm(s) | Sample | Key | Gold value | A0 wrong value |
|---|---|---|---|---|
| B1, C2 | `tier2_parametric:001869` | `sourceUrl` | `https://documentaries.org/nature` | `https://www.documentaries.org/nature` |
| B1, C2 | `tier7_multiturn:000599` | `sourceUrl` | `https://example.com/mymovie.mp4` | `https://example.com/movie.mp4` |

Both are textual URL edits (a `www.` prefix, a truncated filename) repaired by a clean-form
tool-doc row — orthographic through and through; the A2T carrier supplies no speech-term evidence
in either direction.

## 6. What this says about "speech knowledge participates" vs "audio as key"

Probe-1 evidence, stated carefully. On this decomposition the supply loop's L3 gain is **neither**
speech-snap **nor** format-normalization: it is **recall-dominant**. 81.8% (A3) / 85.4% (A1'r) of
converted slots were MISSING — slots the zero-supply baseline simply never produced — so on this
probe the roster behaves primarily as an **elicitation/recall bank**, not (yet) demonstrably as a
perceptual disambiguation prior. The SPEECH-SNAP-PRESENT clauses fail by wide margins (2.3% NEAR-MISS
share vs 25% floor; CR margin +0.00 vs +0.15 floor), and the single NEAR-MISS conversion is
format-adjacent on inspection (§5). At the same time this probe does **not** license the deflationary
"it's all label-space alignment" reading either — EQUIV-FORMAT is only 13.6% of conversions
(FORMAT-DOMINANT fails its 60% floor by a wide margin), even though supply repairs that class almost
perfectly when it occurs (CR 1.0000 on A3, 0.8333 on A1'r).

Three limits keep this from being a verdict on the identity question itself. First, the
**orthographic-proxy caveat** stands: NEAR-MISS by normalized Levenshtein is a proxy for acoustic
proximity, honestly named a proxy in the registration. Second, the instrument was **starved of the
class it tests**: only 4 of 85 baseline failures were NEAR-MISS at all, so the class-conditional
rates ride on n=4 and could not have cleared the 25%-of-conversions floor even at CR = 1.0
(4/44 = 9.1%) — absence of a speech-snap signal here is weak evidence of absence. Third, a
decomposition of WHAT supply converts cannot by itself separate "speech knowledge participates in
the loop" from "the audio is only a retrieval key" — that contrast is exactly what the registered
**P-KEY factorial (probe 2) remains the decisive instrument** for. Descriptive, discovery-tier,
n=60/120; no superiority or generalization claim attaches.
