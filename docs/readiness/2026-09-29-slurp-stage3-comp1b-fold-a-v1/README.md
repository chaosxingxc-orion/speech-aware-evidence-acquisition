# Cell COMP-1b: COMP-1 minus the citation contract

Registered before contact 2026-09-29 at study commit `e42e87f3e`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**Why.** The 2026-09-29 SLU-harm attribution note on branch `fable/comp1slu` (commit `e30aa1b61`,
[`docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md`](../../results/2026-09-29-slurp-comp1-slu-harm-attribution.md)) reads cell COMP-1's read
([`docs/results/2026-09-29-slurp-comp1-fold-a-read.md`](../../results/2026-09-29-slurp-comp1-fold-a-read.md): intent +4.26 [+2.41, +6.11], official SLU-F1
-2.24 [-3.97, -0.47] against the in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`) and names the Solver cited-answer contract
`saea-solver-cited-answer-v1` as the SLU cause: +102 false-positive entities on the 414 zero-gold rows (89% of the
whole +114 FP delta), worth -2.83 pp of pooled SLU-F1 by counterfactual row-swap. The I7n unwrap normaliser adds 0
entities (byte-proven on 1,080/1,080 rows) and the AGREE supply is not the cause (AGREE vs its own A/A is FP -5
[-32,+22], SLU +1.85). On the intent side the contract does not move the Solver's choice on identical Perception
shortlists (COMP-1 vs A/A: 170 identical shortlists, only 6 differ, 166 vs 166 rank-1 picks); the extra intent harms
track Perception's changed shortlist -- the supply (agreement term + centroid key), not the contract. The note's
channel table:

| channel | what was measured | pp |
| --- | --- | ---: |
| (a) the cited-answer unwrap (I7n) | 0 entities added, byte-proven 1,080/1,080 | 0.00 |
| (b) the Solver emitting more entities under the contract | +122 raw entities, +114 exact FP (+102 on zero-gold rows) | -2.83 (the whole guard loss and more) |
| (c) the AGREE / centroid supply changing the Solver's input | AGREE vs its own A/A: FP -5, SLU +1.85 (inside the null) | +0.15 to +0.29 (inside the null; not the cause) |

The note's own recommendation, verbatim: **"COMP-1 minus the citation contract, that is, AGREE + centroid key, on
TRAIN Fold A. The Solver setting is: policy `phase-native-candidates-review-revise-v1`; Solver template
`slurp_native_role_solver_v2.txt`; no response format; deliver normaliser `saea-deliver-normalise-v3`. Everything else
keeps COMP-1's bytes. Read it against the same in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`."** This package is exactly that cell.

**The one change.** Cell COMP-1b is cell COMP-1's OWN committed, already-flown baseline and experiment fragments
(`configs/{baseline,experiment}/slurp-native-stage3-comp1-fold-a-{baseline-}v1.json`) with the citation
contract's four leaf paths reverted, one arming across three JSON locations, and nothing else:

| key | COMP-1 (old) | COMP-1b (new) |
| --- | --- | --- |
| `policy` | `phase-native-candidates-review-revise-cited-v1` | `phase-native-candidates-review-revise-v1` |
| `phase_material.solver.instruction_template` | `probes/slurp_native_role_solver_cited_v1.txt` | `probes/slurp_native_role_solver_v2.txt` |
| `phase_material.solver.response_format_id` | `saea-solver-cited-answer-v1` | `null` |
| `native_episode.deliver_normaliser.normaliser` | `saea-deliver-cited-answer-normalise-v3-v1` | `saea-deliver-normalise-v3` |

Proven by [`scripts/analysis/slurp_comp1b_diff_proof.py`](../../../scripts/analysis/slurp_comp1b_diff_proof.py) (re-run by `tests/unit/test_comp1b_config.py`): the composed config of
the COMP-1b arm differs from cell COMP-1's own committed arm by EXACTLY these four leaf paths plus per-flight
bookkeeping (this cell's own FIT ids, the dropped `prepared_phase_supply`, `what_this_is`) and the experiment
fragment's own metadata block (`cells`, `date`, `experiment_id`, `fragment_kind`, `purpose`,
`stage3_algorithm.note`) -- `anything_else` empty. The agreement term (`rank_weights.w_agree` 1.0, `agreement_source`
the sealed exemplar-intent vote, recall `k` 60) and the centroid boundary key (`facet_source` the released centroid
vectors) are asserted byte-for-byte equal to COMP-1's own, and the writer refuses otherwise. Same for the smoke.

**No new A/A.** The comparator is the EXISTING SEALED in-chain A/A `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` cell COMP-1 already flew and
consumed (owner decision 160's shared-A/A pattern, as cell G5 reused it) -- reused purely cross-flight, never
re-flown. `configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json` therefore carries the COMP-1b arm **alone**.

**`stage3_measurement`.** Unlike COMP-1, the expectation is DECLARED here, not a placeholder: `expected_effect_pp`
**4.26** (the measured COMP-1-vs-A/A intent delta, CI95 [+2.41, +6.11]), `claims_benefit` true, `measurement_design`
`cross-flight-with-in-chain-replicate`, `primary_metric_key` `intent` (owner decision 190, item D3), `replicate_run_id`
`SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`, guard `h_SLU` **1.2485** (the Fold A own null, the SAME margin COMP-1's own rule used). Against the
2.5 pp cross-flight floor at n = 1,080 (`scripts/checks/stage3_effect_floor_check.py`) the declared 4.26 clears it.
`tuning_roster` `slurp-train-construction-pool-agree-kprobe-r01-excluded` / `read_roster` `SLURP-EVO-FOLD-A-V2` (item D3): the agreement table and the centroid key
were built from a TRAIN construction pool disjoint from Fold A by construction, and their conversion probes were read
on Fold A subsets -- the same disclosed circularity COMP-1's own read already carries; no disjointness receipt is
committed for the construction pool yet, so `tuning-roster-unverified` (advisory) is the expected finding.

**`stage3_algorithm`.** The arm and the smoke carry `sealed-credit-system-policy-v1` with `operators_used`
`["context_application"]`, the same label COMP-1 carries: two typed, executable consumption actions (a rank weight
over a pre-computed vote, a retrieval key file) chosen and credited offline over sealed bytes, composed into every
row's Perception supply; this cell performs no rollout, scoring, credit or update of its own.

| file | what it holds |
| --- | --- |
| `../2026-09-29-slurp-stage3-comp1b-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed-config diff against COMP-1, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired read, the attribution-prediction check, step by step |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1/comp1b_mint_receipt.py` |

**Budgets (COMP-1's own arithmetic; removing the citation contract removes tokens, never contacts).** Per generation
cell 11880 contacts (1,080 x 11, run-cumulative), 47520 FIT
endpoints, 6480 native task-contract calls, 33930
repeated speech seconds, 12.0 GPU hours, one official complete score; the smoke
44 / 176 / 117 s, no score.

**Mint, flip, queue (not performed by this registration).** (1) Root countersigns the DRAFT exposure rows and mints
`coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json` from the draft (decision id `slurp-stage3-comp1b-fold-a-admission-v1`, the four eligible run ids). (2) A flip script
extending `scripts/flights/comp1/` re-pins smoke and arm through `repin_loop_generic.sh` until the package converges
at one HEAD; `--allow-output-change` is never passed; the flip mints each cell's own supply, expected to reproduce
COMP-1's own arm supply digest exactly (the citation contract never touches the first-phase supply). (3) A batch
chain script queues the smoke then the arm campaign behind whatever occupies the np4 session (decision 77).

**Not authorised by this package.** No flight before the receipt is minted and both cells are flipped; no contact by
this registration; no re-flying of the comparator or the sealed PLAN arm; no test-split, Fold B or DEV read; no
factor other than removing the citation contract; no store rebuild or release; no re-pin of the 213 committed
configs.
