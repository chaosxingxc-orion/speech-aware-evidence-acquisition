# EVO-S1 stage-one power — what the 60-per-scenario re-draw actually buys

Model-free, zero contacts. Exposure row `SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2`. Generator
`scripts/build_slurp_evo_stage_one_power.py`; rule
`src/speech_aware_evidence_acquisition/analysis/slurp_evo_rosters.stage_one_power`; tests
`tests/unit/test_slurp_evo_fold_rosters.py`. Receipt `power.json`.

The coordinator's decision 1 of 2026-09-06 re-drew the EVO-S1 folds from 30 to 60 utterances per
scenario, and the reason given was stage-one power: at 30 rows too few scenarios can clear the
count gate for a rounds-1-and-2 null to mean anything about the mechanism. That re-draw costs
about 3.35 extra planned GPU-hours (preregistration section 10), so the number of scenarios it
buys is computed here from a committed receipt instead of being asserted in prose.

**Result: three of eighteen at 30 rows, SEVEN of eighteen at 60 — not the nine an earlier draft
of the preregistration asserted.** The re-draw more than doubles the admissible set and is still
worth its price, but the gain is smaller than it was written down as, and one scenario leaves the
set on the way up.

## The input, and the scaling rule

The only measured per-scenario save/harm table this study owns for the mechanism EVO-S1 evolves is
the KC-S1b DEV-1000 read: `docs/checks/speech-aware-evidence-acquisition/2026-09-05-slurp-slot-stage-kc-s1-v1/read.json`
(file sha256 `6b5c158b…7617`), contrast `paired_kc_s1b_over_closed_list`, population `pooled_1000`,
metric `slot_f1_exact_f1` — 97 saves and 7 harms over 1,000 rows, delta +7.80 pp. It is already
committed and already read; this row opens nothing new.

**The scaling rule, stated because the answer is sensitive to it.** A scenario's measured saves and
harms become per-row rates on the population they were measured on, are multiplied by the fold
size, and are compared against the gate's own absolute constants — `saves >= 4`, `harms <= 1`,
`net >= 3` (preregistration section 6 step 4) — **without rounding**. Two other readings are
available and both are wrong here:

* rounding the expected counts to whole rows admits `datetime` at 60 (3.93 saves rounds to 4);
* scaling the harms bound with the fold (`harms <= 2` at 60 rows) admits `transport`.

Taking both at once is how nine is reached. Neither is preregistered: the gate is an absolute row
count precisely so a reviewer can recount a stage-one decision by hand, so the expected counts are
compared against it as they are.

## Per scenario

`saves` / `harms` are KC-S1b's measured counts on its own `n` DEV rows; the two right-hand blocks
are those rates priced at a 30-row and a 60-row fold.

| scenario | n | saves | harms | sv@30 | hm@30 | gate@30 | sv@60 | hm@60 | gate@60 |
|---|---:|---:|---:|---:|---:|:--:|---:|---:|:--:|
| `alarm` | 58 | 4 | 0 | 2.07 | 0.00 | no | 4.14 | 0.00 | **PASS** |
| `audio` | 30 | 1 | 0 | 1.00 | 0.00 | no | 2.00 | 0.00 | no |
| `calendar` | 61 | 7 | 0 | 3.44 | 0.00 | no | 6.89 | 0.00 | **PASS** |
| `cooking` | 37 | 4 | 0 | 3.24 | 0.00 | no | 6.49 | 0.00 | **PASS** |
| `datetime` | 61 | 4 | 0 | 1.97 | 0.00 | no | 3.93 | 0.00 | no |
| `email` | 61 | 3 | 0 | 1.48 | 0.00 | no | 2.95 | 0.00 | no |
| `general` | 61 | 3 | 0 | 1.48 | 0.00 | no | 2.95 | 0.00 | no |
| `iot` | 61 | 7 | 0 | 3.44 | 0.00 | no | 6.89 | 0.00 | **PASS** |
| `lists` | 60 | 3 | 0 | 1.50 | 0.00 | no | 3.00 | 0.00 | no |
| `music` | 51 | 0 | 0 | 0.00 | 0.00 | no | 0.00 | 0.00 | no |
| `news` | 60 | 2 | 1 | 1.00 | 0.50 | no | 2.00 | 1.00 | no |
| `play` | 60 | 3 | 1 | 1.50 | 0.50 | no | 3.00 | 1.00 | no |
| `qa` | 60 | 4 | 0 | 2.00 | 0.00 | no | 4.00 | 0.00 | **PASS** |
| `recommendation` | 60 | 3 | 1 | 1.50 | 0.50 | no | 3.00 | 1.00 | no |
| `social` | 60 | 22 | 0 | 11.00 | 0.00 | **PASS** | 22.00 | 0.00 | **PASS** |
| `takeaway` | 39 | 3 | 2 | 2.31 | 1.54 | no | 4.62 | 3.08 | no |
| `transport` | 60 | 12 | 2 | 6.00 | 1.00 | **PASS** | 12.00 | 2.00 | no |
| `weather` | 60 | 12 | 0 | 6.00 | 0.00 | **PASS** | 12.00 | 0.00 | **PASS** |

Clearing at 30: `social`, `transport`, `weather`. Clearing at 60: `alarm`, `calendar`, `cooking`,
`iot`, `qa`, `social`, `weather`. Five scenarios join and one leaves.

## The finding the coordinator did not have in front of them

**The stage-one gate is not scale-free, and `transport` leaves the admissible set at 60 rows.**
Doubling the fold doubles a scenario's expected harms while the harms bound stays at one absolute
row, so a scenario whose saves are large but whose harm rate is non-zero can clear at 30 and fail
at 60. `transport` is exactly that: 12 saves and 2 harms in 60 measured rows, so at a 30-row fold
it prices at 6.00 saves and 1.00 harms (net 5.00, clears) and at a 60-row fold at 12.00 and 2.00
(net 10.00, refused on the harms bound alone). It is the second-largest measured effect in the
corpus after `social`.

This is a property of the gate, not of the draw, and it is recorded rather than repaired: changing
the gate is a coordinator decision and this row takes none. Two readings are available if the
coordinator wants `transport` back — make the harms bound relative (`harms <= 1 per 30 rows`), or
keep the absolute bound and accept that the loop cannot claim `transport` at this fold size — and
the preregistration's section 16 carries the choice.

## Contact surface

One committed JSON receipt is read and one JSON receipt is written. Zero model, GPU, network,
tokenizer, scorer and audio-decode contacts; no roster, no split, no media file and no sentence
text is opened. Nothing here authorizes a contact.
