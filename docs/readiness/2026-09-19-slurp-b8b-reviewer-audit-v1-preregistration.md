# Cell B8b: the Reviewer slot-audit context block, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B8b registration agent, main checkout
`studies/speech-aware-evidence-acquisition`, base commit `25a7f325` (item E12 merged). Authority:
**owner directive 26 of 2026-09-18** ("analyses into nodes"), which names cell B8b; **owner decision
27 of 2026-09-19**, which puts B8b after cell B7r in the order; **owner decision 15 of 2026-09-17**
(a cell does not fly on a HARMFUL predecessor's base); **owner decision 23 of 2026-09-18** (the bar
and every final evaluation read the OFFICIAL, unprojected `slurp-slu-official-train` number);
**owner decision 25** (the HARMFUL form); **owner decisions 7 and 14** (projection v3 as fixed
post-processing; the TRAIN symmetric sibling); **owner decisions 11-12 of 2026-09-17** (the Reviewer
seat is criticism-only; the Node Context Policy cells); **owner decision 17** (the per-scenario
net-harmed-rows diagnostic); **owner decision 22** (the resume-recovery clause every new
registration carries). All in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`.
Engineering: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` section 3, item
**E12**, and `docs/superpowers/specs/2026-09-17-node-context-policy-design.md` sections **16 and
16.1**.

This document grants no model contact. Both cells it registers stay readiness `held` until the
coordinator mints the root decision receipt and flips them with `scripts/flights/repin_cell.py`.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer, server
and paid-API contacts**. The resident service was never started, stopped or queried; **no run
directory was read or written**; no flight lock was touched; and no utterance text, filler or gold
is printed or persisted anywhere in this package.

## 1. Why this cell exists

Owner directive 26 rules that an offline analysis this program trusts belongs **inside an agent
node**, not only in a report. Cell B8a is the directive's write-side instance — an analysis applied
as a transform of what the episode *delivers*. **B8b is its read-side instance.**

Today the Reviewer is handed the draft and nothing else. Cell B7r fixes the *shape* of what the
Reviewer writes; it gives the Reviewer nothing new to reason from. Meanwhile the A3 audit
(`docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md`, T5/T6) measured that **81 of
135 gold-`date` rows emit no date at all** and **46 of 72 `time` rows emit a non-exact filler**, and
the entity-loss attribution (`docs/results/2026-09-14-slurp-train-a-entity-loss-attribution-v1.md`)
measured that **184 of the 414 empty-gold rows emit an entity anyway**. Those are exactly the
failures a critic could catch — if the critic were told what this intent's slots normally look like.

Cell B8b tells it, deterministically and from construction data only. The question:

> Does rendering the intent's construction slot profile and four harness-computed flags as declared
> context at the `reviewer:current-draft` boundary raise pooled official SLU micro F1 on TRAIN Fold
> A, against cell B7r, without harming intent?

## 2. What the block is, and what it is not

**It is** one `episode`-class key, `native_episode.reviewer_audit` — the **fifth and last** member
of `rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS` — armed with the released construction view
`slot-audit-v1`, its two committed pins and its three thresholds. `rails.slot_audit` plus the
committed template `configs/probes/ncp_slurp_slot_audit_reviewer_v1.txt` render that table, for the
draft under review, as a block **appended after** the boundary's own L1 rendering with one newline
between them.

**It is an ADDITION, never a rewrite.** The L1 draft block above it is produced by the same code and
the same template as on cell B7r, byte for byte. That is why the block *requires* the
`reviewer:current-draft` boundary at level `structured`: it has nothing to attach to at `raw` and
would be replaced at `cleaned`, and both are refused by name before any contact.

**It is deterministic and zero-contact.** No model, tokenizer, encoder, scorer, tool, server or
network contact. The bounded ceiling stays 11 and **every budget is cell B7r's, unchanged.**

**It is not a judge and not a retriever.** All four flags are computed by the harness
(`rails.slot_audit.slot_audit_flags`), never by a model. The block performs no retrieval, adds no
evidence block, and is not a phase's material or supply.

**It moves request bytes, at exactly one boundary, by design.** That is why it is an `episode`-class
switch and not a `run`-class one: no `request-bytes-identical` falsifier can exist for it.
`tests/unit/test_native_episode_runner_reviewer_audit.py` runs the real episode twice through the
shared fake transport and shows that **exactly the Reviewer contacts move** and every Perception,
Solver and Planner contact renders byte-identical bytes.

### The boundary that makes it legal

Section 16 of the NCP design fixes it for every B8 node: **construction data and closed lists only.**

- The table is mined from the governed SLURP TRAIN split **minus every utterance with a recording in
  TRAIN Fold A, TRAIN Fold B or DEV-1000** (the 2026-09-13 exclusion; 2,160 excluded utterances) —
  the same pool `scripts/build_slurp_exemplar_pool_assets.py` pins for module M1, bound to that
  pool's identity hash `67e53fb5…`. 60 intents, 54 entity types, 9,354 construction utterances.
- It carries **counts and shares only**: no filler, no sentence, no utterance id, no recording, and
  **no gold of any evaluated row**, at build time or at runtime.
- The draft's own fillers are read **only** by the `REPRESENTATION` predicate and never reach a
  rendered line; a flag names a **type** and its counts.
- It is a committed repository artifact (`knowledge/slurp/semantic/slot-audit-v1/`) rather than a
  `SPEECHRL_DATA_DIR` store for exactly that reason: its pin is a git blob hash an auditor can check
  offline. Build receipt: `docs/receipts/knowledge/slurp-slot-audit-v1.json`, `execution_profile`
  `model-free-check`, model / tool / encoder / scorer contacts all 0, decontamination verdict
  `clean`.

The four flags, all harness-computed:

| Flag | Fires when |
| --- | --- |
| `TYPE-UNSEEN` | a draft entity type is not attested with this intent anywhere in the construction pool |
| `EMPTY-DRAFT` | the draft declares no entity while at least `empty_draft_min_entity_row_share` (0.5) of this intent's construction rows carry one |
| `MISSING-COMMON` | a type above `missing_common_min_row_share` (0.5) of this intent's construction rows is absent from the draft; `date` and `time` are named like any other type |
| `REPRESENTATION` | a `date` or `time` filler breaks the released spoken-form convention `saea-spoken-form-v1` — no ASCII digit, no colon, no slash |

`profile_min_row_share` (0.05) bounds how many types the profile **lists** and gates no flag.

## 3. The one factor, and the one further key that is not a factor

**The factor.** Exactly one composed key moves against cell B7r's baseline:
`native_episode.reviewer_audit`. Dropping it — together with the harness-robustness key below —
reconstructs cell B7r's `native_episode` block exactly. Proved on the committed fragments and on the
composed configuration by `tests/unit/test_b8b_reviewer_audit_config.py` and
`tests/unit/test_config_table_module_switches.py::test_the_two_b8b_fragments_arm_the_block_and_nothing_else`.

Held identical: the B7r role graph (perception 1, solver 1, reviewer up to 3, planner 1,
`max_revisions` 1, program `phase-native-candidates-review-revise-findings-v1`, ceiling 11), the
policy `typed-slurp-node-context-v1` at level `structured` with the same twelve boundary entries and
the same `producers` block, `phase_material` (the Reviewer keeps
`probes/slurp_native_role_reviewer_v1.txt` and the `saea-review-findings-v1` output contract),
`phase_tools`, `task_instruction_template` `probes/slurp_native_role_context_v3.txt` and its fill,
`knowledge_stores`, `scorers` (`slurp-slu-official-train`, `cost`), the geometry, the roster, the
split, the packets, and the prepared Perception supply reused byte for byte. The bookkeeping that
must differ is four fields: the FIT run and attempt ids, the two provenance-only speech-feature ids
and the free-English `what_this_is` note.

### 3.1 `native_episode.finite_completion_policy` — a harness declaration, not a factor

The coordinator added one further key to both B8b baselines on 2026-09-19, **before any hash in this
package was pinned**:

```
native_episode.finite_completion_policy = "deliver-latest-or-abstain"
```

**Why, root-diagnosed rather than preferred.** Cell B7a's recovery arm aborted after **1,451
contacts** because one Reviewer completion came back with `finish_reason` `length` at the 512-token
cap and the harness default `finite_completion_policy` is `"raise"`
(`rails/native_episode_config.py`). The SLURP anchor and every B cell so far omit the key, so each
of them is one capped completion away from losing a whole flight.

**What it does.** `"deliver-latest-or-abstain"` — already implemented and tested
(`reproduction/ojw/native_episode.py::_finite_terminal_outcome`, `rails/native_episode_receipt.py`,
`rails/runner.py`) — **retains** the row with a `terminal_disposition` whose `reason` is
`"finite_completion"`: the latest delivery-eligible Solver draft is delivered, or the row abstains,
instead of the flight aborting. The capped completion itself is quarantined and never becomes the
delivered answer: `rails.runner` refuses the episode unless the disposition's `rejected_contact`
matches the actual quarantined completion hash for hash.

**It renders no request byte.** The key is read once by `rails.runner` into the core
`NativeEpisodeSpec` and reaches no template, no instruction, no evidence block, no agent state and
no decoding parameter. It cannot move a `MODEL_REQUEST` byte, so **the wire-side one-factor claim of
this cell is unaffected by it**: on any row where no completion hits the cap, the episode is the
base's episode down to the byte. It is also **not** a member of `EPISODE_LEVEL_SWITCH_KEYS` and
claims no module admission; several committed A2T, Earnings and SLURP baselines already carry it at
this value.

**The asymmetry it creates, stated before contact.** It *can* change an outcome, on exactly the rows
where a completion hits the cap. Cell B7r's comparator arm flies under the base's own policy, so a
**sealed** B7r arm implies B7r met no finite completion at all — had it met one it would have
aborted rather than sealed. Any B8b row whose `terminal_disposition.reason` is `"finite_completion"`
is therefore a row the comparator could not have produced, and the pair is not clean on that row.
**The count of such rows is a mandatory diagnostic** (section 6). If it is zero the contrast is
unaffected and the verdict says so; if it is non-zero the verdict reports the count, the affected
sample ids, and the primary metric recomputed with those rows excluded **beside** the registered
all-rows number, which stays the number the decision rule reads. **No row is ever filtered out of
the scored manifest**; every retained row is scored as delivered.

## 4. Arms, comparators and order

| role | identity |
| --- | --- |
| **arm** | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-generation-v1`, cell `slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1`, composed `c8599381f789c332597bbfc8008e64943fd7c3c3cd64c3abf49c4860ead58c6b`, protocol `4997c665acc71869843dd31f0c920ceaacc18384d21db92cf809c57617f3cbae` |
| **arm FIT** | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-fit-v1`, 47,520 endpoints, inside the same campaign |
| **smoke** | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-generation-v1r`, cell `slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-v1`, composed `097e94c094459dcbf14b0ae01067b418124bd334acbe2047f34ac870bc909139`, protocol `6673658fb37f7e562bd31976a869b51e4365ba26332a09262024144fd2035a83` |
| **smoke FIT** | `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-FIT-V1` / `attempt-slurp-native-ncp-l1-reviewer-audit-anchor-smoke-4-fit-v1`, 176 endpoints, inside the same worker |
| **comparator, primary** | **cell B7r's sealed bytes**, run `SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1`, composed `c17c661c…`, protocol `2d3b2a86…`. **B7r has not flown.** Its score, outputs and manifest SHA-256 are `PENDING_B7R_SEAL` in the analysis recipe and are filled in from its own seal. |
| **comparator, secondary** | cell B7a's sealed bytes, run `SAEA-SLURP-NATIVE-NCP-L1-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1` (in flight at this registration), `PENDING_B7A_SEAL`. It gates nothing; it exists so the verdict can decompose the delta over anchor → B7a → B7r → B8b. |
| **context only** | the sealed dual-store anchor `SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (scores `73608763…`, outputs `d87d71e8…`, manifest `049ac230…`; official 48.53 / 77.96) and the released TRAIN A direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1` (scores `7840a959…`, manifest `54610905…`; 33.89 / 73.70 / 82.69 / 75.09 / 21.10) |

**Hash provenance, stated plainly.** The two context arms' hashes are **carried verbatim** from the
registered B7r package (its section 2) and the registered B8a package (its section 5), each of which
re-derived them by hashing the file. They were **not** re-derived here: a GPU campaign was in flight
and this registration touches no run directory at all. They must be re-verified by hashing the files
at read time, together with the two PENDING seals.

All arms share the roster `docs/receipts/rosters/slurp-evo-fold-a-v2.json`
(`1fe7908c31396774d7535fdf37bd791762215c324999d66ed7beb9e7b2f9033d`), split `SLURP-EVO-FOLD-A-V2`,
split identity `61b0f062…`, role `discovery`, 1,080 rows, 125 speaker clusters, 18 scenarios of 60
rows, 523 headset and 557 far-field rows, and the resident session
`serving-slurp-native-candidate-five-train-a-np4-v1` (attach only, never spawn). The four-row smoke
uses the four already-exposed TRAIN A engineering rows (split identity `4e3413fe…`).

**No comparator is ever re-flown or re-scored. No twin is registered**: a derangement or
token-matched control flies only if this cell shows a positive CI95 against B7r, by the program's
twin rule.

### Which side of the delivery node this contrast sits on

The B8a preregistration section 4 requires every later cell to say this, and it now has an answer:
module **M3 was ADMITTED on 2026-09-19** and `native_episode.deliver_normaliser` entered the SLURP
default plan (commit `a533f6dc`).

**Both sides of this contrast are node-free.** Cell B7r's baseline and both cell B8b baselines
declare no `native_episode.deliver_normaliser`, so the delta this cell measures is neither
contaminated by the delivery node nor inflated by it. It does mean that **neither arm is the current
SLURP default plan**: the official numbers this cell reports are node-free numbers and are not
directly comparable to a later node-carrying arm. The verdict states this. Measuring cell B8b on a
node-carrying base would be a **new cell** with its own registration, not an edit of this one.

### Order, and it is part of the registration

1. The **four-row smoke** opens only **after cell B7r's own four-row smoke has sealed**, so the two
   form smokes are never in flight together.
2. The **1,080-row arm** opens only after **cell B7r's arm has sealed and been read NOT HARMFUL**
   (owner decision 15), and after this cell's own smoke has sealed.

One experiment in flight at a time.

## 5. The prepared Perception supply — inherited, and the rebuild proves something

Item E12 states that cell B8b owes **no new preparation**: the slot-audit block is a consumer-side
context addition at one boundary and moves no supply, no retrieval and no evidence block. Both pins
are cell B7r's own, **verified in this registration by hashing the files** under `SPEECHRL_DATA_DIR`,
read-only:

| cell | prepared artifact | SHA-256 | Perception `output` SHA-256 |
| --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-TRAIN-FOLD-A-V1/phase-supply-v2.json` | `391177e18797854db0f41648a4de23a3ff100288e653032bb4c2dae09d8d44cd` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` (1,080 of 1,080 rows — the sealed anchor preparation's own output) |
| smoke | `prepared/SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-AUDIT-ANCHOR-SMOKE-4-V1/phase-supply-v2.json` | `7c9d1e17d2637e18378225ff768e929badbf5c82cbe9a19b7ffbf4e52cb1c1f9` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` (4 of 4 rows — the four-row reference every form smoke of this roster shares) |

**A rebuild is expected, and it is the enforcement.** `core.preparation.artifact_inputs` pins the
cell's **whole composed configuration**, and this cell's differs from B7r's by its two declared keys.
Measured model-free in this registration:

| cell | B7r prepared identity | B8b prepared identity |
| --- | --- | --- |
| arm | `757dfc5b4f4d2127ab041ad3b57d4772c2e921fcf6471ee0b1356bf8c1f3f990` | `7799e57ac7ae47419ac8e5349c5dd49045eb6a570f65c22ea6c5d950a723952d` |
| smoke | `e3d880e111917fee4fb4b7654bde0c00f773d6f9574ce1a2501c93b29be85f68` | `fcd664ae1a9d4e156844321441787ead77c1642cc2ad558c50d8c4830babc17f` |

The two B7r values **reproduce the ones stored inside B7r's own prepared artifacts**, which is what
makes this a checked statement rather than an inference. `core.flight.repin` will therefore derive a
fresh artifact into this run's own prepared directory, and `_compare_artifact_output` will **refuse**
that rebuild unless its Perception output is byte-identical to the inherited one. That refusal is
the model-free proof that neither declared key moves a knowledge-selection byte.

> **`--allow-output-change` must never be passed.** If the output SHA-256 stops being `ba5e1faa…`
> (arm) or `512583ec…` (smoke), a merge changed the knowledge channel — **stop and report.**

**One known refusal, found here rather than at launch.** Because these pins are *cell B7r's own*, a
rebuild changes both the pinned `relpath` and the pinned `sha256`, and
`core.flight.repin.assert_no_residue` then scans all of `docs/` and `configs/` for those old strings
and refuses — because **cell B7r's own committed fragments legitimately still carry them**
(`configs/{baseline,experiment}/…-reviewer-format-{train-fold-a,smoke-4}…json`). The check is
correct behaviour meeting a case it was not written for, not a defect in this package. The runbook's
section 2.1 records the exact files it will name, the preferred remedy (build each cell's own
prepared artifact with the model-free `prepare-supply` step first, **assert its `output_sha256` by
hand against `ba5e1faa…` / `512583ec…` — that assertion replaces `_compare_artifact_output`, which
does not run when the tool has nothing to rebuild** — then pin it and run the tool), and the
fallback. Nothing about the factor, the comparator, the decision rule or any budget depends on which
remedy is taken.

## 6. Metrics, diagnostics and resampling

**Primary: official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded. **Guard: intent (joint scenario+action) accuracy.**

Secondaries: intent, scenario and action accuracy, official pooled span F1, per-row mean official
SLU-F1, per-row mean exact slot F1, and saves / harms / ties with the exact two-sided McNemar p.
**Projection v3 (`slurp-slu-official-projected-v3-train`) and the TRAIN symmetric sibling
(`slurp-slu-f1-normalized-v1-train`) are reported beside every official number** (owner decisions 7
and 14); owner decision 23 keeps the **official, unprojected** number the one that decides.

Mandatory diagnostics:

1. **The four flag counts per row**, read from the flight's own `saea-reviewer-slot-audit-v1`
   receipts inside the `reviewer:current-draft` rows of the `saea-node-context-policy-v1` receipt —
   `TYPE-UNSEEN`, `EMPTY-DRAFT`, `MISSING-COMMON`, `REPRESENTATION` — per contact and aggregated per
   row and per scenario, with the zeros kept (`flag_counts` always carries all four names).
2. The `applied` / `reason` split (`applied: true` versus `applied: false`, `reason:
   "draft-unparsed"`) and the `intent_in_table` share.
3. **How often a flagged row was revised, and whether the revision helped**: for every row whose
   first Reviewer contact fired at least one flag, whether the Planner issued a `REVISE`, and the
   **official-scorer matching of that row before and after** the revision (the pre-revision draft
   scored as if delivered, against the delivered answer), as saves / harms / ties on the flagged and
   the unflagged subsets, beside cell B7r's own revision rate on the same rows.
4. The same before/after table broken down **per flag**, so a flag that never changes an answer is
   visible as such.
5. **Reviewer parse rate** under `rails.review_findings.parse_review_findings` (cell B7r's
   constrained `saea-review-findings-v1` contract) **with the block and without it** — B8b against
   B7r's own sealed rate on the same 1,080 rows, and against the sealed anchor's 2,167-of-2,167
   unparsed baseline.
6. The native task-contract tool-call count against cell B7r's (the Reviewer's first turn is
   required by its instruction to call that tool).
7. The `saea-node-context-policy-v1` aggregate per boundary, with **every** boundary other than
   `reviewer:current-draft` required to carry **no** `slot_audit` block and its pre-E12 fields.
8. **The count of rows whose `terminal_disposition.reason` is `"finite_completion"`** (section 3.1),
   the affected sample ids, the delivered-draft versus abstention split, and — only if the count is
   non-zero — the primary metric recomputed with those rows excluded, **beside** the registered
   all-rows number. No row filtering.
9. The per-scenario intent and SLU tables over all 18 scenarios, in **both** the natural-mixture and
   the equal-scenario weighting.
10. **Net harmed rows per scenario, any scenario of five or more flagged** (owner decision 17) — a
    diagnostic the verdict must carry, not an additional gate.
11. The per-contact prompt-token delta against cell B7r from this cell's own sealed native
    contact-fit receipts, and the realized `block_chars` distribution, against section 7's bound.

**Resampling:** paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for
the decision clauses and CI90 for diagnostics, both as percentile pairs of the same retained
replicate sequence. Sensitivity: paired scenario-stratified row bootstrap, same draws and seed.
Every table in both weightings. Unlike cell B8a, **both sides of this contrast are decoded runs**, so
the paired interval carries real decoding noise; the own-null margins are the calibration for
exactly that.

`delta = cell B8b minus cell B7r`, in percentage points; negative means the arm is worse.

### Decision rule, fixed here before any number is read

Own-null margins, the TRAIN A own null measured by cell B0r on this exact roster and geometry:
**h_SLU = 1.1218 pp**, **h_intent = 1.0051 pp** at CI95 (0.9420 / 0.8505 at CI90).

> **HARMFUL is read first** (owner decision 25, Method B): only by a **measured loss** — a point
> estimate of official pooled SLU or of intent below **-h** (-1.1218 / -1.0051), or a CI95 **upper**
> bound below zero. An interval that straddles zero with the point estimate inside the margin is
> **not** harmful.
>
> **ADMITTED** if and only if all four hold against **cell B7r's sealed score artifact**:
> 1. the CI95 **lower** bound of the paired **official pooled SLU-F1** delta is **greater than 0**;
> 2. **intent is non-inferior** at the own-null margin — its CI95 lower bound exceeds **-1.0051**;
> 3. the **TRAIN symmetric scorer** `slurp-slu-f1-normalized-v1-train` **agrees in sign** with the
>    unprojected primary; and
> 4. **no scenario loses intent beyond the null band** — no scenario's paired intent CI95 **upper**
>    bound lies below zero.
>
> **NEUTRAL** otherwise, with "non-inferiority not proven" stated in those words where an interval
> straddles zero.
>
> **Read exactly once.** No repeat-to-pass, no re-scoring, no second estimator, no re-weighting
> after seeing a number.

**The symmetric clause is evaluable.** The TRAIN sibling of `slurp-slu-f1-normalized-v1` is
registered (owner decision 14, 2026-09-17, and used by the B4b, B1-twin and B5e reads), so clause 3
applies as written and the B7r-era conditional substitution does not. If the sibling were
unavailable at read time the clause would be NOT EVALUABLE, projection v3 would be the agreement
reading, and the substitution would be recorded as a deviation.

**NEUTRAL and the default plan.** Design section 15 resolution 5 fixes that a NEUTRAL node-context
cell enters the SLURP default plan **only if it lowers cost**. A NEUTRAL B8b **does not**: the block
adds context on every Reviewer contact that receives a parseable draft and removes nothing. An
ADMITTED B8b enters the plan on its measured gain, as any admitted module does, and from that moment
every later official SLURP number this program reports is produced by a system that contains the
block. A HARMFUL B8b enters no plan and its successor does not fly on its base (owner decision 15).

**Not a bar attempt.** Cell B8b is a one-factor module admission. The verdict states the official
pooled SLU the arm reaches and whether it clears 64.00 as a **fact**, never as a claim, and
"replicated on the same roster" is not claimed by anything here.

> **STOP condition, before any table of this read is looked at.** (1) Cell B7r's sealed comparator
> must reproduce its own registered official aggregates to the hundredth of a point, from its sealed
> score artifact, with its three `PENDING_B7R_SEAL` hashes filled in and verified by hashing the
> files. (2) Every row must be accounted for — 1,080 in, 1,080 out, no row dropped and no
> `sample_id` invented, on both sides. (3) The roster, split identity and scenario / speaker strata
> must be identical on both sides. If any clause fails, the read stops and the discrepancy is
> reported before anything else happens.

## 7. Prompt fit

Slot **24,576** tokens; decision **ALLOW** for every phase of both cells.

The bound is **cell B7r's own registered per-contact fit table** (its preregistration section 8),
plus this cell's own measured audit-block increment **at the Reviewer phase and nowhere else**,
because the block renders at `reviewer:current-draft` and at no other boundary.

**The increment was measured in this registration, model-free and with zero contacts**, by driving
the production `rails.node_context_policy` renderer over the **real committed table** and the **real
committed template**, for all 60 intents and three draft shapes:

| draft shape | chars (min / median / max) | words (min / median / max) |
| --- | --- | --- |
| one entity type, clean filler | 372 / 466 / 753 | 62 / 79 / 131 |
| no entity at all | 372 / 606 / 992 | 62 / 101 / 170 |
| adversarial: one unattested type plus a `date` and a `time` filler that both break the convention | 943 / 1,106 / **1,373** | 156 / 183 / **231** |

Each additional unattested draft type adds **+87 characters / +12 words** (measured on `calendar_set`
at 1, 2, 3 and 5 unattested types); the `TYPE-UNSEEN` line is the only part of the block a draft can
multiply. The profile lists 0 / 2 / 8 types per intent (min / median / max), 165 rows in total.

**Registered increment: 231 words → 301 proxy tokens** at the repository's stated proxy
(`analysis.slurp_slot_vocabulary.TOKEN_PROXY_FACTOR` = 1.3), applied to the Reviewer phase only:

| phase | B7r max bound | B8b max bound | min margin |
| --- | ---: | ---: | ---: |
| perception | 4,270 | 4,270 | 20,306 |
| solver | 13,544 | 13,544 | 11,032 |
| reviewer | 15,447 | **15,748** | **8,828** |
| planner | 15,593 | 15,593 | 8,983 |

Item E12 reports 687–787 characters / roughly 170–200 tokens; **this registration's own measurement
is wider and is the number registered here**, because it sweeps all 60 intents and an adversarial
draft rather than a sample.

**This is a static bound on the audit block, not on what the Reviewer generates** — cell B7r's own
section 8 already records that its Reviewer bound is static rather than live. The authority in
flight is `core.preparation_fit.build_native_contact_fit_gate`, which fits every realized immutable
request against the resident tokenizer before it is transmitted and stops the flight rather than
truncating. It is not a capacity guarantee for every branch.

## 8. Budgets and cost reporting

Cell B7r's ceilings, **unchanged**, because the block adds no contact of any kind:

| | generation | FIT endpoints | speech seconds | GPU hours | task-contract calls | official scores |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **arm** | 11,880 | 47,520 | 33,930 | 12.0 | 6,480 | 1 |
| **smoke** | 44 | 176 | 117 | 1.0 | 24 | 0 |

ASR, encoder and paid-API calls are zero in both. 11,880 is the exact eleven-contact program maximum
(1,080 × 11), not an estimate and not a target; the sealed anchor realized 5,417 contacts (5.016 per
row) and 3.388 GPU hours at this geometry. Ceilings are run-cumulative across every attempt of a run
id, and unused budget is never attempt authority.

Every verdict reports: actual generation contacts against B7r's realized count and the ceiling;
contacts per row (this cell adds none); actual repeated speech seconds against the anchor's realized
15,459.76; actual FIT endpoints; actual native task-contract calls; GPU hours read from the serving
monitor over the lease window, never a wall-clock guess; mean latency, slot occupancy and duty
cycle; and the prompt-token delta against B7r beside the registered +301 proxy-token increment.

## 9. The four-row smoke — structural acceptance only

The smoke proves that the block reaches the Reviewer **in flight** and reaches nothing else. Accept
only if all six hold:

1. **Contacts.** Perception, Solver, Reviewer and Planner contacts, about five per row plus any
   revision the Planner issues; **no row exceeds 11**.
2. **The receipt on every Reviewer contact of 4 of 4 rows.** Each Reviewer contact's
   `reviewer:current-draft` row carries a `slot_audit` block with `schema`
   `saea-reviewer-slot-audit-v1`, `view_id` `slot-audit-v1`, `release_sha256`
   `eaa2dd0db4d089f9bf1687d353f129ffcf062766f84150b0b93463617fdee7f9`, `snapshot_sha256`
   `0cc3f96c98addad37fb564483f051dbe1a11145ac554a85918312c388573406c`, `table_content_hash`
   `d4cd4bf3fd9bf44725f860257800c415164faf14a8dcce19bd3ab2339fee01de`, `template_id`
   `probes/ncp_slurp_slot_audit_reviewer_v1.txt`, `template_sha256`
   `88cc927d901a45ac2496f92453521184cb5b8d39cbf98aa881872b9116d24d0a`, the three declared thresholds
   and `flag_counts` carrying all four flag names including the zeros. A contact whose draft did not
   parse carries `applied: false`, `reason: "draft-unparsed"` and no block — acceptable on that
   contact, but **at least one Reviewer contact of every row must carry `applied: true`**, or the
   smoke has not shown the block reaching the model.
3. **The block is an addition and reaches nothing else.** On every contact that rendered a block,
   the last `block_chars` characters of the rendered `reviewer:current-draft` text hash to
   `block_sha256`, and the text before them (minus the one joining newline) is the boundary's own L1
   rendering. **No other boundary row carries a `slot_audit` block** and every other boundary row
   keeps its pre-E12 fields. The compilation record's `template_sha256s` carries the three assets the
   block was composed from.
4. **The non-Reviewer channel is cell B7r's.** The **Perception request** of each of the four rows is
   **byte-identical** to cell B7r's own sealed four-row smoke
   (`SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-SMOKE-4-V1`) on 4 of 4 rows — it precedes every
   generation, so nothing else can explain a difference — and the Solver and Planner requests are
   byte-identical wherever their upstream model responses are. Greedy decoding at temperature 0 is
   not bitwise reproducible across batch compositions and the Reviewer's own text legitimately
   changes, so a differing Solver or Planner request whose upstream responses differ is **not** a
   failure; a differing **Perception** request **is**.
5. **Fit and seal.** One `*.request-fit.json` per realized contact with `every_request_fits = true`
   and every required-token count below 24,576; the worker prints a seal; the manifest seals clean;
   the tree is still clean.
6. **The finite path is reported, not required.** Any row whose `terminal_disposition.reason` is
   `"finite_completion"` is **retained**, not an error, and the smoke report states the count and
   which rows. Four rows are very unlikely to hit the 512-token cap, so the expected count is zero; a
   non-zero count is acceptable and is itself useful evidence that the retained path works in flight.
   What is **not** acceptable is an abort on `finish_reason` `length`: that would mean the declared
   policy did not reach the runtime.

**What the four rows will probably not show, stated in advance.** Which flags fire on these four rows
is neither predicted nor required. The flag logic is proved by
`tests/unit/test_slurp_slot_audit_view.py` and `tests/unit/test_reviewer_slot_audit_block.py` over
the real table, not by four rows. A row on which no flag fires is equally acceptable provided the six
criteria hold.

No scorer, no answer, reference or quality interpretation, and no task-quality claim.

## 10. Failure rule

The first failure stops the flight and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. **At most one
root-diagnosed recovery re-registration per flight**; a second failure closes that flight and the fix
must be proven on a four-row dry run before the block is proposed again. A failed four-row smoke
stops cell B8b until the fix is proven on that same four-row roster. One experiment in flight at a
time.

**Resume-recovery clause (owner decision 22 of 2026-09-18).** If an attempt dies of an
**infrastructure** failure with code and request bytes unchanged — never a harness or config defect —
the one allowed recovery may be a **resume-recovery** under item E10 instead of a re-fly: every
complete row of the aborted attempt is kept without selection, every partial or unstarted row is
flown under the same run id, and the merged manifest declares the predecessor attempt with its trace
hash, kept-row list and that list's hash. It changes no question, roster, factor, comparator,
decision rule or cap, and the run-cumulative budget must be re-checked because a resumed attempt and
its predecessor share one run id.

A completion that hits the 512-token cap is **not** a failure in this cell: section 3.1's declared
policy retains the row and the count is a diagnostic.

## 11. What is NOT claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and every claim of this cell stops at it. Fold B, DEV-1000 and the test split stay
  untouched and unread.
- **No gold of an evaluated row enters the block**, at build time or at runtime. The only text of an
  evaluated row that can appear is the draft's own entity **type** names, which the consumer already
  holds in the draft block immediately above.
- **Nothing about cell B7r's own verdict.** B7r has not flown; if B7r is HARMFUL this cell does not
  fly, and no number in this document is evidence for or against B7r.
- **No claim that the Reviewer *acts* on the block.** The cell measures whether the loop's outcome
  moves; whether the Reviewer's criticism changes because of the audit, or for some other reason, is
  not separable here.
- **No attribution to one flag.** The four move together; the per-flag before/after table is a
  diagnostic, not four separate admissions.
- **No claim about the A3 audit's own counts.** They bound what the block can touch; they are never
  a predicted gain.
- **No claim that a larger or differently thresholded table would do better.** The thresholds are the
  registered defaults and are not tuned here; changing one is a new cell.
- **No claim that the retained finite-completion rows are comparable to the comparator's** (section
  3.1).
- **A structural smoke result is never a quality result**, and this is not a bar attempt.

## 12. Pre-contact evidence on file

In this readiness directory (`docs/readiness/2026-09-19-slurp-b8b-reviewer-audit-v1/`), all
model-free:

| file | what it carries |
| --- | --- |
| `README.md` | the launch runbook: mint the receipt, re-pin and flip, commit, fly the smoke, fly the arm, run the read |
| `protocol-registered-v1.json` | the frozen protocol: purpose, cells, the one factor and the one non-factor key, the analysis and its boundary, the harness-admission entry form, comparators, metrics, diagnostics, resampling, decision rule, smoke acceptance, prompt fit, budgets, failure policy, what is not claimed |
| `generation-plan-v1.json`, `generation-plan-registered-v1.json` | the registered generation plan of the 1,080-row arm |
| `fit-plan-v1.json`, `fit-plan-registered-v1.json` | the registered native contact-fit plan of the arm |
| `smoke-generation-plan-v1.json`, `smoke-generation-plan-registered-v1.json` | the registered generation plan of the four-row smoke |
| `smoke-fit-plan-v1.json`, `smoke-fit-plan-registered-v1.json` | the registered native contact-fit plan of the smoke |
| `analysis-recipe-v1.json` | the paired read: arms, estimators, seed, draws, intervals, contrasts, own-null margins, STOP condition, metrics, required diagnostics and tables, output root |

Plus the committed campaign plan
`configs/campaign/slurp-native-ncp-l1-reviewer-audit-anchor-train-fold-a-v1.json` (one cell).

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration
agent that has not committed cannot run it without either failing on its own uncommitted files or
writing an attempt reservation it has no authority to make. The composed and protocol hashes were
computed directly through `core.config.compose` / `core.config.protocol_hash` — the same two
functions `check` itself uses — and **the method was verified on this tree**: composing cell B7r's
own four fragments reproduces its registered composed
`c17c661c0514951ec1ad5ec683f1e236ce269b9eceedf4bf376a9cf87fe03eeb` / protocol
`2d3b2a864a9528b2c69f58e58ff195b69bb8811538b880418dec8175c4e30257`, and its smoke's registered
`c4306c4c7d9f36446715a32daa360455cc7e4f0b94e18b22a638107851c886c4` /
`28af23a50b1dcf1f8f8469c39f377d657a8810c7aeefa9d94ed5bffd2f50ed29`.

**`core.flight.cli wire-check` remains unavailable** for any native-episode cell, as it was for the
anchor, B0, B0r, B1, the B4 cells, B5e, B7a and B7r: `FlightRuntime._dispatch_phase_program` refuses
a native episode whose transport is not the real shared speech renderer, and `wire_check` installs a
text transport double. The substitute is
`tests/unit/test_native_episode_runner_reviewer_audit.py`, which runs the real episode through the
production render path and compares every rendered request with and without the block. The second
declared key is outside that comparison by construction (section 3.1): it renders no request byte.

**These hashes describe the fragments exactly as committed**: readiness `held`, the inherited
`preparation` requirement pinned, **no `decision` requirement**. `compose()` hashes the whole merged
fragment set, so adding the decision requirement, flipping readiness and re-pinning the prepared
artifact each change the composed hash and therefore the protocol hash. The re-pin tool does all
three in one cycle and rewrites every dependent hash; nothing here is edited by hand.

## 13. What this package does not authorise

No readiness flip, no model contact, no default-plan edit and no harness-admission entry. The
admission entry for the module "Reviewer slot-audit context block" is written from the sealed
verdict, never from this registration; the protocol document records the expected entry shape so the
coordinator can check it against the switch rule before writing it. Neither cell opens before cell
B7r seals, and the arm does not open before B7r is read not HARMFUL.
