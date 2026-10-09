# SLURP delivery post-processing v4g: LOCK record (NX round R0.4, confirmed on TRAIN Fold B)

Recorded 2026-10-09 by Claude Opus 5.5 (analysis agent, on the coordinator's brief, Fable 5.1) in the worktree
`fable/nx-v4g-lock`. Docs only: this note re-registers no cell, moves no pin in any registered package, changes no
config or module hook, and grants no contact. Every number below is read from registered, sealed reports; zero GPU,
zero model contacts across the whole evidence chain. Development numbers only (owner decisions 28 and 86).

Authority: the NX programme's R0.4 lock rule (`docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`,
round table row R0.4: "lock v4 if Fold-A CI-LB > 0"), with the confirmation roster moved by the coordinator's ruling
after the audio attribution (hand-off entry "v4g registered" and the attribution entry, 2026-10-09): the guarded set
v4g is the lock candidate and its confirmation is read offline on the R1 cell's delivering-arm column (TRAIN Fold B),
because Fold A located the defect the guards answer and cannot confirm them. No owner decision number is cited for
this lock because none is on file for it.

## 1. What is locked

**`saea-deliver-normalise-v4g`, version `1`** (rule id `slurp-use-projection-v4g`, class
`rails.delivery_normalisers.SlurpProjectionV4GuardedDeliveryNormaliser`, `DELIVER_NORMALISE_V4G_VERSION = "1"` in
`src/speech_aware_evidence_acquisition/rails/delivery_normalisers.py`, blob sha256 at this note's base
`a41283fe95c645f0e6c390eedc2bb7e80739fd52ae2d03990f70326ca6731dc6`), as registered by
`docs/readiness/2026-10-09-slurp-nx-postprocessing-v4g-registration-v1.md` and receipt
`docs/receipts/knowledge/slurp-v4g-registration-v1.json` (sha256
`d235d5456c18ffe154851e2de56f3f35293ec29b24054df44208bc0b77bbf8d3`).

- **Stages (fixed order).** `saea-deliver-normalise-v3` unchanged (label rule, legal-label projection v2, filler P2),
  then the entity stage `fx-article`, `fx-oclock`, `scope`, `ti1`, `ee10`.
- **Guards (TRAIN statistics only; constants in code, echoed in every row receipt).**
  - `ti-expressible`: ti1 fires only on a delivered intent with >= 100 pool exemplars
    (`V4G_GUARDS.ti1_min_exemplars = round(1 / V4_TI_MIN_SHARE) = 100`).
  - `ee-wilson`: ee10 fires only when the Wilson score 95 % upper bound of the intent's pool entity-carrying rate is
    < 0.10 (`ee_wilson_max_upper = 0.10`, `ee_wilson_z = 1.959963984540054`).
  - A change to any guard constant bumps the version and voids this lock.
- **Pinned tables** (`prepared/SAEA-SLURP-V4-TRAIN-STATISTICS-V1/`, receipt
  `docs/receipts/knowledge/slurp-v4-train-statistics-v1.json` sha256
  `5bf43b3afa12dba2faa0de7778c61de4b1befff83fe783c5fdece10f09049531`; loaded statistics digest
  `01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223`):

| table | sha256 |
| --- | --- |
| `article-strip-v1.json` | `db42bf10a08ae9ccc51c656fd5cbbf8a636ee88a12b4c37100b5d69cf4d51b79` |
| `oclock-v1.json` | `36779d582b0da541f55b90d3dcfc55ef7d3cfd6c4e3dfbec402daec5226399c7` |
| `type-by-intent-v1.json` | `41a57d45bc434a3e42f3950590985d86f8598c38fdd8aba443d161c57059329d` |
| `intent-entity-rate-v1.json` | `bd43804dd23868d2e4d6531f2ff305c1b0fd7a3a96cef4afaa28ab63793fac59` |

The tables come from one TRAIN pool (`size-pool-annotated-exemplars-minus-r01`: TRAIN minus Fold A, Fold B, R01 and
R01C; 8,554 exemplars, 59 intents), disjoint from every evaluation roster below. The normaliser never moves an intent
label (intent delta 0 rows on every pool read).

## 2. Why it is locked (the evidence chain; all offline, zero GPU, zero model contacts)

| step | roster (n) | column | delta official pooled SLU-F1 pp [CI95] | rows edited | source |
| --- | --- | --- | --- | ---: | --- |
| 1. A2 selection of v4 (431 combinations + 10 single rules) | DEV-2000-ADDED, COMP-1b delivered (1,000; 913 utterance clusters) | v4 vs sealed v3 column (65.93) | **+0.98 [+0.21, +1.74]** (equal-scenario +0.10) | 124 | `docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md` (search driver `31ea97e1...`; `select-a2/`) |
| 2. single Fold-A read of the selected list | TRAIN Fold A, COMP-1b delivered (1,080) | v4 vs v3 column (63.61 -> 65.28) | **+1.67 [+0.81, +2.50]** (equal-scenario +0.93); **audio -17.47** on 60 rows | 130 | same note, section 4; `confirm-fold-a/report.json` sha256 `cfe31596...` |
| 3. attribution and guards (A2 only; Fold A not re-read for the guarded set) | Fold A audio loss = ee10 on `audio_volume_mute` (4 / 45 TRAIN exemplars carry entities; Wilson upper 20.7 %); guards `ee-wilson` + `ti-expressible` | guarded vs v3 on A2 | **+0.98 [+0.25, +1.71]** (equal-scenario +0.23; vs v4 -0.00 [-0.24, +0.26]) | 115 | `docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md`; reports `a2/` `f5e486a8...`, `fold-a/` `7a6ca3eb...` |
| 4. registration reproduces step 3 byte for byte | A2 (1,000) | registered `--apply v4g` | +0.9761 [+0.2453, +1.7120], copy `6e50951c...` | 115 | `docs/readiness/2026-10-09-slurp-nx-postprocessing-v4g-registration-v1.md` |
| **5. fresh-roster confirmation** | **TRAIN Fold B, R1 delivering `lock` column (1,080 clusters)** | **v4g(lock) vs lock's normalised (v3) column, 62.13 -> 63.69** | **+1.55 [+0.81, +2.33]**, CI95 lower bound > 0; equal-scenario +1.76; audio +7.05 | 104 | `docs/results/2026-10-09-slurp-nx-r1-solver-fold-b-column-read.md` section 7 (successor); `offline-v4/v4g-lock/report.json` sha256 `7f2d22be05a4d36be484b13e0a34ed4066753d9c9bb337b4e042479faa6af6c4` |

Bootstrap everywhere: paired, whole-utterance clusters, 10,000 draws, seed 20260915, CI95. Each column was scored once
by the registered scorer on a derived copy (`slurp-slu-official` on A2, `slurp-slu-official-train` on Folds A and B),
reproducing the in-process number to 1e-6.

**Lock rule: MET.** The CI95 lower bound of `v4g(lock) - lock` on Fold B is +0.81 > 0. Fold B never entered the rule
search (A2) or the defect location (Fold A); it is the roster that had not seen the rule question.

**Robustness beside the confirmation (same reports, not separate confirmations).** On every other arm of the R1 run,
v4g(X) - X has a CI95 lower bound above 0: aa +1.52 [+0.81, +2.29], r1-c1 +2.21 [+1.44, +3.03], r1-c2 +1.84
[+1.08, +2.64], r1-c3 +0.81 [+0.12, +1.53] (smaller: its empty-entity decision overlaps ee10), r1-c4 +1.51
[+0.82, +2.24], r1-c5 +1.58 [+0.82, +2.37]. Unguarded v4(lock) - lock is +1.44 [+0.62, +2.27] with audio -10.13.

## 3. What it replaces, and scope

- **v4g replaces `saea-deliver-normalise-v3` as the delivery normaliser of the NX composition** for every NX cell
  registered after this lock takes effect at the module step of section 5, and for the R5 composed read (programme
  row R5: module v3 = base + R0.4 + R1 + R2 ...).
- **Cells already registered with v3 keep v3 at delivery.** R1 iteration 2
  (`slurp-native-stage3-nx-r1-i2-solver-fold-b-v1`; its baseline fragment names `saea-deliver-normalise-v3`) is not
  re-registered, re-pinned or re-flown because of this note; its read applies v4g offline as a column
  (`slurp_nx_postproc_v4_apply.py --apply v4g`), exactly as R1 iteration 1 did.
- **The COMP-1b intent lock is untouched** (`docs/results/2026-10-09-slurp-intent-lock-comp1b-v1.md`): v4g moves no
  intent label.
- **v4 (unguarded) is not locked.** It stays registered for replay only.
- A composed read never mixes the two at delivery: a cell is read against an A/A on its own normaliser.

## 4. What is not claimed

- **No test claim.** Every number is a development number on DEV-2000-ADDED or a TRAIN construction fold (owner
  decisions 28 and 86); the signed test sample was not read. No superiority, generalisation, cross-carrier or
  paper-scale claim; SLU-F1 for SLURP stays open until R5 and the second test-sample allowance (row 233).
- **The per-scenario audio caveat of v4, and how v4g removes it.** Unguarded v4 deletes whole rows through ee10 on
  intents whose TRAIN entity rate is not resolved below 10 % (`audio_volume_mute` 4 / 45, Wilson upper 0.207;
  `audio_volume_other` 0 / 8, 0.324; `music_query` 4 / 71, 0.136). That cost audio -17.47 on Fold A and -10.13 on the
  Fold B lock column (-10.13 to -26.62 across the seven R1 arms). Under `ee-wilson` none of those three intents fires
  ee10 (of the four ee10-eligible intents in the attribution note's table, only `qa_maths`, 0 / 66, upper 0.055,
  still fires), and
  `ti-expressible` removes 32 of 59 intents from ti1. On Fold B the v4g audio delta is +7.05 on the lock column and
  0.00 to +7.05 across the arms; v4g(lock) loses only in datetime -0.84, lists -1.10 and takeaway -1.15 (60 rows
  each, unresolved). Per-scenario numbers are descriptive.
- **Guard constants were not tuned on any evaluation roster.** They follow from the TRAIN pool and the rules' own
  thresholds; the A2 numbers of steps 3 and 4 are descriptive (A2 is the pool the guards were checked against), and
  only step 5 is the confirmation.
- **Exposure.** A2 and Fold A carry prior exposure to these rules (the scope-rule Fold-A rehearsal, the COMP-1b reads,
  steps 1 to 3); Fold B carries the R1 iteration-1 flight and its read, which did not involve post-processing rules.

## 5. Next step (exact)

The SLURP module hook still pins v3: `src/speech_aware_evidence_acquisition/rails/adapters/slurp_module_hooks.py`
line 185 `DEFAULT_DELIVER_NORMALISER = "saea-deliver-normalise-v3"`, returned by `default_deliver_normaliser` (line
248), which `rails/consumption_module.py` enforces against the composed `deliver.normaliser`. Moving
`default_deliver_normaliser` for profile slurp to `saea-deliver-normalise-v4g` (version 1, the pinned tables above) is
a **separate registered step before R5**: one code change with its unit tests and the module receipt re-proven on the
new request/delivery bytes, plus the registration test that today asserts no file under `configs/` names v4g
(`tests/unit/test_deliver_normaliser_v4g.py`) updated in the same change. Until that step lands, no config or cell
delivers with v4g.
