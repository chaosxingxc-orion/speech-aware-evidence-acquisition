# Cell G5: the Reviewer instruction that orders a retired tool, repaired

Registered before contact 2026-09-27 at study commit `81307ac3` (owner decisions 135 and 153,
a row-127 no-harm item for round 3); all three cells **held**. Nothing here authorises a flight, a flip or an
admission entry.

**The defect.** [`docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md`](../../results/2026-09-26-slurp-reviewer-planner-global-state-audit.md) section G5: the locked PLAN plan's Reviewer
instruction (`configs/probes/slurp_native_role_reviewer_v1.txt`, resolved from the composed config at `phase_material.reviewer.instruction_template`) opens by ordering
the Reviewer to call a task-contract tool "exactly once through its native function schema" and to "use only its
returned source-bound result". That toolkit was **RETIRED as item E25** -- `docs/receipts/harness-admission.json`, the entry with row
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`, status `RETIRED`, switch class `phase_tools`, after
[`docs/results/2026-09-20-slurp-b1-notool-verdict.md`](../../results/2026-09-20-slurp-b1-notool-verdict.md) (decisions 55, 56, 61) -- and the locked plan renders
0 tool schemas in every contact (`tool_calls` 0 in the sealed PLAN cost block).
The same day's summary diagnostic recorded the consequence: summaries treating a Reviewer's textual tool-result
claims as execution while the tool event list is empty. Decision 135 deferred the repair so that the AGREE read
would carry one prompt-byte change, not two; decision 153 admits it now.

**The measurement, reproduced** (`scripts/analysis/slurp_g5_reviewer_instruction_token_measurement.py` -> [`instruction-token-measurement-v1.json`](instruction-token-measurement-v1.json),
the audit's own vocab-only `llama-tokenize` and the audit's own split at "Then review"; zero model, server, encoder
or scorer contacts): the whole instruction is **82** tokens, the retired-tool order **52**
-- 52 / 82 = **63.4 %**, the audit's 63 % exactly. The surviving text tokenised on its own
costs **31** (not 82 - 52 = 30: "Then" at the start of a text is a different token from " Then" after a
space), so the wire saving is **-51 tokens per Reviewer contact**. The sealed PLAN arm
(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`) made **1,108 Reviewer contacts on 1,080 rows**
(1.0259 per row; role visits {"perception": 1080, "planner": 1108, "reviewer": 1108, "solver": 1118}, run-manifest `calls_used`
4,424), so the saving is **52.32 tokens per row** and
**56,508 per 1,080-row flight** (0.154 % of the arm's
36,742,293 prompt tokens). No cap is denominated in tokens, so no cap moves.

**The repaired instruction.** `configs/probes/slurp_native_role_reviewer_v1_g5_v1.txt` (sha256 `724a437de1eeb1167d11395ad78605d595e324e682cff552c27cb84caa8cef35`) is the old file with the two sentences
that order, describe and depend on the retired tool deleted and NOTHING added: word-level diff = `equal` and
`delete` opcodes only (42 of 70 words deleted, 28 kept in order), and old == deleted head +
new byte for byte. Two words a reader might also cut are KEPT on purpose and priced in the receipt: "Then" (deleting
it forces a case change, which is a rephrase) and "or invent a tool result" (it forbids fabricating a tool result --
the very failure the diagnostic recorded -- and neither orders nor depends on the tool).

**One pin, proven.** Arm and smoke: `phase_material.reviewer.instruction_template` `probes/slurp_native_role_reviewer_v1.txt` -> `probes/slurp_native_role_reviewer_v1_g5_v1.txt`; the composed-config diff
against the locked PLAN cells (`registered-facts-v1.json`, `composed_config_diff_against_the_locked_plan_cell`) is that
pin plus bookkeeping only (each cell's FIT identities and cap, no committed `prepared_phase_supply`, `what_this_is`).
The in-chain A/A is the locked form with the OLD instruction and bookkeeping alone. `phase_tools` is absent everywhere.
`tests/unit/test_g5_config.py` re-proves all of it.

**Owner decision 160: ONE shared in-chain A/A (2026-09-27).** COMP-1 and G5 each registered an in-chain A/A that
re-flies the locked PLAN plan's own request bytes; decision 160 flies ONE of them, COMP-1's
`SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`, in the same chain as both arms, on a condition checked model-free before any
flip: the two A/As' prepared first-phase supply digests and composed request bytes are byte-identical. **They are**
([`../2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json`](../2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json), verdict `IDENTICAL`, by
`scripts/flights/comp1/comp1_g5_shared_aa_proof.py`, zero contacts): both supplies carry output digest `ba5e1faa...` on
all 1,080 rows; the real dispatch of both A/As against the real llama-server transport with a fake POST produced
byte-identical canonical payloads and POST bodies on all 663 contacts of the first 120 rows (the Planner's canned REVISE
on 61 of them exercising the revision loop) under one scratch run id, and byte-identical POST bodies under their own run
ids (the payloads then differ only in the run-id-derived custody hash `source_query_state_sha256`); every differing
composed-config leaf is bookkeeping except the first-phase recall width `k` (COMP-1's A/A 60, this package's 8), which
the equal supply digests prove output-neutral. So:

- the arm's `replicate_run_id` is **`SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`** in `registered-facts-v1.json` (canonical)
  and the preregistration fence, with a `replicate_note` citing decision 160 and the proof; `analysis-recipe-v1.json`
  reads the delta at it; `registered-facts-v1.json` carries the whole re-declaration in `shared_in_chain_replicate`;
- this family's own A/A pair, `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1` and `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-FIT-V1`, is
  **SUPERSEDED UNFLOWN**: never flown, never consumed, never deleted -- its fragment, baseline, plans and exposure rows
  stay as the record of what G5 registered, and its rows say so;
- `configs/campaign/slurp-native-stage3-g5-fold-a-v1.json` carries the G5 arm ALONE; the receipt is minted with
  `g5_mint_receipt.py --drop-aa`; the family flips only through `scripts/flights/comp1/comp1_g5_flip.sh` and flies only
  in `scripts/flights/comp1/batch_chain_comp1_g5.sh` (`g5_flip.sh` and `batch_chain_g5.sh` refuse in this mode);
- `protocol-registered-v1.json` keeps its registration-time `comparator.in_chain_replicate` on purpose: every plan
  document pins that file's sha256 and every exposure row pins its plan's, so an edit there would cascade before the
  flip; the documents above take precedence.

**Three cells, one chain (the AGREE shape), as registered.** `configs/campaign/slurp-native-stage3-g5-fold-a-v1.json` carried the A/A
and the arm, because a cross-flight contrast with no in-chain replicate is refused outright (instrument rule 4); the
four-row smoke is outside the plan and never scored. If round 3 flies several consumption-form items in one chain, ONE
A/A can serve them all: drop this family's A/A from the campaign plan before the flip, re-point `replicate_run_id`,
and mint with `g5_mint_receipt.py --drop-aa` -- which is what decision 160 did (above).

**`stage3_measurement`.** The arm declares `admission` **`no-harm`** with `harm_margin_pp` **1.2485** (the gate's single
field, SLU, the design's measured floor at n = 1,080) and `harm_margin_pp_by_metric` intent **0.9943** / SLU **1.2485**
(the Fold A own-null half-widths of PLAN vs PLANr, instrument section 2d), `claims_benefit` false, `expected_effect_pp`
0.0, `measurement_design` `cross-flight-with-in-chain-replicate`, `replicate_run_id` `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`
(the shared A/A, decision 160; registered as this package's own `SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1`). The gate reads the
replicate as a run id and never asks which package registered it (`tests/unit/test_stage3_effect_floor_check.py`
proves both package orders). `scripts/checks/stage3_effect_floor_check.py` reads a
no-harm margin against the design's SAMPLING half-width (decision 127's own numbers), not against the rule-3 benefit
bar. **The rule:** admitted iff the intent CI95 lower bound against the in-chain A/A is not below -0.9943 and the SLU
lower bound not below -1.2485; HARMFUL on a measured loss; never reported as a gain.

**`stage3_algorithm`.** `none`: a deletion is not a policy search.

**COMP-2.** Decision 153 folds G5 into the composed round after round 3, so the pin is also prepared as a fragment:
[`comp2-pin-v1.json`](comp2-pin-v1.json) -- key `phase_material.reviewer.instruction_template`, value `probes/slurp_native_role_reviewer_v1_g5_v1.txt`, sha256 `724a437de1eeb1167d11395ad78605d595e324e682cff552c27cb84caa8cef35`.

| file | what it holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `instruction-token-measurement-v1.json` | the reproduced measurement, the deletion-only proof, the sealed Reviewer contact rate |
| `registered-facts-v1.json` | every model-free fact, the one-pin diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's two plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the standard paired roster read on intent + SLU under the no-harm rule |
| `comp2-pin-v1.json` | the fragment COMP-2 pins |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/g5/g5_mint_receipt.py` |

**Budgets, as arithmetic (AGREE's).** Arm and A/A each: 11,880 generation contacts (1,080 x 11, run-cumulative),
47,520 FIT endpoints, 6,480 native task-contract calls, 33,930 repeated speech
seconds, 12.0 GPU hours, one official complete score. Smoke: 44 / 176 / 24 / 117 / 1.0, never
scored. Expected spend per 1,080-row cell about 4,424 contacts and about 3.7 GPU hours at the sealed PLAN
arm's own rate, the arm minus 56,508 prefill tokens.

**No committed `prepared_phase_supply`, and empty requirements lists.** The flip mints each cell's own first-phase
supply under its own run id (item E16) and appends the requirement; `--allow-output-change` must never be passed. The
Reviewer instruction is not an input to the supply, so every minted supply must carry the sealed PLAN output digest
`ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` -- the flip's byte-identity check.

**Mint, flip, queue (decision 160: together with COMP-1).** The coordinator sequence is written once, in
[`../2026-09-27-slurp-stage3-comp-1-fold-a-v1/README.md`](../2026-09-27-slurp-stage3-comp-1-fold-a-v1/README.md): COMP-1's expectation is declared, the branch is
merged, root countersigns the five LIVE DRAFT rows of this family (the arm, the smoke, their FIT identities and
`SAEA-SLURP-G5-REVIEWER-INSTRUCTION-TOKEN-MEASUREMENT-V1`; never the superseded A/A pair), mints
`coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json` (id `slurp-stage3-g5-fold-a-admission-v1`) with
`scripts/flights/g5/g5_mint_receipt.py --drop-aa` (four eligible run ids), beside COMP-1's receipt, flips BOTH families
with `scripts/flights/comp1/comp1_g5_flip.sh` (COMP-1's three cycles, then `g5_repin_smoke.sh` and `g5_repin_arm.sh`
-- never `g5_repin_aa.sh` -- converged at one HEAD), then queues `scripts/flights/comp1/batch_chain_comp1_g5.sh`
behind whatever occupies the np4 session (decision 77). As registered this read: root countersigned all seven rows,
minted six eligible ids, flipped with `g5_flip.sh` and queued `batch_chain_g5.sh`; that path is superseded.

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no re-pin of
the 211 committed configs; no report of a gain; no admission entry.
