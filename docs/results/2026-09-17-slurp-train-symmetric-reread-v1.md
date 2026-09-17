# TRAIN A symmetric-normalised re-read: an addendum to every sealed TRAIN A verdict

Status: **ADDENDUM. No verdict's status changes.** Cells B0, B0r and B4b keep the verdicts their
own preregistered rules already gave them; this note adds the column owner decision 7 of
2026-09-17 requires and decision 14 made evaluable, and says, per sealed verdict, whether the
symmetric contrast agrees in sign with the official one and by how much the official gain exceeds
the symmetric one. Root: the TRAIN symmetric-scorer agent, 2026-09-17. Zero model, tokenizer,
encoder, ASR and server contacts; five invocations of the pinned official `evaluate.py` (commit
`8eb16545`) over read-only COPIES of sealed outputs; no run directory and no sealed file was
written or modified; no utterance text or gold filler is printed or persisted anywhere in this
read.

Authority: `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md` (decisions 7 and
14); `docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md` (what "symmetric-normalised"
means here); the sealed verdicts
`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`,
`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md` and
`docs/results/2026-09-17-slurp-train-a-direct-anchor-release.md`.
Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`, section 5.

## What decision 14 registered

`slurp-slu-f1-normalized-v1-train` (commit `00fb4915`, branch `fable/symtrain`). It is the same
function the DEV binding is, with one argument changed: `split_id="train"`. Gold resolution rule:
`data.slurp.load_slurp_split(lock, root, "train")`, exactly as `slurp-slu-official-train` resolves
it, and a `devel` sample id is refused with *"outputs sample_id ... is not part of SLURP split
'train'"* just as the DEV binding refuses a TRAIN one. The document it returns carries
`aggregate["split_id"] = "train"`, so a manifest or an offline read names the gold it scored
against instead of hiding it in a call site. The slot normalizer is unchanged and is mined from
TRAIN and only from TRAIN whichever split is scored (`saea-slurp-slot-normalizer-v1`, rungs
`R0-case-whitespace`, `R1-whisper-english`, `R2-meridiem-join`, `R3-train-leading-preposition`;
inventory 55 entity types, 4,147 distinct normalised TRAIN fillers, learned leading tokens `the`
and `in`, 34 gold false merges reported).

Symmetry is the whole point and it is unchanged: the normalizer rewrites the **gold and the
predicted filler alike** before the distance blocks, so an arm cannot gain under it by writing its
answers differently from the corpus, only by saying what the corpus says. It normalises fillers
only and never a label: on every one of the five arms, **0 of 1,080 rows** change their intent
(scenario+action) flag between the official and the symmetric column, so every label metric below
is the official one, unchanged.

## Inputs, all hash-pinned

| Arm | Run id | Sealed `outputs.jsonl` SHA-256 | Re-read scores SHA-256 |
| --- | --- | --- | --- |
| anchor | SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1 | `d87d71e8fa0fe93b45d5c6817ba125b016d8d91f44a14309171dd0f3a64270d8` | `167f0ba131988c99e04f87154d3eb86d9db9ba5e0cdb7d5c7f353ad771eb26c0` |
| direct | SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1 | `5c182ddfc81effe2465fb58f052842538f22ead3601355dbe77427c937decd61` | `77a770c4fef5ac04c65ef2ce36079ae9eafc904e9f4a479fd223c3d60f72ddff` |
| B0 | SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-V1 | `108d6851c5cc5347e5b626354a99ea370f65d321c16396a914274e90c2678e65` | `ba949fef2826d127ad6213f3e8630bb5be0782fb898a67c8225774f809c33436` |
| B0r | SAEA-SLURP-NATIVE-REVIEW-OFF-TRAIN-FOLD-A-REPLICATE-V1 | `3212bcbc1913d8357ee101c2926e0df2292c39e33da874e4f5983440a09fe29f` | `9d5ea3052bafd88612bdb5aa0edd0a60e904965f762ba5f55229adf0794839da` |
| B4b | SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2 | `01b56d39fa55c48fbdf53e9e9ad5ac4b92428bd9d13a8308a958a7aa0048dfdb` | `3982769587f221772c15af90bf2b83e55d02557524eba74caa5034695270dffa` |

Each arm's sealed `scores.json` and `run-manifest.json` were hash-verified first (`73608763...`,
`7840a959...`, `51f37e6c...`, `2974b45b...`, `751c5298...` and the five manifests), every manifest is
COMPLETED, pins the score bytes this read used, and carries split identity
`61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6`, role discovery. Population:
1,080 rows, 125 speakers, 18 scenarios, roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`1fe7908c...`). Estimator: paired whole-speaker cluster bootstrap, 10,000 draws, seed 20260915,
CI95 and CI90 -- the same draws cells B0r and B4b used.

**STOP conditions, both passed before any table was read.** (1) The re-read's own official half
reproduces every arm's sealed official aggregate to better than 1e-9 and every registered verdict
number to the last quoted digit (48.5336 / 33.8851 / 48.6654 / 48.6288 / 51.0855 pooled SLU-F1).
(2) The per-row counts pool to the aggregate they claim, in both columns, for all five arms and
both pooled metrics (20 of 20 checks within 1e-6).

## Arms: official beside symmetric

| Arm | Official SLU-F1 | Symmetric SLU-F1 | Gap | Official span F1 | Symmetric span F1 | Gap | Intent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| sealed dual-store anchor | 48.53 | **52.09** | +3.56 | 29.50 | **41.38** | +11.89 | 77.96 |
| released direct anchor | 33.89 | **34.46** | +0.57 | 21.10 | **24.38** | +3.28 | 73.70 |
| cell B0 (review off) | 48.67 | 52.16 | +3.50 | 29.34 | 41.70 | +12.36 | 77.59 |
| cell B0r (replicate) | 48.63 | 51.89 | +3.26 | 29.66 | 40.79 | +11.14 | 77.69 |
| cell B4b (slot store v2) | 51.09 | **54.26** | +3.18 | 32.40 | **43.99** | +11.59 | 78.52 |

The gap column is that arm's own representation-alignment charge: what the official metric takes
off it for writing a filler differently from the way the corpus writes it, with content held
fixed. It is **5.6 to 6.2 times larger for every agent arm than for the direct arm** (+3.2 to
+3.6 pp against +0.57 pp). On exact-span F1 the charge is larger than a third of the score itself.
This is the same asymmetry A1 measured on DEV1000 -- the official `evaluate.py` lower-cases the
gold filler and never the prediction, and the agent arms emit the less corpus-like surface -- now
measured on TRAIN A directly rather than inferred from a one-sided projection.

## Contrasts: pooled SLU-F1

delta = right minus left; the direction each sealed verdict used is preserved.

| Contrast | Official delta | Official CI95 | Symmetric delta | Symmetric CI95 | Symmetric CI90 | Sign agrees | Official minus symmetric |
| --- | ---: | --- | ---: | --- | --- | --- | ---: |
| B0 minus anchor | +0.13 | [-1.15, +1.45] | +0.08 | [-1.40, +1.62] | [-1.16, +1.36] | yes | +0.06 |
| B0r minus anchor | +0.10 | [-1.04, +1.19] | -0.20 | [-1.48, +1.04] | [-1.28, +0.84] | **no** | +0.29 |
| B0r minus B0 (own null) | -0.04 | [-1.22, +1.02] | -0.27 | [-1.64, +0.98] | [-1.41, +0.77] | yes | +0.23 |
| B4b minus anchor | +2.55 | [+1.13, +3.98] | **+2.17** | **[+0.62, +3.68]** | [+0.89, +3.44] | yes | +0.38 |
| anchor minus direct | +14.65 | [+11.79, +17.51] | **+17.63** | [+14.58, +20.69] | [+15.11, +20.16] | yes | **-2.98** |
| B0 minus direct | +14.78 | [+11.90, +17.70] | +17.71 | [+14.63, +20.78] | [+15.16, +20.32] | yes | -2.93 |
| B0r minus direct | +14.74 | [+11.78, +17.68] | +17.44 | [+14.32, +20.53] | [+14.81, +20.03] | yes | -2.69 |
| B4b minus direct | +17.20 | [+14.00, +20.35] | **+19.80** | [+16.36, +23.14] | [+16.93, +22.58] | yes | **-2.60** |

Equal-scenario weightings agree with the natural mixture on every row (B4b minus anchor +2.11
official / +1.68 symmetric; anchor minus direct +13.10 / +16.10).

## Contrasts: pooled span F1

| Contrast | Official delta | Official CI95 | Symmetric delta | Symmetric CI95 | Sign agrees | Official minus symmetric |
| --- | ---: | --- | ---: | --- | --- | ---: |
| B0 minus anchor | -0.15 | [-1.74, +1.48] | +0.32 | [-1.30, +1.98] | **no** | -0.47 |
| B0r minus anchor | +0.16 | [-1.37, +1.64] | -0.59 | [-2.12, +0.88] | **no** | +0.75 |
| B0r minus B0 (own null) | +0.31 | [-1.31, +1.81] | -0.91 | [-2.45, +0.51] | **no** | +1.22 |
| B4b minus anchor | +2.91 | [+0.79, +5.12] | **+2.61** | **[+0.46, +4.74]** | yes | +0.30 |
| anchor minus direct | +8.40 | [+5.18, +11.65] | +17.01 | [+13.49, +20.54] | yes | **-8.61** |
| B0 minus direct | +8.25 | [+5.09, +11.39] | +17.32 | [+13.94, +20.80] | yes | -9.08 |
| B0r minus direct | +8.56 | [+5.22, +11.86] | +16.42 | [+13.02, +19.78] | yes | -7.86 |
| B4b minus direct | +11.31 | [+7.89, +14.70] | +19.62 | [+15.67, +23.42] | yes | -8.31 |

## The symmetric own null

B0r minus B0 on byte-identical requests, symmetric pooled SLU-F1: point estimate **-0.271 pp**,
CI95 [-1.64, +0.98], **half-width 1.310 pp**; CI90 half-width 1.092 pp. Span F1: -0.905 pp, CI95
half-width 1.480 pp.

On pooled SLU the symmetric own null is **wider** than the official one (1.310 against
1.122 pp); on span F1 it is slightly narrower (1.480 against 1.559). Re-reading a TRAIN A cell
symmetrically therefore buys no extra power on the primary metric: a cell that cannot clear
h_SLU = 1.1218 officially will not clear 1.3100 symmetrically. These half-widths are registered
here as the symmetric margins for any future TRAIN A read that wants them; the program's decision
margins remain cell B0r's official h_SLU = 1.1218 and h_intent = 1.0051, because the primary
number is the official one.

## Per verdict

**Cell B0 / B0r re-decision (`2026-09-17-slurp-b0-review-off-redecision-v2.md`, HARMFUL).**
Unchanged. Both passes stay inside both columns' nulls on pooled SLU: B0 minus anchor +0.13
official / +0.08 symmetric, B0r minus anchor +0.10 / -0.20. The B0r leg's sign **flips** between
the columns, and the span-F1 column flips sign on all three review-off contrasts. Nothing follows
from those flips: every one of them is a point estimate far inside a null whose half-width is an
order of magnitude larger than the estimate, which is exactly what a sign flip in the noise band
looks like. The re-decision turned on the **intent** clause, and intent is byte-identical between
the two columns (0 rows change flag), so the symmetric read cannot and does not touch it. The
verdict stands as written, on the evidence it was written on.

**Cell B4b (`2026-09-17-slurp-b4b-slot-store-v2-verdict.md`, ADMITTED, provisional).** Unchanged,
and materially strengthened. The symmetric contrast **agrees in sign** and is still bounded away
from zero: +2.17 pp, CI95 [+0.62, +3.68], CI90 [+0.89, +3.44], against the official +2.55 [+1.13,
+3.98]. The official gain exceeds the symmetric one by **0.379 pp**, i.e. **14.9 % of the
official +2.55 is representation alignment and 85.1 % is content** -- the module made the core say
more of what the corpus says, not merely write it more like the corpus. Span F1 agrees: +2.61
symmetric against +2.91 official, 0.30 pp of representation. The per-scenario shape survives
normalisation with two named exceptions worth recording, since B4b was a date/time cell: `alarm`
falls from +13.10 official to +7.49 symmetric and `datetime` from +4.80 to +0.56, so **most of
the `datetime` gain and about 43 % of the `alarm` gain was surface form**, while `news` (+4.66 ->
+7.45), `social` (+5.91 -> +6.78) and `email` (+4.56 -> +5.64) grow under the symmetric reading.
The two losing scenarios lose identically in both columns (`lists` -5.74, `general` -2.95). The
admission does not rest on representation alignment; part of its *time* story does, which is
consistent with the verdict's own filler-distance table (74.34 -> 53.48 mass, a representation
term it already named as such).

**The released direct anchor (`2026-09-17-slurp-train-a-direct-anchor-release.md`).** Unchanged,
and read in the opposite direction from what decision 7 anticipated. The official metric
**understates** the system-over-direct margin: +14.65 official against **+17.63 symmetric** on
pooled SLU (-2.98 pp), and +8.40 against **+17.01** on span F1 (-8.61 pp). The agent arms are
charged six times more representation than the direct arm, so removing the surface charge from
both sides widens the gap rather than shrinking it. A1 predicted this on DEV1000 under the P2
projection (14.62 -> 17.81); TRAIN A reproduces it symmetrically, at 17.63.

## What decision 7's "about 2.5 pp of the bar is representation alignment" now reads as, on TRAIN A

Decision 7 priced the *projection's* gain. This read prices the *arms'* own surface. Both numbers
are now on record and they are not the same measurement:

- The anchor is 15.47 pp short of the SLU-F1 >= 64 bar on the official scale. **3.56 pp of that
  distance is representation alignment** and 11.91 pp is content; B4b is 12.91 pp short of which
  3.18 pp is representation.
- Published SLURP systems emit lower-cased spoken text, so their official and symmetric numbers
  nearly coincide and the bar is stated where it is for a reason. The honest statement is
  therefore: *if this system wrote its fillers the way the corpus writes them, it would read
  52.09 (anchor) and 54.26 (B4b) on the official scale without answering a single extra row
  correctly.* That is a prompt/commit-judge engineering item -- module M3's runtime half already
  points at it -- not a capability claim, and it is not a way to reach 64.
- The rung decomposition says which rung the charge sits in. Cumulative symmetric pooled SLU-F1:

| Arm | R0 (case+whitespace) | +R1 (Whisper English) | +R2 (meridiem) | +R3 (TRAIN leading token) |
| --- | ---: | ---: | ---: | ---: |
| anchor | 50.88 | 51.14 | 51.91 | 52.09 |
| direct | 33.90 | 33.94 | 34.39 | 34.46 |
| B0 | 51.07 | 51.20 | 51.98 | 52.16 |
| B0r | 50.84 | 50.98 | 51.75 | 51.89 |
| B4b | 53.39 | 53.34 | 54.02 | 54.26 |

  Case and whitespace alone carry **+2.35 pp of the anchor's +3.56** (66 %) and +2.30 of B4b's
  +3.18; the numeric/punctuation and meridiem rungs carry the rest. A1's DEV1000 finding that
  about three quarters of the P2 gain is case is reproduced here on TRAIN A as two thirds.

## What is not claimed

- **No status changes.** B0/B0r stay HARMFUL, B4b stays ADMITTED (provisional, one pass, awaiting
  its request-identical replicate under decision 13). This note re-decides nothing and no clause
  of any preregistration is re-applied here.
- **The symmetric number is not comparable to a published SLURP number.** It normalises the gold
  as well as the prediction, so it is a repository-internal instrument reported beside the
  official one, never instead of it, exactly as `asr-wer-whisper` sits beside `asr-wer`. The
  paper-facing SLURP number stays the official `evaluate.py` one and the >= 64 bar stays on that
  scale.
- **No label claim.** The normalizer touches fillers only; intent, scenario and action are the
  official numbers unchanged, and 0 of the 5,400 arm-rows changes its intent flag.
- **No new roster, split or held-out reading.** TRAIN Fold A is an exposed discovery roster; Fold
  B, DEV-1000 and the test split stay unread. The DEV1000 cells already had the DEV symmetric
  scorer and are not re-read here.
- **No projection is applied anywhere in this read.** Every number above is on raw, unprojected
  labels; the projection-v3 columns of the sealed verdicts are untouched and are a different
  measurement.
- **Nothing about the cause of the surface gap.** This read measures it; it does not say which
  node writes the filler, and it does not attribute the direct arm's smaller charge to anything.

## Files

| File | SHA-256 |
| --- | --- |
| `analysis/SAEA-SLURP-TRAIN-SYMMETRIC-REREAD-V1/result.json` | `a083cfc0d4a1108545195a7d11c7943eb4d344c8123ba5b9e8d2c038fe2b804a` |
| `.../README.md` | `9ec1f165a00944ef3dcaef9a44cdb19d2646dfe61081ce121868dfc18367412d` |
| `.../train_symmetric_reread.py` | `16e260153ed8c1a90ceee25aeb37135cfc5b3abe1c73e74a2fb7c1dd6f687578` |
| `.../cache/score.json`, `.../cache/contrasts.json` | intermediates, re-derivable from the driver |

All under `SPEECHRL_DATA_DIR`; the per-arm re-read scores and the read-only outputs copies live
under `.../copies/<run-id>/`. Scorer `slurp-slu-f1-normalized-v1-train`
(`slurp-official-8eb16545`, port `slurp-scorer-v1`, evaluator commit
`8eb16545762be97ace75334109d73824217311f1`), registered at commit `00fb4915`.
