# Cell COMP-1: the first composed Stage-3 arm

Registered before contact 2026-09-27 at study commit `8d403ffa` (owner decisions 138 and 152);
all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**THE EXPECTATION IS NOT DECLARED YET, ON PURPOSE.** `stage3_measurement.SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1.expected_effect_pp`
is the literal string `the coordinator-declared value (placeholder until 2026-09-27; declared 3.23 pp from the measured conversions, see expected_effect_declaration)` in BOTH places the gate reads:
`registered-facts-v1.json` (top-level `stage3_measurement`, canonical) and the fenced json block of
`../2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md`. Owner decision 139 forbids a prior; decision 152 says the number is composed by the
coordinator from the AGREE and KPROBE reads' measured m values. Until the coordinator replaces the string with
a number in both places, `scripts/checks/stage3_effect_floor_check.py` refuses the arm as
`unparsable-declaration` -- **that refusal is the intended state of this package**, and the flip must not be
run before it clears. What the coordinator composes over is registered here: m_agree = 32 of 70 (read), m_kprobe
(pending), the per-row headroom 0.092615 pp intent, and the four exclusive classes below -- the two
newly-delivered sets share 47 of their 78 rows, so the two m values do not add.

**What COMP-1 is.** The locked v2.0 plan (the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`) with FOUR changes composed,
each registered and measured separately, and nothing else: (1) the agreement term exactly as cell AGREE carries
it -- `w_agree` 1.0 over the self-excluded exemplar-intent vote, recall `k` 60, delivered `fuse_coverage` 8-1-8
([`docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1`](../2026-09-26-slurp-stage3-agree-w1-fold-a-v1/README.md)); (2) the centroid boundary key exactly as cell KPROBE pins it --
`facet_source` `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` sha256 `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532`
([`docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1`](../2026-09-27-slurp-stage3-kprobe-fold-a-55-v1/README.md)); (3) the citation contract as a row-127 no-harm base item (decision
152): policy `phase-native-candidates-review-revise-cited-v1`, Solver `response_format_id` `saea-solver-cited-answer-v1`,
instruction `probes/slurp_native_role_solver_cited_v1.txt`, `deliver_normaliser`
`saea-deliver-cited-answer-normalise-v3-v1` (`rails/solver_citation.py`; +134 instruction tokens per Solver contact,
+26 output skeleton and 12.71 per cited id, measured on the sealed PLAN trace; byte-identical default); (4) nothing
else. The composed-config diff against the locked PLAN cell is proven in `registered-facts-v1.json`
(`composed_config_diffs`: `arm_vs_locked_plan` = the three factor groups + `k` 8 -> 60 + bookkeeping;
`aa_vs_locked_plan` = `k` alone + bookkeeping; `arm_vs_aa` = the three factor groups ALONE; `anything_else` empty
in every entry) and re-proven by `tests/unit/test_comp1_config.py`.

**Three cells, one chain.** `configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json` carries the A/A replicate **and** the arm (instrument rule 4); the
four-row smoke is outside the plan and never scored. The A/A is the PLAN lock's own bytes -- `w_agree` 0.0, no
`agreement_source`, the written key, the un-armed citation default -- at the same recall `k` 60, so the two arms
differ in the three composed factors alone. **Its prepared first-phase supply reproduces the sealed comparator's
output digest `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` on all 1,080 rows (verified in this registration; 8,624 selected value ids).**
The arm's own prepared supply carries output digest `ce68bebcf2bbf5502b081221a92c3fde1095da3979106bcdddb6eeeca9e9c41a` (1,079 rows seeded, 8,626 ids)
and the smoke's `1d55ea73ae0ef4ef2d175e66303eaa5b500c7fc2a3ac356f3808686deba051e0` (4 rows).

**Composed delivery, measured model-free before contact** (`attribution-classes-v1.json`, by `scripts/flights/comp1/comp1_attribution_classes.py`):
of the 191 PLAN intent-wrong rows the locked plan delivers the gold boundary entry on 86, the agreement term alone on
156, the centroid key alone on 136, and **the composition on 162 (84.8 %)**. The five exclusive classes decision
152's read is attributed over, membership fixed now, outcome read after the seal:

| class | rows | delivered under COMP-1 | by bank class |
| --- | ---: | ---: | --- |
| delivered-but-wrong (delivered under the locked plan) | 86 | 82 | {'INTENT-COVERED': 59, 'INTENT-UNCOVERED': 27} |
| newly-by-both (in CONV's 70 and KPROBE's 55) | 47 | 46 | {'INTENT-UNCOVERED': 47} |
| newly-by-agree (CONV's roster only) | 23 | 23 | {'INTENT-UNCOVERED': 23} |
| newly-by-centroid (KPROBE's roster only) | 8 | 6 | {'INTENT-COVERED': 1, 'INTENT-UNCOVERED': 7} |
| catch-all | 27 | 5 | {'INTENT-COVERED': 1, 'INTENT-UNCOVERED': 26} |

Seven rows a single factor or the plan delivers are NOT delivered under the composition, and five catch-all rows are
delivered only under it (ids in the file). On the whole roster the composition gains delivery on 107 rows and loses
it on 6 (by bank class in the file; the harm side of the read). **One row is seeded with no boundary entry at
all** (`slurp:train:015793:audio-1490106752`, INTENT-UNCOVERED, catch-all): its sealed speech vector has cosine -0.0039 to its nearest
centroid key (negative to all 60, against +0.0533 to the nearest written key), the fuser admits a candidate only at
cosine >= tau 0.0, so nothing is admitted -- a property of the centroid key alone, tolerated by the runtime and
reported by the read.

**Fit.** The prompt budget binds to the live 24,576-token slot with a one-eighth reserve; the locked plan's Solver
phase already reads COMPACT_REQUIRED with a positive physical margin (2,755 tokens at 21,278 rendered) and proceeds
under `compact-or-abstain`; the cited Solver instruction adds 134 tokens, leaving a positive physical margin of about
2,621 before compaction. The runtime's own `check` measurement is folded into `registered-facts-v1.json` (`fit`).

**`stage3_algorithm`.** The arm and the smoke carry `sealed-credit-system-policy-v1` with `operators_used`
`["context_application"]` -- the family's step (iv), the re-execution of a composed policy chosen and credited over
sealed bytes, beside its in-chain replicate; this cell performs no rollout, scoring, credit or update of its own, and
the citation credit table it seals is the INPUT to the next round's credit. The A/A carries `none`.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence (placeholder to be filled) |
| `registered-facts-v1.json` | every model-free fact, the composed-config diffs, the CANONICAL `stage3_measurement` (placeholder to be filled), the two fill points |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired read and the per-class attribution table, step by step |
| `attribution-classes-v1.json` | the 191 rows' class membership and composed delivery, fixed before contact |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1/comp1_mint_receipt.py` |
| `shared-aa-proof-v1.json` | owner decision 160's condition, proven model-free: the two A/As' composed configs, prepared supplies and request bytes compared (identity hashes quoted by 16-hex prefix, because the flip re-pins every JSON file of this package) |

**Budgets (the AGREE arithmetic; the citation adds tokens, never contacts).** Per generation cell 11880 contacts
(1,080 x 11, run-cumulative), 47520 FIT endpoints, 6480 native task-contract calls,
33930 repeated speech seconds, 12.0 GPU hours, one official complete score; the smoke
44 / 176 / 117 s, no score.

**Owner decision 160: this A/A is ALSO cell G5's in-chain replicate.** COMP-1 and G5
([`../2026-09-27-slurp-stage3-g5-fold-a-v1`](../2026-09-27-slurp-stage3-g5-fold-a-v1/README.md)) each registered an in-chain A/A that re-flies the locked
PLAN plan's own request bytes; decision 160 (row 160 of `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`)
flies ONE, this package's `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`, in the same chain as both arms, conditional on the two
A/As being byte-identical -- checked model-free before any flip, **verdict `IDENTICAL`**
([`shared-aa-proof-v1.json`](shared-aa-proof-v1.json), by `scripts/flights/comp1/comp1_g5_shared_aa_proof.py`, zero
contacts):

| proof | what it compared | result |
| --- | --- | --- |
| 1. composed config | every leaf of the two composed A/A configs, flattened | 20 differing leaves: 19 bookkeeping (cell / run / attempt / FIT ids, the readiness block and its requirement pin, prose, the generation-budget target) and ONE supply-recall-width leaf, `knowledge_stores.intent-boundaries.phase_supply.perception.k` 60 vs 8; nothing request-affecting |
| 2. prepared supply | `core.flight.cli prepare-supply` for both A/As into a scratch directory | output digest `ba5e1faa...` on both, 1,080 rows, 8,624 value ids each -- the recall width is output-neutral; this A/A's fresh mint reproduces its registered pin byte for byte |
| 3. request bytes | each A/A's REAL dispatch against the REAL llama-server transport with a fake POST (canned role answers; Planner REVISE on first visit for 61 of 120 rows), serial | under ONE scratch run id: all 663 canonical payloads and all 663 POST bodies byte-identical; under their OWN run ids: all 663 POST bodies byte-identical, payloads identical up to `history[].source_query_state_sha256` (a custody hash over a QueryState whose `query_id` embeds the run id -- never sent to the model) |
| self-control | this A/A dispatched twice at the production np4 concurrency, 12 rows | the SAME cell differs from itself in `request_id`, the provenance relpaths, `source_query_state_sha256` and the POST body's `id_slot` -- arrival-order and run-id fields, which is why proof 3 dispatches serially |

Nothing in COMP-1's cells, campaign plan, declaration or placeholder moves. G5's arm re-declares its
`replicate_run_id` to this A/A, G5's own A/A pair is superseded unflown, G5's campaign plan carries its arm alone, and
both families flip and fly together (below). Both arms are read at the same null in the same serving state.

**The coordinator sequence (decision 160).** (1) **Declare**: the coordinator replaces the placeholder with the number
composed from the AGREE and KPROBE reads in the two places named above and commits (decisions 139 and 152); nothing
else in either package waits on it. (2) **Merge** the branch carrying decision 160's wiring to master. (3) **Mint**:
root runs `scripts/flights/comp1/comp1_mint_receipt.py` (six eligible run ids; it refuses while the placeholder
stands) and `scripts/flights/g5/g5_mint_receipt.py --drop-aa` (four eligible run ids: G5's arm, smoke and their FIT
identities). (4) **Countersign** COMP-1's seven DRAFT rows and G5's five live DRAFT rows (never G5's superseded A/A
pair). (5) **Flip**: `scripts/flights/comp1/comp1_g5_flip.sh` refuses unless the proof says `IDENTICAL`, the G5 plan
is the arm alone and the G5 receipt was minted without its A/A; it runs `comp1_flip.sh` (the placeholder refusal and
this package's three cycles -- the A/A's re-minted supply must again be `ba5e1faa...`), then G5's smoke and arm
cycles, then re-runs all five cycles until one whole pass commits nothing, and writes the ONE converged HEAD to
`/home/chao/comp1g5-flight-commit.txt`; `--allow-output-change` is never passed. (6) **Queue**
`scripts/flights/comp1/batch_chain_comp1_g5.sh` behind whatever occupies the np4 session (decision 77): ONE driver queue
of two steps -- the COMP-1 smoke, then this package's plan (the shared A/A, then the COMP-1 arm); the G5 smoke, then the
G5 arm -- because the batch driver flies one smoke per step. `batch_chain_comp1.sh` alone now refuses (it would leave G5
without its in-chain null) unless `COMP1_ALONE=1` records that the owner withdrew G5 from the chain.

**Not authorised by this package.** No flight before the expectation is declared, the receipt is minted and all
three cells are flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or
DEV read; no fourth factor; no store rebuild or release; no re-pin of the 211 committed configs; the citation part is
never reported as a gain.

## Recovery attempt (resume)

The arm attempt `attempt-slurp-native-stage3-comp1-fold-a-generation-v1` ABORTED on 2026-09-28 at contact
`flight-1854` (flight commit `cb628f59`; 471 rows settled, 1 incomplete, 608 never started; 1,913 contacts; trace
SHA-256 `029a2dbb...61997`) on a Solver citation-contract refusal
(`docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md`; fix `a451f942`). The shared A/A FINALIZED
before the arm opened and is never re-flown; G5 never started. The owner rules between two HELD recovery forms;
**either is COMP-1's ONE recovery re-registration** and a second failure closes the cell.

**Variant 1, the resume (owner decision 22, item E10).** The same run id under
`attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume` with `resume_from` the aborted attempt and its trace
SHA-256; 471 rows kept under I7r custody, 609 flown; run-cumulative worst case 8,612 of 11,880. Package
[`../2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/`](../2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/),
note `../2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md`. Decision 22's letter (code and
request bytes unchanged) is broken by the citation fix and by the resume-replay repair
(`core.flight.resume.NON_WIRE_CONTACT_BLOCKS`, without which the replay classified 0 of 471 settled rows
COMPLETE); its purpose is proven by `scripts/flights/comp1/comp1_resume_byte_identity_proof.py` (PASS: 481 of 481
kept citation records byte-identical under the fixed code; the one changed disposition lies in the re-flown row).
Flip `scripts/flights/comp1/comp1_resume_flip.sh`; launch `scripts/flights/comp1/batch_chain_comp1_resume.sh`.

## Recovery re-registration (-REC)

**(SUPERSEDED UNFLOWN 2026-09-28 by owner decision 175: the recovery flies as the RESUME attempt; never launched)**

**Variant 2, the full re-fly.** `SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1` over all 1,080 rows plus its four-row smoke
`SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1`, the parent bytes except identities and the recovery note, the
measurement declaration identical to the arm's (3.23 pp; not re-declared), the aborted run's rows marked
`consumed = yes` at countersignature. Package
[`../2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1/`](../2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1/), note
`../2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1-preregistration.md`. Flip `scripts/flights/comp1/comp1_rec_flip.sh`;
launch `scripts/flights/comp1/batch_chain_comp1_rec.sh`.
