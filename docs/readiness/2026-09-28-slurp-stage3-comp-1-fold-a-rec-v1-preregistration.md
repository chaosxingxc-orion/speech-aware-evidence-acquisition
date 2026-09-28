# Cell COMP-1 recovery, variant 2: the -REC recovery re-registration (HELD)

Status: **REGISTERED BEFORE CONTACT, HELD until the owner rules between this -REC re-registration and the
resume-recovery** (`2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md`). The variant
the owner does not choose is superseded unflown. Written with zero model, tokenizer, encoder, scorer,
server and GPU contacts. Ids, counts and hashes only.

This note addends the COMP-1 registration
[`2026-09-27-slurp-stage3-comp-1-fold-a-v1/`](2026-09-27-slurp-stage3-comp-1-fold-a-v1/) and its
preregistration, which are **not edited**. The question, the composition, the comparator, the decision
rule, the margins, the attribution table and the prohibitions stand unchanged.

## 1. Why

The COMP-1 arm `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` ABORTED on 2026-09-28 at contact `flight-1854`
(flight commit `cb628f59`; 1,913 contacts; trace SHA-256 `029a2dbb...61997`) on a harness defect named
to a component (`docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md`): the Solver citation
parser refused a repeated id the per-contact grammar admits. The fix is `a451f942`
(`rails/solver_citation.py` only). The arm's own `failure_policy` says a harness defect takes the FULL
re-fly form; this is that form (precedent: the B5e recovery run
`SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`).

## 2. The cells

| item | arm | four-row smoke |
| --- | --- | --- |
| experiment / cell | `slurp-native-stage3-comp1-fold-a-rec-v1` | `slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1` |
| run id | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1` | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1` |
| attempt | `attempt-slurp-native-stage3-comp1-fold-a-rec-generation-v1` | `attempt-slurp-native-stage3-comp1-fold-a-rec-smoke-4-generation-v1` |
| FIT run | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-FIT-V1` | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-FIT-V1` |
| parent bytes | `slurp-native-stage3-comp1-fold-a-v1` | `slurp-native-stage3-comp1-fold-a-smoke-4-v1` |
| rows / caps | 1,080 / 11,880 calls, 33,930 s (the arm's, unchanged) | 4 / the smoke's |
| inherited supply output | `ce68bebc...` | `1d55ea73...` |

The bytes are the parent's except the run, attempt and FIT identities and the recovery note (in the
baseline `what_this_is`, the readiness reason, the `failure_policy` and the purpose prefix). Both cells
inherit their parent's prepared supply pin; the flip rebuilds it under the -REC run id and asserts the
output unchanged -- `--allow-output-change` is never passed. The smoke is the four-row dry run of the
fixed tree the abort diagnosis requires, recorded beside the model-free replay of the fix, never as a
proof on its own. Configs: `configs/{baseline,experiment,campaign}/slurp-native-stage3-comp1-fold-a-rec-*`;
derivation `scripts/flights/comp1/derive_slurp_comp1_recovery_cells.py --variant rec`.

**The recovery counter.** This is COMP-1's **ONE** root-diagnosed recovery re-registration. A second
failure CLOSES cell COMP-1: no third registration.

**The aborted run.** Its two rows (`SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` and its FIT row) are marked
`consumed = yes` at countersignature; its 1,913 contacts stay charged to it; no row of it is kept,
scored or read.

## 3. The measurement declaration

The package's `registered-facts-v1.json` declares, keyed by the -REC run ids, a Stage-3 measurement
block **identical to the arm's**: `cross-flight-with-in-chain-replicate`, expected effect 3.23 pp
intent (the coordinator's declared basis, unchanged), 1,080 rows, benefit claimed, replicate
`SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`; the smoke keeps the parent smoke's form-proof block. **The
recovery does not re-declare.** Disclosed: the A/A flew in the aborted chain and is FINALIZED; the -REC
arm flies in a later chain, so the replicate is no longer strictly in-chain. It is reused as the
comparator, not re-flown.

## 4. The ledger

Four DRAFT rows: the -REC arm, its FIT identity, the smoke and its FIT identity. The READ row
`SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1` is unchanged: the COMP-1 read is one read whichever
recovery form carries the arm, and this package's recipe names the -REC arm.

## 5. The flight

G5 never started in the aborted chain (no `runs/` or `attempts/` directory under its run ids, verified
2026-09-28). `scripts/flights/comp1/batch_chain_comp1_rec.sh` flies ONE queue of two steps: the -REC
smoke then the -REC arm; the G5 smoke then the G5 arm, exactly as `batch_chain_comp1_g5.sh` had them.

Flip: `bash scripts/flights/comp1/comp1_rec_flip.sh` (loop form; refuses until the receipt lists the four
-REC run ids, the aborted rows read `consumed = yes`, the -REC rows read `consumed = no`, the A/A is
FINALIZED and nothing of -REC or G5 has started). Launch: `bash scripts/flights/comp1/batch_chain_comp1_rec.sh`.
