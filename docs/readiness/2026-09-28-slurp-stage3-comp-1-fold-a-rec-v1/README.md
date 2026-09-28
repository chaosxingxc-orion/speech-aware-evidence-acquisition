# Cell COMP-1 -REC recovery re-registration package (variant 2, SUPERSEDED UNFLOWN)

**(SUPERSEDED UNFLOWN 2026-09-28 by owner decision 175: the recovery flies as the RESUME attempt; never launched)**

The registration note is
[`../2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1-preregistration.md`](../2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1-preregistration.md).
The parent package [`../2026-09-27-slurp-stage3-comp-1-fold-a-v1/`](../2026-09-27-slurp-stage3-comp-1-fold-a-v1/)
is never edited. Everything here was produced with zero model, tokenizer, encoder, scorer, server and GPU contacts.

| file | what it is |
| --- | --- |
| `README.md` | this runbook |
| `protocol-registered-v1.json` | the -REC protocol: the parent protocol by reference, the abort, both cells' identities |
| `generation-plan-registered-v1.json`, `fit-plan-registered-v1.json` | the -REC arm's registered plans |
| `smoke-generation-plan-registered-v1.json`, `smoke-fit-plan-registered-v1.json` | the -REC smoke's registered plans |
| `analysis-recipe-v1.json` | the parent recipe with the arm moved to the -REC run; READ run id unchanged |
| `registered-facts-v1.json` | the Stage-3 measurement blocks keyed by the -REC run ids, identical to the parent's (3.23 pp, not re-declared) |

## Recovery counter

COMP-1's **ONE** recovery re-registration. A second failure closes cell COMP-1.

## Launch sequence (after the owner rules for -REC)

1. Merge `fable/comp1rec` (the citation fix) and `fable/comp1res` (this package).
2. Root countersigns the four -REC DRAFT rows, marks the aborted run's two rows `consumed = yes`, marks the resume
   clauses and proof row superseded unflown, and mints `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json`
   (decision id `slurp-stage3-comp1-fold-a-rec-admission-v1`; eligible: the four -REC run ids).
3. `bash scripts/flights/comp1/comp1_rec_flip.sh` -- loop form; converges the -REC smoke, the -REC arm, G5 smoke and
   G5 arm at one HEAD and writes `/home/chao/comp1rec-flight-commit.txt`. Each re-pin rebuilds the inherited supply
   under the -REC run id and must reproduce the parent's output (arm `ce68bebc...`, smoke `1d55ea73...`); never
   `--allow-output-change`.
4. `bash scripts/flights/comp1/batch_chain_comp1_rec.sh` behind whatever occupies the np4 session.
