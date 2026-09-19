# Cell B1r: the request-identical replicate of the exemplar-supply cell (module M1)

Status: **REGISTERED BEFORE CONTACT.** Author: the B1r registration agent, worktree
`/home/chao/saea-worktrees/fable-b1r`, branch `fable/b1r`, base commit `0989edb1` (which carries
harness item E18, merged at `0989edb1`).

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried; no run directory, attempt
record or sealed artifact was written, moved or renamed; `locks/flight.lock` was never held; no
scheduled task was touched. The only writes outside the repository are this cell's own two
**model-free** prepared Perception supplies, under this cell's own run ids, and the root decision
receipt under `coordination/`.

## 1. Why this cell exists

Module **M1** — the speech-keyed annotated TRAIN exemplar supply to the Solver, plain top-k = 20 —
is **ADMITTED but PROVISIONAL** in `docs/receipts/harness-admission.json` (row
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`). Its `provisional.state` is
`UNMET` and its `requirement` reads, verbatim:

> replicate on the same roster before the default plan carries the store: the B5e / B5er
> combination pair (owner decision 19 of 2026-09-18) both showing the module's contribution within
> the own null, or **a request-identical replicate of this cell (about 3.7 GPU hours)**; a second
> entry records the replication and this entry stays

The B5e leg did not discharge it. Cell B5e (`docs/results`, 2026-09-18) missed the bar by 1.66 SLU
and its combination contrast against cell B1 was +1.20 [−0.11, +2.48] — a reading too wide to
license anything, because the interval was drawn under a request-identical null that cell B1 had
never measured. So the obligation stayed `UNMET`, and **module M1 has therefore never been allowed
into the SLURP default plan**, despite carrying the largest single-cell gain the v2 program has
recorded (+12.61 pp official pooled SLU-F1).

**Owner decision 37 of 2026-09-19** closed that: asked whether the replicate should fly before the
base lock, the owner answered *"follow your recommendation"* — a request-identical replicate of cell
B1 flies before the lock closes, and **module M1 enters the default plan only if it replicates**.
This package is that cell.

It is also the only way to get the second thing the program now needs. **Owner decision 38** fixed
the margin regime: *a contrast involving a configuration uses the margins of that configuration's
own request-identical replicate*, with cell B0r's own null (h_SLU 1.1218, h_intent 1.0051) as the
registered fallback where none exists. The exemplar-supplied configuration has no such replicate, so
every contrast against an exemplar-supplied arm — B5e's included — has been borrowing a **review-off**
configuration's half-widths. This cell measures the right ones.

## 2. The cell, and why it is a replicate by construction

| item | value |
| --- | --- |
| arm cell / experiment fragment | `slurp-native-exemplars-k20-anchor-replicate-v1` |
| arm baseline fragment | `slurp-native-anchor-exemplars-k20-replicate-v1` |
| generation run / attempt | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1` / `attempt-slurp-native-exemplars-k20-anchor-replicate-train-fold-a-generation-v1` |
| native fit run / attempt | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-FIT-V1` / `attempt-slurp-native-exemplars-k20-anchor-replicate-train-fold-a-fit-v1` |
| smoke cell / experiment fragment | `slurp-native-exemplars-k20-anchor-replicate-smoke-4-v1` |
| smoke baseline fragment | `slurp-native-anchor-exemplars-k20-replicate-smoke-4-v1` |
| smoke generation run / attempt | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1` / `attempt-slurp-native-exemplars-k20-anchor-replicate-smoke-4-generation-v1` |
| smoke native fit run / attempt | `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-FIT-V1` / `attempt-slurp-native-exemplars-k20-anchor-replicate-smoke-4-fit-v1` |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` (**cell B1's**) |
| dataset fragment | `slurp-speech-native-evo-fold-a-1080` (**cell B1's**) |
| campaign plan | `configs/campaign/slurp-native-exemplars-k20-anchor-replicate-v1.json` |
| composed config / protocol (arm, **pre-flip**) | `130a72f658a3d30d549d06745db4ef7cd1bacafbb9dc378f81be2246fe776150` / `9c17b1723917f8ea67b8b454967d4ef15e8cd7b6fbb45d149e60a537723a1cd7` |
| composed config / protocol (smoke, **pre-flip**) | `188ac3fc02b1b66cda23c2a88ed1b0791284698f59f5611044ab387a38076d68` / `47a32c78a98698789b2ccd9e9377194b30f54f10edf2e40bb5693283a58b2714` |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held` with this cell's own `preparation` requirement pinned and **no decision requirement** |
| decision | id `slurp-b1-replicate-admission-v1`, receipt `coordination/slurp-b1-replicate-v1/root-admission-v1.json` |

**The composed and protocol hashes above are the pre-flip values** of the five fragments exactly as
committed. `compose()` hashes the complete merged fragment set, so adding the decision requirement
and flipping readiness each change both. The re-pin tool recomputes them and rewrites every document
that quotes them; nobody edits them by hand. **The method was verified on this tree against a sealed,
registered pair**: the same `core.config.compose` / `core.config.protocol_hash` call reproduces cell
B1's own registered `114b7917…` / `c66d507d…`, exactly the values
`docs/results/2026-09-17-slurp-b1-exemplars-k20-verdict.md` records for the sealed arm.

## 3. The one factor, and what it is not

**There is no factor.** Every model-facing key of
`configs/baseline/slurp-native-anchor-exemplars-k20-replicate-v1.json` is
`configs/baseline/slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2.json`'s, byte for byte:
the `train-exemplars` store block (release `171aa4a8…`, snapshot `4c498dc0…`, `phase_supply.solver`
keyed by the row's own sealed Fold A speech vector in the `content` dimension, k = 20,
`saea-fuse-supplyfilter-v1` at m = c = top_l = 20, `saea-rank-wcos-prior-agree-v1` with w_cos = 1
and tau 0.0), both other stores, the phase program, the phase material, the phase tools, the policy,
the scorers, the serving geometry, the promoted EVO-FOLDS-V2 packets and every instruction template.
The committed proof is `tests/unit/test_b1_replicate_config.py`.

**The factor this cell measures is batch composition under greedy decoding, and nothing else.**
`llama-server` at temperature 0 does not return bytes independent of how requests batch across
slots, so a cell that changes nothing at all still produces a non-zero delta. Earnings-21 measured
its own version of that on 1,593 windows; SLURP measured the **review-off** version on this roster
(cell B0r) and the **slot-store v2** version on it (cell B4b-rep, h_SLU 1.3222 / h_intent 1.0682).
**The exemplar-supplied five-contact configuration has never had that measurement**, and until it
does, module M1's admission rests on a half-width it did not measure.

Not the media, not the prompt, not the knowledge, not the role graph, not the geometry, not the
population.

### 3.1 What moves, named rather than discovered later

Eight fields move, and none of them is model-facing.

| field | why it must move |
| --- | --- |
| `cells[].run_id`, `cells[].attempt_id` | a replicate is a new run; reusing cell B1's ids would collide with a sealed, consumed row |
| `native_contact_fit.run_id` / `.attempt_id` | `core.preparation_fit.build_native_contact_fit_gate` refuses a request-fit receipt path that already exists, and every one of cell B1's exists |
| `speech_feature_key_representation_id`, `speech_feature_matcher_policy_id` | provenance-only ORG/CONTROL identity strings; **absent from every rendered request byte**, which cell B1's own preregistration proved by scanning every envelope |
| `prepared_phase_supply` | item E16: a prepared artifact is evidence only for the implementation that produced it, so this cell builds and pins its own (section 3.2) |
| `what_this_is`, the experiment's `purpose`, `failure_policy`, `readiness.reason`, `date`, `fragment_kind` | free English and registration bookkeeping |

**And one declared key that cell B1 did not carry.**
`native_episode.finite_completion_policy = "deliver-latest-or-abstain"` is required of every live
SLURP native cell by `scripts/checks/finite_completion_policy_check.py` (item E13). **It is not a
factor.** It renders **no request byte** and only decides whether a finite completion aborts the
flight or the row is **retained** with a `terminal_disposition` reason `finite_completion`. Cell B1
flew without it, and `docs/receipts/slurp-finite-completion-exposure-v1.json` is the registered
receipt proving **zero finite completions** on the sealed native arms, so the comparator side is
provably unaffected. `tests/unit/test_b1_replicate_config.py` proves the byte claim on the
production render path: driven through the real OpenJiuwen role graph over the shared fake
transport, **every one of a row's five contacts is byte-identical** between cell B1's parsed policy
and cell B1r's.

### 3.2 The prepared Perception supply — this cell's own, and identical where it counts

Item E16 makes a prepared artifact evidence only for the implementation that produced it, and
`core.flight.repin.assert_no_residue` refuses an inherited pin. So both cells built their own,
**model-free**, under their own run ids, in this registration:

| cell | artifact | SHA-256 | Perception `output` SHA-256 |
| --- | --- | --- | --- |
| arm | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1/phase-supply-v1.json` | `7f2c82d982df64641b3b0c7b2a06650a6fd2248e8450fa8ee7778f568b0326ef` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| smoke | `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1/phase-supply-v1.json` | `78aa0622394f37287878116beab4b229dd2c5afbb28b08d8210e798e21ed0f83` | `512583ec2c684a2e285bfafea3f4101033a2a1d413fad39c8cfd2b74fbff5733` |

**Both `output` blocks were asserted by hand in this registration against the sealed cell B1
preparation's own `output`, and both matched exactly** — `ba5e1faa…` on **1,080 of 1,080** rows
against `prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2/phase-supply-v2.json`,
and `512583ec…` on **4 of 4** rows against
`prepared/SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-SMOKE-4-RECOVERY-V2/phase-supply-v1.json`. The arm
value is also the sealed anchor preparation's own output, which is why the knowledge channel is
provably unmoved. That hand assertion replaces `_compare_artifact_output`, which does not run when
there is nothing to rebuild. **`--allow-output-change` must never be passed**: an output that moved
would mean the knowledge channel moved, and this would no longer be a replicate.

### 3.3 This cell keeps PER-ROLE tool-schema rendering, deliberately

`native_episode.tool_schema_rendering` (item E17, merged at `d6fade1e`) is **not armed**. Request
identity with cell B1 requires the sealed anchor's **per-role** rendering, and arming the constant
rendering would add a `tools` array to the Perception, Solver and Planner requests — which is
exactly the byte change efficiency cell EFF-1 exists to measure. **Cell B1r is therefore a per-role
cell.** Its result is unaffected by EFF-1's outcome, whichever way that cell falls; and if EFF-1 is
NEUTRAL and the constant rendering enters the SLURP default plan, this cell's numbers remain the
per-role numbers and the verdict says so, in the same way the B8a package's clause requires a later
cell registered against a sealed per-role arm to declare it.

### 3.4 What cannot be held fixed

Two passes of the same bytes at temperature 0 are not bit-identical on this server (the repository's
own finding: greedy decoding is not bitwise reproducible across batch compositions), and the wall
clock, the slot assignment and the host's other work are not under this cell's control. That is the
point of the measurement, not a defect in it. Nothing else is permitted to vary.

## 4. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondary gate: intent (joint scenario+action) accuracy. Agreement reading: **projection v3**
(`slurp-slu-official-projected-v3-train`), owner decision 7, reported beside every official number,
with the **OFFICIAL unprojected number deciding** (owner decision 23). The **TRAIN symmetric**
sibling `slurp-slu-f1-normalized-v1-train` is reported beside every official number (owner decision
14); it is never a gate.

Secondaries: scenario accuracy, action accuracy, official pooled span F1, per-row mean official
SLU-F1, per-row mean exact slot F1, saves/harms/ties with the exact two-sided McNemar p, and the
count of rows whose delivered (scenario, action) pair differs between the two passes.

**Two signed contrasts.** The **clauses** use `delta = B1r minus the sealed anchor`; the **own null**
uses `delta = B1r minus cell B1`. Both in percentage points, negative meaning worse.

## 5. Resampling, tables and the STOP condition

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for the clauses and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence — cell B1's
own estimator settings, unchanged. Sensitivity: paired scenario-stratified row bootstrap, same draws
and seed. Speaker clusters (125) come from the released roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`). Every verdict carries
the 18-scenario table in both the natural-mixture and the equal-scenario weighting.

**STOP condition.** Before any table of this cell is read, the recomputed `(B1 minus anchor)`
contrast must reproduce the first pass's registered CI95 lower bounds **+10.54** (pooled SLU) and
**+0.74** (intent) to the two decimals the verdict publishes, and both comparators must reproduce
their registered official and projection-v3 aggregates (anchor 48.53 / 77.96 / 84.81 / 79.26 / 29.50
and 51.99 / 79.35; cell B1 61.14 / 80.19 / 86.39 / 81.39 / 48.43 and 62.67 / 81.76). If they do not,
the read stops: the same sealed bytes under the same estimator and seed cannot give two answers.

## 6. Decision rule (fixed here, before the replicate is read)

> **Replication of module M1 (the speech-keyed exemplar supply, k = 20) on TRAIN Fold A.**
> Let R be this replicate, B1 the first pass and A the sealed dual-store anchor, all on the same
> 1,080 rows with the same paired whole-speaker cluster bootstrap (10,000 draws, seed 20260915).
>
> **Clause 1 — the replication clause.** R is **REPLICATED** if and only if all three of the
> clauses cell B1 passed hold for R, applied unchanged: (a) the CI95 lower bound of the official
> pooled SLU micro F1 delta `(R − A)` is **greater than 0**; (b) intent is **non-inferior within
> 1.0051 pp** — the CI95 lower bound of the intent delta `(R − A)` exceeds −1.0051; (c) the
> **projection-v3** reading of the pooled SLU delta **agrees in sign** with the unprojected one.
> Read **exactly once**, from the single official score of the complete manifest.
>
> **Clause 2 — the own null of the admitted configuration.** `h_SLU_M1` and `h_intent_M1` are the
> CI95 half-widths of `(R − B1)` for pooled SLU and intent respectively, on the same rows at the
> same interval level. They are **outputs of this cell, not inputs**: no value for either is
> written anywhere in this registration and neither may be chosen after the fact. They are reported
> beside the B0r-measured **1.1218** and **1.0051**, which are the review-off configuration's
> half-widths cell B1 had to borrow, and beside the B4b-rep-measured **1.3222** and **1.0682**.
>
> **Clause 3 — the consequence.** On **REPLICATED**, the provisional obligation of the M1
> harness-admission entry is **MET**: a second entry records the replication, the first entry stays
> (as the KC-E1f v1/v2 and M4b pairs do), and the **SLURP default plan may carry the exemplar
> supply** — specifically the whole `knowledge_stores.train-exemplars` block the M1 entry's
> `switch.on` records, with release `171aa4a8…`, snapshot `4c498dc0…`, `phase_supply.solver` at
> k = 20 with `saea-fuse-supplyfilter-v1` (m = c = top_l = 20), `saea-rank-wcos-prior-agree-v1`
> (w_cos = 1, w_prior = 0, w_agree = 0), `tau` 0.0 and `store_role` `train-exemplars`. If clause 1
> fails, the entry **stays provisional with its obligation UNMET**, module M1 stays **out** of the
> SLURP default plan, and **the owner is told**. **No third pass** of this configuration is
> registered or authorized either way.
>
> **Clause 4 — mandatory tables.** The full 18-scenario table in both the natural-mixture and the
> equal-scenario weighting, plus the owner-decision-17 diagnostic — **net harmed rows per scenario,
> with any scenario at five or more flagged** — for both the `(R − A)` and the `(R − B1)` contrasts.
>
> **Clause 5 — the symmetric scorer.** The TRAIN sibling registered on 2026-09-17 is reported
> beside every official number. It is never a gate here.
>
> Diagnostics reported beside the rule and never used for it: the `(R − B1)` point estimates,
> saves/harms/ties with the exact two-sided McNemar p, the per-type slot decomposition recomputed on
> R's own sealed outputs, cell B1's own per-scenario intent band, row agreement between the two
> passes, and R's contacts, GPU hours and duty cycle.

Four properties of that rule are deliberate and are recorded here so no later reader has to infer
them.

1. **Clause 1 is cell B1's rule, not a new one.** A replication that moved the bar would not be a
   replication. The three conjuncts, the −1.0051 margin, the estimator, the draws and the seed are
   copied from `docs/readiness/2026-09-17-slurp-b1-exemplars-k20-anchor-v2-preregistration.md`
   section 7.
2. **Clause 1 does not restate cell B1's twin clause.** Cell B1's ADMITTED rule required the CI95
   lower bound above zero *versus the sealed anchor AND versus the twin*. Owner decision 37 asked
   for a **request-identical replicate**, and no derangement twin is re-flown here: the twin is an
   attribution control, not a replicate. Cell B1's twin decomposition (+7.83 pp arm-minus-twin,
   +4.77 pp twin-minus-anchor with nil intent) is **quoted** in the verdict as an established fact
   and is **not re-measured**. This is a deliberate, owner-directed scoping of the gate, stated here
   so it is not read later as a silent drop.
3. **The half-widths are outputs.** No value of `h_SLU_M1` or `h_intent_M1` appears in this
   document. The 1.1218 / 1.0051 and 1.3222 / 1.0682 quoted above are other configurations'
   measurements, quoted only to say what this cell replaces; they gate nothing here.
4. **One replicate, not a family.** A third pass of this configuration would be repeat-to-pass and
   is neither registered nor authorized, whichever way clause 1 falls.

## 7. Cost reporting (mandatory in the verdict)

- actual generation contacts, against cell B1's realized **5,425** (5.023 per row) and the anchor's
  5,417 (5.016); the ceiling is 11 per row, **11,880** per cell;
- contacts per row;
- actual repeated speech seconds, against cell B1's realized **15,494.60** and the ceiling 33,930;
- actual FIT endpoints, 4 per realized contact, against cell B1's **21,700** and the ceiling 47,520;
- actual native task-contract tool calls, against cell B1's **1,084** and the ceiling 6,480;
- GPU hours (monitor active seconds), against cell B1's **3.6819** and the ceiling 12.0;
- prompt and completion tokens against cell B1's 49,388,949 / 255,524; slot occupancy, utilisation
  and parked share against cell B1's 0.877 / 91.01 % / 0.045 (owner decision 41);
- the one official complete scoring job and its seconds.

Ceilings are bounds, never targets, and unused budget is not attempt authority.

## 8. Prompt fit

Cell B1 realized `every_request_fits = true` with a minimum margin of **8,600 tokens** in the
`reviewer` phase against the 24,576-token slot, and its widest realized request needed **15,976**
tokens. This cell renders the same bytes, so the same bound holds; `native_contact_fit` fits every
realized request in flight at the unchanged 47,520-endpoint ceiling, and any request that did not
fit would stop the flight rather than be truncated.

## 9. The four-row smoke

A four-row standalone-worker form smoke (`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-SMOKE-4-V1`)
seals before the arm opens. It is **structural only** and is never scored: the eleven-contact anchor
role graph, the `train-exemplars` typed content blocks present in the Solver request, one native
contact fit receipt per realized contact, any retained `finite_completion` row reported rather than
treated as an error, the per-role authority refusals reported, and a clean seal. It flies the same
four already-exposed TRAIN A engineering rows every four-row form smoke of this roster flies, and
they are members of the arm's 1,080-row roster.

It is registered even though the form is already proved three times over — because the arm's own
budget must never be charged smoke contacts, and because this cell's run ids, fit identities and
prepared pins have never been exercised end to end.

## 10. Containment

Discovery only. TRAIN Fold A's 1,080 rows are already exposed by the sealed dual-store anchor, the
released direct anchor, cells B0 and B0r, cell B1's own recovery arm and its derangement twin, cells
B4b, B4b-rep and B5e, and cells B7a, B7r, B8b and EFF-1. **This cell adds no new population and reads
no gold, reference or new knowledge.** Fold B, DEV-1000 and the test split stay untouched and unread.
No ASR, encoder or paid-API contact; paid API spend stays at zero.

## 11. Failure rule

Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster,
role-graph, prompt, knowledge, geometry or cap change. **At most one root-diagnosed recovery
re-registration** for this run; a second failure **closes cell B1r** — no third registration — and
the fix must be proven on a four-row dry run before another mechanism is admitted.

**Resume-recovery clause (owner decision 22 of 2026-09-18).** If the abort is an **infrastructure**
failure with code and request bytes unchanged, the one recovery takes the resume-recovery form of
harness item E10: the same run id, a fresh attempt id, a `resume_from` declaration naming the
predecessor attempt and its trace SHA-256, every COMPLETE row kept without selection under invariant
I7r, every partial or unstarted row re-flown in full, no change to the question, roster, comparator,
decision rule or caps, and the run-cumulative budget re-checked. Otherwise the one recovery is a full
re-fly. **A partial manifest is never scored and never read.** One experiment in flight at a time.

## 12. What is NOT claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is a discovery
  roster; meeting clause 1 admits module M1 into the SLURP default plan and nothing more. Stage-3
  claims belong to a separately admitted paper repository.
- **No twin claim.** No derangement twin is re-flown, and cell B1's twin decomposition is quoted,
  not re-measured. Nothing here revises the attribution of cell B1's gain between exemplar presence
  and the speech key.
- **No claim about k, the fuse policy, the rank weights, the exemplar pool or the derangement seed**
  beyond the flown values; no sweep is run.
- **No geometry claim**, and **no claim about constant tool-schema rendering**, which this cell
  deliberately does not arm.
- **No claim that this cell's own null transfers to any other configuration.** `h_SLU_M1` and
  `h_intent_M1` are the exemplar-supplied five-contact configuration's half-widths on this roster at
  this geometry, and nothing more.
- **No sub-population claim**, and no reading of any partial manifest.
- **A structural smoke result is never a quality result.**
- Nothing about any in-flight cell, and nothing about Earnings or Audio2Tool.

## 13. Analysis recipe

`docs/readiness/2026-09-19-slurp-b1-replicate-v1/analysis-recipe-v1.json`, SHA-256
`88f085ac4ea3888f2f4e7632637ba907b664c8f667b7386484b533a511782493`. It names the comparators by
sealed hash, the two contrasts, the estimator entry points, the resampling settings, the mandatory
tables, the mandatory diagnostics and the output paths, and it is registered before contact.

## 14. Pre-contact evidence on file

| evidence | where |
| --- | --- |
| protocol document | `docs/readiness/2026-09-19-slurp-b1-replicate-v1/protocol-registered-v1.json`, SHA-256 `f9c7bffa95ddd7f4c923b585a5ac1ba8e5940f91ea254e95b3206f6f59c8372e` |
| generation plan | `…/generation-plan-registered-v1.json`, SHA-256 `c4b6ca5ff489d5940d81b8529e658538d2d41e8f9ba9fc7bf940c5c5c17a83d7` |
| FIT plan | `…/fit-plan-registered-v1.json`, SHA-256 `1d60df6210bccdc2f7234c947cd76446bc9e6fc41ef1bfcb6f948795dd55c97e` |
| smoke generation plan | `…/smoke-generation-plan-registered-v1.json`, SHA-256 `243f0bb7e0d931ef735ee25784ebed2b68f8af9359b02dcb9411f448736d8697` |
| smoke FIT plan | `…/smoke-fit-plan-registered-v1.json`, SHA-256 `575d78c22449b599d7e912cccb1e0f5d06e2404630fe68afa8d3a0f5a85b1cdd` |
| config proof | `tests/unit/test_b1_replicate_config.py` |
| prepared-supply identity | asserted by hand in this registration; both `output` digests above |
| hash method | verified on this tree against cell B1's own registered `114b7917…` / `c66d507d…` |

**No `core.flight.cli check` receipt is on file, and that is deliberate.** `FlightRuntime.preflight`
asserts a clean study tree and reserves the attempt in the durable `AttemptStore`; a registration
agent that has not committed can neither pass the first nor is entitled to the second. The composed
and protocol hashes were computed directly through `core.config.compose` /
`core.config.protocol_hash` — the same two functions `check` itself uses — and the method was
verified against a sealed, registered pair. `core.flight.cli wire-check` remains unavailable for any
native-episode cell; the substitute is `tests/unit/test_b1_replicate_config.py`, which drives the
real OpenJiuwen role graph and the real render path over the shared fake transport.

The runbook is [`2026-09-19-slurp-b1-replicate-v1/README.md`](2026-09-19-slurp-b1-replicate-v1/README.md).
